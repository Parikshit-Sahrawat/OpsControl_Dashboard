# CI-003 PR84 browser recovery

Baseline cbbaec54ea74139f51b1d75a26ce91378f89a298, remote matched before modification. Test/harness changes only; no frontend application/backend/migration/D1–D4 edits. Source file hashes identify the tested worktree; final commit supplied in handoff.

## Root cause → correction

- Staging42446670957: capture_phase1_ui waited for Data Pipeline Monitoring in collapsed Operations. Add shared accessible navigation helper; use permission-filtered real buttons and aliases for current labels/route keys.
- Operational42446670999: configured ETL browser awaited same hidden control. Correct ETL/NOC helpers without weakening lifecycle, telemetry, tenant or alert assertions.
- Release42446670923: preserved raw diagnostics name navigation:Dark:Compute Health. Expand actual category before selecting Compute Instances/legacy route identity.
- Access42446670928: independently reproduced baseline with browser enabled. Private failed.log confirms Data Sources / Resources hidden behind collapsed group. Correct login navigation readiness/expansion. After change real authenticated API25 groups and browser8 groups PASS.
- Native42446670952: independently reproduced Data Sources / Resources failure, then exposed obsolete positive Incidents navigation/investigation assertions. Replace only excluded UI assertions with absence/direct-route rejection; keep independent real backend incident lifecycle/notification/engine tests. Correct mobile helper to preserve initially closed-menu assertions. Final ARCH001 browser and access-v15(5 groups) PASS.
- Quality42446670911: same ARCH/browser and compatibility dependencies. Actual consolidated PostgreSQL/TLS/upstream pinned OTel integration PASS, quality checks PASS. Complete hosted workflow still PENDING, not claimed locally reproduced in every step.

## Additional failed attempts preserved

First helper tested a missing nav before authentication shell was ready, incorrectly treating desktop as mobile; wait for real Sign out control before checking navigation visibility. Staging clock test found hidden closed Display preferences; open the actual preference panel and select its clock, preserving tick/timezone/reload assertions. No timeout increases or skips.

Operational and compatibility disposable PostgreSQL startup failed with initdb No space left on device on nearly full Docker backing filesystem. Retain raw failure, add redacted DB startup diagnostics, and use task-only PG tmpfs as existing owned harnesses do. This changes no production storage or telemetry durability contract; tests do not certify PostgreSQL host power-loss durability. No broad Docker cleanup.

## Actual local results

- Frontend46 PASS/0 FAIL/0 SKIP; lint/build/quality PASS. Backend564 total:344 PASS/220 SKIP/0 FAIL. Background incident+access focused27 PASS (subset, not additive).
- Access PostgreSQL migration/security25 groups and authenticated browser8 groups PASS.
- ARCH001 migration/API/engine/background incident/notification/browser and access-v15(5 groups) PASS; actual runtime job's complete step set remains hosted PENDING.
- Operational real PostgreSQL, TLS Carte-shaped fixture, local host, browser phases and tenant/security negatives PASS. Genuine Carte qualification remains pending.
- Release recovery/retention/restore/TLS/pagination harness PASS; its full hosted image-build job remains PENDING.
- Staging equivalent substantive18 commands PASS: incremental migration,10 backend probes,4 authenticated browser checks and fixture commands. Additional hosted environment/install steps are not claimed locally executed.
- Consolidated real PostgreSQL/TLS API/pinned OTel0.123.0/browser compatibility PASS. Binary SHA2566bca4ddd928b4b0880f7ec6c16511922f740c497b4efa4b33915b2d54a729213. Genuine Windows/provider qualification NOT TESTED.
- All27 PR85 workflow definitions validated under CI003A; PR84 existing workflow checker passed. Workflow definitions on PR84 are unchanged.

Raw results retain failures and screenshots, source hashes and scoped cleanup. No grand total across overlapping suites. All six affected hosted workflows will be triggered by the PR84 push; results PENDING under Trigger-and-Exit. No merge, deploy, publication or release promotion. Sprint1 NOT COMPLETE; CHK001 FAIL, CHK002 BLOCKED, SECURITY BLOCKED, RELEASE NO-GO.

Evidence packaging validation found two `eks.json` files containing multiple original JSON values. Their bytes are retained as `.jsonstream`, not falsely presented as single JSON documents. All other JSON parses; checksum manifest covers the raw streams too. Initial validator failure is retained here as a packaging correction, not a runtime test failure.
