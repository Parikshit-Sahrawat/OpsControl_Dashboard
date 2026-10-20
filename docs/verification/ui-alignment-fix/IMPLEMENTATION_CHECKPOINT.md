# UI Alignment Fix — implementation checkpoint

Status: **PARTIAL; direct-main gate not met**. Branch `feat/ui-alignment-fix` started from `origin/main` `eb7fb17dfae40fe580fc49e2dadeb3e7f0ad5167`. This record is a development checkpoint, not independent UAT acceptance. The full UI-001–UI-023 register and UAT Test 1 text were supplied in `opscontrol_ui_alignment_sources.zip` on 2026-10-20; that attachment is the requirement source, not a pre-existing repository specification.

## Implemented and exercised

- Resource Management component selector and guarded Event Parameters, Alert Rules and Notification Delivery routes. Sidebar group expansion and desktop collapse persist; mobile focus and drawer behavior were checked.
- Compute onboarding uses a full-page ten-step workspace with sequential access after identity save, one draft and one Continue action, source/collector identity checks, and backend-confirmed verification before activation. No activation was attempted.
- Resource and Organization create actions remain in page headers. Customer Organizations remain distinct from provider Departments. Existing Collector method configuration remains accessible.
- Owner-approved native integration reconciliation: the existing read/edit editor appears after the ETL resource list, while its duplicate create button is hidden. The legacy pipeline create action remains. Existing methods, sources, jobs and associations were not deleted or migrated.
- Dashboard includes a bounded running-execution projection from the authenticated execution feed, with UTC start time and separate monitoring status. Missing running-step/order details are not fabricated.
- Current alert tables show the authorized customer, observed start time, and severity ordering within the bounded feed. Alerts filters have visible labels; the deferred Alerts redesign is unchanged.
- Owner-approved additive multi-environment filtering now supports explicit checkbox selection in the global header. Existing scalar `environment` requests remain supported; eight operational endpoint families also accept repeated `environments` values. Simultaneous scalar and list filters return 422. The filter is a request restriction and never grants customer access.
- The Agent package button now passes the OS identifier expected by the existing download helper. A browser request assertion confirmed one read-only `/api/v1/agent-control/packages/linux` path; it did not install an Agent. The guided Department → Employee → Permissions screen now searches within the selected provider department and uses selectable result rows in place of a duplicate employee dropdown.
- Reports use searchable resource selection; Incidents show the scoped page range and total. Access boundary fields are grouped; Access Management begins with Departments.

| UI IDs | Current result |
| --- | --- |
| UI-001, UI-002, UI-004, UI-005, UI-006, UI-010, UI-011, UI-021, UI-022 | Implemented in bounded routes/layouts; synthetic browser checks passed. Broader independent UAT remains pending. |
| UI-003, UI-007, UI-008, UI-009 | Partial. Identity-to-collector path checked; real agent installation and activation were not tested. |
| UI-012, UI-014, UI-016 | Partial. Desktop, tablet and mobile checks passed; multi-environment selection was exercised; full light/dark and keyboard audit remains. |
| UI-013, UI-015, UI-018, UI-023 | Partial. UI-015 guided search and provider department boundary were exercised; further layout and workflow checks required. |
| UI-020 | Visible filter labels implemented; broader Alerts redesign remains deferred. |
| UI-017, UI-019 | Not completed; operational adapter/probe evidence view requires separate end-to-end verification. |

## Executed verification

Environment: isolated UAT state `/tmp/opscontrol-ui-alignment-final`, dedicated Docker Compose project `opscontrol-s14-uat-293e0bca`, disposable PostgreSQL 17 database migrated to `0037_access_boundaries`, synthetic UAT fixture. Browser screenshots: [desktop workspace](evidence/compute-workspace-desktop.png), [mobile workspace](evidence/compute-workspace-mobile.png), [Organizations](evidence/organizations-desktop.png). Screenshots show fixture data only.

| Command | Result |
| --- | --- |
| `npm run lint --prefix frontend` | PASS |
| `npm test --prefix frontend` | 5 test files, 0 failed; measured included-module line coverage 97.39% |
| `npm run build --prefix frontend` | PASS; existing >500 kB chunk warning |
| `node frontend/scripts/ui_recovery_acceptance.mjs` with `OPSCONTROL_UAT_STATE_DIR` | 80 passed, 0 failed in Chromium after additive-filter change |
| `node frontend/scripts/ui_alignment_onboarding_acceptance.mjs` with `OPSCONTROL_UAT_STATE_DIR` | 5 passed, 0 failed; synthetic create, method access and package request only |
| `node frontend/scripts/access_onboarding_acceptance.mjs` with `OPSCONTROL_UAT_STATE_DIR` | 3 passed, 0 failed; read-only wizard selection |
| `ENV=test .../python -m unittest tests.test_access_control tests.test_sprint07_frontend_contracts tests.test_registry_contracts -q` from `backend/` | 26 passed, 0 failed |
| `git diff --check` | PASS |

Additional additive-filter gate: on a fresh, disposable PostgreSQL 17 UAT state (`/tmp/opscontrol-ui-multi-env`, revision `0037_access_boundaries`), `OPSCONTROL_UAT_STATE_DIR=/tmp/opscontrol-ui-multi-env node frontend/scripts/environment_scope_acceptance.mjs` passed 26 authenticated HTTP checks, 0 failed, including scalar compatibility, multi-value results, ambiguous-filter rejection and cross-customer denial. The updated Chromium script passed 80 checks, 0 failed, including multi-selection persistence. The fixture contains SANDBOX resources and no DEV resource, so these checks do not yet measure a two-populated-environment union.

`python -m compileall -q app` passed. Scoped Ruff on `app/native_incidents/api.py` passed. Ruff on all four touched backend files reported existing style findings: the ETL route had 27 at the previous commit and 26 after this change; `app/unified/api.py` and `app/unified/reporting.py` retain their existing import findings. These baseline findings were not suppressed or reformatted across unrelated code.

The complete backend suite, PostgreSQL preservation suite, critical 80% coverage gate, final CI and independent manual UAT have **not** been run for this checkpoint. No production or genuine Pentaho acceptance was performed; RT-001–RT-020 remain NOT RUN.

## Mandatory remaining work before direct-main integration

Dashboard running-step/order evidence is unavailable in the current bounded execution list and must remain unknown unless a verified endpoint supplies it. Complete Compute and API operational views, ETL filters/layout, full Access Management and Reports UAT, light/dark accessibility checks, a populated two-environment union test, backend PostgreSQL and coverage gates, CI and independent UAT. Do not merge or push `main` while these gates are open.

Backend changes are limited to additive environment query filters. No schema, migrations, production resources or protected PR #33 were changed.
