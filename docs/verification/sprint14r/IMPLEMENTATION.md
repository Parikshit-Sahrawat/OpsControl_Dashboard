# Sprint14R implementation and audit dispositions

Baseline: fetched `origin/main@59344c97401340e222627063f7c89bb5e2e89ead`. Dedicated worktree `/workspace/scratch/opscontrol-s14r`, branch `feat/sprint14r-foundations`. Original worktrees/uncommitted UAT/audit reports preserved. No historical branch merged, no backend/runtime schema or migration changed in14R.

## Existing corrections reused

The [prior21-row disposition register](../p0-p1-remediation-2026-10-20/DISPOSITIONS.md) and [executed evidence](../p0-p1-remediation-2026-10-20/VERIFICATION.md) remain historical sources. XBA01/02 P0 and XBA03/04/05/07/08/09/10/11 P1 corrections already exist in main;14R verifies rather than duplicates them. XBA12 prior closure now has accepted local81.28% and exact-runtime remote CI in [main integration](../p0-p1-remediation-2026-10-20/INTEGRATION.md);14R must independently satisfy current applicable gates. XBA13 main metadata fix retained.

XBA06 positive shared-customer VM behavior remains UNIMPLEMENTED and DESIGN-BLOCKED. XBA14 obsolete branch UI remains excludedP2. XBA15 graph/fence cost and XBA18 aggregates are performance risks; XBA16 optional legacy method identity remains a policy/provenance question. XBA17 intermittent UI timing is not a newly proven defect. XBA19 real-provider/replay coverage remains partial future evidence; XBA20 original IMP/SLO governance remains source-blocked; XBA21 Agent log growth remainsP2. No open evidence gap becomes an invented implemented-scope defect.

## New bounded UI changes

- `visual-system.css`: extend existing semantic tokens with navy/violet light/dark palette, local font stack, spacing/radius/motion tokens, restrained shell glass, compact/sticky inventory headers, contrast/focus/forced-color/reduced-motion rules. No new dependency or external font.
- Correct reproduced collapsed-sidebar breakpoint mismatch: at720px mobile mode was active but desktop72px content offset persisted. Align existing701px collapse rule with existing760px mobile boundary. Actual baseline screenshot and geometry prove this defect; the menu itself was already full width.
- `TopNav.jsx`: existing group labels in breadcrumb, accessible navigation group names, focus first permitted destination when mobile menu opens; Escape returns existing toggle focus. Preserve all permission/route maps and group visibility.
- `AuthGate.jsx` / `App.jsx`: keyboard skip link focuses main without altering child hash/history.
- `UnifiedResourceManagement.jsx`: existing inventory gains a named keyboard-scrollable region and sticky headers. No duplicate configuration or create action.
- `theme.js`: browser chrome color follows existing theme preference with new canvas colors.
- `sprint14r_acceptance.mjs`: actual authenticated Chromium, both themes/four widths, loaded synthetic inventory, semantic contrast, focus, scrolling, reduced motion/forced colors and CustomerA-only direct CustomerB denial. Native evidence untouched.

Configuration/monitoring boundaries, customer versus department identity, collector multiple-method controls, all six pipeline pages, explicit scopes, generation guards and existing routes/localization remain canonical. No new grant/model/platform capability is introduced. [Manual UAT](MANUAL_UAT_CHECKLIST.md) remains independent.
