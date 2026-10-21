# UI Alignment Fix continuation — development evidence and merge gate

Reference branch: `feat/ui-alignment-fix`, starting commit `1379d1d6cd135e51294c3bde80b5fd51b3f807cc`. On 2026-10-21, fetched `origin/main` was `4ebd8d8a64dff75ef7577c169c76e651e435dcc7`. Its intervening Stage B PR #40 deployment changes did not overlap this continuation's files. This document describes a development candidate; it is **not** independent UAT acceptance.

## Changes and contract

- `frontend/src/pages/UnifiedResourceManagement.jsx`: legacy Pipeline and API Endpoint create/edit use the existing full-page resource workspace with three guided stages: identity, configuration, review/save. The ten-stage Compute workspace and existing native integration read/edit controls remain. No create action was moved into Operations, no new backend model or endpoint was added, and save does not certify monitoring health.
- `frontend/scripts/ui_recovery_acceptance.mjs`: added stage navigation, single-save, light/dark persistence and 390 px workspace overflow checks. No ETL or probe was executed.
- `backend/app/unified/reporting.py`: scalar report `environment` once again compiles to scalar equality; explicit `environments` still compiles to a multi-value filter. `backend/tests/test_unified_v15_contracts.py` checks both shapes. This repairs a failure found by the full backend unit discovery without weakening either filter.
- [Traceability](TRACEABILITY.md) maps UI-001–UI-023 and grouped UAT Test 1 source requirements to actual code and remaining gates. The approved source texts are in `source/`.

## Actual validation

Isolated browser fixture: newly created local Compose project `opscontrol-s14-uat-9b56d220` at `/tmp/opscontrol-ui-guided-20261021`, synthetic UAT A/B customer data, PostgreSQL 17 migrated by the UAT startup script to `0037_access_boundaries`. The database container used its own anonymous volume `1d481ab2bf123fa94508ad430d48cb05576dad1d69b02763b5e6d6f89a590457`. Existing Development, Demo, Pentaho and UAT projects were not reset or changed. The tested UI was served from a development worktree before this candidate was committed, so this is **not** exact-commit independent UAT.

After browser checks, `scripts/uat/local_environment.py stop` stopped only this project's API, frontend and PostgreSQL processes. Its state and PostgreSQL volume were retained; `reset` and `docker compose down -v` were not used.

| Command | Result |
| --- | --- |
| `npm run lint --prefix frontend` | PASS |
| `npm test --prefix frontend` | PASS, 5/5 test files; included-module line coverage 97.40%, not the critical backend coverage gate |
| `npm run build --prefix frontend` | PASS; existing bundle-size warning (>500 kB) |
| `OPSCONTROL_UAT_STATE_DIR=/tmp/opscontrol-ui-guided-20261021 node frontend/scripts/ui_recovery_acceptance.mjs` | PASS, 97 Chromium checks, 0 failures, after allowing local Chromium startup |
| `OPSCONTROL_UAT_STATE_DIR=/tmp/opscontrol-ui-guided-20261021 node frontend/scripts/ui_alignment_onboarding_acceptance.mjs` | PASS, 5 checks, synthetic resource identity/collector/package request; no agent install or monitoring activation |
| `OPSCONTROL_UAT_STATE_DIR=/tmp/opscontrol-ui-guided-20261021 node frontend/scripts/access_onboarding_acceptance.mjs` | PASS, 3 checks, no grant mutation |
| `ENV=test /workspace/OpsControl_Dashboard/backend/.venv/bin/python -m unittest discover -s tests -q` from `backend/` | Initial run FAIL (1 scalar report filter regression); after correction PASS, 503 tests, 210 skipped |
| `OPSCONTROL_TEST_PYTHON=/workspace/OpsControl_Dashboard/backend/.venv/bin/python OPSCONTROL_TEST_EVIDENCE_DIR=/tmp/opscontrol-ui-critical-20261021 bash scripts/test-quality.sh unit` | PASS; instrumented unit and frontend tests |
| Same variables, `bash scripts/test-quality.sh coverage` | **FAIL**, 45.04% versus unchanged 80% threshold. Only unit paths were instrumented; PostgreSQL/owned-lab/API/agent acceptance inputs were not executed, so this is an incomplete coverage run, not a waiver. Report: `/tmp/opscontrol-ui-critical-report.log`. |
| `git diff --check` | PASS |
| `python -m black --check backend/app/unified/reporting.py backend/tests/test_unified_v15_contracts.py`; scoped `ruff check --select E9,F63,F7,F82` | PASS after formatting the directly affected reporting file |

The first browser rerun in the restricted shell failed to launch Chromium (`setsockopt: Operation not permitted`); the same test passed under the allowed local-browser execution. A previous browser run found a loading race in the synthetic Organisational Access assertion; the script now waits for the table header before checking rows, and the API was independently checked to return four scoped grants.

## Direct-main decision

**BLOCKED.** The unchanged 80% critical coverage gate did not pass with executed evidence. PostgreSQL preservation/ownership, full browser/CI gates against an immutable candidate, and owner-accepted independent UAT remain outstanding. No `main` merge or push is permitted on this evidence. Pentaho RT-001–RT-020 remain NOT RUN; production readiness is not established.

For independent UAT, build and deploy the exact candidate commit through the approved controlled process, record the resulting source SHA and migration revision, then work through the [manual UAT checklist](../sprint14-baseline/ui-recovery/MANUAL_UAT_CHECKLIST.md) and [UAT Test 1 source](source/UAT_TEST_1_UI_ALIGNMENT_FIX.txt). Confirm customer A/B isolation, granted versus read-only actions, VM draft/resume and blocked activation, ETL/API configuration persistence, Operations evidence freshness, Reports, keyboard/mobile and both themes. An owner acceptance record tied to that immutable SHA is required before direct-main integration.
