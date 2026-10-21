#!/usr/bin/env bash
# Reproducible development/CI gates. No production database is used by this script.
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
PYTHON=${OPSCONTROL_TEST_PYTHON:-"$ROOT/backend/.venv/bin/python"}
OUT=${OPSCONTROL_TEST_EVIDENCE_DIR:-"/tmp/opscontrol-v15-quality"}
mkdir -p "$OUT"
export COVERAGE_FILE="$OUT/.coverage"
CONFIG="$OUT/coverage.ini"
cat > "$CONFIG" <<EOF_CONFIG
[run]
branch = True
parallel = True
sigterm = True
source =
    $ROOT/backend/app/registry
    $ROOT/backend/app/unified
    $ROOT/backend/app/telemetry
    $ROOT/backend/app/pipeline_adapters
    $ROOT/backend/app/native_incidents
    $ROOT/agent
[report]
precision = 2
show_missing = True
skip_empty = True
EOF_CONFIG
# Child FastAPI/worker/Agent processes contribute real executed-line evidence.
mkdir -p "$OUT/instrumentation"
cat > "$OUT/instrumentation/sitecustomize.py" <<'EOF_PYTHON'
import os
if os.environ.get("COVERAGE_PROCESS_START"):
    import coverage
    coverage.process_startup()
EOF_PYTHON
unit() {
  (cd backend && "$PYTHON" -m coverage run --rcfile="$CONFIG" -m unittest discover -s tests -v)
  npm test --prefix frontend | tee "$OUT/frontend-coverage.txt"
}
agent() {
  (cd backend && "$PYTHON" -m coverage run --rcfile="$CONFIG" -m unittest discover -s tests -p 'test_agent_v15.py' -v)
  (cd backend && "$PYTHON" -m coverage run --rcfile="$CONFIG" -m unittest discover -s tests -p 'test_collection_v15.py' -v)
  bash -n agent/install-linux.sh agent/uninstall-linux.sh
}
pentaho() {
  # Unit discovery intentionally skips owned-PostgreSQL cases. Execute them
  # under the same coverage instrumentation before enforcing the configured floor.
  local targets
  targets=$("$PYTHON" -c 'from pathlib import Path;print(",".join("tests."+p.stem for p in sorted(Path("backend/tests").glob("test_*.py"))))')
  ENV=test COVERAGE_PROCESS_START="$CONFIG" \
    PYTHONPATH="$OUT/instrumentation${PYTHONPATH:+:$PYTHONPATH}" \
    V16_STAGING_PRESERVATION=1 V16_PENTAHO_R1_ACCEPTANCE=1 \
    V16_PENTAHO_REVIEW_ACCEPTANCE=1 V16_PENTAHO_HISTORY_ACCEPTANCE=1 \
    V16_PENTAHO_INCIDENT_ACCEPTANCE=1 V16_SPRINT08_ACCEPTANCE=1 \
    V16_SPRINT09_ACCEPTANCE=1 V16_SPRINT07_ACCEPTANCE=1 V16_SPRINT13_RECOVERY=1 \
    V16_API_ACCEPTANCE=1 V16_BROWSER_ACCEPTANCE=1 V16_TEST_TARGETS="$targets" \
    V16_EVIDENCE_DIR="$OUT/pentaho-postgres" "$PYTHON" scripts/v16-acceptance.py
}
owned_lab() {
  local mode=$1
  local runtime=0 browser=0
  case "$mode" in
    runtime) runtime=1 ;;
    browser) browser=1 ;;
    *) printf 'Unknown owned lab mode: %s\n' "$mode" >&2; return 2 ;;
  esac
  command -v docker >/dev/null
  docker info >/dev/null
  ENV=test COVERAGE_PROCESS_START="$CONFIG" \
    PYTHONPATH="$OUT/instrumentation${PYTHONPATH:+:$PYTHONPATH}" \
    ARCH001_API_ACCEPTANCE=1 ARCH001_ENGINE_ACCEPTANCE=1 \
    ARCH001_RUNTIME_ACCEPTANCE="$runtime" ARCH001_BROWSER_ACCEPTANCE="$browser" \
    ARCH001_EVIDENCE_DIR="$OUT/owned-lab-$mode" \
    "$PYTHON" scripts/arch001-acceptance.py
}
quality() {
  "$PYTHON" -m black --check backend/app/registry backend/app/unified backend/app/telemetry backend/app/pipeline_adapters backend/app/native_incidents agent scripts/test-performance.py
  "$PYTHON" -m ruff check --select E9,F63,F7,F82 backend/app/registry backend/app/unified backend/app/telemetry backend/app/pipeline_adapters backend/app/native_incidents agent scripts/test-performance.py
  local prettier=${PRETTIER_BIN:-"/tmp/opscontrol-access-prettier/node_modules/.bin/prettier"}
  if [[ ! -x "$prettier" ]]; then
    printf '%s\n' 'Missing Prettier: set PRETTIER_BIN to a pinned installed executable.' >&2
    return 1
  fi
  "$prettier" --check frontend/src/pages/AccessManagement.jsx frontend/src/pages/AccessOnboarding.jsx frontend/src/access-management.css frontend/scripts/access_v15.mjs
  npm run lint --prefix frontend
  npm run build --prefix frontend
}
security() {
  (cd backend && "$PYTHON" -m unittest discover -s tests -p 'test_access_control.py' -v)
  (cd backend && "$PYTHON" -m unittest discover -s tests -p 'test_release_hardening.py' -v)
  (cd backend && "$PYTHON" -m unittest discover -s tests -p 'test_remote_auth.py' -v)
  # Keep both reports even when one audit fails; never suppress its exit status.
  local pip_status=0 npm_status=0
  "$PYTHON" -m pip_audit -r backend/requirements-providers.txt -r backend/requirements-hosts.txt --strict --format json --output "$OUT/pip-audit.json" || pip_status=$?
  npm audit --prefix frontend --audit-level=high --json > "$OUT/npm-audit.json" || npm_status=$?
  if (( pip_status != 0 || npm_status != 0 )); then
    printf 'Dependency audit failed: pip=%s npm=%s. See %s reports.\n' "$pip_status" "$npm_status" "$OUT" >&2
    return 1
  fi
}
coverage_report() {
  "$PYTHON" -m coverage combine --keep --rcfile="$CONFIG" "$OUT"
  "$PYTHON" -m coverage json --rcfile="$CONFIG" -o "$OUT/coverage.json"
  "$PYTHON" -m coverage xml --rcfile="$CONFIG" -o "$OUT/coverage.xml"
  "$PYTHON" -m coverage report --rcfile="$CONFIG" --fail-under="${OPSCONTROL_COVERAGE_MIN:-70}"
}
compatibility() {
  ENV=test COVERAGE_PROCESS_START="$CONFIG" PYTHONPATH="$OUT/instrumentation${PYTHONPATH:+:$PYTHONPATH}" ACCESS_EVIDENCE_DIR="$OUT/access-regression" "$PYTHON" scripts/access-acceptance.py
  ENV=test COVERAGE_PROCESS_START="$CONFIG" PYTHONPATH="$OUT/instrumentation${PYTHONPATH:+:$PYTHONPATH}" UAT_EVIDENCE_DIR="$OUT/consolidated-uat" "$PYTHON" scripts/uat/acceptance.py
}
performance() {
  : "${OPSCONTROL_PERFORMANCE_INPUTS:?Set owner-only local lab credential/input JSON path}"
  ENV=test OPSCONTROL_PERFORMANCE_ACCEPTANCE=1 "$PYTHON" scripts/test-performance.py --inputs "$OPSCONTROL_PERFORMANCE_INPUTS" --output "$OUT/performance.json"
}
case "${1:-unit}" in
  unit) unit ;;
  integration) owned_lab runtime ;;
  e2e) owned_lab runtime; owned_lab browser ;;
  agent) agent ;;
  pentaho) pentaho ;;
  quality) quality ;;
  security) security ;;
  compatibility) compatibility ;;
  coverage) coverage_report ;;
  performance) performance ;;
  docker) ACCESS_DOCKER_EVIDENCE_DIR="$OUT/docker-smoke" "$PYTHON" scripts/access-docker-demo.py ;;
  all) quality; unit; agent; pentaho; owned_lab runtime; owned_lab browser; compatibility; ACCESS_DOCKER_EVIDENCE_DIR="$OUT/docker-smoke" "$PYTHON" scripts/access-docker-demo.py; security; coverage_report ;;
  *) printf 'Unknown test group: %s\n' "$1" >&2; exit 2 ;;
esac
