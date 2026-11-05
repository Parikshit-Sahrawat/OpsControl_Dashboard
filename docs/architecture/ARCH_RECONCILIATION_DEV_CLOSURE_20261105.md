# Architecture Reconciliation & Development Closure — owner decision delta

Status: implementation-authorized; **not** production approved.
Historical merge baseline: PR #74, `beddc671ecb3e0860cac42139eef314fcb3e016f`.
Reconciliation target: current `main` at branch creation. Newer owner decisions take precedence over conflicting older proposals; retain non-conflicting, verified Pentaho safety requirements.

## Scope and authority

- Journey 20 (Service Catalog & Dependency Mapping): **out of scope**. Do not remove ETL job dependency order, resource monitoring or incident correlation.
- ETL v1.6: owner-approved **Workflow → Job** configuration; every Job belongs to a Workflow; no separately configurable Task entity. Workflow Order expresses job dependencies, not scheduler control.
- Job form: job/native identity, resource and source mapping, **expected duration** and optional long-running threshold. No job-level expected start or expected end input. Workflow-level expected start/end, frequency, expected duration and SLA remain.
- Source evidence: read-only Oracle or Microsoft SQL Server scheduler execution tables, or approved log-file evidence. S3 and SFTP are excluded from new ETL configuration scope. Preserve platform-native Pentaho identity/evidence where relevant.
- Scheduler database lifecycle: insert a row at start with `RUNNING`, update **same row** on completion to `SUCCESS` or `FAILED`. Native run ID includes a date stamp; uniqueness scope, row key, end-time RUNNING semantics, duration units, timestamp types, retention and update visibility require source certification.
- Read-only discovery and active-run reconciliation: bounded overlapping discovery; query active RUNNING records by stable identity; append/version evidence; persist checkpoints only after approved durable acceptance. No dirty reads or `NOLOCK`. Do not infer completed status from a RUNNING end-time placeholder.
- ETL v1.7: separate **Event Rules** (evidence-derived operational facts) from **Alert Rules** (severity, deduplication, routing, escalation, suppression, recovery). Inheritance: Monitoring Template → Workflow → Job with controlled overrides. Keep historical failures and SLA breaches, separate stale/unknown evidence from execution outcome.
- Notifications: Email, PagerDuty, ServiceNow subject to authorization and idempotency. OpsControl is monitoring-only: no scheduler dispatch, rerun, stop or write privileges.

## Implementation reconciliation — initial file-level inventory (not acceptance)

The following paths exist on the inspected repository default branch and need functional/test review:

| Area | Initial implementation anchor | Closure evidence required |
| --- | --- | --- |
| ETL entities | `backend/app/models/entities.py` (`JobOrder`) | workflow/job identity and compatibility mapping |
| ETL API | `backend/app/api/etl.py` | tenant isolation, execution identity, source lifecycle |
| Pipeline integration | `backend/app/data_pipelines/models.py` | approved source types, mappings and activation |
| Settings | `frontend/src/monitoringSettings.js`; `verification/dev05/settings.mjs` | authenticated persistence/reload regression |
| Alert engine | `backend/app/worker/alert_engine.py`; `backend/app/telemetry/rules.py` | event/alert separation, recovery, replay-safe dedup |
| Architecture | `README.md`; `docs/architecture/ARCH_001.md` | superseded decisions identified; retained safety contracts |

Presence of a path is **not** proof of completed functionality.

## Closure sequence and gates

1. Build requirement-to-code-to-test-to-owner-acceptance matrix; classify Implemented / Partial / Missing / Unverified / Out of Scope.
2. Reconcile source configuration, Workflow → Job model, dependencies, event/alert rules and settings without breaking existing integrations.
3. Implement scoped gaps with tests and migration safety, in separate reviewable PRs.
4. Obtain individual owner acceptance for nine verified requirements; resolve remaining requirement-authority decisions.
5. Re-run authenticated UAT, genuine Pentaho/provider validation, telemetry durability and security certification.

**Release gates unchanged:** CHK-001 FAIL, CHK-002 BLOCKED, security BLOCKED, genuine-provider certification BLOCKED, authenticated UAT outstanding; **production NO-GO**. No design approval or passing unit test substitutes for those gates.

## Open evidence requests

Sanitized Oracle/MSSQL schema and three sample rows (RUNNING/SUCCESS/FAILED); stable source row key and publication delay; timestamp/duration semantics; retention; latest nine-requirement owner acceptance records; genuine provider evidence; current SBOM/Grype and CHK-001/CHK-002 certification results.
