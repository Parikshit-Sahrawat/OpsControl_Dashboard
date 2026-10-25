# CHK-001 — checkpoint-to-delivery causality, 2026-10-25

**Partial mitigation only. CHK-001 FAIL; SECURITY BLOCKED; RELEASE NO-GO.**
Implementation: `7af6927a16056597794c42549a813d3408860a57`.
Task start: `76a97e3fcf6709533151fffb36b16138e4475aba`.
Original product baseline: `f617cc653a965c2ad1bb7edf9e20237e40044b97`.
Dates use 2026-10-25; raw clock fields are explicitly UTC/Unix nanoseconds.

## Reproduction before changes

The unchanged A.3B harness, against the exact task-start product source, reproduced
**28/44 distinct IDs**, **16 missing** (`event-0028`–`event-0043`) after the original
65-second restart deadline. PostgreSQL timestamps independently reproduce the API
ledger's missing set. That failure is retained in `baseline-reproduction/`.
Its existing, unchanged recovery phase subsequently produced 44 distinct IDs,
100 physical rows and 56 duplicates. Recovery does not turn the preceding failed
native-delivery phase into PASS; the recovery utility was neither changed nor
expanded.

Two instrumented baseline runs then established causality with real binaries:
for both 0.123.0 and 0.163.2, a SIGSTOPped committed checkpoint was at source EOF,
the persistent queue contained none of the 16 new IDs, and the API had received
none. SIGKILL before the batch timeout and restart left all 16 absent. See
`instrumented-baseline-attempt2/`, including independent DB reconciliation.

## Three distinct loss windows

1. **Pipeline batch processor.** `consume` enqueues into an in-memory channel and
   returns success. Its five-second/512-record batch flush runs later. Filelog
   saves offsets after consuming the source; its success is not an API ACK or a
   durable exporter-queue write. The checkpoint can therefore pass data held only
   in memory. The original 16-of-44 failure occurs in this interval.
2. **Stanza receiver emitter.** Removing the pipeline batch alone is insufficient:
   the default Stanza emitter also buffers in memory (100 records/100 ms). Under
   queue backpressure its background flusher can block while file reading and
   checkpoints advance. `fixed-attempt1` preserves the failing saturation safety
   predicate. That attempt aborted before its recovery step, so its empty DB is
   not presented as an independently completed recovery failure. The upstream
   `stanza.synchronousLogEmitter` gate exists in both pinned binaries, is **alpha**,
   and was specifically introduced for this loss window.
3. **0.123.0 full persistent-queue recovery.** On restart,
   `retrieveAndEnqueueNotDispatchedReqs` reads and **deletes** in-flight item keys,
   then calls `putInternal` to re-enqueue. A full queue can reject the re-enqueue.
   The source checkpoint may already cover those IDs. This still loses data even
   with the synchronous-handoff candidate. The controlled two-slot case lost one
   of ten IDs. With the **unchanged generated 256-request queue and default
   consumers**, staggered writes/checkpoints reproduced **10 missing of 267**:
   `event-0000`–`event-0009`. All ten were previously checkpointed. The failure-cut
   snapshot has no queued event IDs; API and PostgreSQL agree on 257 distinct IDs,
   257 accepted attempts, 257 physical rows, zero duplicates. The restart log
   records failure while moving in-flight items back to the full queue.

The default-size burst test is deliberately retained beside the staggered test:
271/271 arrived, with **526 physical rows / 255 duplicates**. Its older checkpoint
caused source rereading to cover queue-recovery deletion. A PASS on that workload
alone would incorrectly hide the full-queue loss. It is not exactly-once evidence.

Upstream reference files, blob identifiers and SHA-256s are in `upstream/`.
Candidate stack traces identify v0.163.0 component modules; those module sources
are reference evidence, not a claim of a separately rebuilt 0.163.2 image.
The unavailable v0.163.2 source tag lookup and initial wrong manager path are
retained as failed lookups. Binary identities are verified separately.

## Smallest implemented mitigation and limits

Only collector configuration generation, its Agent launch contract and focused
regressions changed:

- For native filelog configurations, remove the asynchronous batch processor from
  the common logs pipeline, retain resource attribution and memory limiting, use
  filelog retry with no elapsed-time expiry, and fsync existing file storage.
- Retain the same exporter, receiver and storage identities and queue capacity.
  Set transient exporter retry to no elapsed-time expiry for these configurations.
- Prefix the generated, checksummed YAML with a fixed contract marker. Matching
  backend validation and Agent apply/start/offline restart enable only the literal
  `stanza.synchronousLogEmitter` flag. Rollback reads the actual prior config;
  arbitrary marker text never becomes arbitrary runtime arguments.
- The 0.123.0 production version pin and both existing version guards are intact.
  0.163.2 was used only as a direct synthetic producer. No promotion occurred.

The native-filelog condition also affects other receivers sharing that logs
pipeline, and the exporter retry lifetime for other signals sharing the exporter.
Metrics/traces keep their existing batch processors. The alpha emitter can increase
request rate (notably one-record requests in 0.123.0); throughput/retention sizing
needs owner review. This candidate is **not a complete loss-free release fix**.
No checkpoint converter, rewind, archive replay utility, custom binary, queue-file
rewrite, dropped-finding suppression or version-guard bypass was introduced.

## Supported observation boundary

The tests use retained synthetic source files, stable run-local IDs, functioning
local storage, the exact binaries, actual TLS/authenticated API and disposable
PostgreSQL, under non-root/read-only/cap-drop/memory/CPU/PID restrictions. Source
inventory is fsynced independently before append. SQLite records request receipt,
API commit visible in a separate DB transaction and server response completion;
PostgreSQL is independently reconciled after every run, including failures.
A server response write is not called a client ACK: queue item removal plus
exporter metrics provide the separate observed acknowledgement boundary.

Path-filtered strace delays pwrite only on the selected queue/checkpoint file.
Final syscall probes take committed-page snapshots while stopped, reassert the
boundary and SIGKILL while still stopped. Raw write buffer contents are excluded;
no tracing capability or relaxed seccomp policy was added. Each binary passed
before-enqueue and after-enqueue/before-checkpoint recovery. That latter boundary
replayed four IDs per binary, creating four physical duplicate rows each.

The producer inventory detects every missing ID in these tests (**zero undetected
loss in the audited finite sets**), but 27 expected IDs are actually missing across
the selected final candidate cases. This is a failed delivery gate, not a claim
that production detects gaps. Permanent HTTP 400 and source retention expiry each
remain explicit FAIL cases. Power failure, storage faults, long outages,
production load and a production per-event reconciliation service are NOT TESTED.
