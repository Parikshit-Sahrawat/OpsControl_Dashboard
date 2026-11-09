# ETL v1.6 / v1.7 source reconciliation (read-only audit of main, 2026-11-05)

This matrix describes inspected source, not acceptance. Latest main includes merged PR #78 Stage 2A evidence. Journey 20 remains excluded. Production remains NO-GO.

| ID | Approved contract | Source inspected | Finding | Status |
|---|---|---|---|---|
| ETL-01 | Workflow → Job hierarchy | backend/app/models/entities.py (JobOrder); backend/app/api/etl.py | JobOrder has organization/VM identity but no required workflow parent in inspected model/API | GAP |
| ETL-02 | Workflow owns expected start/end, frequency and SLA | entities.py JobOrder; schemas/etl.py JobOrderCreate | JobOrder still owns schedule, SLA and expected windows | MISMATCH |
| ETL-03 | Job form owns expected duration, optional long-running threshold only | schemas/etl.py JobOrderCreate | Creation schema requires SLA and permits expected window start/end | MISMATCH |
| ETL-04 | Workflow Order dependencies | entities.py, api/etl.py | No approved first-class workflow dependency API established in inspected paths | GAP |
| ETL-05 | Native execution identity and attempts | entities.py JobOrderHistory; api/etl.py | Provider execution identity and history exist; full native row-key and retry semantics require proof | PARTIAL |
| ETL-06 | Oracle/MSSQL/log evidence | data_pipelines/service.py | DATABASE and FILE_LOG methods exist; inspected validation references MSSQL/SQL Server, Oracle not certified | PARTIAL |
| ETL-07 | RUNNING same-row update to SUCCESS/FAILED | data_pipelines/models.py; service.py | Source/checkpoint models exist; active-row polling, overlap, retention and durable checkpoint contract not certified | UNVERIFIED |
| ETL-08 | Job long-running event based on actual elapsed | entities.py; api/etl.py | Expected runtime/long-running representation exists; source-freshness correctness not verified | PARTIAL |
| ETL-09 | Separate ETL Event Rules from Alert Rules | worker/alert_engine.py | Existing metric threshold rules directly evaluate alerts; approved ETL event layer not established | GAP |
| ETL-10 | Template → Workflow → Job policy inheritance | worker/alert_engine.py; entities.py | ETL-specific effective policy inheritance not established | GAP |
| ETL-11 | Workflow and job event catalog | api/etl.py; worker/alert_engine.py | Existing execution status vocabulary does not establish v1.7 event catalog | PARTIAL |
| ETL-12 | Normal/Pending/Firing/Recovered, stale orthogonal | worker/alert_engine.py | Existing metric states OPEN/RESOLVED; ETL lifecycle semantics require separate verification | PARTIAL |
| ETL-13 | Email/PagerDuty/ServiceNow routed idempotently | worker/alert_engine.py | Existing metric notification outbox exists; ETL routing/correlation not verified | UNVERIFIED |
| ETL-14 | Durable replay and acceptance | Stage 2A SECURITY_RELIABILITY_GATES.md | CHK-001 FAIL; CHK-002 BLOCKED; no release qualification | BLOCKED |
| ETL-15 | Workflow/Job configuration UI | frontend/src/pages/ETLJobs.jsx | Execution investigation UI exists, but approved Workflow/Job editor not established | GAP |
| ETL-16 | Tenant isolation/monitoring-only | api/etl.py; data_pipelines/models.py | Organization scoping exists; complete authorization/negative-case review pending | UNVERIFIED |

## Bounded implementation increment

- `frontend/src/pages/ETLJobs.jsx`: Clear filters now restores `environment = "All"` rather than silently restricting to PROD.
- `frontend/scripts/etl_filters.test.mjs`: regression guards for all four filter defaults and the all-environment filter.
- `frontend/package.json`: includes new test in `npm test`.

This is an approved defect fix, **not** implementation of ETL-01 through ETL-16. Full workflow migration requires backward-compatible data design, stable native scheduler source schema and migration tests.

## Test and evidence honesty

The GitHub connector confirms changed file content and branch comparison. Full local frontend/backend test execution was not available through the connector; GitHub Actions runs for the latest commit were queued/pending at inspection time. Do not claim PASS before logs and outcomes are checked.

## Required next steps

1. Produce backward-compatible Workflow → Job schema/API design and migration plan; inspect all consumers of `JobOrder`.
2. Implement the approved workflow-first foundation with focused backend, frontend and migration tests.
3. Add source-specific Oracle/MSSQL RUNNING→terminal polling and idempotent evidence contract, using sanitized schema and genuine fixtures.
4. Implement v1.7 event/alert separation, inheritance, deduplication, recovery and routes.
5. Obtain owner acceptance; independently certify UAT, CHK-001/002, security and genuine provider.

No scheduler write permissions, release gate changes, production deployment or collector upgrades authorized by this file.
