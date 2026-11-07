# Performance baseline and load results

Review date: 2026-11-08 (Asia/Calcutta). Execution logs retain their original UTC timestamps. Tested source `80835f0065de24ebf271fc621b6d1e5e83d73bd2`; main `ffe5ac285ab8aef33a1139bce6f3da79be3d6d33`.


**RM-DEF-036 NOT REPRODUCED; no performance fix or SLO claim.** Baseline app is2fbb959 with identical new test-only ASGI/load instrumentation; app/migration bytes unchanged. Candidate is the tested source above. Each uses30 additional synthetic Linux sources/30 enabled collector configurations, one actual synthetic transport identity and real authenticated legacy-compatible OTLP metrics. This does not qualify an enrolled provider/method generation. Existing test fixtures also remain: exact total resources/collectors and DB size are in each JSON. Matched baseline runs the retained pipeline/Sprint08 fixtures; three extra final unit cases do not alter database fixtures.

Each level uses5-second reader windows: idle1 reader/0 producers, moderate2/1 with25 batches×10 and50ms pacing, higher4/2 with25 batches per producer×10 and20ms pacing. Producers are finite and can outlast/end before the reader window; the exact duration and actual sample rate are recorded, not an invented sustained throughput claim. Four reads: infrastructure listing, paginated source listing, unified listing and one effective-configuration detail. Real browser login/resource navigation occurs during higher level. No sample is directly inserted into MetricSample by this load probe (older controlled-load.json direct-write fixture remains separately labelled).

|App|Level|Readers/producers|Seconds|Reads/errors|p50 ms|p95 ms|p99 ms|API CPU seconds|API max RSS MiB|
|---|---|---|---:|---|---:|---:|---:|---:|---:|
|Before|idle|1 / 0|5.015|75 / 0|35.138|62.044|712.533|3.09|279.6|
|Before|moderate|2 / 1|5.038|85 / 0|59.396|132.923|839.402|4.85|296.9|
|Before|higher|4 / 2|5.551|76 / 0|172.032|882.261|929.545|5.50|304.8|
|After|idle|1 / 0|5.420|69 / 0|34.472|65.906|803.285|3.64|298.6|
|After|moderate|2 / 1|5.849|106 / 0|54.522|122.252|839.656|5.56|308.4|
|After|higher|4 / 2|5.542|75 / 0|150.811|1048.006|1093.016|5.51|318.6|

Before totals: 88 sources/82 collectors; after: 88/82. Both reconcile750 expected/distinct/physical ordinals,0 missing/duplicates,75 batch receipts. Producer ordinals are stable test identities carried in metric values, not a new production event-ID guarantee. This new finite probe does not replay payloads; retained actual200-sample OTLP replay/invalid-token evidence from002B remains historical, and release-final independently exercises remote replay negative paths.

Per-request SQL counts include authentication/security statements and are measured only in the disposable ASGI wrapper, never added to deployment. Representative latest-sample EXPLAIN ANALYZE/BUFFERS retained; plans for every expensive API remain NOT TESTED. Exact per-path count sets, request latencies, process samples, RSS and database bytes are in raw/before-matched/representative-load.json and raw/final-retry/representative-load.json. Polling observations: sanitized browser traces include auth/me5-second refreshes and actual API paths; exhaustive all-module duplicate-poll analysis is NOT TESTED. Current source confirms overlap suppression/abort in operations.js and existing Overview sampling; no polling/consistency control changed to improve numbers.

Measured API-process CPU/RSS only; PostgreSQL/browser/host process utilization not comprehensively captured. CPU limit `400000 100000`, memory limit `34359738368` bytes; shared managed host, not dedicated hardware. Browser load-navigation.json reports navigation/render and event-loop delay; it is one desktop route. Fleet cardinality, Windows/genuine collectors, long-run retention, six-tab performance UI, complete historical queries/all operational pages and the exact reported slow scenario remain missing. Increasing tail latency at higher load is an observation, not a demonstrated fixed defect; no arbitrary performance threshold or optimization was introduced.


**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**
