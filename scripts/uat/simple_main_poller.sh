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
