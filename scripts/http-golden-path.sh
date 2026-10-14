#!/usr/bin/env bash
# Disposable real HTTPS lifecycle. Needs Docker, Node/npm, Playwright + Chromium.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo_root"
run_dir="$(mktemp -d "${GOLDEN_RUNTIME_ROOT:-${TMPDIR:-/tmp}}/opscontrol-golden.XXXXXX")"
export BUILDX_CONFIG="${BUILDX_CONFIG:-$run_dir/buildx}"
project="golden-$(basename "$run_dir" | tr '[:upper:].' '[:lower:]-')"
export GOLDEN_EVIDENCE_DIR="${GOLDEN_EVIDENCE_DIR:-$repo_root/docs/screenshots/http-golden-path}"
export GOLDEN_SESSION_FILE="$run_dir/private/session.json"
export GOLDEN_UI_URL=http://127.0.0.1:15173
mkdir -p "$run_dir/private" "$run_dir/evidence" "$run_dir/tls" "$GOLDEN_EVIDENCE_DIR"
chmod 700 "$run_dir/private" "$run_dir/tls"
compose() { docker compose -p "$project" -f "$run_dir/compose.yml" "$@"; }
cleanup() {
  local result=$?
  if [[ "$result" != 0 ]]; then
    compose logs --tail=30 api >&2 || true
    if [[ -f "$run_dir/vite.log" ]]; then tail -20 "$run_dir/vite.log" >&2; fi
  fi
  if [[ -n "${vite_pid:-}" ]]; then kill "$vite_pid" 2>/dev/null || true; fi
  docker rm -f "$project-agent" "$project-target" >/dev/null 2>&1 || true
  compose down --volumes --remove-orphans >/dev/null 2>&1 || true
  docker network rm "$project-target-net" "$project-control-net" >/dev/null 2>&1 || true
  # Removes only this run's private files, including ephemeral TLS/account keys.
  rm -rf "$run_dir"
  exit "$result"
}
trap cleanup EXIT
umask 077
python3 - "$run_dir/private/admin-password" <<'PY'
import pathlib,secrets,sys
pathlib.Path(sys.argv[1]).write_text(secrets.token_urlsafe(32))
PY
# Use the host's verified trust bundle for package downloads through cloud proxies.
mkdir -p "$run_dir/backend"
cp -R backend/app backend/scripts backend/migrations "$run_dir/backend/"
cp backend/requirements.txt backend/alembic.ini "$run_dir/backend/"
cp "${GOLDEN_BUILD_CA_BUNDLE:-/etc/ssl/certs/ca-certificates.crt}" "$run_dir/backend/build-ca.crt"
cat > "$run_dir/backend/Dockerfile" <<'EOF'
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY build-ca.crt /build-ca.crt
COPY requirements.txt .
RUN PIP_CERT=/build-ca.crt pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["sh","-c","alembic upgrade head && python -m scripts.bootstrap_public_demo && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
EOF
cat > "$run_dir/compose.yml" <<EOF
services:
  postgres:
    image: postgres:17
    environment:
      POSTGRES_DB: opscontrol
      POSTGRES_USER: opscontrol
      POSTGRES_PASSWORD: golden-local-only
    volumes: ["pgdata:/var/lib/postgresql/data"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U opscontrol -d opscontrol"]
      interval: 2s
      timeout: 3s
      retries: 30
  api:
    build:
      context: $run_dir/backend
      dockerfile: Dockerfile
    environment:
      ENVIRONMENT: demo
      OPSCONTROL_GOLDEN_PATH: "1"
      SEED_DEMO_DATA: "false"
      DATABASE_URL: postgresql+psycopg://opscontrol:golden-local-only@postgres:5432/opscontrol
      CORS_ORIGINS: http://127.0.0.1:15173
    volumes:
      - "$run_dir/private/admin-password:/run/secrets/demo_admin_password:ro"
      - "$run_dir:/golden"
    depends_on:
      postgres: {condition: service_healthy}
    ports: ["127.0.0.1:18000:8000"]
volumes:
  pgdata:
EOF
compose up --build -d postgres api
for attempt in {1..60}; do
  if curl -fsS http://127.0.0.1:18000/health/db >/dev/null; then break; fi
  sleep 1
done
curl -fsS http://127.0.0.1:18000/health/db >/dev/null
openssl req -x509 -newkey rsa:2048 -nodes -days 1 \
  -keyout "$run_dir/tls/tls.key" -out "$run_dir/tls/tls.crt" \
  -subj '/CN=portal.example.test' -addext 'subjectAltName=DNS:portal.example.test' >/dev/null 2>&1
printf 'healthy\n' > "$run_dir/tls/state"
docker network create --internal --subnet 172.28.77.0/24 "$project-target-net" >/dev/null
docker network create --internal --subnet 172.28.78.0/24 "$project-control-net" >/dev/null
docker network connect --alias opscontrol-control "$project-control-net" "$(compose ps -q api)"
docker run -d --name "$project-target" --network "$project-target-net" \
  --ip 172.28.77.10 --network-alias portal.example.test \
  -v "$run_dir/tls:/fixture:ro" -v "$repo_root/deploy/fixtures/private_https_target.py:/app.py:ro" \
  python:3.12-alpine python /app.py >/dev/null
docker run -d --name "$project-agent" --network "$project-target-net" \
  -v "$repo_root/backend:/src:ro" -v "$repo_root/deploy/fixtures:/tests:ro" \
  -v "$run_dir/private:/golden/private:ro" -v "$run_dir/tls/tls.crt:/fixture/ca.crt:ro" \
  -e SSL_CERT_FILE=/fixture/ca.crt -e PYTHONPATH=/src \
  -e NO_PROXY=opscontrol-control -e no_proxy=opscontrol-control python:3.12-alpine sleep 3600 >/dev/null
docker network connect "$project-control-net" "$project-agent"
for attempt in {1..30}; do
  if docker exec "$project-target" python -c 'import socket;socket.create_connection(("127.0.0.1",443),1).close()' 2>/dev/null; then break; fi
  sleep 1
done
# Trust only this fixture certificate; verify hostname and TLS, never bypass them.
docker exec "$project-agent" python /tests/probe_private_https.py SUCCESS
compose exec -T api python -m scripts.http_golden_path_probe setup
(
  cd frontend
  exec env VITE_API_BASE_URL=http://127.0.0.1:18000 ./node_modules/.bin/vite --host 127.0.0.1 --port 15173 --strictPort
) > "$run_dir/vite.log" 2>&1 &
vite_pid=$!
for attempt in {1..30}; do
  if curl -fsS "$GOLDEN_UI_URL" >/dev/null; then break; fi
  sleep 1
done
curl -fsS "$GOLDEN_UI_URL" >/dev/null
node frontend/scripts/http_golden_path.mjs configured
for phase in healthy failed recovered; do
  if [[ "$phase" == failed ]]; then printf 'failed\n' > "$run_dir/tls/state"; else printf 'healthy\n' > "$run_dir/tls/state"; fi
  compose exec -T api python -m scripts.http_golden_path_probe schedule
  docker exec "$project-agent" python /tests/golden_agent_cycle.py
  compose exec -T api python -m scripts.http_golden_path_probe "$phase"
  node frontend/scripts/http_golden_path.mjs "$phase"
done
compose exec -T api python -m scripts.http_golden_path_probe isolation
# Internal networks prevent public outbound access; exercise the network boundary.
docker exec -i "$project-agent" python - <<'PY'
import socket
try:
    socket.create_connection(('1.1.1.1',443),timeout=2)
except OSError:
    print('Network-level public egress denial PASS')
else:
    raise AssertionError('Unexpected public egress')
PY
cp "$run_dir/evidence/report.json" "$GOLDEN_EVIDENCE_DIR/report.json"
chmod 644 "$GOLDEN_EVIDENCE_DIR/"*.png "$GOLDEN_EVIDENCE_DIR/report.json"
printf 'HTTP golden path PASS; screenshots and redacted report: %s\n' "$GOLDEN_EVIDENCE_DIR"
