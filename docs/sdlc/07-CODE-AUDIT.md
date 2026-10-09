# DOC-07 — Evidence-Based Current-State Audit (Iteration 1)
**Status:** Static code review completed for key execution paths; runtime tests pending | **Date:** 2026-10-10 | **Branch:** `docs/sdlc-phase-1`

## Audit evidence standard
- **Implemented (code present):** concrete execution path exists, but runtime behavior may remain unverified.
- **Partial:** part of required path exists or UI is disconnected from real data.
- **Broken (static):** source contains a reproducible code-level defect; runtime confirmation still pending.
- **Missing:** required implementation or test suite absent from inspected tree.
- **Unverified:** implementation exists but no successful runtime or behavioral test observed.

This audit reviewed the repository tree; routes in `organizations.py`, `resource_management.py`, `etl.py`, `investigations.py`, `monitoring.py`; model and migration inventories; template resolver; collector runtime; alert/notification modules; frontend navigation and Overview; CI scripts and docs. Full line-by-line verification of every large UI module, schema, migration and README claim remains an open follow-up.

## Feature inventory
| Area | Classification | Evidence | Tracking |
|---|---|---|---|
| Organization CRUD | Implemented (unauthorized) | `api/organizations.py` provides list/get/create/update/disable without identity authorization | #2 |
| Organization isolation | Broken/security gap | Organization filters are optional and user-controlled; ID operations lack authorization checks | #2 |
| Data Source CRUD | Implemented, unverified | `api/resource_management.py`, `api/monitoring.py` provide overlapping CRUD routes | #2 |
| Collector CRUD and scheduling | Partial | Collector routes and scheduler loop exist; worker execution reliability untested | #6 |
| Template editing/version/attachment | Partial | `monitoring.py` routes and `template_resolution.py` persist/merge configuration | #3 |
| Template -> live monitoring | Missing | Attachment path does not create/reconcile collector/metric/log/alert entities | #3 |
| API Basic-auth collector | Broken for HTTPS; HTTP unverified | `collector_runtime.py` calls `opener.open(..., context=...)` on HTTPS | #4 |
| Windows/Linux monitoring | Missing transport | Adapters explicitly return transport-not-installed | #7 |
| Pentaho source collector | Missing transport | Adapter explicitly returns provider implementation pending | #7 |
| Metric sample persistence | Implemented path, unverified | `_persist_metric_samples` creates samples for existing metric definitions | #3 |
| Alert state and notifications | Implemented path, unverified | `alert_engine.py`, `notifications.py` and monitoring API | Pending tests |
| ETL executions and investigations | Implemented routes, unverified | `etl.py`, `investigations.py`; no verified live source adapter | #7 |
| Correlation | Implemented path, unverified | `services/correlation.py`, investigation/ETL endpoints | Pending tests |
| Overview KPI correctness | Broken/static | `Overview.jsx` contains fixed counts and demo VM/incident rows | #5 |
| KPI filtered navigation | Partial/broken | KPI buttons exist; `App.jsx` renders placeholders for VM Health/APIs/Incidents/Reports | #5 |
| Organization create/edit UI | Implemented path, unverified | `ResourceManagementV2.jsx` includes `OrgModal` | Pending UI tests |
| Frontend test/lint | Missing | No test/lint scripts in `frontend/package.json`; no test files in tree | #6 |
| Backend tests | Missing | No test files in repository tree; CI checks imports/mappers/compilation only | #6 |
| Database migrations | Present, unverified | Alembic revisions 0001–0011; 0011 upgrade/downgrade are no-ops | #6 |
| Docker/CI | Partial | Compose and CI workflow exist; deployment/startup unverified | #6 |

## Reproduction plans (not claimed executed)
1. **Tenant boundary (#2):** seed organizations A/B and users with scoped permissions; request unfiltered listings and B IDs as A; assert no B data returned or mutated. Current app lacks a user/role dependency.
2. **Template-to-sample (#3):** create source + committed template with API collector and availability metric; attach template; run scheduler; assert generated collector, definition, run and sample. Current attach function only stores attachment.
3. **HTTPS (#4):** configure API collector to a controlled TLS test server; execute; inspect `CollectorRun.outcome`; verify TLS handling. Static `OpenerDirector.open` signature mismatch identified.
4. **KPI (#5):** seed different counts; verify cards match API results and link to filtered lists, not placeholder pages.
5. **Stub adapters (#7):** configure valid Windows/Linux/Pentaho collectors; execute; inspect expected stub error messages.
6. **Migration/test (#6):** provision PostgreSQL, run `alembic upgrade head`, inspect schema and start API/worker; run pytest/build/lint once scripts are available.

## Validation evidence and blockers
| Check | Observed evidence | Result |
|---|---|---|
| GitHub Actions PR workflow | Run [37982640390](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/actions/runs/37982640390) | SUCCESS |
| Python compileall | CI job includes `python -m compileall -q app migrations` | Passed as part of workflow |
| SQLAlchemy mapper configuration and app import | CI job includes `configure_mappers(); from app.main import app` | Passed as part of workflow |
| Frontend production build | CI job includes `npm run build` | Passed as part of workflow |
| Frontend lint | No lint script configured | NOT RUN |
| Backend pytest | No test suite or CI step found | NOT RUN |
| Alembic upgrade / downgrade | Not present in workflow | NOT RUN |
| PostgreSQL + FastAPI startup | Not present in workflow | NOT RUN |
| Tenant negative tests | No auth test harness | NOT RUN |
| Template-to-sample integration | No fixture/runtime environment available | NOT RUN |
| Live UI screenshot comparison | No browser/staging runtime available; existing SVGs not verified against rendered current UI | NOT RUN |

**Execution environment limitation:** Connected GitHub tools provide repository and Actions access, but no registered Codex execution environment was available; container network could not resolve GitHub. No local test execution is claimed.

## README and screenshot reconciliation
README is approximately 56.9 KB. Seven SVG screenshot assets exist under `docs/screenshots/`, named Overview, ETL Jobs, VM Health, APIs, Incidents, Reports and Resource Management. `App.jsx` implements only Overview, ETL Jobs and Resource Management as real page routes; the other navigation targets render placeholders. Therefore screenshots of VM Health, APIs, Incidents and Reports must be labeled **conceptual/illustrative** until live pages exist. A visual pixel-by-pixel reconciliation remains pending.

## Risks and recommendations
1. **P0 release blocker:** introduce authenticated identity, RBAC and mandatory server-side organization isolation; negative tests are required.
2. **P0 release blocker:** define template activation/reconciliation contract and prove source -> collector -> metric sample.
3. **P1 correctness:** repair HTTPS transport and test TLS verification and authentication.
4. **P1 truthfulness:** replace hard-coded KPI/demo incident/VM data with scoped queries, or visibly label demo data.
5. **P1 readiness:** build test, lint, migration and startup jobs; preserve successful current CI checks.
6. **P1 capability:** do not market Windows/Linux/Pentaho as operational collectors while adapters remain stubs.

## Linked issues
- [#2 Organization isolation](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/issues/2)
- [#3 Template activation](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/issues/3)
- [#4 HTTPS collector](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/issues/4)
- [#5 KPI data and navigation](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/issues/5)
- [#6 Tests and CI](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/issues/6)
- [#7 Stub adapters](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/issues/7)

## Phase 1 gate
**NOT APPROVED** until runtime checks and tenant boundary tests are executed and the SRS is updated for explicit authorization, activation semantics, API transport, truthful UI data and verification gates.
