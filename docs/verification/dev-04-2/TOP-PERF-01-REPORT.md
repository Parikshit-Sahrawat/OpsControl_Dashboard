# TOP-PERF-01 — bounded topology traversal and contention evidence

**Status: `PARTIALLY_RESOLVED`.** The cycle check now uses one bounded PostgreSQL reachability query instead of one SQL query per visited node. Correctness, authorization, rollback and PR #60 regressions passed on disposable PostgreSQL. The customer-wide transaction lock remains necessary under the present design, and concurrent writers still wait on it. No narrower lock was shipped without a concurrency proof.

## Source and environment

- Starting `origin/main`: `535f81d55a07d2e1b2fe199539850989658d3437` (PR #61 merged). Implementation commit: `329220af9b35f0fd55ea8c4a6dca9ac974cf9198`. The final evidence commit is the PR head; its exact SHA is recorded in the PR and submission response because a commit cannot contain its own hash.
- Branch: `fix/dev-04-2-top-perf-01`. Only [the topology handler](../../../backend/app/unified/api.py), [disposable benchmark probe](../../../backend/scripts/topology_gate_probe.py), [read-only parity probe](../../../backend/scripts/topology_read_parity.py), [focused tests](../../../backend/tests/test_topology_traversal.py), and this evidence package changed. No migration, model, public API, customer/RBAC, Kubernetes, frontend, deployment, or CI file changed.
- Date: 2026-10-23–24 UTC. Disposable, volume-free `postgres:17-alpine` containers on loopback ports 32854 (unchanged main) and 32855 (optimized branch) for the matched timing run; PostgreSQL **17.11**. Alembic head **`0038_k8s_cluster_associations`**. Python **3.12.14**, SQLAlchemy **2.0.43**, Alembic **1.16.5**, psycopg **3.2.10**, FastAPI **0.143.0**, Pydantic **2.14.1**. Pool size 8, overflow 8. Runner: 3 reported CPUs, 9.7 GiB memory; shared-runner load uncontrolled. No existing database or Docker volume was reset.
- Reproduction dataset: seed **420042**, exactly **1,000** synthetic VM resources and **3,000** valid active dependencies, split evenly across two customer Organizations with overlapping names but distinct UUIDs. Each customer has a depth-479 chain, high fan-in/out nodes, disconnected nodes, and 1,500 acyclic edges. Eight overlapping operations were run concurrently. [PR #61's verification report](REPORT.md) specifies the dataset and original gate.

## Cause, query plan, and correction

`add_dependency` previously walked `resource_id → depends_on_id` in Python and issued one active-edge query per visited node while holding a customer-wide `pg_advisory_xact_lock`. A matched unchanged-code rerun reproduced **261–280 SQL statements per creation**. On the benchmark's 253-node reachable subgraph, the old per-node lookup used the current-edge index repeatedly; network/ORM round trips dominated total transaction time.

The replacement uses a parameterized SQLAlchemy recursive CTE. `UNION` deduplicates node identities, the recursive term includes only active dependencies for the already-authorized customer, and an outer **1,000-node limit** preserves the existing validation bound. A 1,000-node reachable result is rejected; 999 is accepted. The query walks the entire bounded reachable set before deciding whether the new child is reached, avoiding a new early-exit timing shortcut. It returns no graph identities to the API. [Measured CTE plan](TOP_PERF_CTE_PLAN.json): Recursive Union → indexed bitmap lookup on `ix_resource_dependencies_resource_id`, 253 output nodes, 24 recursion loops, **0.9 ms** execution on a warmed disposable database. This plan is local evidence, not a production guarantee.

The existing transaction-scoped customer lock, endpoint authorization, `FOR UPDATE` recheck, audit event, uniqueness constraint, and commit behavior remain. Endpoint-only locks were rejected: simultaneous `A→B` and `B→A` would touch overlapping nodes, but longer cycles can be formed by transactions with disjoint endpoints. Connected-component locks would require a stable component identity under concurrent edge creation; no safe implementation was demonstrated. Holding the established lock for a much shorter traversal is the bounded correction.

## Matched before/after measurements

The same instrumented [probe](../../../backend/scripts/topology_gate_probe.py) ran against fresh containers, with **20 measured samples per operation after warm-up**. Values are milliseconds. p99 at n=20, and especially n=8, is statistically limited and **not** a reliable production tail percentile. SQL counts include handler authorization/audit queries; each statement is one database round trip. `lock SQL` is client-observed advisory-lock statement duration, including network overhead, rather than a pure PostgreSQL server wait. Raw results: [before](TOP_PERF_BEFORE.json), [after](TOP_PERF_AFTER.json).

| Operation | Before p50 / p95 / p99 | After p50 / p95 / p99 | Before → after SQL | Before → after mean / max |
| --- | --- | --- | --- | --- |
| Create (n=20) | 2353.304 / 2738.864 / 2738.864 | 69.579 / 113.814 / 113.814 | **261–280 → 9** | 2348.843 / 3203.301 → 84.736 / 292.898 |
| Deep cycle rejection (n=20) | 2262.693 / 2799.399 / 2799.399 | 55.858 / 118.705 / 118.705 | **276 → 5** | 2323.985 / 2849.561 → 73.863 / 330.675 |
| 50-edge detail preview (n=20) | 65.160 / 121.271 / 121.271 | 84.181 / 297.239 / 297.239 | **19 → 19** | 79.772 / 270.058 → 106.408 / 316.439 |
| History page of 200 (n=20) | 41.769 / 47.905 / 47.905 | 47.481 / 51.657 / 51.657 | **15 → 15** | 52.289 / 243.664 → 58.867 / 262.958 |

The unchanged GET paths had large outliers in the 20-request runs. Two separate **100 measured direct handler calls per path**, after 10 warm-ups on each source snapshot, gave preview p50/p95 **59.313/235.872 → 49.756/218.150** in run 1 and **49.389/201.925 → 46.463/195.817** in run 2. History gave **28.804/44.946 → 23.059/26.442** in run 1 and **22.145/25.951 → 21.772/147.216** in run 2. [Both read-only runs](TOP_PERF_READ_PARITY.json) use the [reusable parity probe](../../../backend/scripts/topology_read_parity.py). These are direct handler timings, not authenticated HTTP latency. The unchanged read code and varying high-tail observations do not establish a repeatable read-path regression; shared-runner variance remains a limitation.

Eight overlapping operations produced **4×201 and 4×409** both before and after, with **no committed cycle** on independent graph inspection. Before → after: operation p50 **9771.375 → 605.277 ms**, maximum **18340.792 → 713.533 ms**; SQL per operation **276–284 → 5–9**; maximum advisory-lock SQL duration **15982.257 → 353.949 ms**. Sampled maximum simultaneous advisory waiters was **7 → 6**. There were **0 database deadlocks or retries** in the benchmark. The lock is still contended; reducing its duration did not prove safe fine-grained locking.

## Regression and failure evidence

| Gate | Result | Executed evidence |
| --- | --- | --- |
| TPERF-01 traversal | **PASS** | New PostgreSQL tests: self, two-node, deep and multi-path cycles; duplicate; disconnected graph; fan-in/out; 999-versus-1,000-node bound. Existing 3,000-edge probe also passed. |
| TPERF-02 authorization | **PASS** | Probe: authorized creation **201**; foreign detail/history and forged customer scope **404**; foreign write/cross-customer edge denied; scoped A inventory **500**. New Resource LIMIT test: hidden parent **404**, allowed edge created. Existing access-control, Sprint 08 RBAC, Sprint 12 trust tests passed. |
| TPERF-03 concurrency | **PASS** | New barrier-synchronized eight-op opposite-edge test: 4 committed, 4 rejected, no reciprocal committed edge. Existing benchmark's eight overlapping operations: 4 created, 4 cycle-rejected, full persisted graph acyclic. |
| TPERF-04 preservation | **PASS** | Preview **50** of **253**, history page limits **1–200**, stable IDs and retired audit history retained. PR #60 Kubernetes association/revocation tests passed. Alembic head unchanged; `alembic check` found no drift. |
| TPERF-05 failure | **PASS** | Lock timeout and controlled PostgreSQL deadlock each rolled back the losing transaction without a partial relationship. Eight concurrent duplicate submissions left exactly one active edge. Existing API duplicate contract remained **409**. |

The controlled deadlock test observes PostgreSQL SQLSTATE `40P01`; it proves transaction rollback and surviving graph integrity, not an application-level retry policy. The direct handler still exposes the existing unique-index exception on duplicate flush, while authenticated HTTP returns 409; no duplicate behavior was changed by this optimization. Initial development of the test fixture hit `monitoring_resources_vm_id_key` because legacy VM insertion auto-created a binding. The synthetic fixture was corrected to use the existing manual-binding flag; the final fresh test run is green. No production data was used.

## Commands and final local results

The disposable-only database password was not committed. Each fresh volume-free container used `docker run --detach --rm --name <unique-test-name> --publish 127.0.0.1::5432 --env POSTGRES_USER=opscontrol --env POSTGRES_DB=opscontrol --env POSTGRES_PASSWORD=<disposable-only> postgres:17-alpine`, followed by `docker port <unique-test-name> 5432`. `DATABASE_URL` pointed to `postgresql+psycopg://opscontrol:<disposable-only>@127.0.0.1:<loopback-port>/opscontrol`; `ENVIRONMENT=test`, `OPSCONTROL_V16_ACCEPTANCE=1`, `DATABASE_POOL_SIZE=8`, `DATABASE_MAX_OVERFLOW=8`. The exact program invocations were:

```sh
PYTHON=/workspace/scratch/opscontrol-dev04-1/.venv/bin/python
cd backend
${PYTHON} -m alembic upgrade head
${PYTHON} -m scripts.topology_gate_probe
${PYTHON} -m scripts.topology_read_parity
${PYTHON} -m unittest tests.test_topology_traversal tests.test_kubernetes_cluster_associations tests.test_audit_remediation tests.test_unified_v15_contracts tests.test_access_control tests.test_sprint08_rbac tests.test_sprint12_shared_trust -v
${PYTHON} -m alembic current
${PYTHON} -m alembic check
cd ..
${PYTHON} -m black --check backend/app/unified/api.py backend/scripts/topology_gate_probe.py backend/scripts/topology_read_parity.py backend/tests/test_topology_traversal.py
${PYTHON} -m ruff check --select E9,F63,F7,F82 backend/app/unified/api.py backend/scripts/topology_gate_probe.py backend/scripts/topology_read_parity.py backend/tests/test_topology_traversal.py
${PYTHON} -m compileall -q backend/app/unified/api.py backend/scripts/topology_gate_probe.py backend/scripts/topology_read_parity.py backend/tests/test_topology_traversal.py
git diff --check
```

The unchanged baseline probe and two optimized probe runs **passed**. Final relevant unittest selection: **94 passed, 0 failed, 0 skipped** on the optimized disposable database; this includes **7 new tests**, PR #60 regressions, preview/history, RBAC, trust and authorization tests. Alembic upgrade/current/check, Black, Ruff, compilation and diff check **passed**. PostgreSQL 17.11/head `0038` were confirmed. No frontend behavior changed; browser, independent UAT, live Kubernetes and production benchmarks were **NOT RUN**.

## Remaining risk and owner decision

`TOP-PERF-01` is **`PARTIALLY_RESOLVED`**: traversal round trips and observed lock hold time fell materially, but a customer-wide writer lock still causes measurable waiting at eight concurrent operations. A narrower lock needs a separate graph-concurrency proof, adversarial tests across multi-node cycles, and authorization review before implementation. No schema/index migration is justified by this measured dataset. The 20-sample p99 values and shared runner do not certify production throughput. TOP-01 freshness/version/expiry and genuine Kubernetes monitoring remain separate scope; DEV-03.3 Pentaho exact-build qualification remains ON HOLD pending evidence and owner approval.
