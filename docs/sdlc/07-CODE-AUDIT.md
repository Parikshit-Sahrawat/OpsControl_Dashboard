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

## Iteration 2 — Expanded source and asset reconciliation (2026-10-10)

### Review coverage
- **Frontend:** inspected both Resource Management modules (active `ResourceManagementV2.jsx`, 291 source lines; inactive `ResourceManagement.jsx`, 571 source lines), `App.jsx`, `TopNav.jsx`, `Overview.jsx`, `ETLJobs.jsx`, `JobDetailsDrawer.jsx`, `api.js`, `resourceApi.js`, package scripts. Note that compressed one-line JSX makes line counts a poor proxy for complexity. A formal per-statement code-review signoff is not claimed.
- **Schemas:** inspected the four schema files (`monitoring.py`, `etl.py`, `investigation.py`, `organization.py`); organization IDs are accepted in client payloads rather than bound to a principal.
- **Migrations:** inspected all eleven Alembic revision files 0001–0011 and `migrations/env.py`. The `down_revision` chain is linear and internally linked; 0011 is intentionally a no-op. **Execution against PostgreSQL remains unverified.** The `env.py` online connection derives its URL from `alembic.ini`, not directly from application `Settings.database_url`; deployment must explicitly reconcile these values.
- **Worker:** inspected collector runtime, adapter registry, alert and notification module entry points, and credentials provider. Only API transport has a real HTTP request path; Linux, Windows and Pentaho are stubs; OTEL is unregistered.
- **Tests:** repository tree contains no `tests/` directory or test files, and frontend has no test/lint scripts. CI is compile/import/build only.

### Additional findings
| ID | Priority | Source evidence | Result |
|---|---|---|---|
| [#8](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/issues/8) | P1 | `ResourceManagementV2.jsx:215` creates `collector_type: "OTEL"`; `collector_runtime.py:208–213` registers only WINDOWS, LINUX, API and PENTAHO | **Broken by design**: onboarding creates unsupported collector. Existing source edits do not update agent collector configuration. |
| [#9](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/issues/9) | P1 | `ResourceManagementV2.jsx:247–255,274–280` fetches organizations/templates globally and counts all; Data Sources only are selection-filtered | **Partial/misleading**: multi-org selection is not a security boundary and totals do not share consistent scope. |
| [#10](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/issues/10) | P2 | All seven screenshot SVGs consist of vector labels/shapes; none contains a captured browser image | **Documentation mismatch**: illustrative assets cannot establish actual UI appearance. |
| [#11](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/issues/11) | P1 | `collector_runtime.py:349–370` uses unleased scheduler claim and `asyncio.create_task`; sample organization copied from metric definition without checking source ownership | **Risk/unverified**: duplicate runs with multiple workers and inconsistent cross-org entity links require database tests. |

### Screenshot-by-screenshot reconciliation (static asset vs active React routes)
| Asset | Asset contents | Current code | Classification |
|---|---|---|---|
| `01-overview.svg` | Vector illustration with KPI counts, ETL table and incident cards | Overview page exists, but hard-coded KPI counts and static incident/VM rows; values/text do not consistently match illustration | **Illustrative, not verified screenshot** |
| `02-etl-jobs.svg` | Illustrated execution statuses and list | ETL Jobs page exists and uses API-backed `jobs`, with client filters and details drawer | **Illustrative; live data/browser unverified** |
| `03-vm-health.svg` | Explicitly labels CPU/memory/disk/services as planned view | `App.jsx` renders generic placeholder | **Planned only** |
| `04-apis.svg` | Explicitly labels endpoint health UI planned | `App.jsx` renders generic placeholder | **Planned only** |
| `05-incidents.svg` | Explicitly labels incident UI planned | `App.jsx` renders generic placeholder; Overview has static incident rows | **Planned only** |
| `06-reports.svg` | Explicitly labels reporting UI planned | `App.jsx` renders generic placeholder | **Planned only** |
| `10-resource-management.svg` | Illustrates organizations, sources, collectors, templates and onboarding | `ResourceManagementV2.jsx` implements these surfaces, but OTEL activation and org-scope issues remain | **Illustrative; browser unverified** |

### Database and tenant test execution record
**NOT EXECUTED.** No registered remote Codex environment was available and direct GitHub access from the local container failed DNS resolution. The connected GitHub integration supports reading/writing source and retrieving Actions results, not arbitrary command execution against a live PostgreSQL instance. It would be inaccurate to claim that migrations, API startup, tenant negative tests, browser screenshots or template-to-sample integration were exercised.

**Required execution environment:** disposable PostgreSQL database, checked-out exact branch commit, Python and Node dependencies, a running FastAPI instance and worker, two seeded tenant fixtures with authenticated identities, controlled HTTP/HTTPS endpoints, and a browser runner. Do not run destructive migration downgrade tests against production or shared data.

**Acceptance commands to execute in a safe environment:**
```bash
cd backend
python -m compileall -q app migrations
python -c 'from sqlalchemy.orm import configure_mappers; from app.main import app; configure_mappers(); print("mapper startup ok")'
alembic upgrade head
alembic current
# Run a future pytest tenant + activation suite once written; none exists today.
cd ../frontend
npm install
npm run build
# npm run lint is currently unavailable: no lint script.
```
**Tenant negative matrix:** list, get, patch, delete data sources/collectors/templates/metrics/logs/ETL and investigation records using org-A caller with org-B IDs; test no filter, one filter, multi-filter and forged organization_id; test inactive org behavior. The current API has no authenticated principal, so true tenant-boundary execution must first define a test identity model and security contract.

**Template-to-sample matrix:** attach committed template; resolve effective config; verify materialized collector and metric definition; run supported adapter; assert collector run and metric sample; repeat attachment to test idempotency; detach and confirm deactivation. Existing attach flow does not materialize the entities.

### Updated approval gate
Phase 1 remains **NOT APPROVED**. Static source and SVG reconciliation expanded; live PostgreSQL, tenant authorization and real browser captures remain blocked by execution environment and missing identity/test harness. No functional code changes have been made.

## Iteration 3 — Staging harness provisioned
A disposable PostgreSQL 17 GitHub Actions integration smoke workflow has been added at `.github/workflows/phase1-staging.yml` with backend migration, startup, OpenAPI, anonymous-access diagnostic, frontend build and evidence artifact steps. **Execution is pending; no runtime success is claimed.** See [DOC-08](08-STAGING-VERIFICATION.md). Authenticated tenant-boundary tests, template-to-sample execution and browser screenshots remain unresolved.

## Iteration 4 — Live integration and browser verification completed (2026-10-10)
Evidence: [successful GitHub Actions run 37987379543](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/actions/runs/37987379543); the `phase1-staging-evidence` ZIP contains JSON evidence, API/Vite logs, and 11 PNG screenshots. All tests ran against an ephemeral PostgreSQL 17 service and synthetic fixtures. **Workflow success measures execution of probes, not release compliance.**

### Runtime results
- **PASS:** Alembic migrations 0001–0011 applied to fresh PostgreSQL 17 after correcting duplicate enum creation in migration 0001 on the review branch (issue #14).
- **PASS:** SQLAlchemy mapper/app import, FastAPI startup/OpenAPI, Vite production build, and browser navigation capture.
- **PASS:** A manually created API Collector generated one SUCCESS CollectorRun and one AVAILABILITY sample valued 1.0.
- **FAIL P0:** Anonymous GET organizations, GET data sources, GET a second organization's source, and PATCH that source all returned HTTP **200**; the synthetic unfiltered source list exposed both artificial organizations. This is confirmed absent authorization, not merely a possible UI isolation bug (#2).
- **FAIL P0:** Template attachment persisted and resolved the effective API collector, but created **0 Collectors and 0 MetricDefinitions**; automatic template activation is unimplemented (#3).
- **BROWSER VERIFIED:** 11 live page screenshots captured, 0 page errors and 0 visible error banners after fixing staging origin configuration. Main navigation: Overview, ETL Jobs and Resource Management render; VM Health, APIs, Incidents and Reports are placeholders. Nested Resource pages show 2 synthetic organizations, 2 Data Sources, 1 manually configured collector and 1 template. Frontend navigation/screenshot evidence does not mean all CRUD flows or monitoring functions were exercised.
- **NOT EXECUTED:** true authenticated org-A vs org-B role negative tests (no authentication model implemented), real Pentaho/Windows/Linux adapter integrations, HTTP TLS verification, UI accessibility/load, migration downgrade, formal pytest/lint suites. These remain in the risk/implementation backlog and are not prerequisites for documenting discovery, but they block product release where applicable.

The original `docs/screenshots/*.svg` files are editorial illustrations, **not** genuine captures. README has been amended to make this distinction. Actual screenshots are stored in the linked CI artifact; [DOC-09](09-PHASE1-HANDOFF.md) gives a per-screen review.

### SDLC gate distinction
**Phase 1 discovery/audit deliverables: complete for draft owner review.** Scope/roles/retention/SLO approval and merge remain pending. **Operational/production release: blocked** by #2, #3, #8, #4 and missing acceptance tests. The project may proceed into **provisional Phase 2 architecture design** with known risks, but must not equate design progress with production readiness.
