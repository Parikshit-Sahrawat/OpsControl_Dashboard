# OpsControl 10-Sprint CI/CD Modernisation — Audit and Implementation Contract v1

**Recorded:** 2026-11-08 | **Status:** Proposed workflow refactor for owner/Codex review, NOT implemented by this document.
**Basis:** Owner-approved OpsControl Development Completion 10-sprint roadmap, mandatory real-component tests, included/excluded scope and preserved release blockers. Source snapshot: main `ffe5ac285ab8aef33a1139bce6f3da79be3d6d33`; PR #84 `cbbaec54ea74139f51b1d75a26ce91378f89a298`. Reverify workflow files and moving branches before implementation. This document is authored on an **isolated documentation branch** and must not be merged into main during intermediate sprints.
**Critical distinction:** Excluded-product *positive functionality* need not be certified, but **negative security, scope-removal, historical data preservation and denial tests remain mandatory**. Do not skip a shared test executable merely because its name or fixture mentions excluded features; inspect its assertions first.

## 1. Current workflow observations from repository (not implementation claims)

- `.github/workflows/validation.yml` runs full backend unittest and frontend npm test/build on PR/main, without a complete real PostgreSQL/migration/browser gate in that workflow.
- `.github/workflows/security-validation.yml` runs pip-audit on requirements, npm audit `--omit=dev --audit-level=high`, and gitleaks; this is not complete SBOM/image/license/release proof.
- `.github/workflows/phase1-staging.yml` is named **OpsControl Security Release Gate**, but uses historical staging/phase-1 test sequences, including `provider_unit_probe.py` described as "EC2, Kubernetes and Pentaho ... offline fakes". Inspect and split assertion scope. Don't remove the retired-Kubernetes rejection tests.
- `.github/workflows/operational-acceptance.yml` also invokes `provider_unit_probe`; `.github/workflows/pipeline-v16.yml` runs protected regression module `tests.test_native_incidents_v15` that may contain historically useful background-alert/retirement regressions. Inspect actual assertions before suppressing it.
- `.github/workflows/v15-quality.yml`, `arch001-native-monitoring.yml`, `access-architecture.yml`, and `operational-acceptance.yml` each repeat unit/frontend and some expensive integrated testing. Preserve coverage first; only deduplicate after equivalence is proven.
- `scripts/check-workflows.sh` invokes checksum-verified actionlint for a hard-coded **subset** of workflow files. Expand to all `.github/workflows/*.yml/*.yaml` and lint new workflow policies, with bounded opt-outs for genuine syntax constraints.
- `.github/workflows/local-uat-image-validation.yml` builds images and checks entrypoints without deployment, a useful PR check.
- `.github/workflows/local-uat-auto-deploy.yml` **publishes UAT images/release assets on push to main** (guarded by `verify_publish.py`); this is not a production deployment but must remain separately gated while the owner forbids intermediate main integration and formal UAT. Reassess trigger and release-approval policy, never relax.
- `.github/workflows/stage-b-uat.yml` contains highly privileged self-hosted deployment operations behind approval and environment guards. Keep manual/disabled until UAT phase; never enable by CI refactor.
- `.github/workflows/release-reliability.yml` tests non-root images, restore/retention/TLS, but a green job does not clear CHK-001/CHK-002 or certify the centralized PostgreSQL spool.
- Current pinned OTel contrib guard `0.123.0` is independent of future collector/spool implementation; don't silently upgrade or downgrade.
- Historical tests might exercise old ServiceNow, incident, EKS, SFTP or S3 code. *Positive* certification must be removed from product acceptance; *denial/retirement/migration/compatibility* tests must remain until safe retirement verified.

## 2. Authoritative product scope

**Positive feature verification only for approved capabilities:** Organizations/multi-org/tenant RBAC; Resource Management, templates and configuration revision/history; Windows/Linux host/process/service collectors; central PostgreSQL spool and recovery; real metric/log evidence; API and HTTP/TLS monitoring; **read-only** Pentaho ETL; background alerts/correlation/recovery; Email/PagerDuty notifications; Reports/Trends; role-aware desktop frontend; self-hosted packaging for Kubernetes **deployment**, Windows Server service and Linux Server service.

**Excluded positive functionality:** ServiceNow ITSM/incident creation; incident-management UI; SFTP monitoring; cloud object storage/S3 monitoring; Kubernetes/EKS/AKS/GKE/OpenShift **workload** monitoring; Pentaho job execute/stop/mutation. Deployment on Kubernetes remains explicitly allowed. Historical backup/migration/denial regression remains in scope as protective verification.

**Do not mechanically delete or disable tests based on matching a name such as "incident", "kubernetes" or "S3"**. Inspect intent: an `incident` test may assert prohibited incident UI is absent, or validate retained background alert evidence. An EKS test may prove retired discovery is denied. Tests for AWS EC2 **compute/VM** monitoring must be independently classified from Kubernetes/EKS workload monitoring; do not assume all AWS checks are excluded.

## 3. Target CI tier architecture

| Tier | Event | Purpose | Mandatory outcome |
|---|---|---|---|
| **A: PR fast / always** | every PR incl docs and workflow changes | actionlint on ALL workflow files; approved scope policy; secrets; Python JS lint/compile; frontend tests/build; backend focused/unit regression; authority/schema/document validation; workflow-permission/trigger checks | No unknown test omission. Stable required check names. Docs-only PRs still exercise scope/security/CI policy; optimized expensive tests may be path-aware ONLY if trustworthy and never skip required check itself. |
| **B: PR integrated / changes requiring runtime** | every development PR, with changed-path matrix for added depth | Disposable **real PostgreSQL 17** migration + populated restore; actual FastAPI + React/Vite + Chromium Playwright; source-owned revision, all-writer concurrency, tenant/RBAC revocation; collector/API/Pentaho mocked/real boundary correctly labelled | A mandatory baseline integrated suite runs for every development PR. Additional feature-specific suites use proven path mappings; unknown paths fail closed into broad coverage. |
| **C: PR security + artifacts** | each PR | pip/npm vulnerability scans for locked runtime + build/development graphs, action pinning, secret scans, SBOM and image scanning when Dockerfiles/dependencies/runtime change; package/version/license provenance; redact and hash evidence | Scanner failures must not be hidden via blanket continue-on-error. Distinguish installed-toolchain issues from production image findings. Open vulnerabilities maintain SECURITY BLOCKED. |
| **D: Nightly / manual stress** | scheduled/manual restricted to non-secret disposable runners | OTel/central PostgreSQL spool crash/restart/ack/replay/dup matrix, prolonged load, OS-agent packaging and compatibility where infrastructure available; historical migration upgrade/restore; audit/retention | Missing pinned Contrib binary/real providers = `NOT_TESTED` / `BLOCKED` in evidence. Do not claim positive pass because optional jobs were skipped. Nightly failures generate auditable issues/actions but don't silently mutate release gate. |
| **E: Sprint exit candidate** | manual/ref-pinned for each sprint in isolated branch | All required A–D applicable suites, exact artifact hashes, acceptance mapping, no unexplained skips, review owner decisions; certify only bounded sprint scope | Sprint acceptance is independent of green GitHub job; cannot auto-merge into main. |
| **F: Release / formal UAT** | ONLY after Sprint 10 + explicit approvals | full matrix, Windows/Linux/Kubernetes deployment-packaging checks, security/SBOM/licence approval, CHK-001/002 closeout, qualified collector/provider evidence, signed immutable image digest, independently approved backup/migration/rollout | No automatic publish/deploy or release status from PR success. `main` publishing guard must require an approved release/UAT-change record and exact commit; self-hosted deploy remains disabled outside formal UAT. |

Stable check names should be **scope-policy**, **unit-and-build**, **real-postgres-migration**, **app-api-browser**, **security-sbom**, **sprint-evidence**, **release-readiness** (release-only). Do not require skipped optional feature jobs as evidence of a pass.

## 4. Sprint-to-CI focus

| Sprint | Specific additional mandatory evidence |
|---|---|
| **0** | Owner-approved scope, authority provenance, traceability, initial security and test baselines. Historical gaps remain explicitly flagged. |
| **1** | Real PostgreSQL revision ledger/applicability validation, attachment/detach/override history, all-writer concurrency + atomic multi-step save rollback, authorisation, browser admin/operator resource workflows, migration/restore. |
| **2** | Windows/Linux agent installers, binary integrity, secure registration, collector OS/runtime compatibility, revocation, restart, configuration confirmation. |
| **3** | PostgreSQL durable spool transactions, queue crashes/acks/replay/backpressure, zero unexplained losses/duplicates, replay and idempotent completion contract; CHK-001/002 remain independent gate. |
| **4** | Windows/Linux host CPU/memory/disk/network/process/service metrics, PID lifecycle identity, selected process monitoring, real collector/API/browser freshness, state accuracy. |
| **5** | Historical retention, aggregation, sampling/timezone, gaps, process/service time-series, bounded real DB API/UI load. |
| **6** | API HTTP/TLS and read-only Pentaho native observation, provider auth/negative mutation, seven-day raw-log retention defaults, preserve structured long-term evidence and holds. |
| **7** | Background alert transitions, notification lease/retry/idempotency, Email/PagerDuty delivery and suppression, correlation, recovery, no ITSM/inactive incident management reentry. |
| **8** | Desktop 1920/1440/1366 screenshots and keyboard/ARIA/table/filter/route/favorites regression; all authorized controls work; keep role-scoped differences. |
| **9** | Production representative image/SBOM/licence/vuln scanning, tenant/offline/egress hardening, DB backup restore, performance, durability capacity/restart and provenance. |
| **10** | Full integrated regression, all 31 included journeys as source recovers (missing source stays `SOURCE_NOT_RECOVERED`), 14 closure steps, nine owner acceptances separately, exact merge candidate and independent gate decisions. |

## 5. Excluded-capability verification rules

For each test/check, classify from actual assertions as:
- `INCLUDED_POSITIVE`: may be required for approved feature certification;
- `EXCLUDED_NEGATIVE`: **must retain** denial, no-registration, no-route, no-deploy, no-collector-activation tests;
- `LEGACY_PRESERVATION`: **must retain** migration, restore and archived-data integrity for removed capabilities until reviewed retirement;
- `SHARED_SECURITY`: **must retain** auth/tenant/egress/secret checks independent of old feature names;
- `EXCLUDED_POSITIVE`: remove from mandatory acceptance only after a reviewed test-function/assertion-level classification and replacement for shared checks;
- `UNKNOWN`: don't skip; manual triage required, favor running in existing suite until safely classified.

Provide a machine-readable `ci_scope_manifest` mapping **each workflow → job → test script/module/function → classification → approved authority → trigger tier → replacement/retirement disposition**. Manifest MUST be validated against current repo scripts and source; no inferred green evidence. Positive certification of excluded features must never gate Sprint 10/release; protective negative/legacy tests remain required. Any skipped scope-excluded test must have an explicit rationale with matching manifest entry.

## 6. Migration, regression and security safeguards

1. **Migration:** Alembic single-head/check; empty clean PostgreSQL 17 upgrade; seeded old-schema upgrade with before/after table, row, relation, FK and hash comparison; negative downgrade/reupgrade only for explicitly reversible migrations; no automatic destructive downgrade of production-like data; rollback strategy + backup/restore prove retained old-client data. Require independent migration review for schema change.
2. **Concurrency:** real DB parallel writers, expected_revision preconditions, POST/PATCH/DELETE, stale intent, idempotent retry, TOCTOU, revoked user/tenant change at commit, multi-call failure and clear error contract. Exact Sprint 1 applicability/history decisions apply.
3. **Regression:** explicit baseline suites + differential path-aware feature suites; unknown changes use broad coverage; external tools pinned and verifiable; retain current protected source ownership/tenant/alert tests. Validate role-screen actions with Playwright.
4. **Security:** minimal job permissions, SHA-pinned third-party actions with managed update policy, scoped OIDC only where needed, never use pull_request_target to execute untrusted code, no secret exposure to forked PRs, supply-chain attestations, SBOM with digest+scan threshold and reviewed waiver register, licence/NOTICE completeness, runtime image non-root and read-only checks, API auth and egress checks.
5. **Evidence:** exact GIT_SHA, branch, time, tool versions, commands, exit codes, test count, `SKIP/NOT_TESTED/BLOCKED` reasons, PostgreSQL version, image/collector digest, artifact SHA256 manifest, retention/redaction, UI screenshots and evidence links. Separate hosted CI result from local probe; no double counting repeated tests.
6. **CI race control:** concurrency groups isolate PR/ref, cancel only obsolete PR attempts; DO NOT auto-cancel migration/release operations; never run destructive tests against shared PostgreSQL; use per-job random isolated prefixes/network/DB/containers; cleanup scoped task-owned resources only.
7. **Required-check stability:** GitHub branch protection must be reviewed against exact job names before renaming/removing workflows. Add replacements and verify first; retire obsolete checks only once updated branch rules are operational. No change may accidentally permit bypass through a 'skipped-success' job, path-filter, or status-name mismatch.
8. **Publishing/deployment:** re-review automatic UAT publisher and manual Stage B on latest main; keep disabled/untriggered under current owner 'final main integration only' instruction. Do not alter protected environment controls without independent review; no production deployment authorization.

## 7. Bounded Codex execution plan (requires separate implementation approval)

**CI-01 Inventory / preservation (documentation and scripts only):** enumerate all `.github/workflows`; extract jobs/triggers/scripts, classify assertions; list redundant paths, excluded positives vs protective negatives, branch required-check rules and current CI status. Audit PR80–84 and the new D1–D4 contracts; no production behavior changes.

**CI-02 Scope and workflow validation:** introduce `ci_scope_manifest` validator and tests, all-workflow actionlint, least privilege and safe event/skip rules. Phase in as stable, non-deploy checks; fail closed on unclassified tests, keep core security.

**CI-03 Sprint 1 integrated checks:** add real PostgreSQL 17 migration/old-state restoration, all-writer CAS/atomic/immutability and role browser tests as implemented, with truthful NOT_TESTED status for unavailable binary/provider. Don't falsely certify unimplemented D1–D4 contracts.

**CI-04 CI tier consolidation:** reduce duplicate suites only after coverage parity evidence, maintain exact job names/branch protection, publish reproducible evidence artifacts.

**CI-05 Security/release safeguards:** SBOM/image/license scans, attestations, gating/approval records; harden automatic UAT publish trigger in coordination with owner; no releases until independent gates cleared.

**CI-06 Sprint 2–10 matrix:** implement sprint-specific checks incrementally as real capabilities are introduced, not fake/stub passing placeholders. The final comprehensive integration runs before approved main merge.

Each slice: isolated branch, owner-reviewed diff, actual actionlint/YAML+schema tests, no intermediate merge to main, no deploy, no release-gate changes, stop for review.

## 8. Exit criteria for CI refactor itself

- Every workflow inventoried with owner/status and safe trigger; approved scope mappings validated.
- No `EXCLUDED_POSITIVE` job is mandatory; all critical `EXCLUDED_NEGATIVE`, `LEGACY_PRESERVATION` and `SHARED_SECURITY` tests preserved or equivalently replaced with proven coverage.
- Existing real Postgres/API/browser/security baseline unchanged or stronger, with actual execution at tested commit.
- No skip/conditional/path event produces a false green required check.
- All-workflow actionlint; dependency and action integrity; evidence hashes.
- Release/publish gates cannot be loosened by this work.
- No uncontrolled deployment, collector pin change, main merge or false security/CHK closeout.

**Independent statuses unchanged:** `CHK-001 FAIL` · `CHK-002 BLOCKED` · `SECURITY BLOCKED` · `RELEASE NO-GO` · `FORMAL_UAT PENDING` · `DEVELOPMENT_CLOSURE NOT COMPLETE`.
