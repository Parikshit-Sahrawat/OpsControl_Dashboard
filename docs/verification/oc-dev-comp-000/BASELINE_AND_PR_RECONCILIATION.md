# Baseline, branch and draft PR reconciliation

Sprint0 review date:2026-11-08 Asia/Calcutta. Application baseline `ffe5ac285ab8aef33a1139bce6f3da79be3d6d33`, tested harness `d4c5e8e24b7c9d3c62fa35a5c6ea87ec75e43e79`.


Verified main `ffe5ac285ab8aef33a1139bce6f3da79be3d6d33` before work and again after fetching the owner program; unchanged. Sprint0 branch `dev/oc-dev-comp-000-baseline` in `/tmp/oc-dev-comp-000` starts at this exact main. Existing worktrees/branches and all draft work are preserved. No product/application/migration/collector or deployment configuration changes. Only planning, policy/authority, test harness and evidence changes.

|PR|Exact verified head|Disposition/reuse|Dependencies/limits|
|---|---|---|---|
|80|958193f266c89302b2f1919e3703faece591e0af|Draft/unmerged ETL workflows, native bindings, source proof, readiness, writer fencing, migration tests|24 app paths and4 migration-directory changes versus main (including env and0039–0041); review complete security/schema unit, not models alone. Genuine-provider/older-writer qualifications remain partial|
|81|af9bad0428dd4023829e210cb923d32fa0adba3c|Draft/unmerged planning/feature/backlog reconciliation; no application/migration changes|Reuse evidence/requirements, do not treat proposed tasks or unmerged source as merged implementation|
|82|1ebe07fb6adb2d1bc5c3c885d9923e6afc7d25b2|Draft/unmerged Resource/RBAC/template/browser/preservation work and controlled evidence|10 app paths versus main, no migrations. Reuse reviewed pieces in later development integration candidate. Applicability/history/performance gaps remain; not all acceptance closed|

research/branch-comparison.json preserves complete changed-path lists and merge bases. Current read-only full main→PR82 patch check on the private PR80 tree exits1 in frontend/package.json and scripts/v16-acceptance.py; no patch applied. Earlier PR82 incremental-delta checks reported3 conflicts using a different base. This is not a resolved merge or tested convergence. Even textually clean parts need schema, scope-hook, older-writer and end-to-end review. Do not copy/renumber/rewrite PR80 migrations.

Integration strategy: keep Sprint0 from main; each later sprint isolated; reconcile only reviewed dependencies into a development integration candidate. Test combined identity/migration/RBAC contracts there, preserve all original evidence and SHA provenance. No intermediate sprint main merge. Final Sprint10 development review and explicit owner approval required; genuine provider/security/release gates remain independent. No integration branch product assembly was started in Sprint0.

The only borrowed harness subset is PR82's failure-safe V1.6 finalizer, reviewed and transplanted as test-only logic. It stops allocated API/UI, exports redacted logs and removes only its named PG/private fixture inputs even on failure. No PR82 product changes or complete branch merged/cherry-picked. New aggregate baseline harness preserves nonzero statuses while running independent checks. Application source bytes match main; harness tests at d4c5e8e24b7c9d3c62fa35a5c6ea87ec75e43e79. Global policy/registration documentation commits are separate.


**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO · formal owner UAT PENDING · development closure NOT COMPLETE.**
