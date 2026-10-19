# Executed Sprint 08 delivery commands

Commands run from repository root unless otherwise indicated. Owned-local test
network/Docker access was approved by the execution environment. No vendor or
production environment was used. Final logs are copied into `evidence/`.

## Backend unit/contract gate

Working directory: `backend`.

```bash
ENV=test .venv/bin/python -m unittest \
  tests.test_access_control tests.test_pipeline_adapters \
  tests.test_pipeline_runtime_v15 tests.test_pipeline_transport_v16 \
  tests.test_pentaho_r1 tests.test_pentaho_surface_contracts \
  tests.test_pentaho_execution_contracts tests.test_pentaho_review_contracts \
  tests.test_pentaho_history_contracts tests.test_pentaho_incident_contracts \
  tests.test_unified_v15_contracts tests.test_native_incidents_v15 \
  tests.test_sprint07_frontend_contracts -v
```

155 passed; zero failures/skips. `evidence/unit.txt`.

## Complete owned PostgreSQL, HTTP, browser and migration gate

```bash
V16_TEST_TARGETS=tests.test_pipeline_ownership_v16,tests.test_pentaho_execution_r1,tests.test_pentaho_review_r1,tests.test_pentaho_history_r1,tests.test_pentaho_incident_r1,tests.test_sprint08_rbac.Sprint08RBAC \
V16_STAGING_PRESERVATION=1 \
V16_PENTAHO_R1_ACCEPTANCE=1 V16_PENTAHO_REVIEW_ACCEPTANCE=1 \
V16_PENTAHO_HISTORY_ACCEPTANCE=1 V16_PENTAHO_INCIDENT_ACCEPTANCE=1 \
V16_API_ACCEPTANCE=1 V16_SPRINT08_ACCEPTANCE=1 \
V16_BROWSER_ACCEPTANCE=1 V16_SPRINT07_ACCEPTANCE=1 \
V16_EVIDENCE_DIR=/tmp/sprint08-delivery \
python -u scripts/v16-acceptance.py
```

169 PostgreSQL tests passed with zero failures/skips; 27 existing and 14 new HTTP
groups passed; existing configuration browser, 16 Sprint07 and 5 Sprint08 browser
groups passed. The harness creates/removes its own local PostgreSQL container and
local API/UI processes, executes Alembic upgrade/check and preservation probes,
checks populated downgrade refusal and an empty downgrade/upgrade, and writes
`evidence/gate.txt`, `ownership.txt`, JSON results and screenshots. No live Pentaho
runtime acceptance is claimed.

An intermediate focused pass used `V16_TEST_TARGETS=tests.test_sprint08_rbac.Sprint08RBAC,tests.test_pentaho_incident_r1`
with the same HTTP/browser flags, without `V16_STAGING_PRESERVATION`, writing to
`/tmp/sprint08-followup`. That pass preceded the final two PostgreSQL tests and final
transaction-cleanup/agent compatibility checks; the complete final run supersedes it.
Earlier failed runs and corrected test fixtures are described in `REPORT.md`.

## Frontend gates

```bash
npm --prefix frontend test
npm --prefix frontend run lint
npm --prefix frontend run build
```

20 tests passed, zero failures/skips. Lint and build exit zero. The build reports
a nonblocking 500 kB chunk warning. Browser scripts executed by the owned harness:

```bash
node frontend/scripts/pipeline_v16_acceptance.mjs
node frontend/scripts/pipeline_sprint07_acceptance.mjs
node frontend/scripts/sprint08_acceptance.mjs
```

Their fixture URLs, temporary credentials and database connection strings are
provided privately by the harness; do not run them against an arbitrary backend.

## Python static and import gates

Exact argv lists (not abbreviated globs) are in `evidence/black-command.json`,
`ruff-command.json` and `compile-command.json`. All returned zero:

```text
backend/.venv/bin/black --check <21 substantive/new Python files>
backend/.venv/bin/ruff check --select F,E9 <all 26 changed Python files>
backend/.venv/bin/python -m py_compile <all 26 changed Python files>
```

Five minimally edited legacy HTTP probes are excluded only from whole-file Black
to preserve their previous formatting; Ruff and compilation include them.

Working directory: `backend`:

```bash
ENV=test .venv/bin/python - <<'PY'
import app.main
from sqlalchemy.orm import configure_mappers
configure_mappers()
print('Application imports and ORM mapper configuration PASS')
PY
.venv/bin/alembic heads
```

Head: `0037_access_boundaries`. `evidence/imports.txt`, `heads.txt`.

## Delivery integrity

```bash
git diff --check
git diff --cached --check
git ls-remote origin refs/heads/feat/arch-etl-001-v16-r1
git commit -m "Implement Sprint 08 scoped RBAC and delegated administration"
git push origin HEAD:feat/arch-etl-001-v16-r1
git rev-parse HEAD
git ls-remote origin refs/heads/feat/arch-etl-001-v16-r1
git status --porcelain
```

Delivery additionally compares the approved architecture and Sprint01–07 evidence
to starting HEAD, verifies the source SHA-256 manifest and checks the final remote
SHA equals local HEAD. Commit/push results are reported in the completion message;
the commit cannot contain its own SHA. No PR, merge or deployment commands are run.
