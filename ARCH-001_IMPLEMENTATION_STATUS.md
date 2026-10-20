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

## ARCH-ETL-001 V1.6-R1 Sprint 01

Branch: `feat/arch-etl-001-v16-r1`. Immutable baseline published in `ce603a4`;
source R1 README `cab0e63`. [Controlling specification](docs/architecture/ARCH_ETL_001_V16.md),
[REC-01–REC-12 reconciliation](docs/architecture/ARCH_ETL_001_V16_R1_RECONCILIATION.md),
[focused verification](docs/verification/arch-etl-001-v16-r1/sprint01/REPORT.md).
Historical V1.5 results above are not R1 implementation/certification results.

| Work | Status | Evidence / limitation |
| --- | --- | --- |
| Approved authority publication | Complete | Exact 23,653-byte copy; SHA-256 `ed8af0f9c3fce3375d0375e2431bdf43567133943551b2c0bc9f0b9882ab5446`; published separately from application changes |
| REC-01–REC-12 architecture reconciliation | Complete for Sprint 01 | All mapped to source clauses, canonical owners, known gaps and later implementation; formal sign-off/runtime completion not implied |
| Versioned read-only Pentaho surface contract | Implemented and contract-tested | Existing metadata APIs expose Kitchen/Pan/Server as proposed and Carte as partial; no new runnable adapter, all unverified |
| Candidate version families | Implemented as metadata only | Existing candidates retained, 10.2.x/11.0.x added; none certifies an installed build |
| Employee cardinality / P0 wording | Architecture ambiguity resolved | Exactly one department for new employees, preserve legacy multi/direct roles; reconstructed RT index accepted by baseline §§14–15 |
| Attempts, verified projections, historical notifications | Pending Sprint 02 | Existing mutable history/step attempts do not supply the complete logical-attempt/revision/idempotency contract |
| CLI/Server and full Carte adapters / operational UI | Pending later implementation | Metadata is not execution, installation, endpoint support or runtime parity |
| Incident/granular scope/replay/retention extensions | Pending later implementation | Reuse current owners, explicit denies, fences and legal holds; no runtime policy change this sprint |
| Migrations | None introduced | Existing `0032_pipeline_ownership` retained; concrete schema gaps documented before design |
| Focused tests / static/reference checks | See verification report | Baseline regressions and six new executable contract tests; no false native-runtime acceptance claim |
| RT-001–RT-020 genuine Pentaho acceptance | NOT RUN | Requires actual exact-build installations, native evidence and independent reviewers; no architecture-text blocker remains |

Stop after the focused Sprint 01 commit. No PR, merge, deployment, production-data
change, ETL control command or full Pentaho/RBAC/UI redesign in this sprint.

## ARCH-ETL-001 V1.6-R1 Sprint 02

[Adapter implementation and verification report](docs/verification/arch-etl-001-v16-r1/sprint02/REPORT.md).
The immutable Pentaho specification remains unchanged. This supersedes Sprint 01
metadata-only status for the capabilities below; it does not mark full R1 complete.

| Work | Status and limits |
| --- | --- |
| CLI observations | Implemented/local deterministic verification: host/start/invocation identity, executable hash, job/transformation distinction, native-result normalization, argument hashing. Native OS process/log producers and installation/runtime verification remain pending |
| Server observations | Implemented/local deterministic verification: authorized Agent export schema, repository/scheduler/history authority separation. Server network APIs remain unsupported without exact-build endpoint/auth/native-shape evidence |
| Carte R1 reader | Implemented/local deterministic verification: three fixed TLS GET paths, safe XML, server/restart scoping, advisory inventory, unchanged-status and epoch-bound checkpoints. Exact-build mapping, automatic epoch detection and genuine runtime acceptance remain unverified |
| Shared integration | Existing versioned connections, method identity, source fence/generation, customer/host binding, atomic evidence/checkpoint acceptance, selected-job projection and capability gates retained/extended; no duplicate models |
| Runtime capability gate | Exact-build/surface proof added before profile labeling and to collection eligibility; static context/candidate metadata never certifies |
| Verification | 110 unit tests, 56 actual PostgreSQL tests and nine existing HTTP groups passed; migration integrity and static/import checks passed. See report for commands and test boundaries |
| Migrations / protected semantics | No new migration or frontend change; no retry/recovery reconstruction, conflict engine, incident/RBAC redesign, ETL control, retention deletion, merge or deployment |
| Genuine RT-001–RT-020 | All 20 NOT RUN. Three surfaces remain PARTIAL and runtime-unverified; no live provider access or real source activation |

Stop after Sprint 02. Next sprint: logical executions/attempts and observed
retry/recovery reconstruction, with genuine source evidence required separately.

## ARCH-ETL-001 V1.6-R1 Sprint 03

[Implementation and verification report](docs/verification/arch-etl-001-v16-r1/sprint03/REPORT.md).
Baseline `7cd81efc65aba53a768b23ab1c0037f34a2a4559`; same R1 development branch.
Approved Pentaho architecture unchanged. No PR, merge, deployment or real-source activation.

| Work | Status / evidence |
| --- | --- |
| Canonical identity and attempts | Implemented and locally verified on existing JobOrderHistory/reducer; immutable scoped native aliases, whole-run attempts and append-only observation revisions |
| Retry lifecycle | Verified pending retry remains WAITING_FOR_RETRY; verified later success is SUCCESS_AFTER_RETRY; final failure requires exhaustion authority; missing authority never implies exhaustion |
| Manual recovery | Distinct logical execution; many-to-many observed links, independent scoped confirmation, idempotency, audited reversal and original FAILED preservation |
| Security / compatibility | Customer/resource/history composite FKs, explicit verified native claims, new-model ORM scoping and existing etl.view/etl.investigate enforcement; eight other adapters unchanged |
| Migration | Additive 0033_pentaho_attempts; populated old customer/user/hash/history/evidence/hold preservation, empty roundtrip, populated downgrade refusal and no drift verified |
| Executed tests | 150 unit tests and 76 actual PostgreSQL tests passed, zero failed/skipped; nine existing and four new actual HTTP groups passed; imports/mappers/routes/static checks passed |
| Cleanup | Only related query reuse, post-lock observation refresh, R1 synthetic-start removal and touched import formatting; no active legacy model/adapter removed |
| Runtime acceptance | RT-001–RT-020 all NOT RUN. Provider-specific producers, genuine exact builds/native artifacts and independent certification remain required |
| Later milestones | Sprint 04 full conflict/identity adjudication; later replay/schedule and incident changes. Existing 100-run intake and embedded-history bounds remain; no load or production-readiness claim |

Stop after Sprint 03. No frontend workflow was added. New tables are persistence
extensions, not a second canonical execution, incident or scheduler engine.

### ARCH-ETL-001 V1.6-R1 — Sprint 04

| Feature | Implementation / verification | Evidence / limitation |
| --- | --- | --- |
| Claim-specific reconciliation | Native invocation/outcome/scheduler authority separated; contradictions freeze the last defensible projection | `backend/app/unified/pentaho_execution.py`; deterministic + owned PostgreSQL tests |
| Evidence Review | Six categories, append-only actor/reason/evidence/projection decisions; granular customer-scoped permission; stale/idempotent/concurrent decisions tested | `pentaho_review.py`, unified APIs, migration `0034_pentaho_review`; no implicit role grants |
| Identity correction | Exact matching legacy adoption and verified outcome correction; immutable aliases preserved | Ambiguous merge/split/alias remapping unsupported and quarantined; missing pre-S04 proof snapshots require new verified evidence |
| Operational safety | Prior conditions held during unresolved review/historical adjudication; no automatic incident reopening | Historical notification/reassessment remains Sprint 05; no Sprint 06 redesign |
| Regression/security/migrations | 155 unit tests, 101 PostgreSQL tests, 18 authenticated HTTP groups passed; migration/schema checks passed | Owned PostgreSQL + real authenticated HTTP with controlled authority fixtures; no live certification |
| Native provider acceptance | NOT RUN | RT-001–RT-020 require separately authorized genuine installations/evidence |
| Frontend | NOT RUN / not modified | Backend contract documented for Sprint 07 |

Delivery evidence: `docs/verification/arch-etl-001-v16-r1/sprint04/REPORT.md`.

### ARCH-ETL-001 V1.6-R1 — Sprint 05

| Feature | Implementation / verification | Limitation |
| --- | --- | --- |
| Schedule authority | Explicit native/expectation/manual modes; versioned immutable occurrence provenance; calendar/DST/freshness/grace/NO_RUN tests | Native exports require exact-build independent acceptance; unknown/partial telemetry never establishes absence |
| Historical reconciliation | Bounded accepted-evidence range cursor, live-first fencing/holds, independent beyond-bound review, restart/idempotency safeguards | No provider/file rewind, fabricated native endpoints, gap closure or live continuity certification |
| Historical notices | Customer opt-in policy; durable execution/destination obligations; existing transports/worker/inbox; retries, current RBAC, audit and evidence pinning | External SMTP/webhook delivery not exercised; full incident/recovery redesign remains Sprint 06 |
| Migration | 0035_pentaho_history; preserved legacy inbox/alert/schedule and R1 attempt/history snapshots | Populated rollback is intentionally blocked; verified restore or schema-compatible code rollback required |
| Verification | 160 unit tests, 127 PostgreSQL tests and 22 HTTP groups passed; migration/import/static checks passed | Controlled fixtures are not runtime certification; RT-001–RT-020 remain NOT RUN |

Evidence: `docs/verification/arch-etl-001-v16-r1/sprint05/REPORT.md`.

### ARCH-ETL-001 V1.6-R1 — Sprint 06

| Feature | Implementation / verification | Limitation |
| --- | --- | --- |
| Incident correlation | Existing native incidents retain identities and seven-state lifecycle; immutable per-execution failure evidence; exact, capability-attested common-root references; separate unrelated failures | Native cause producers require independent installed-build acceptance; names, timestamps and generic correlation confidence are not proof |
| Recovery assessment | Independent candidate/pending/validated/failed/insufficient results; confirmed recovery links, complete native success, current monitoring, dependency and schedule evidence, configurable observation period | Explicit periodic assessments are required; a gap over 120 seconds restarts observation; successful execution alone cannot restore service |
| Historical reassessment | Sprint 05 eligibility consumed; occurrence/discovery times, associations and separate audit retained; resolved/closed incidents stay closed | Historical notice outbox and delivery policy remain unchanged |
| API and isolation | Existing native incident detail/preview/transition extended; paged failure and assessment evidence; authorized revision/idempotency-protected assessment mutation | No new implicit grants, workload controls or frontend workflow |
| Migration | Additive 0036_native_recovery; immutable failure/assessment records and scoped foreign keys | Populated downgrade refused; conservative retention also protects legal holds |

Verification and exact results: `docs/verification/arch-etl-001-v16-r1/sprint06/REPORT.md`.
RT-001–RT-020 remain NOT RUN. Sprint 07 may consume these backend contracts;
this does not certify native providers or authorize activation/deployment.

### ARCH-ETL-001 V1.6-R1 — Sprint 07

Six scoped operational frontend pages now consume the completed resource, execution,
attempt, schedule, evidence-review, recovery-link and native incident APIs. Existing
session/effective-access resolution, customer/environment isolation and separate
customer Organizations versus employee Departments remain in use. Consequential
forms use explicit confirmation and the backend revision/idempotency contracts.

Validation passed: 13 pipeline cases plus existing permission tests, 10 backend
contract tests, 27 authenticated HTTP groups, the existing configuration browser
workflow and 16 Sprint 07 actual Chromium groups; lint and production build passed.

Exact contracts, final validation, screenshots, limits and Sprint 08 dependencies:
`docs/verification/arch-etl-001-v16-r1/sprint07/REPORT.md`.
Genuine Pentaho RT-001–RT-020 remain NOT RUN; no deployment or source activation.

### ARCH-ETL-001 V1.6-R1 — Sprint 08

Canonical effective access now enforces explicit one/several/ALL customer selection
and additive environment/resource restrictions. Direct roles, department inheritance,
legacy multiple memberships, explicit denies and existing provider break-glass
protections are retained. Delegated Access Management requires an explicit complete
department/customer/permission budget; no existing roles receive implicit grants.
Boundary decisions are audited, immutable, revision/idempotency protected, and
serialized with authorization revocation and protected human decisions. Agent
transport keeps its existing separate service authentication.

Migration `0037_access_boundaries` adds policy and decision tables only; populated
preservation, empty rollback/upgrade, populated downgrade refusal and schema drift
checks passed. The frontend exposes authorized selection and explainable direct,
inherited and restricted access, and clears sensitive state on authorization changes.

Final validation: 155 backend unit/contract tests, 169 actual PostgreSQL tests,
41 authenticated HTTP groups, 20 frontend tests, existing configuration Chromium
workflow, 16 Sprint 07 Chromium groups and 5 Sprint 08 Chromium groups passed.
ESLint, production build, scoped Black/Ruff, compilation/imports and migration
gates passed. Vite's entry-bundle size warning remains; scale/contention testing,
external-client explicit-scope adoption and genuine runtime certification remain
outstanding. RT-001–RT-020 are NOT RUN.

Exact contracts, security acceptance, screenshots, migration safeguards and limits:
`docs/verification/arch-etl-001-v16-r1/sprint08/REPORT.md`.
Sprint 09 requires separate authorization. No PR, merge, deployment, real-source
activation or Pentaho workload execution occurred in Sprint 08.

### ARCH-ETL-001 V1.6-R1 — Sprint 09

Integration hardening preserves the approved architecture and all existing
identities, grants, employee memberships, evidence, histories, holds and source
checkpoints. No schema migration or permission grant was added; head remains
`0037_access_boundaries`.

Inventory and execution projections now batch page-level lookups; resource-scoped
archive pages expose older schedule occurrences, observed steps, attempt revisions
and aliases, integration collections and incident activities with bounded limits
and stable ordering. Server execution/compliance filters and exact incident
failure-association filters are available. Large integration previews explicitly
report incomplete readiness, while authoritative activation is unchanged.
Pipeline agent transport uses its existing separate authentication rather than a
human-only session dependency. Owned raw HTTP/browser clients send explicit
authorized customer scopes; third-party migration requirements are documented.

Verification: 159 backend unit/contract cases, 177 actual PostgreSQL cases,
47 authenticated HTTP groups, 22 frontend cases, existing configuration Chromium,
16 Sprint07, five Sprint08 and three Sprint09 Chromium groups; nine timed
PostgreSQL resilience scenarios. Migration preservation/rollback safeguards/drift,
source fencing, direct/inherited RBAC, revocation and all scoped quality gates are
recorded with exact commands/results. Minimally edited legacy probes retain their
existing Ruff findings with zero introduced diagnostics.

Bounded local performance uses 1,201 resources/five authorized customers and
concurrent read/revocation fixtures; before/after measurements document the removed
inventory N+1 bottleneck. This is not production-scale or native runtime acceptance.
Remaining: third-party/complete legacy-stack migration certification, large/deep
archive contention, process/host failover, the Vite bundle warning, and genuine
Pentaho RT-001–RT-020, which remain NOT RUN.

Evidence and limitations:
`docs/verification/arch-etl-001-v16-r1/sprint09/REPORT.md`.
Sprint10 requires separate authorization. No PR, merge, deployment, real-source
activation or ETL workload execution occurred.


## Sprint 10 — architecture reconciliation and adoption planning

Documentation-only reconciliation against development baseline
`4726fb49b0b7db4d635869648412c9eec40d5572`; no application, architecture baseline,
migration or previous sprint evidence changed. The owner's Sprint 10 instruction
provided continuation authorization; prior acceptance is controlled evidence,
not production sign-off.

[Verification package](docs/verification/arch-etl-001-v16-r1/sprint10/REPORT.md)
contains architecture-to-code/test traceability, exactly 62 improvement rows,
16 candidate rows, six P0/eight P1/two P2 gaps, bounded code findings and a
conditional Sprint 11–42 proposal. Original approved definitions for all 62 IMPs
were not recovered; 54 titles are missing and eight titles come only from the
current owner instruction. All NEW dispositions remain UNRESOLVED pending exact
source comparison. No new candidate or future implementation is approved here.

Production remains NOT READY: real installed-build RT-001–RT-020 are NOT RUN,
and independent runtime/security, trust, PKI, disaster recovery and fleet
validation remain open. Sprint 11 is ready only for explicitly authorized source
recovery/governance; it has not started. No PR, merge, deployment, real-source
activation or ETL workload execution occurred.


## Sprint 11 — source recovery and governance checkpoint

Documentation-only [Sprint 11 report](docs/verification/arch-etl-001-v16-r1/sprint11/REPORT.md)
continues from commit `7b3b3f03bab6f935644d6003973bc6bff60a50ad`.
Status: DELIVERED_WITH_SOURCE_BLOCKERS. A bounded repository/history, GitHub
issue/PR/code and accessible-record search recovered zero original approved IMP
definitions or approval revisions; 62 remain SOURCE_NOT_RECOVERED (54 titles
missing, eight owner-prompt titles unverified against originals). The detailed
original Sprint 11–42 proposal also remains unavailable. All sixteen NEW
candidates are UNRESOLVED_SOURCE_MISSING pending source comparison.
The owner subsequently confirmed both original documents are currently
unavailable; the Sprint 10 roadmap remains a conditional planning proposal.

The conditional Sprint 12–42 plan now maps all sixteen P0–P2 readiness gaps,
all eight audit findings, known title-only IMPs and NEW candidates to decision
and evidence gates. No future implementation is approved by this status entry.
Pentaho RT-001–RT-020 remain NOT RUN, real target acceptance and production
readiness remain blocked, and Sprint 12 has not started. No application code,
architecture baseline, migration, prior verification evidence, PR, merge,
deployment, real-source activation or ETL workload was changed/executed.

## Sprint 14R — bounded remediation verification and UI foundations

[Current Sprint14R evidence](docs/verification/sprint14r/REPORT.md) continues from
verified main `59344c97401340e222627063f7c89bb5e2e89ead`, reusing existing P0/P1
corrections and preserving historical delivery credit. It adds bounded responsive,
keyboard, theme and inventory-table improvements. Approved ARCH-001/ARCH-ETL-001
baselines, backend authorization, schema and native evidence remain unchanged.

[Governance reconciliation](docs/verification/sprint14r/GOVERNANCE_RECONCILIATION.md)
records the owner's Product Alignment/private-network decisions with explicit
provenance. Original ENG-001 and roadmap wording remain incompletely recovered;
full compliance is not claimed. The owner now calls the18 OC-IMP proposals approved;
per-entry revision reconciliation and separately scoped implementation remain open.
The62 original IMP definitions remain SOURCE_NOT_RECOVERED. Shared-resource design,
independent UAT, RT-001–RT-020 and all production release gates remain open.
Production remains NOT READY; no real-source activation or deployment is authorized.
