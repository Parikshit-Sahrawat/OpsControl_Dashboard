# B — production bounded replay fallback contract

**Proposed / Pending accountable approval; NOT IMPLEMENTED as a production contract.**
Linked decision: [ADR CHK-001](ADR-CHK-001.md). CHK-001 FAIL, CHK-002 BLOCKED,
SECURITY BLOCKED and RELEASE NO-GO remain. This document does not expand either
existing recovery utility or authorize a real replay operation.

B may be primary only for explicitly admitted source classes where **all** clauses
below are enforced, monitored and tested. Otherwise it is an experimental/manual
recovery possibility, not a delivery guarantee. The following are proposed
production requirements; historical evidence is called out separately.

## R1 — complete durable source inventory and admission

Assign an immutable, tenant/source/epoch-scoped unique event ID and original payload
hash before collector handoff. Define a sealed producer window with expected IDs,
sequence bounds, count, byte count, schema version, archive hash, source generation
and creation/retention times. Rotated/truncated files must remain traceable to that
window. Prefix/tail completeness needs a producer watermark or transactional
source acknowledgment; observing the next event alone cannot detect a lost tail.

Durably commit source bytes and their inventory through a recoverable journal
before acknowledging source admission. If separate files/stores are involved,
prove recovery from each partial write/commit; do not assume a two-file rename is
atomic. On crash, reconcile unacknowledged captures by stable ID without discarding
accepted records. The archive must survive the declared queue/storage failure
model (e.g. an independent failure domain for a lost queue disk), with verified
backups, integrity checks and access control. SHA seals detect modification but
do not authenticate a producer or establish source completeness by themselves.

An inventory synthesized from delivered rows, queue contents or surviving source
fragments is insufficient. Source classes without enforceable durable capture,
complete inventory and pause/reject admission semantics are **ineligible for B as
primary**. Do not accept telemetry under a completeness promise while capture is
unavailable. Availability impact of backpressure must be explicitly approved.

## R2 — bounded retention and capacity enforcement

Owners must approve numeric limits for admitted bytes/events/rate, supported
outage, detector lag, human response, recovery duration and post-recovery audit.
For each supported window require:

`T_keep > T_outage + T_detect + T_page + T_replay + T_validate + T_margin`.

Size archive capacity from the admitted peak byte rate over `T_keep`, plus
inventory/index overhead, replay staging and backup headroom. Record the chosen
values, capacity measurements and failure-domain assumptions; no production
numbers have been approved here. A recovery lease must prevent expiry of its
sealed inputs. Purge only after independent receipt closure and the required audit
retention, never solely because a filelog checkpoint or exporter ACK advanced.

Bounds must be enforceable: alert and stop/reject further admission before quota
or time guarantees become impossible. Do not silently purge undelivered data or
extend an unbounded retry/lease indefinitely while claiming bounded storage.
If an outage exceeds the approved bound, declare the promise breached and escalate;
retain unresolved evidence, do not record delivery success. Missing/expired bytes
are irrecoverable by replay unless an independently verified retained backup exists.

Historical D helper limits are **10,000 unique `event-NNNN` IDs and 16 MiB per sealed
input**, exact legacy SHA, private local files and an explicit deadline. Those
finite synthetic limits are not a production capacity/SLO or universal log format.
A production implementation must also bound output expansion, concurrent windows,
replay concurrency and retry cost; those controls are not established by D.

## R3 — independent missing-ID detection and receipts

Maintain a production reconciler independent of collector queue/checkpoint state.
It compares sealed expected windows with authorized, consistent PostgreSQL receipt
exports scoped to organization, source, collector/method and schema/config epoch.
Use the primary commit visibility or a measured, bounded replica watermark; an
absent row on a lagging replica is not immediate proof of loss. Record row IDs,
original event/payload identity, transaction/commit cut and accepted API batch
receipts. Current batch receipt hashes alone are not a complete per-event source
inventory. The production receipt export and reconciler need their own contracts;
the D private-file fixture API is not such a service.

Persist expected, accepted, rejected, present, missing, duplicate and unexpected
sets/counts per sealed window. Distinguish pending within the approved delivery
budget from overdue gaps, but never call a window complete while a gap exists.
Reconcile on restart/outage, source-window sealing and a bounded periodic schedule.
A no-new-events tail, detector crash, missing heartbeat, stale receipt watermark,
partial/unavailable inventory or archive corruption must itself alert and stop
claiming protection. A detector deriving expectations from its own successes can
miss an entire lost window and does not satisfy this clause.

Detection has a separate outcome from recovery: alerting on ten missing IDs is
not delivery of those IDs. Detection completeness must be demonstrated with
intentional dropped IDs, entire missing windows, missing tails, reordered events,
duplicate IDs, receipt lag and detector outage. Production liveness/coverage
monitoring is required even when A is selected as the primary path.

## R4 — authorized, idempotent recovery protocol

Use these durable states: `SEALED → GAP_IDENTIFIED → REVIEWED → PREPARED →
PUBLISHED → RECONCILED → CLOSED`; any uncertainty enters `BLOCKED/ESCALATED`.
Each transition records actor/role, input hashes, scope, exact binary/config/schema,
window, receipt cut and transaction ID. Recovery authorization must be scoped and
audited; never trust caller-supplied tenant IDs or a JSON `writer_stopped` field as
production proof of authorization/exclusive ownership.

Fence the relevant writer and automatic recovery controllers, settle outstanding
requests, and obtain a fresh consistent receipt cut. Verify complete archive/ID
coverage and retention before selecting missing IDs. A lease/fencing token or an
equivalent owner-reviewed exclusive-operation protocol must prevent concurrent
or stale recovery writers; private permissions alone are not a distributed lock.

Bind the recovery transaction deterministically to approved sealed inputs, receipt
cut, scope and exact config/runtime. Write a private bounded staging file, fsync,
validate its hash/permissions and atomically publish into an already approved
filelog path; fsync the parent directory. Preserve original IDs/fields and an
explicit reserved replay-transaction marker to prevent original-file fingerprint
aliasing. Test collision/format handling; the D marker fixes one observed case,
not every possible parser/format/fingerprint interaction.

A crash must resume the same transaction or stop on a corrupt/partial stage;
never silently overwrite, discard, rewind checkpoints or reset queue state.
Identical sealed input publication must be an idempotent no-op. Changing a receipt
cut creates a new plan and requires reconciliation and authorization again. The
collector must be able to start safely; B does not fix a corrupt queue or decode
incompatible filelog checkpoints. Restoration is a separately reviewed operation.

Replay only through the existing authenticated, TLS-protected, tenant/method-scoped
collector/API path. Do not write events directly into PG to manufacture success,
relax egress/credentials, add arbitrary headers, or use production secrets in
verification. After restart, independently export receipts and reconcile the same
original IDs. Close only when all expected events are actually persisted and all
unexpected/duplicate effects are accounted for. Keep the failed native phase.

## R5 — duplicate and ordering contract

Record `expected IDs`, authenticated accepted record attempts, PG distinct IDs,
missing IDs and physical duplicate rows for every phase, using the definitions in
[the native plan](NATIVE_ACCEPTANCE_PLAN.md). Retry requests and duplicate rows are
not equivalent: batch deduplication can suppress rows while attempts increase.
Use immutable original payload identity so replay metadata does not masquerade as
a different original event; flag same ID/different original content as a conflict.

Idempotent replay-file publication does not imply exactly-once ingestion. Stale
snapshots, ACK loss, new plans and source rereads can duplicate or reorder records.
Owners must approve downstream duplicate budgets and ordering semantics per
source class before primary use; consumers that cannot tolerate measured effects
are not eligible without separately reviewed deduplication/ordering work. No such
backend change is authorized by this ADR. A final zero-missing/zero-duplicate
sample alone is not certification of exactly-once delivery.

Historical counterexamples must remain visible: B's earlier 44-ID recovery used
100 physical rows (56 duplicates), and C's burst case produced 255 duplicates.
D's three 267-ID recoveries had zero physical duplicates in those finite runs only.

## R6 — irrecoverable conditions and operator escalation

| Condition | Required action and recorded outcome |
|---|---|
| Missing/expired source, incomplete inventory, lost tail with no authoritative watermark | Stop automatic replay; preserve expected/missing sets and surviving material; notify source owner and SRE. Delivery FAIL, recovery BLOCKED; do not infer missing bytes. |
| Corrupt queue or incompatible protobuf state | Preserve full stopped state and hashes; do not delete/reset it or reuse the CHK-002 utility without its separate approved boundary. Runtime owner reviews restoration; delivery FAIL/BLOCKED. |
| Permanent API rejection / tenant or payload violation | Quarantine the rejected event and reason under scoped access; alert API/data owner. Correct cause only through approved change, then a new audited plan. Never turn a rejected ID into a successful receipt. |
| Receipt export unavailable/stale; detector or archive heartbeat absent | Protection status UNKNOWN/BLOCKED, not healthy. Stop closure and unsafe replay, enforce admission/retention limits and page operations. |
| ENOSPC/EIO, backup hash failure, partial journal or stale fencing token | Stop publication/admission, retain staged/original evidence, alert storage/runtime owners. Resume only after integrity and exclusive ownership are re-established. |
| Undocumented duplicate/order effects or scope mismatch | Stop and escalate to data/API/security owners; preserve raw attempts/rows. No silent acceptance or cross-tenant recovery. |

Define an on-call recipient, alert acknowledgment deadline, recovery authority and
handoff/escalation deadline before operation. Those names/numeric budgets are
PENDING. Incident records must carry run/window identity, hashes, missing IDs,
remaining retention, request/commit chronology, actor actions and closure evidence;
redact credentials. No alert acknowledgment or operator waiver counts as delivery.

## R7 — qualification and present gap

Before B can be primary, demonstrate durable source capture interrupted at every
journal boundary; rotation/truncation with complete windows; archive loss within
the declared failure model; quota/expiry enforcement and backpressure; dropped
prefix/tail/whole-window detection; detector and receipt-service outage/lag;
concurrent/stale recovery refusal; pre/post-publication crashes; duplicate/conflict
accounting; permanent rejection; and post-recovery restarts. Use independently
persisted authenticated API/PG receipts and retain every delivery failure.

D demonstrates finite sealed-file validation, marker-based replay, publication
idempotence and some process-crash refusals. It does **not** implement or certify
production R1 capture/admission, R2 retention enforcement, R3 detector/receipt
service, distributed R4 fencing/authorization, or approved R5/R6 budgets/ownership.
Thus **B is presently BLOCKED as primary**. The named roles and approval record in
the ADR must be completed before an implementation scope or real operation is
approved. This proposed contract grants neither approval nor a release exception.
