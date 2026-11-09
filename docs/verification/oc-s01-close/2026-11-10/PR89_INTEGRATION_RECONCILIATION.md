# PR89 integration reconciliation

Main `2e4fe5d8cb0f39170b0d789fdd7e07be4ac0219a`, candidate `ecfdff2cf3f9d1a7b7b284e79a7f708d1baea8ce`. All six current remote heads equal the integration ledger's pinned heads and are ancestors of PR89. Main is also an ancestor. No source branch was modified. Existing merge parents/conflicts are preserved in `docs/verification/sprint1-integration/MERGE_PROVENANCE.json` and MERGE_RESOLUTIONS.md.

|Source PR|Exact current head|Ancestor|Branch changed paths vs main merge-base|Byte-identical at PR89|Different at PR89|
|---|---|---|---:|---:|---:|
|#86|`6cc4dfc168db8df95be11503c483177c4747421e`|True|194|123|71|
|#84|`c6c21dea79e24fe44d083a113879c1442db57163`|True|1276|1239|37|
|#83|`f9cdc8d9204c40d66c1d956166bb6125eaec7581`|True|135|134|1|
|#82|`1ebe07fb6adb2d1bc5c3c885d9923e6afc7d25b2`|True|613|599|14|
|#81|`af6d2c8243c49d60019c8fb75770a459342626d4`|True|46|46|0|
|#80|`958193f266c89302b2f1919e3703faece591e0af`|True|2595|2578|17|

No changed source-present path from these six branches is missing at PR89. Complete binary-safe SHA256 comparisons,including unchanged rows,are retained losslessly in raw/pr-commit-file-comparison.full.json.gz; compact differing rows and counts are in raw/pr-commit-file-comparison.json. A changed path is not automatically a lost requirement. Ancestry does not by itself prove semantic equivalence.

## Semantic conflict reconciliation

- #80: all37 original model classes remain; all41 migrations present at that source are byte-identical. Additive0042/0043 follow0041. ETL/scope/write hooks and foundation/DAG/native-binding/older-writer regressions rerun against actual PG/API/browser. Workflow and monitoring-only behavior preserved. Supported positive provider authority remains blocked.
- #81: all46 changed paths are identical; historical requirement authority/evidence is not relabelled as current acceptance.
- #82: resource schema/API/template paths now adapt to the single source command and mandatory revisions. Fresh revocation,tenant/context,stale conflict,history and restore evidence verifies the intended safeguards rather than preserving obsolete optional-write behavior. Old migration files are not rewritten.
- #83:134/135 changed paths identical; v16 harness is the sole difference,retaining scoped cleanup and adding later acceptance. Policy,AUTH694 and ten-sprint records remain.
- #84: workspace/theme/configuration paths include later history/staged/child-source/catalogue CAS and navigation/test fixes. New desktop/RBAC/tenant/filter/theme/keyboard and persistence tests verify current behavior. No competing configuration authority or full redesign added by this review.
- #86: current App/FeatureDirectory/TopNav exclude incident management. Updated historical browser expectations retain protective exclusions and background IDOR/pagination assertions. Existing background processing/history not deleted. Scope acceptance and direct-route browser checks executed.
- #85: its merged main/CI modernization remains an ancestor;28 workflows and all13 required contexts preserved. No branch-protection edits.

Historical metadata collisions remain under `docs/verification/sprint1-integration/source-evidence/`, with original commits reachable. See original MERGE_RESOLUTIONS.md for per-file choices. The complete differing-path inventory remains the input to **independent human semantic review**,which is PENDING. This assessment found no missing original path/migration/class and no tested functional loss; it does **not** claim universal behavioral equivalence or independent approval.

Model/migration structural proof: MODEL_MIGRATION_CONSERVATION.json. Newly executed tests: TEST_RECONCILIATION.json. No merge/conflict resolution or runtime code change was performed during OC-S01-CLOSE.
