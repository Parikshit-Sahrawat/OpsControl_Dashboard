# Draft upstream review brief — not submitted

**Scope:** persistent exporter queue recovery of admitted, unacknowledged records.
No fork, patch, binary build or upstream message is authorized or performed here.
This draft is review material for a separately authorized maintainer discussion.

## Precise gap

At core v0.163.0 commit `5177a6a85ca3783068077e25aec6cebbe1d50d1f` and main
`82148555675e5a0a201189cd4220395eb8baa1ad`,
`exporter/exporterhelper/internal/queue/persistent_queue.go` has identical bytes.
`enqueueNotDispatchedReqs` reads old payloads, separately commits their deletion,
then writes replacements individually. File storage Batch maps each invocation
to one independent bbolt Update. Between the deletion commit and all replacement
commits, some admitted unacknowledged records exist only in process memory.
SIGKILL can therefore leave no recoverable queue copy or independently committed
receipt for those records. The path handles both current qmv0 restart and legacy
migration; it is not fixed merely by choosing the newer schema.

The official v0.163.2 distribution at
`6c65793ec707f673304e52dfcb642684fda1a048` assembles 0.163.0 components and does not
supply a correcting queue implementation. PR13330 removes capacity rejection from
recovery but leaves the separate deletion and replacement transactions. Shutdown
retention and metadata-read failure changes address different boundaries.

## Existing independent observations (not newly executed in F)

- Guarded 0.123.0, queue 256/default ten consumers: individually inventory/fsync 267
  source IDs, hold API before commit, fill ten in-flight and 256 waiting, persist
  checkpoints, SIGKILL, reopen with healthy API. 267 expected  / 257 PG distinct /
  ten missing  / 257 accepted attempts  / 257 rows  / zero physical duplicates.
- Newer exact binary, same saturated legacy cut, interrupt after one replacement
  commit: 267 expected  / 258 PG distinct /nine missing  / 258 accepted attempts /
 258 rows  / zero physical duplicates. Two historical partial-requeue runs agree.
- Ordinary newer restart and interruption after all replacement commits pass in
  historical finite tests. They do not cover the destructive intermediate cut.

Independent source inventory, actual authenticated API transactions, PG rows and
batch receipts, stopped committed-page snapshots and syscall timestamps are
preserved under [D evidence](../2026-10-26-queue/QUEUE_DECISION.md). D's later repeats
freeze fixture sources; initial instrumentation source-hash limits remain disclosed.
No customer target, credential or provider certification is involved.

## Questions for maintainers / implementation acceptance

1. Is there an authoritative maintained release or supported distribution with an
   atomic/resumable correction for this exact startup window? Supply commit,
   distribution/component binding, immutable artifact identity and supported
   storage/schema migration boundary; a capacity-only or shutdown-only fix is
   insufficient.
2. Can recovery reuse the durable old indices until acknowledged, or atomically
   commit replacement payloads and metadata with old-key retirement? Define the
   old/new state invariant after every successful or failed storage transaction.
3. How does the proposal handle full capacity without dropping existing durable
   work, repeated crash before/after migration markers, unmarshal/read/write errors,
   incorrect metadata, partial dispatch completion and ACK ambiguity?
4. Which observer hooks or storage tests can witness the transaction cuts without
   silently substituting timing-based kills? The ADR requires at least ten repeat
   runs per prescribed cut, partial migration, repeated restart and independently
   reconciled actual receipts, with no source replay masking native loss.
5. What are the rollback implications for qmv0 and legacy queue metadata, separately
   from the incompatible default protobuf filelog checkpoints tracked as CHK-002?

A correction must preserve old durable payloads or committed receipts until its
replacement is durably reachable. Any design that merely increases capacity,
resets corrupt state, rewinds source checkpoints or hides loss with replay does
not satisfy native qualification. No custom implementation is proposed as
approved; custom build/fork and product transition require separate authorization.

## Reproducible source review (read-only)

Use the recorded GET endpoints in [FETCH_LOG.json](FETCH_LOG.json), saving new
responses under a new directory. For example:

```sh
gh api repos/open-telemetry/opentelemetry-collector/contents/exporter/exporterhelper/internal/queue/persistent_queue.go?ref=5177a6a85ca3783068077e25aec6cebbe1d50d1f
gh api repos/open-telemetry/opentelemetry-collector-releases/contents/distributions/otelcol-contrib/manifest.yaml?ref=6c65793ec707f673304e52dfcb642684fda1a048
gh api repos/open-telemetry/opentelemetry-collector/pulls/16230
```

Decode API `content` as base64; compare its SHA-256 and Git blob ID against
[SOURCE_INDEX.json](SOURCE_INDEX.json). Review initClient, legacy migration,
enqueueNotDispatchedReqs, putInternal, the storage Batch implementation and PR
patches, not just release descriptions. Distribution tags are explicitly mutable;
use captured commits. Publisher checksum text and its asset digest are distinct
from locally hashing a binary archive. This task downloaded only checksum text.

No runtime reproduction command is recommended for immediate execution because
Phase 1 did not establish a qualifying candidate. Preserve the existing fixtures
and return to the unchanged [N1–N4 plan](../2026-10-26-adr/NATIVE_ACCEPTANCE_PLAN.md)
only after its candidate prerequisite is satisfied. Do not run replay helpers in
that native qualification.
