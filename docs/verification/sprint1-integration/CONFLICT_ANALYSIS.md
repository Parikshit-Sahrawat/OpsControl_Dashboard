# Six-PR conflict analysis — 2026-11-08

Compared recursive Git trees (all untruncated) for baseline `ffe5ac285ab8aef33a1139bce6f3da79be3d6d33`, post-#85 main `2e4fe5d8cb0f39170b0d789fdd7e07be4ac0219a`, and approved PR heads pinned in INTEGRATION_LEDGER.md.

## Observed scope
- #80: 2,595 paths changed from shared baseline
- #81: 357 paths changed
- #82: 613 paths changed
- #83: 135 paths changed
- #84: 1,276 paths changed
- #86: 194 paths changed
- **86 paths have competing blob versions between source branches and/or changes in main.** This is a *conservative tree-level conflict candidate count*, not the number of Git textual conflict hunks. Git three-way merge and semantic tests must still be performed.

## Critical source collisions

| File | Competing sources | Required resolution |
|---|---|---|
| `.github/workflows/phase1-staging.yml` | #80, #81, main | Preserve #85 CI policy and original security checks |
| `.github/workflows/pipeline-v16.yml` | #80, #81, main | Preserve ETL validation and enforced check identities |
| `.github/workflows/v15-quality.yml` | #81, #84, main | Preserve mandatory test policy |
| `.github/workflows/validation.yml` | #80, #81, main | No skip/waiver of mandatory jobs |
| `frontend/package.json` | #80, #81, #82, #84, main | Union required scripts/dependencies, regenerate lockfile and audit |
| `frontend/src/App.jsx` | #84, #86 | Preserve resource workspace, remove excluded incident routes |
| `frontend/src/components/TopNav.jsx` | #84, #86 | Preserve accessible workspace nav, remove incident entry |
| `frontend/src/pages/ResourceManagementV2.jsx` | #82, #84 | Preserve resource lifecycle and workspace flows |
| `frontend/src/pages/UnifiedResourceManagement.jsx` | #80, #82, #84 | Preserve ETL workflow and resource controls |
| `frontend/src/pipelines/PipelineWorkspace.jsx` | #84, #86 | Keep pipeline functionality, exclude incident UI |
| `frontend/src/components/ResourceTemplateConfiguration.jsx` | #82, #84 | Preserve version pins, fail-closed validation and revision UI |
| `frontend/scripts/ui_theme_acceptance.mjs` | #84, #86 | Preserve corrected light-default behavior and browser assertions |
| `frontend/scripts/consolidated_uat.mjs` | #81, #84, #86, main | Union authenticated journeys, do not weaken scope assertions |

Other competing paths include browser acceptance scripts, verification evidence and documentation. All require per-path review before merge.

## Owner-approved contracts for implementation and tests
1. Explicit typed OS/collector-method applicability, fail closed on incompatibility.
2. Immutable tenant-scoped attachment, override and effective-configuration history with actor, timestamp and source revision.
3. Every writer must use revision-checked optimistic concurrency; each committed change atomic; staged drafts are not operational.
4. Rollback creates a new audited revision referencing the old configuration; no mutation of historical rows.

## Status and gates
No six-branch semantic merge is complete. No exact-head consolidated PostgreSQL/browser/CI pass. Do not merge draft #89. Verify migration ordering and real PostgreSQL, RBAC/tenant isolation, old/new CI and owner visual acceptance; obtain independent review.
