# Sprint 08 — Granular RBAC, delegated administration and customer scope

Repository: `Parikshit-Sahrawat/OpsControl_Dashboard`
Branch: `feat/arch-etl-001-v16-r1`
Verified starting HEAD and remote: `410a0cb1956fd5d732e7bdd394fd99676810fc4b`
Starting working tree: clean. Verification date: 2026-10-17 UTC.

The canonical authorization resolver, scoped ORM, authenticated session, permission
catalog and Access Management APIs are extended in place. No permission keys,
default role grants, customer identities or employee memberships are seeded or
rewritten. The approved architecture and Sprint 01–07 evidence remain unchanged.
External customer Organizations and internal employee Departments remain separate.
OpsControl remains monitoring-only; no workload-control capability was added.

## Effective access and scope contract

The existing resolver combines direct roles, active department-inherited roles,
paired customer grants and compatible legacy memberships. Existing global
permission denies and customer denies still win. Inactive employees/providers or
invalid persisted boundary specifications fail closed. The effective projection
adds contributing boundary identity/revision/specification and explicit ALL
authority to existing direct/inherited role provenance and deny information.

An additive `access_boundaries` record constrains these existing assignments:

| Kind | Meaning | Grant authority |
| --- | --- | --- |
| LIMIT | Exact permission/customer pair restricted to specified environments/resources; all applicable LIMITs intersect | None |
| DENY | Exact permission/customer pair denied wholly or for matching environments/resources; applicable denies win over LIMITs | None |
| DELEGATE | Employee administration budget of internal departments, customer IDs and implemented permission keys; optional empty-department creation | Must be issued explicitly by a platform administrator; still requires existing access-management permissions |
| ALL_CUSTOMERS | Extends one already-assigned active role using an explicit permission snapshot, either recorded customer IDs or explicitly including future active customers | Platform-controlled; cannot invent role permissions or confer provider administration |

Within one restriction, environment and resource qualifiers must both match when
both are specified. Multiple values in a qualifier are alternatives. Separate
delegations cannot combine permission/customer/department dimensions into a wider
cross product: one budget must cover the complete proposed operation. The
established protected `User.platform_admin` break-glass flag retains its authority
and explicit ALL capability; ordinary configurable roles cannot create that flag.

Authenticated operational requests use `X-OpsControl-Customers` with comma-separated
immutable customer UUIDs, an empty string, or the exact elevated value `ALL`.
Existing `organization_id`/`organization_ids` query filters further intersect the
header selection. Without either explicit selection, the scope is empty. Wildcard
strings are rejected. Requested IDs are intersected with current authorized
customers; zero authorized customers exposes zero customer records. Selecting all
listed IDs is an explicit snapshot selection, never an ALL grant.

This intentionally tightens the previous implicit scope default: external human
API clients must send explicit customer filters. Existing acceptance clients now
do so. `/auth` identity/customer-directory metadata and `/access` delegated
administration use their independent authorized scopes rather than the operational
selector. Agent transport retains its separate existing handler authentication.

Tenant and resource criteria apply in SQL before pagination and nested reads.
Environment/resource restrictions cover inventories, executions/attempts, schedule
and review evidence, recovery links, native incidents, historical policies and
pipeline source/configuration paths. Shared sources/integrations/incidents require
all referenced resources to be visible; ambiguous/unbound references fail closed.
One shared restriction plan is built per query. Unrestricted customer IDs use an
expanding bind rather than repeated SQL branches; tests cover 1,001 selected IDs
and one inventory SQL request without per-row permission queries.

## Permission and route matrix

All existing route policies remain authoritative. Resource restrictions are
evaluated for the actual action, including the exact incident handler permission
rather than borrowing the alternative permission in the middleware's OR gate.

| Operation / existing contract | Required permission and additional authority |
| --- | --- |
| Operational execution, attempt, schedule, evidence-review and recovery reads under `/api/v1/unified/resources/{id}` | `etl.view`; current selected customer and resource scope |
| Unified resource catalog/detail | `resources.view` where required by the existing catalog contract |
| Recovery-link proposal, confirmation, reversal under `/executions/{history_id}/recovery-links` | `etl.investigate`; server actor, independent confirmer, original failure preserved |
| `/evidence-reviews/{review_id}/decision` | `etl.resolve_identity`; verified native evidence, expected revision, reason, idempotency |
| `/api/v1/data-pipelines/sources/{id}/recovery` accepted-evidence reconciliation | Existing `etl.configure` write gate plus `etl.replay`; retained-evidence bounds/generation/holds/fencing unchanged |
| `/api/v1/data-pipelines/operations/{id}/approve` for elevated accepted-evidence replay | Existing `etl.configure` gate plus `etl.approve_replay`; independent authenticated actor and current source generation |
| Supported data-pipeline configuration | `etl.configure` plus existing resource/source ownership and independent approval rules |
| `/api/v1/native-incidents` reads | `incidents.view` |
| Native incident acknowledge, investigation, assessment, transition and other mutations | Exact existing `incidents.acknowledge` or `incidents.manage`; seven-state lifecycle and verified recovery rules unchanged |
| `/historical-notifications` | Existing `alerts.view` read / `templates.manage` policy write; current scoped resource |
| `/api/v1/access/employees`, departments, memberships, roles, customer grants | Existing `access.view` plus exact existing management key; explicit complete DELEGATE budget for ordinary administrators |
| `/api/v1/access/audit` and effective-permission views | Existing audit/effective-access requirements; delegated subject/customer filters prevent unrelated identity exposure |
| `GET /api/v1/access/boundaries` | `access.view`; ordinary employees see only their applicable projection; platform sees provider policies |
| `POST /api/v1/access/boundaries`, `PATCH /boundaries/{boundary_id}` | Platform flag plus `access.manage_permissions`; strict specification, immutable subject/kind, reason, idempotency; PATCH requires expected revision |

## Delegated administration and decision safety

Ordinary delegated administrators can manage authorized employees, departments,
assignments and customer grants only within one explicit budget. They cannot edit
their own authorization path, grant provider administration or ALL, remove
applicable explicit restrictions/denies, or change a shared role with assignments
outside their delegation. Whole-role footprint checks deliberately use unfiltered
Core queries so administrative list filtering cannot conceal outside assignments.
Privileged/protected accounts and last-platform-administrator protections apply on
both canonical and legacy identity routes.

New employees still require exactly one active internal department. The existing
single-department trigger and form remain in force. Existing legacy multiple
memberships and their valid inherited permissions are preserved. An explicitly
authorized empty-department creation extends that administrator's existing budget
with the new immutable department ID and records the revision/audit; it grants no
roles or customer access to that department or any employee.

Authorization mutations and authenticated human decision transactions share a
PostgreSQL advisory transaction lock. After acquiring it, the authoritative
transaction re-resolves active employee/provider access and checks the permission
revision and exact session token/expiry. Revocation cannot commit between that
check and a protected decision. Sessions close on denial. Existing sessions are
re-resolved on every request; replay workers also recheck current author/reviewer
permissions and source/resource authority at use time. Existing legal holds,
source generation, leases/fences and decision revisions remain enforced.

Boundary writes use actor-scoped idempotency keys and body hashes, locked revisions,
immutable before/after decisions and the established security audit. Equal retries
return the recorded result; different bodies with the same key or stale revisions
fail with 409. Role permission PATCH uses a required content-revision fingerprint
returned by the role list; stale edits fail with 409. Actual concurrent boundary
HTTP edits are tested: one succeeds and one receives 409. Independent recovery
confirmation and replay approval use authenticated server identity; forged actor
fields cannot substitute for it. Privilege never fabricates native outcome proof.

## Frontend integration

The existing authenticated request layer carries explicit selected UUIDs/ALL.
The selector shows authorized customers and exposes ALL only with the resolver's
explicit capability. Clearing the last customer now leaves an empty scope.
Resource Management retains its independent explicit administrative filter.
Authorization/customer/session revisions invalidate the Sprint 07 workspace and
Access Management, clearing sensitive feeds, drawers, rows and pending actions.
Existing feed abort/generation guards remain in use. Exact action affordances
also check environment/resource restrictions, while server denial is definitive.

Access Management retains compact employee/department/role/customer lists and
direct/inherited Effective Access. It now explains applicable restrictions,
delegation and ALL/future semantics, constrains permission choices to delegation,
and includes confirmed platform-only boundary create/revise/deactivate forms.
Ordinary administrators receive a read-only policy projection. The new policy form
creates employee policies; department policies are supported by the API and can
be revised in the UI once present. No redesign of the six operational pages or new
frontend dependencies was introduced.

## Additive migration

`0037_access_boundaries`, after `0036_native_recovery`, creates two tables only:
`access_boundaries` and append-only `access_boundary_decisions`. Constraints enforce
one subject, provider ownership, supported kind, positive revision, employee-only
delegation, JSON-object specification and actor/key uniqueness. Restrictive FKs and
a PostgreSQL immutable-history trigger protect decision evidence. API validation
enforces actual catalog/role/customer/resource identities and ownership.

No existing assignment/membership/history/hold is rewritten. The owned database
preservation probe hashes 15 existing authorization/history/audit/hold tables,
including a controlled pre-existing employee with two departments, across the
0036→0037 upgrade. Empty downgrade/upgrade and Alembic schema drift checks run in
the gate. Populated downgrade explicitly refuses to discard policies or audit
decisions; retain the compatible schema or restore a verified backup. This is an
intentional preservation safeguard, not an automatic destructive rollback.

## Executed verification

Exact commands are in [commands.md](commands.md); file lists for Black, scoped Ruff
and compilation are stored alongside their logs. Final public evidence is in
[evidence](evidence/). Credentials, tokens, fixture passwords and private failure
diagnostics are excluded.

| Final gate | Actual result |
| --- | --- |
| Backend unit, RBAC, eight-platform adapters, Sprint 03–07 contracts | 155 passed, 0 failed/skipped |
| PostgreSQL ownership/execution/review/history/incident/RBAC regressions | 169 passed, 0 failed/skipped; includes 22 new Sprint 08 cases |
| Existing authenticated V1.6 + Sprint 03–06 HTTP acceptance | 27 groups passed |
| New authenticated Sprint 08 HTTP authorization acceptance | 14 groups passed |
| Existing configuration Chromium workflow | Passed, including mobile/eight-step onboarding |
| Sprint 07 six-page Chromium acceptance | 16 groups passed |
| Sprint 08 authorization/Access Management Chromium acceptance | 5 groups passed |
| Frontend permissions/pipeline tests | 20 passed, 0 failed/skipped |
| ESLint / Vite production build | Passed; nonblocking bundle-size warning remains |
| Black / Ruff `F,E9` / Python compilation / imports and mappers | Passed in recorded scopes |
| Existing populated upgrade, S03–S08 preservation, empty roundtrip, populated downgrade refusal, schema drift, ownership race 41/42 | Passed on owned PostgreSQL |
| Genuine Pentaho RT-001–RT-020 | **NOT RUN** |

Black checks the 21 substantive/new Python files. Five older HTTP probes receive
only the explicit-selection helper import/call and necessary unused-import cleanup;
their pre-existing whole-file formatting is intentionally excluded. Ruff and
compilation include all 26 changed Python files. No whole-repository formatter or
unrelated cleanup was applied.

Development failures were resolved before the final gate: the expanded ALL dataset
exposed repeated restriction SQL construction, fixed with one shared query plan
and a bounded-SQL regression; the browser exposed the missing CORS allowance for
the selection header, now allowed; migration fixture ordering was corrected to
check prior sprint snapshots before inserting the S08 legacy fixture. New test
fixture/accessor errors were corrected. Earlier failed runs are not counted as
passes. Default sandbox local-socket tests were rerun in the approved local test
environment; no vendor endpoint was contacted.

## Security acceptance coverage

| Requested acceptance | Evidence |
| --- | --- |
| 1–5 one/several/ALL/future/unauthorized ALL/empty | Sprint08 PostgreSQL choice tests, authenticated HTTP selection/pagination/IDOR/ALL groups and selector browser checks |
| 6–8 direct/inherited/combined/denies | Resolver PostgreSQL regressions, preserved two-department fixture, applicable LIMIT intersection and DENY tests |
| 9–10 new single department / legacy multiple preservation | Actual employee HTTP creation, migration hashes and inherited-access assertions; browser form |
| 11–13 delegation/escalation/last administrator | Allowed and denied actual HTTP writes; shared-role/outside assignment check; canonical and legacy last-admin protection |
| 14–15 cross-customer manipulation / revocation | Actual scoped inventory/detail/pagination/query tests; existing-session grant revocation and live browser revision invalidation |
| 16 evidence adjudication | Allowed/denied actual HTTP decisions, stale revision/idempotency/forged actor tests; existing review native-proof regressions |
| 17 recovery independence | Existing Sprint03 HTTP and PostgreSQL proposal/confirm/reverse/self-confirmation/foreign-history tests; Sprint07 drawer browser |
| 18 replay/independent approval | Sprint05 actual HTTP and PostgreSQL approval/generation/fence/hold tests; new current resource-authority worker test |
| 19 incident/historical notifications | Actual scoped HTTP reads/policies and exact incident-action restriction test; existing verified-recovery/closed-history tests |
| 20 concurrent/stale/idempotent | Actual simultaneous authenticated boundary edits, role fingerprint conflicts, idempotent audit count and immutable decision PostgreSQL test |
| 21 frontend unauthorized controls/cache | Chromium ALL/revocation/drawer/delegated policy checks; frontend permission and generation tests |
| 22 eight other platforms | Existing adapter, runtime/transport and API contract regressions; configuration Chromium workflow |
| 23 ownership/fences/holds/audit | Full PostgreSQL regressions, source race 41/42, prior-sprint and S08 preservation, append-only ledger tests |

Screenshots genuinely captured from the owned local backend include all six
operational pages, execution/review/schedule/incident drawers, mobile/tablet
inventory, and elevated/delegated/revoked Access Management states. They are
controlled acceptance fixtures, not proof of native provider health.

## Remaining risks and Sprint 09 readiness

No known failing acceptance gate remains. The explicit-selection requirement needs
to be carried to any separately maintained human API client. Ordinary existing
AccessAdministrator roles retain their recorded keys but need a deliberately
issued delegation before administrative writes; there is no automatic migration
grant. Platform provisioning of boundaries is an authorized operational rollout
step and was not performed against any real environment.

The global authorization transaction lock deliberately favors revocation safety;
large-scale contention/load testing remains outstanding. Shared/unbound resource
scope fails closed and can conservatively hide whole source/incident records.
Boundary lists are not yet paginated; department-policy creation uses the API.
Role revisions are configuration fingerprints rather than a new historical
version table. The Vite entry chunk is 504.85 kB minified (142.75 kB gzip), triggering
the existing 500 kB warning; no unrelated bundle refactor was attempted.

Sprint 09 may proceed with these recorded limits when separately authorized.
No Sprint 09 cleanup or Sprint 10 final acceptance was performed. Genuine runtime
certification, exact installed-build artifacts and RT-001–RT-020 remain outstanding.
No production data changes, real-source activation, Pentaho workloads, PR, merge
or deployment occurred. Delivery stops after committing/pushing this sprint and
verifying the remote SHA and clean working tree.

Changed paths: [changed-files.txt](changed-files.txt). Source integrity manifest:
[source-sha256.json](source-sha256.json). Delivery commit is the commit containing
this report; it is intentionally not embedded in its own hashed contents.
