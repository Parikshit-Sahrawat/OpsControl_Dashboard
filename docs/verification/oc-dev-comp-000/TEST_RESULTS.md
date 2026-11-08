# Actual baseline commands and results

Sprint0 review date:2026-11-08 Asia/Calcutta. Application baseline `ffe5ac285ab8aef33a1139bce6f3da79be3d6d33`, tested harness `d4c5e8e24b7c9d3c62fa35a5c6ea87ec75e43e79`.


Aggregate command: `OC_COMP_BASELINE_EVIDENCE=/tmp/occomp000-baseline PLAYWRIGHT_MODULE=/tmp/oc-closure-tools/node_modules/playwright/index.mjs PLAYWRIGHT_BROWSERS_PATH=/tmp/oc-etl003a-browsers backend/.venv/bin/python scripts/development-completion-baseline.py` at tested harness `d4c5e8e24b7c9d3c62fa35a5c6ea87ec75e43e79`. COMMANDS.json records every subcommand/flags/exit; product source/migrations/agent/frontend bytes equal main `ffe5ac285ab8aef33a1139bce6f3da79be3d6d33`. No product feature applied from draft branches.

|Check|Actual outcome|
|---|---|
|Backend current test module inventory in owned PG|552 executions:550PASS,0FAIL/ERROR,2SKIP|
|Skipped real runtime cases|test_actual_contrib_accepts_five_methods; test_actual_scrape_and_log_rotation_truncation_restart — pinned binary not configured; NOT TESTED|
|Frontend helpers|38PASS,0FAIL/SKIP|
|Lint/build|exit0 each|
|Real core HTTP|9 grouped checks PASS|
|Real RBAC HTTP/browser|14 HTTP groups/5 browser groups PASS|
|Pipeline browser/resource browser|PASS retained8-step/mobile and actual CRUD/delayed inventory/collector identity negatives|
|Controlled release/security/restore|13 grouped checks PASS;100tables/1191rows/499constraints restored|
|pip-audit/npm audit|exit1 each;10pip advisory entries/3packages and4moderate npm affected-package entries; unresolved findings|
|Dependency consistency/Compose/Ruff|pip check, docker compose config --quiet, new baseline runner Ruff exit0|
|AUTH694 registration contract|9focused positive/negative tests PASS,0fail/skip; documentation only|
|Image-level scans/genuine providers|BLOCKED/NOT TESTED, no false zero-findings/certification|

Counts overlap and test existence is not acceptance; legacy behaviors that conflict with current scope can pass baseline tests. See fault/component matrix. No unexecuted contract is certified from mocks or later UAT. Original npm audit and pip audit nonzero results retained. Initial GitHub AUTH694 search returned422 requiring is:issue/is:pull-request, corrected queries found0 before owner supplied decision text; that search was not proof authority absent.

Environment metadata in research/environment-static.json, dependency logs and postgres-image.json; PostgreSQL17.11 immutable fixture image recorded. No new dependencies installed. Full original AUTH694 source and all relevant old decisions still not independently recovered. All global policy/governance dimensions remain separate.


**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO · formal owner UAT PENDING · development closure NOT COMPLETE.**

Controlled harness cleanup negative: deliberately missing Playwright module after real API/UI startup produces expected exit1. All exact-owned container/process/private-input cleanup flags true; raw/cleanup-negative contains redacted failure and expected-failure ledger. This is a cleanup PASS only, not browser PASS.
