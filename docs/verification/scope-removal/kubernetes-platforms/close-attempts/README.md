# Preserved attempts

- Baseline harness: exploratory PASS; source was edited while that process was running, so it is not a qualifying immutable-SHA result.
- Run 1 (fa8e96e): FAIL, new fixture used a non-existent Resource Management detail GET route (405). Corrected to existing Monitoring detail API; cross-tenant 404 assertion retained.
- Run 2 (68be490): PASS for then-current tests; superseded by final stronger browser/template/Pentaho and immutable-record checks.
- Run 3 (5fb46e6): FAIL, PostgreSQL readiness/storage exhaustion. Attributed volume 6a23a475b91f46b9c43834dd1ef1017efbcb195958e4045741216fff3f32a27b belonged to container bbf935300de0b6a98f71a575e5460d96daa25c75bde7ca51cc7308916b26266b (commands.log plus Docker mount event); removed explicitly. No broad cleanup.
- Run 4 (ca1a40d): FAIL, fixture incorrectly expected template inclusion true with no activation. Actual approved default false retained, then real selection tested. Parallel standalone build also failed ENOSPC; final sequential build passed.
- Run 5 (c039b3e): FAIL, fixture searched for new integration creation in the existing-only resource view. Updated to actual persisted Pentaho resource editor.
- Run 6 (db5fae2): FAIL, fixture skipped editor Continue/review steps before Save. The final test follows the actual wizard, without bypassing validation.
- Run 7 (732e44d): PASS; retained under run7-evidence. Final run 8 (46e6f0f): PASS with additional retired association mutation verbs; kept under close-2026-10-28/http-browser.

A focused unit invocation from repository root initially failed to import app; rerunning from backend passed. An npm setup attempt failed because its default cache was unavailable; the task-owned /tmp cache succeeded. Neither failure was treated as a product PASS.

Run 9 at 0a7f669ddb02f820749ee40d9cf91452fd062492: FAIL in the new collector selector test: tenant fixture had no Create Collector control. Screenshot and raw failure retained. Subsequent test uses the authorized synthetic administrator and requires a supported collector row, preventing an empty-table false positive.

Run 10 at cfb3d18ed876db0394dd80250a0c106bbed6f289: FAIL: new administrator login assertion expected Dashboard despite preserved resource navigation. Retained screenshot/log. Corrected test waits for authenticated Sign out control.

Run 11 at 6b3756f: FAIL: direct collector navigation initially returned an empty scoped snapshot even for administrator. Next run explicitly exercises the existing Refresh control before positive/negative collector assertions. Initial timing hypothesis was disproven by later source review: the fixture omitted explicit customer selection required by the canonical list (App.jsx/auth.js).

Run 12 at 6af205b: FAIL: Refresh does not grant missing customer selection. Final fixture correction selects only the authorized LAB-N UUID, following existing scope browser probes. No implicit ALL, authorization bypass or empty-view PASS.

Final run 13 at 402834e351d816d48760974e4566185631600995: PASS, 17 browser groups including collector positive/negative control, 67 focused HTTP checks and all original harness gates. Retained in close-2026-10-29/http-browser.
