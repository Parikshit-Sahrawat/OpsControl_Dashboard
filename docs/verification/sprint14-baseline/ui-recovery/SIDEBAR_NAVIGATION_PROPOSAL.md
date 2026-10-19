# Sidebar and navigation proposal

This is an owner-review proposal against the [current audit](CURRENT_UI_AUDIT.md), not an approved route change. Keep the existing permission resolver, customer selector and operational subpages. Grouping must never broaden authorization.

| Current flat navigation | Proposed grouped navigation using existing views |
| --- | --- |
| Overview | Overview → Dashboard (`Overview`, label change only) |
| Data Pipeline Monitoring; Compute Health; API Endpoint Monitoring; Alerts; Incidents; Reports | Operations → Data Pipelines (all six existing tabs), Compute Instances, API Endpoints, Alerts, Incidents, Reports |
| Resource Management (internal tabs) | Resource Management → Organizations, Data Sources / Resources, Collectors; Event Parameters, Alert Rules and Notification Delivery remain reachable as configuration/policy entries. Collection Methods stays inside the selected collector unless an independently useful route is approved. Monitoring Templates appears only if the existing implementation and permissions support a stable entry. |
| Access Management (internal tabs) | Access Management → Employees, Departments, Roles & Permissions, Organisational Access (existing customer grants and boundaries), Access Audit |
| No separate administration page verified | Administration → existing settings only if located and authorized; no placeholder link. |

Current paths are primary in-memory page keys; only the Data Pipelines subpages have hash paths in `PipelineWorkspace.jsx`. A proposed persistent sidebar entry therefore needs a navigation-state/deep-link design before implementation. Preserve the six pipeline hashes, browser Back behavior, initial-page selection and current scope clearing. Do not introduce broken direct links while changing labels.

The existing top sidebar toggle, 240/72 px states, `aria-current`, icon components and collapsed labels can be reused. Proposed improvements: clear group headings, a visible active group + child state, persistent icon-only collapse on desktop, tooltips and accessible names, keyboard-operable group expansion, and a compact mobile drawer or clearly signaled overflow with focus return. The current narrow top strip is scrollable but its hidden entries have weak discoverability in [mobile evidence](evidence/390-access.png). A mobile solution must preserve customer selection and the separate meaning of “All listed customers” versus explicitly authorized `ALL customers`.

Use `canNavigate` and effective-access projection to hide unauthorized destinations, and keep the page guard plus backend authorization. Hide unauthorized actions inside pages according to existing permissions. A navigation redesign may expose an existing Access Management customer-grant view, but it must not convert internal departments into customer Organizations or grant access by selecting a customer. The incident page and pipeline Incident Correlation tab should remain separate entry points to the same native incident records until the owner chooses a single primary navigation pattern.

Owner decisions: exact labels/group placement for Alerts, Incidents, Reports and Resource Management policy pages; whether Organizational Access is a first-class tab; whether Collectors is a sidebar destination or a resource-detail child; whether all pages gain stable URLs; and the mobile navigation pattern. These are proposals, not changes to approved architecture.
