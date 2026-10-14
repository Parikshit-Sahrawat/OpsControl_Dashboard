# Unified monitoring operations — ARCH-001 V1.5

OpsControl monitors three domains: ETL, VM/EC2 health and API availability. Customer organizations remain the resource ownership boundary. Employee departments remain independent provider teams. V1.5 restores native incidents and recovery validation. External ITSM and the Organization Access editor remain removed; backend customer grants remain enforced.

## Resource onboarding

Open Resource Management → Data Resources. The three domain tabs are Data Pipelines, Compute Instances and API Endpoints. Administrative filters are independent of the operational header's customer/environment selector.

**Compute Instances:** Create a Windows/Linux VM with name, hostname, DNS/IP, customer, environment and VM/EC2 classification. Select a normalized customer or, with platform administration authority, create one inline. Configure native host metrics, optional services/processes and independent collection methods. A repeated method type receives its own stable ID and revision. The logical Collector belongs to the VM; installation runs an OpsControl Agent supervising Contrib 0.123.0. Configure methods, preview and validate YAML, save a revision, issue a short-lived enrollment token and install the agent. Explicitly approve a revision for application. Verify authenticated runtime heartbeat, matching applied configuration and actual selected signal reception before activation. A stopped service is valid observed evidence, not missing instrumentation. Unknown/missing telemetry must never be interpreted as health.

**Data Pipelines:** Select Pentaho, IICS, Airflow, NiFi, Azure Data Factory, AWS Glue, SSIS, Talend or Custom/Shell. Selecting a VM inherits customer, environment, host identity and Collector. Supply multiple absolute log paths and parser mappings; those paths become separate VM Collector methods. Apply a new agent configuration revision before attempting activation. SaaS IICS may have no VM. Its read-only metadata connector uses an approved HTTPS endpoint, an operator-provisioned secret reference and explicit field/status mappings. `INFA-SESSION-ID`, `icSessionId` and Authorization bearer headers are supported; choose the actual deployment's header. Do not store credentials in JSON or URLs. Metadata must identify executions and source timestamps; incomplete inventories cannot certify schedule coverage. Genuine provider acceptance requires the actual customer-approved interface and credentials.

**API Endpoints:** Configure customer, environment, DNS/IP, port, HTTP/HTTPS, path, GET/HEAD/OPTIONS, frequency, timeout, expected authentication reference, optional VM and probe location. The backend worker independently validates deployment-approved host, exact destination CIDR and port, pins the DNS answer, verifies TLS and refuses redirects. HTTP is disabled unless explicitly allowed and never carries authentication. Platform administration approval starts a native probe; saving an endpoint does not execute it or certify availability.

Existing resource UUIDs and histories are retained. Legacy records without an unambiguous host/collector mapping remain visible with reconciliation issues; editing an immutable ownership binding through a generic API is forbidden. Review those mappings before activation. The deployment does not guess or delete ambiguous records.

## Event Parameters

Resource Management → Event Parameters has exactly Data Pipeline Parameters, Compute Health Parameters and API Endpoint Parameters. Select a resource to view inherited identity. Identity attributes are read-only. Save a validated version, inspect the effective preview and explicitly activate it. Provenance identifies INHERITED, CONFIGURED, OVERRIDDEN and TELEMETRY_DERIVED values. Parameter activation and resource activation are distinct operations.

ETL rules cover calendar schedules (hourly, daily, weekly, monthly, quarterly and five-field custom cron), IANA timezone, DST fold policy, exceptions, No Run grace, delayed starts, Long Running, No Response, completion SLA and dependencies. Expected windows persist even when no logs arrive. Collector outages leave those windows UNKNOWN; observed failed dependencies may mark them BLOCKED. Execution terminal status is separate from concurrent monitoring conditions.

VM rules bind exact observed metric definitions and units. Static, dynamic-baseline and combined thresholds support sustained windows, consecutive samples, maximum gaps and recovery hysteresis. Configure service/process collection in the parent VM before enabling matching rules. Missing instrumentation is reported separately from service/process failure.

API rules configure expected statuses, warning/critical latency, consecutive failures, recovery successes, missing results and observed-probe availability windows. Native runs retain their active policy version/hash at observation time; later policies do not reinterpret historical outcomes. Availability here is weighted per completed probe, not a time-weighted SLO or contractual uptime guarantee.

## Native engine behavior

Normalized execution events retain source evidence and semantic identities. Replay handles duplicate/out-of-order events, parallel executions, step retries and missing terminal events. Ambiguous execution identifiers remain unresolved rather than combining concurrent runs. One complete jobchain execution maps to one existing JobOrderHistory record; step attempts remain independently identified.

The collector worker runs durable reconstruction, schedule evaluation, domain rules and correlation with bounded processing, resource row leases and customer/environment correlation locks. Poison resources roll back independently and expose an evaluation error. Disabled customer organizations stop local collection/evaluation. Recovery requires observed data. Correlation requires explicit same-customer/environment relationships and overlapping evidence; confidence describes an association, never a proven root cause.

Overview KPIs open filtered domain/alert lists. Reports aggregate persisted ETL execution/step/window history, actual VM metrics and completed API probes. Empty results remain empty. Reports accept aware date ranges up to 366 days and paginate histories. Histograms are bounded and label their observation units. Legacy inventory adapters remain available through operational compatibility views.

## API surface

All routes require authenticated permissions and independently enforce customer scope.

| Route under `/api/v1/unified` | Purpose |
|---|---|
| `GET /resources` | Customer/domain/environment/search filters; SQL total and pagination |
| `POST /resources/vm`, `/resources/etl`, `/resources/api` | Typed, scoped onboarding |
| `GET /resources/{id}`, `PUT /resources/{id}` | Details and revision-checked configuration updates |
| `GET /resources/{id}/verification`, `POST /resources/{id}/activate` | Actual evidence gates and explicit activation |
| `POST /resources/{id}/start-probe` | Platform-approved native outbound collection |
| `POST/DELETE /resources/{id}/dependencies[/dependency_id]` | Scope-checked, cycle-free relationship history |
| `POST /parameters/{id}/preview`, `POST/GET /parameters/{id}` | Effective provenance, immutable save/history |
| `POST /parameters/{id}/import`, `/import/validate` | Safe bounded YAML/JSON validation/import |
| `POST /parameters/{id}/activate` | Explicit version activation with retained intervals |
| `GET /resources/{id}/executions`, `/schedule-windows`, `/metrics` | Actual execution/step/expectation/series evidence |
| `GET /overview`, `/domain-state/{domain}`, `/alerts`, `/correlations`, `/reports/{domain}` | Operational evidence and SQL report aggregates |
| `GET /mapping-issues` | Scoped legacy reconciliation exceptions |

Existing `/agent-control`, authenticated `/agent`, alert acknowledgment, notification and customer-grant APIs remain authoritative. The customer-grant APIs are retained for authorized administration; there is no grant editor in Access Management. OpenAPI provides exact request/response schemas.

## Database and migration

`0027_unified_monitoring` follows `0026_managed_telemetry_uat`. It adds monitoring_resources, resource_dependencies, resource_parameter_versions, resource_parameter_activations, normalized_telemetry_events, expected_execution_windows, resource_conditions, event_correlation_groups, event_correlation_members and resource_mapping_issues. It extends CollectorRun metadata, execution conditions, step attempt/evidence and agent configuration snapshots. JobOrder.vm_id becomes nullable for SaaS; a partial unique index prevents duplicate VM-less customer/job/environment identities. DELAYED/UNKNOWN enum labels are additive.

Backfill retains existing resource primary keys, customer foreign keys, password hashes, sessions, execution history and incident archives. Composite scope foreign keys and a database resource identity trigger reject cross-customer bindings. Parameter documents are immutable; activation intervals preserve policy provenance and rollback history. Historical migrations are unchanged.

For production, first identify the exact database and approved window, restore-test its backup, take a migration-specific backup, inventory counts/mapping exceptions, run the migration transaction and compare identities/counts/FKs afterward. No production operation was performed during development. A populated downgrade refuses data loss. Application rollback must retain the additive schema; a schema rollback requires verified restoration or an empty new schema. Enum labels remain after an empty downgrade because removing them would rewrite history.

## Local Docker verification

```bash
bash scripts/demo-up.sh
docker compose -f docker-compose.demo.yml ps
docker compose -f docker-compose.demo.yml exec -T api python -m alembic current
docker compose -f docker-compose.demo.yml exec -T api python -m alembic check
docker compose -f docker-compose.demo.yml logs --tail=40 worker
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:5173/ >/dev/null
```

The demo includes PostgreSQL, API, frontend, authenticated TLS ingestion gateway and the background worker. Its fictional bootstrap is idempotent and does not activate monitoring. Sign in as demo-admin with the generated private password file. API/worker share deployment-owned native host/CIDR/port allowlists. The default allowlists are empty; no arbitrary outbound probe is permitted. Provision target credentials and trust through a private Compose override, never tracked config. The local ingestion gateway uses HTTPS on localhost:8443; trust the generated development CA explicitly. Remote hosts require an approved reachable DNS identity and matching trust.

Run development gates from the repository root after preparing backend/.venv and frontend dependencies:

```bash
(cd backend && .venv/bin/python -m unittest discover -s tests -v)
npm test --prefix frontend
npm run build --prefix frontend
ARCH001_API_ACCEPTANCE=1 ARCH001_ENGINE_ACCEPTANCE=1 \
  backend/.venv/bin/python scripts/arch001-acceptance.py
ARCH001_API_ACCEPTANCE=1 ARCH001_ENGINE_ACCEPTANCE=1 ARCH001_RUNTIME_ACCEPTANCE=1 \
  OPSCONTROL_OTEL_BINARY=/absolute/path/to/verified/otelcol-contrib \
  backend/.venv/bin/python scripts/arch001-acceptance.py
ARCH001_API_ACCEPTANCE=1 ARCH001_ENGINE_ACCEPTANCE=1 ARCH001_BROWSER_ACCEPTANCE=1 \
  PLAYWRIGHT_MODULE=/absolute/path/to/playwright/index.mjs \
  PLAYWRIGHT_CHROMIUM_EXECUTABLE=/absolute/path/to/chromium \
  backend/.venv/bin/python scripts/arch001-acceptance.py
backend/.venv/bin/python scripts/access-acceptance.py
backend/.venv/bin/python scripts/access-docker-demo.py
```

These labs own random-named disposable PostgreSQL/TLS targets, ports and credentials; they do not modify production or existing Docker volumes. Redacted reports and actual screenshots go to ARCH001_EVIDENCE_DIR (default `/tmp/opscontrol-arch001-evidence`). Runtime and browser runs should be separate so local Docker network changes do not interrupt Chromium. `.github/workflows/arch001-native-monitoring.yml` repeats these checks with the digest-pinned upstream binary.

## Acceptance boundaries

Checked-in [evidence](evidence/arch001/) records passed owned PostgreSQL migrations, actual API/scoping, controlled engine boundaries and actual Agent/Contrib/native TLS transport. Controlled IICS-style metadata is not genuine IICS acceptance. Native Windows service execution, real systemd installation/permissions, AWS discovery, actual provider account acceptance, production migration/backup and independent operator/security sign-off remain target-environment gates. Remote installation is unavailable without an authorized channel. The historical browser suites written for removed standalone tabs need updated journeys; their old assertions must not be reported as passing the new architecture.

## V1.5 Agent and configuration lifecycle

Enrollment tokens expire and are one-use, stored hashed server-side. Renewable
credentials remain bound to the enrolled resource; revocation invalidates current
and grace credentials. Desired, downloaded, applied, verified and last-working
versions are distinct. The server verifies the checksum and post-application
telemetry; quiet readable File Logs are explicitly Idle, never fabricated reception.
Operator approval controls configuration application. Failed validation rolls back
to a known working revision and preserves compatible file checkpoints.

Use Compute onboarding's ten stages and save drafts when interrupted. Event
Parameters, Alert Rules and Notification Delivery are optional for monitoring
activation. Enabling alerting explicitly binds an active parameter version.
Edits use optimistic revision checks. Pause stops the bound Data Source/Collector.
Use Collection Methods to change bound log paths deliberately.

## Native incident operations

Grant incidents.view, incidents.acknowledge and incidents.manage explicitly to
appropriate roles and customer scopes. Existing retired assignments remain inactive.
The default-deny API requires customer grants independently of navigation visibility.
Open a native incident, assign an authorized employee, add investigation notes and
move through Acknowledged, Investigating, Recovery in Progress and Monitoring.
Resolution requires fresh healthy source evidence over the configured recovery
window. A rebreach inside the window prevents resolution. Resolved incidents may
close or reopen; all transitions retain actor, revision and audit history. Original
breach evidence remains immutable even when the underlying alert recovers.

## Reproducible validation

Run make test-all after installing runtime/dev requirements and the pinned actual
Contrib binary. Separate runtime and browser labs avoid network topology changes
interrupting Chromium. See docs/TESTING_V15.md and the implementation status ledger
for passed, failed, fixture-based and pending native/provider checks. Use
scripts/backup-local-demo.py before upgrading an existing local demo; it restores
an owned copy and compares records without modifying the source database.

## V1.5 additive migration verification

Current head is `0031_in_app_notifications`, after the registry/draft/runtime checkpoint migration 0028, Agent control migration 0029 and native incident migration 0030. Run `backend/.venv/bin/python scripts/backup-local-demo.py` before upgrading the default existing local demo; require restore verification. The helper preserves a private dump and its checksum. Then run `bash scripts/demo-up.sh`, `alembic current` and `alembic check` inside the API service. Guarded populated downgrades refuse data destruction and privilege resurrection; retain the additive schema for application rollback.
