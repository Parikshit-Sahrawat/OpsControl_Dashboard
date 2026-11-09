# Performance before/after

**RM-DEF-036 NOT REPRODUCED at this bounded workload, NOT FIXED.** No SLO, fleet throughput or global certification claim. No performance optimization was justified/applied.

Before: application6adc4f0 in detached worktree; new test-only instrumentation added, application/migrations unchanged. After: c4c773601c53d0c8f44fdcb51b447c7664fb6eb8. Identical probe code exercises20 OTLP JSON batches×10 points, one exact replay, one invalid credential negative. Three authenticated GET paths: infrastructure/resources, resource-management/data-sources,unified/resources.12 warm/baseline reads,30 during producer+browser,12 recovery reads. Both datasets have additional existing controlled harness fixtures; after also adds template/auth tests. Small samples/cold start and fixture differences prevent causal performance-improvement claims.

| Application | Phase | p50 ms | p95 ms | p99 ms | Requests/errors |
|---|---|---:|---:|---:|---|
|Before6adc4f0|baseline_no_ingestion|37.196|429.179|429.179|12/0|
|Before6adc4f0|concurrent_ingestion|47.723|142.428|481.643|30/0|
|Before6adc4f0|after_ingestion|37.518|66.963|66.963|12/0|
|Afterc4c7736|baseline_no_ingestion|37.691|454.052|454.052|12/0|
|Afterc4c7736|concurrent_ingestion|51.913|115.830|470.315|30/0|
|Afterc4c7736|after_ingestion|36.242|60.388|60.388|12/0|


Both runs:22 payload requests,21 accepted HTTP responses including replay, one expected401 rejection;20 distinct TelemetryReceipt rows;200 expected producer ordinals carried in metric values,200 distinct persisted,200 physical rows,0 missing/duplicates. Ordinals are fixture identifiers, not a new protocol event-ID guarantee. This is **actual legacy-compatible authenticated OTLP admission**, not direct MetricSample insertion; the older direct-write probe remains separately labeled. No forged qualified source/reader profile seeded; method-version/generation positive certification is not covered.

Rawlatencies, expected/persisted IDs and representative EXPLAIN ANALYZE/BUFFERS latest-sample query are in before-application/otlp-performance.json and final-application/otlp-performance.json. SQL **queries per API request not measured**; no blanket absence of N+1 asserted. CPU/memory/process utilization not captured. Browser login/render, resource navigation, event-loop delay and API response/error counts are in paired load-navigation.json. This is one desktop path; full all-module/polling/mobile responsiveness under representative sustained ingestion remains NOT TESTED. No speed gain inferred from variance. No broad polling/consistency changes made to hide delays or drop telemetry.

**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**

Environment caveat: final workload shared this managed test host with an independent task-owned preservation run. CPU/memory and host contention were not measured; before/after differences are descriptive, not controlled evidence of improvement/regression. Fixture producer identity uses unique ordinals as metric values; no production event-ID or source-generation contract is invented.
