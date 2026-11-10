# OC-S01-UI-001 — Resource Management sidebar correction

Review date: 2026-11-10, Asia/Calcutta.

- Baseline PR89: `ecfdff2cf3f9d1a7b7b284e79a7f708d1baea8ce`.
- Implementation and tested application: `f39596548a45f48d3e24a2ea76b7584634d67a18`.
- CI gate follow-up: `60c0037b15e5ec681949727fd181a2f6aefdc22e`; product and test-script content is unchanged by this one-line workflow flag.
- Dedicated branch: `fix/oc-s01-ui-001-resource-navigation`. PR89 and the closure-resolution branches/evidence are untouched.

## Behavior

Resource Management expands directly to Organizations, Compute Instances, Data Pipelines, APIs, Collectors, Monitoring Templates, Event Parameters, Alert Rules and Notification Delivery. The generic Data Sources / Resources entry and redundant Workspace configuration subgroup are gone from this category.

The three management destinations select the existing shared inventory using VM, ETL and API domains. Sidebar, component selector and domain tabs remain synchronized. Active highlighting, breadcrumbs, organization/environment filters, reload, keyboard controls and browser history are verified. The legacy `#/resources/data-resources` bookmark remains supported. Global search opens the matching management domain.

Operations uses the requested Data Pipeline Monitoring, Compute Health, API Endpoint Monitoring, Alerts and Reports labels. Its existing monitoring components remain separate. Frontend addresses for previously unaddressed views support history/reload without new backend endpoints or duplicate pages. Existing Access Management functionality remains.

Section synchronization preserves collector-editor handoffs. No stylesheet, backend, database model/migration, monitoring behavior, permission catalogue or collector pin changed. Historical browser selectors were updated for the renamed destination while retaining their functional assertions. Two new mandatory unit cases were added to the scope inventory; all 817 previous records remain unchanged. The existing workspace CI job enables the ten new browser groups without changing its identity, permissions or thresholds.

## Final-source verification

| Check | Result |
|---|---|
| Frontend | 57 passed: 55 retained, 2 new; 0 failed/skipped |
| Lint / production build | PASS; existing bundle-size warning retained |
| PostgreSQL ownership | 56 passed; 0 failed/skipped |
| PostgreSQL configuration/security | 46 passed; 0 failed/skipped |
| Authenticated HTTP | 15 retained groups passed |
| Browser | 10 new navigation, 9 retained resource-security and 15 retained workspace groups passed; pipeline journey passed |
| CI policy / workflow syntax | PASS; actionlint covers all 28 workflows; all 13 required contexts preserved |
| Desktop captures | 6 before and 18 domain-specific after images, covering both roles and all three requested resolutions |

The two PostgreSQL suites contain 102 distinct test identities. Unit/API/browser groups are not added together as a single coverage count. Real PostgreSQL 17.11, FastAPI, Vite and Chromium were used. Fresh migration, refusal of unsafe populated downgrade, 108-table restore and selected configuration crash/restart/replay probes passed; these are not collector disk-durability certification.

Both administrator and operator exercised all three inventories at 1920×1080, 1440×900 and 1366×768. Operator mutations returned 403 for VM/ETL/API. Foreign-customer inventory was denied or empty. A real account without `resources.view` had no management-domain links or direct-route inventories, and all three domain API requests returned 403. Existing backend authorization uses `resources.view` across these inventories; no new domain permission was invented. ETL monitoring retains its separate `etl.view` permission.

Existing browser assertions preserve create/edit/reload, template version pins and association, immutable history/diff/detach/rollback, staging, stale conflicts, revocation and delayed authentic tenant responses. Exact commands, test identities and raw evidence are in COMMANDS.json and TEST_RESULTS.json. [Before/after images](SCREENSHOTS.md) and [changed code paths](CODE_CHANGED_FILES.txt) are linked.

## Attempts and acceptance limits

Retained failures include an outdated generic-directory expectation and a subsequently introduced reverse-domain helper predicate error. Both were corrected without weakening assertions. The first successful browser attempt used an intermediate uncommitted tree and is not final-source acceptance evidence. The final run is pinned to the implementation commit above. The initial documentation validator ran before the package was complete; its failure is retained, followed by final validation.

No confirmed defect remains in the tested scope. Owner visual acceptance of this navigation correction is PENDING. Only selected screenshot pairs were manually inspected; no pixel-equivalence or comprehensive accessibility certificate is claimed. No formal UAT, genuine-provider qualification or production/shared UAT access occurred. Existing independent image, licence, durability and release blockers remain.

Four task-owned containers and their API/UI processes/private fixture inputs were cleaned by exact identity. No broad Docker cleanup, PR closure or remote branch deletion occurred. Hosted CI will be recorded as TRIGGERED — RESULT PENDING after the draft PR; no completion polling.

**SECURITY BLOCKED · CHK-001 FAIL · CHK-002 BLOCKED · RELEASE NO-GO · Collector 0.123.0 unchanged · Sprint1 NOT COMPLETE.**
