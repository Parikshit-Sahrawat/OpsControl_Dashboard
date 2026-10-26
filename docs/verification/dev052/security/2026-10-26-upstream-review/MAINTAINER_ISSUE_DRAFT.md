# [exporterhelper] Make in-flight persistent queue recovery atomic or resumable across interrupted startup

Draft for maintainer review — **not submitted**. Source review refreshed
2026-10-26. The runtime results below are historical synthetic experiments;
this review did not execute a new collector or build a patch.

## Component and versions

Collector core `exporter/exporterhelper` persistent queue with Contrib
`file_storage` (bbolt), Linux amd64, fsync enabled. Historical controls used
Contrib 0.123.0; newer recovery used the official Contrib distribution labelled
0.163.2. That distribution assembles core/Contrib 0.163.0 components:

- [Core v0.163.0 queue source](https://github.com/open-telemetry/opentelemetry-collector/blob/5177a6a85ca3783068077e25aec6cebbe1d50d1f/exporter/exporterhelper/internal/queue/persistent_queue.go).
- [Inspected main queue source](https://github.com/open-telemetry/opentelemetry-collector/blob/82148555675e5a0a201189cd4220395eb8baa1ad/exporter/exporterhelper/internal/queue/persistent_queue.go).
- [Official 0.163.2 distribution manifest](https://github.com/open-telemetry/opentelemetry-collector-releases/blob/6c65793ec707f673304e52dfcb642684fda1a048/distributions/otelcol-contrib/manifest.yaml).
- [File-storage Batch implementation](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/df849b5403c041d5e799e7846392a6f18b0b55ae/extension/storage/filestorage/client.go#L118-L130).

The two inspected core queue files have identical SHA-256
`a98bd9990c2405d0b24cdee951ccacec01b58b4dc347ceb6b7c256ceea789d98`.
This does not establish binary qualification or a supported correction.

## Observed persistence sequence

`enqueueNotDispatchedReqs` performs a Batch read of dispatched payloads, then a
separate Batch deletion of their old keys, then individual `putInternal` calls.
Each replacement commits its payload and metadata together, but not in the same
transaction as the earlier deletion of all old keys. Each file-storage Batch maps
to its own bbolt Update. Fsync does not make several transactions atomic.

Consequently, after old-key deletion commits and before all replacements commit,
some unacknowledged payloads exist only in the recovering process's memory. A kill
at that cut can leave neither a recoverable queue payload nor a committed receiver
receipt. The same helper is invoked by both qmv0 startup and legacy metadata
migration; only the legacy recovery path was exercised in the newer historical
experiment reported here.

[PR13330](https://github.com/open-telemetry/opentelemetry-collector/pull/13330)
removes capacity rejection from recovery `putInternal`, addressing the older
full-queue failure. It leaves the deletion/replacement transaction separation.
An ordinary restart succeeding does not establish interrupted recovery safety.

## Historical reproduction and independently reconciled results

1. Durably inventory 267 synthetic, unique, run-scoped source event IDs and payload
   hashes before emitting them; append/fsync records individually and stagger them
   so filelog checkpoints advance. Use queue capacity 256 and ten consumers.
2. Hold the isolated receiving service **before** database commit. Witness ten
   in-flight requests plus 256 waiting requests; the 267th event remains a
   backpressured, uncheckpointed source tail. Preserve queue/checkpoint snapshots.
3. Kill the writer. For the legacy control restart 0.123.0, release the receiving
   service, and reconcile against independently queried PostgreSQL event rows and
   committed batch receipts. The ten old keys are deleted and replacement attempts
   are rejected at capacity. They are already checkpointed and are not reread.
4. On a separate populated legacy queue, restart with the newer 0.163.2-labelled
   binary. Witness committed old-key deletion and exactly one replacement commit;
   stop/kill at that boundary, then restart and drain to the receiving service.
   Preserve committed-page snapshots, process/syscall timing and receipt exports.

| Historical case | Expected IDs | Persisted distinct | Missing | Accepted record attempts | Physical rows | Duplicate rows |
|---|---:|---:|---:|---:|---:|---:|
| 0.123.0 saturated restart | 267 | 257 | 10 | 257 | 257 | 0 |
| 0.163.2 interrupted legacy recovery after first replacement | 267 | 258 | 9 | 258 | 258 | 0 |

Two historical partial-replacement probes agree. Ordinary newer recovery and kills
after all replacements committed delivered all 267 IDs in finite controls. Those
successes do not cover the failing intermediate cut. Independent inventories and
database receipts, rather than queue depth or exporter success counters, identify
the gaps. No source replay helper repaired these native outcomes.

Limitations: the newer probes populated state with 0.123.0 first; they are not
steady-state qmv0 crash tests. Their filelog polling overlay was 20ms, whereas the
legacy control retained its generated polling timing. Early instrumentation runs
did not freeze exact fixture-source hashes; later frozen-source repeats confirmed
the gap. This text describes reproduction, not a newly published standalone
harness. It makes no exactly-once, power-loss, all-storage-backend, or comprehensive
version certification claim. Synthetic experiments contained no customer data.

## Expected invariant and questions

For every admitted, unacknowledged item, **a durable payload reachable from
authoritative queue metadata must survive every committed transaction and restart,
until its replacement is durably reachable or delivery is independently confirmed
committed**. A source checkpoint is not delivery; a successful send attempt is not
a database commit. Lost ACKs may require redelivery and explicit duplicate
accounting. Permanent rejection is a separate terminal policy, not successful
delivery or an excuse to drop work during recovery.

1. Is there already a maintained, supported correction for this exact startup
   window? Please identify the commit/release, component-to-distribution binding,
   supported storage contract and migration/rollback boundary.
2. Would maintainers prefer retaining the original durable indices until completion,
   committing replacement payload/metadata and old-key retirement atomically, or
   a resumable migration journal? What invariant should hold after each failed or
   committed transaction, including existing qmv0 and legacy state?
3. How should full capacity, read/unmarshal/write errors, ENOSPC, partially committed
   migration, repeated crashes and corruption behave? In particular, can recovery
   avoid deleting any old payload after a failed read or before valid replacement?
4. Which test/observer mechanism can witness each real transaction boundary without
   substituting timer-only kills? Proposed qualification uses the original 267-ID
   staggered workload, at least ten runs per cut, repeated recovery crashes, no
   source replay, and independent committed receipts with physical duplicate rows.
5. Who can own design review and identify the supported release path? Is
   [the disk-queue POC](https://github.com/open-telemetry/opentelemetry-collector/pull/15993)
   intended to address this invariant and populated-queue migration, or should a
   smaller exporterhelper correction be reviewed separately? Its author's durability
   claims are not adopted here as qualification evidence.

[PR16230](https://github.com/open-telemetry/opentelemetry-collector/pull/16230)
addresses metadata-read startup errors; shutdown-retention discussions address
other boundaries. Neither is assumed to resolve interrupted re-enqueue. Queue
schema compatibility also needs separate review from filelog's protobuf checkpoint
format: a queue fix alone cannot make older filelog readers decode newer state.

No implementation or maintenance commitment is assumed, and no custom binary has
been built for this review. The requested outcome is an authoritative design and
support path before a separately authorized qualification attempt.
