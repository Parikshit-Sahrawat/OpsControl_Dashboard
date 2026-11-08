# External React Reference — UI Patterns Accepted for Consideration (Functionality-First)

**Recorded:** 2026-11-08.
**Source:** Owner-supplied pasted React demo, `Pasted text(20261108-032306).txt` (roughly 749 lines), provided in OpsControl conversation. The original source file has **not** been checked into the repository. Do not claim a GitHub-authored source or silently copy its functional implementation.
**Classification:** Non-authoritative UI reference / reusable interaction patterns only. Not an OpsControl feature specification, approved capability register, working telemetry implementation, or integration evidence.
**Related visual spec:** [Overview visual reference](OC_OVERVIEW_VISUAL_REFERENCE_V1_2026-11-08.md) and [global UI/UX v1.1 functionality-first](OC_UI_UX_APPROVED_V1_2026-11-08.md).

## Useful source patterns to adapt to OpsControl

| Source feature | UI pattern worth retaining | Required OpsControl adaptation |
|---|---|---|
| Expand/collapse grouped sidebar and mobile overlay | Responsive, space-efficient hierarchical navigation | Extend existing `frontend/src/components/TopNav.jsx`, preserving its real routes, permission guards and multi-organization controls. Keep escape/focus behavior; no second navigation tree. |
| Pinned bookmarks/favorites near top of sidebar | Speed for recurring operational journeys | Link to **real, authorized existing routes**, hide revoked destinations on RBAC/scope changes, and only persist if existing client preference contract supports it (or explicitly approved local-only preference without security/tenant leakage). Do not pin excluded views. |
| Route-aware breadcrumb and active-state labels | User orientation and fewer clicks | Derive from OpsControl router/section state, not a static NAV_GROUPS demo; consistent with back/forward/deep-link behavior. |
| Topbar search and scope controls | Fast resource/task discovery | Preserve OpsControl's actual multi-org and PROD/QA/TEST/DEV/SANDBOX semantics; only expose a search that truly queries available authorized data, with empty/error states. |
| Compact status/KPI cards with colored icons | Scan quickly for urgent conditions | Real, permission-scoped counts and correct drilldowns; accessible status text and freshness, no fabricated percentages. |
| Reusable area/line/bar chart containers, legend, tooltip and axis styling | Readable monitoring visualizations | Reuse installed components or consider a chart library only after dependency/security review; bind to real data and proper units/timezones. Honor historical-trends-in-Reports current product decision. |
| Inline severity filter chips + search on log stream | Efficient, task-focused evidence filtering | Apply to **existing authorized evidence/log APIs** when actually supported; bounded pagination, log retention, masking and tenant filters. No generated live stream. |
| Visible pause/play live control and manual refresh | Operator control over polling and screen stability | Wire to actual fetch/subscription lifecycle; pause must cancel/stop requests and manual refresh must really reload; show data sample timestamp vs UI refresh timestamp and stale/error state. |
| Status badges, right-aligned metrics, concise rows | Dense but legible operational scan patterns | Consistent shared OpsControl light-first theme; accessible contrast and no icon/color-only states; mobile wrapping. |
| CSS microinteractions and content transitions | Pleasant navigation without excess animation | Reduced-motion support, avoid continuous flashing/bouncing and excessive rerenders. |

## Explicitly **DO NOT IMPORT** from the demo

- `generateTimeSeries()` uses `Math.random()` for RPS/errors/latency/CPU/memory; charts are **mock data**, not monitoring results.
- `setInterval` generates randomized pretend ingestion logs every two seconds. It is **not** an OpenTelemetry stream, collector integration, or durable-ingestion verification.
- `setLogs(prev => [...prev])` on demo Refresh is not a real fetch or refresh.
- Hard-coded incident banners, `INC-8921`, status percentages, fake services, infrastructure panels, topology state, alert count badges, 'OTel Ingestion 99.98%', `14.2k req/s`, sample hostnames and 'Collector v0.92.0 connected' are **not evidence**.
- Demo `PulseTrace`, Prometheus/Vector/Jaeger branding is external reference, not OpsControl brand or verified collector architecture. Keep OpsControl identity and existing telemetry contracts.
- `Active Incidents`, `Triage Incident`, `Incident Management & Alerts` are **excluded incident-management UI**. OpsControl **background alerts and permitted alert drilldowns remain included**.
- `Container & K8s Cluster`, k8s nodes/pods, Kubernetes workload monitoring are **excluded**. Kubernetes remains a permitted **OpsControl deployment target**, not a monitored workload feature.
- `Distributed Traces`, trace explorer, waterfall analyzer, full service mesh/topology and bespoke 'Prometheus Stream' panels must **not** be inferred as approved implemented functionality from this example. Investigate existing approved source/authority separately before proposing capabilities.
- The demo's `prod/staging/dev` environment taxonomy is not a substitute for OpsControl's authorized PROD/QA/TEST/DEV/SANDBOX values.
- Do not copy third-party library dependencies blindly. Validate installed Lucide/Recharts equivalents, license, bundle/performance and security first.
- No imitation of demo's always-dark theme as the OpsControl default; the approved Overview and global theme are **light canvas + navy sidebar**. Preserve optional real theme toggle.
- Avoid nonsemantic clickable `<div>` with nested `<button>`, hover-only pin buttons without keyboard focus, unsafe live log excerpts, flashing/bouncing continuous animations and low-contrast tiny text.

## Suggested engineering adoption

**Within Sprint 1 shared UI and Resource Management scope:** audit existing `TopNav.jsx` and effective router; add only non-disruptive shell polish, current-context breadcrumbs, appropriate saved/pinned navigation patterns if permitted, responsive/keyboard state and semantic/status token consistency. No invented search API, streaming, new entity type or backend mutation. Scope strictly to approved resource workflows and global UI primitives.

**Sprint 4/5:** use chart style/axis/legend patterns for genuinely delivered Windows/Linux current and historical metrics; chart data and process/service filters must be backed by real agent/API/DB evidence.

**Sprint 6/7:** use log and severity-filter patterns only for actual authorized API/Pentaho/evidence/alert feeds; preserve Pentaho read-only semantics, log retention and approved background alerts. No incident UI.

**Sprint 8:** complete global visual consistency, pinning/saved view experience when data/preferences contracts allow, responsive and accessible operators' journeys, reports and chart/panel refinement.

## Codex acceptance instructions

1. Do not paste the demo's `App` component into the OpsControl app. Audit real routes, auth permissions, components and dependencies; create `source feature → current route/contract → presentation reuse → parity test` mapping.
2. Implement **UI-only adaptations** during the authorized sprint, except separately scoped and approved product features under their own tickets. No backend/model/security logic changes just to match demo.
3. Use real FastAPI/PostgreSQL/React/Playwright tests; inspect live filters, authorized route clicks, keyboard, multi-org scopes, mobile breakpoints and test-level uncertainty. No mock-generated telemetry in application screens or certification.
4. Differentiate `Implemented`, `Proposed`, `Source not recovered`, `Unsupported`, `Unavailable` and `Not tested`.
5. Maintain the existing OpsControl approval, exclusions, 14-step closure gates and `CHK-001 FAIL`, `CHK-002 BLOCKED`, `SECURITY BLOCKED`, `RELEASE NO-GO` conditions. No intermediate `main` merge or formal UAT.

**Outcome of this document:** reference patterns recorded for Codex; no application code, DB schema, tests or source telemetry changed by this documentation-only update.
