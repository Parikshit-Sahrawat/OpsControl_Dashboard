# A — native recovery acceptance plan

**Proposed / Pending accountable approval. All new cases below are NOT TESTED.**
This is a design specification linked to [ADR CHK-001](ADR-CHK-001.md), not an
execution request or a claim that a supported correction has been found.
Existing D failures remain FAIL. Production 0.123.0 pin/guards stay unchanged.

## Admission criteria and reproducibility

Before execution, runtime/verification owners must approve the exact upstream
release/source or separately reviewed custom candidate, binary/image SHA,
architecture, storage/OS support boundary and fault schedule. Custom source/build
execution and production transition are separate approvals. No mutable `latest`,
unverified binary, widened version guard or scanner-result substitution is valid.

Freeze product, generator, Agent, fixture, syscall observer and upstream source
hashes before starting. Preserve failed attempts and raw inputs. Use synthetic
producer data only, actual authenticated TLS API transactions and an independent
PostgreSQL reader; retain tenant/method scope, network policy and non-root/resource
constraints. Existing D fixtures are reusable starting points, not proof of new
acceptance. Do not weaken their assertions or edit prior evidence.

The proposed deterministic lab profile is Linux amd64/local fsync-capable storage,
queue capacity 256/default ten consumers, the unchanged generated polling timing
for acceptance, and 267 unique run-scoped events. Diagnostic fast-poll overlays
must be separately labelled and cannot substitute for unchanged timing. Burst,
small-queue and higher-load tests supplement, never replace, staggered saturation.

Proposed repeat/budget profile: ten independent runs of each positive case and
transaction cut, including schedules with three consecutive SIGKILLs and ten
clean restarts after drain. Allow up to 120 seconds for a boundary to be witnessed
and 120 seconds to drain after the last injected fault is removed; these are
**test budgets pending approval, not production SLOs**. Missing the observation
point is BLOCKED/NOT TESTED for that cut, not PASS. Missing IDs at the fixed drain
deadline are FAIL. Preserve a longer diagnostic attempt separately if needed;
do not erase the failed timed run. Native loss must never be repaired with replay
and then reported as a native PASS.

## Independent accounting and acceptance oracle

Before emitting each record, the producer durably stores its stable ID, original
payload hash, source/organization/collector/method identity and ordered window.
Do not reconstruct expected events from queue contents or downstream successes.
For each phase export raw IDs and counts, not merely aggregate throughput:

- `E`: independently inventoried, durable producer events admitted to this run.
- `A(i)`: actual authenticated API commit-accepted record attempts for ID `i`,
  with payload/batch hashes and commit times; received/rejected requests separate.
- `P(i)`: independently queried physical PG event rows for ID `i`, with row IDs,
  original-payload identity and creation times; export batch receipts separately.
- Missing `M = E − {i : P(i)>0}`; unexpected `U = {i : P(i)>0} − E`.
- Physical duplicates `sum(P(i)) − |{i : P(i)>0}|`; accepted duplicate attempts
  `sum(A(i)) − |{i : A(i)>0}|`. Distinct events, attempts and rows are never conflated.

Freeze the writer/resolve outstanding requests before each receipt cut; use a
consistent database snapshot and recorded watermark. Correlate queue committed
transaction IDs, old/new item keys, in-flight lists, checkpoint offsets, fsync
results, exporter enqueue/send/ACK observations, API commit and PG receipts.
Server response-send completion alone is not a client ACK. Export and independently
reconstruct pre-fault, native recovery and final phases; a later recovery may not
rewrite an earlier missing set. Validate API payload receipt hashes against DB
receipts and account for deduplicated batch attempts.

For each supported transient-failure case require `M=∅`, `U=∅`, no unexplained
payload/tenant mismatch, and `P(i)≤A(i)` with every physical row linked to an
accepted request. Stable post-drain restarts must not increase attempts/rows.
No-fault/fully-ACKed controls require zero duplicates. At ACK-ambiguity cuts,
resends may duplicate: require a trace explaining every duplicate, including
source rereads, and an explicit per-case duplicate budget approved before running.
An unset production duplicate/order budget blocks production acceptance even if
finite delivery passes. No exactly-once claim follows from zero observed duplicates.

Keep the queue-only invariant visible: a checkpointed unacknowledged item must
remain reachable from committed queue metadata/payload or an independently
committed receipt at every cut. A test ledger detecting its disappearance is a
FAIL, not a durable copy from which the native system can recover.

## Test matrix

| ID | Setup and precise fault/control | Required evidence and result |
|---|---|---|
| N1 historical control | Run unchanged guarded 0.123.0 staggered generated-size fixture before candidate tests: ten in-flight +256 waiting, last source event backpressured | Reproduce 267/257/10 with prior missing set/old-key deletion; record native FAIL and successful reproduction separately. If it does not reproduce, investigate fixture/environment drift; never assume the defect vanished. |
| N2 admission durability | Queue empty, then almost full and full; crash before durable enqueue, after payload/metadata write before commit, after commit/fsync before return, and after filelog checkpoint advancement | Upstream rejection/backpressure must not advance the source past data with no recoverable handoff. Lost source admission must be detectable; all durable admitted IDs eventually arrive. Failed fsync/write must not produce successful durable admission. |
| N3 saturated normal restart | Candidate, same267-ID staggered workload, both SIGTERM and SIGKILL, API held before commit; inspect ten in-flight and 256 waiting | 267/267 after release, no capacity-based dropping or restart deadlock. Prove checkpointed prefix was not masked by source reread. Additional queue-only control quarantines the hashed source on the owned clone and checks the 266 already-queued IDs before separately resuming the uncheckpointed tail; report its denominator separately. No checkpoint reset/replay. |
| N4 recovery transaction cuts | Observe each cut listed below on a fresh saturated clone, then SIGKILL while stopped; repeat each ten times, plus three consecutive crashes during recovery | At every committed cut all preexisting IDs remain recoverable; after final restart all 267 delivered with accounted duplicates. Retain before/after raw queue files, transaction IDs and syscall/commit evidence. |
| N5 exporter/API ambiguity | Crash after durable enqueue, dequeue/in-flight marking, before send, after API receipt before DB commit, after DB commit before ACK, after ACK before queue deletion, and after deletion commit; interrupt API and retry | No successful response before actual DB commit; no permanent native loss on transient interruption. Link every attempt/row and explain deduplication/resends. Queue removal cannot precede its declared successful completion contract. |
| N6 recurrence, outage and source lifecycle | Three successive SIGKILLs per boundary, ten clean restarts after drain; 60-second API outage with full queue/retry; file rotation, truncation and restart with sealed producer windows | Zero missing within supported retained-source boundary, stable final counts, no stalled full queue. Retained/new source identities tracked independently. Unretained truncation is a separate delivery FAIL/unsupported scenario, not a PASS. |
| N7 storage/adverse outcomes | Inject owned queue write/commit/fsync ENOSPC/EIO at each transaction phase; stopped-clone corruption of metadata/payload; unavailable storage; retention expiry; permanent rejection | Errors are surfaced, no success after failed durable admission, failed bytes/backups preserved, operator alert and admission stop as specified. After supported transient storage recovery, reconcile all IDs. Unrecoverable corruption/expiry/rejection keep delivery FAIL/BLOCKED even if refusal/alert tests pass. Never fill the shared disk or delete state to force success. |
| N8 compatibility/rollback | Exact candidate plus generated config and all five methods; populated legacy JSON and queue metadata upgrade, interrupted migration, restart, rollback, API/supervisor/TLS/auth/egress negatives and sandbox constraints | Full compatibility evidence and coordinated state rollback, not just version-string acceptance. CHK-002 remains BLOCKED until independently satisfied. Any changed storage format must retain old/new cuts and prove what rollback can read. |

N4 must map the actual implementation to these observation points: before reading
in-flight metadata; after reading payloads but before any mutation; before the
first durable recovery mutation; after its committed metadata page/fsync; after
each replacement/metadata commit (including zero, one, intermediate and all ten);
before/after clearing in-flight markers; before consumers resume. For an atomic
single-transaction correction, cuts inside the transaction must expose either
complete old or complete new state on restart, never a partly deleted set. Mark
inapplicable old per-item cuts as replaced by named equivalent atomic boundaries
with source justification; do not silently skip them. For an existing-index
redelivery design, cut its ownership/in-flight metadata and completion commits.

SIGSTOP/reassert/SIGKILL must bind the process to the actual committed boundary;
a timer-only kill without witnessed state is not proof of that cut. No source
replay utility may be invoked in N1–N8 native delivery assertions. Filesystem
power-loss qualification requires a separate approved VM/storage fault harness;
process SIGKILL and injected syscall errors do not certify it. If the proposed
production failure model includes power loss, that unexecuted requirement blocks
qualification rather than being assumed from fsync.

## Exit and review

Each case stores exact commands, source/image/binary/config hashes, source windows,
all attempts, receipt cuts, expected/missing/unexpected sets, physical duplicates,
rejections, timeout budgets, fault-witness evidence and scoped cleanup. A passing
reproduction/refusal subtest is distinct from delivery acceptance. Missing test
capability or approval is BLOCKED; an observed gap is FAIL; an unrun case is NOT
TESTED. Do not use a majority pass rate to approve a loss boundary.

A can be recommended for implementation/transition only after all required cases
in the owner-approved failure model pass, support/provenance and rollback are
reviewed, and independent reconciliation is retained. Further production load,
source classes, platforms and independent release gates remain explicit. This
plan supplies neither a custom-binary approval nor a release or transition signoff.
