ARCH-ETL-001 V1.6 — Consolidated Approved Pentaho Monitoring Architecture
Status: OWNER-APPROVED CONSOLIDATED BASELINE — 2026-10-16 (reconstructed from approved discussions; not a verbatim archival transcript)
Scope: Pentaho Data Integration (PDI) monitoring in OpsControl Dashboard
Authority: User-approved Pentaho architecture decisions from design discussions; no modification of those decisions is intended.
Implementation milestone: ARCH-ETL-001 V1.6-R1 (modify shared ARCH-001 and application implementation to comply; do not weaken this Pentaho baseline).
Approved repository destination: docs/architecture/ARCH_ETL_001_V16.md
Change control: Owner approved this consolidated specification for implementation. Do not present it as a verbatim archival transcript. Do not weaken approved goals or decisions; unverified provider capabilities require runtime evidence.
1. Goals, boundaries and non-goals
Deliver trustworthy, self-hosted, customer-isolated monitoring of Pentaho ETL jobs and transformations across Kitchen/Pan command-line execution, Pentaho Server, and Carte, on Windows and Linux, including offline-capable environments. Detect and explain execution outcomes, retry chains, missed schedules, recovery relationships, conflicting evidence, failures, historical discoveries and incidents, with defensible native evidence and auditable operator review.
Monitoring-only: OpsControl must not start, rerun, restart, repair, cancel, or otherwise control ETL workloads. A recovery relationship is an observed/audited association, not permission to execute a recovery. Preserve the current React/Vite frontend, FastAPI/Python backend, PostgreSQL/SQLAlchemy/Alembic persistence, background workers and OpenTelemetry-compatible telemetry approach. Preserve other pipeline platform integrations, existing resources and history, customer isolation, access controls and legal holds.
Tenancy: A customer Organization under Resource Management is a monitored external company; an internal Department under Access Management is a team of service-provider employees. They are never the same entity. All authorization and customer scope checks are enforced server-side. A UI selection never grants access.
2. Architecture and compatibility invariants
1. Pentaho requirements in this document govern Pentaho behavior. Shared ARCH-001 components should be extended/reused; never introduce a parallel canonical execution engine or duplicate customer/resource/incident identities without an approved necessity.
2. Each collection method has a canonical collection identity; exactly one fenced active owner may collect for each canonical collection unit at a time. One Collector can configure multiple collection methods independently. Preserve shared-source behavior, generations, lease/fence epochs, durable checkpoints, and idempotent atomic acceptance.
3. Approved source-level shared-source suspension may affect other enabled integrations, with affected-resource preview. Holds compose; clearing one does not bypass others. Suspended backlog remains held unless separately authorized replay policy permits processing.
4. Preserve platform-native resource classifications (Pentaho job/transformation, Airflow DAG, NiFi processor/process group, ADF pipeline, SSIS package, etc.) within common Data Pipeline inventory. Do not force them into one misleading subtype.
5. Each of nine platform families requires an immutable, version-aware capability profile separating documented support, runtime verification and unknown/unverified capability. Never treat fixture or catalogue entries as live certification.
6. Conflicting native identity claims quarantine ambiguous updates while preserving existing registrations/selections; operator review is required. Manual metadata is preserved during inventory reconciliation.
7. Legal holds prohibit permanent deletion of protected source-owned records and evidence. Safe detach/retire without erasure may proceed where allowed. Actual deletion requires approved release plus normal checks.
8. Existing ARCH-001 eight-stage integration wizard is reused: General; Platform; Connection; Integration; Collection Sources; Job Discovery/Selection; Source Associations; Validate & Activate. Add Pentaho fields within this flow without removing approved functionality. Save/draft is not activation.
3. Logical domain model (design contract; not a migration)
The logical entities are: Customer; Pipeline Definition and platform-native identity; Schedule Configuration and Schedule Occurrence; Logical Execution; Execution Attempt; Evidence and Evidence Association; Identity Registry and Identity Claims; Execution Relationship; Incident Association; Reconciliation Decision; Notification Outbox and Delivery; Legal Hold. These are conceptual boundaries, not instructions to create duplicate tables.
Map them onto existing MonitoringResource, JobOrder, the execution reducer, incident and alert engines, and ARCH-001 pipeline_integrations, pipeline_connections, pipeline_capabilities, pipeline_sources, pipeline_methods, pipeline_jobs, pipeline_associations, pipeline_holds, pipeline_evidence, pipeline_operations where valid. Add schema only for proven gaps, with backward-compatible migrations and explicit upgrade/downgrade safety.
3.1 Identity
Canonical native identity includes customer, platform, environment/authority, stable native job/transformation identity, and relevant invocation or scheduler authority. Maintain an identity registry with immutable aliases and versioned, scoped assignments. Never merge observations merely because names, timestamps, log text or process IDs match. Merge adapter observations only when verified native/scheduler/process invocation identity establishes sameness. PID alone is insufficient without process start epoch/host identity. Ambiguous identities are quarantined and cannot change confirmed execution projections or resource selections. Audited reversible manual recovery links do not bypass identity quarantine.
3.2 Execution and attempt distinctions
A logical execution is distinct from its attempts, schedule occurrence, evidence, incident and recovery relationship. External scheduler/monitoring expectation provides schedule authority; Pentaho status alone must not invent a schedule. Scheduler retries belong to attempts of the same logical execution only when scheduler/native identity proves it. A manually triggered rerun is a distinct logical execution with a linked recovery relationship, never retroactively a successful attempt of the failed execution.
Lifecycle: IDENTIFIED, RUNNING, WAITING_FOR_RETRY, TERMINAL.
Terminal outcomes: SUCCESS, SUCCESS_AFTER_RETRY, FAILED, CANCELLED, UNKNOWN.
WAITING_FOR_RETRY is nonterminal. Verified retry success produces SUCCESS_AFTER_RETRY; verified exhausted/terminal failure produces FAILED. An original failed execution remains FAILED even if a separate manual recovery execution succeeds. Completeness, monitoring health, schedule compliance and execution outcome are independent dimensions. Step visibility and step results are shown only where native evidence verifies them.
3.3 Scheduling
Support per-job timezone, daylight-saving transitions, expected windows, freshness and NO_RUN/missed-occurrence detection using an external schedule authority or an explicitly configured monitoring expectation. Distinguish absent execution from absent telemetry and from unknown schedule. Never manufacture schedule success/failure solely from an unavailable adapter.
4. Adapter contracts and collection
4.1 Kitchen/Pan CLI via OpsControl Agent
Read-only observation of local process invocation context, executable identity, command metadata where safe, process start epoch, process exit, structured/native logs and relevant scheduler identity. Windows and Linux supported as targets. Protect secrets in arguments/logs; avoid raw command-line credential exposure. An exit code alone is not proof of remote downstream outcome or scheduler retry authority. The scheduler, where present, owns authoritative retry grouping. Agent registration and authenticated transport use customer/resource binding. Initial installation may be manual/offline; optional remote push/installer is future scope and not assumed present.
4.2 Pentaho Server
Use authorized, read-only repository/scheduler/execution-history surfaces. Distinguish scheduled trigger status from verified underlying ETL execution result. Scope identity to server, repository/environment and native execution IDs; never assume every Server version exposes the same endpoints or history granularity. No write/control API operations.
4.3 Carte
Allowlisted, verified read-only GET status endpoints may include /kettle/status, /kettle/jobStatus, /kettle/transStatus, subject to exact-build behavior and authentication. Scope execution IDs by server/restart epoch; IDs may be recycled across restarts. Carte running-status inventory is not a persistent authoritative job catalogue; use manually registered stable native identities when required. Do not call start/stop/remove or other control endpoints.
4.4 Version and capability gating
Declare exact installed build and evidence-backed capabilities independently per method. Version families such as Pentaho 10.2.x/11.0.x are candidates, not certified versions. Where one capability is unavailable, continue verified eligible monitoring methods with explicit limitations, rather than claiming full parity or disabling all methods unnecessarily. An unverified method cannot be marked certified or activated as if accepted. Retain documented, runtime-verified and unknown states separately.
5. Evidence, reconciliation and durability
Use append-only evidence and append-only execution state revisions, with deterministic current projection. Durable raw evidence includes provenance, native IDs, observed time vs event time, source/generation, method, hash, acceptance and audit metadata. Payloads are protected in a self-hosted durable store, and acceptance acknowledgments are recorded. Atomic acceptance must bind evidence/idempotency/projection/checkpoint under the current fenced owner and source generation; stale owners cannot commit.
Evidence precedence is claim-specific (e.g., an authenticated scheduler may establish retry intent while native execution history establishes actual outcome); no single source has universal precedence. Reconcile claims by identity, provenance, relevance, verification and authority. If equally applicable verified claims contradict one another, mark CONFLICTED_EVIDENCE, quarantine the disputed claim and preserve the last defensible verified projection rather than overwriting it with arbitrary arrival order. Flag uncertainty visibly and require authorized review. A conflict is not automatically FAILED or SUCCESS.
Late evidence may revise historical understanding by appending an event-time state revision, never rewriting original evidence. Maintain discovery/processing time separately from historical occurrence time. Legal holds extend to protected revisions, evidence associations, incident links and notification records.
6. Replay, suspension and continuity
Live collection takes priority over bounded recovery. Replay uses its own cursor and durable operation tracking; it cannot silently advance the live cursor or bypass fence/hold checks. Suspended backlog remains held unless approved policy authorizes its processing. All recovery must be bounded, idempotent, auditable and source-generation-aware. Where a provider cannot establish continuity or bounded replay, fail closed and report the limitation; never claim restored monitoring based on an HTTP health check or a fixture.
Existing ARCH-001 defaults currently include automatic recovery limits of 6 hours for File Log and 24 hours for platform/database methods, with independent approval beyond bounds. These are shared implementation defaults to preserve unless an approved Pentaho-specific requirement expressly supersedes them. Existing backend bounded replay is only proven for certain supported provider ranges; do not claim Pentaho backend replay is implemented or certified without evidence. Rotation/truncation, server restart and source remapping require continuity proofs or reviewed generation transitions.
7. Incident correlation and recovery validation
Verified related failures may associate with one eligible active incident when a common-root relationship is supported; each failed execution retains its own immutable failure record. Correlation confidence is not proof of causality. A resolved/closed incident must not silently reopen when historical evidence arrives; instead create an auditable reassessment/new action according to incident policy.
Late verified historical failures require an idempotent historical-failure notification through the existing notification infrastructure, with event occurrence and discovery times clearly distinguished, subject to evidence and replay eligibility. Prevent duplicate sends on replay. Recovery linking is an observed association, not proof of restoration.
Reuse the existing incident engine and its native lifecycle (Open → Acknowledged → Investigating → Recovery in Progress → Monitoring → Resolved → Closed) while satisfying the approved Pentaho behaviors. Before declaring restoration, require fresh verified healthy execution/monitoring evidence, successful expected workflow outcome, downstream dependency checks where observable, a stable observation window, and recorded evidence/actor/audit trail. Do not auto-close solely on a recovery link, alert reset or isolated green sample.
8. Access Management and customer scope
Internal IT admins may manage delegated departments, employees, configurable roles and permissions, with server-enforced authorization. Roles may be inherited through departments and assigned directly to employees; effective access must explain source of grant, role, customer/environment/resource scope and explicit restrictions/denies. Creating a department or employee does not confer privileged access. Prevent last-administrator lockout. Ordinary delegated admins cannot grant platform-administrator break-glass or authority beyond their own delegation. Executable permission keys require backend enforcement, not merely UI labels.
Per-action customer scope may select one customer, several customers, or ALL customers. ALL is an elevated, explicitly granted permission and must define coverage of future customers; it is never inferred from a UI filter. No selected customer means no access. Preserve immutable customer IDs. Identity resolution and replay approval require separate granular, audited privileges. Main currently restricts new employee assignment to one department while retaining legacy multiple memberships; the approved Pentaho access model requires department inheritance and direct roles, and must not be weakened. Approved resolution: every newly created employee is assigned exactly one department. Existing employees with legacy multiple department memberships retain those memberships and their valid inherited access; do not destructively migrate or silently remove them. Direct employee roles remain supported.
9. Operational UI contract
Use existing navigation rather than competing resource modules:
- Resource Management → Data Resources → Data Pipelines: inventory, Pentaho integration onboarding, collection methods and source associations; customer Organizations remain separate from internal departments.
- Data Pipeline Monitoring: Pipeline Inventory, Execution History, Schedule Monitoring, Evidence Review, Recovery Tracking and Incident Correlation as pages/tabs consistent with the existing information architecture.
- Execution details drawer: Attempts, Evidence, Steps, Incidents, Audit. Show only verified step data and visibly distinguish missing/unverified evidence.
- Evidence Review: a dedicated operator queue for identity conflicts and separate relationship-link review, with granular permission gates, decisions, provenance and audit.
- Recovery monitoring: backlog, holds, source generation/epochs, gaps, live/replay cursors, evidence and notification status; explicit unsupported/blocked states.
- Access Management: Departments, Employees, Roles & Permissions, Customer Access/Organizational Access, Effective Access and Access Audit, harmonized with current Main navigation.
Dense inventories use list/table layouts; keep actions in page headers, preserve responsive boundaries and collapsible sidebar behavior. Do not expose a Run ETL button.
10. Retention, audit and legal holds
Use ARCH-001 shared retention defaults unless the owner approves a different Pentaho-specific retention policy: raw evidence 30 days, audit at least 365 days, and existing stale-item/cursor cleanup rules. Retention is configurable only within approved security/legal policy. Holds prevent deletion of protected source-owned records, execution revisions, evidence, associations, incident and notification records. Detach/retire is permissible only without protected erasure; deletion requires approved hold release and normal safety checks. Keep append-only audit for privileged actions and administrative changes.
11. Acceptance and certification
Architecture acceptance and runtime certification are separate gates. No runtime certification is implied by this document, code review, mock tests, static adapter profiles, screenshots, HTTP connectivity or catalogue entries. Real installed builds, genuine native evidence, exact reader/source generation, capability attestation and independent approval are required before calling a capability runtime-certified. Existing ARCH-001 acceptance is disabled by default and uses an independently approved workflow (including OPSCONTROL_PIPELINE_RUNTIME_ACCEPTANCE=1 where applicable).
The approved design included a 20-scenario P0 acceptance plan RT-001 through RT-020, with zero tests executed at baseline approval. The original per-scenario wording is not available in the present record; the matrix below is a proposed reconstructed coverage index, NOT a claim that these are the verbatim approved RT descriptions. The exact original scenario wording is not required for implementation. Treat the following reconstructed matrix as the R1 working acceptance coverage index, not as verbatim historical wording:
ID	Proposed coverage (requires owner confirmation)
RT-001	Kitchen/Pan verified native invocation and identity
RT-002	Pentaho Server read-only history and result authority
RT-003	Carte GET status and restart-epoch identity
RT-004	Exact-build capability verification and unsupported features
RT-005	Independent collection method ownership/fencing
RT-006	Conflicting identity quarantine, existing selection preserved
RT-007	Scheduler retry attempt grouping
RT-008	Verified retry success → SUCCESS_AFTER_RETRY
RT-009	Terminal failed execution remains FAILED after manual recovery
RT-010	WAITING_FOR_RETRY remains nonterminal
RT-011	Timezone/DST and missed schedule occurrence
RT-012	Claim-specific evidence precedence
RT-013	CONFLICTED_EVIDENCE preserves last verified projection
RT-014	Late historical failure revision and notification deduplication
RT-015	Active-incident correlation without asserted causality
RT-016	Incident recovery observation and downstream verification
RT-017	Suspension holds, backlog and authorized bounded replay
RT-018	Legal-hold protection of revisions/evidence/notifications
RT-019	Cross-customer isolation and granular delegated RBAC
RT-020	UI evidence/recovery review and audit traceability


For every test: capture native source, exact build, method, customer, source generation, expected/observed outcome, evidence hashes, run timestamp, environment, reviewer, pass/fail/blocked and any waiver. Do not mark blocked or mocked tests as passed.
12. Approved V1.6 decision register (reconstructed from approvals)
ID	Binding decision
A1	Exact Pentaho version/build and verified capabilities
A2	Continue eligible verified methods with limitations when other capabilities unavailable
A3	Merge adapter observations only with verified native identity
B1	Preserve last verified state and flag conflicting evidence
B2	Late historical failure notification and incident reassessment, no automatic reopen
B3	Hold suspended backlog unless replay policy explicitly approved
B4	Group verified common-root failures in eligible active incident while preserving distinct failures
C1	Data Pipelines/ETL operational navigation
C2	Execution drawer: Attempts, Evidence, Steps, Incidents, Audit
C3	Dedicated Evidence Review queue
D1	Delegated IT administrators for access management
D2	Selected one/several/ALL customer access, ALL elevated
D3	Department-inherited plus direct employee roles and effective-access explanation
D4	Granular audited privileged identity/replay operations
D5	Formal architecture sign-off after authoritative reconciliation; runtime certification independent


Approval history: The 15 V1.6 decisions were approved. The logical model V1.2, adapter contracts V1.3, reconciliation/state/incidents/replay V1.4 and P0 acceptance design preceded V1.6. Their exact original document text is not reproduced here unless independently recovered. No original objectives or goals are intentionally altered.
13. ARCH-001 implementation reconciliation (change Main, not this Pentaho baseline)
REC	Required Main-side disposition
01	Reuse/extend eight-stage wizard with all Pentaho configuration requirements
02	Extend existing MonitoringResource/JobOrder execution engine; avoid duplicates
03	Add proposed CLI, Server and Carte capability contracts; certify separately
04	Add conflict-safe last-verified execution projection
05	Add historical-failure outbox/idempotent notification behavior
06	Extend existing incident engine to meet Pentaho semantics
07	Extend delegated RBAC with backend permission enforcement and restrictions
08	Implement one/several/ALL customer grants securely
09	Enforce exactly one department for new employees; preserve existing legacy multiple memberships and direct roles without destructive migration
10	Keep evidence retention, append-only audit and legal holds
11	Require exact-build independent genuine runtime certification
12	Do not promote correlation into asserted causality


14. Open verification items — do not silently invent
1. RT-001–RT-020: reconstructed coverage index accepted for R1 planning; exact historical wording is not a blocker. The 20 cases remain unexecuted until tested.
2. Employee departments: resolved — exactly one department for new employees; preserve existing legacy multi-department memberships and effective permissions.
3. Original text completeness: the consolidated reconstruction is owner-approved as the implementation baseline, but it is not a verbatim archival transcript of the earlier V1.2–V1.6 discussions.
4. Provider-specific API shapes, installed-version matrices and retention exceptions: require evidence/approval; do not invent endpoint support or certifications.
5. Production/runtime acceptance: zero Pentaho P0 runtime tests are evidenced as executed here; no merge/deploy authority.
15. Approval and publication gate
The owner approved this consolidated architecture for implementation on 2026-10-16, including the reconstructed RT-001–RT-020 coverage index and exactly one department for new employees while retaining legacy multi-department memberships. Publish this owner-approved consolidated baseline on the R1 development branch and use it as the Pentaho-specific source of truth. Do not modify its objectives or approved decisions. Do not merge or deploy without separate approval.

## Excluded platforms

Kubernetes, EKS, AKS, GKE, OpenShift and other Kubernetes distributions are REMOVED_FROM_SCOPE by OC-SCOPE-REM-001. Legacy database records and historical audit evidence are retained; this is not release acceptance. Standalone VM/EC2, applications, ETL/Pentaho and API monitoring remain in scope.
