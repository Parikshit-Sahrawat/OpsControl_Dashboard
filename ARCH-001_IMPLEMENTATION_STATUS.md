# ARCH-001 V1.5 implementation and verification

Evidence date: October 14, 2026. Development target: `main`. This release is for local Docker development and controlled testing. No live production deployment was performed. Native Incidents are restored under the owner's V1.5 clarification; external ITSM integrations remain removed.

## Implementation matrix

| Checkpoint / feature | Status | Implementation | Verification and limits |
| --- | --- | --- | --- |
| A: Attribute/Capability Registry | Implemented and verified | `backend/app/registry`, `DynamicConfigurationForm.jsx`, migration 0028 | Typed/versioned definitions, OS-conditional inputs, secret rejection, scoped API and actual browser forms |
| A: Resources, relationships and drafts | Implemented and verified | `backend/app/unified`, `UnifiedResourceManagement.jsx` | Three domains, inline organization creation, inherited VM/collector, immutable customer ownership, saved/resumed ten-stage wizard and optional alert stages |
| A: Access Management | Implemented and verified | `backend/app/security`, `backend/app/api/access.py`, Access UI | Separate departments/customers, Name/Username/Email columns, membership/effective permissions, 25 independent security groups and five actual browser workflows |
| B: Agent identity/control plane | Implemented and controlled-runtime verified | `agent/opscontrol_agent.py`, telemetry API/models, migration 0029 | One-use/expired enrollment, renewable/rotating/revocable identity, same-resource re-enrollment, scoped configurations/checksums and authentic receipt verification |
| B: Configuration reconciliation | Implemented and verified | Agent supervisor, telemetry compiler/deployment history | Desired/downloaded/applied/verified/last-working states; invalid rollout rollback; authorization denial stops the runtime; persistent source/export buffers |
| B: Linux package | Implemented; package/runtime verified | Install/uninstall scripts, `scripts/build-demo-agent.sh`, package builder | Actual package with digest-pinned Contrib 0.123.0 built; actual Supervisor runs in the owned TLS lab. Privileged target-systemd clean install/upgrade/uninstall remains host UAT |
| B: Windows package | Implemented; native build/installation awaiting validation | `agent/windows_service.py`, PowerShell installers, Inno Setup build, packaging workflow | Source/build pipeline provided; this Linux environment does not certify a compiled Windows EXE or SCM install/upgrade/uninstall |
| C: Five collection methods | Implemented and controlled tests verified | `telemetry/configuration.py`, ingestion, `agent/service_health.py` | Host Metrics, Services, Syslog, File Logs, OpsControl Scrape; independent same-type methods, actual Contrib configuration validation, selected signals and OS constraints |
| C: File Logs and scrape | Implemented and local-runtime verified | Pinned Contrib receivers and durable file storage | Actual HTTP scrape and file rotation/truncation/restart tests; separate source identities, readable quiet-file Idle handling and failure states |
| C: Telemetry ingestion | Implemented and verified | Authenticated OTLP ingestion and TLS gateway | Actual logs/metrics/traces persisted over verified TLS; customer/method scoping, evidence timestamps, missing-data distinction |
| D: Nine platform adapters | Implemented; controlled contracts verified; live validation pending | `backend/app/pipeline_adapters` | Pentaho, IICS, Airflow, NiFi, ADF, Glue, SSIS, Talend, Custom/Shell; platform semantics, auth/errors, pagination, checkpoints and normalization. Genuine provider acceptance remains separate |
| D: Execution reconstruction/deduplication | Implemented and verified | `unified/normalization.py`, `reconstruction.py`, runtime cursors | Persisted raw evidence, distinct source identity, stable execution/step/retry identity, duplicates/out-of-order/incomplete terminal conflicts and restart handling |
| D: Schedule evaluation | Implemented and verified | `unified/calendar.py`, `engines.py`, expected windows | Time-zone/DST-aware schedules, No Run without incoming logs, delayed/long-running/SLA conditions, outage uncertainty and durable restart evaluations |
| E: Parameters and Alert Rules | Implemented and verified | DomainParameters, NativeAlertSetup, unified schemas/API/engines | Three domain editors, inheritance/provenance, explicit activation, sustained/consecutive conditions, refreshed active evaluation and deduplicated recovery |
| E: Notifications | Implemented and verified | `telemetry/inbox.py`, delivery worker, EventDelivery, migration 0031 | Optional RBAC-scoped user/team inbox, preferences, queue retries/idempotency; actual queued HTTP/DB delivery. SMTP/webhook TLS contracts tested without sending external messages |
| E: Correlation and native incidents | Implemented and verified | `backend/app/native_incidents`, unified correlation, migration 0030 | Seven lifecycle states, assignment, notes/escalation/reopen/revisions, preserved evidence, recovery observations, audits/customer/environment filtering; API and actual browser acceptance |
| F: API Endpoint monitoring | Implemented and controlled-runtime verified | Native API transport/adapters/worker | Real approved HTTPS probe failure/recovery with TLS, SSRF/redirect/credential boundaries |
| F: Overview and reports | Implemented and verified | UnifiedOverview, DomainReports, unified reporting | Persisted three-domain data, filters/pagination, clickable KPIs and actual browser routes; no hardcoded live health |
| F: Local Docker/data preservation | Implemented and verified | Demo Compose, TLS gateway, backup and smoke scripts | Five services, additive head 0031, 74 tables/zero drift, populated migration preservation, guarded rollback, restart/session/bootstrap idempotency and restored local backup |
| Continuous quality | Implemented; local gates verified | Makefile, test-quality runner, ESLint, V1.5 Actions workflows | Formatting/lint/build, backend/frontend/security/runtime/browser/migrations/Docker, measured coverage and bounded performance; remote CI status must be checked separately |
| Remote SSH/WinRM installation | Unavailable until an authorized management channel is configured | Manual installation remains functional | No remote-success button or claim based solely on knowing a host IP |

## Executed validation

- **194 backend tests passed**, including actual Contrib runtime tests; no skipped tests when `OPSCONTROL_OTEL_BINARY` is configured.
- **6 frontend permission tests passed**. Node's scoped coverage measured `permissions.js` at **95.24% lines / 88.24% branches**; this is not whole-React coverage.
- Black, Ruff correctness checks, scoped Prettier, ESLint and Vite production build passed.
- Clean combined critical-module statement/branch coverage passed the unchanged **80% gate** (measured **80.24%**). Scope: registry, unified monitoring, managed telemetry, pipeline adapters, native incidents and Agent; it does not represent every legacy/security/worker module.
- Actual TLS Agent 1.5 + Contrib 0.123.0 telemetry, execution/alert/probe recovery and enrollment/rotation/revocation API/DB acceptance passed.
- Actual Playwright wizard/drafts/registry/parameters/report/incident/inbox/access and mobile journeys passed. Screenshots are actual controlled local UI captures.
- Independent access migration/schema/RBAC regression passed **25 check groups**; Access UI passed **5 browser checks**.
- Controlled legacy monitoring UAT passed. Its fixtures do not certify genuine providers.
- Disposable migration upgrade/downgrade/upgrade, populated identity/history preservation and unsafe rollback refusal passed. Full PostgreSQL/model comparison: **74 tables, zero drift**.
- Isolated five-service Docker build/bootstrap/restart/authentication passed. Existing local demo was backed up, restore-verified (42 original tables / 20 records), upgraded additively and checked through actual login, API/UI, trusted TLS and Alembic consistency.
- Current Python/npm dependency scans passed; this is not an assertion that unknown vulnerabilities do not exist.
- Controlled loopback performance: **100 API and 100 ingestion requests, concurrency 4, zero errors**. The first fresh run measured p95 API **1067 ms**, ingestion **174 ms**. These bounded results do not establish production capacity or a universal SLA.

Evidence is under [docs/evidence/v15](docs/evidence/v15). Reproduce with [docs/TESTING_V15.md](docs/TESTING_V15.md); never mix different source revisions to manufacture coverage. Private credentials, backups, packages and failure diagnostics are excluded from Git.

## Migrations and recovery

Preserved historical migrations are followed by:

1. `0028_attribute_registry`: immutable registry, scoped onboarding drafts and durable runtime checkpoints.
2. `0029_agent_v15`: Agent identity/configuration lifecycle metadata.
3. `0030_native_incidents_v15`: additive native incident associations/details and lossless inactive legacy permission links; no implicit privilege grants.
4. `0031_in_app_notifications`: user preferences and durable user-targeted inbox with database idempotency constraints.

Populated downgrades refuse data loss or privilege resurrection. Retain additive schema for application rollback; use an explicitly verified backup for a database restoration. Do not drop existing volumes or remove unmapped histories.

## Remaining verification limits

- Native Windows build/signing/service installation and privileged Linux host installation/upgrade/uninstall require the corresponding runners/hosts. Unsigned development installers are not production release artifacts.
- All genuine external provider integrations require approved instances, credentials and provider-version acceptance. AWS setup remains paused. SSIS requires its supported ODBC driver; Glue requires a valid SDK/workload identity.
- Services and syslog have controlled configuration/contracts; genuine target service permissions and target-network listener acceptance remain host UAT.
- Long-interval sources must be reviewed against freshness windows; the current control plane expects frequent Agent heartbeat and recent activation evidence. Do not infer missing-data health from saved configuration.
- Large inventories, sustained high-volume logs, multi-agent outages, regional failover and production capacity/RTO/RPO require broader load and resilience acceptance. The bounded local load test does not cover those scenarios.
- Independent security review and operator UAT remain the owner's local acceptance activities. Local test success does not authorize live rollout.

## Git delivery

Verified implementation commit on `main`: `ac01704` (`feat: deliver ARCH-001 V1.5 agents monitoring incidents and verified local UAT`). Earlier architecture checkpoints are `51a989c`, `e54891a` and `72b3550`. The subsequent documentation commit records delivery metadata only; application source remains the validated implementation. Remote CI is a separate gate and is not replaced by local success.
