# Bounded local performance measurements

All requests use actual authenticated HTTP and an owned PostgreSQL container.
No vendor systems, ETL workloads or production data are used. These are bounded
local measurements, not production-scale or native-platform certification.

## HTTP before/after inventory batching

| Phase / workload | Requests | Concurrency | Duration (s) | Throughput (req/s) | p50 (ms) | p95 (ms) | p99 (ms) | Failures |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Before batching: One customer inventory | 20 | 1 | 17.0029 | 1.176 | 733.299 | 1240.97 | 1240.97 | 0 |
| Before batching: Five customer inventory | 40 | 4 | 53.7607 | 0.744 | 5302.066 | 5883.358 | 5991.029 | 0 |
| Before batching: Execution/evidence/schedule reads | 60 | 8 | 5.0228 | 11.946 | 499.31 | 962.779 | 983.017 | 0 |
| Final: One customer inventory | 20 | 1 | 0.8966 | 22.306 | 44.196 | 49.939 | 49.939 | 0 |
| Final: Five customer inventory | 40 | 4 | 2.6112 | 15.319 | 168.291 | 1072.333 | 1079.932 | 0 |
| Final: Execution/evidence/schedule reads | 60 | 8 | 4.9815 | 12.045 | 367.931 | 1561.072 | 1610.461 | 0 |

The authorized workload is identical: five customers, 1,201 resources, 207 execution
records, 603 occurrences, 103 attempt revisions, 206 aliases and 205 added incident
activities plus native audit events. Other regression-fixture population differs
between the earlier focused run and final full gate. This is not a statistically
controlled paired experiment. The fixed SQL-count regression independently verifies
the removed per-row lookups. One bounded run per reported phase is shown; no SLA or
production throughput target is asserted.

Each request includes current authentication/permission resolution, SQL, serialization
and loopback HTTP. A single API worker, local PostgreSQL container, Python 3.12.14,
Linux and 3 visible CPUs were used. TLS, remote network,
long-duration load, multi-worker contention and vendor performance are not measured.
HTTP percentiles use lower empirical order-statistic quantiles: sorted sample at
`floor((n-1)*p)`. No failed request is excluded from the latency sample.

## Ownership, duplicate ingestion and recovery restart

| Scenario | Dataset | Iterations | Internal concurrency | Total (s) | Scenarios/s | p50 (ms) | p95 / p99 (ms) | Failures / skips |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| test_two_actual_database_sessions_cannot_both_own_source | one source; two competing PostgreSQL sessions | 3 | 2 | 0.5606 | 5.351 | 123.601 | 315.917 / 315.917 | 0 / 0 |
| test_duplicate_observations_keep_raw_records_but_not_duplicate_attempts_revisions | one source; repeated accepted native observation | 3 | 1 | 1.0315 | 2.908 | 346.607 | 372.181 / 372.181 | 0 / 0 |
| test_worker_restart_resumes_retained_recovery_without_reprocessing | two retained events; two fresh worker sessions; one-row recovery batches | 3 | 1 | 1.4536 | 2.064 | 482.984 | 488.479 / 488.479 | 0 / 0 |

These scenario timings include fixture setup and assertions. With only three samples,
p95/p99 are the observed maximum. They are not ingestion-event throughput measurements.
Restart means a fresh database session and reconstructed source/operation objects
after saving one batch; completed recovery cannot process again and the live
checkpoint remains unchanged. OS-process crash, host failover and real runtime
restart acceptance remain unperformed.

Revocation overlaps 24 queued/concurrent read requests. Five additional reads after
the mutation returns are denied; zero reads started after that return succeed.
Already authenticated in-flight reads retain the existing per-request snapshot
contract. This is distinct from the transactional recheck for protected mutations.

## Findings versus proposed follow-up

| Observed finding | Disposition |
| --- | --- |
| Inventory per-row parameter and customer binding queries | Fixed with page-bounded ORM preloads; simple inventory test uses four queries for 26 rows |
| Execution child/attempt count requests per row | Fixed with five handler queries for the tested page and grouped server counts; frontend per-row HTTP counts removed |
| Remaining concurrent mixed-read latency tail | Measured above; profile authentication/ORM construction and scoped SQL plans before proposing further changes |
| Exact retained totals/window previews and large activation readiness graphs | Current bounded contracts retained; deeper-archive and activation/lock-contention load are unmeasured |

No speculative migration, permission cache, default role grant or production tuning
was introduced. Full raw measurements: `evidence/sprint09-performance.json`,
`evidence/performance-before-inventory-batch.json`, `evidence/sprint09-resilience.json`.
