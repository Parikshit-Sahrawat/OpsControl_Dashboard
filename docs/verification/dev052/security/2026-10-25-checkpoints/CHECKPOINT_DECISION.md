# DEV-05.2A.3B — checkpoint migration and rollback, 2026-10-25

**Overall native acceptance: FAIL. Security BLOCKED; collector promotion BLOCKED;
release NO-GO.** A bounded recovery path succeeded for the measured fixture, but
the interrupted-upgrade delivery test remains failed. No production version guard,
publication, deployment, merge, waiver or DEV-05.2B transition occurred.

Reviewed COLLECTOR_COMPATIBILITY_PLAN.md, the A.3 COLLECTOR_DECISION.md and Issue
#68's checkpoint-only authorization. Work starts at
`28fbe93f06fcc1b8535b0a1b5c628c4bc2e2392a` on the existing release branch.
Recovery implementation commits are `9f10022e79e0a5f5f3e492fde5045d3cd004292f`
and `5c7f1b519076784924b071222a511ec179390a1b`. The final native run is bound to
the latter commit and pre-execution file hashes in `source-inputs-run4.json`.
The independently archived application source remains unchanged 0.123.0. Subsequent
postprocessing/docs hashes are recorded separately.

## Implemented boundary

Chose the explicitly permitted **bounded recovery** alternative, not an unreviewed
in-place BoltDB/protobuf converter. `verification/dev052/checkpoints/recovery.py`
backs up complete stopped checkpoint state, verifies sealed SHA-256 manifests and
unchanged config, requires a complete independent stable-ID archive, atomically
exchanges a verified legacy copy with live state, preserves failed candidate state,
then atomically publishes a deterministic replay input. No checkpoint key/file is
deleted to force a pass. Pending journals block the supported operator start path.

The tested procedure is limited to Linux/local atomic-rename filesystems, owned
0700 roots and 0600 nonlinked state files, stopped/cooperatively locked collectors,
confirmed healthy legacy cuts, unchanged filelog config/identities and complete
JSON-line source records with stable IDs. Existing state advancement, corrupt or
missing evidence, unidentified/conflicting records and unsafe paths are refused.
The production Agent is not wired to the experimental pending-journal gate.

See the [operator runbook](../../../../../verification/dev052/checkpoints/OPERATOR_RUNBOOK.md)
for backup, upgrade, validation, rollback, resume, failure response, data retention,
duplicate effects and irreversible cases. Accountable execution/transition approval
is still missing; this procedure grants none.

The lab uses direct checksum-pinned runtime processes, **not a promoted Agent
contract**. The default 0.123.0 API/Agent guards, installers and pins are untouched.
Actual scoped authentication/TLS ingestion remains enforced. A test-only response
ledger records payload hashes/IDs after the real app commits; PostgreSQL event and
receipt exports independently reconcile successful requests. Neither offsets nor
process health are treated as delivery proof.

## Exact measured results

| Case | Result / evidence |
|---|---|
| Existing collection/lifecycle/re-enrollment/telemetry/access/worker regressions | **53 PASS**, unchanged assertions, legacy pin |
| New offline recovery/security/failure-injection unit tests | **17 PASS** |
| Populated 0.123.0 cut → 0.163.2 legacy-write-mode upgrade | **PASS**, eight pre-cut IDs retained; new IDs delivered |
| Two clean candidate restarts, rotation and retained copy-truncate | **PASS**, 28 distinct IDs in 28 DB rows before interruption |
| Interrupted default 0.163.2 upgrade, then restart | **FAIL**: IDs event-0028 through event-0043 absent from both API/DB after the 65-second validation window |
| 0.123.0 downgrade against default protobuf state | **FAIL reproduced** on a disposable clone; `decoding file count` error; sole original preserved |
| Incomplete archive / live writer / pending partial stage | **PASS rejection tests**, no unsafe start or incomplete replay accepted |
| Partial copy and abrupt recovery-process death after atomic exchange | **PASS**, same transaction resumes without another exchange; hashes preserve failed candidate state |
| Bounded restore + replay | **PASS for finite fixture**: 44 distinct IDs, 100 API-accepted source attempts / 100 DB source rows, 56 duplicate rows, zero missing/unexpected IDs |
| Independent receipt reconciliation | **PASS**, all five DB batch-receipt payload hashes match successful API ledger payloads; one additional control-marker row accounted separately |
| Three clean legacy restarts after recovery | **PASS**, no new source deliveries/count growth |
| Same completed recovery before starting | **PASS idempotent no-op**; after state advances, repeat rewind is refused |
| Direct protobuf→JSON value conversion | **NOT TESTED / not implemented**; bounded backup/archive procedure used |
| Other signals/platforms, power loss, arbitrary corrupt BoltDB, unsupported filesystem, production rollout | **NOT TESTED / BLOCKED** |

Counts are per run, not additive distinct-test totals. Final details are in
`lab-attempt-4/`, `unit-final.log`, `existing-regressions.log` and `test-matrix.json`.
The native lab and fixture preserve exit code **1 / status FAIL** despite successful
independent recovery. No original test was changed to turn that failure green.

Independent DB phase reconstruction in `phase-db-reconciliation.json` shows:

| Phase | Expected distinct IDs | Missing IDs | DB source rows |
|---|---:|---:|---:|
| Legacy backup cut | 8 | 0 | 8 |
| Compatible upgrade / rotation / truncation | 28 | 0 | 28 |
| SIGKILL interruption | 44 | 16 | 28 |
| Default-mode restart validation | 44 | 16 | 28 |
| Bounded recovery / final restarts | 44 | 0 | 100 |

These demonstrate a finite delivery gap and successful retained-source recovery,
**not exactly-once semantics**. Duplicate physical rows are visible by stable ID;
no server-side stable-ID deduplication was added. Source files and the independent
producer inventory prove only the tested retained cut, not arbitrary source history.

## Defects and retained failures

**CHK-001 — interrupted-upgrade delivery gap, unresolved:** after SIGKILL, default
0.163.2 resumed file offsets with an empty exporter queue and did not deliver 16
new IDs within the measured window. API and DB agree. A batch-buffer/durable-queue
handoff window is plausible, but the exact internal cause is not established.
This task does not change production collector pipelines or assert a general loss
fix. Recovery requires retained source bytes and independent ID coverage.

**CHK-002 — protobuf downgrade incompatibility:** default 0.163.2 file checkpoints
are rejected by 0.123.0. The procedure preserves that failed state, restores a
separately verified healthy legacy cut and replays a bounded archive. It does not
claim to convert the protobuf database in place.

Attempt 1 stopped at the failed interrupted-upgrade assertion; later cases in that
attempt are NOT TESTED. Attempts 2–4 preserve the failed case and continue only to
independent recovery/accounting checks, retaining overall FAIL and nonzero exit.
All raw logs remain. Native runs were repeated to bind final code/hash inputs and
exercise added archive refusal guards; no unrelated hosted workflows were rerun.

## State integrity, provenance and cleanup

Verified runtime binaries remain:

- 0.123.0: `6bca4ddd928b4b0880f7ec6c16511922f740c497b4efa4b33915b2d54a729213`
- 0.163.2: `dbd12d55073b70add777895457040f8ede59fc1ee7198d6ae179a37087eea8bb`

The reused owner checks both before running. Config SHA, healthy legacy backup
manifest/file hashes, archive manifest/source hashes, preserved-candidate hashes,
transaction journal, replay SHA, final-state hashes, API payload receipts and DB
row IDs/timestamps are retained. Synthetic evidence tarballs contain the complete
legacy backup, forensic protobuf/crash snapshots, final state and retained inputs;
the exact transaction quarantine is verified in-run and its hashes are journaled.
Opaque evidence is checked for fixture credential bytes before export. It contains
synthetic data only; private credentials/identity/TLS files are excluded.

SHA-sealed files, fsync, atomic rename/exchange and cooperative locks are tested;
none are claimed as a physical power-loss/storage-controller certification.
All four labs removed their named containers/owned anonymous volumes/networks,
private credentials, database and TLS material after evidence preservation. No
unrelated Docker cleanup, image publication or deployment was performed.
Earlier DEV05/DEV051/A.1/A.2/A.3 evidence remains unchanged.

## Approval request / residual risks

Accountable runtime/release/security/operations owners must review the exact code,
unresolved CHK-001 delivery gap, legacy cut evidence, source retention/completeness,
duplicate/downstream effects, pending-journal pre-start integration and filesystem
support before any real recovery or transition. No reviewer/signature is supplied.
Missing/corrupt legacy cuts, lost source bytes, absent independent IDs, unknown mixed
state, order-dependent consumers or unsupported signals can prevent safe recovery.
Automatic abort of a partially published recovery is not implemented; stop and
preserve both trees for expert review. General production recovery is not certified.

Other release workstreams are unchanged and deliberately out of scope. **Keep PR
#69 draft, production guard 0.123.0, promotion/security BLOCKED and release NO-GO.**
