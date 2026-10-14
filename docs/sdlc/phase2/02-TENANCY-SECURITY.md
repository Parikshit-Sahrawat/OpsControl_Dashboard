# 02 — Identity, RBAC and Tenant Isolation (Proposed / P0)

## Evidence driving design
[Staging run 37987379543](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/actions/runs/37987379543) confirmed HTTP 200 from anonymous organization list, data source list/detail and update endpoints; unfiltered responses exposed both synthetic organizations. **Current application is not safe to expose to untrusted networks.**

## Identity and authorization contract
- Authenticate every non-health route using an OIDC/JWT or trusted reverse-proxy identity contract. Identity provider and token verification configuration require separate review.
- Derive `principal_id`, platform role and `allowed_organization_ids` from a validated session/token and server-side memberships.
- Authorization defaults to deny. Per-resource reads/edits require membership plus capability; absent organizations must never be inferred from user-supplied query arguments.
- A request's selected org IDs must be intersected with **allowed** org IDs; an unauthorized specific ID returns a consistent 403 or privacy-preserving 404. Empty org selection is not a reason to disclose all tenants.
- Global monitoring templates are a separate explicit platform permission; organization-owned templates may only attach within authorized orgs.
- Establish the same enforcement for ETL executions, investigations, alerts, correlations, collector runs, metric samples, log events, attachments and exports.
- Audit actor/organization/action/resource/outcome; redact tokens, credentials and response bodies containing secrets.

## Proposed permissions
| Capability | NOC Operator | Support Engineer | Org Admin | Platform Admin |
|---|---|---|---|---|
| Read authorized dashboards/jobs/alerts | Yes | Yes | Yes | Scoped/all by explicit platform role |
| Investigate/annotate | Yes | Yes | Yes | Yes |
| Create/edit Data Sources & attachments | No | Request/approved | Yes | Yes |
| Run connectivity tests | No | Approved | Yes | Yes |
| Modify alert thresholds | No | Approved | Yes | Yes |
| Manage organization memberships | No | No | Own organization | All |
| Manage global templates/platform configuration | No | No | No | Yes |
| Configure secrets and notification endpoints | No | No | Approved controlled UI | Yes |
| Remote remediation | No | No | No | Out of initial scope |

Roles and permission names are proposals; enforce permissions in shared dependencies and/or a service policy layer, not scattered ad hoc checks.

## Data-layer isolation and integrity
- Prefer tenant-bound entities carrying `organization_id`; where parent-derived, join through authorized parent using enforced predicates.
- Ensure `MetricDefinition.organization_id`, `Collector.data_source_id`, alert rule, log source and evidence all match the Data Source's organization. Prevent cross-tenant FK combinations with service validation and, where practicable, composite database constraints.
- On updates, never allow changing `organization_id` without an explicit admin-only move workflow.
- Optional PostgreSQL row-level security can provide defense in depth after testing connection-role/pooling behavior; **not** a substitute for API authorization.

## Collector and external-source safety
- Collector credentials are secret **references** resolved only in worker scope; avoid passwords in template/config JSON, API responses and logs.
- Apply outbound SSRF protections to user-configurable HTTP URL collectors: host allowlist or network policy, reject metadata/loopback/private networks except explicitly approved development sources, bounded response sizes, redirects and timeouts.
- TLS certificate verification on by default; never silently fall back to insecure transport.
- Pentaho and VM source credentials must be read-only, minimally scoped. No arbitrary command execution.
- Audit and rate limit configuration changes and connectivity checks.

## Required authorization test matrix
User A only in org A, user B only in org B, org admin A, platform admin, anonymous. Test GET list/detail, POST with forged org ID, PATCH/DELETE by B ID, multiple-org query filters, template attachment, metric/log/alert writes, read of nested runs and ETL investigations. Confirm 401 for no identity; 403 or 404 for unauthorized identities, no B data disclosed to A; ensure audit log. This cannot be fully executed until authentication exists (#2).

## Release gate
**P0**: all negative authorization tests passing; documented key rotation/secret policy; no anonymous write or cross-org disclosure. The existing staging smoke must not be reinterpreted as a passing security test.
