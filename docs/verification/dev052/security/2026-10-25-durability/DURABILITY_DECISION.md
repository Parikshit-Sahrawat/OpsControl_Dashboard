# DEV-05.2A.3C decision — 2026-10-25

**CHK-001 FAIL; CHK-002 BLOCKED; SECURITY BLOCKED; RELEASE NO-GO.**
Draft PR #69 / Issue #68 remain open. No publication, deployment, merge,
vulnerability waiver, production version change or DEV-05.2B work occurred.

Implementation commit: `7af6927a16056597794c42549a813d3408860a57`.
Task-start source: `76a97e3fcf6709533151fffb36b16138e4475aba`.
Original product baseline: `f617cc653a965c2ad1bb7edf9e20237e40044b97`.
The evidence commit is the commit containing this report; source file hashes and
format-only AST equivalence to the executed staged product are recorded separately.

## Decision and remaining defect

The exact 16-of-44 baseline loss was reproduced before edits. In-memory pipeline
batching and the Stanza emitter allow checkpoints to outrun durable delivery.
The candidate synchronizes those handoffs, enables fsync/backpressure/infinite
transient retry, and retains the default 0.123.0 pin/guard. See [root cause](ROOT_CAUSE.md).

The **unchanged default-size 0.123.0 queue still loses ten already-checkpointed
in-flight IDs on saturated restart**: 267 expected, 257 distinct/physical rows,
257 accepted attempts, zero duplicates; missing `event-0000`–`event-0009`.
Read-before-delete/re-enqueue failure in the upstream persistent queue is the
remaining supported-runtime blocker. The queue is empty at the final failure cut.
No source replay/conversion was added to conceal the failure.

A burst case with the same default queue passed 271/271 only with 255 physical
duplicates; its earlier checkpoint allowed replay to mask queue deletion. The
staggered case prevents that masking. No exactly-once claim is made.

## Exact selected candidate matrix

These are the latest adjudicated per-case results across the named runs, **not a
claim that one entire run passed**. Earlier failed attempts are retained in
[all-attempts.json](all-attempts.json). Known negative delivery outcomes stay FAIL.

| Runtime / case | Result | Expected | DB distinct | Missing | Accepted attempts | Physical rows | Duplicate rows |
|---|---|---:|---:|---:|---:|---:|---:|
| 0.163.2-before_read | PASS | 4 | 4 | 0 | 4 | 4 | 0 |
| 0.163.2-after_checkpoint_before_commit | PASS | 4 | 4 | 0 | 4 | 4 | 0 |
| 0.163.2-after_commit_before_ack | PASS | 4 | 4 | 0 | 8 | 4 | 0 |
| 0.163.2-after_ack | PASS | 4 | 4 | 0 | 4 | 4 | 0 |
| 0.163.2-unavailable_api | PASS | 4 | 4 | 0 | 4 | 4 | 0 |
| 0.163.2-queue_saturation | PASS | 10 | 10 | 0 | 10 | 10 | 0 |
| 0.163.2-repeated_crashes | PASS | 4 | 4 | 0 | 4 | 4 | 0 |
| 0.163.2-retained_source_before_read | PASS | 4 | 4 | 0 | 4 | 4 | 0 |
| 0.163.2-expired_source_before_read | FAIL | 4 | 0 | 4 | 0 | 0 | 0 |
| 0.163.2-permanent_rejection | FAIL | 4 | 0 | 4 | 0 | 0 | 0 |
| 0.123.0-before_read | PASS | 4 | 4 | 0 | 4 | 4 | 0 |
| 0.123.0-after_checkpoint_before_commit | PASS | 4 | 4 | 0 | 4 | 4 | 0 |
| 0.123.0-after_commit_before_ack | PASS | 4 | 4 | 0 | 8 | 4 | 0 |
| 0.123.0-after_ack | PASS | 4 | 4 | 0 | 4 | 4 | 0 |
| 0.123.0-unavailable_api | PASS | 4 | 4 | 0 | 4 | 4 | 0 |
| 0.123.0-queue_saturation | FAIL | 10 | 9 | 1 | 9 | 9 | 0 |
| 0.123.0-repeated_crashes | PASS | 4 | 4 | 0 | 4 | 4 | 0 |
| 0.123.0-retained_source_before_read | PASS | 4 | 4 | 0 | 4 | 4 | 0 |
| 0.123.0-expired_source_before_read | FAIL | 4 | 0 | 4 | 0 | 0 | 0 |
| 0.123.0-permanent_rejection | FAIL | 4 | 0 | 4 | 0 | 0 | 0 |
| 0.163.2-before_enqueue | PASS | 4 | 4 | 0 | 4 | 4 | 0 |
| 0.163.2-after_enqueue_before_checkpoint | PASS | 4 | 4 | 0 | 8 | 8 | 4 |
| 0.123.0-before_enqueue | PASS | 4 | 4 | 0 | 4 | 4 | 0 |
| 0.123.0-after_enqueue_before_checkpoint | PASS | 4 | 4 | 0 | 8 | 8 | 4 |
| 0.123.0-production_queue_saturation | PASS | 271 | 271 | 0 | 526 | 526 | 255 |
| 0.123.0-staggered_production_saturation | FAIL | 267 | 257 | 10 | 257 | 257 | 0 |

Selected matrix: **20 PASS, 6 FAIL**. Across its independent run-local ID sets:
**646 expected / 619 persisted distinct / 27 missing / 890 accepted record attempts /
882 physical rows / 263 physical duplicates**. Accepted duplicate attempts: 271.
The 27 missing comprise default-queue loss10, small-queue loss1, retention expiry8,
and permanent rejection8. All were detected by the independent test inventory;
no production missing-ID detector is claimed.

- Final regression command: `OPSCONTROL_OTEL_BINARY=/tmp/dev052-online/otelcol-contrib
  .venv/bin/python -m unittest tests.test_collection_v15 tests.test_agent_v15
  tests.test_agent_reenrollment tests.test_managed_telemetry tests.test_access_control
  tests.test_api_worker_v2 -v` from `backend`: **57 PASS, 0 FAIL, 0 SKIP**.
  This includes the two actual pinned-runtime tests and four new configuration/
  Agent contract tests. `regressions-final.log` is the raw result.
- Existing recovery/security procedure tests, unchanged: `python -m unittest
  discover -s verification/dev052/checkpoints -p 'test_*.py' -v`: **17 PASS**.
- Syntax, source whitespace and final formatting checks passed. Local formatter
  was Black25.1.0 on ordinary Python sources with a private cache; this does not
  revise earlier supply-chain advisory dispositions. Its unsupported `--no-cache`
  attempt is retained as a failed tool invocation.
- Ten disposable labs completed scoped cleanup. Three lab-level PASS and seven
  lab-level FAIL; the nine instrumented labs contain **39 PASS / 21 FAIL** scenario
  attempts. The unchanged original lab separately retains its 13 passing checks
  and failed native-delivery case. Repetition is recorded, not added to the final
  selected matrix to inflate coverage.

## Failed attempts and evidence interpretation

`instrumented-baseline-attempt1` did not yet parse the legacy count-prefixed JSON
checkpoint format. Its .123 observation timed out; a read-only parser correction
produced the exact .123 failure in attempt2. No checkpoint bytes were modified.

`fixed-attempt1` omitted the synchronous emitter and failed the saturation safety
predicate; recovery was not reached in that case. `fixed-attempt2` included the
fixed gate, but its initial .123 small-queue fixture waited for four requests at a
single held consumer. That fixture timeout is retained. The corrected one-request
barrier in `boundaries-attempt1` exposed the actual one-ID recovery loss.

The initial syscall fixture used an unavailable `/proc/.../children` file. It was
changed to identify the owned child by PPid, without adding permissions. Attempt2
passed; `boundaries-final` tightens the boundary by keeping the process stopped
between reasserting the snapshot and SIGKILL. Its four cases all pass. There is no
assertion weakening: the saturation safety predicate still yields FAIL and every
failed/recovered run is independently reconciled.

The first live strace smoke attempt found that its owned runner had already been
cleaned up; the next owned runner proved tracing works without added capabilities.
Public source lookup 404s and all raw failed lab logs are retained.

## Limits and independent gates

- CHK-001 remains FAIL. The finite source/queue handoff probes pass, but full-queue
  restart, permanent rejection and expired retention do not provide zero loss.
- CHK-002 protobuf rollback remains separately BLOCKED. Recovery utility, prior
  runbook, guard and pin were not modified. No native protobuf conversion added.
- Alpha feature-gate acceptance, combined Agent/config rollout, throughput and
  retention budgets require accountable owner review. The candidate has not been
  deployed. The request in [OWNER_REVIEW_REQUEST.md](OWNER_REVIEW_REQUEST.md) grants
  no approval and asks for no vulnerability waiver.
- Power/storage failure, long outage/production load and genuine provider tests are
  NOT TESTED here. See [NOT_TESTED.json](NOT_TESTED.json). Test-ledger detection is
  not a shipped event-acknowledgement protocol or loss alert.
- Security/vulnerability, six pip dispositions, licenses, final release-image
  identities, hosted checks and genuine-provider gates retain their prior status.
  No fresh SBOM/security/CI work was performed in this explicitly narrow scope.

## Preservation and cleanup

[cleanup.json](cleanup.json) lists every owned container/network. All ten lab
cleanups passed; owned database volumes, private TLS material and synthetic secrets
were removed. Post-cleanup inspection finds no named lab containers/networks.
Only project-owned resources were removed, with no image publication or broad
Docker cleanup. Synthetic input/checkpoints and redacted logs were preserved first.

465 hashes across prior DEV-05.2 manifests verified; PR65/67 historical evidence
and every frozen security/checkpoint tree compare unchanged against task start.
The recovery utility also compares unchanged. See
[prior-evidence-integrity.json](prior-evidence-integrity.json).

Machine evidence: [test-matrix.json](test-matrix.json), per-run
`reconciliation.json`, `api-timeline.json`, `db-events.json`, `db-receipts.json`,
`e2e.json`, runtime/controller/syscall/metrics logs, state archives/manifests,
[binary-provenance.json](binary-provenance.json), [source-sha256.json](source-sha256.json)
and `artifact-sha256.json`. IDs are scoped by run; do not deduplicate them globally.
