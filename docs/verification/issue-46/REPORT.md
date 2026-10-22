# Issue #46 — onboarding and authorization verification

Status: **VERIFIED (developer verification only)**. No product defect was confirmed. Independent UAT, genuine provider acceptance, and production certification remain open.

## Immutable baseline and environment

- Repository: `Parikshit-Sahrawat/OpsControl_Dashboard`.
- Source tested: `ae4df971d07fa65bbe9e50fbdacba2c68ceae7be` (`origin/main`, verified before branching).
- Verification branch: `verify/issue-46-onboarding-authorization`, created from that exact commit; no runtime, migration, RBAC, fixture, or CI changes.
- Date: 2026-10-22 UTC. Linux, Python 3.12, Node 24, Chromium, Docker 28.4, disposable `postgres:17-alpine` containers with random owned names. Alembic head: `0037_access_boundaries`.
- Test services bound to loopback; synthetic customers, employees, resources and telemetry only. Existing UAT volumes, customer environments, production infrastructure, and ETL workloads were untouched. Disposable container cleanup was performed by each harness.

## A. Post-merge main gate

PRs [#48](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/pull/48), [#49](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/pull/49), and [#50](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/pull/50) are merged. PR #50 carried the combined content; #49's head was not separately rebased after #48. This report verifies the resulting main source and does not retrospectively claim separate #49-head CI success.

| Main push workflow at exact SHA | Result | Evidence |
| --- | --- | --- |
| OpsControl Validation | PASS | [run 39827607825](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/actions/runs/39827607825) |
| ARCH-001 V1.5 continuous quality | PASS | [run 39827607578](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/actions/runs/39827607578): unit, Agent, disposable PostgreSQL, Sprint 07 browser, Access/security, Docker smoke, coverage |
| ARCH-001 V1.6 pipeline ownership | PASS | [run 39827607355](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/actions/runs/39827607355) |
| Stage B branch-aware UAT | NOT RUN by design | [run 39827607428](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/actions/runs/39827607428), manual pilot disabled; not a required main-push gate |

Main's `frontend/scripts/pipeline_sprint07_acceptance.mjs` uses the Global environments button and Organizations sidebar child; `frontend/scripts/operations_acceptance.mjs` selects the authorized customer and checks four failed-phase then five recovered-phase report executions. `scripts/test-quality.sh` still combines, writes JSON/XML and prints coverage without `--fail-under`; `.github/workflows/v15-quality.yml` retains the coverage artifact and mandatory test/security stages. The main quality run measured **82.66%** over 7,455 statements, informational only; its unit stage ran **503 tests, 208 skipped**. The owned PostgreSQL acceptance separately exercises cases outside ordinary unit discovery.

## B. Issue #46 source and contract mapping

| Requirement | Source and exercised contract | Result |
| --- | --- | --- |
| External customer versus internal department | `backend/app/models/entities.py` `Organization`; `backend/app/security/access_models.py` `Department` and `DepartmentMembership`; `/api/v1/organizations`, `/api/v1/access/departments`, `/api/v1/access/customer-grants`; `backend/scripts/access_acceptance_probe.py` | PASS: independent UUID identities; department role does not imply customer grant |
| VM/EC2 single owner | `backend/app/models/entities.py` `VM.organization_id` non-null FK; `backend/app/unified/models.py` `MonitoringResource.organization_id` non-null FK; `backend/app/unified/api.py` resource creation/detail; ARCH-001 and infrastructure acceptance | PASS for controlled fixtures; no shared-VM model introduced |
| Scoped inventory and details | `backend/app/security/scope.py` `configure_request_session` and `scope_reads`; `/api/v1/unified/resources`, `/api/v1/resource-management/data-sources`, `/api/v1/data-pipelines/integrations`; resource CRUD and V1.6 acceptance | PASS: authorized records returned; other-customer IDs/rows denied or absent |
| Draft/save/resume/revision | `/api/v1/resource-drafts` in `backend/scripts/arch001_acceptance_probe.py`; `frontend/scripts/arch001_acceptance.mjs` ten-step VM browser; V1.6 pipeline browser | PASS: server draft persisted/reloaded; stale revision returned 409 |
| Activation boundary | `/api/v1/unified/resources/{id}/verification` and `/activate`; `backend/scripts/arch001_runtime_probe.py` | PASS: unverified VM activation rejected; controlled, verified TLS/Agent evidence allowed VM and ETL activation after parameters and alert setup |
| Direct API RBAC, forged IDs and customer scope | `backend/scripts/access_acceptance_probe.py`, `backend/scripts/deep_tenant_security_probe.py`, `frontend/scripts/resource_crud_acceptance.mjs`, `frontend/scripts/pipeline_v16_acceptance.mjs` | PASS: negative tests execute HTTP requests, not just hidden controls |
| Persistence and migration | Access migration probe, ARCH-001 populated mapping and schema check, release custom-format backup/restore | PASS: identifiers, ownership FKs, password hashes, sessions, execution history and audit references preserved in disposable PostgreSQL |

Representative executed HTTP outcomes: authorized organization/resource, integration and draft creation returned **201**; authorized reads returned **200**. Anonymous integration reads returned **401**. Missing `access.view` and unauthorized integration mutation returned **403**. Cross-customer source/collector/detail lookups returned **404** or an empty scoped list. A forged ETL-to-VM customer association returned **422**. Duplicate source creation and stale draft revision returned **409**. These are the exact assertions exercised by the named harnesses; a 403/404 alternative is recorded only where the contract explicitly accepts either.

## Executed verification

All commands below ran at the exact source SHA on this verification branch. Evidence files are outside the repository under `/tmp/opscontrol-issue46-*`; logs contain synthetic fixture details and are not published.

| Command (from repository root unless noted) | Result |
| --- | --- |
| `ACCESS_EVIDENCE_DIR=/tmp/opscontrol-issue46-access backend/.venv/bin/python scripts/access-acceptance.py` | PASS: 25 migration/provider/department/customer RBAC groups; `/tmp/opscontrol-issue46-access.log` |
| `ACCESS_BROWSER_ACCEPTANCE=1 ACCESS_EVIDENCE_DIR=/tmp/opscontrol-issue46-access-browser backend/.venv/bin/python scripts/access-acceptance.py` | PASS: 25 security groups plus 7 Chromium groups; screenshots and `security.json`, `migration.json`, `browser.json` |
| `ARCH001_API_ACCEPTANCE=1 ARCH001_ENGINE_ACCEPTANCE=1 ARCH001_BROWSER_ACCEPTANCE=1 ARCH001_EVIDENCE_DIR=/tmp/opscontrol-issue46-arch001-complete backend/.venv/bin/python scripts/arch001-acceptance.py` | PASS: populated migration, API/onboarding/scope, incident engine, VM ten-stage browser, draft/resume and invalid activation; `api.json`, `browser.json`, `migration.json` |
| `ARCH001_API_ACCEPTANCE=1 ARCH001_RUNTIME_ACCEPTANCE=1 ARCH001_EVIDENCE_DIR=/tmp/opscontrol-issue46-arch001-runtime backend/.venv/bin/python scripts/arch001-acceptance.py` | PASS: positive evidence-backed activation with disposable TLS/Agent fixture; `runtime.json`, `api.json` |
| `PLAYWRIGHT_MODULE=/workspace/.golden-tools/node_modules/playwright/index.mjs PLAYWRIGHT_CHROMIUM_EXECUTABLE=/usr/bin/chromium INFRA_EVIDENCE_DIR=/tmp/opscontrol-issue46-infra-complete backend/.venv/bin/python scripts/infrastructure-acceptance.py` | PASS: controlled EC2/VM configured, healthy, failed and recovered browser phases, scope negatives; `/tmp/opscontrol-issue46-infra-complete.log` |
| `PLAYWRIGHT_MODULE=/workspace/.golden-tools/node_modules/playwright/index.mjs PLAYWRIGHT_CHROMIUM_EXECUTABLE=/usr/bin/chromium RELEASE_BROWSER_ACCEPTANCE=1 RELEASE_EVIDENCE_DIR=/tmp/opscontrol-issue46-release backend/.venv/bin/python scripts/release-acceptance.py` | PASS: 11 release/restore groups including 205-resource pagination, CRUD, tenant denial, populated backup/restore and schema integrity; `resource-crud.json`, `report.json` |
| `V16_API_ACCEPTANCE=1 V16_BROWSER_ACCEPTANCE=1 V16_SPRINT08_ACCEPTANCE=1 V16_EVIDENCE_DIR=/tmp/opscontrol-issue46-v16 backend/.venv/bin/python scripts/v16-acceptance.py` | PASS: 9 V1.6 HTTP groups, 14 Sprint 08 HTTP groups, 5 Sprint 08 Chromium groups, V1.6 pipeline browser, PostgreSQL ownership/migration; `api.json` |
| `OPERATIONAL_EVIDENCE_DIR=/tmp/opscontrol-issue46-noc backend/.venv/bin/python scripts/operational-acceptance.py` | PASS: configured/failed/recovered browser and customer-scoped reporting, tenant negatives; `browser-*.json`, screenshots |
| `cd backend && .venv/bin/python -m unittest tests.test_access_control tests.test_registry_contracts tests.test_unified_v15_contracts -q` | **43 passed**, 0 failed/skipped |
| `npm test --prefix frontend` | **5 passed**, 0 failed/skipped |
| `npm run lint --prefix frontend`; `npm run build --prefix frontend` | PASS; Vite emitted a non-failing large-chunk advisory |
| `cd backend && .venv/bin/python -m alembic heads` | `0037_access_boundaries (head)`; disposable harnesses executed upgrade/check and supported downgrade checks |

Two initial harness runs failed for incomplete local invocation, then passed without changing code: the first ARCH-001 browser run omitted `ARCH001_ENGINE_ACCEPTANCE=1` and had no incident row for its incident assertion; the first infrastructure browser run omitted the installed `PLAYWRIGHT_MODULE` path and failed import before browser execution. Their logs are `/tmp/opscontrol-issue46-arch001.log` and `/tmp/opscontrol-issue46-infra.log`. Neither establishes a product defect. No behavioral assertion was changed or skipped.

## Decision and remaining boundaries

Issue #46 is **VERIFIED for controlled developer acceptance** on the main source SHA. No confirmed implemented-scope defect or RBAC/customer-ownership redesign is required. These fixture-backed results do not establish independent UAT, genuine AWS/Kubernetes/Windows/Pentaho runtime compatibility, or production readiness. Issue #47 was not started.
