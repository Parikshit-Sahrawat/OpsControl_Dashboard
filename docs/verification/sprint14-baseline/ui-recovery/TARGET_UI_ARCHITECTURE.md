# Target UI architecture proposal

Authority: [ARCH-001](../../../ARCH_001_V16.md), [ARCH-ETL-001](../../../architecture/ARCH_ETL_001_V16.md). This document proposes presentation and navigation changes only. Approved resource, employee, authorization, collection and evidence identities remain unchanged.

## Plane separation and page ownership

| Plane | Owner and existing view | Target presentation boundary | Existing dependency |
| --- | --- | --- | --- |
| Resource Management | Customer Organizations; VM, ETL and API resources; Pentaho integration wizard; collectors, sources, collection methods; event/alert/delivery configuration | One canonical inventory/configuration workflow. List → detail → permitted edit, with collector → configured-method list. No parallel onboarding in monitoring pages. | `UnifiedResourceManagement.jsx`, `DataPipelineIntegrations.jsx`, `CollectorControl.jsx`, `/api/v1/unified/resources`, `/api/v1/data-pipelines/integrations`, `/api/v1/agent-control/collectors`. |
| Access Management | Internal employees/departments, roles, customer grants, LIMIT/DENY/DELEGATE boundaries and audit | Workforce administration and customer access assignments; never customer Organization ownership. Distinguish direct and inherited permission sources where the effective-access contract supports it. | `AccessManagement.jsx`, `AccessBoundaries.jsx`, `/api/v1/access/*`. |
| Operations | Dashboard, six pipeline pages, compute, API, alerts, native incidents and reports | Health, freshness, execution/incident evidence and permitted investigation. Resource details link to canonical configuration owner. | `UnifiedOverview.jsx`, `PipelineWorkspace.jsx`, `DomainMonitoring.jsx`, `NativeIncidents.jsx`, `/api/v1/unified/*`, `/api/v1/native-incidents/*`. |

## Shared interface patterns

Use the existing shell and tokens from `visual-system.css` and pipeline styles rather than a second design system. The proposed page shell has (1) breadcrumb and title, (2) scope/freshness summary, (3) permission-gated primary action at the right edge of the page header, (4) compact search and filters, (5) a paginated table/list with bounded columns and a clearly visible horizontal-scroll affordance on small screens, and (6) a detail drawer or page. Summary cards, when used, link to filtered records. A configuration state must be named as such and visually separate from monitoring health.

Keep loading, zero-scope, empty, partial/stale, error and forbidden states distinct. Keep explicit timezone presentation, stable severity/status vocabulary and claim-specific evidence. Forms use labeled sections, field errors, save/cancel and revision conflict messages. Primary action placement is a UI concern; no endpoint changes are implied. Provide readable focus outlines, Escape/close focus restoration, `aria-current`, keyboard tab order and touch targets. Desktop, tablet and mobile acceptance should measure both page-level and table-internal overflow.

## Collector details

`CollectorControl.jsx` already supports identity/OS settings, a separate Add Method form, and multiple method rows with edit, enable, disable and remove. The proposed redesign makes this sequence visible: create/edit collector → select OS/deployment type where supported → save → add one method through its own form → inspect/manage method list → repeat. Existing backend revision, source ownership and permission checks remain in force. Show OpsControl Agent, OpenTelemetry Collector/infrastructure, collector configuration, collection method and telemetry class (logs, metrics, traces) as different concepts. Agent installation or unsupported collection capability must not be exposed as working merely because a configuration label exists.

## Migration rule

Update the shared shell and one module at a time, retaining current components, endpoints and permissions until regression evidence exists. Keep legacy compatibility surfaces reachable while checking their actual usage. Do not remove functions or change backend data ownership for visual cleanup. Backend changes are **not established as necessary** by this audit; a contract gap needs a reproduction, route/schema review and separate owner authorization before work.
