#!/usr/bin/env bash
# Local public-safe demo, requires Docker Compose. Never publish ports.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .demo-private
chmod 700 .demo-private
if [[ ! -f .demo-private/admin-password ]]; then
  umask 077
  python3 - <<'PY'
import pathlib,secrets
pathlib.Path(".demo-private/admin-password").write_text(secrets.token_urlsafe(24),encoding="utf-8")
PY
fi
chmod 600 .demo-private/admin-password
if ! docker compose -f docker-compose.demo.yml up --build --detach; then
  echo "Primary image registry failed; trying alternate PostgreSQL mirror..."
  if docker pull postgres:17; then
    docker tag postgres:17 public.ecr.aws/docker/library/postgres:17
    docker compose -f docker-compose.demo.yml up --build --detach
  else
    echo "Container registry unavailable or rate-limited." >&2
    exit 1
  fi
fi
echo
echo "OpsControl local demo: http://127.0.0.1:5173"
echo "Username: demo-admin"
echo "Password saved locally in .demo-private/admin-password"
echo "No private infrastructure is connected. All data is fictional."
echo "To stop: docker compose -f docker-compose.demo.yml down"
