# ARCH-001 implementation assessment and migration design

Baseline: main `fc63455121a9a6fbb98f060622a6b816e097bff5`; implementation branch `feature/arch-001-unified-monitoring`.

## Assessment and gaps

| Domain | Existing implementation | Required correction |
|---|---|---|
| Identity/access | Normalized customer organizations; independent provider departments, employees and scoped RBAC | Keep customer ownership; remove the grant UI while preserving backend customer-scope enforcement |
| Resources | VM/JobOrder/DataSource identities plus independently configured Collectors | Unified resource bindings; inline customer onboarding; VM-owned collection configuration; SaaS ETL without a VM |
| Telemetry | Actual authenticated OTLP logs/metrics/traces; pinned Contrib; real HTTPS probing; Carte snapshots | Durable normalized log/API execution events, platform mappings and service evidence |
| ETL | Carte execution history, steps, daily schedule observation and investigation | Log reconstruction, retry/parallel-step identity, terminal status independent of conditions, persisted timezone-aware expected windows |
| Parameters | Versioned monitoring packages, activation and sustained metric evaluation | Exactly ETL/VM/API parameter editors with identity inheritance, explicit override provenance and effective preview |
| Correlation | Time-window evidence attached to ETL executions | Explicit dependency graph and cross-domain evidence groups; proximity alone must not establish cause |
| Incidents | Historic native tables retained; active native/ITSM behavior retired by PR #32 | Owner clarified: remove incident functionality and retain alerts/correlation; historical incident records remain intact |
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
6. Alert/correlation recovery and domain reporting; no incident lifecycle or external ITSM.
7. Disposable PostgreSQL migrations, security/integration/worker tests, actual OTel evidence, browser/build/Docker validation and documentation/PR delivery.

Each phase is committed after its relevant checks pass. Completion is evidence-based; unsupported/genuine provider and target-host acceptance remain explicitly recorded.

## Risks and dependencies

Legacy JobOrder serializers assume a non-null VM; coordinated API/schema/UI changes are required before SaaS ETL is exposed. Schedules require an IANA timezone, deterministic DST policy and durable catch-up. Execution events without an unambiguous execution key must remain unresolved instead of combining concurrent runs. Collector outages must produce telemetry uncertainty rather than invented ETL failure. Production service monitoring requires service-identity permissions on the actual target. Genuine IICS/Windows/cloud acceptance needs approved endpoints/credentials/hosts; controlled fixtures do not certify those providers.

## Phase evidence

Foundation validation uses `scripts/arch001-acceptance.py`: owned PostgreSQL 17, old-schema fixtures, additive upgrade, full Alembic comparison, immutable-history/identity checks, tenant constraints and an actual FastAPI process. Resource/parameter API tests verify inline customer creation, Windows/Linux onboarding, VM-less IICS, inherited ETL paths, safe YAML/JSON imports, immutable versions, scoped denials and refused activation without telemetry. `backend/tests/test_unified_monitoring.py` verifies safe schemas and timezone/DST calendar boundaries. The complete backend unit suite passes 57 tests at this foundation stage.

Pinned Contrib 0.123.0 validates the new loopback syslog receiver and log pipeline. Remote syslog requires TCP with mutual TLS; unprotected public UDP listeners are rejected. Native outbound API/IICS collectors require platform approval plus deployment-owned host, CIDR and port allowlists. HTTP requires a separate explicit deployment flag and cannot carry authentication. HTTPS always verifies TLS and pins an allowed DNS answer; no redirects are followed.

Agent configuration revisions now retain configured service identities. Read-only systemd/Windows SCM observations use fixed commands with validated argument lists and no shell. Failed queries produce unavailable/error evidence, not healthy values. Target OS service execution is a separate acceptance gate.

Engine replay, actual service/transport, domain UI and broader regression gates are not certified by these foundation checks; they are validated in subsequent phases.
