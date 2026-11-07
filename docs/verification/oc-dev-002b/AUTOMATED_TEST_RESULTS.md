# Automated test results

Exact final V1.6 code source c4c773601c53d0c8f44fdcb51b447c7664fb6eb8; broad release run5b5e55c has identical application source, differing only in the V1.6 test finalizer. Working tree tracked-clean during final runs, then documentation only. Local tests only; **CI TRIGGERED — RESULT PENDING** is the required post-push status, never a local PASS claim.

| Suite | Actual outcome | New/retained |
|---|---|---|
| Backend unit |9 PASS,0fail/error/skip |4 new template/config cases +5 retained002 cases |
| Frontend helpers |41 PASS,0fail/skip |3 new pin cases +38 retained; not mounted React component unit tests |
| Pipeline PostgreSQL |56 PASS,0fail/error/skip |retained |
| Focused Sprint08 PostgreSQL |42 PASS,0fail/error/skip |retained suite includes imported incident fixtures |
| Core authenticated HTTP |14 groups PASS |3 new002B groups (template, stale session, race),11 retained002 groups |
| Sprint08 HTTP |14 groups PASS |retained |
| Pipeline browser |PASS eight-step/draft/negative activation/mobile |retained |
| Sprint08 browser |5 groups PASS |retained |
| Resource browser |PASS one extended real-backend flow,7 recorded checks |new enable/reload/mobile/focus assertions added to retained flow |
| Release/preservation |13 grouped checks PASS,100 tables/499 constraints restored |retained broad harness on final source |
| Actual OTLP load |PASS bounded admission/replay/rejection/accounting |new probe; not full performance acceptance |
| Ruff, frontend lint/build |PASS exit0 |focused/static and unchanged build contract |

Counts overlap; do not sum to a unique-test or feature coverage total. No formal UAT, provider, isolated mounted-component or converged PR80 runtime certification.

Commands:
```sh
PYTHONPATH=backend backend/.venv/bin/python -m unittest tests.test_sprint_template_configuration tests.test_sprint_resource_lifecycle -v
npm test --prefix frontend
npm run lint --prefix frontend
npm run build --prefix frontend
V16_PERFORMANCE_PROBE=1 V16_API_ACCEPTANCE=1 V16_BROWSER_ACCEPTANCE=1 V16_STAGING_PRESERVATION=1 PLAYWRIGHT_MODULE=/tmp/oc-closure-tools/node_modules/playwright/index.mjs PLAYWRIGHT_BROWSERS_PATH=/tmp/oc-etl003a-browsers V16_EVIDENCE_DIR=/tmp/ocdev002b-cleanup-final backend/.venv/bin/python scripts/v16-acceptance.py
V16_TEST_TARGETS=tests.test_sprint08_rbac V16_SPRINT08_ACCEPTANCE=1 V16_API_ACCEPTANCE=1 V16_BROWSER_ACCEPTANCE=1 V16_STAGING_PRESERVATION=1 PLAYWRIGHT_MODULE=/tmp/oc-closure-tools/node_modules/playwright/index.mjs PLAYWRIGHT_BROWSERS_PATH=/tmp/oc-etl003a-browsers V16_EVIDENCE_DIR=/tmp/ocdev002b-rbac backend/.venv/bin/python scripts/v16-acceptance.py
RELEASE_BROWSER_ACCEPTANCE=1 RELEASE_EVIDENCE_DIR=/tmp/ocdev002b-preservation-verified PLAYWRIGHT_MODULE=/tmp/oc-closure-tools/node_modules/playwright/index.mjs PLAYWRIGHT_BROWSERS_PATH=/tmp/oc-etl003a-browsers backend/.venv/bin/python scripts/release-acceptance.py
```

Failures retained: development load failed launching browser from backend-relative path; corrected absolute source path. A unit initially asserted the intentionally mutable effective accumulator was immutable; corrected to assert unrelated metric retention and preserve immutable-version history through actual HTTP/restore tests. First final HTTP probe lacked select import; fixed. First extended Resource browser timed out after reload; no confirmed root cause, no removed assertion, later retry and independent final-source run pass. Textual PR80 compatibility check fails and remains BLOCKED. These are not silent skips.

**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**

## Cleanup negative and export limitations

Final harnessc4c7736 additionally runs an intentional missing-Playwright failure after API/UI start. Runner exit1 is EXPECTED, not PASS for the browser; injected-cleanup/cleanup.json proves container/process/private-fixture removal. Redacted private-failure.log retained; the legacy error text still names the removed private path. Normal final-application/cleanup.json also has all cleanup flags true. Orphan-process check found no matching task servers. Known earlier failed private inputs removed after redacted export.

Legacy retired-EKS probe emits malformed JSON suffix bytes. Four captured exports are retained unchanged as eks.json.raw.txt, not counted as valid JSON or edited into PASS. The report.json and independent scope HTTP evidence remain valid. This exporter serialization limitation is not a new live provider test.
