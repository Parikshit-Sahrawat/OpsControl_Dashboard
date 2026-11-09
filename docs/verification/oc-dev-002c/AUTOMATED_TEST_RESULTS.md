# Automated tests and reproducible commands

Review date: 2026-11-08 (Asia/Calcutta). Execution logs retain their original UTC timestamps. Tested source `80835f0065de24ebf271fc621b6d1e5e83d73bd2`; main `ffe5ac285ab8aef33a1139bce6f3da79be3d6d33`.


Final source and file hashes are in BASELINES.json/SOURCE_SHA256.json. Actual final run exits0; raw/final-retry/ownership.txt records110 PASS,0 failures/errors/skips. This includes56 retained pipeline cases,42 retained Sprint08 suite cases and12 focused units (9 prior002B+3new002C). Counts are executions, not110 independent requirements; imported fixtures overlap. The separate12-unit command overlaps those110. Frontend41 helper tests PASS; no new mounted-component unit framework was installed. The new component is verified through real browser/PostgreSQL acceptance. Frontend lint/build and focused Ruff exit0.

HTTP core15 grouped checks (14 retained+1new atomic attachment group), Sprint08 HTTP14 retained; new Resource/template/security browser7 groups, Sprint08 browser5 retained, pipeline browser retained. Broad release13 grouped checks include extended CRUD with8 recorded assertions and preservation/TLS/alerts/telemetry/security. Do not add overlapping suites into a coverage percentage. Full57-module backend selection in the task-owned PostgreSQL harness ran564 cases:562PASS,0FAIL/ERROR,2SKIP. Skipped test_actual_contrib_accepts_five_methods and test_actual_scrape_and_log_rotation_truncation_restart both state Pinned Contrib binary not configured. These are NOT TESTED collector runtime cases, not acceptance PASS; no pin or guard changed. Exact module selection/flags/exit0 are in backend-all-command.json, output in raw/backend-all/ownership.txt. This is the complete current test_*.py module inventory invoked through unittest in the isolated database, including overlapping imported fixtures. Genuine provider/collector qualification remains separate.

```sh
PYTHONPATH=backend backend/.venv/bin/python -m unittest tests.test_sprint_template_configuration tests.test_sprint_resource_lifecycle tests.test_sprint_monitoring_only -v
npm test --prefix frontend
npm run lint --prefix frontend
npm run build --prefix frontend
V16_TEST_TARGETS=tests.test_pipeline_ownership_v16,tests.test_sprint08_rbac,tests.test_sprint_template_configuration,tests.test_sprint_resource_lifecycle,tests.test_sprint_monitoring_only V16_SPRINT08_ACCEPTANCE=1 V16_EXTENDED_LOAD=1 V16_API_ACCEPTANCE=1 V16_BROWSER_ACCEPTANCE=1 V16_STAGING_PRESERVATION=1 PLAYWRIGHT_MODULE=/tmp/oc-closure-tools/node_modules/playwright/index.mjs PLAYWRIGHT_BROWSERS_PATH=/tmp/oc-etl003a-browsers V16_EVIDENCE_DIR=/tmp/ocdev002c-evidence/final-retry backend/.venv/bin/python scripts/v16-acceptance.py
RELEASE_BROWSER_ACCEPTANCE=1 RELEASE_EVIDENCE_DIR=/tmp/ocdev002c-evidence/release-final PLAYWRIGHT_MODULE=/tmp/oc-closure-tools/node_modules/playwright/index.mjs PLAYWRIGHT_BROWSERS_PATH=/tmp/oc-etl003a-browsers backend/.venv/bin/python scripts/release-acceptance.py
```

Checks command/exit metadata: raw/verified-checks/commands.json; baseline and final release exact flags/exits: comparison-release-commands.json. Baseline instrumentation modifies test entry only; no application or migration changed. Expected injected500 is a negative transaction test, not an unreported successful update. Earlier failures:500 plain-text parsing,204 empty-body parsing, missing accessible name, native option visible/attached mismatch and redacted error-shape assertion. Pre-commit/dirty runs explicitly are developmental evidence, not exact-SHA acceptance substitutes. Raw static formatting/lint errors shown in tool output were corrected; complete tool-only stdout was not exported as a raw file. No failure silently skipped.

Cleanup: each V1.6 cleanup.json has exact container/process/private-input removal; release-final cleanup.json lists exact image/container identities, stopped processes and no remaining containers. Scoped orphan scan accompanies package. No broad Docker prune, shared volume or UAT operation. Logs are redacted; malformed retired-EKS producer exports are retained byte-for-byte as *.raw.txt, not parsed or counted as valid JSON/PASS.


**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**
