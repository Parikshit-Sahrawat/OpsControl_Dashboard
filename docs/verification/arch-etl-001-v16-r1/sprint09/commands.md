# Executed Sprint 09 gates

Run from repository root unless stated. All HTTP, PostgreSQL and browser tests
use the owned-local acceptance harness; none target vendor or production systems.
Full final logs are under `evidence/`. Earlier failed development runs are not
counted as passed final gates.

## Backend unit and contracts

Working directory: `backend`.

```bash
ENV=test .venv/bin/python -m unittest \
  tests.test_access_control tests.test_pipeline_adapters \
  tests.test_pipeline_runtime_v15 tests.test_pipeline_transport_v16 \
  tests.test_pentaho_r1 tests.test_pentaho_surface_contracts \
  tests.test_pentaho_execution_contracts tests.test_pentaho_review_contracts \
  tests.test_pentaho_history_contracts tests.test_pentaho_incident_contracts \
  tests.test_unified_v15_contracts tests.test_native_incidents_v15 \
  tests.test_sprint07_frontend_contracts tests.test_sprint09_contracts -v
```

159 passed; zero failures/skips. The new four contract cases also ran separately
using `ENV=test .venv/bin/python -m unittest tests.test_sprint09_contracts -v`.
An initial root-directory discovery invocation failed to import `app`; the
correct backend working-directory invocation above passed.

## Complete PostgreSQL, migration, HTTP, performance and Chromium gate

```bash
V16_TEST_TARGETS=tests.test_pipeline_ownership_v16,tests.test_pentaho_execution_r1,tests.test_pentaho_review_r1,tests.test_pentaho_history_r1,tests.test_pentaho_incident_r1,tests.test_sprint08_rbac.Sprint08RBAC,tests.test_sprint09_hardening.Sprint09Hardening \
V16_STAGING_PRESERVATION=1 \
V16_PENTAHO_R1_ACCEPTANCE=1 V16_PENTAHO_REVIEW_ACCEPTANCE=1 \
V16_PENTAHO_HISTORY_ACCEPTANCE=1 V16_PENTAHO_INCIDENT_ACCEPTANCE=1 \
V16_API_ACCEPTANCE=1 V16_SPRINT08_ACCEPTANCE=1 V16_SPRINT09_ACCEPTANCE=1 \
V16_BROWSER_ACCEPTANCE=1 V16_SPRINT07_ACCEPTANCE=1 \
V16_EVIDENCE_DIR=/tmp/sprint09-final \
python -u scripts/v16-acceptance.py
```

The complete final gate includes 177 PostgreSQL tests, 47 authenticated HTTP
groups, 120 measured HTTP requests, 24 revocation-load reads plus five subsequent
denials, nine timed PostgreSQL scenarios, the existing configuration browser
workflow, 16 Sprint07, five Sprint08 and three Sprint09 Chromium groups. The
harness executes all migration/preservation/drift/downgrade checks in its own
database. Actual results are in `evidence/gate.txt`, `ownership.txt` and JSON.

The new performance and resilience subprocesses are:

```bash
# Working directory: backend; fixture environment supplied by the owned harness.
.venv/bin/python -m scripts.sprint09_http_probe
.venv/bin/python -m scripts.sprint09_resilience_probe
```

They require `OPSCONTROL_V16_ACCEPTANCE=1`, `ENVIRONMENT=test` and private local
fixture paths. They must not be pointed at an arbitrary backend.

Focused development PostgreSQL commands used:

```bash
V16_TEST_TARGETS=tests.test_sprint09_hardening.Sprint09Hardening \
V16_EVIDENCE_DIR=/tmp/sprint09-focused \
python -u scripts/v16-acceptance.py
```

This initially exposed fixture uniqueness, query-count instrumentation and UUID
assertion mistakes, corrected without weakening the underlying constraints.
Focused integration/browser commands used:

```bash
V16_TEST_TARGETS=tests.test_sprint09_hardening.Sprint09Hardening \
V16_API_ACCEPTANCE=1 V16_SPRINT09_ACCEPTANCE=1 V16_BROWSER_ACCEPTANCE=1 \
V16_EVIDENCE_DIR=/tmp/sprint09-integration \
python -u scripts/v16-acceptance.py

V16_TEST_TARGETS=tests.test_sprint09_hardening.Sprint09Hardening \
V16_API_ACCEPTANCE=1 V16_SPRINT09_ACCEPTANCE=1 V16_BROWSER_ACCEPTANCE=1 \
V16_EVIDENCE_DIR=/tmp/sprint09-browser \
python -u scripts/v16-acceptance.py
```

The first integration runs exposed the missing mandatory resource/job fixture
binding, the inventory N+1 bottleneck, hidden HTML-option waiting and selector
accessible naming. The final focused browser run passed eight PostgreSQL cases,
existing HTTP nine groups, new HTTP six groups, nine resilience scenarios,
configuration browser, three new browser groups and migration/schema checks.
Two intermediate broad runs passed their PostgreSQL/API stages but stopped at
browser synchronization/naming issues; only the complete final run is reported
as the full passing gate. Intermediate before-batching measurements are retained
under `evidence/performance-before-inventory-batch.json`.

## Frontend gates

```bash
npm --prefix frontend test
node --test --test-isolation=none --test-reporter=spec \
  frontend/scripts/permissions.test.mjs \
  frontend/scripts/pipelines.test.mjs \
  frontend/scripts/explicit_scope.test.mjs
npm --prefix frontend run lint
npm --prefix frontend run build
```

The normal Node24 isolated reporter summarizes three test files; the second
command prints all 22 passing cases explicitly. Both execute the existing test
assertions; isolation is not used to skip or suppress them. ESLint and Vite exit
zero; the entry-chunk warning remains.

Actual browser scripts executed by the controlled harness:

```bash
node frontend/scripts/pipeline_v16_acceptance.mjs
node frontend/scripts/pipeline_sprint07_acceptance.mjs
node frontend/scripts/sprint08_acceptance.mjs
node frontend/scripts/sprint09_acceptance.mjs
```

Credentials/fixture URLs remain in the private harness directory, not in this
report. Browser screenshots are actual captures from the owned backend.

## Static checks and imports

```bash
python /tmp/sprint09-quality.py
```

The exact quality driver is preserved as `evidence/quality-check.txt`. Exact
Black/Ruff/compile argv lists are in the corresponding `*-command.json` files.
It checks 12 implementation/new Python files with Black and Ruff `F,E9`, compiles
all 23 changed Python files and checks every changed `.mjs` with `node --check`.
Eleven minimally edited legacy probes retain their previous whole-file formatting.
Their full `F,E9` diagnostics are compared to the exact `99b38e5` file using Ruff
`--stdin-filename`; no new diagnostic is allowed. The existing findings are
recorded in `legacy-ruff-baseline.json`, not suppressed or reported clean.

Working directory: `backend`:

```bash
ENV=test .venv/bin/python - <<'PY'
import app.main
from sqlalchemy.orm import configure_mappers
from scripts.export_api_inventory import inventory
import json
from pathlib import Path
configure_mappers()
Path('/tmp/sprint09-final/api-inventory.json').write_text(json.dumps(inventory(), indent=2)+'\n')
print('Imports, ORM mapper configuration and current route inventory PASS')
PY
.venv/bin/alembic heads
```

Head remains `0037_access_boundaries`.

## Integrity and delivery

```bash
git diff --check
git diff --cached --check
git ls-remote origin refs/heads/feat/arch-etl-001-v16-r1
git commit -m "Harden Sprint 09 scoped archives and integration regression"
git push origin HEAD:feat/arch-etl-001-v16-r1
git rev-parse HEAD
git ls-remote origin refs/heads/feat/arch-etl-001-v16-r1
git status --porcelain
```

Delivery compares the approved architecture, migration files and Sprint01–08
evidence to starting HEAD, verifies the source manifest and the exact staged-path
list, then verifies remote SHA equals local HEAD and the working tree is clean.
No PR, merge, deployment, source activation or ETL execution command is run.
