# Recovery invariant and failure-cut coverage

**Proposed acceptance coverage only; no injections or runtime tests in H.**
**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**

> Every admitted, unacknowledged item remains durably reachable until a replacement is committed or delivery is independently confirmed committed.

Durably reachable requires both recoverable payload bytes and an authoritative
committed index/ownership path that restart can enumerate. Orphan bytes, in-memory
copies, a checkpoint, or a test ledger listing missing IDs are insufficient.
Queue requests may carry several event IDs; receipts must reconcile every event,
not just request counts. New main and core0.164.0 retain the old read/delete/
individual-replacement sequence, confirmed by source bytes only. Source review
does not certify all schema/backend paths at runtime.

## Failure matrix

| Boundary/failure | Required safe behavior | Future evidence and classification | Coverage |
|---|---|---|---|
| Capacity saturation | Previously admitted in-flight work retains durable ownership; cannot be dropped as a new producer offer; backpressure new offers without false admission | Inspect256waiting+10inflight; preserve267source inventory/266admission distinction. Missing IDs or full-queue deadlock FAIL | N2/N3/N4 |
| Read error | No destructive payload/metadata mutation based on failed read; explicit retry/refusal preserving state | Witness read failure and unchanged authoritative keys; current code attempts cleanup before checking retrieval error. Refusal success does not equal delivery | N4; adverse coverage N7 |
| Write/commit/fsync error | No successful durable admission or ownership switch without known durable commit; preserve old authoritative copy or resumable transaction | Actual error/transaction IDs and reopened state, including ambiguous commit outcome. Silent disappearance FAIL | N2/N4/N7 |
| Unmarshal/missing payload | Preserve original bytes and unresolved ownership; explicit diagnostic/quarantine/refusal, never log-and-skip as successful recovery | Exact key, payload hash, affected IDs, receipt cut; missing delivery remains FAIL | N4/N7 |
| ENOSPC/EIO | Stop/backpressure admission safely; no false success; preserve last committed state and failed attempt | Owned bounded fault injection only in future authorization, never fill a shared disk. Restore transient capacity then reconcile; arbitrary loss is not waived | N2/N4/N7 |
| Old-key deletion before replacement | No committed state with neither old payload nor durable reachable replacement/confirmed receipt | Witness predelete, postdelete, replacement0/1/intermediate/all; exact invariant violated in historical partial recovery | N4 |
| Partial migration | Durable generation/authority/progress survives; old/new state selection deterministic; cleanup idempotent | Populated legacy and current-schema snapshots, partial progress and all metadata changes independently observed | N4/N8 |
| Repeated crash | No reliance on previous process memory; each restart preserves pending ownership and completion semantics | Ten repeats per cut, three consecutive crashes, ten clean post-drain restarts; stable attempts/rows | N3/N4/N6 |
| Corrupt metadata/payload | Preserve failed data/backups, refuse unsafe state reset, escalate unresolved IDs | Corruption refusal may meet safety criterion while delivery is FAIL/BLOCKED. Fresh empty DB is not recovery | N7; rollback matrix |
| Lost ACK / commit ambiguity | Retain/resend unacknowledged data despite possible downstream commit; do not erase earlier unacknowledged items using later completions | Independent DB commit and actual client-ACK observations; account for every attempt/duplicate physical row, freeze duplicate budget | N4 completion mapping; full N5 |
| Retention expiry/permanent rejection | Preserve known gaps and explicit terminal reasons; stop unsafe recovery and escalate | Expected vs persisted ID sets remain missing. Detection/refusal is not successful delivery; no source replay in native qualification | N7; separate recovery decision |
| Unobservable transaction boundary | Do not claim a timer-only kill hit a specific durable cut | BLOCKED until supported observation or certified boundary available; no unapproved custom instrumentation build | N2/N4 |

No row is a new PASS. Historical corruption, retention and rejection failures
remain preserved. Larger capacity, more retries or successful ordinary restart
alone do not satisfy the destructive transaction boundary.

## Queue safety versus end-to-end delivery

Queue durability concerns admitted payloads surviving supported queue transitions.
End-to-end delivery additionally requires durable source handoff, correct tenant/
payload routing, actual API database commit-before-success, and final persisted
receipts. A filelog offset or exporter completion counter proves none of those
alone. The collector does not automatically consult the independent receipt store.
The receipt oracle detects violations; it is not a new runtime recovery mechanism.

Lost ACKs can cause legitimate retransmission and physical duplicates. Distinct-ID
completeness is not exactly-once; attempts, rows, ordering effects and receipt
payloads must all be retained. Permanent rejection/retry exhaustion can be an
upstream terminal policy and still be a delivery FAIL against the inventory.

Fsync per bbolt Batch does not make several Batches atomic. The generic storage
API's Batch declaration does not promise all-backend atomicity; a supported design
must identify its transactional storage boundary. SIGKILL is not power-loss or
arbitrary-corruption qualification. If production requires those failure models,
their missing tests remain blockers. No new storage guarantee is inferred here.

Design alternatives and questions remain [G's proposed options](../2026-10-26-upstream-review/ATOMIC_RECOVERY_DESIGN_OPTIONS.md).
Only authoritative guidance plus reviewed source/provenance and later scoped
qualification can change readiness. Nothing here authorizes implementing them.
