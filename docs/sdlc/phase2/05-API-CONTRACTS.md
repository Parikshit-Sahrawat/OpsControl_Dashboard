# 05 — REST API and Worker Event Contracts (Proposed)

## Existing API assessment
Current app mounts `/api/v1/organizations`, `/api/v1/resource-management`, `/api/v1/monitoring`, `/api/v1/etl` and investigation routes. Resource CRUD overlaps between `resource-management` and `monitoring` routers. Existing request organization filters are optional and do **not** enforce authorization.

## Contract conventions
- Authenticate by validated bearer/OIDC identity; worker service identities use separate scoped credentials.
- All tenant-owned operations derive permitted organizations from the authenticated principal; filters only *reduce* permitted scope.
- Create responses `201`; activation asynchronous requests `202`; successful idempotent changes `200`; no content `204`.
- `401` missing/invalid identity; `403` not authorized (or consistent `404` for hidden resource); `409` conflicts; `422` invalid config; `503` connector unavailable.
- Consistent JSON errors: `{code, message, request_id, details?}`; never expose connection secrets or source response bodies that may contain credentials.
- Pagination/ordering documented; scoped counts and lists use the **same filter contract**. No unbounded response triggered by selecting "All."
- Idempotency keys on activation and event ingestion; timestamp semantics UTC ISO 8601.
- Maintain backward compatibility in existing routes until migrated behind deprecation/versioning; do not add more parallel CRUD implementations.

## Proposed endpoints (NOT implemented)
| Method | Path | Role / semantics |
|---|---|---|
| GET | `/api/v1/me/organizations` | Permitted organization list for UI selector |
| GET | `/api/v1/data-sources` | Scoped list with status, environment, type and pagination |
| POST | `/api/v1/data-sources` | Org-admin create, organization permission checked |
| GET | `/api/v1/data-sources/{id}/effective-configuration` | Derived preview and diagnostics; does not imply execution |
| POST | `/api/v1/data-sources/{id}/activation-preview` | Validate desired diff, show generated objects and secret/reference requirements |
| POST | `/api/v1/data-sources/{id}/activations` | Authorized, idempotent apply; returns activation ID/status |
| GET | `/api/v1/data-sources/{id}/activations/{activation_id}` | Desired/applied revision, state, conflicts and errors |
| POST | `/api/v1/data-sources/{id}/deactivate` | Disable generated monitoring without erasing history |
| GET | `/api/v1/collectors/{id}/runs` | Scoped execution evidence |
| GET | `/api/v1/metrics/{id}/samples` | Scoped, bounded numeric observations |
| GET | `/api/v1/log-sources/{id}/events` | Scoped, bounded log observations |
| GET | `/api/v1/dashboard/kpis` | Scoped totals and filter tokens |
| GET | `/api/v1/etl/executions` | Scoped ETL executions, scheduled/actual state |
| GET | `/api/v1/audit-events` | Restricted audit history |

Route names are proposals; final OpenAPI contract should minimize breaking changes from current `monitoring` routes.

## Activation example (illustrative)
```json
{
  "desired_template_versions": [{"template_id": "uuid", "version": 2}],
  "overrides": {},
  "validate_only": false,
  "idempotency_key": "client-generated-stable-key"
}
```
Response `202` contains `activation_id`, `status: ACTIVATING`, `desired_hash`, `warnings`, and a pollable status URI; `ACTIVE` is only set after validated reconciliation. Collector `HEALTHY` requires runtime evidence.

## Worker event contract (proposed)
Use a versioned record `{event_id, schema_version, organization_id, data_source_id, collector_id, run_id, observed_at, source_identity, evidence_type, payload, trace_id}`. Worker-owned results use stable idempotency key per source execution/sample; retry must not duplicate evidence/alerts. Source-origin `FAILED` must not be inferred from transport `NO_RESPONSE`.

## Critical negative tests
- Anonymous POST/PATCH and GET must reject (run 37987379543 demonstrated current HTTP 200).
- Org-A user may not GET/PATCH org-B Data Source even if full UUID is known.
- Template attachment cannot cross organization unless explicitly global/authorized.
- Concurrent activation request with same idempotency key returns same resulting revision, no duplicates.
- KPI totals match filtered lists with the same authorized query scope.
