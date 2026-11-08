# Sprint 1 six-PR integration ledger — IN PROGRESS

Base: `2e4fe5d8cb0f39170b0d789fdd7e07be4ac0219a` (merged PR #85). Owner approved combining #80, #81, #82, #83, #84 and #86. Do not merge without owner visual acceptance, independent approval and green required CI.

| PR | Pinned head | Scope |
|---|---|---|
| #80 | 958193f266c89302b2f1919e3703faece591e0af | ETL workflow architecture |
| #81 | af6d2c8243c49d60019c8fb75770a459342626d4 | Development reconciliation |
| #82 | 1ebe07fb6adb2d1bc5c3c885d9923e6afc7d25b2 | Resource lifecycle and PostgreSQL |
| #83 | f9cdc8d9204c40d66c1d956166bb6125eaec7581 | Sprint 0 policy / AUTH-694 |
| #84 | c6c21dea79e24fe44d083a113879c1442db57163 | Workspace and theme correction |
| #86 | 6cc4dfc168db8df95be11503c483177c4747421e | Excluded incident UI |

All branches diverged from old main `ffe5ac285ab8aef33a1139bce6f3da79be3d6d33`. #80/#82/#84/#86 are dirty against current main. Integration must preserve every branch's required behavior, not overwrite files wholesale. For each conflict, record file, both variants, decision, test and reviewer. Do not use blanket ours/theirs.

Integration order: #83 policy, #81 docs, #80 ETL models/API/migration/scope, #82 resource lifecycle/RBAC/template pins, #84 UI and keyboard/browser behavior, #86 incident UI removal. Verify old protected APIs, all tenant/security boundaries, migrations, and CI checks. Preserve theme fix c6c21de and scope assertion. Keep background alerts and audit even though incident UI is excluded.

Owner-approved Sprint 1 product contracts (2026-11-08): (1) explicit OS and collector-method applicability; incompatible configurations fail closed, with legacy compatibility handled explicitly; (2) immutable tenant-scoped attachment, override and effective-configuration history with actor, timestamp and source revision; (3) revision-checked optimistic concurrency for every writer, atomic committed configuration changes, optional staged drafts not operational until applied; (4) rollback creates a new audited revision referencing the earlier configuration, never rewrites history. Retention duration and legacy migration behavior still require detailed policy verification; do not silently invent values.

Required tests: disposable PostgreSQL migration and restore; resource lifecycle, stale sessions, RBAC, tenant isolation, ETL; authenticated desktop and mobile browser; incident exclusion; theme persistence; Tier A/B/C and every enforced GitHub required check. Security/image/license findings are not waived. Owner visual acceptance and independent PR approval are mandatory.

Current state: integration branch initialized with this ledger only; source changes not yet merged; CI not validated; no merge authorization. Release remains NO-GO, CHK-001 FAIL, CHK-002 BLOCKED, SECURITY BLOCKED.

## Execution update — 2026-11-08 (initial state above retained as history)

All six pinned tips have been integrated by three-way merge into this branch, retaining merged main/CI85. Source branches and GitHub PR states were not merged or rewritten. See MERGE_PROVENANCE.json and MERGE_RESOLUTIONS.md for actual parents, reproducible conflicts and semantic resolutions. Application implementation progresses through acb5308,8da3bf6,a54b69b,c39ad3c and test candidate89f8a55; exact full SHAs are in test provenance/Git history. All current code remains isolated on PR89.

Additive0042 introduces DataSource-owned immutable configuration revisions and source/actor-scoped idempotency. HTTP source commands serialize under existing authorization/source locks; legacy attachment endpoints require source preconditions. Rollback appends and never applies/deploys. Explicit Windows/Linux method schemas and HTTPS GET/HEAD configuration shape validation are reused; actual worker egress/DNS/TLS authorization remains separate. Existing global package versions are immutable. Initial legacy intent requires explicit unverified import; no historical authors or validation are invented. No purge or collector-version change.

Approved single-panel navigation replaces the inherited flyout; real admin/operator screenshots and focused accessibility/navigation/theme/failure tests are development evidence, not visual acceptance. Retired incident UI remains absent; background processing/history stay intact. Full atomic source-context cutover and remaining history/application UX/contracts are explicit open work, not hidden by green tests.

CI names/coverage are mapped without retiring any legacy enforced check. All28 workflows are validated. Ruleset additive update was **refused403** by the integration despite the repository-admin flag; re-read proved the original13 contexts, strictness and independent approval remain unchanged. See RULESET_UPDATE_RESULT.json. Security/image/licence policy failures remain enforced. Hosted final-HEAD results must be reported as pending until actually available; no historical green run qualifies this candidate.

Sprint1 NOT COMPLETE. Owner visual acceptance and independent PR approval remain prerequisites to any future merge. CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.
