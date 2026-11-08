# OpsControl UI/UX Design Authority — Unified Monitoring Workspace v1.1 (functionality-first clarification)

**Authority:** Product-owner approval in OpsControl ChatGPT conversation, 2026-11-08.
**Approval:** APPROVED_FOR_IMPLEMENTATION_IN_DEVELOPMENT_PROGRAM.
**Reference:** The latest owner-approved generated UI visual named *Monitoring Operations & Configuration*; combines the light monitoring/performance detail, no-code configuration workflow, and Reports & Trends concepts from the three selected visual mock-ups (NOT the first two rejected overview/command-center mock-ups).
**Reference image provenance:** Generated in the owner conversation. A binary screenshot has **not** been committed to this repository by this task. Codex must use the owner-provided visual as a visual reference if available, and this text as the testable acceptance contract. Do not claim pixel-level comparison until the screenshot is actually supplied to the Codex workspace.
**Status:** Specification/authority recorded; UI implementation and visual acceptance NOT VERIFIED.
**Source baseline:** Sprint 0 draft PR #83 at `f9cdc8d9204c40d66c1d956166bb6125eaec7581`. This document is a **post-Sprint-0 additive design record**, not a rewrite of the Sprint 0 sealed test evidence.
**Program:** [Approved development-completion program](../planning/OC_DEV_COMP_PROGRAM_2026-11-08.md). No intermediate merge to `main`, no deploy, no formal owner UAT.

## OWNER CLARIFICATION — Functionality-first UI adaptation (2026-11-08; supersedes any conflicting visual-first wording)

**Priority rule: CURRENT IMPLEMENTED APPLICATION FUNCTIONALITY AND APPROVED REQUIREMENTS ARE AUTHORITATIVE; THE GENERATED IMAGE IS A VISUAL DESIGN INSPIRATION ONLY.** Adapt the frontend UI **to the current application capabilities**. Do not change application behavior, data contracts, API endpoints, backend services, database models, migrations, domain rules, monitoring semantics, security policies, routing meaning, permissions, existing functional workflows, or feature scope merely to resemble the image. No destructive redesign, no replacement of working controls with attractive but inert mockup widgets.

**Required workflow for Codex and reviewers:**
1. Audit the *actual current* frontend routes, visible controls, workflows, API calls, authorization and tests; produce an **existing-functionality inventory** before UI changes.
2. Make a screen-by-screen mapping: `existing route/feature → existing action/API/permission → proposed visual layout/component → evidence/test`. Keep features and their meaning intact; keep necessary controls accessible within equivalent or fewer sensible navigation steps.
3. Apply the reference picture selectively for **navy sidebar, light canvas, spacing, typography, card/panel styling, tabs, visual hierarchy, readable tables, filters that existing backend supports, accessibility and responsive design**. Rearrange presentation where safe, without breaking interactions.
4. Do **not** invent controls/features, telemetry fields, chart series, permissions, transitions, search indices, filter capabilities, configuration editors, save endpoints, rollouts or reports because they appear in the artwork. Do not remove working capabilities simply because they are absent from the artwork. Existing approved product exclusions still apply, but their retirement must be tracked as independent authorized scope changes, not incidental UI styling.
5. New filters may be added as **presentation-only options** only if the actual API/data supports them, including server-side tenant scoping, pagination, time windows and rate limits. A UI filter cannot promise a query the backend does not perform. Keep unsupported concepts in a later product backlog without creating fake controls.
6. Nontechnical operator and admin layouts must reflect **existing RBAC and backend contracts**; hiding a button does not grant/revoke permission. Preserve current users' working actions and use role-aware progressive disclosure.
7. Refactor styles/components incrementally with functional parity tests before/after. Run current backend/API/real PostgreSQL/React/Playwright regression under mandatory development policy. Verify keyboard and responsive layouts, organization scoping, current functionality, deep links and exact click outcomes.
8. Where the image and implemented code disagree, **follow existing implemented code and approved current authority**; document the deviation in a visual mapping report. No backend/business-logic changes under the UI design task. Future roadmap feature work is separately planned and independently tested under its own sprint authorization.
9. Preserve the review sequence: Sprint 0 is delivered, Sprint 1 begins only upon authorization, no intermediate `main` merge, no formal UAT or release gate change.

**Acceptance:** Functional parity is mandatory; visual similarity is secondary. A working but visually adapted OpsControl UI is preferred over a pixel-matched mockup that changes or fakes features.

---

## 1. Design intent and fidelity

Build a polished, professional, low-friction enterprise NOC/operations web UI that **adapts the approved image's presentation to current working application functionality**, while preserving existing application contracts, accessibility, responsiveness, actual data availability and performance. Favor layout and interaction fidelity over decorative imitation. All displayed operational functionality must use real, permission-scoped application behavior, not nonfunctional demo controls, invented health states or hard-coded telemetry.

The owner requested **two role-specific experiences** using a shared design system:
- **Admin / configuration-capable operator:** overview and monitor detail plus actual permitted configuration, template editing, validation, apply/rollout, history, access controls and advanced filters.
- **Operations viewer / nontechnical operator:** operational health, search, simplified task-based filters, resource details, trends, alerts and reports **without** configuration/mutation controls. The operator-only view is a role-adapted derivative of the approved admin visual; exact separate visual acceptance remains pending owner review. Never hide an authorization defect with UI alone; the backend must enforce the same authorization.

Use a single set of components, not separate divergent app implementations.

## 2. Visual specification — close to the approved image

**Shell / global frame**
- Fixed/collapsible **deep navy left sidebar**, approximately 208–236 px expanded and 56–68 px collapsed; logo top; clear active-item blue pill/rail, icon + label, compact named groups. Sidebar may become a mobile drawer.
- **Light blue-gray/off-white workspace canvas**, white cards with fine blue-gray borders, subtle shadows and 10–12 px corners, 12–16 px consistent gaps. Avoid dark command-center treatment as the default; retain accessible dark theme if currently supported without sacrificing light-theme fidelity.
- Sticky **top utility bar**: organization selector (multi-organization where authorized), environment selector, global search, clock/timezone, refresh status, notifications, Help, profile. Must fit or collapse cleanly at common widths.
- Main content: concise title and subtitle, mode/tab strip, scoped quick filters, live KPI strip, monitoring visualizations, configuration/validation, trend panel. Use predictable grid alignment, clean edges and consistent baseline.
- Brand accent: modern **blue** (approx `#1463EB`), secondary cyan/teal, semantic healthy green (approx `#16A34A`), warning amber (approx `#D97706`), critical red (approx `#DC2626`), subdued neutral text (approx `#475569`); validate WCAG contrast, avoid color-only signaling. Colors are starting tokens subject to accessible calibration, not exact sampled screenshot values.
- System/inter-like sans font; headings 20–24 px main and 15–18 px card titles, body 13–14 px with 1.4–1.5 line-height, metadata 12–13 px; no tiny chart text below usable accessibility bounds. Prefer system font or an already licensed/local project font; do not introduce third-party font licensing or extra network dependencies.
- Icons: consistent SVG/icon library and stroke weights. Tables: balanced row heights, aligned numbers, truncated long names with accessible full detail, visible hover/focus and status chips.

**Information hierarchy**
1. Global context (organization/environment/timezone).
2. Saved workspace + useful filters.
3. Live performance and health KPIs.
4. Monitoring panels (CPU, memory, disk, network, processes, services, API, read-only Pentaho ETL).
5. Selected-resource detail, collector freshness and effective template/monitoring configuration.
6. For authorized admins only: edit/preview/validate/apply configuration, rollout status, rollback if approved by real backend contract.
7. Historical charts/reports with window and aggregation controls.

Do not render large fabricated totals/percentage examples copied from the mock-up; real values or clearly labeled unavailable/empty/stale states only.

## 3. Navigation and view composition

Recommended semantic groups, harmonized with the existing router rather than a new competing navigation system:
- **Operations:** Overview, Resources/Compute Instances, Processes, Services, APIs, Pentaho ETL (read-only).
- **Configuration:** Monitoring Templates, allowed resource configuration/collector administration (permission gated).
- **Monitoring & Analytics:** Alerts, Reports & Trends.
- **Administration:** Access Management, Settings, Help (only permitted items).

Avoid redundant top tabs and sidebar entries: top tabs are contextual within a selected workspace/resource (e.g., Overview | Performance | Processes | Services | History | Configuration for authorized users | Alerts); sidebar drives major destinations. Keep the organization scope persistent across navigation, synchronize compatible filters with URL search parameters, and offer breadcrumbs/back to source. Overview KPI counts navigate to the exact matching scoped list.

**Explicit exclusions:** no incident-management UI or ServiceNow links/fields; no SFTP/file-transfer or cloud object-storage monitors; no Kubernetes/EKS/AKS/GKE/OpenShift workload monitoring; no Pentaho job-execution/mutation actions. Keep background alerts, correlation and notification delivery. Deployment of OpsControl on Kubernetes is not Kubernetes workload monitoring.

## 4. Role-based experience

### A. Admin / configuration-capable operator

- Full monitoring overview and selected-resource details.
- Contextual configuration workspace with **Metrics | Processes | Services | APIs | Pentaho (read-only)** segments where supported by approved capabilities.
- Form-first monitoring settings; if an actual schema-backed JSON/YAML view exists, keep two-way validated parity; otherwise clearly show unavailable/preview-only rather than fake round-trip editing.
- Explicit **Edit → Preview effective configuration → Validate → Review changes → Apply**; don't equate template-save with activation. Show individual target status and collector acknowledgment/first evidence after application. Failed targets actionable, no false success.
- Scope selection must be explicit (selected targets vs broader environment), with impact preview and version/diff before confirmed apply. Optimistic concurrency, idempotent retries, audit and server-side RBAC required by actual contract.
- Restore/rollback controls only if server capability and authorization are implemented; otherwise do not render clickable placeholders.
- Deep operational filters and named saved views; sensitive credentials never exposed in UI/logs.

### B. Nontechnical operator / viewer

- Simplified **Today’s Health / My Resources / Active Alerts / Performance / Reports** type of contextual experience derived from same components and permissions, not a separate dataset.
- Large readable status summary, “Needs attention”, resource search, quick chips (Critical / Warning / Healthy / Unavailable), easy time-range presets, approachable labels and “What changed?” contextual timestamps.
- Fast route: **Find affected resource → See what's wrong and freshness → Inspect relevant process/service/metric history → View alert and allowed notification status → Share/export permitted report**.
- Keep advanced filters in expandable panel; never expose apply/rollback/threshold-edit/collector-secret/RBAC controls. Acknowledge/mutate alert only if separately permissioned and supported by approved background-alert workflow.
- Provide human-readable unit/timezone descriptions and explanatory empty/stale/unmonitored states. Advanced technical detail accessible through permissioned drilldown, never necessary for basic triage.

## 5. Filtering and workflow — maximum useful choice without overload

Global controls: multi-org where authorized, environment, saved workspace, search, timezone, freshness. Per-page filters supported by actual data model: resource type/name/host/OS/collector health, status/severity, metrics groups, process name/PID, service name, API monitor, Pentaho job, monitoring template, tags, time range, aggregation/frequency. Show **high-frequency controls first**, advanced fields in expandable drawer/panel; avoid a permanent two-row wall of filters for basic operators.

Functional requirements:
- Debounced global and local search with keyboard shortcut (`Ctrl/⌘+K`), focus/ESC management, safe query cancellation and actionable zero results.
- Cascading, tenant-scoped selectors; visible selected-filter chips; Apply/Reset; clear-all; displayed match count; validation; URL/bookmark/shareable scopes without secrets.
- Named, saved views are user-scoped and persist across reloads only where a real persistence contract is implemented; otherwise no misleading Saved indicator. Allow default presets and Restore Defaults.
- Time presets 15m, 1h, 6h, 24h, 7d, 30d and bounded custom date range; aggregation/frequency only where backend can honor them, with explicit step and units. Enforce allowed query sizes, pagination, time-zone conversion, retention limits and stale/readiness states.
- Auto-refresh respects tab visibility, request concurrency and in-flight cancellation; never silently multiply backend polling load. 5-second refresh is a **target subject to load validation**, not a guarantee; show observed last update, data/sample timestamp, loading/errors and pause/resume.
- KPIs route to source-filtered tables; switching tabs retains compatible user context; resource selection drives all adjacent details and charts without cross-resource mismatch.

## 6. Functional panel requirements and source fidelity

- **Live KPI ribbon:** real CPU, memory, disk, network, API availability, Pentaho status and background alert counts as permitted; include unit/time window and missing/unavailable state.
- **Live performance:** inspect one or multiple scoped resources; metric toggle CPU/Memory/Disk/Network; sampling and timestamp on charts; no fake sparkline.
- **Process and service monitoring:** searchable/filterable running process inventory, PID, name, CPU%, memory, current state, last seen; selected-process tracking and historical drilldown; service state/duration and changes. Separate ephemeral process identity (PID and creation start) from durable monitoring rule. Support Windows and Linux without assuming identical OS facilities.
- **API monitoring:** actual latest status/latency, check failures, freshness and bounded trend; no invented SLA.
- **Pentaho ETL:** only status, outcome, execution evidence, freshness/history and failures; no execute/stop/retry job controls.
- **Effective monitoring template:** actual applied version, override provenance, collector readiness and last telemetry; distinguish saved draft, validation, applied configuration and confirmed telemetry.
- **Apply/rollout:** per-target outcome, conflict or failure and retry when supported; never claim "3/3 applied" while a target failed.
- **Reports & Trends:** metric time range, aggregation, time-zone, scoped export and scheduled reports only with actual backend support; show as unavailable rather than nonfunctional UI.
- **Notifications and Alerts:** Email and PagerDuty only; provider delivery status evidence if available; no verified external closure claims. Never bring back removed Incident Management.

## 7. Accessible and responsive acceptance

Target desktop 1366/1440/1920 widths, tablet 768, mobile 390; no horizontal page overflow; dense tables may scroll inside their own region. Sticky filter/navigation must not obscure scroll destinations. Support keyboard-only search, tabs, tables, sidebars, drawers, error states and confirmation; visible focus, correct ARIA, screen-reader labels, minimum hit areas, WCAG AA contrast and reduced-motion preferences. Validate light/dark visual regressions where both supported. Do not use color without text/icon/status semantics.

Prefer configurable density with **Comfortable** (operator/default) and **Compact** (expert/admin) rather than shrinking all text to imitate a dense mock-up.

## 8. Implementation plan across approved development sprints

| Sprint | Design delivery / integration requirement | Gate |
|---|---|---|
| **1 Resource Management** | Introduce reusable tokens, shell, sidebar/topbar, filter primitives, role-aware context and resource/template workspace foundation; wire real existing resource/configuration behavior without expanding Sprint 1 beyond approved resource scope. | Accessibility, 390/768/1366/1920 screenshots, actual PostgreSQL/API/Playwright, tenant/RBAC negatives, no dead actions. |
| **2 Collectors** | Collector readiness and authenticated connection/freshness components shared by admin/operator. | Real agent/collector integration evidence, no claimed healthy state without sample. |
| **3 Telemetry / spool** | Live/stale/queued/error semantics connected to durable evidence and retry states; no cosmetic override of failed gates. | Fault/replay/tested true delivery and timestamp provenance. |
| **4 Host/process/service monitoring** | Full live performance, processes, services, selected monitoring, resource details. | Real Windows/Linux evidence and browser/API integration. |
| **5 Historical monitoring** | Time-series charts, range + interval controls, aggregation, drilldown, saved filters if approved persistence exists. | Real time-series DB/API/browser and time-zone/retention/pagination tests. |
| **6 API/Pentaho** | Real API status tiles, Pentaho monitoring-only panels and history. | Read-only Pentaho negative tests/provider limitations. |
| **7 Alerts/Notifications** | Attention-first alerts, Email/PagerDuty visibility, retry/status and correlation navigation. | Transport/error/idempotency evidence, no incident UI or provider-verified closure implication. |
| **8 Operational UI/Reports** | Finish full mock fidelity across pages, reports and role-adapted operator workspace; responsive polish, end-to-end user journeys and saved views. | Screenshot comparisons, accessibility and no dead controls across roles. |
| **9 Security/Performance** | Tune filter/query polling and keyboard/cross-tenant security under realistic workloads. | Security and performance metrics with explicit tolerances. |
| **10 Development Closure** | Full application visual/functional regression and owner review for design acceptance; verify every capability against implementation and evidence. | Explicit acceptance; only then consider final integration to main. |

The Sprint 1 scope is Resource Management and shared UI primitives, **not** an authorization to invent telemetry APIs, implement all later panels at once, or merge to main.

## 9. Mandatory verification and traceability

- Preserve the mandatory development testing policy in [MANDATORY_DEVELOPMENT_TEST_POLICY.md](../policies/MANDATORY_DEVELOPMENT_TEST_POLICY.md): real PostgreSQL, running FastAPI/React, Playwright, security, controlled faults where applicable, exact SHA and artifact hashes.
- Record screenshot-to-component acceptance at 1366 and 1920 as well as 768/390; compare side-by-side to owner reference when available, classify deviations rather than claiming identical pixels.
- Every visible control is mapped to a working backend-backed action, safe navigation, valid filter or clearly disabled/unavailable state; automated interaction test for each actionable control.
- Verify organization switching invalidates cache and prevents cross-tenant bleed; authorization enforced on API and UI.
- User journeys include admin configuring a resource and validating actual first telemetry; viewer finding a critical resource in 3 or fewer *primary* navigation actions, then reading scoped history. Times/interaction counts are UX targets to measure, not pre-existing evidence.
- Protect existing features and all 31 approved journeys; source missing for 30 original numbered journey definitions remains `SOURCE_NOT_RECOVERED`. Do not infer their canonical wording from the design picture.
- Track implemented, tested, role-qualified and owner-accepted states separately. Sample screenshot values are fictional visual placeholders and have **zero** evidentiary standing.
- All security/release gates remain unchanged: `CHK-001 FAIL`, `CHK-002 BLOCKED`, `SECURITY BLOCKED`, `RELEASE NO-GO`, `FORMAL_UAT PENDING`, `DEVELOPMENT_CLOSURE NOT COMPLETE`.

## 10. Codex steering sequence

1. Read this file, the approved program, Sprint 0 PR #83 review package and existing frontend routes/permissions.
2. Reconcile this new UI authority into the **Sprint 1–10 work plan** without rewriting sealed Sprint 0 evidence or claiming it was approved in original AUTH-694 text. It is a **later separate owner-approved UI decision**.
3. In Sprint 1 implement only safe shared design system/resource management work: responsive shell, tokens, scoped filters, resource detail configuration and real interactions. Preserve existing implemented behavior.
4. Keep operator-only view as a role-specific implementation requirement; obtain owner visual acceptance for the *specific operator mock* before claiming visual approval of that variant.
5. Stop after Sprint 1 for review. No merging into main, deploying, formal UAT or advancing unrelated gates.

**This document authorizes design-aligned work within approved sprint scopes; it does not certify any UI has been implemented or mark Sprint 1 started.**
