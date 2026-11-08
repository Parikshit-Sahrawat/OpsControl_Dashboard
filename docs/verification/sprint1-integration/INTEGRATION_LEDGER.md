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

Unresolved product authority: typed template OS/method applicability and legacy behavior; immutable attachment/override/effective configuration provenance and retention; all-writer revision/CAS and atomic-vs-staged save; rollback as new revision. No arbitrary contract assumptions.

Required tests: disposable PostgreSQL migration and restore; resource lifecycle, stale sessions, RBAC, tenant isolation, ETL; authenticated desktop and mobile browser; incident exclusion; theme persistence; Tier A/B/C and every enforced GitHub required check. Security/image/license findings are not waived. Owner visual acceptance and independent PR approval are mandatory.

Current state: integration branch initialized with this ledger only; source changes not yet merged; CI not validated; no merge authorization. Release remains NO-GO, CHK-001 FAIL, CHK-002 BLOCKED, SECURITY BLOCKED.
