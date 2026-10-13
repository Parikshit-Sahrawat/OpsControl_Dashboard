# Authentication, internal access and customer ownership

OpsControl separates external customer ownership from service-provider identity administration. See the [model, migration and precedence contract](architecture/CUSTOMER_DEPARTMENT_RBAC.md) and [implementation acceptance report](architecture/ACCESS_IMPLEMENTATION_REPORT.md). These development checks do not constitute independent human security review or production authorization.

## First administrator

Apply migrations in an isolated development database following [Quickstart](QUICKSTART.md). From `backend/`, run:

```bash
python -m scripts.create_admin --username admin
```

The command prompts for the password, hashes it server-side and refuses to create another bootstrap administrator once one exists. Never supply passwords as command arguments or commit credentials. Existing upgraded accounts/password hashes are preserved. No default production account or public sign-up is introduced. The localhost Docker demo uses a random private password file and fictional resources only.

## Ownership and roles

The `organizations` table represents **Customers**. Its resource, application, VM, ETL, collector, monitoring, incident and evidence relationships remain unchanged. The operating provider (default display name **OpsControl Services**) owns independent **Departments** and **Employees**. An employee has one immutable user UUID. New creation/assignment requires exactly one existing department; legacy unassigned or multiple memberships are preserved until explicitly transferred. Departments never reuse customer UUIDs. A manager designation grants no authority.

| Role | Internal administration | Customer operational rights |
|---|---|---|
| Platform Administrator | Protected break-glass capability; last active account cannot be disabled/demoted | Bypasses customer grants; reserved for protected administrators |
| Access Administrator | Employee/department/role/grant administration and access audit | None automatically; monitoring access needs an explicit role/customer grant |
| Resource Administrator | None automatically | Customer resource/policy management when scoped; customer creation itself grants no ownership access |
| NOC Operator | None automatically | Scoped monitoring, ETL investigation and incident acknowledgment |
| Incident Operator | None automatically | Scoped monitoring, incident acknowledgment/investigation/notes/resolution |
| Read-Only Viewer | None automatically | Explicitly scoped observation/evidence views |

Defaults are immutable reviewed roles. Create custom roles from implemented permission keys instead of editing defaults. Configurable roles cannot create platform administrator status. Only existing platform administrators may delegate `access.*`, `audit.view`, or break-glass authority. Other administrators with the relevant management permission may delegate the catalog's monitoring permissions, independently of their own monitoring grants. They cannot modify their own role, deny, inactive-role or department inheritance paths. Department activation and deactivation check the authority over existing roles again. Accounts assigned reserved administration permissions, including inactive roles/departments, require platform authority for another administrator to change their credentials, lifecycle or authorization. This prevents password-reset or account-enabling takeover of a stronger administrative identity. An administrator may edit their own profile/reset their own password; self-authorization changes remain denied.

Default deny applies. Customer-specific actions require both the relevant permission and its customer scope. A customer's selected UUID never grants access. Department role and customer grant are paired; membership in departments with different roles does not produce a cross-product of every role and every customer. Employee customer DENY overrides inherited/legacy scope; employee role DENY subtracts those permission keys. Contradictory direct grants are rejected, including concurrent requests serialized per employee. Inactive accounts/providers/departments/roles grant no corresponding access.

## Administration workflow

1. Sign in with `access.view` and the necessary `access.manage_*` action.
2. Open **Access Management → Employees**; create an employee with full name, username, optional employee ID/work email and a strong initial password.
3. Create custom **Departments**, including optional code, description and manager. Add existing employee identities; do not create duplicate customer-specific accounts.
4. Assign reviewed or custom roles under department/employee details. The roles page provides a matrix of actual implemented backend actions.
5. Open **Customer Access** or a subject's detail to pair an assigned role with a customer. Review the server-validated preview before confirming. Previews roll back all proposed database mutations.
6. Review **Effective access**, including provider permissions, department/direct/legacy sources, customer scopes and employee restrictions.
7. Review **Access Audit** for actor UUID, target, action, outcome and timestamp. Deactivation, password reset and grant revocation are audited. Sensitive actions require explicit confirmation.

Employees, departments, grants and audit lists are paginated with total counts. Independent search/status/department/role/customer filters do not consume the global selector. Administrative option directories fetch bounded pages without silently omitting later employees/departments.

The global selector is hidden on Access Management and Resource Management. Operational pages list only authorized customers, and intersect selection with action-specific authorization. Resource Management owns its own customer filter. Authorization refresh invalidates stale operational/detail state.

## Sessions and backend enforcement

`POST /api/v1/auth/login` returns an opaque random bearer token with a 12-hour expiry. PostgreSQL stores only its digest. Browser sessionStorage holds the tab-scoped token. Logout, password reset, account disabling and protected-account changes revoke sessions. Disabled users cannot authenticate or reuse old tokens.

`GET /api/v1/auth/me` preserves old identity/membership fields and adds effective permissions, paired customer permissions, inheritance/restrictions, role IDs and an authorization revision. The backend recalculates database-backed rights on **every request**, including existing sessions. The UI refreshes authorization on window focus and every five seconds; backend enforcement does not wait for that timer. A minimal `/api/v1/auth/customer-scope` directory supplies the operational selector. `/api/v1/access/customer-directory` is separately authorized internal grant-target metadata, not operational access.

Middleware and route dependencies reject unauthorized module access, and services enforce the exact action/provider identity. Customer-scoped ORM reads and writes restrict the actual customer's permitted action. Anonymous access returns 401. Authenticated module/action denial returns 403; detail/mutation queries outside an authorized customer action scope return 404 without disclosing records. Changing owner foreign keys or referencing another customer's resources is forbidden. No frontend button is an authorization boundary.

Legacy `/api/v1/auth/users` and `/memberships` remain platform-only compatibility APIs. `organization_memberships` remains customer access, never department membership. Migrated and post-migration legacy API/CLI memberships appear in the new customer-grant list; explicit revocation deletes the authoritative legacy source. Direct SQL/CLI identity writes are trusted operator actions and must not be exposed to ordinary employees.

Worker tokens remain separate service identities bound to a customer and configured/leased resource jobs. Human roles do not authorize a worker to browse employee information. Local provider collection, remote worker enrollment and shared global template mutations retain their protected platform boundary. An ETL investigation permission does not execute/restart a job.

## Development validation and remaining gates

Run the owned PostgreSQL/browser and Docker commands in the [acceptance report](architecture/ACCESS_IMPLEMENTATION_REPORT.md). Existing HTTP, ETL, incident, remote-service, restore, retention and deployed TLS fixture regressions are retained.

The deployment is **single-provider**. Adding independent providers requires a reviewed customer/provider ownership and login-context design. PostgreSQL 17 is the validated database target. The database runtime role must remain a restricted non-owner with append-only audit privileges; apply capability grants after every owner-run migration. Direct SQL bypasses application authorization, so database credentials and migration/maintenance identities are trusted deployment boundaries.

Production rollout, independent security review/operator UAT and genuine AWS, Windows and Carte acceptance remain separate gates. The schema check records unrelated existing monitoring-model drift; no destructive reconciliation is generated automatically. Do not revert to an older membership-only backend after new restrictions are configured; follow the additive rollback contract.
