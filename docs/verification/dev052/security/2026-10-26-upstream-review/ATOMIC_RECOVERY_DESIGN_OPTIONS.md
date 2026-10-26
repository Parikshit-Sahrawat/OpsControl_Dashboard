# Atomic/resumable recovery — proposed design questions

**Proposed / PENDING upstream and accountable owner review. Not implemented.**
Source finding: [decision](UPSTREAM_REVIEW_DECISION.md). Production 0.123.0 stays
pinned. None of these options is an approved fork, supported feature or delivery
guarantee. Independent reconciliation remains mandatory for every option.

## State and invariant

Let `p(i)` be an admitted request payload (potentially containing multiple stable
event IDs), `R` the authoritative durable waiting/in-flight index set, `M` the
durable schema/migration generation, and `C(i)` independent committed receipts.
For every admitted, unacknowledged item `i`, every committed cut must preserve
`reachable(R, M, p(i)) OR C(i)`. Reachability means a restart can enumerate and
recover the bytes without guessing keys, replaying the source, or consulting the
test inventory as a substitute payload store. An orphan payload is insufficient.
The invariant is request-level; qualification reconciles all constituent event
IDs and payload hashes, including partial-success behavior.

Queue admission, filelog checkpoint, exporter completion, HTTP response, client
ACK and database commit are separate facts. Collector normally cannot query our
receipt store: downstream commit-before-success is a qualification precondition,
not a capability supplied by this proposal. A missing client ACK requires keeping
recoverable work even when the server may have committed. Duplicate delivery is
possible; every observed attempt/row must be explained. No exactly-once claim.
Permanent rejection/retry exhaustion may be upstream terminal policies, but any
undelivered inventoried ID still fails delivery. A terminal disposition must never
be silently reclassified as a successful receipt.

| Durable state | Requirement before acknowledging or retiring anything |
|---|---|
| Offered, not yet admitted | Failed/unfinished writes cannot signal successful durable admission; upstream retains/backpressures the source |
| Waiting/in flight | Persist payload plus authoritative index/ownership together; dispatch must not eliminate the sole durable copy |
| Recovery prepared | Original payload/index remains authoritative; any intent identifies exact generation, old key and replacement key |
| Replacement committed | New payload and reachable metadata commit together; original can be retired only in that transaction or after it is independently durable |
| Recovery complete | Every old item maps to a live replacement or confirmed completion; clear markers only after this is durable |
| Completion/ACK ambiguity | Persist recoverable item or replay-safe completion frontier; duplicate possibility remains explicit |
| Error/corruption | Stop admission/recovery as required; preserve state and report unresolved IDs; never initialize empty state as a successful recovery |

Invariant violations remain FAIL even if an independent detector notices them.
The source inventory is defense in depth, not an implicit native recovery copy.

## Candidate design alternatives for upstream review

| Option | Proposed transaction model | Benefit | Questions/risks blocking acceptance |
|---|---|---|---|
| A. Resume original indices | Persist an explicit recoverable in-flight set; redeliver those original keys; remove payload and ownership metadata only on completion | Avoids payload movement and full-queue re-admission; potentially smallest format change | Dispatch ownership, ordering, size accounting, sparse indices, out-of-order ACK, read-index advancement and legacy migration must all remain crash-safe; no claim current implementation does this |
| B. Atomic old/new transition | Pre-read/validate payloads while originals remain authoritative; one supported transaction writes replacement payloads, authoritative metadata and old-key retirement | A crash exposes either complete old or complete new state; existing bbolt Batch may support the bounded transaction | Storage abstraction guarantees, fsync/commit error semantics, maximum transaction size/memory, concurrent ACK/producer exclusion and index collision need review; one giant unbounded transaction is unacceptable |
| C. Resumable migration journal | Durably record generation and stable old→new mapping; commit each replacement and its progress marker atomically while retaining originals; atomically switch authority before idempotent cleanup | Bounds work per transaction and resumes partial migration | Additional schema and dual-authority complexity; every restart must pick a single authority and not duplicate admissions; more rollback/maintenance burden than A/B |

For B, a per-item atomic transition can be viable only if every transaction updates
both the old in-flight set and new reachable index/size state consistently; merely
changing delete order is not proof. For C, a journal containing only counters or
intent without either payload plus a recoverable authoritative pointer is not
durable handoff. Old/new authority selection must not depend on in-memory state.
Recovery work already admitted must not be rejected as a fresh producer offer at
full capacity. Capacity accounting must not double count retained originals and
replacements; new offers may remain blocked until recovery completes.

Preferred review order: ask whether A can preserve existing keys with minimal
metadata change; compare B against the actual storage contract; consider C only
if transaction bounds or migration requirements justify its extra schema. This
ordering is a proposal, not an implemented correction or maintainer preference.
Do not replace recovery safety with larger capacity, source rewind, corruption
reset, relaxed fsync, or optimistic success logging.

## Required failure semantics

| Fault | Proposed required behavior | Acceptance consequence |
|---|---|---|
| Full queue at recovery | Preserve admitted in-flight work; reserve/transfer ownership without producer capacity rejection; block new admission where necessary | Saturated original workload must drain; a larger queue alone is insufficient |
| Payload/metadata read failure | No destructive mutation; retain original state; explicit startup failure/retry | Current source attempts cleanup before checking retrieve error; adjacent PR16230 alone does not cover this |
| Missing payload/unmarshal error | Preserve failed bytes/indices and diagnostic identity; fail closed or explicit quarantine with durable unresolved ownership | Logging and skipping is not delivery; missing ID stays FAIL |
| Commit/fsync/write ENOSPC/EIO | No acknowledged admission or authority switch without known durable outcome; restart from committed state, resolving ambiguous outcome safely | Witness actual storage commit boundaries; error return alone does not prove rollback |
| SIGKILL during migration | Restart from complete old/new state or journal progress; no reliance on process memory; repeated interruptions idempotent | Ten runs per cut and repeated-crash schedules required |
| Out-of-order completion/lost ACK | Do not retire earlier unacknowledged items based on a later ACK; track durable sparse completion or safe frontier | Account for legitimate resends and physical duplicates; freeze budgets before tests |
| Corrupt queue or exhausted retention | Preserve failed state/backups; stop/escalate with a precise missing set where independently known | Corruption refusal may PASS while delivery remains FAIL/BLOCKED; recreation does not restore lost data |
| Permanent rejection/retry expiry | Explicit reason, IDs/receipt evidence and terminal policy; do not suppress missing IDs | No waiver or successful-delivery claim; supported delivery boundary remains limited |

The [storage API](source/storage-contract.txt) describes Batch operations but
does **not explicitly promise all-backend atomicity**; its Walker commentary
conditions transaction semantics on storage support. The bbolt implementation's
per-Batch Update is concrete evidence for that backend, not a universal contract.
Option B therefore needs a supported transactional capability or an explicit
backend restriction, reviewed by maintainers. A process kill is not power-loss
certification. `file_storage.recreate`
can keep a backup and start a new DB according to upstream documentation; that
availability feature is not an approved loss-free repair and must not mask this
test's missing records. No fault injections were run in G.

## Evidence and decisions needed

Maintainers must identify a concrete source transition and map every old-key,
replacement, metadata, ACK and journal commit to the
[unchanged N1–N4 plan](../2026-10-26-adr/NATIVE_ACCEPTANCE_PLAN.md), using the
[alignment](NATIVE_TEST_ALIGNMENT.md). Storage owners must confirm transaction
atomicity/durability and failed-commit semantics; runtime/verification owners must
approve observers and exact candidate identity. Schema/rollback implications are
separate [blocking decisions](ROLLBACK_AND_CHK002_IMPACT.md). The proposed invariant
is stronger than an ordinary restart demonstration; no existing POC or author
benchmark satisfies it by implication.
