# ARCH-001 implementation assessment and migration design

Baseline: main `fc63455121a9a6fbb98f060622a6b816e097bff5`; V1.5 implementation target `main` (owner-authorized local development).

## Assessment and gaps

| Domain | Existing implementation | Required correction |
|---|---|---|
| Identity/access | Normalized customer organizations; independent provider departments, employees and scoped RBAC | Keep customer ownership; remove the grant UI while preserving backend customer-scope enforcement |
| Resources | VM/JobOrder/DataSource identities plus independently configured Collectors | Unified resource bindings; inline customer onboarding; VM-owned collection configuration; SaaS ETL without a VM |
| Telemetry | Actual authenticated OTLP logs/metrics/traces; pinned Contrib; real HTTPS probing; Carte snapshots | Durable normalized log/API execution events, platform mappings and service evidence |
| ETL | Carte execution history, steps, daily schedule observation and investigation | Log reconstruction, retry/parallel-step identity, terminal status independent of conditions, persisted timezone-aware expected windows |
| Parameters | Versioned monitoring packages, activation and sustained metric evaluation | Exactly ETL/VM/API parameter editors with identity inheritance, explicit override provenance and effective preview |
| Correlation | Time-window evidence attached to ETL executions | Explicit dependency graph and cross-domain evidence groups; proximity alone must not establish cause |
| Incidents | Historic native tables retained; active native/ITSM behavior retired by PR #32 | V1.5 supersedes the earlier removal decision: native incident lifecycle, recovery and evidence restored; external ITSM remains outside scope |
| Reports/UI | Data-backed operational views, dual themes and compact tables | Approved navigation, unified onboarding, domain reports, environment filtering and filtered KPI drill-downs |

## Affected modules

New modular code belongs under `backend/app/unified/`. Integration points are `app/main.py`, `models/entities.py`, `security/scope.py`, `security/access_control.py`, migration registration, OTLP ingestion, existing collector worker scheduling, ETL serialization and existing alert evaluation. Frontend integration uses `App.jsx`, navigation/permissions, Resource Management, Overview, Reports, access sections and CollectorControl. Existing telemetry/worker/provider adapters, identity/password/session tables and historical migrations remain authoritative.

## Data model and mapping

An additive resource binding identifies the domain and references existing VM, JobOrder and/or DataSource records. It never introduces a second customer identity table. New VM/API profiles own their existing DataSource; an ETL profile references its JobOrder and optionally an associated VM. VM relationships determine inherited customer, environment and Collector; parameter overrides cannot change customer ownership.

Versioned parameter documents, dependency history, normalized telemetry events, expected execution windows and resource conditions add durable engine state. Cross-domain correlation groups contain explicit relationship/evidence references. Existing histories and steps are extended rather than replaced; VM-less SaaS JobOrders become possible by making the VM FK nullable. Existing multiple step attempts/legacy statuses survive.

Migration backfill uses existing primary keys and explicit relationships. VM-to-DataSource inference is accepted only when customer, hostname and environment identify exactly one compatible host. Ambiguous mappings are retained as scoped reconciliation issues, not guessed or deleted. Existing API DataSources and JobOrders remain in place. No old migration is edited.

## Production impact and rollback

No production environment/database has been identified. Development changes and disposable PostgreSQL validation are authorized. Applying to production requires the owner's specified environment identification, verified restoration, migration-specific backup, affected-record inventory, preflight/postflight counts/FKs and transactional migration plan. Unmapped records block destructive operations. No destructive production operation is planned.

A populated additive schema is retained for application rollback. Downgrade is allowed only when new data is absent and no VM-less job exists; otherwise it must refuse. Restore procedures must target an explicitly identified database and a tested backup, never an assumed local/staging database.

## Implementation phases

1. Assessment, contradiction resolution and lossless migration mapping.
2. Resource relationships, safe onboarding APIs and parameter schemas/versioning.
3. Durable event normalization/reconstruction and calendar schedule evaluation.
4. VM service/syslog telemetry, secure API probes and dependency-based correlation.
5. Resource/event navigation, inheritance UI, operational overview and domain reports.
6. Alert/correlation recovery and domain reporting; native incident lifecycle and recovery validation; no external ITSM.
7. Disposable PostgreSQL migrations, security/integration/worker tests, actual OTel evidence, browser/build/Docker validation and documentation/direct-main delivery.

Each phase is committed after its relevant checks pass. Completion is evidence-based; unsupported/genuine provider and target-host acceptance remain explicitly recorded.

## Risks and dependencies

Legacy JobOrder serializers assume a non-null VM; coordinated API/schema/UI changes are required before SaaS ETL is exposed. Schedules require an IANA timezone, deterministic DST policy and durable catch-up. Execution events without an unambiguous execution key must remain unresolved instead of combining concurrent runs. Collector outages must produce telemetry uncertainty rather than invented ETL failure. Production service monitoring requires service-identity permissions on the actual target. Genuine IICS/Windows/cloud acceptance needs approved endpoints/credentials/hosts; controlled fixtures do not certify those providers.

## Phase evidence

Foundation validation uses `scripts/arch001-acceptance.py`: owned PostgreSQL 17, old-schema fixtures, additive upgrade, full Alembic comparison, immutable-history/identity checks, tenant constraints and an actual FastAPI process. Resource/parameter API tests verify inline customer creation, Windows/Linux onboarding, VM-less IICS, inherited ETL paths, safe YAML/JSON imports, immutable versions, scoped denials and refused activation without telemetry. `backend/tests/test_unified_monitoring.py` verifies safe schemas and timezone/DST calendar boundaries. The foundation suite passed 57 backend tests; the completed native adapter regression suite passes 59 backend tests.

Pinned Contrib 0.123.0 validates the new loopback syslog receiver and log pipeline. Remote syslog requires TCP with mutual TLS; unprotected public UDP listeners are rejected. Native outbound API/IICS collectors require platform approval plus deployment-owned host, CIDR and port allowlists. HTTP requires a separate explicit deployment flag and cannot carry authentication. HTTPS always verifies TLS and pins an allowed DNS answer; no redirects are followed.

Agent configuration revisions now retain configured service identities. Read-only systemd/Windows SCM observations use fixed commands with validated argument lists and no shell. Failed queries produce unavailable/error evidence, not healthy values. Target OS service execution is a separate acceptance gate.

Subsequent phases passed actual PostgreSQL reconstruction/retry/parallel/out-of-order cases, durable schedule restart/outage handling, alert deduplication/recovery, dependency correlation, actual Agent 1.1.0 + Contrib 0.123.0 logs/metrics/traces over verified TLS, native HTTPS failure/recovery and authenticated controlled IICS-style metadata. The existing managed telemetry regression passed source-read errors, approved rollback and independent notification delivery. Actual Playwright produced five resource/parameter/report/mobile screenshots. Access acceptance passed 25 security check groups across 68 tables with zero schema/model differences. The isolated four-service Docker build/bootstrap/worker/restart/session suite passed. See [operations and acceptance boundaries](../ARCH_001_OPERATIONS.md) and checked-in evidence. Genuine provider/Windows/systemd and production acceptance remain separate; older browser suites targeting removed tabs are not certified against this navigation.

## V1.5 extensions

Migrations 0028–0031 add the immutable Attribute/Capability Registry, actor-owned
onboarding drafts, transactionally persisted provider checkpoints, Agent revision
and credential lifecycle fields, native incident detail/alert associations, and durable per-user notification inbox/preferences.
Retired role-permission links are preserved inactive; new incident permission
definitions do not grant existing employees privileges. Role editing preserves
revocations instead of deleting historical links.

The three domains use official UI terms Compute Instances, Data Pipelines and API
Endpoints. Five collection methods share one compiler and server schema registry.
Nine platform adapters preserve source evidence and platform semantics. Native
incidents reuse retained history; database ownership remains customer-scoped.
The local stack adds a TLS ingestion gateway; its generated CA is development-only.
Current verification and unresolved gates are recorded in
[ARCH-001_IMPLEMENTATION_STATUS.md](../../ARCH-001_IMPLEMENTATION_STATUS.md).

## ARCH-ETL-001 V1.6-R1 shared architecture reconciliation

The [owner-approved Pentaho specification](ARCH_ETL_001_V16.md) is immutable and
controls Pentaho-specific behavior. [Revision-1 reconciliation](ARCH_ETL_001_V16_R1_RECONCILIATION.md)
maps all twelve REC items to its clauses and existing implementation owners.
Reuse MonitoringResource/JobOrder and the current reducer, durable evidence and
fenced cursors, native incidents/outbox and customer-scoped RBAC. Concrete
attempt/revision/outbox gaps are documented before any additive migration;
no second canonical engine or destructive schema change is approved here.

Sprint 01 adds only static, versioned Pentaho monitoring-surface declarations to
existing metadata APIs, preserving current collection/configuration/activation
behavior and the eight other platforms. Runtime reconstruction, recovery,
retention, incident and permission changes belong to later tested slices.
New employees require one department; existing legacy multiple memberships and
direct-role access remain intact. Correlation remains evidence-supported
confidence, never an assertion of proven cause. All genuine runtime certification
remains independent of architecture approval, unit tests and connectivity.

## R1 Sprint 03 — canonical executions and observed recovery

Pentaho-specific behavior is controlled by the immutable
[ARCH-ETL-001 V1.6 baseline](ARCH_ETL_001_V16.md). The
[Sprint 03 report](../verification/arch-etl-001-v16-r1/sprint03/REPORT.md)
records executable contracts, migration safety, acceptance and limitations.

`JobOrderHistory` remains the logical execution, reached through existing fenced
source acceptance → durable CollectorRun evidence → NormalizedEvent →
`reduce_execution()`. Nullable `pentaho_*` fields distinguish lifecycle, outcome,
completeness, scoped identity and native schedule occurrence. Attempts, immutable
native aliases and append-only revisions extend this owner; no competing engine,
resource identity or workload runner is introduced. Other platform reducers retain
their path. Legacy status mapping remains compatible, including SUCCESS_AFTER_RETRY
as SUCCESS and WAITING_FOR_RETRY as RUNNING.

Retry grouping requires explicit native/scheduler authority attested per method,
not names, PID, time proximity or a connection test. An unverified proposal remains
separate/quarantined. Manual recovery is a many-to-many observed relationship
between distinct histories, confirmed by a different scoped investigator and
reversed only through an append-only decision. It never rewrites a failed original
or establishes incident restoration. Reads use `etl.view`; decisions use
`etl.investigate`, with customer enforcement and composite database constraints.

Migration `0033_pentaho_attempts` preserves legacy rows without guessed identity
backfills. Immutable journals and referenced evidence are protected; populated
downgrade fails closed. Full conflict adjudication, large-backlog replay, schedule
monitoring and incident redesign remain later milestones. All genuine Pentaho
runtime acceptance remains unexecuted.

### Pentaho R1 Sprint 04 — claim reconciliation

Pentaho evidence review extends the existing canonical execution reducer and
customer-scoped source pipeline. `pentaho_evidence_reviews` is a review queue,
not a second execution registry; `pentaho_evidence_decisions` appends evidence,
actor/reason and before/after projection decisions. `JobOrderHistory` gains an
independent nullable review state. Immutable native aliases and raw history are
preserved. Migration 0034 follows 0033 and refuses populated review downgrade.

Native invocation, execution outcome and scheduler retry authority are independent.
Equal applicable contradictory native claims preserve the last defensible projection
and require explicit customer-granted `etl.resolve_identity`. No existing employee
receives that permission implicitly. Identity quarantine cannot be bypassed by an
outcome or recovery decision. New evidence must prove identity; operator assertions
cannot retarget aliases. Raw source acceptance retains the existing fencing and
checkpoint transaction. Reviewed historical corrections cannot automatically drive
incident reopening; historical reassessment/notifications remain a separate gate.
See `../ARCH_001_V16.md` and the Sprint 04 verification report for contracts,
migration limitations and the deferred UI workflow. The controlling
`ARCH_ETL_001_V16.md` is unchanged; no live platform acceptance is implied.

### Pentaho R1 Sprint 05 — authority and historical processing

Pentaho reuses versioned ETL parameters and expected windows. Explicit modes
VERIFIED_SCHEDULER / MONITORING_EXPECTATION / MANUAL separate native schedule
claims from configured monitoring expectations. Exact-build, source-generation-
bound schedule export proof and native occurrence IDs are required for native
mode; unverified or expired exports fail closed. Coverage requires fresh complete
acceptance receipts and uninterrupted persisted monitoring observations, not a
healthy endpoint or a reachable collector alone.

Bounded accepted-evidence reconciliation reuses PipelineOperation and the existing
canonical reducer, with event-time range, independent approval outside method
bounds, live-first scheduling, fencing, holds and a separate operation cursor.
It never resets physical checkpoints or claims unproven provider-gap recovery.
Pentaho provider/file replay remains unsupported without verified continuity.

The historical notice outbox fills the proven gap in the live alert outbox (which
requires an AlertState). It reuses existing destinations, TLS/secret handling,
notification worker and recipient inbox instead of manufacturing live alerts.
Failure eligibility is independent of incident lifecycle; old closed incidents
remain closed. Delivery is opt-in, customer-scoped and idempotent in-app, with
leases/retries/audit and current authorization checks. Existing live notifications
run first and remain isolated from historical-worker failures.

Additive migration 0035 preserves legacy schedule and notification rows; protected
historical records refuse deletion/populated downgrade. See `../ARCH_001_V16.md`
and the Sprint 05 verification report for exact API contracts, test evidence,
unsupported native capabilities and the Sprint 06 boundary. The approved
ARCH_ETL_001_V16 baseline is unchanged.

### Pentaho R1 Sprint 06 — incident evidence and verified recovery

The existing native incident engine now accepts verified Pentaho terminal failure
associations, with immutable per-execution evidence and optional independently
attested native common-root references. Generic similarity/confidence grouping is
not promoted to verified causality. Historical eligibility from Sprint 05 produces
separately audited reassessment while preserving existing associations and closed
states; its notification outbox is unchanged.

Independent recovery assessments combine confirmed recovery relationships, native
outcome/completeness, source health, required dependencies, schedules and explicit
observation periods. Authorized existing lifecycle transitions recheck this gate;
a manual recovery never rewrites the failed execution. Additive migration 0036
pins the evidence and rejects populated downgrade. Customer-scoped native incident
APIs expose paged failure/assessment evidence and audited, revision/idempotency-
protected assessment mutations using existing explicit permissions.

See `../ARCH_001_V16.md` and the Sprint 06 verification report for contracts,
acceptance evidence and limits. ARCH_ETL_001_V16 remains unchanged. No ETL workload
controls, production changes, real-source activation or runtime certification are
included. Sprint 07 can consume these backend contracts.
