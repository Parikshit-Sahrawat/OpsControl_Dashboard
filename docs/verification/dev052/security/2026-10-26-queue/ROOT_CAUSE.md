# CHK-001 saturated restart — 2026-10-26 (Asia/Calcutta)

**Native safety remains FAIL.** Raw timestamps are UTC/Unix nanoseconds. Product
source is `97be9b3d1acffc83367b79cdc9ee179f8b694c05`; the production 0.123.0 pin and
version guards are unchanged. This investigation changes only verification files.

## Exact unchanged reproduction

`guarded-baseline/` runs the unchanged C fixture and generated configuration:
256-request queue, ten default consumers, individually fsynced input writes and
persisted checkpoints. **267 expected, 257 PostgreSQL distinct/physical rows,
257 authenticated API accepted record attempts, ten missing, zero duplicates.**
The missing set is `event-0000` through `event-0009`. At the full cut those ten are
present in queue payload keys and covered by filelog checkpoints; the final queue
is empty. This is not the earlier in-memory batch-window defect.

## Durable transaction sequence

The old upstream implementation is retained in the unchanged C evidence at
`../2026-10-25-durability/upstream/legacy-queue.txt`.

1. `Read` dispatches a request, advances the read index and records it as in-flight.
   Its payload remains in storage until successful/permanent completion. API hold
   injection leaves ten requests in-flight and 256 waiting requests. A 267th source
   ID is blocked behind the full queue and not covered by the final checkpoint.
2. On startup, `retrieveAndEnqueueNotDispatchedReqs` gets the recorded in-flight
   list and calls a storage Batch **read** for all ten payloads. Those bytes now
   also exist only in the restarting process's memory.
3. A separate Batch **deletes all ten old payload keys**. The file-storage bbolt
   transaction commits independently. `fsync: true` does not combine transactions.
4. Each payload is separately unmarshalled and passed to `putInternal`. In 0.123.0
   this first tests `queueSize + reqSize > capacity`. The queue is full, so every
   re-enqueue returns `ErrQueueIsFull`; the deleted bytes are not restored. Restart
   logs count ten errors moving in-flight records back to the queue.
5. Remaining queued records deliver normally; filelog rereads only the final
   uncheckpointed source ID. It does not reread the ten checkpointed IDs. A burst
   test with an older checkpoint could mask this defect through replay/duplicates.

The queue's write-index and new payload are atomic **within one re-enqueue Batch**.
The earlier bulk deletion and the sequence of replacement Batches are not one
transaction. Thus removing the capacity rejection alone is insufficient for
SIGKILL safety. A client ACK, a source checkpoint, an API send completion and an
independently committed PG receipt are distinct boundaries.

## Upstream fix research and actual compatibility limit

Public GitHub search results, failed search, source history, issue, PR, tag ancestry
and exact main source are retained under `upstream/` (with artifact hashes).

- Core PR [13330](https://github.com/open-telemetry/opentelemetry-collector/pull/13330),
  merged commit `e2954b98139a839d31cd7ae4d826966f33a9180f`, implements unified qmv0
  metadata, related to issue12890's inaccurate queue-size backup. It moves the
  capacity check into `Offer`; recovery `putInternal` no longer rejects a full
  queue. Tag comparison proves v0.130.0 contains it and v0.129.0 predates it.
  These are source ancestry checks, not binary certification of those versions.
- The exact previously provisioned experimental binary identifies itself as
  0.163.2; recorded component stack/module sources identify core v0.163.0. Its
  checksum and prior image provenance are retained separately. The public Contrib
  `releases/latest` response currently identifies v0.163.0, and the prior .163.2
  source-tag lookup failed. Do not equate the binary label to a verified matching
  public source tag or infer permission to promote it.
- That binary passes ordinary full-queue restart: **267/267, no duplicate rows**.
  But SIGKILL after only one replacement commit leaves **258/267, nine missing**.
  The old ten payload keys are gone and only one has a committed replacement.
  Raw snapshots, strace pwrite/fsync logs and PG receipts establish the window.
- The inspected main source commit
  `82148555675e5a0a201189cd4220395eb8baa1ad` still performs the separate bulk delete
  followed by per-item re-enqueue. No complete supported upstream atomic-recovery
  fix was found in the inspected sources/search. This finite search is not proof
  that no fix exists anywhere. Shutdown retention fixes (e.g. PR15680/16140) do not
  make this restart read/delete/re-enqueue sequence atomic.

## Candidate comparison and decision

| Option | Evidence and disposition |
|---|---|
| Supported collector replacement | Newer queue avoids capacity rejection but measured partial-requeue SIGKILL still loses nine IDs. Version/source provenance, full transition and CHK-002 rollback remain BLOCKED; no guard change. |
| Narrow custom queue fix | A reviewed design should preserve the old payload until a replacement and metadata are committed atomically, or resume old in-flight indices without destructive movement. Must cover partial failures, metadata migration, sizing and retries. No custom binary/fork was built or authorized. Owner/upstream review and full validation are BLOCKED. |
| Independently inventoried bounded replay | Small offline experimental candidate in `verification/dev052/queue_restart/replay.py`. Sealed retained source plus independent PG receipts identify missing records; replay goes through the same authenticated collector/API path. No queue/checkpoint rewrite or capacity increase. Demonstrated finite recovery is separate from native FAIL and is not automatic production durability. |

The first replay attempt failed because the replay began with the same bytes as
the already-checkpointed original file: filelog fingerprint matching skipped those
records. `replay-attempt1/` retains all failures and input/state. The candidate now
adds a leading reserved replay-transaction field, preserving stable event IDs and
all original fields. `replay-marker/` independently proves actual restoration of
the ten missing records, including repeated-crash recovery. Expired retention is
refused and leaves the missing records unresolved. No detection-only result is
called delivery success; no exactly-once, general storage-failure or production
certification is claimed.

Operator preconditions, explicit limits and refusal behavior are in the candidate
[runbook](../../../../../verification/dev052/queue_restart/README.md). Any real
operation, custom build/fork or runtime transition requires accountable owner
review. No such approval is supplied by these experiments.
