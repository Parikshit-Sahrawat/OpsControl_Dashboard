# Sprint 1 integration ledger — PR #80 + #82 + #84

Status: INTEGRATION IN PROGRESS; NOT ACCEPTED; NO MERGE AUTHORIZATION.
Base: main @ 2e4fe5d8cb0f39170b0d789fdd7e07be4ac0219a (PR #85 merged).

## Source identities
- #80 ETL architecture: 958193f266c89302b2f1919e3703faece591e0af (62 commits after original baseline).
- #82 secure resource lifecycle: 1ebe07fb6adb2d1bc5c3c885d9923e6afc7d25b2 (17 commits after original baseline).
- #84 desktop workspace: c6c21dea79e24fe44d083a113879c1442db57163 (includes approved light-default fix).
- Shared original base: ffe5ac285ab8aef33a1139bce6f3da79be3d6d33.

## Integration requirements
1. Merge source changes into this branch without discarding ETL, tenant isolation, fail-closed scope, collector-parent checks, template pins, resource lifecycle or monitoring contracts.
2. Reconcile .github/workflows and scripts/ci against merged #85: preserve all required status contexts and new Tier A/B/C/F checks; do not disable security or release gates.
3. Record every textual/semantic conflict with file, chosen resolution, tests and reviewer.
4. Resource Management contract decisions pending owner: typed OS/collector applicability and legacy fallback; immutable attachment/override/effective history and provenance retention; mandatory revision/CAS and atomic vs staged writers; rollback as new revision.
5. Run exact-head Python/Node tests, real disposable PostgreSQL migration/restore, authenticated resource and ETL browser, RBAC/tenant negative tests, NOC recovered-phase theme test, and all GitHub required checks.
6. Obtain explicit owner visual acceptance and independent GitHub approval before merge.

## Known verification
- #80 and #82 report mergeable_state=dirty against main. #84 also dirty.
- #82 and #84 share identical blobs for resource_management.py, template_resolution.py and collector_lifecycle.py at inspected heads; preserve once, do not overwrite with older main versions.
- #84 noc failure: ui_theme_acceptance.mjs:468 after OS color-scheme change; theme.js listener removed in c6c21de. Hosted revalidation pending.
- Previous green checks were on pre-#85 heads; they are not evidence of acceptance on this integration branch.
- CHK-001 FAIL; CHK-002 BLOCKED; SECURITY BLOCKED; RELEASE NO-GO unchanged.

## Merge gate
Draft until actual source integration, complete contract decisions, full CI green, owner visual acceptance and independent approval. No automatic merge or production release.
