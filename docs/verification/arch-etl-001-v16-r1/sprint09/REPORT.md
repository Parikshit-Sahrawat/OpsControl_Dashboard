# Sprint 09 — Integration hardening and regression

Repository: `Parikshit-Sahrawat/OpsControl_Dashboard`.
Branch: `feat/arch-etl-001-v16-r1`.
Verified clean starting local/remote SHA: `99b38e532c958dce9b7a836d7c0e68dc0891f4ec`.
Verification date: 2026-10-17 UTC.

The approved `docs/architecture/ARCH_ETL_001_V16.md`, existing identities,
authorization infrastructure and Sprint01–08 evidence are preserved. Changes are
limited to reproduced query/transport defects, explicit-scope compatibility,
bounded archive access and their regression/measurement evidence. No new canonical
model, permission key, role grant, schema migration or dependency was introduced.

## Defects and scoped changes

| Finding | Change and verification |
| --- | --- |
| Inventory executes parameter/customer/parent lookups per row | Page-bounded, request-local ORM preloads for parameters, customer names, legacy API sources and linked hosts. Four SQL queries for a simple 26-row inventory; up to two additional batches for source/host bindings. No cross-request authorization cache. Measured before/after on the same 1,201-resource workload. |
| Execution pages query steps per execution; frontend fetches attempt counts per row | One windowed, bounded child query and one grouped attempt-count query for the page; five SQL queries for the tested three-execution page. Table consumes `attempt_count` directly. Older observed steps use a separate page. |
| Attempt previews fetch aliases/revisions per attempt and cannot retrieve older evidence | Batch window queries preserve the existing 200-alias/100-revision previews, add exact totals and offer validated nested archive pages. Drawer pages retained revisions/aliases. |
| Schedule UI only sees latest 500 occurrences and filters locally | Preserve the legacy schedule-window array; add a separate paginated occurrence API with server compliance filtering. UI pages retained history and does not infer NO_RUN. |
| Integration detail bounds some collections but not associations/sources | All collection previews are bounded at 500 with totals/has-more metadata; a fixed-allowlist records endpoint exposes older rows. Oversized readiness previews explicitly report incomplete; authoritative activation still performs its original complete validation. UI identifies partial previews. |
| Incident activity is limited to latest 200 and inventory lacks exact failure association filters | Preserve detail preview, add paginated activities and exact resource/history failed-execution filters. Incident inventory preloads native details once per page rather than once per incident. Existing seven-state lifecycle and recovery rules remain intact. |
| Pipeline-agent routes depend on a human-only scoped session | Separate database lifetime dependency for the three already-allowlisted transport handlers; existing agent/worker/customer authentication, locking, source binding and fencing remain authoritative. Real HTTP tests distinguish valid agent credentials reaching a missing-source 404 from human/revoked-agent 401. No source or workload is activated. |
| Older owned HTTP/browser probes omit explicit customer selection | Shared explicit UUID-snapshot helpers and affected documented examples updated. Missing/invalid authority stays empty or fails; ALL is never inferred. Third-party clients are not claimed as updated. |

The execution server outcome filter uses the canonical native projection, with
WAITING_FOR_RETRY taking precedence over a failed attempt. Native-only outcomes
are compared safely alongside the legacy PostgreSQL status enum. SUCCESS,
SUCCESS_AFTER_RETRY, FAILED, CANCELLED and UNKNOWN are not upgraded from process
exit or scheduler status. Manual recovery remains a separate execution.

Readiness truncation affects only the large integration **read preview**. It is
never an activation permission, runtime capability or successful monitoring result.
No incident restoration, evidence adjudication, replay, legal-hold or source-owner
semantics were redesigned. Existing review/recovery queues remain resource-scoped.

## Compatibility and pagination

The maintained client contract and complete route table are in
[API_CUSTOMER_SCOPE.md](../../../API_CUSTOMER_SCOPE.md).

| Consumer | Compatibility assessment |
| --- | --- |
| Existing application authenticated requests and customer selector | Existing Sprint08 explicit one/several/ALL behavior retained; generation guards and authorization-driven sensitive-state invalidation retained |
| Existing `schedule-windows` callers | Same array response, default/max limit and no offset; deterministic UUID tie-breaker added |
| Existing executions/attempts callers | Same items/total and canonical fields; child previews carry additional totals. Steps now have a 200-row preview and an explicit retained-step page for larger executions |
| Existing integration detail callers | Same collection keys; associations/sources now also capped, with explicit metadata. Consumers needing all retained records must use the new record pages |
| Existing incident detail callers | Same latest-200 activity preview and lifecycle; paginated activities are additive |
| New archive endpoints | `items,total,limit,offset,has_more`; 1–200 page size, nonnegative offset, deterministic ordering, fixed collection/status values |
| Legacy Python probes | Eleven direct human HTTP helpers updated; operations and ARCH001 runtime probes inherit updated helpers. Syntax/compilation and scoped compatibility tests executed; full legacy disposable stacks are not represented as rerun |
| Legacy Chromium raw requests | Access, access-v15, resource CRUD use an explicit authorized snapshot helper; consolidated UAT supplies its fixture customer UUID. These complete historical browser stacks are not represented as rerun |
| Agent/worker clients and public readiness checks | Separate existing service authentication/public metadata retained; no employee scope substituted |
| Third-party clients | Migration instructions documented; implementations and deployments outside this repository are **not updated or certified** |

New archive routes are read-only. Every page resolves current authentication,
customer selection and resource/parent authorization. Tests manipulate parent IDs,
foreign customer selections, bounds and collection values. Offset is not authority;
no opaque client-supplied cursor or arbitrary SQL sort/expression is introduced.
Pages are live queries, not frozen export snapshots; concurrent inserts can shift
offset positions. Existing source checkpoints and reconciliation cursors are not
used as frontend pagination tokens.

The old Sprint07 browser assertion assumed a synchronous client-side outcome
filter. It now waits for the verified server response and rendered row before
retaining its original one-result assertion. No prior acceptance assertion was
removed or relaxed. Read-only UI state remains separate from backend authority.

## Schema and preservation

Migration head remains `0037_access_boundaries`. No migration file or existing
schema model was changed. The disposable PostgreSQL gate runs the populated old
database upgrade, Sprint03–08 preservation probes, legacy multiple-department and
grant preservation, password-hash/history/evidence/hold snapshots, Alembic drift
checks, supported empty downgrade/upgrade and unsafe populated-downgrade refusal.
Existing composite ownership FKs, unique identities and immutable evidence/decision
protections are exercised by the retained regression suites.

No shared development/production volume is reset. The acceptance harness creates
and removes only its own named PostgreSQL container, temporary API/UI processes
and private fixture directory. Credentials and private failure diagnostics are
excluded from committed public evidence.

## Regression and security acceptance

Exact commands and scope lists: [commands.md](commands.md).
Public final results and screenshots: [evidence](evidence/).

| Gate | Actual final result |
| --- | --- |
| Backend unit, RBAC, adapter/runtime/transport and Sprint03–09 API contracts | 159 passed, zero failures/skips |
| Real PostgreSQL ownership, execution, review, history, incident and RBAC regression | 177 passed, zero failures/skips; eight new Sprint09 cases |
| Existing V1.6 and Sprint03–06 authenticated HTTP | 27 groups passed |
| Sprint08 authenticated HTTP | 14 groups passed |
| Sprint09 authenticated HTTP archive/compatibility/resilience | Six groups passed |
| Timed PostgreSQL ownership/duplicate/restart scenarios | Nine iterations passed; measured separately from request throughput |
| Existing configuration Chromium workflow | Passed |
| Sprint07 six operational pages Chromium | 16 groups passed |
| Sprint08 authorization/Access Management Chromium | Five groups passed |
| Sprint09 archive/filter/drawer Chromium | Three groups passed |
| Frontend tests | 22 cases passed; normal npm test also passed all three test files |
| ESLint / production Vite build | Passed; entry-chunk size warning remains |
| Scoped Black / scoped Ruff F,E9 / all changed Python compilation / mappers/imports | Passed in recorded scopes |
| Minimally edited legacy probes, full F/E9 comparison | No new diagnostics versus exact starting files; existing diagnostics remain, and full legacy Ruff is **not** claimed clean |
| Migration preservation, empty roundtrip, populated refusal, schema drift and source race 41/42 | Passed on owned PostgreSQL |
| Genuine Pentaho RT-001–RT-020 | **NOT RUN** |

Retained acceptance covers direct and inherited roles, applicable denies,
existing-session revocation, delegated self/escalation protection, independent
reviewers, evidence proof/revision/idempotency, manual recovery/original failure,
native schedules/coverage, historical notifications/closed incidents, eight other
platforms, source generations/leases/fences, audit retention and legal holds.

New regressions cover bounded SQL counts, more than 500 schedule occurrences,
more than 200 aliases, more than 100 revisions, more than 500 integration jobs,
nested parent IDOR, exact incident association filtering, unknown/incomplete
coverage, native-only outcome values and service/human authentication separation.
Only existing decision schemas authorize mutations; archive routes add none.

Development failures were corrected before delivery: large fixture resources
initially violated the existing mandatory job/resource binding, a schedule fixture
violated its unique occurrence constraint, fixture refresh affected an initial SQL
count, a UUID assertion compared the wrong Python representation, and browser
waits initially assumed visible `<option>` elements or synchronous filtering.
The retained constraints/assertions were preserved. The first bounded benchmark
exposed the inventory N+1 defect; its slower measurements are retained separately.
Earlier failed runs are not counted as passing acceptance.

## Bounded local measurements

The HTTP dataset contains five authorized customers, 1,201 resources, 207 execution
records, 603 schedule occurrences, 103 revisions and 206 aliases on one archived
attempt, and over 205 incident activities. Fixtures are explicit controlled data;
they do not establish verified native monitoring health.

The request benchmark runs a single local API worker and owned PostgreSQL on Linux,
Python 3.12, with three visible CPUs, plain loopback HTTP and no vendor traffic.
Twenty sequential one-customer inventory requests, forty requests at concurrency
four across five customers, and sixty mixed execution/evidence/schedule requests
at concurrency eight are measured. Latency includes authentication/resolution,
database access, serialization and loopback transport. No performance target is
invented; failures, duration, throughput and p50/p95/p99 are recorded.

The measured comparison is in [performance.md](performance.md), with the complete
machine-readable before/after samples. Each phase is one bounded local run; these
measurements are not production-scale, TLS, remote-network, endurance or native
platform certification.

Revocation overlaps 24 queued/concurrent reads. Five requests issued after the
mutation returns are denied, and no read started after that point succeeds.
Previously authenticated in-flight reads may complete under the established
per-request snapshot contract; protected mutations recheck in their transaction.

Three runs each of the existing two-session owner race, duplicate observation
reduction, and the new fresh-session retained-recovery restart are timed. The
restart test closes its session and discards source/operation objects after one
batch, loads the saved cursor in a fresh session, completes exactly the remaining
event, preserves the live checkpoint and refuses re-execution after completion.
This simulates loss of worker memory; it is not an OS-crash/failover exercise.
Small-sample resilience percentiles include setup and use the observed maximum
for p95/p99; they are scenario timings, not ingestion events/second claims.

## Remaining issues and Sprint 10 readiness

No genuine runtime or production readiness is established. RT-001–RT-020 remain
NOT RUN and require separately approved installations, credentials, native
artifacts and independent acceptance. No workload is executed or source activated.

Remaining limits: cross-resource queues are still resource-scoped; offset pages
can shift under concurrent insertion; integration configuration UI retains a
clearly marked 500-row preview while older collections are available via the
paginated API. Full legacy browser/disposable stacks and third-party client
migrations are not certified by this delivery. Existing legacy-probe Ruff findings
remain unchanged; unrelated broad cleanup was deliberately excluded.

Exact count/window queries still inspect the scoped retained range. Larger policy
sets, deeper archives, global authorization-write lock contention, multi-worker
deployments, remote latency, process/host failures, long-duration load and live
notification delivery remain unmeasured. Further optimizations should follow
query plans and measured contention, not speculative schema changes. The Vite
entry-chunk warning remains; bundle restructuring is outside these verified fixes.

Sprint10 may proceed with these explicit limitations when separately authorized.
This is integration-hardening readiness, not native runtime sign-off. No PR,
merge, deployment, production monitoring activation or ETL workload execution
occurred. Delivery stops after commit/push and remote-SHA/clean-tree verification.

Changed paths: [changed-files.txt](changed-files.txt).
Implementation integrity: [source-sha256.json](source-sha256.json).
The delivery commit is the commit containing this report; its SHA is reported in
the completion response rather than embedded in its own content.
