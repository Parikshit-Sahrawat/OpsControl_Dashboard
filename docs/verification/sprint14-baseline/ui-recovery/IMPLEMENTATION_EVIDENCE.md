# IUAT-S14-UI-003 implementation evidence

Feature branch: `feat/iuat-s14-ui-003`, based on frozen `main` SHA `1a3a31e30fb5607d68ae328477af0d1df007dbd1`. Remote `main` was fetched and matched that SHA before branching. This feature is for review; it does not sign off Sprint 14 or production readiness. The unrelated prior UAT reports, migration evidence, untracked scripts and PR #33 were not edited.

## Implemented changes and finding disposition

| Finding | Feature-branch result | Evidence / limitation |
| --- | --- | --- |
| UI-003-01 | **FIXED IN BRANCH**: resource Create action moved from filters to page header, preserving `resources.create` check. | [Browser regression](../../../../frontend/scripts/ui_recovery_acceptance.mjs): header action present; toolbar action absent. |
| UI-003-02 | **FIXED IN BRANCH**: one contextual Create department action, in page header. Employee and role actions follow the active tab. Guided onboarding remains. | Browser regression counts one department action. Older browser selectors adjusted to follow contextual tabs. |
| UI-003-03 | **FIXED IN BRANCH**: grouped navigation includes the three owner-approved independent children. Existing six pipeline tabs and URLs remain. | Browser verifies groups, six pipeline tabs, three children, child hashes, refresh and Back/Forward. Other top-level page deep links remain unchanged. |
| UI-003-04 | **FIXED IN BRANCH for tested viewport**: explicit mobile menu, accessible open/close state, Escape with focus return, close on destination selection. | Browser at 390 px; [open menu](evidence/implemented-menu.png), [closed menu](evidence/implemented-mobile.png). Tablet and assistive-technology manual review remains. |
| UI-003-05 | **FIXED IN BRANCH**: Organisational Access opens the existing customer-grant list, effective-access review and scope boundaries without a new grant workflow. | Owner approved the destination. The synthetic browser run verifies grant filtering; backend RBAC and grant semantics were not changed. |
| UI-003-06 | **FIXED IN BRANCH (navigation)**: Collectors opens the canonical list and existing multiple-method form/list. | Owner approved the sidebar destination. No collector runtime or backend changes. |
| UI-003-07 | **FIXED IN BRANCH (label)**: “Configuration state” and “Configuration enabled · health in Operations” separate configuration from observed health. | Browser verifies header. This does not add or assert health data. |
| UI-003-08 | **PARTIAL**: existing Resource Management tabs, guided Access action and inventory rows use shared compact styling. | [Feature desktop](evidence/implemented-desktop.png); wider cross-browser review remains. |
| UI-003-09–11 | **OPEN / UNVERIFIED / OUT OF SCOPE** as classified in the [findings register](IUAT_S14_UI_003_FINDINGS.md). | No incident route consolidation, agent installation, shared-resource association or future-sprint capability was added. |

## Executed validation

All browser and database fixtures were synthetic in a new disposable PostgreSQL 17 Compose project (`opscontrol-s14-uat-84591256`) under `/tmp/opscontrol-ui-003-uat`, separate from previous UAT state. Backend was the frozen SHA; frontend was this feature branch. No live collector, ETL workload or customer source was connected. This is local integration evidence, not production acceptance.

| Command / gate | Result |
| --- | --- |
| `npm run lint --prefix frontend` | PASS; ESLint exit 0. |
| `npm test --prefix frontend` | PASS; 4 test files, 0 failed; reported line coverage 96.98% over instrumented files. The repository's 80% gate was not changed. |
| `npm run build --prefix frontend` | PASS; Vite 7.3.7; existing >500 kB chunk warning, no build failure. |
| `OPSCONTROL_UAT_STATE_DIR=/tmp/opscontrol-ui-003-uat UI_RECOVERY_EVIDENCE_DIR=docs/verification/sprint14-baseline/ui-recovery/evidence node frontend/scripts/ui_recovery_acceptance.mjs` | PASS; 52 Chromium checks, 0 failures; 1366 px desktop, 768 px tablet and 390 px mobile. The synthetic UAT environment contains two customer Organizations and four inactive collectors. The route, list, filter, collector detail, grant view, Back/Forward, refresh and permissions were exercised. Screenshots are linked below. |
| Disposable DB: `python -m unittest -v tests.test_sprint12_shared_trust tests.test_sprint08_rbac` from `backend/`, with `DATABASE_URL` and `OPSCONTROL_V16_ACCEPTANCE=1` supplied from private UAT state | PASS; 45 tests, 0 failures. `unittest` discovery also ran existing imported incident cases. No credential values entered the report. |
| `python -m pytest -q tests/test_sprint12_shared_trust.py tests/test_sprint08_rbac.py` | NOT RUN: installed backend interpreter lacks pytest. The same applicable cases were executed with the repository's `unittest` framework instead. |
| Frontend typecheck | NOT APPLICABLE: frontend is JavaScript/JSX and defines no `typecheck` script or TypeScript configuration. ESLint and Vite compilation ran. |

## Remaining limits and manual UAT

The screenshot evidence is from a controlled synthetic environment and selected states. The original IUAT-S14-UI-003 screenshots were unavailable. Browser regression did not certify screen readers, all tablet widths, every modal, or production telemetry. Resource inventory and Access Management remain separate from operational monitoring. Backend contracts, RBAC, tenant isolation, customer selection semantics, collector ownership, migrations and the 80% coverage threshold were unchanged. Use the [manual checklist](MANUAL_UAT_CHECKLIST.md) before approving a merge.

## Owner-approved navigation completion in PR #39

**OWNER APPROVED:** Organizations, Collectors and Organisational Access are independently selectable children. The navigation implementation is complete in this branch and supported by the focused tests above. This does not constitute independent manual UAT approval.

The browser run caught two integration defects in the new path: the wrapper applied an empty administrative customer override while mounting the canonical lists, and older sparse scope-boundary specifications caused a render exception when expanded. The frontend now uses the explicit global customer selection for the canonical Organization/Collector children, and displays absent optional boundary arrays as empty without changing backend grants. The tests verify both customers' seeded rows, local/global scope filtering and the expanded grant view.

[Organizations desktop](evidence/organizations-desktop.png), [Collectors desktop](evidence/collectors-desktop.png), [Organisational Access desktop](evidence/organisational-access-desktop.png), [mobile menu](evidence/navigation-r2-mobile-menu.png), and [Organizations mobile](evidence/navigation-r2-organizations-mobile.png) come from the controlled synthetic UAT environment. Existing earlier `implemented-*` screenshots are preserved. The access screenshot contains synthetic employee names only.

Changed frontend files: `src/App.jsx`, `src/navigation.js`, `src/components/TopNav.jsx`, `src/pages/UnifiedResourceManagement.jsx`, `src/pages/ResourceManagementV2.jsx`, `src/pages/AccessManagement.jsx`, `src/pages/AccessBoundaries.jsx`, `src/visual-system.css`, `scripts/navigation.test.mjs`, `scripts/ui_recovery_acceptance.mjs`, `package.json`, and legacy browser acceptance selectors updated for the accessible child labels. No backend code, migration, RBAC contract or architecture file changed. PR #39 baseline head before this update: `7f4ca8b17040b7832af906030a018d5cc2fffcf2`. The resulting exact head SHA is recorded in the draft PR description and final delivery report after push; a commit cannot contain its own SHA.
