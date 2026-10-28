# Queue format, rollback and CHK-002

**BLOCKED; design questions only.** Production Contrib0.123.0 pin/guards and the
existing checkpoint recovery utility are unchanged. A supported queue correction
would not by itself authorize a collector transition or resolve CHK-002.

## Two independent state formats

| State | Observed source/history | Consequence |
|---|---|---|
| Legacy exporter queue | Individual `ri`, `wi`, `di`, `si` metadata and indexed payload keys | Preserve populated legacy state and its in-flight/waiting membership; never restore metadata alone against mismatched payloads |
| Newer exporter queue | Protobuf `qmv0` PersistentMetadata: item/byte sizes, read/write indices, currently-dispatched indices; legacy fallback migration | Current source calls destructive recovery before saving unified metadata and separately removing legacy keys. Forward-read support does not establish downgrade safety |
| Filelog checkpoint | Historical default0.163.2 protobuf checkpoint state fails legacy0.123.0 decoding with `decoding file count` | CHK-002 remains independently BLOCKED; exporter queue transactions do not convert filelog offsets/fingerprints |

[Fresh queue metadata schema](source/core-meta.txt) and
[startup/migration source](source/core-main-queue.txt) are source evidence only.
[Checkpoint decision](../2026-10-25-checkpoints/CHECKPOINT_DECISION.md) and
[operator runbook](../../../../../verification/dev052/checkpoints/OPERATOR_RUNBOOK.md) retain actual failed
downgrade, backup/restore boundaries and irreversible cases. Experimental legacy
JSON checkpoint writing and finite rollback results do not certify protobuf
conversion or coordinated production rollback. A stale backup can replay records
already committed after its cut; receipt reconciliation and duplicates remain
necessary. No recovery utility extension is authorized here.

## Questions a supported correction must answer

1. Which schema readers accept populated legacy, qmv0 and any new journal/marker
   state? Is conversion one-way? Supply release-specific support, not a version
   string or an assumption that fallback makes older readers compatible.
2. How does a restart distinguish absent metadata from failed read, corrupt data,
   interrupted migration, and intentionally retired old keys? No failed read may
   authorize an empty queue. PR16230 is an adjacent proposal, not rollback proof.
3. For each migration transaction, which old/new metadata and payload set is
   authoritative? Can an older process ignore the new marker and reprocess or
   overwrite indices? Require explicit refusal or a demonstrated safe reader;
   downgrade must not silently open incompatible state.
4. What happens after replacement commits but before old cleanup, after only part
   of a journal advances, and after downstream commits but before queue ACK?
   Preserve receipt windows and count duplicates; neither restore nor an ACK can
   retroactively cancel committed downstream effects.
5. Can rollback retain all admissions since the backup? A pre-upgrade snapshot
   alone cannot recover later-admitted payloads. If the necessary source/payload
   is absent, report irrecoverable loss/blocked rollback and escalate; do not
   implement replay or discard state under this design task.

## Proposed transition evidence, not an operational instruction

Before any separately approved experiment, freeze exact old/new binary and image
identities, generated config, feature gates, OS/architecture, storage backend,
schema and fixture sources. Stop/exclude all writers and preserve an integrity-
hashed complete queue plus filelog state snapshot, permissions/ownership and a
consistent independent receipt cut. Validate copies on isolated owned paths;
never move the sole surviving state to test compatibility.

Prove upgrade, interrupted conversion, current-format restart, repeated crash and
rollback using preserved populated state and independent expected/attempt/physical
row inventories. Inspect old/new authority at each committed cut. A migration
failure must leave deterministic resumable state or a preserved refusal with an
operator path. Any schema/marker change needs maintainer-owned support and an
explicit rollback boundary before production transition can be considered.

Process SIGKILL tests do not cover host power loss or arbitrary filesystem damage.
An untested backend or unavailable safe rollback remains BLOCKED. No destructive
DB recreation, checkpoint reset, partial-state overwrite or capacity increase is
an accepted rollback. Preserve CHK-001 FAIL until delivery criteria pass, and
CHK-002 BLOCKED until its independent format/restore criteria pass.
