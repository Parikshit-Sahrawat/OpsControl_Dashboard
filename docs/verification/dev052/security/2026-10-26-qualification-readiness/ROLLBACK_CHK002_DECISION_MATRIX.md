# Separate rollback, CHK-002 and safe recovery decisions

**All candidate transition/rollback approvals remain BLOCKED or PENDING.**
No queue migration, checkpoint conversion, backup restore or compatibility test
ran in H. Production0.123.0 guard and checkpoint recovery utility remain unchanged.
The preserved [checkpoint decision](../2026-10-25-checkpoints/CHECKPOINT_DECISION.md),
[operator runbook](../../../../../verification/dev052/checkpoints/OPERATOR_RUNBOOK.md)
and [G rollback analysis](../2026-10-26-upstream-review/ROLLBACK_AND_CHK002_IMPACT.md)
are references, not new operational authorization.

## A. Persistent-queue storage/schema migration

| Decision | Evidence required before qualification/transition | Present outcome |
|---|---|---|
| Legacy queue → qmv0 | Exact reader/writer versions, old `ri/wi/di/si` plus indexed payloads, new qmv0 read/write/in-flight metadata; preserve populated snapshots and complete ownership mapping at each commit | **BLOCKED**. Forward-read fallback is known by source, interrupted migration safety is not qualified |
| Current qmv0 → corrected schema/journal, if any | Maintainer-owned format/version contract, migration generation, authoritative old/new selection, bounded transaction/cleanup semantics | **BLOCKED**: no supported correction or agreed new schema |
| Interrupted migration/repeated restart | Deterministic complete-old/complete-new or resumable state after every failure; all admitted IDs and duplicate rows reconciled | **BLOCKED**; historical newer recovery of legacy state loses9 IDs after partial replacement |
| Downgrade to0.123.0 | Demonstrated old-reader handling or safe explicit refusal of each newer queue format; no unknown marker ignored; populated rollback with receipts | **BLOCKED**; current forward compatibility is not backward compatibility |
| Snapshot restore | Quiesced exclusive writers; whole matching queue/checkpoint/config/binary set, hashes/permissions, consistent receipt watermark; account for all post-snapshot admissions | **BLOCKED for candidate**. Stale backup alone cannot recover payloads admitted later or undo downstream commits |

## B. Filelog protobuf checkpoint compatibility — CHK-002

| Decision | Preserved fact / required proof | Present outcome |
|---|---|---|
| New default checkpoint read by0.123.0 | Historical default newer protobuf state caused legacy `decoding file count` failure | **CHK-002 BLOCKED**, independent of queue repair |
| Experimental legacy JSON write mode | Prior finite compatibility probes used a legacy-write overlay; no universal protobuf conversion or product integration demonstrated | Historical evidence only; no promotion approval |
| Populated checkpoint upgrade/downgrade | Preserve offsets/fingerprints plus corresponding queue state, exact feature gates and schemas; test rotation/truncation/restarts and independently persisted IDs | **NOT TESTED in H; BLOCKED** pending separate scope and compatibility proof |
| Conversion/recovery utility | Proven atomicity, integrity, idempotence, interruption behavior, permissions, recovery limits and accountable review | No utility change allowed in H; existing bounds remain, no conversion inferred from queue migration |

A queue correction must not clear CHK-002. Two protobuf-based formats can be
independent: queue qmv0 metadata and filelog checkpoint encoding have distinct
readers, schemas and failure modes. A version string cannot establish either
format's rollback compatibility.

## C. Safe failure, retention and recovery

| Condition | Required behavior and evidence | Decision rule |
|---|---|---|
| Read/unmarshal error, incompatible version | Preserve exact failed bytes and hashes, stop unsafe mutation, retain diagnosable ownership; consult supported reader/maintainer | Safe refusal can be validated separately; unresolved delivery never becomes PASS |
| Transient ENOSPC/EIO | Retain last durable state, report/backpressure instead of false admission; after authorized fault removal recheck integrity and reconcile receipts | Missing admitted IDs remain FAIL; no destructive reset to get startup success |
| Corrupt/unreadable queue | Quarantine/preserve original and backup; stop/escalate with independently known missing set; never mutate the sole copy | No automatic reconstruction guarantee. Upstream recreate starts a fresh DB and is not a loss-free repair |
| Expired/missing source retention | Refuse unsupported replay/restore; report irrecoverable payload/ID gaps and operator escalation | Retained ledger alone is not retained data. FAIL/BLOCKED remains; no retention waiver |
| Lost ACK or stale snapshot | Reconcile downstream rows/commit receipts and all post-cut admissions; explain duplicate attempts/physical rows and ordering effects | Do not claim exactly-once, truncate receipts, or assume snapshot restore reverses committed delivery |
| Permanent rejection/retry expiry | Preserve reason and missing IDs, stop cycling an unsupported recovery indefinitely; escalate terminal policy | Rejection detection is not successful delivery; any missing ID remains explicit |
| Unknown schema, backend or power-loss semantics | Preserve state; require maintainer contract and separately approved qualification | BLOCKED, not inferred safe from a process restart or fsync setting |

Future recovery approval must name runtime, data-persistence and operations owners,
exact identities, retention/storage/fault boundaries, receipt cut and duplicate
budget. Every irreversible case (lost sole payload, unreadable sole state, missing
post-backup admissions) needs explicit escalation, not a fabricated successful
conversion. Production replay requires a separate enforceable source/inventory/
retention/detection contract; H does not implement it.

**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**
