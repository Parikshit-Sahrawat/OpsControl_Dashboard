#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
args=(-f docker-compose.demo.yml)
if [[ -n "${OPSCONTROL_DEMO_COMPOSE_OVERRIDE:-}" ]]; then
  args+=(-f "$OPSCONTROL_DEMO_COMPOSE_OVERRIDE")
fi
docker compose "${args[@]}" down
echo "Local database preserved; add --volumes to docker compose down only to intentionally remove demo data."
