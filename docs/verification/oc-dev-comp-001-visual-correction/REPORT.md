# Revised Sprint1 desktop candidate — 2026-11-08

**Sprint1 NOT COMPLETE. Prior visual acceptance REJECTED. Revised candidate AWAITING OWNER VISUAL REVIEW.** Green automated tests are not an owner approval. See [owner direction](OWNER_DIRECTION.md) and the detailed [remaining development blocker assessment](../oc-dev-comp-001-blocker-review/REPORT.md).

Source baseline PR84 `ccd524f3afd9231d6d3056071d922577fefcf538`; branch `dev/oc-dev-comp-001-resource-workspace`, PR84 remains draft. Main `ffe5ac285ab8aef33a1139bce6f3da79be3d6d33` unchanged. Approved product is open-source/self-hosted on Kubernetes, Windows Server and Linux Server; Kubernetes deployment does not imply Kubernetes workload monitoring. This correction targets1920×1080,1440×900,1366×768 desktop workflows. Narrow-width tests are retained only for graceful behavior, not mobile-product priority.

## Presentation and control parity

- Added shared Feature Directory, retaining existing authorized categories and destinations. Categories expand/collapse; explicit right-side subcategory flyout opens by pointer or ArrowRight, supports Up/Down/Home/End/Escape, returns focus, closes on outside focus/pointer, stays within viewport and filters revoked/unauthorized destinations. No second route/permission catalogue or new product capability.
- Preserved navy sidebar/light canvas/blue tokens, shared admin/operator styles and source-backed utility actions. Default desktop density compact; explicit Comfortable preference remains functional. Shared directory state is browser-local presentation only.
- Resource tabs and component selection share horizontal desktop space. Customer/environment/name primary filters remain horizontal; advanced configuration-state panel expands explicitly. Chips/reset/apply still issue actual scoped requests. Filter helper text is screen-reader available, not a large permanent paragraph.
- Large stacked summary cards replaced by compact actual-data summary. Table uses deliberate columns, readable configuration badges, accessible full names for truncated text and compact Details/Edit/Collector actions. At all three desktop sizes pagination stays in viewport; table scrolls independently. No health or metric values simulated. Viewer/operator mutations remain independently refused by backend.
- No backend, API, schema, persistence, collector version, permission catalog or activation behavior changed. Existing template/history/compatibility blockers remain. See [source/change identities](SOURCE_IDENTITIES.json).

## Desktop evidence and comparison

Full-resolution **viewport** PNGs, not scaled mobile/full-page substitutes:

| Role | 1920×1080 | 1440×900 | 1366×768 |
|---|---|---|---|
| Platform administrator | [1920](evidence/final-roles-02/admin-desktop-1920x1080.png) | [1440](evidence/final-roles-02/admin-desktop-1440x900.png) | [1366](evidence/final-roles-02/admin-desktop-1366x768.png) |
| Actual organization `operator` membership | [1920](evidence/final-roles-02/operator-desktop-1920x1080.png) | [1440](evidence/final-roles-02/operator-desktop-1440x900.png) | [1366](evidence/final-roles-02/operator-desktop-1366x768.png) |

[Feature Directory flyout](evidence/final-roles-02/feature-directory-desktop.png). A separate viewer account continues the negative role tests; actual operator membership/screenshots and actual operator PATCH403 are separately recorded. Same components/data, no divergent admin/operator UI implementation.

Compared with [supplied approved configuration image](../../design/references/OpsControl_Approved_UI_Admin_Reference.png): navy rail, light blue-gray workspace, blue active navigation, compact white bordered panels, horizontal quick filters and dense table/details layout are retained. Measured resource-table top is about398px at1366×768; pagination bottom about758px in the compact desktop fixture. Geometry files retain actual values for each run/size, not an invented SLO. Rows are readable with full labels available to assistive technology/tooltips; numbers are real synthetic test inventory counts, not monitoring performance claims.

Intentional differences: Resource Management inventory is the real supported Sprint1 surface, not the reference's later-sprint multi-chart monitoring dashboard. No fictional CPU/API/ETL percentages, rollout success, history rollback or unsupported filter controls were introduced. Global operational scope remains separate from explicit Resource Management customer filters and is labelled accordingly. The directory uses current application categories; no exact separate committed taxonomy was recovered. The remote Overview-specific image binary is still unavailable; no comparison to its unseen pixels is claimed. Owner may request further visual changes; this document does not assert fidelity acceptance.

## Actual verification

[Machine results](TEST_RESULTS.json), [command/evidence records](COMMANDS.json), raw logs and [artifact hashes](ARTIFACT_SHA256.json).

- 46 frontend helper/navigation tests; lint and production build. Two new tests cover unique existing directory routes and permission filtering/revocation.
- Real task-owned PostgreSQL17.11, actual migrations, authenticated running FastAPI/React/Vite/Chromium. Main regression run at `c460426`:68 PASS,0 FAIL/SKIP; HTTP15 core +14 authorization groups; seven resource-security browser groups,11 workspace groups and five retained authorization browser groups PASS. Separate legacy-navigation run retains the17-group Pentaho browser regression; its machine results and raw log are separately identified. Focused final role/accessibility run at `c09e3184a5d84c86b4f78f1da4fe37ad39ee45ff` passed12 unit tests and12 workspace groups including actual operator membership; repeated groups are not additive.
- Targeted accessibility: keyboard flyout traversal/escape/focus, accessible names, unique IDs/valid control references at1366 desktop, no page horizontal overflow, horizontal primary filters, visible pagination. These are bounded checks, not full WCAG or screen-reader certification. Actual control counts in JSON.
- Current template pin/overrides/reload, failed-save preservation, revoked session401, viewer/operator403, foreign-source denial and delayed tenant-response protection remain real API/DB/browser assertions. Fresh/populated migration checks and refused unsafe downgrade unchanged; restore compares100 tables/content/schema/FKs in owned fixtures.
- Earlier broad backend562 PASS/2 skips and release13 groups are **historical at95b4ab6**, not newly executed by this frontend correction. Backend/collector source is byte-identical. The two actual Contrib binary tests remain NOT TESTED; no provider certification.
- Prior dependency audits remain unresolved (installed Python10 records/3 toolchain packages and four npm moderate affected entries); unrestricted baseline Ruff19 findings remain. No dependency/image/security remediation, waiver or fresh clearance is implied. Hosted CI follows Trigger-and-Exit, results pending.

## Failed attempts retained

Initial lint caught unqualified window dimensions, corrected with `window.innerWidth/innerHeight`. First actual browser attempt caught flyout anchored a few pixels inside the sidebar; corrected to use the sidebar's right boundary. Second attempt passed new workspace10 groups but legacy pipeline navigation timed out on a now-collapsed category; the test now explicitly expands that category, preserving its full resource/ETL journey assertions. Main rerun passed. Desktop accessibility and an actual operator-role account were subsequently added as explicit evidence. The first operator fixture was correctly rejected422 for missing Department; fixture onboarding now creates a Department and a separate customer operator membership without changing the rule; all attempts remain identifiable, not overwritten or reclassified PASS.

Cleanup removes only each task-owned container, process and synthetic credential directory. Backup is actually restored/hash-compared then removed because it contains synthetic authentication records. No shared UAT/production provider endpoints, deployment, merge, destructive schema retirement or broad Docker prune.

**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.** Nine owner selections Pending, historical controlled-scope approvals unchanged. D07/D08 Pending. Stop for owner visual/architecture decisions; no Sprint2 or additional backend implementation.
