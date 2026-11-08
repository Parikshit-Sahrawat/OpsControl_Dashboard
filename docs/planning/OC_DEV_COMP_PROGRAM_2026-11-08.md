# OpsControl Development-Completion Program — Owner-Approved Execution Plan

**Program ID:** OC-DEV-COMP | **Version:** 1.0 | **Recorded:** 2026-11-08
**Status:** Approved for sprint-by-sprint development; not implemented or certified by this document.
**Starting reviewed main SHA:** `ffe5ac285ab8aef33a1139bce6f3da79be3d6d33` (reverify `origin/main` before execution).
**Integration policy:** Develop on isolated sprint branches/worktrees, reconcile into a development integration branch, and merge to `main` only at the final development-completion checkpoint with explicit owner approval. No intermediate sprint merges to `main`.
**Formal UAT:** Starts after development-completion review; do not mistake automated development evidence for formal owner UAT.

## Authority and provenance

The product owner approved this program and the mandatory testing policy in the OpsControl ChatGPT conversation. AUTH-694 was selected as option A in Round 110; its original repository/GitHub approval artifact has **not been recovered**. Track approval as `APPROVED_BY_OWNER_IN_CONVERSATION`, original repository provenance as `SOURCE_NOT_RECOVERED`, and implementation/certification separately as `NOT_VERIFIED`. This record does not purport to reproduce an independently recovered original AUTH-694 artifact. The owner-provided AUTH-694 summary requires versioned authority reconciliation against 31 included journeys, 14 closure steps, scope/supersession, evidence, dependencies, UAT and independent gates. Do not invent unrecovered journey definitions or exact step labels.

See [existing completion register](DEVELOPMENT_COMPLETION_REGISTER.md) and [PRD](../sdlc/04-PRD.md). Older registers may contain superseded capabilities; preserve their history, and record conflicts rather than silently changing behavior in Sprint 0.

## Approved scope

**Included:** Windows/Linux host, process and service metrics; user-selected running-process monitoring; live/current utilization and status; historical charts with selectable time ranges and aggregation/frequency; API monitoring; read-only Pentaho ETL; Email/PagerDuty; background alert lifecycle, correlation, recovery and notifications; multi-organization controls; centralized PostgreSQL-backed transactional durable spool (design approved, implementation and certification outstanding).

**Excluded:** ServiceNow integration; incident-management UI (background alert processing remains included); SFTP monitoring; cloud object storage/S3 monitoring; Kubernetes/EKS/AKS/GKE/OpenShift **workload monitoring** (OpsControl deployment on Kubernetes remains permitted); Pentaho execution/mutation controls.

Preserve AUTH-491=B and AUTH-495=C: local resolution does not establish provider-verified external closure; do not display or assert external closure status as verified. Pentaho raw logs default to seven days after completion, with prompt disposal of unrelated data, minimized longer-term structured evidence and governed legal holds/deletion.

## Mandatory development test policy — effective immediately

Every applicable sprint must run, record and review:
1. Backend/frontend unit and contract tests.
2. **Real PostgreSQL** integration with actual schema/migrations, transactional, persistence, concurrency and tenant-isolation checks.
3. Running **real FastAPI and React/Vite application components** over actual HTTP interfaces; Playwright browser workflows against the integrated application.
4. Security checks: authentication, authorization, tenant isolation, dependency/image vulnerability scans, secrets exposure and applicable supply-chain checks.
5. Controlled fault injection where applicable: crashes, restart, queue replay, backpressure, partial failure, duplicate delivery, recovery, and failure accounting.
6. Collector/provider integration tests using real component boundaries where the contract is being certified; genuine external-provider qualification remains separately labeled.
7. Reproducible evidence per exact source commit: commands, versions, environment, logs, results, failures, skips, artifacts and hashes.

Mocks and synthetic fixtures are allowed for isolated tests, **never as substitutes for real-component integration certification**. Unavailable, skipped, mocked-only or non-reproduced checks cannot be reported as passing end-to-end certification. No unexplained failures or silent waivers. Evidence collection is mandatory during development, not deferred to formal UAT.

## Sprint sequence and required outputs

| Sprint | Scope | Required exit evidence |
|---|---|---|
| **0 — OC-DEV-COMP-000** | Reverify main; inspect draft PR #80/#81/#82; recover/register authority source gaps; reconcile 31 journeys and 14 steps without inventing definitions; identify excluded-code conflicts; establish automated test baseline and integration branch strategy. No operational behavior changes. | Exact baseline SHA; PR reuse/conflict report; authority/provenance register; gap/backlog matrix; actual baseline tests and skips; Sprint 1 recommendation. |
| **1** | Resource Management: organizations, compute instances, template applicability, configuration/version history, persistence, RBAC and workflows. | PostgreSQL migration/preservation, real API and Playwright, concurrency and tenant-negative tests. |
| **2** | Windows/Linux collector installation, secure enrollment, configuration activation, lifecycle, health, upgrades/rollback. | Real component/package and OS-specific tests; identity/security/restart evidence. |
| **3** | Telemetry ingestion and centralized PostgreSQL durable spool: transactional completion/ack, deduplication, replay, recovery, schema compatibility. | Fault-injection durability matrix, real DB queue/restart/replay, loss accounting, load and idempotency evidence. |
| **4** | Windows/Linux host metrics, process/service inventory, selected-process monitoring and live status. | Real agents and application component tests; process lifecycle and tenant isolation. |
| **5** | Historical resource monitoring: time ranges, sample frequency/aggregation, retention, charts, freshness and drilldowns. | Time-series PostgreSQL/API/browser tests and bounded load/freshness evidence. |
| **6** | API monitoring and read-only Pentaho execution/status/history/evidence. | HTTP/TLS checks, provider boundary tests, read-only negative tests and provenance/retention evidence. |
| **7** | Background alerting, correlation, recovery, Email and PagerDuty delivery/retry/idempotency. | Real persistence, fault/retry tests, alert-state invariants and transport qualification distinctions. |
| **8** | Operational frontend, overview, monitoring pages, reports, administration, accessibility, responsive UX. | Full browser regression, keyboard/accessibility and scoped KPI/list consistency. |
| **9** | Security, reliability and performance hardening, tenant isolation, backup/restore, vulnerability remediation. | Reproducible scans, real PostgreSQL restoration, security negatives, load and recovery evidence. |
| **10** | Full development closure, integrated regression, traceability, artifacts, final integration candidate and owner review. | All development acceptance criteria satisfied or blockers explicitly reported; explicit owner approval required before merge to main. |

Sprint labels are planning labels, not assertions that the original 14 canonical closure-step names have been recovered. Each sprint ends at a review checkpoint; do not auto-start the next sprint without authorization.

## Per-sprint Codex execution contract

- Verify target branch and baseline SHA; use isolated branch/worktree; do not silently rewrite prior evidence.
- Map approved requirements to code changes, tests, data migrations and negative cases.
- Implement only the approved sprint scope; test real integrated components; record exact results and known limitations.
- Update a versioned requirement-to-journey-to-step traceability and evidence register; preserve historical excluded/superseded items.
- Commit sprint work with exact SHA and provide changed files, CI/test report, failures/skips, remaining blockers and next-sprint dependencies.
- Do not deploy, begin formal UAT, merge to `main`, or claim release readiness from sprint completion.

## Independent gates — unchanged until separately certified

| Gate | Current authority-preserved state |
|---|---|
| CHK-001 persistent-queue durability | **FAIL** |
| CHK-002 | **BLOCKED** |
| Security | **BLOCKED** |
| Production release | **NO-GO** |
| Formal owner UAT | **PENDING** |
| Development closure | **NOT COMPLETE** |

Design approval of the PostgreSQL-backed spool does not close CHK-001/CHK-002. No authority decision or green unit test substitutes for end-to-end completion and durability evidence. Security and release gates require separate evidence and authorized decisions.

## Sprint 0 / AUTH-694 registration task

Register AUTH-694 in the existing canonical authority system if found, preserving: `option=A`, `round=110`, `approval=APPROVED_BY_OWNER_IN_CONVERSATION`, `repository_original_source=SOURCE_NOT_RECOVERED`, `implementation=NOT_VERIFIED`, `certification=NOT_CERTIFIED`, `formal_owner_UAT=PENDING`. The owner-provided decision is versioned product-authority reconciliation with independent implementation, evidence, UAT and release gates. Do not fabricate the original source text, source URL, approval timestamp or GitHub comment. Do not alter product behavior in Sprint 0.

**Next action:** Codex executes OC-DEV-COMP-000 using this plan; stops after Sprint 0 with evidence and readiness assessment. This document is a planning record, not evidence that Codex execution has started.
