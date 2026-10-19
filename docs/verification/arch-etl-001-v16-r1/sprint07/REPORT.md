# ARCH-ETL-001 V1.6-R1 — Sprint 07

Date: 2026-10-17 UTC. Development branch: `feat/arch-etl-001-v16-r1`.
Implementation baseline: `72af4bad25b1433868905ee39c81b341b0be0845`, confirmed against the remote development branch before editing. The resumed executor initially contained an older `work` checkout; the clean checkout was switched and fast-forwarded to the verified development head. Uncommitted Sprint 07 files were not retained by that executor replacement and were reconstructed from the recorded implementation/contracts. Sprint 01–06 commits and verification evidence are preserved.

The controlling `docs/architecture/ARCH_ETL_001_V16.md` is unchanged. No production backend, migration, permission resolver, provider adapter or dependency manifest dependencies were redesigned. No PR, merge, deployment, real source activation or Pentaho workload was performed.

## Implemented routes and components

The existing **Data Pipeline Monitoring** navigation opens a compact operational workspace. Hash routes support reload and direct navigation within the current authenticated shell:

| Route | Implementation | Operational behavior |
| --- | --- | --- |
| `#/pipelines/inventory` | `PipelineWorkspace.jsx` | Server search/pagination; native workload type, customer/environment, collector/method, actual source health, monitoring readiness, observation, latest execution, completeness and exact-build capability evidence. Pipeline drawer links to operational sections. |
| `#/pipelines/executions` | `ExecutionViews.jsx` | Canonical logical executions and attempt counts; separate lifecycle/outcome, retry/type, completeness, review and incident references. Overview, Attempts, Evidence, observed Steps, Incidents and Audit drawer sections. |
| `#/pipelines/schedules` | `ScheduleView.jsx` | Persisted schedule occurrences; native scheduler versus monitoring expectation, calendar/timezone/DST/grace, observed execution, compliance, coverage and evaluation evidence. |
| `#/pipelines/evidence` | `ReviewView.jsx` | Resource-scoped queue within the selected customer; all six review categories, prior defensible projection, native claim/provenance, timestamps, revision and decision history. |
| `#/pipelines/recovery` | `RecoveryView.jsx` | Original failure, scheduler retry and distinct manual recovery remain separate; evidence-backed proposal, independent confirmation and reversal with decision audit. |
| `#/pipelines/incidents` | `IncidentView.jsx` | Customer/environment-scoped native incident list; seven-state lifecycle, failure/common-root evidence, historical reassessment, assignment, recovery/dependency/schedule/observation evidence and audit. |

`usePipelineFeed.js` reuses the existing authenticated `controlPlane.js` client. It provides abort plus generation guards, immediate path-key isolation, 30-second refresh, explicit loading/empty/error/forbidden/stale states and background inventory enrichment with at most three workers. Customer/environment/authorization changes remount the workspace and clear sensitive selections and drawers. A 503 leaves prior evidence visibly stale; 401/403 discard prior results. Consequential forms disable while their data is loading or stale and require explicit confirmation.

`contracts.js` contains display/request helpers, UTC formatting and existing action/state values; it grants no permissions. `ui.jsx` reuses the existing status component and dialog focus trap, adds readable evidence fields, compact tables, pagination and guarded forms. Native success is never derived from HTTP success, process exit or scheduler status. `WAITING_FOR_RETRY` is nonterminal; `SUCCESS_AFTER_RETRY` stays distinct. Steps appear only when actual step observations exist.

The collapsible sidebar and existing responsive shell remain. Tables contain their own horizontal scroll regions, readable headers and focusable keyboard scrolling; long identifiers truncate with accessible full values. Header refresh is outside filter forms. No oversized summary cards were introduced. Resource Management exposes the authorized **Organizations** list; employee **Departments** remain under Access Management using the unchanged resolver and employee relationships.

## Exact API contracts consumed

All paths are existing authenticated backend contracts inspected in source and generated OpenAPI before mapping. No endpoint was invented.

| Method and path | Request/response usage |
| --- | --- |
| `GET /api/v1/auth/customer-scope`, `/auth/me` | Existing authenticated customer selection/session/effective access. Explicit selected IDs never imply an ALL grant. |
| `GET /api/v1/unified/resources` | `domain=ETL`, repeated `organization_id`, optional `environment`, server `search`, `limit=20`, `offset`. Response `items,total,has_more`; native `configuration` and inherited customer binding are preserved. |
| `GET /api/v1/unified/resources/{id}` | Current scoped resource, native configuration, conditions/dependencies and parameter bindings. |
| `GET /api/v1/unified/domain-state/ETL` | Explicit customer/environment/resource ID and `limit=1`; `source_verification`, `latest_execution` and current native monitoring state. |
| `GET /api/v1/data-pipelines/integrations/{id}` | Bound jobs/associations/methods/sources, connection monitoring context and capability evidence. Only a resource's bound methods contribute to its inventory capability/type display. |
| `GET /api/v1/unified/resources/{id}/executions` | Server `limit=20,offset`; response `items,total`, canonical `pentaho_*` fields, execution type, actual steps and legacy incident reference where exposed. Outcome filtering is explicitly limited to the current page because this API has no outcome query. |
| `GET /api/v1/unified/resources/{id}/executions/{history_id}/attempts` | `limit,offset`; response canonical `execution,total,items`; native identity, retry authority, outcome, completeness, aliases and immutable revisions. Count requests use `limit=1`. |
| `GET /api/v1/etl/executions/{id}` | Existing non-Pentaho execution detail; no Pentaho authority is assigned to legacy status or evidence. |
| `GET /api/v1/unified/resources/{id}/schedule-windows` | `limit=500`; array response, no offset. Authority is read from `pentaho_authority.selection.mode`, calendar/grace from the persisted snapshot; compliance and `evidence.coverage` come from the evaluator. |
| `GET /api/v1/unified/resources/{id}/evidence-reviews` | Server `status,category,limit,offset`; response `items,total`. Categories: `AMBIGUOUS_IDENTITY`, `NATIVE_ALIAS_CONFLICT`, `RETRY_RELATIONSHIP`, `EXECUTION_OUTCOME`, `LEGACY_ADOPTION`, `RECOVERY_IDENTITY`. |
| `GET /api/v1/unified/resources/{id}/evidence-reviews/{review_id}` | `limit,offset`; response `review,decisions,total`. Context includes identity, verification, prior projection, evidence/revision references and occurrence/observation/receipt timestamps. |
| `POST /api/v1/unified/resources/{id}/evidence-reviews/{review_id}/decision` | Exactly `action,expected_revision,idempotency_key,reason`. Allowed actions: `DEFER`, `REJECT_CLAIM`, verified outcome-category `ACCEPT_VERIFIED_CLAIM`, legacy-category `ADOPT_LEGACY`. The backend anchors evidence to the review's candidate `event_id`; this schema **does not accept** an arbitrary evidence-reference field. The candidate and raw reference are displayed before confirmation. |
| `GET /api/v1/unified/resources/{id}/executions/{history_id}/recovery-links` | Server `limit,offset`; response `items,total`, proposer, status, revision and decision audit. |
| `POST /api/v1/unified/resources/{id}/executions/{history_id}/recovery-links` | Exactly `recovery_history_id,evidence_ids,reason,idempotency_key`; 2–25 accepted event references covering both executions. Proposal schema has no expected-revision field. |
| `POST /api/v1/unified/resources/{id}/executions/{history_id}/recovery-links/{link_id}/decision` | `action=CONFIRM|REVERSE,expected_revision,reason,idempotency_key`. Self-confirmation unavailable; server independently checks actor, scope, revision and native evidence. |
| `GET /api/v1/native-incidents` | Repeated `organization_id`, optional `environment,status`, `limit=20,offset`; `items,total`, owner/revision and existing lifecycle. |
| `GET /api/v1/native-incidents/{incident_id}` | Native detail, activities, execution failures and current server recovery proof (`ready,result,reasons,evidence`). |
| `GET /api/v1/native-incidents/{incident_id}/execution-failures` and `/recovery-assessments` | Server `limit,offset`, response `items,total`; exact history/resource/evidence association and independent assessment history. |
| `POST /api/v1/native-incidents/{incident_id}/recovery-assessments` | `revision,idempotency_key,observation_seconds` (60–86400); records the backend result, including pending or failed checks. No client `ready` field. |
| `POST /api/v1/native-incidents/{incident_id}/recovery-validation` | `revision`; offered in MONITORING, enabled only when current backend recovery proof is ready. |
| `POST /api/v1/native-incidents/{incident_id}/transition` | `revision,status,note`; only existing permitted transitions, with resolution/closure gated by backend proof. Reopening is an explicit confirmed action; historical evidence never triggers it in the UI. |
| `POST /api/v1/native-incidents/{incident_id}/notes`, `/assignment`, `/escalate` | Existing `text`; `revision,assigned_user_id`; `revision,note` schemas respectively. Employee owner ID is validated by the backend. |

## Permission mapping and consistency

| Effective permission | Frontend usage |
| --- | --- |
| `etl.view` | Data Pipeline navigation and relevant operational reads, intersected with explicit selected customer IDs. |
| `resources.view` | Also required by the existing unified resource catalog/detail authorization. Missing catalog access has an explicit message; no implicit grant is added to make discovery succeed. |
| `etl.investigate` | Recovery-link proposal, independent confirmation and reversal for the current customer. |
| `etl.resolve_identity` | Evidence adjudication with category/evidence-approved actions. |
| `incidents.view` | Native incident lists and execution-to-incident evidence; customers without this grant are excluded. |
| `incidents.manage` | Existing investigation, assignment, escalation, assessment, validation and lifecycle mutations. |
| `incidents.acknowledge` | Existing acknowledge transition only. |
| Existing resource/access/configuration grants | Existing Resource Management and Access Management controls; unchanged backend authorization and direct/department-inherited resolver. No configuration/replay or workload controls were added. |

409 conflicts preserve the error and block resubmission until an explicit refresh. Stable request idempotency keys are retained for transport retries and reset after successful saves. Review decisions cannot assign arbitrary native outcomes. Separate recovery success never mutates the original failed execution and never establishes downstream or incident restoration.

## Validation

Final relevant regression result: **PASS**.

| Check | Actual final result | Evidence |
| --- | --- | --- |
| Existing permission tests + pipeline module | Both test files passed; pipeline helper cases also executed individually: 13/13 | `frontend-unit.txt`, `pipeline-unit.txt` |
| Frontend lint | PASS | `lint.txt` |
| Production Vite build | PASS; 77 modules, JS 495.75 kB / gzip 139.69 kB | `build.txt` |
| Backend OpenAPI/incident contracts | 10/10 PASS | `ownership.txt` |
| Existing authenticated API workflow | 9 groups PASS | `api.json` |
| Sprint 03/04/05/06 HTTP probes | 4 + 5 + 4 + 5 groups PASS; 27 total with existing workflow | `pentaho-http.json`, `pentaho-review-http.json`, `pentaho-history-http.json`, `pentaho-incident-http.json` |
| Existing configuration browser acceptance | PASS: eight steps, resume, independent methods, source association, activation denial, customer isolation and mobile | `browser.json`, `pipeline-v16-*.png` |
| Sprint 07 actual Chromium acceptance | 16 groups PASS; actual authenticated API and owned database | `sprint07-browser.json`, `sprint07-*.png` |
| Additive migration/schema/owned database cleanup | PASS, head `0036_native_recovery`, no drift, populated downgrade refused | `report.json`, migration preservation JSONs, `gate.txt` |

The first combined gate found an existing browser test's single-customer fixture assumption: Sprint 03 explicitly adds a second authorized membership to its viewer. The test now verifies the authenticated customer scope and an explicit single-customer query independently, retaining foreign-customer and mutation denials. The combined gate was rerun and passed. Earlier focused runs also corrected test refresh synchronization and made the actual `resources.view` discovery requirement explicit; these are not represented as initial passes.

The focused pre-gate run passed 13 pipeline unit cases, existing permission tests, ten backend contract tests, lint, production build, nine existing authenticated HTTP groups and 15 real Chromium operational check groups. The final gate also passed the existing Data Pipelines configuration browser acceptance, Sprint 03–06 authenticated HTTP probes and a catalog-restricted reader check.

Reproducible final commands:

```sh
cd frontend
npm test
node scripts/pipelines.test.mjs
npm run lint
npm run build
cd ..
V16_TEST_TARGETS=tests.test_sprint07_frontend_contracts,tests.test_pentaho_incident_contracts \
V16_PENTAHO_R1_ACCEPTANCE=1 V16_PENTAHO_REVIEW_ACCEPTANCE=1 \
V16_PENTAHO_HISTORY_ACCEPTANCE=1 V16_PENTAHO_INCIDENT_ACCEPTANCE=1 \
V16_API_ACCEPTANCE=1 V16_BROWSER_ACCEPTANCE=1 V16_SPRINT07_ACCEPTANCE=1 \
V16_EVIDENCE_DIR=/tmp/sprint07-final python -u scripts/v16-acceptance.py
```

The harness creates its own PostgreSQL container and controlled backend fixtures, runs additive migration/schema checks, starts the actual authenticated API and production frontend preview, drives Chromium, and cleans up its owned container/processes. No configured demo or production database is used. Secrets/tokens and private fixture files are excluded from evidence.

| Required acceptance behavior | Executed coverage |
| --- | --- |
| Six pages with authenticated fixtures | Real Chromium route/table/drawer workflows and six page screenshots. |
| Navigation/customer selection | Real selector switches, six hash links, independent customer/resource administration, collapsible sidebar. |
| Stale customer response isolation | A real prior-customer response is delayed across a selector change; old records never return to the UI. |
| Pagination/filters/drawers | Actual inventory page 1/2, server search, execution outcome filter and pipeline/execution/review/schedule/incident drawers. |
| Retry distinctions | Real canonical WAITING_FOR_RETRY and SUCCESS_AFTER_RETRY rows and two-attempt detail; deterministic outcome contract tests. |
| Original failure preserved | Proposal, second-investigator confirmation and reversal through actual API; original remains FAILED. |
| Conflict/incomplete evidence | Conflicted execution, unknown process-exit-only outcome and previous defensible projection remain visible. |
| Review permissions/stale revision | Actual competing DEFER advances revision; stale UI decision receives 409, refresh required; read-only actor gets 403. |
| Recovery flows | Real accepted references, explicit confirmations, hidden self-confirmation, independent reviewer, reverse audit. |
| Incident recovery rules | Real assessment returns non-restoration proof; validation/closure are not inferred from a recovery execution. |
| Native versus expected schedule | Both persisted evaluator authority snapshots rendered distinctly. |
| UNKNOWN/INCOMPLETE versus NO_RUN | Unit authority/unknown contracts and evaluated INCOMPLETE coverage; no frontend absence inference. Prior schedule HTTP checks also exercise actual evaluator rules. |
| Unauthorized controls | Read-only adjudication/recovery controls absent; actual unauthorized POST denied; catalog grant handled explicitly. |
| Responsive/keyboard | Actual 768px/390px pages have no horizontal document overflow; table keyboard scrolling; modal focus containment and Escape. |
| Non-Pentaho compatibility | Existing bridge-created Airflow resources retain DAG classification; NiFi/ADF/SSIS resources also present in controlled inventory; existing configuration browser remains in final regression. |
| Access/Resource navigation | Customer Organizations and employee Departments remain separate and reachable. |

Normal monitoring data comes from the actual API and owned database. Only the failure-state test injects a 503 transport response, and the customer race test delays an actual response; neither injects successful operational monitoring data.

### Captured screenshots

| Page | Screenshot |
| --- | --- |
| Pipeline Inventory | [Inventory](sprint07-inventory.png) |
| Execution History | [Executions](sprint07-executions.png) |
| Schedule Monitoring | [Schedules](sprint07-schedules.png) |
| Evidence Review | [Review queue](sprint07-evidence.png) |
| Recovery Tracking | [Recovery proposal](sprint07-recovery.png), [Independent reversal](sprint07-recovery-reversed.png) |
| Incident Correlation | [Incidents](sprint07-incidents.png) |

Key drawers: [Pipeline](sprint07-pipeline-drawer.png), [Execution attempts](sprint07-execution-attempts.png), [Schedule evidence](sprint07-schedule-drawer.png), [Review provenance](sprint07-review-drawer.png), [Incident recovery](sprint07-incident-recovery.png).
Responsive captures: [390px](sprint07-inventory-390.png), [768px](sprint07-inventory-768.png). Existing configuration captures: [Wizard](pipeline-v16-wizard.png), [Methods](pipeline-v16-methods.png), [Read-only operator](pipeline-v16-viewer.png), [Mobile](pipeline-v16-mobile.png).

See `changed-files.txt` for the exact delivery inventory. `source-sha256.json` records implementation/test/status-document hashes. Saved logs, JSON acceptance results and screenshots are local acceptance evidence, not provider certification. Genuine Pentaho **RT-001–RT-020 remain NOT RUN**.

## Backend compatibility, limitations and Sprint 08 dependencies

The completed backend contracts are consumed without production backend changes. Unsupported query parameters, global review APIs, outcome overrides, workload controls and scheduler endpoints are not introduced. `resources.view` is an additional real catalog-read requirement; an operator with only `etl.view` needs an existing resource read grant to discover/select pipelines. Incident reads still follow their own grants.

Queues and execution/schedule views select a resource within the authorized customer scope because the backend exposes resource-scoped APIs. Execution outcome filtering covers only the displayed server page. Schedule history is the latest 500 occurrences with no server offset. Attempt detail exposes up to 100 revisions and 200 aliases per attempt. Integration detail is bounded by the existing 500-item contract. Incident activities are the latest 200; failure/assessment records paginate. The incident API has no execution/resource filter, so the scoped incident list and exact failure associations are labeled explicitly. A legacy incident reference is shown when present; otherwise the execution drawer provides scoped, verifiable associations. Missing data is shown as unreported, never inferred.

The interface renders the current server recovery assessment. Continuous observation still requires the existing repeated fresh backend assessments; no autonomous scheduler or new recovery worker is implied. Existing direct-dependency validation and non-Pentaho proof limits remain. Resource Management Organizations is an authorized read list; existing resource-onboarding organization creation and other administrative workflows are preserved.

Sprint 08 can consume these reviewed UI/API workflows. Remaining dependencies are separately authorized genuine installed-build RT-001–RT-020 and platform/capability evidence, native failure-cause/schedule producers, real dependency/observation proof, large-fleet/load/failover and longer-duration acceptance, live notification delivery, and any approved server-side cross-resource queue/filter expansion. This delivery does not certify production or native runtime readiness.
