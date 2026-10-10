# DOC-02 — Software Requirements Specification
**Status:** Draft | **Version:** 0.1

Requirements use IDs for traceability. **MUST** means required for the proposed first operational release; **SHOULD** is an enhancement requiring prioritization.

## Functional requirements
| ID | Requirement | Priority | Verification |
|---|---|---|---|
| FR-001 | Create, edit, activate and select organizations with server-side tenant isolation | MUST | Cross-tenant API tests |
| FR-002 | Manage data sources scoped to organizations, including type, environment and connection settings | MUST | CRUD/API and UI tests |
| FR-003 | Configure and manage collector instances, intervals, lifecycle and health | MUST | Collector integration tests |
| FR-004 | Attach monitoring templates to data sources and resolve them into effective collector/metric/log configuration | MUST | Template-to-execution end-to-end test |
| FR-005 | Collect and persist metric samples and log events with resource association | MUST | Ingestion and query tests |
| FR-006 | Monitor scheduled Pentaho executions and preserve source statuses, history and step evidence when available | MUST | Adapter contract tests |
| FR-007 | Detect missing, failed, long-running and unresponsive execution states without conflating them | MUST | Deterministic time/state tests |
| FR-008 | Evaluate alert rules, maintain alert state and deduplicate transitions | MUST | Alert state tests |
| FR-009 | Send selected alert transitions via configured notification channels with retry/audit | SHOULD | Mock-provider tests |
| FR-010 | Correlate execution evidence with related metrics/logs/alerts without claiming confirmed root cause | SHOULD | Correlation tests |
| FR-011 | Provide dashboard KPI cards linking to filtered item lists | MUST | UI navigation tests |
| FR-012 | Support resource, alert and execution drill-down with organization filters | MUST | E2E navigation tests |
| FR-013 | Support read-only checks for API, SFTP, S3, databases and VMs via least-privilege adapters | SHOULD | Per-adapter tests |
| FR-014 | Record configuration and privileged activity in audit logs | MUST | Audit tests |
| FR-015 | Provide exportable execution and notification reports | SHOULD | Report tests |

## Nonfunctional requirements
| ID | Requirement | Verification |
|---|---|---|
| NFR-001 | Every organization-scoped query enforces authorization on the server | Negative authorization tests |
| NFR-002 | Credentials are never committed or returned in plaintext to clients | Secret scanning and API tests |
| NFR-003 | Collector work is isolated from request processing and bounded by timeout/retry limits | Worker resilience tests |
| NFR-004 | Ingestion and alert processing are idempotent for stable event identities | Replay tests |
| NFR-005 | UI polling target is 5 seconds where enabled; actual load/performance budgets TBD | Load and browser tests |
| NFR-006 | Errors distinguish upstream outage, auth failure, no data and business failure | Failure injection |
| NFR-007 | Database changes use reversible or documented safe migrations | Migration tests |
| NFR-008 | Production operations require logging, auditability and documented rollback | Release checklist |
| NFR-009 | Accessibility, browser support, retention, uptime and recovery objectives must be baselined before release | Stakeholder sign-off |

## Assumptions and open issues
- Data source templates must create **effective operational monitoring**, not only a saved configuration package.
- A source can be active while an individual collector is unhealthy.
- Customer-specific credentials and datasets will not be embedded in public tests/docs.
- Notification channel availability and credentials are environment-dependent.
- Read-only monitoring is the default; remediation is a separately gated capability.

## Audit-driven SRS refinements (2026-10-10)
These strengthen the baseline and are **requirements**, not assertions of current functionality.

| ID | Requirement | Priority | Verification |
|---|---|---|---|
| FR-016 | All organization-scoped list, detail, create, edit and delete operations MUST derive authorized tenant scope from authenticated identity, never from request filters alone | MUST / P0 | User A cannot enumerate, read, modify or delete B data even with B IDs |
| FR-017 | Monitoring template activation MUST validate, materialize/reconcile effective Collector, MetricDefinition, LogSource and AlertRule objects and expose activation/health state | MUST / P0 | Attach template -> scheduler run -> persisted metric sample; idempotent reactivation |
| FR-018 | UI KPI totals MUST derive from the same authorized query scope as the linked filtered list; demo data MUST be clearly identified | MUST / P1 | Seeded counts and click-through E2E tests |
| FR-019 | Collector adapter capability MUST be exposed accurately (supported, configuration-only, unavailable) | MUST / P1 | API and UI capability tests |
| NFR-010 | HTTPS collection MUST support certificate verification and correct SSL context handling | MUST / P1 | Controlled TLS endpoint tests, trusted and untrusted certificates |
| NFR-011 | CI MUST run automated backend tests, frontend build/lint, migration smoke tests and API startup checks before release | MUST / P1 | Required checks and published evidence |
| NFR-012 | A release MUST NOT represent placeholder pages or stub collectors as live operational functionality | MUST / P1 | Product review and smoke-test checklist |

See [DOC-07 Code Audit](07-CODE-AUDIT.md) and tracked issues #2–#7.
