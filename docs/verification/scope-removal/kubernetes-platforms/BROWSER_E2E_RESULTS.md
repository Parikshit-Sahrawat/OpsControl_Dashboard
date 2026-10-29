# Browser E2E acceptance — 2026-10-29

Tested source: `402834e351d816d48760974e4566185631600995`. Real Chromium (`/usr/bin/chromium`) driven by Playwright 1.56.1 against task-owned Vite/FastAPI/PostgreSQL. No browser API mocking in the removal probe. Synthetic users and resources only; screenshots contain no real customer information.

**PASS: 17 removal assertion groups**, plus the unchanged resource CRUD and pagination browser probes in the full release harness. Raw assertions: [scope-browser.json](close-2026-10-29/http-browser/scope-browser.json); [commands](close-2026-10-29/http-browser/commands.json); [browser output](close-2026-10-29/http-browser/commands.log). Screenshots: [Compute](close-2026-10-29/http-browser/scope-compute.png), [API and template selection](close-2026-10-29/http-browser/scope-api.png), [Pentaho](close-2026-10-29/http-browser/scope-pipelines.png).

Executed navigation/selector/control absence, legacy source absence from actionable inventory, eight direct retired URLs/hashes, real Linux/Windows/EC2 edits and saves, API inventory and monitoring configuration, persisted template attachment and real inclusion checkbox interaction, and persisted Pentaho edit/save through its review steps. The unchanged CRUD probe separately creates a VM in the browser, verifies persistence/configuration, rejects cross-tenant access and disables the fixture. Pagination checks exercise both themes and 205 resources.

Command: `RELEASE_BROWSER_ACCEPTANCE=1 PLAYWRIGHT_MODULE=/tmp/oc-scope-close-browser/node_modules/playwright/index.mjs PLAYWRIGHT_CHROMIUM_EXECUTABLE=/usr/bin/chromium RELEASE_EVIDENCE_DIR=/tmp/oc-scope-close-run13 backend/.venv/bin/python scripts/release-acceptance.py` with Docker explicitly pinned to the local Unix socket. Exit **0**. Browser credentials are synthetic fixture values; no production/UAT target.

Earlier fixture errors and screenshots are retained in [attempts](close-attempts/README.md). No failed assertion was relabelled PASS. Pentaho/VM/cloud configuration acceptance is not genuine-provider execution or certification. Browser/API evidence jointly verifies tenant/RBAC constraints; no independent owner UAT is claimed.

Additional collector acceptance: authorized administrator must see the supported HTTP collector, while the retained legacy collector is absent from actionable rows and its source is absent from creation options. [Collector screenshot](close-2026-10-29/http-browser/scope-collectors.png). Prior 2026-10-28 passing evidence remains unchanged; failed extension attempts 9–12 are retained.
