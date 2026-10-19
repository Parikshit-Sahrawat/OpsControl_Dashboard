# Explicit customer selection for human API clients

Sprint 08 requires an explicit customer selection on operational HTTP requests.
Selection filters current authority; it never grants a role or customer access.
This applies to resource, execution, evidence, schedule, recovery, incident,
notification, replay and resource-configuration APIs, including nested details.

1. Authenticate using the existing `/api/v1/auth/login` session contract.
2. Read `/api/v1/auth/customer-scope` with that bearer session to obtain current
   authorized immutable customer UUIDs. This directory is independent of the
   operational selection and must not be cached across authorization changes.
3. Send the user-selected UUID or comma-separated UUIDs in
   `X-OpsControl-Customers`. An explicit `organization_id` query also selects a
   scope; when both are present the query further intersects the header.
4. An empty header, omitted selection, or zero authorized customers exposes no
   operational customer data. Wildcards are rejected. A JSON body customer ID,
   pagination offset, cached ID or resource ID does not establish selection.

```http
GET /api/v1/unified/resources?domain=ETL&limit=20&offset=0
Authorization: Bearer [EMPLOYEE_SESSION_TOKEN]
X-OpsControl-Customers: [AUTHORIZED_CUSTOMER_UUID]
```

For several customers use the exact authorized UUID list. `ALL` is a distinct
elevated selection available only when `/api/v1/auth/me` reports
`all_customers_authorized`. Its policy independently specifies an existing-customer
snapshot or future-customer coverage. Selecting every currently listed UUID does
not confer ALL. Missing authorization never falls back to ALL or platform access.

On 401, discard session-sensitive cached responses and reauthenticate. On 403 or
404, clear denied rows/drawers/pending actions and refresh effective access; do not
retry with broader scope. On an authorization revision change, invalidate scoped
requests and caches. Existing permitted in-flight reads use the established
per-request authority snapshot; subsequent requests re-resolve current access.
Protected human mutations also recheck authority/session in their transaction.

The `/api/v1/auth` identity APIs and `/api/v1/access` delegated administration use
their existing independent metadata/administrative scopes. Internal Departments
remain separate from monitored customer Organizations. Agent/worker ingestion
uses its existing separate credentials and customer/source bindings; do not send
an employee scope header as a substitute for service authentication.

Role permission PATCH requests must include the `authorization_revision` captured
from the role list as `expected_revision`. A 409 requires operator review of the
new configuration; do not automatically refresh and overwrite it. Merely assigning
an AccessAdministrator role does not create an administrative delegation. Owned
historical fixtures or third-party tools expecting provider-wide employee lists
or writes must be provisioned with an explicit approved DELEGATE boundary. This
sprint does not add broad grants to make old fixtures pass.

## Owned client compatibility

| Client family | Sprint 09 treatment |
| --- | --- |
| Application React requests | Existing Sprint08 authenticated layer supplies explicit UI selection; administrative filters remain explicit and independent |
| V1.6 and Sprint03–08 HTTP/Chromium probes | Existing explicit selection retained; full applicable gate rerun |
| Legacy HTTP probes: access, auth/tenant, ARCH001, consolidated UAT, ETL, infrastructure, golden path, live HTTPS, remote protocol, security release and release-runtime scale | Shared `scripts.acceptance_scope.probe_headers` explicitly selects the current authorized UUID snapshot; empty/invalid authority fails closed; no implicit ALL |
| Operations and ARCH001 runtime probes | Inherit the updated ETL/ARCH001 request helper |
| Legacy access/access-v15/resource CRUD Chromium raw requests | Shared `frontend/scripts/explicit_scope.mjs` supplies the current authorized snapshot |
| Consolidated UAT Chromium raw requests | Supplies its explicit fixture customer UUID |
| Worker/agent clients, gateway smoke, readiness/health/OpenAPI checks | Separate service authentication or public metadata; no human customer scope substituted |
| Pre-authentication phase1 staging probe | Remains an intentionally unauthenticated diagnostic; it cannot gain operational access and is not certified as a current authenticated acceptance workflow |
| Third-party integrations | **Not updated or certified**. Their owners must implement this contract and test permitted, forbidden, empty and revoked selections |

Snapshot selection in controlled probes is a deliberate test-client choice; it is
not a new application default. Full legacy disposable stacks are not claimed as
rerun solely because their raw HTTP helpers were updated. Historical verification
reports remain unchanged. Older consolidated enterprise documents are historical
snapshots; this contract and live OpenAPI describe the current development branch.

## Bounded operational archives added in Sprint 09

Existing arrays/detail previews remain available. New page responses use
`items,total,limit,offset,has_more` with `limit` 1–200 and nonnegative `offset`.
Ordering includes a deterministic UUID tie-breaker. Every page repeats current
authentication, selected-customer and resource checks; offset is never authority.
No client-supplied SQL sort/expression or opaque cross-customer cursor is accepted.

| API | Additive behavior |
| --- | --- |
| `GET /api/v1/unified/resources/{id}/executions` | Optional canonical `outcome` server filter; batched `attempt_count`, bounded `steps` preview with `steps_total,steps_has_more`; existing items/total retained |
| `GET .../executions/{history_id}/steps` | Page retained observed steps; no inferred step support |
| `GET .../schedule-windows` | Existing latest-occurrence array and limit retained |
| `GET .../schedule-occurrences` | Page all retained occurrences with optional validated compliance `status`; UNKNOWN/INCOMPLETE do not imply NO_RUN |
| `GET .../executions/{history_id}/attempts` | Existing 200-alias/100-revision per-attempt previews preserved, now batched with exact child totals |
| `GET .../attempts/{attempt_id}/aliases` or `/revisions` | Page older retained alias/revision evidence; parent execution/attempt binding verified |
| `GET /api/v1/data-pipelines/integrations/{id}/records/{collection}` | Page `connections,capabilities,methods,jobs,operations,associations,sources` using a fixed allowlist |
| `GET .../integrations/{id}` | Existing arrays bounded at 500 with per-collection pagination metadata; oversized readiness preview explicitly incomplete; actual activation validation unchanged |
| `GET /api/v1/native-incidents` | Optional exact failed-execution association `resource_id` and `history_id` filters; unknown associations are not inferred |
| `GET .../native-incidents/{incident_id}/activities` | Page older native activity; existing 200-activity detail preview retained |

Execution/review queues remain resource-scoped. This sprint does not add a global
cross-resource queue. Offset pages are live queries rather than frozen snapshots;
concurrent insertion/removal may shift positions. Consumers needing a stable
export must use a separately defined snapshot contract, not assume offsets are a
durable replay cursor. These operational reads do not modify source checkpoints.
