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
