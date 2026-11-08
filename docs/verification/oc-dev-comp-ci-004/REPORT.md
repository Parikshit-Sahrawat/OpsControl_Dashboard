# CI004 — PR86 recovery

Verified remote/base e74038d8248b0849127339230ef89a942b5700c5. No application/backend/migration/permission enforcement changes. Only stale test expectations corrected. All seven background incident states remain tested. Admin and incidents.view cannot open retired UI; five monitoring pages exclude incidents. Protective scope assertions retained.

Hosted six failures reviewed:42479882305(frontend validation),42479882325(native),42479882245(access),42479882232(quality) repeat the same two stale frontend assertions.42479882249(release) waits for removed Incidents UI in full_closure_acceptance;42479882340(operational) waits for it in ui_theme_acceptance. Remaining stale ARCH/consolidated/Sprint09 assertions were traced and converted to UI absence while preserving authenticated background pagination, stable IDs, bounds and tenant denial. No timeout increases or skips.

Correction of prior summary: CI003 raw frontend log actually has36 PASS/2 FAIL; its narrative38 PASS was incorrect. That historical raw evidence remains untouched. CI004 actual result38 PASS/0 FAIL/0 SKIP. Lint/build PASS; background/access27 PASS. Actual ARCH/API/browser PASS, RELEASE_BROWSER_ACCEPTANCE=1 release harness PASS, OPCONTROL_UI_THEME_ACCEPTANCE=1 operational harness PASS, real-PG Sprint09 selection8 PASS plus API/Sprint08/Sprint09 browser groups PASS. Repeats not added as new coverage.

Local Docker backing storage is nearly full. Initial operational startup failed with initdb ENOSPC; retained failed attempt. Successful run used external task-only docker wrapper injecting PG tmpfs for the allocated ephemeral ETL fixture. No repository storage/production/durability contract changed; no host crash durability qualification. Overlay source retained for reproduction. Controlled Carte-shaped provider fixture is not genuine Carte certification.

No merge/integration into84/85. New hosted conclusions PENDING after push; owner monitors. Sprint1 NOT COMPLETE; CHK-001 FAIL, CHK-002 BLOCKED, SECURITY BLOCKED, RELEASE NO-GO.
