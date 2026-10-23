# DEV-04.2 customer-safe topology verification and benchmark

**Gate: `VERIFIED_DEFECTS_FOUND`.** The bounded relationship, customer-scope, cycle, preview, history and PR #60 regressions passed on disposable PostgreSQL. A reproducible traversal/lock-contention performance finding remains; this report authorizes no fix. TOP-01 freshness/version/expiry policy and live Kubernetes monitoring remain outside this developer verification.

## A. Environment and authority

- Tested source: `origin/main` `82a70df5e918a6059f0eda978509b11cf636defd` (merge commit for PR #60). `7d177385fda624c3ff0c7b29dde47dca9b097e0a` is an ancestor. Verification branch: `verify/dev-04-2-topology-gate`, created clean from that main SHA. No existing worktree was modified.
- Container: `opscontrol-dev04-2-gate`, disposable `postgres:17-alpine`, PostgreSQL **17.11**, loopback port **32850** for the final run, database `opscontrol`, no persistent volume. Destroy it after verification. Alembic head **`0038_k8s_cluster_associations`**; `alembic check` reported no new operations.
- Python **3.12.14**; SQLAlchemy **2.0.43**, Alembic **1.16.5**, psycopg **3.2.10**, FastAPI **0.143.0**, Pydantic **2.14.1**, httpx **0.28.1**. Connection pool: size 8, overflow 8. Runner reported 3 CPUs and 10.2 GB memory; shared CI/workspace load was uncontrolled. Times are local developer measurements, not capacity certification.
- Authority: [canonical register](../../planning/DEVELOPMENT_COMPLETION_REGISTER.md) TOP-01; [DEV-04.2 backlog](../issue-47/BACKLOG.md) TOP-01/AUD-01/AUD-02; [traceability](../issue-47/TRACEABILITY.md); [ARCH-001 V1.6](../../ARCH_001_V16.md). [Topology handlers](../../../backend/app/unified/api.py) and [model](../../../backend/app/unified/models.py) are the actual implementation. [Migration 0038](../../../backend/migrations/versions/0038_kubernetes_cluster_associations.py) and [cluster authorization](../../../backend/app/api/resource_management.py) are PR #60's separate cluster-only foundation. Customer Organizations were never treated as internal Departments.

## B. Reproducible dataset

[Probe](../../../backend/scripts/topology_gate_probe.py) seed **420042** inserts exactly **1,000** customer-owned VM `MonitoringResource` rows and **3,000** valid `ResourceDependency` rows before measurement: 500 resources and 1,500 edges per customer. There are 500 Linux and 500 Windows synthetic VMs, all in TEST. The two customers deliberately reuse the same 500 display names and hostnames, but have distinct UUIDs and exactly one owning customer per VM. Edges point from a higher-numbered resource to a lower-numbered resource, yielding an acyclic graph; composite customer FKs and uniqueness remain enforced. The active subgraph has a chain of depth 479, high fan-in at node 0, high fan-out at node 479, and 20 isolated resources per customer. Directed edge density within each customer is 1,500/(500×499), approximately 0.60%. Cross-customer, duplicate and cycle edges are attempted only through the existing handler/API after the valid baseline is committed.

Warm-up is excluded from samples. Eight overlapping customer-A operations run concurrently: four valid additions from node 479 and four cycle candidates toward node 479. Their statuses were **4×201 and 4×409**. Database inspection found **1,526** active A edges before a separate historical-retirement check (1,500 baseline + 1 API creation + 1 warm-up + 20 measured creates + 4 concurrent creates) and **no committed cycle**. The history check subsequently retired its API-created edge without deleting its row.

## C. Acceptance matrix

| Case | Result | Actual execution and evidence |
| --- | --- | --- |
| V42-01 relationship creation | **PASS** | Authenticated customer-admin API creation **201**, retrievable in history; direct handler warm-up and measured adds committed. Duplicate **409**, nonexistent ID **404**, cross-customer ID **404**, invalid type **422**. Current schema has no client-provided dependency revision; stale-revision semantics are **NOT RUN** as a separate subcase. [JSON evidence](BENCHMARK_RESULTS.json) `api`, `benchmark`. |
| V42-02 customer isolation | **PASS** | Customer-A scoped inventory total **500**. Foreign detail, forged B scope, foreign history, foreign write, and A→B edge each returned **404**. Customer-B viewer write returned **403**. Equal 404 detail bodies for protected and forged-scope lookups; no cross-customer edge exists in the database. Platform-admin benchmark authority was kept separate from ordinary customer API tests. |
| V42-03 cycle detection | **PASS** | Self **422**; two-node, multi-node and deep-path cycles **409**. Eight concurrent operations produced 4 accepted/4 rejected, and a post-commit graph walk found no cycle. This demonstrates the tested paths, not all possible interleavings. |
| V42-04 graph preview | **PASS** | Resource detail returned exactly **50** of **253** pre-creation relationships, `dependency_has_more=true`, and matching `dependency_total`. An isolated resource returned zero. Authenticated B detail was **404**. Ordering matched first 50 history entries. |
| V42-05 relationship history | **PASS** | Limit 1/200 **200**; limit 0/201 **422**. Two pages covered all **253** original IDs without omission/duplication under a stable snapshot; foreign history **404**. Retirement **204**, retained row has `valid_to`, and one `ARCH_DEPENDENCY_RETIRE` audit event was observed. Concurrent inserts during offset pagination were **NOT RUN**; current API does not promise snapshot pagination across requests. |
| V42-06 PR #60 regression | **PASS (bounded)** | Five controlled PostgreSQL cluster-association tests passed: canonical A/B cluster identity, forged scope, revocation, changed physical ID quarantine and immutable decision history. A cluster UUID passed as a topology parent returned **404**: association alone did not grant a topology edge. Cluster projection exposes empty namespace/workload scope and UNKNOWN monitoring status; no live cluster or namespace-level claim is made. `DataSource.organization_id` and VM single-customer ownership remain unchanged in source/schema. |

Direct API checks used FastAPI `TestClient` with real login/session middleware and migrated PostgreSQL, not UI-hidden-button assertions. The benchmark called the existing `add_dependency` handler with scoped test principal and separate SQLAlchemy sessions. Existing [tests](../../../backend/tests/test_kubernetes_cluster_associations.py) and [dependency pagination regression](../../../backend/tests/test_audit_remediation.py) were also executed against the disposable database.

## D. Performance observations

All latencies are milliseconds. Each row has **20 measured samples** after warm-up; empirical p99 is statistically limited at this sample size and must not be read as a reliable production tail percentile. Query counts include handler/API authorization and audit SQL for that operation. No fixed performance threshold was applied.

| Operation | p50 | p95 | p99 (limited) | Min–max | Mean | SQL statements |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Relationship create, actual handler | 2,613.203 | 3,094.450 | 3,094.450 | 2,140.861–3,197.203 | 2,681.543 | **261–280** per operation |
| Deep cycle rejection, actual handler | 3,362.736 | 4,683.683 | 4,683.683 | 2,108.606–5,222.407 | 3,455.678 | **276** per operation |
| Detail/50-edge preview, authenticated API | 79.976 | 103.108 | 103.108 | 65.458–291.966 | 92.095 | **19** per request |
| History/200-edge page, authenticated API | 55.673 | 86.226 | 86.226 | 45.774–287.247 | 69.663 | **15** per request |

The eight concurrent operations ranged from **3,840.994 to 28,968.861 ms** wall time and made **276–284 SQL statements each**. Transaction duration was within roughly 0.6 ms of total handler duration for measured single operations. A 20-ms `pg_stat_activity` sampler recorded **479 samples**, **409** with at least one advisory lock waiter, maximum **7** simultaneous waiters, event `advisory`. These are sampled observations, not exact lock-wait durations. The representative traversal `EXPLAIN (FORMAT JSON)` used `uq_dependency_current` with an Index Only Scan (estimated cost 21.08 for node 479). A history page plan on the preceding equivalent run used Limit→Sort (estimated cost 65.35); its count used an Index Only Scan (cost 9.75). See [raw final-run measurements and traversal plan](BENCHMARK_RESULTS.json).

Total SQL statements over the reported measured groups were **5,410** create, **5,520** cycle rejection, **2,240** concurrent, **380** preview and **300** history. These totals exclude warm-up, fixture creation, login and acceptance setup.

## E. Findings, scope limits and next decision

| ID | Severity | Evidence and boundary | Recommended bounded correction; approval |
| --- | --- | --- | --- |
| TOP-PERF-01 | **P1 performance scalability finding** | [add_dependency](../../../backend/app/unified/api.py) performs one active-edge SELECT per visited node under a customer-wide advisory transaction lock. On this synthetic 1,000/3,000 dataset, creates made 261–280 SQL statements and concurrent operations showed up to seven advisory waiters and 29.0 s maximum latency. Correctness and tenant isolation still passed. | Owner to authorize a separate measured optimization increment preserving the same permission, lock, cycle, evidence and history semantics. Compare equivalent dataset, query counts and concurrency before/after; no threshold or implementation is approved by this report. |

No customer-isolation, concurrent-cycle, history-leak or PR #60 authorization failure was reproduced. The TOP-01 relationship version/expiry/freshness policy remains a separate architecture decision. The current API offers offset-based history; cross-request snapshot guarantees were not demonstrated. The Kubernetes cluster-only association does not provide namespace/workload authorization or topology projection. No independent UAT, live EKS, real provider or production acceptance was performed.

## F. Commands, results and preservation

Executed on tested source SHA above (the disposable-only password is redacted below):

```sh
docker run --detach --rm --name opscontrol-dev04-2-gate --publish 127.0.0.1::5432 -e POSTGRES_USER=opscontrol -e POSTGRES_DB=opscontrol -e POSTGRES_PASSWORD=<disposable-only> postgres:17-alpine
cd backend
DATABASE_URL=postgresql+psycopg://opscontrol:<disposable-only>@127.0.0.1:32850/opscontrol ENVIRONMENT=test python -m alembic upgrade head
DATABASE_URL=postgresql+psycopg://opscontrol:<disposable-only>@127.0.0.1:32850/opscontrol ENVIRONMENT=test OPSCONTROL_V16_ACCEPTANCE=1 DATABASE_POOL_SIZE=8 DATABASE_MAX_OVERFLOW=8 python -m scripts.topology_gate_probe
DATABASE_URL=postgresql+psycopg://opscontrol:<disposable-only>@127.0.0.1:32850/opscontrol ENVIRONMENT=test OPSCONTROL_V16_ACCEPTANCE=1 python -m unittest tests.test_kubernetes_cluster_associations tests.test_audit_remediation tests.test_unified_v15_contracts -v
DATABASE_URL=postgresql+psycopg://opscontrol:<disposable-only>@127.0.0.1:32850/opscontrol ENVIRONMENT=test python -m alembic current
DATABASE_URL=postgresql+psycopg://opscontrol:<disposable-only>@127.0.0.1:32850/opscontrol ENVIRONMENT=test python -m alembic check
python -m black --check backend/scripts/topology_gate_probe.py
python -m ruff check --select E9,F63,F7,F82 backend/scripts/topology_gate_probe.py
git diff --check
```

`alembic upgrade/current/check` **PASS**; probe **PASS**; focused existing tests **35 passed, 0 failed, 0 skipped** on the final container. A separate direct-API check on the preceding equivalent disposable database returned nonexistent resource **404**, customer-B viewer mutation **403**, and cluster ID as topology parent **404**. The first dry run's customer-A fixture had an operator role lacking `resources.update`; that test-fixture error was corrected to existing `org_admin` before the final fresh-container benchmark. No runtime, model, migration, API, frontend, CI or deployment file changed. All data and credentials were synthetic. The measured database was disposable and must be destroyed without touching other volumes.
