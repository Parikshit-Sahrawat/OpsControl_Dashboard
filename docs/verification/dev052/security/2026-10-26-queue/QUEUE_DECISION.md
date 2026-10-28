# DEV-05.2A.3D decision — 2026-10-26 (Asia/Calcutta)

**CHK-001 FAIL; CHK-002 BLOCKED; SECURITY BLOCKED; RELEASE NO-GO.**
Continue draft PR #69 / Issue #68. No merge, publication, deployment, waiver,
production version change or DEV-05.2B work occurred.

Implementation commit: `d48cf540aa1759b770eee6e30d619f939c281f0a`.
Task-start product commit: `97be9b3d1acffc83367b79cdc9ee179f8b694c05`.
Original product baseline: `f617cc653a965c2ad1bb7edf9e20237e40044b97`.
The evidence commit is the commit containing this report. Source/archive/binary
hashes and exact frozen executed fixture files are retained separately.

## Finding and smallest candidate

The unchanged guarded 0.123.0/default-queue baseline reproduces **267 expected,
257 persisted, ten already-checkpointed IDs missing**, zero physical duplicates.
The queue reads its in-flight payloads, deletes them in a committed transaction,
then attempts replacements. At capacity the old implementation rejects all ten
replacements. Checkpoint advancement is not proof of downstream delivery.

Upstream PR13330, present in core v0.130.0 and newer inspected source, removes the
capacity check from recovery. The previously verified experimental .163.2-labelled
binary passes ordinary full-queue restart, but **two partial-requeue SIGKILL probes
each persist only 258/267 IDs**. After all replacement commits, two SIGKILL probes
persist 267/267. The read/delete/per-item-re-enqueue crash window remains in the
inspected main source. See [causal proof and upstream research](ROOT_CAUSE.md).
No custom binary/fork was built; no runtime transition is approved.

The implemented correction candidate is deliberately separate from native queue
repair: a small offline, bounded source-replay module, plus an isolated synthetic
fixture, safety tests and operator review material. It uses a sealed independent
producer inventory, complete retained JSONL archive and separately queried PG
receipts to publish only missing IDs. Exact legacy binary SHA, scope, retention,
size/ID bounds, private nonlinked inputs, atomic fsynced publication and idempotence
are enforced. A reserved leading transaction marker prevents filelog mistaking the
replay for the original source. No checkpoint/queue mutation, capacity increase,
CHK-002 utility expansion or production Agent hook was added.

This is a measured recovery candidate, **not a complete native collector fix**.
Real-target operation, automatic receipt reconciliation/replay integration and any
custom binary or transition require accountable engineering/operations approval.
The [owner decision request](OWNER_REVIEW_REQUEST.md) records missing signoffs.
The [runbook](../../../../../verification/dev052/queue_restart/README.md) defines
limits and failure response; none of its preconditions grant production approval.

## Exact results

[Machine matrix](test-matrix.json), [readable matrix](MATRIX.md), and
[all attempts](all-attempts.json) retain independent accounting.

- Selected native delivery cases: **4 PASS, 13 FAIL**. All 18 native attempts,
  including the first failed replay experiment: **4 PASS, 14 FAIL**. No failed
  native phase is relabelled because later replay succeeds.
- Three bounded recoveries pass with actual authenticated API/PG evidence:
  saturated legacy restart, three repeated crashes, and an injected queue-write
  ENOSPC followed by native restart. Each progresses **257 → 267 distinct IDs**,
  **267 accepted record attempts / 267 physical rows / zero physical duplicates**
  after replay; two subsequent restarts preserve counts.
- The first unmarked replay attempt remains FAIL: **257/267** after replay because
  its leading-byte fingerprint matched the original file. The corrected marker
  addresses that specific failure; both versions' evidence is retained.
- Transient API process outage and retry: **4/4 persisted**, four accepted attempts,
  four physical rows, zero duplicates. Actual API shutdown/restart was used.
- Expired retention: replay **BLOCKED**, native **257/267** (ten missing).
- Corrupt owned queue metadata: startup reports `invalid database`; **0/267**
  persisted, recovery **BLOCKED**. Backup hash/raw original are preserved. No queue
  repair or destructive reset was attempted.
- Permanent HTTP400 rejection: **0/4** persisted both before and after attempted
  replay, **FAIL**. A test ledger detecting these IDs does not deliver them.
- All selected native phases total **4,013 expected / 3,634 persisted / 379 missing**.
  After the three recoveries, the selected final cuts total **3,664 persisted /
  349 missing / 3,664 accepted attempts / 3,664 physical rows / zero duplicates**.
  IDs are scoped per run. Totals include deliberate negative cases and repetition;
  they are not a production rate or an exactly-once claim.
- New offline safety/failure-injection tests: **17 PASS**. Existing unchanged
  checkpoint/recovery safety tests: **17 PASS**. Relevant collection/Agent,
  re-enrollment, telemetry authorization, access-control and worker regressions:
  **57 PASS, 0 FAIL, 0 SKIP**, including actual pinned-runtime checks. **91 PASS**
  across those regression commands. See `unit-marker.log`,
  `checkpoint-regressions.log`, and `collector-security-regressions.log`.
- Python syntax, Black check and source whitespace checks pass. Formatting did
  not change semantics; final files match the frozen final lab source. No hosted
  workflow was manually dispatched and no unrelated green CI was rerun.

Transaction probes use the real binaries with path-filtered strace write delays,
committed bbolt snapshots, SIGSTOP/reassert/SIGKILL and independently persisted
API/PG evidence. Each before-delete, after-delete, partial-re-enqueue and completed
re-enqueue cut was tested twice. The D fixture keeps capacity256/default10consumers;
its only timing overlay is filelog polling20ms. The unchanged baseline keeps the
original timing. ENOSPC is an actual syscall error injected on the owned queue
write, not exhaustion of the shared host filesystem.

## Evidence quality, failed attempts and limits

Each run includes source ID timelines, config hashes, API attempt/commit/send logs,
PG row IDs/timestamps and receipt payload hashes, raw runtime/syscall logs, queue
metadata snapshots, synthetic state archive and hashes. Phase reconstruction
compares independently queried final PG row IDs/times with native/replay snapshots,
so later recovery cannot erase the earlier gap. `replay-marker/` and later runs
freeze their actual fixture source. The first two new instrumentation runs did
not capture exact in-memory fixture-source hashes; that provenance limitation is
explicit in `source-sha256.json`. Repeated frozen-source probes confirm the findings.

The API runs as a scoped host process with TLS, while PostgreSQL and the non-root
collector runner use isolated Docker networks/containers. The actual application's
authentication/tenant/receipt transaction remains in use. These are synthetic
queue probes, **not genuine provider certification** or final release images.
The .163.2 binary/source-label ambiguity remains recorded; no source correspondence
or release authorization is inferred from its version string.

The candidate is limited to finite retained JSON objects with stable IDs, complete
inventory, trusted fresh receipt cuts, exclusive stopped writers, exact binary,
approved filelog glob and local atomic filesystem semantics. Stale snapshots/new
replay transactions can cause duplicates; loss of retained source, arbitrary
storage faults, real power loss and production operational integration remain
unsupported/unvalidated. [NOT_TESTED.json](NOT_TESTED.json) lists limits explicitly.

## Cleanup and preserved gates

**All six disposable labs cleaned up successfully** after preserving artifacts:
18 named containers, 12 named networks, owned database volumes and private synthetic
credentials/TLS files. Final inspection found no owned container/network residue.
No images were built/published and no broad Docker cleanup ran. See `cleanup.json`.
The fixture source temporary trees are removed by their owner wrapper.

All 395 hashes in prior checkpoint/durability manifests were reverified. Production
application/Agent code, the CHK-002 utility, DEV-05.0/05.1 historical evidence and
all prior security evidence compare unchanged against task start. No backend CVE,
pip, licensing, final-release-image or CI remediation scope changed.

| Gate | Current result |
|---|---|
| Native saturated queue restart / SIGKILL safety | **FAIL — unresolved** |
| Finite bounded source replay | Three measured recoveries PASS; initial attempt and permanent rejection FAIL; owner integration **BLOCKED** |
| CHK-002 protobuf rollback / collector promotion | **BLOCKED — unchanged** |
| Security / supply-chain / licenses / final image identity | **BLOCKED — unchanged independent gates** |
| Genuine providers / production operations / hosted checks | No new certification; prior blockers unchanged |
| Release | **NO-GO** |
