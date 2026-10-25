# Checkpoint backup and bounded rollback/replay — experimental runbook

**BLOCKED for production execution or version promotion.** This is a concrete
procedure for accountable owner review, tested only in disposable Linux fixtures.
It does not change the 0.123.0 production guard, authorize 0.163.2, repair opaque
BoltDB/protobuf values in place, or provide exactly-once delivery. Do not use a
vulnerable rollback runtime as security clearance.

## Supported recovery boundary

- Linux local filesystem supporting atomic `renameat2(RENAME_EXCHANGE)`, directory
  fsync and cooperative BoltDB flock locking. No sequential-rename fallback.
- Execute as the state-owning service UID. State, vault and log roots must be
  private owned 0700 directories; state files must be nonlinked regular 0600
  files. Stop the Agent supervisor, service manager/watchdog and every collector;
  prevent automatic restart throughout maintenance. Killing only the child runtime
  is insufficient. Stop other operators that could write these paths. No symlinks,
  hardlinked state, live writers or cross-filesystem state exchange.
- Only JSON-line **filelog telemetry** with stable unique `event_id` strings and
  unchanged collector/source/method identity, input paths, credentials context,
  TLS/exporter policy and byte-identical config. Other signal queues, arbitrary
  binary/multiline/unidentified records, new parser settings and order-dependent
  downstream workflows are not qualified by this procedure.
- Require a confirmed healthy, pinned 0.123.0 cut and a complete, independently
  established event-ID inventory plus retained source bytes through recovery.
  Hashes prove integrity, not completeness. An inventory reconstructed solely
  from surviving files cannot prove that missing/truncated records never existed.
- Recovery intentionally replays source IDs and can duplicate already-ingested
  events. Accountable application/operations owners must approve duplicate handling
  and any alert/downstream effects. Do not rerun mutating jobs or customer actions.

The tool cannot infer codec provenance from arbitrary BoltDB bytes. A backup
marked `operator-confirmed legacy cut` must actually come from a stopped, healthy
0.123.0 runtime after independently checked receipts. Never label protobuf state
as legacy. Missing backup, complete archive, reliable ID inventory or authority
means **BLOCKED**, not permission to reset state.

## 1. Prepare and back up before upgrading

1. Obtain explicit maintenance/transition and rollback approval. Record source,
   collector/method IDs, config SHA-256, exact runtime binary/image pins, owner,
   source-ID cut and independently persisted receipt evidence. Verify the pinned
   binaries using the existing provisioners; reject mismatches before execution.
2. Stop input writers or establish a durable retained cut. Retain rotated files;
   take a byte-preserving copy **before** copy-truncate. Check retention capacity
   for the whole maintenance/replay window. Snapshot live state only after stopping
   the collector cleanly and reconciling pre-cut API/DB receipts.
3. Save all checkpoint files and queues, not just an offset key. Reserve enough
   space for the original tree, full backup, staged restoration, forensic tree,
   complete log archive and replay file. Partial staging is preserved on failure.
4. Define reviewed paths as the service UID (examples are placeholders, not
   authorization to run against an existing installation):

```bash
CHK_STATE=/approved/private/agent/otel-checkpoints
CHK_CONFIG=/approved/private/agent/otel.yaml
CHK_VAULT=/approved/private/checkpoint-vault
CHK_LOG_ROOT=/approved/private/retained-input
CHK_TOOL=/reviewed/checkout/verification/dev052/checkpoints/recovery.py
```

Create the vault as 0700 before use; verify the existing roots' ownership and
permissions. Keep sensitive real backups outside Git and public evidence.

```bash
python "$CHK_TOOL" backup --state "$CHK_STATE" \
  --backup "$CHK_VAULT/legacy-cut-001" --config "$CHK_CONFIG"
```

The tool acquires exclusive nonblocking locks, copies to a private partial backup,
fsyncs files/directories, verifies hashes, seals a hashed manifest, and atomically
publishes the backup. Preserve `manifest.json` and `SEALED` hashes in the maintenance
record. Neither an existing cut nor failed candidate state is overwritten.

## 2. Experimental upgrade and validation

Production remains pinned to 0.123.0 until separately approved. The A.3 experiment
uses exact 0.163.2 plus `--feature-gates=-filelog.protobufCheckpointEncoding` at
validation/start to preserve legacy JSON writes. That is not proof of crash-safe
delivery or conversion of previously written protobuf state.

For an approved isolated experiment, start against the backed-up populated state;
append known IDs and reconcile each with actual API and DB receipts. Test clean
restart, rotation and retained truncation. Preserve the pre-upgrade backup and all
source records. **Observed failure:** killing default-mode 0.163.2 after new input
left 16 of 44 IDs absent after restart in the retained fixture. Exporter queue
metadata was empty while filelog resumed known offsets; the exact internal loss
window needs separate investigation. Never call offsets alone delivery proof.

## 3. Freeze a complete recovery archive

Stop collector and source writers. Preserve the full failed tree before probing
other binaries. Probe downgrade only on a disposable clone with approved network
isolation; 0.123.0 may write queue metadata before rejecting protobuf file state.
Never experiment on the sole original tree.

The expected-ID JSON file must be a nonempty array derived from an independent
durable producer/receipt inventory. List all reviewed retained source files:

```bash
python "$CHK_TOOL" archive --expected-ids /approved/private/expected-ids.json \
  --output "$CHK_VAULT/archive-001" \
  /approved/private/retained-input/app.log \
  /approved/private/retention/app-before-truncate.jsonl
```

Missing IDs, conflicting bodies for an ID, malformed JSON, or unidentified source
records are refused. The only no-ID exception is the explicit reserved tool control
marker. Identical structured records sharing an ID are canonicalized once in the
sealed archive; originals and their hashes remain separately retained. The replay
uses deterministic lexicographic ID order, not a claim about original chronology.

## 4. Restore and bounded replay

Check the legacy backup/config/archive hashes again and confirm every producer is
stopped. Choose one stable transaction ID for this recovery. Do not invent a new
ID to bypass a refusal or cause another rewind.

```bash
python "$CHK_TOOL" recover --state "$CHK_STATE" \
  --backup "$CHK_VAULT/legacy-cut-001" --archive "$CHK_VAULT/archive-001" \
  --config "$CHK_CONFIG" --vault "$CHK_VAULT" --replay-root "$CHK_LOG_ROOT" \
  --transaction rollback-001
python "$CHK_TOOL" check-start --vault "$CHK_VAULT"
```

The replay root must be in the **already approved input include glob**. The tool
checks byte config identity, not arbitrary resolved environment or include-glob
semantics; the owner must verify this contract. It does not alter collector config.

A durable journal records PREPARED/STAGED/RESTORED/COMPLETED. A verified full legacy
copy is atomically exchanged with live state; the entire failed candidate tree
remains at the journal's `preserved_candidate` path. No BoltDB key is edited or
discarded. The replay file is published atomically with source IDs unchanged and
one explicit control marker that gives it a fresh file fingerprint. This can
re-deliver both original retained files and archived records; duplicates must be
accounted for, not hidden.

The service must remain stopped until `check-start` succeeds. This experimental
pre-start gate is an operator obligation, **not integrated into the production
Agent/service**. Bypassing it is unsupported. Resume only the approved legacy
runtime/config; this procedure does not coordinate backend/Agent version changes.

## 5. Validate and close recovery

Reconcile expected IDs against independent successful API payload hashes and DB
event/receipt rows. Report missing IDs, unexpected IDs, accepted attempts and
physical duplicate rows separately. Do not mark recovery complete from a healthy
process, an offset or a row count alone. Exercise repeated restarts without new
input and ensure counts do not grow unexpectedly. Keep every failed attempt.

Measured fixture outcome after bounded recovery: 44 distinct IDs, 100 source-event
rows, 56 duplicate rows, zero missing IDs, plus one control-marker row. These are
finite persisted observations, not a general exactly-once guarantee or universal
duplicate budget.

Before starting the collector, repeating the same completed transaction is a
verified no-op. After the collector advances state, repetition is refused to
prevent a second rewind; that refusal does not mean the completed recovery failed.

## Failure response and irreversible boundaries

- Partial/empty copy or process death before exchange: original state remains;
  resume the **same** transaction. Incomplete staged copies are quarantined.
- Death after atomic exchange: the journal plus both tree hashes identify that
  exchange already occurred. Resume; never exchange again blindly.
- Death before replay publication: startup stays blocked. Resume to publish the
  complete replay, then validate. Never manually clear pending journal state.
- Corrupt backup/archive, changed config, replay-path collision, unsafe permissions,
  unknown mixed state or advanced state: stop and preserve all evidence. No force
  option, checkpoint deletion, automatic reset or non-atomic fallback is provided.
- If recovery itself must be abandoned, keep both trees and the journal, leave the
  service stopped and obtain expert/owner review. Automatic abort/reversal of a
  partly published recovery is **not implemented**.
- Missing legacy cut, lost source bytes beyond retention, missing independent ID
  inventory or unapproved duplicate effects can make zero-loss recovery impossible
  to establish. Mark BLOCKED; do not invent receipts or claim restored offsets
  recovered the data. Physical power-loss, other OS/filesystems, huge states and
  unrelated collector signal queues are NOT TESTED.

`--inject-failure` exists only for disposable tests. Never use it on real state.
Retain backups/forensics until accountable owners approve disposal under their
retention policy. This runbook grants no production execution/transition approval.
