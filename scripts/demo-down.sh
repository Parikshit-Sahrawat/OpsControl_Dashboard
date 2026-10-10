#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose -f docker-compose.demo.yml down
echo "Local database preserved; add --volumes to docker compose down only to intentionally remove demo data."
