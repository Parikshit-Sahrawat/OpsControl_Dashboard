# Next five development sprints — proposed, not started

No calendar commitments or capacity estimates are invented. These are dependency-ordered candidate scopes, not a promise to complete all55 items in five time boxes. S/M/L/XL estimates are relative. Owners must size/split XL work before authorizing a sprint; an ID closes only on its complete backlog acceptance criteria, never on a partial milestone. P0 security, preservation and global-performance work begins early and can span slices. External qualification/formal UAT are separately planned, not executed here.

## Sprint 1 — Secure resource → template/configuration baseline and global responsiveness evidence

- Included IDs: OC-DEV-103, OC-DEV-105, OC-DEV-106, OC-DEV-121, OC-DEV-135, OC-DEV-201, OC-DEV-501, OC-DEV-503, OC-DEV-123.
- Dependencies: No external provider dependency for scoped synthetic fixtures.201 must establish transaction detail before101.501 is review, not an automatic merge.
- Coding deliverables: One canonical resource/method configuration path, preservation regressions and representative global performance reproduction; current publication failure understood or explicitly blocked.
- Automated deliverables: Authenticated create/edit/reload/denial, effective template/config comparison, query/latency/receipt baselines under task-owned ingestion, fresh/populated migration refusal/restore.
- Regression scope: Resource/RBAC/VM ownership/API hydration/removed-platform boundaries.
- Exit criteria: Controlled end-to-end configuration behaves correctly, no tenant leak/data loss or fake health; global symptom is measured or remains unresolved; no publication bypass.
- Expected remaining blockers: CHK001/002, security/legal, genuine providers, missing owner policy and all formal UAT remain.

## Sprint 2 — Source identity → durable admission → host/collector lifecycle

- Included IDs: OC-DEV-101, OC-DEV-102, OC-DEV-107, OC-DEV-114, OC-DEV-115, OC-DEV-117, OC-DEV-136.
- Dependencies: 201 detail and103.101/107 boundaries are explicit; real OS qualification302 is separate.
- Coding deliverables: Reviewed central PG durable-spool implementation, receipt provenance, one-time onboarding→central administration, bounded Linux/Windows packaging and VM evidence projection.
- Automated deliverables: Crash/capacity/restart/replay accounting, source generation/ownership, installer/service negative cases, same collector/revision/history reload.
- Regression scope: All Sprint1 contracts, retained collector0.123.0 pin, backup/restore and real HTTP negative cases.
- Exit criteria: Zero undetected loss within the demonstrated admitted boundary, explicit duplicate counts and unsupported limits; no source/reader reattribution or re-enrollment loop.
- Expected remaining blockers: Upstream pre-admission durability and checkpoint qualification306, genuine OS/provider302, independent certification remain.

## Sprint 3 — Telemetry → alerts/incidents → notifications and scoped operational views

- Included IDs: OC-DEV-108, OC-DEV-109, OC-DEV-110, OC-DEV-116, OC-DEV-118, OC-DEV-119, OC-DEV-120, OC-DEV-205, OC-DEV-206, OC-DEV-502.
- Dependencies: 107 and policy205/206 for their exact behaviors; existing supported channel contracts reusable.
- Coding deliverables: Evidence-backed incidents/recovery, supported email/in-app delivery, scoped dashboards/reports and reproducible freshness/coverage.
- Automated deliverables: Stable expected IDs/counts, threshold/recovery, stale/missing signals, revoked recipients, retries/duplicate delivery, browser drilldowns and report exports.
- Regression scope: API HEAD/latency/header persistence, tenancy, method ownership, incident history, responsive mounted/browser cases.
- Exit criteria: Persisted source evidence matches displayed counts/outcomes; no missing-data success or unauthorized recipients; unsupported policy remains blocked.
- Expected remaining blockers: Retired PagerDuty/ServiceNow conflict, real delivery providers and formal UAT remain distinct.

## Sprint 4 — Workflow configuration → native evidence → ETL event/readiness projection

- Included IDs: OC-DEV-125, OC-DEV-126, OC-DEV-127, OC-DEV-128, OC-DEV-129, OC-DEV-130, OC-DEV-131, OC-DEV-204, OC-DEV-207, OC-DEV-301.
- Dependencies: 204/207 exact policy;501 foundation;301 authorization for genuine positive proof. If not available, positive native items remain BLOCKED, not simulated PASS.
- Coding deliverables: Only approved calendar/threshold/event policy and read-only source mapping; exact immutable binding/receipt/cutover safeguards; authoritative readiness UI.
- Automated deliverables: Existing002–008 regression baseline plus Q01–Q08 when genuinely authorized; DAG concurrency; temporal history and migration guards.
- Regression scope: Resource/Access, pipeline ownership, old-writer fence, UI persistence, monitoring-only prohibitions.
- Exit criteria: Approved behaviors implemented and tested; absent provider/authority classified explicitly; no Run/Retry/Stop/scheduler control.
- Expected remaining blockers: D07/D08/catalog/source identity until supplied; genuine certification, active cutover and operational rollback until proven.

## Sprint 5 — Authorized settings/profile and installation lifecycle acceptance candidates

- Included IDs: OC-DEV-104, OC-DEV-111, OC-DEV-112, OC-DEV-113, OC-DEV-122, OC-DEV-124, OC-DEV-132, OC-DEV-134, OC-DEV-202, OC-DEV-203.
- Dependencies: 202/203 for new fields/licensing;132/123/503 and target prerequisites for installation; no deployment authorized by this audit.
- Coding deliverables: Contract-limited settings/profile/access UX, compatible rollback candidate, immutable installation evidence and licensing only after exact authority.
- Automated deliverables: Allowlisted settings/auth/audit/reload; stale sessions; responsive keyboard cases; restore/old-writer refusal and isolated controller crash/rollback.
- Regression scope: All preceding critical paths, retained migration/audit data, no retired platform/integration restoration.
- Exit criteria: Technical candidate evidence complete for implemented subset; independent303–306 and owner401/402 remain separate; no automatic Stage/release promotion.
- Expected remaining blockers: Licensing authority, independent security/DR/provider qualification and formal UAT; release stays NO-GO until all established gates pass.

**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**

