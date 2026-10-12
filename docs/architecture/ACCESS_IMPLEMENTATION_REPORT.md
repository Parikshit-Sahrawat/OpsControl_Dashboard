# P0 implementation report: customers, departments and access

Validated locally on 2026-10-12 on dedicated branch `feature/customer-department-rbac`, based on main `a845291a83cde941859dafe64134595cb5bd697c`. This report records development acceptance, not production deployment or independent human approval. The pull request remains unmerged.

## Implemented vertical slice

External Customers retain the `organizations` table and all existing resource foreign keys. Internal Departments and Employees belong to the independent operating provider (default PTC). Existing employee identities may join multiple departments; departments and employees have independent immutable UUIDs, optional unique codes/employee IDs, active status and provider-consistent foreign keys.

A fixed implemented permission catalog, immutable reviewed default roles, configurable custom roles, department/user assignments and paired role/customer grants enforce default deny. User customer denies and role restrictions narrow inherited access. Access Administrators receive identity administration and explicit monitoring-delegation authority without automatic monitoring access. Reserved administration identities and protected platform administrators cannot be taken over through a lower administrator's password reset, status change, inactive-role edit or department lifecycle change. The last active platform administrator remains protected.

The API checks authentication/module access, exact service actions, provider ownership and customer/action scope. Every existing session re-resolves current rights. Worker identities remain on their separate customer/resource/lease authentication boundary. The UI has Employees, Departments, Roles & Permissions, Customer Access and Access Audit with paging, search/filter, loading/empty/error/success states, confirmation and effective-access previews. Grant previews roll back all proposed writes. The global selector is operational-only and cannot affect internal administration or Resource Management's independent filter. Malformed cached preference objects are discarded before entering selector state.

Save dialogs remain busy until the refreshed snapshot is available. A browser regression holds a genuine authenticated response to verify that a late refresh cannot close a save early, switch table schemas or erase the next detail selection. No artificial health data or API responses are inserted into that check.

## Migration and compatibility

`backend/migrations/versions/0025_provider_department_rbac.py` follows `0024_notification_leases`. It adds nine tables: `service_providers`, `departments`, `department_memberships`, `permissions`, `roles`, `role_permissions`, `department_role_assignments`, `user_role_assignments`, and `customer_access_grants`. Existing `users` gains provider ownership, full name, optional employee ID and work email. PostgreSQL triggers protect UUID/provider ownership changes; composite FKs, indexes, grant uniqueness and effect checks enforce consistency.

Existing user UUIDs, password hashes, active/admin flags, customer UUIDs, resource relationships and sessions are retained. Legacy viewer/operator/org_admin memberships map to equivalent paired customer grants and compatibility roles, without becoming departments or access administrators. Unknown legacy roles abort the entire transaction. Post-migration API/CLI memberships remain visible through a read-only union without duplicate migration mirrors; revocation removes the authoritative legacy source.

Schema downgrade is refused. Retain the additive schema for an RBAC-capable application rollback. An older membership-only backend can ignore new restrictions and is an unsafe rollback target after access configuration changes. A pre-upgrade backup restoration is tested only in a separate owned database; production recovery needs separate approval and data reconciliation. See the [full mapping and rollback contract](CUSTOMER_DEPARTMENT_RBAC.md).

The [schema/model reconciliation](SCHEMA_MODEL_RECONCILIATION.md) resolves all 32 previously reported non-access differences without changing historical migrations or the database. Full-schema drift now fails acceptance.

## Local verification results

| Gate | Result and scope |
|---|---|
| Backend automated suite | 35 unittest cases passed; no skipped cases |
| Frontend unit suite | 4 Node tests passed, covering navigation/action scope, independent administrative pages, revocation and malformed cached selection |
| Frontend production build | Vite build passed; no new application dependency |
| Access migration/security runtime | 25 grouped real HTTP/PostgreSQL checks passed; populated 0024 upgrade, unknown-role transactional refusal, provider/department separation, grant precedence, self-escalation, protected credentials, concurrent contradictory grants, revocation and audit |
| Access browser runtime | 7 grouped real Chromium journeys passed, including manual employee/department creation, assignment, rollback-only preview/confirmation, independent filters, direct denial, modified cached preference/URL, stale-session revocation and delayed-response save regression |
| Legacy staging migration compatibility | Reversible 0024 smoke and populated 0016→0025 preservation pass before applying the protected head; probe refuses production/non-loopback or already-upgraded access databases |
| New schema comparison | No differences for the nine access tables and modified users table; migration head 0025 confirmed; unsafe downgrade refused |
| Full schema comparison | **Passes: zero differences across all 50 application tables**, real `alembic check` reports no new operations; no new migration or destructive DDL |
| HTTP/ETL/incident/NOC regression | Controlled verified HTTPS, live Linux host, read-only Carte-shaped lifecycle, failure/recovery, logs/steps/investigation/history, incident acknowledgment/resolution, tenant/worker negatives and all primary tabs in both themes passed |
| Release regression | Tenant/RBAC/secret/audit/worker negatives, Basic-auth HTTPS, controlled ServiceNow delivery, read-only EKS, collector contention/restart/recovery, paging over 205 resources, bounded retention, TLS/proxy/frontend headers and restricted production fixture roles passed |
| Populated backup/restore | Every row fingerprint and FK/CHECK/migration/audit integrity preserved across 51 tables, 913 rows and 190 constraints in the owned fixture |
| Docker demo | Final images rebuilt in an owned three-service project; head migration, zero-drift image-level Alembic check, random credentials, distinct customer/department UUIDs, idempotent bootstrap, frontend headers and API restart/session persistence passed; existing volumes untouched |
| API inventory | All 154 HTTP routes inventoried; existing human API routes have an explicit permission policy |
| Python syntax and diff hygiene | Compile and git diff whitespace checks passed |

Local Docker/browser labs are run sequentially. Concurrent Docker topology changes interrupted a Chromium development-module request with `net::ERR_NETWORK_CHANGED`; diagnostics identified the cause, and the complete serialized gate passed. No assertions were disabled and no automatic passing retries were introduced.

[Security checks](../screenshots/access-management/security.json), [migration](../screenshots/access-management/migration.json), [schema](../screenshots/access-management/schema.json), [browser](../screenshots/access-management/browser.json), [Docker](../screenshots/access-management/docker.json), [release regression](../screenshots/access-management/release-regression.json), [operational regression](../screenshots/access-management/operational-regression.json) and [primary-tab theme regression](../screenshots/access-management/ui-regression.json) contain redacted evidence. Private passwords, session tokens, old row/hash snapshots, dumps and failure diagnostics are not committed.

## Actual browser captures

| Screen | Capture |
|---|---|
| Employee identity and effective inherited access | [Dark](../screenshots/access-management/employees-dark.png) |
| Departments, UUIDs, memberships and paired scopes | [Dark](../screenshots/access-management/departments-dark.png) · [Light](../screenshots/access-management/departments-light.png) |
| Roles and implemented permission keys | [Dark](../screenshots/access-management/roles-dark.png) |
| Direct/inherited/legacy customer grants | [Dark](../screenshots/access-management/customer-access-dark.png) |
| Administrative action and denied-access history | [Dark](../screenshots/access-management/access-audit-dark.png) |

Theme state is explicitly asserted before each screenshot. These are captures of the running authenticated application backed by an owned PostgreSQL fixture.

## Required acceptance coverage

| Requirement | Verification |
|---|---|
| 1, 13, 14 — separate entities, stable IDs, preserved data | Additive populated migration snapshot plus UUID/uniqueness/integrity runtime assertions |
| 2, 3 — same role/different customers and multiple departments | Two department scopes and an employee joining/leaving both through the same existing identity/session |
| 4, 5, 18 — unauthorized/indirect identity access | Anonymous 401 and viewer/worker 403/401 across employee, department, permission, directory and legacy administration routes; browser refresh/manual URL checks |
| 6, 7 — no platform/self escalation | Platform flag/role creation denial, own role/grant/departments guards, DENY/inactive-role edit rejection and protected administrative credentials |
| 8, 10 — independent selected/customer authorization | Other-customer list/detail/mutation negatives, role/customer pairing and actual operational browser isolation |
| 9 — selector independent of administration | Global A selection while Resource Management displays B; own filter then works; Access Management has a neutral header and independent provider queries |
| 11, 12 — disable/session and last administrator | Old token/login denial, password-reset revocation, last-admin disable/demotion rejection and coordinated PostgreSQL race regression |
| 15 — invalid membership constraints | PostgreSQL invalid member/provider/effect rejection and paired grant FK enforcement |
| 16 — prompt permission updates | Existing token observes member/custom-role/deny changes immediately; browser clears caches/navigation and logs out on disable |
| 17 — audit actor/target/action/outcome/time | Success/denied administrative records, no credential serialization and append-only audit/incident history regressions |
| 19 — service identity scope | Worker identity retains its customer; lease/replay/foreign evidence negatives and direct employee API rejection |
| 20 — backend/frontend regressions | Backend suite, frontend tests/build, real browser gates, all-tab regressions and rebuilt Docker fixture |

## Exact local Docker verification

Run from a local checkout with Docker Engine/Compose (v2.24.4+ for `!override`) and Python 3. No cloud credentials are needed.

```bash
git fetch origin
git switch feature/customer-department-rbac
python3 scripts/access-docker-demo.py
```

The command builds a randomly named isolated project with generated private credentials and loopback ports, verifies it, and removes only its own test project/volumes. It leaves your existing demo/development database untouched. Redacted result defaults to `/tmp/opscontrol-access-docker-evidence/docker.json`; failure diagnostics remain in a private temporary directory.

To run the persistent fictional development demo after the isolated check:

```bash
bash scripts/demo-up.sh
docker compose -f docker-compose.demo.yml exec -T api alembic current
docker compose -f docker-compose.demo.yml exec -T api alembic check
docker compose -f docker-compose.demo.yml exec -T api python -m scripts.bootstrap_public_demo
```

Expected head is `0025_provider_department_rbac`. Open `http://127.0.0.1:5173`, sign in as `demo-admin` with the locally generated `.demo-private/admin-password` file, then check Customers, Employees, Departments, Roles & Permissions, Customer Access and Access Audit. The demo seeds three independent internal departments and one fictional customer without granting ordinary employee privileges. Keep the password file private. `bash scripts/demo-down.sh` stops the persistent demo and preserves its database; do not use volume deletion for that project.

If Docker dependency downloads require an organization CA, follow [trusted ephemeral build overrides](../DEPLOYMENT_UAT.md); `OPSCONTROL_BUILD_OVERRIDE=/absolute/path/to/compose.override.yml python3 scripts/access-docker-demo.py` supports the owned build gate. TLS verification remains enabled. Production uses separately reviewed TLS, owner-run migrations and restricted runtime/maintenance identities; this demo is not its deployment recipe.

## Full security/browser reproduction

Linux/macOS/WSL Bash, PostgreSQL Docker and Node 20.19+ or 24 are supported development prerequisites. Browser tooling is installed outside application dependencies.

```bash
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements-providers.txt -r backend/requirements-hosts.txt
npm ci --prefix frontend
npm install --prefix /tmp/opscontrol-access-tools --no-audit --no-fund playwright@1.56.1
/tmp/opscontrol-access-tools/node_modules/.bin/playwright install --with-deps chromium
export PLAYWRIGHT_MODULE=/tmp/opscontrol-access-tools/node_modules/playwright/index.mjs
(cd backend && .venv/bin/python -m unittest discover -s tests -v)
npm test --prefix frontend
npm run build --prefix frontend
ACCESS_BROWSER_ACCEPTANCE=1 backend/.venv/bin/python scripts/access-acceptance.py
```

The access harness owns its database/API/UI processes, tests a populated older schema, and cleans up only those fixtures. An installed `/usr/bin/chromium` is detected; otherwise Playwright uses its installed Chromium. `PLAYWRIGHT_CHROMIUM_EXECUTABLE` may explicitly select your approved browser. Execute additional networking labs sequentially:

```bash
RELEASE_BROWSER_ACCEPTANCE=1 backend/.venv/bin/python scripts/release-acceptance.py
OPSCONTROL_UI_THEME_ACCEPTANCE=1 backend/.venv/bin/python scripts/operational-acceptance.py
```

CI adds `.github/workflows/access-architecture.yml` with these access/Docker gates and uploads redacted screenshots/evidence. Existing unit, provider, HTTP, ETL, infrastructure, operational and release workflows remain in place. Remote CI and independent human review are separate pull-request states; they must not be inferred from local results.

## Unresolved risks and production gates

- The former 32 non-access drift groups are resolved by matching models to existing migration contracts; [the reconciliation inventory](SCHEMA_MODEL_RECONCILIATION.md) records each group. Full schema comparison is now a required CI gate. No production schema or data changes are needed.
- The owner accepts deliberately single-provider runtime authorization. Customer/provider ownership, login context and shared template ownership need an explicit review before enabling multiple independent operating providers.
- The owner is performing independent human security review and operator UAT locally; results remain owner-recorded acceptance gates. Deployment-scale authorization throughput is not proven by these controlled fixtures. Existing DB runtime credentials remain a trusted application boundary; ORM/API checks do not replace a separately reviewed DB isolation strategy.
- Production RTO/RPO, distributed target failover/host affinity, genuine AWS/Windows/Carte acceptance and approved audit/incident/ETL archive retention remain separate release gates. No production deployment or production data modification was performed.
- Schema rollback to older authorization software is unsafe after new grants/denies exist. Retain the additive schema and an RBAC-capable backend; follow the documented backup/recovery process.

## Files changed

The complete source/config/documentation list is recorded in `access-files-changed.json`; the PR diff is authoritative. Major changes are:

| Area | Exact paths |
|---|---|
| Existing schema reconciliation | `backend/app/models/entities.py`, `backend/app/services/rule_models.py`, `backend/app/worker/remote_models.py`, `backend/tests/test_schema_contract.py`, `SCHEMA_MODEL_RECONCILIATION.md` |
| Models/catalog/resolver | `backend/app/security/access_models.py`, `permission_catalog.py`, `access_control.py`, `models.py`, `scope.py`, `http.py`, `deployment.py` |
| Migration/API enforcement | `backend/migrations/versions/0025_provider_department_rbac.py`, `backend/app/api/access.py`, `activation.py`, `monitoring_diagnostics.py`, `operations.py`, `remote_protocol.py`, `rule_catalogs.py`, `backend/app/main.py` |
| Frontend identity/filter/permission UX | `frontend/src/pages/AccessManagement.jsx`, `ResourceManagementV2.jsx`, `MonitoringSetup.jsx`, `Overview.jsx`, `Incidents.jsx`, `Reports.jsx`, `frontend/src/App.jsx`, `api.js`, `permissions.js`, `operations.js`, `access-management.css`, `components/AuthGate.jsx`, `TopNav.jsx` |
| Acceptance and compatibility | `scripts/access-acceptance.py`, `access-docker-demo.py`, `etl-acceptance.py`, `infrastructure-acceptance.py`, `backend/scripts/access_acceptance_probe.py`, `access_schema_probe.py`, `auth_tenant_probe.py`, `bootstrap_public_demo.py`, `database_integrity.py`, `operations_acceptance_probe.py`, `release_runtime_probe.py`, `backend/tests/test_access_control.py` |
| Browser/unit/CI | `frontend/scripts/access_acceptance.mjs`, `permissions.test.mjs`, existing ETL/operational/theme/access capture scripts, `frontend/package.json`, `.github/workflows/access-architecture.yml`, `validation.yml`, `phase1-staging.yml` |
| Documentation/evidence | `README.md`, `docs/AUTHENTICATION.md`, `QUICKSTART.md`, `OPERATIONAL_ARCHITECTURE.md`, `IMPLEMENTATION_ROADMAP.md`, this report, `CUSTOMER_DEPARTMENT_RBAC.md`, pre-edit impact inventory and actual redacted captures |
