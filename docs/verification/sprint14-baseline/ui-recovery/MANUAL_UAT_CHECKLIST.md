# IUAT-S14-UI-003 manual UAT checklist

Use an isolated synthetic UAT database and the feature-branch UI. Record browser, viewport, user role, customer selection, screenshot and actual result for each item. Do not treat mock or synthetic monitoring states as live. This checklist is pending independent UAT.

- [ ] At desktop width, inspect Overview, Operations, Resource Management and Access Management groups; confirm every existing permitted destination remains reachable and active indication follows selection.
- [ ] Collapse and expand the desktop sidebar with keyboard; verify icon names/tooltips, focus indication and preference persistence after refresh.
- [ ] At 390 px and 768 px, open mobile navigation, activate each permitted destination, close with Escape and confirm focus returns to the toggle. Check that hidden groups are not visible to unauthorized users.
- [ ] Select one customer, several explicitly authorized customers, no customers and explicit ALL (only with a grant). Switch scope while a drawer and request are open; confirm prior customer data clears.
- [ ] In Resource Management, inspect Organizations separately from internal Access Management Departments. Create/edit an authorized VM, ETL or API resource from the page header; confirm no create action appears in filters.
- [ ] Inspect resource configuration state and corresponding operational health/freshness. Confirm an enabled configuration is not presented as verified healthy telemetry.
- [ ] In a collector detail, add two independently configured collection methods, edit one, and check the method list and permission-denied states. Do not start a live agent or workload.
- [ ] In Access Management, verify exactly one contextual Create Department action, then Employee and Role actions on their respective tabs. Check guided onboarding, direct/inherited grants, restrictions, audit and legacy memberships.
- [ ] Visit all six Data Pipeline pages, including filters, pagination, drawers, UNKNOWN/INCOMPLETE states, retry identity and incident permission notices. Check VM and API operational pages and existing Alerts, Incidents and Reports navigation.
- [ ] At 390/768/1366 px, inspect table scroll cues, long identifiers, modal bounds, sticky headers and page-wide overflow. Compare against original IUAT screenshots when available.
- [ ] Repeat a representative create/investigate action as a read-only user; confirm the control is unavailable and a direct forbidden backend request still fails.

Record defects separately with exact reproduction. Pentaho RT-001–RT-020 remain NOT RUN without separately authorized real installed-build acceptance. Do not sign off production readiness from this UI UAT.
