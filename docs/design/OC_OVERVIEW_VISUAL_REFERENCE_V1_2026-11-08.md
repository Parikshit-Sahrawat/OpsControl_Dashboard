# OpsControl Overview — Owner-Supplied Visual Reference and Functionality-First UI Contract

**Recorded:** 2026-11-08 | **Authority:** Product-owner direction, after UI/UX v1.1 clarification.
**Status:** Visual reference approved for Dashboard Overview styling **only**, implementation not verified by this document.
**Reference:** Owner-uploaded screenshot named `ChatGPT Image Nov 8, 2026, 07_43_45 AM-1.png`, presented in the OpsControl ChatGPT conversation. Binary image **is not yet checked into this repository**. Codex must obtain that user-provided image in its workspace for precise screenshot comparison; do not invent a public URL or claim visual testing without it.
**Relationship:** Complements [approved common UI/UX contract](OC_UI_UX_APPROVED_V1_2026-11-08.md); the screenshot is **Overview-specific visual inspiration**, whereas the earlier *Monitoring Operations & Configuration* reference informs configuration/detail and Reports/Trends workspaces. All pages share the same OpsControl tokens and component system.

## Non-negotiable authority precedence

**Existing implemented behavior + current approved product authority + actual backend/API/RBAC/tenant contracts > visual artwork.** Refactor frontend UI presentation to fit **existing OpsControl functionality**, not backend or domain behavior to match fake screenshot controls or metrics.

Do NOT add new application entities, APIs, database changes, collector capabilities, historical measurements, SLA values, saved reports, notification transports, navigation destinations, monitoring types or mocked status data solely because the screenshot depicts them. Do not remove or break existing functional controls that are absent from the picture. Implement separately approved new features in their existing planned development sprint, not as untracked visual changes. Screenshot sample numbers, labels, timestamps and percentages are placeholders only.

**No destructive or functional backend changes permitted under this visual-design adaptation.** In particular no new incident-management UI or ServiceNow, SFTP, cloud object storage, Kubernetes-workload monitoring or Pentaho execution/mutation. Background alerts, permitted evidence correlation and Email/PagerDuty capability stay in approved scope.

## Exact UI visual features to draw from the screenshot

- **OpsControl identity:** deep-navy/cobalt left sidebar, existing brand mark, bright blue selected nav item, grouped icon+label navigation, clean visual hierarchy. Preserve actual existing route identities, permission checks, active section and collapse/mobile behavior from `frontend/src/components/TopNav.jsx`.
- **Main canvas:** calm near-white/light blue gray, crisp white cards, thin cool-gray borders, subtle shadows, rounded corners, consistent gutters and balanced text density. Use shared design tokens rather than one-off Overview styling.
- **Header:** prominent 'Overview' heading and concise supporting description; global organization and environment scope, notification/profile/help and time/freshness context based on existing live controls. Do not fake a search box, clock timezone picker or refresh selector if not implemented; retain real existing controls.
- **KPI row:** compact clickable cards with familiar large number/icon/secondary label/status color, responsive wrap, clear hover/focus, consistent alignment; KPI's actual count and navigation route must match exact same tenant/environment/status scoped destination. Preserve current `Overview.jsx` KPI semantics and any active `UnifiedOverview.jsx` semantics; decide which the actual route uses by inspecting `frontend/src/App.jsx`.
- **Evidence panels:** visual inspiration for 'Active Alerts', 'Recent Data Pipeline Executions (Pentaho read-only)', 'Resource Status' and 'Collector Readiness' only where current actual data feeds support them. Keep current `UnifiedOverview.jsx` features such as open ETL executions, domain-specific alert lists and Correlated Events, with complete access to their existing actions. Reuse chart/table/card styling without fabricating new data.
- **Right-side utility column (desktop):** prioritize permitted, functioning quick actions and monitoring context; on smaller screens stack below primary evidence. Show quick actions only when the current route, API, permissions and real operation exist. No dead 'Create Alert', 'Add Monitor', 'Generate Report' or 'Manage Access' placeholders.
- **Progressive disclosure:** operators see attention-first critical/warning signals and recent changes; admins retain their already authorized configure/investigate routes without turning overview into a giant editor. Cards remain drilldown destinations rather than duplicates of detailed pages.
- **Typography:** consistent legible system/inter-like sans serif, headings 20–24 px, card titles 15–18 px, body 13–14 px; avoid tiny charts/labels from image. Align values and units, define text/icon/contrast for status (not color alone).
- **Responsiveness/accessibility:** verify 1920/1366/768/390 px, keyboard and screen reader navigation, reduced motion, tab order, horizontal scroll limited to tables, clear empty/loading/stale/error states.

## Important discrepancy: overview health trend

The attached visual includes a large 'Resource Health Trend' chart. Prior owner requirements explicitly moved trend visualization to Reports rather than the home/Overview page. **A visual reference by itself does not reverse that product requirement.** Do **not** introduce the trend chart into Overview solely because it appears in the screenshot. Retain the existing approved overview content and historical reports navigation unless the product owner explicitly approves a changed functional scope.

Likewise, screenshot sections 'Alert Delivery Health', 'Monitoring Coverage', 'Collector Readiness', 'Availability %' and quick actions are *layout references*, not evidence these data contracts exist or are certified. Only display them when live, tenant-qualified APIs already provide verifiable data and the functionality is approved.

## Source inventory for implementation discovery (read actual current code, not assumptions)

- `frontend/src/App.jsx`: actual mounted Dashboard route and access-controlled navigation.
- `frontend/src/pages/UnifiedOverview.jsx`: actual `/api/v1/unified/overview` evidence feed, running data pipeline executions, ETL/VM/API alert lists and correlation evidence; check live route use.
- `frontend/src/pages/Overview.jsx`: KPI/operational feed and recent pipeline alerts; may be an alternative/legacy page; inspect imports and route to avoid duplicating or overwriting functions.
- `frontend/src/components/TopNav.jsx`: existing sidebar, organization + environment selectors, profile/help, InAppNotifications and theme switch; preserve multi-org and explicit all-customer authorization semantics.
- `frontend/src/permissions`, `frontend/src/navigation`: actual backend-backed authorization and route guards.

Document `current page/route → current action/API/permission → new visual placement → parity test` for each visible control before writing UI code. Do not assume the screenshot's pictured 5-second refresh applies: `UnifiedOverview.jsx` currently schedules a 15-second poll; any interval change requires load validation and is not implied by this design.

## Implementation acceptance and delivery

1. Build Overview presentation using **the existing OpsControl application data and actions**, with no backend/domain-model/permission/API behavior change under this UI work.
2. Make the new Overview visually consistent with the approved light OpsControl workspace theme and previously selected resource configuration/report designs.
3. Preserve **all current functional panels**, correlated events, ETA/ETL workflow drilldowns, negative-path and tenant-isolation safeguards, linked list scope, state/freshness and permission gating.
4. Measure visual parity against owner reference only once screenshot is supplied to Codex workspace; log image-to-page intentional deviations (e.g. omitted unsupported cards or moved trend) as compliant behavior, not cosmetic regression.
5. Use mandatory development test policy (actual React/FastAPI/real PostgreSQL/Playwright, accessible responsive screenshots, security/RBAC/tenant negative tests, no mock-only certification). No unexplained skips or regressions.
6. Scope Overview styling to the approved frontend sprint work and preserve all other Sprint 0–10 priorities. No `main` merge, no deploy or formal UAT without separate authorization. Maintain `CHK-001 FAIL`, `CHK-002 BLOCKED`, `SECURITY BLOCKED`, `RELEASE NO-GO`.

## Recommended layout mapping (not extra functionality)

Desktop: sidebar + compact topbar → Overview header → current clickable KPIs → two-column evidence layout (primary current running ETL + alerts/correlation, optional compact secondary utility actions that already work) → additional evidence cards. Tablet: primary content first, utility panels below. Mobile: stacked cards, no lost content/controls.

**Owner's directive:** “Do not change our code according to image; instead change Front-end UI according to our code functionality. For dashboard Overview take reference from attached picture, but maintain visual similarities and unique global theme for OpsControl.”

**Verification state:** Documented only; the screenshot is not yet in repository; no application code changed by this documentation task.
