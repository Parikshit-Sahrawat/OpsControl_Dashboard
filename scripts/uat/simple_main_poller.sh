#!/usr/bin/env bash
# OpsControl local UAT: poll remote main and update application services only.
set -Eeuo pipefail
: "${OPSCONTROL_UAT_CHECKOUT:?Set dedicated checkout directory}"
: "${OPSCONTROL_UAT_COMPOSE_FILES:?Set absolute colon-separated Compose paths}"
: "${OPSCONTROL_UAT_API_HEALTH:?Set local API health URL}"
: "${OPSCONTROL_UAT_FRONTEND_HEALTH:?Set local frontend URL}"
: "${OPSCONTROL_UAT_STATE:?Set private persistent state directory}"
: "${OPSCONTROL_UAT_PROJECT:=opscontrol-uat}"
[[ "${OPSCONTROL_UAT_ENABLED:-false}" == true ]] || { echo "Disabled"; exit 0; }
: "${OPSCONTROL_UAT_HOME:?Set UAT private home}"
: "${OPSCONTROL_UAT_APPROVED_MIGRATIONS_TREE:?Set approved migration tree}"
: "${OPSCONTROL_UAT_APPROVED_ALEMBIC_HEAD:?Set approved DB revision}"
[[ -d "$OPSCONTROL_UAT_CHECKOUT/.git" ]] || { echo "Dedicated normal Git checkout required" >&2; exit 1; }
mkdir -p "$OPSCONTROL_UAT_STATE"
chmod 700 "$OPSCONTROL_UAT_STATE"
exec 9>"$OPSCONTROL_UAT_STATE/deploy.lock"
flock -n 9 || { echo "Another deployment running"; exit 0; }
cd "$OPSCONTROL_UAT_CHECKOUT"
[[ -z "$(git status --porcelain)" ]] || { echo "Checkout dirty: refusing destructive reset" >&2; exit 1; }
[[ "$(git branch --show-current)" == main ]] || { echo "Dedicated checkout must track main" >&2; exit 1; }
git fetch --no-tags origin +refs/heads/main:refs/remotes/origin/main
target="$(git rev-parse refs/remotes/origin/main)"
last="$(cat "$OPSCONTROL_UAT_STATE/deployed.sha" 2>/dev/null || true)"
[[ "$target" != "$last" ]] || { echo "Already deployed $target"; exit 0; }
# Preserve current revision for recovery; do not claim rollback on failure.
previous="$(git rev-parse HEAD)"
# Refuse deployment of changes to migration history.
tree="$(git rev-parse "$target:backend/migrations")"
[[ "$tree" == "$OPSCONTROL_UAT_APPROVED_MIGRATIONS_TREE" ]] || { echo "Migration tree changed: refusing deployment" >&2; exit 1; }
git merge --ff-only "$target"
args=(docker compose -p "$OPSCONTROL_UAT_PROJECT")
IFS=: read -r -a files <<< "$OPSCONTROL_UAT_COMPOSE_FILES"
for file in "${files[@]}"; do
  [[ -f "$file" ]] || { echo "Missing Compose file: $file" >&2; exit 1; }
  args+=(-f "$file")
done
# Guard against Compose files accidentally omitting the expected application services.
"${args[@]}" config --services | grep -Fxq api
"${args[@]}" config --services | grep -Fxq worker
"${args[@]}" config --services | grep -Fxq frontend
"${args[@]}" config --services | grep -Fxq postgres
# Fail closed unless the effective API startup bypasses migration and bootstrap.
config_json="$("${args[@]}" config --format json)"
printf '%s' "$config_json" | python3 -c '
import json, os, pathlib, sys
services=json.load(sys.stdin)["services"]
expected=["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
if services["api"].get("command") != expected:
    sys.exit("Unsafe API startup command")
home=pathlib.Path(os.environ["OPSCONTROL_UAT_HOME"]).resolve()
for service, targets in {
  "api": ("/run/secrets/demo_admin_password", "/opt/opscontrol/packages"),
  "worker": ("/run/secrets/demo_admin_password", "/opt/opscontrol/packages"),
  "ingestion-gateway": ("/etc/opscontrol/tls/tls.crt", "/etc/opscontrol/tls/tls.key")
}.items():
    mounts={v["target"]:pathlib.Path(v["source"]).resolve() for v in services[service].get("volumes",[]) if v.get("type")=="bind"}
    for target in targets:
        src=mounts.get(target)
        if src is None or not src.is_relative_to(home) or not src.exists():
            sys.exit("Missing/unsafe private mount: "+service+" "+target)
'
current="$(docker exec "$OPSCONTROL_UAT_PROJECT-postgres-1" psql -U opscontrol -d opscontrol -Atqc 'SELECT version_num FROM alembic_version' | tr -d '\r')"
[[ "$current" == "$OPSCONTROL_UAT_APPROVED_ALEMBIC_HEAD" ]] || { echo "Database revision mismatch; refusing deployment" >&2; exit 1; }
# Never run 'down', volume deletion, postgres recreation, or database migrations.
"${args[@]}" build api worker frontend
"${args[@]}" up -d --no-deps --no-build api worker frontend
healthy=false
for i in $(seq 1 60); do
  if curl -fsS --max-time 4 "$OPSCONTROL_UAT_API_HEALTH" >/dev/null &&
     curl -fsS --max-time 4 "$OPSCONTROL_UAT_FRONTEND_HEALTH" >/dev/null; then
    healthy=true; break
  fi
  sleep 2
done
[[ "$healthy" == true ]] || { echo "Health check FAILED; previous checkout was $previous; no automatic rollback" >&2; exit 1; }
printf '%s\n' "$target" > "$OPSCONTROL_UAT_STATE/deployed.sha.tmp"
mv "$OPSCONTROL_UAT_STATE/deployed.sha.tmp" "$OPSCONTROL_UAT_STATE/deployed.sha"
echo "UAT deployed $target"
