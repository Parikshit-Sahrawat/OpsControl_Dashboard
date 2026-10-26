# N1–N4 alignment — design only

**N1, N2, N3 and N4: NOT RUN in DEV-05.2A.3G. Qualification BLOCKED.**
No new expected/persisted/missing/attempt/duplicate counts exist; each is **null**,
not zero. Source review and document validation are not runtime tests. The
[original acceptance plan](../2026-10-26-adr/NATIVE_ACCEPTANCE_PLAN.md) remains
unchanged; this document maps design questions to it without weakening assertions.

| Case | G execution | Required future evidence |
|---|---|---|
| N1 guarded control | NOT RUN | Unchanged 0.123.0 original staggered 267-ID fixture, capacity256/default10consumers, original generated polling. Historical 267/257/10 must be reproduced and retained as native FAIL, distinct from successful defect reproduction. Investigate drift if absent. |
| N2 admission | NOT RUN | Empty/almost-full/full queue; before enqueue, write-before-commit, commit/fsync-before-return and after source checkpoint. Show durable admission, failed-write backpressure and no checkpointed unowned payload. Source handoff failures remain visible. |
| N3 saturated restart | NOT RUN | Candidate, original 267-ID fixture, SIGTERM and SIGKILL with API held before commit. Independently show ten in-flight/256 waiting. Require 267/267; additional queue-only cloned control quarantines source and accounts for 266 admitted records separately before resuming the uncheckpointed tail. No source replay/reset. |
| N4 interrupted recovery | NOT RUN | Witness each actual transaction cut below on fresh saturated state; at least ten independent repetitions per cut, schedules of three consecutive crashes, ten clean restarts after drain, populated legacy and current schema, partial migration. Preserve all missing-ID FAILs and observation-point BLOCKED cases. |

The ADR proposes 120 seconds to witness a cut and 120 seconds to drain after final
fault removal. These are test budgets, not production SLOs. Carry the existing
isolated-study governance into a new explicit scope decision; do not infer that G
authorizes execution. An unwitnessed cut is BLOCKED, not an uninstrumented PASS.
Missing IDs at the accepted drain deadline are FAIL; later diagnostic recovery
must not overwrite that result.

## N4 cut mapping required before implementation/qualification

| Required observation point | Existing-index proposal A | Atomic proposal B | Journal proposal C |
|---|---|---|---|
| Before in-flight metadata read; after payload read, before mutation | Preserve original ownership | Preserve original indices/payloads | Preserve original authority; no intent assumed |
| First recovery mutation, before/after committed page/fsync | Witness durable redispatch/ownership state | Witness precommit and postcommit old/new transition; interrupted transaction exposes old or complete new | Witness intent/generation commit before any retirement |
| Replacement zero, one, intermediate, all ten commits | Map explicitly to original-index dispatch/ownership/completion transitions | If single transaction, justify replacement of old per-item cuts with named inside-transaction and final-commit cuts; do not silently skip | Witness each mapping/progress/payload commit; all unconverted originals remain reachable |
| Before/after clearing in-flight/migration markers | No forgotten original owners | Clear only within/after full authority transition | Completed generation and authority switch durable before cleanup |
| Before consumers resume | All pending work enumerated consistently | New authority durable, no stale old deletion | Resume current generation once, cleanup idempotent |
| Repeated restart/partial migration | No repeated admission or lost ownership | Reopen exact committed side deterministically | Resume durable generation/progress, including failed cleanup |

These are proposed mappings, not substitutes already accepted by upstream. Bind
SIGSTOP/reassert/SIGKILL to committed queue snapshots, transaction IDs and syscall
evidence. If a supported binary cannot expose/certify a required boundary, report
BLOCKED; do not build an unauthorized instrumented fork or use timer-only kills.
Test both legacy migration and already-current qmv0 recovery. Historical newer
partial-requeue results covered populated legacy state; they do not cover both.

## Independent accounting for every phase

Before emission, persist source IDs and original payload hashes independently.
Preserve admission evidence separately from the 267-event producer denominator.
Capture actual authenticated API accepted record attempts and batch/commit times;
independently export PostgreSQL physical row IDs, event IDs, payload hashes and
receipt timestamps at a consistent frozen-writer watermark. Calculate:

- Expected `E`, distinct persisted `D`, missing `E − D`, unexpected `D − E`.
- Accepted attempts per ID `A(i)`, physical rows per ID `P(i)`.
- Physical duplicates `sum(P(i)) − |D|`; accepted duplicate attempts separately.
- Every physical row linked to an accepted request; original payload and tenant
  identity checked. A received request, response send, client ACK and DB commit
  are not interchangeable witnesses.

Require no missing admitted IDs or unexplained extras/payload differences at
every accepted recovery cut. Fully ACKed/no-fault controls require zero duplicates;
ACK-ambiguous resends require traceable explanations and a preapproved per-case
duplicate budget. Distinct counts alone cannot hide duplicated rows. Ledger-only
loss detection is FAIL, not zero-loss. All logs, input/config/binary/observer hashes,
state snapshots, DB exports and cleanup must be retained, including failed runs.

No replay helper is allowed in native qualification. N5–N8, full five-method and
security contracts, storage/power-loss scope, CHK-002 rollback and release gates
remain pending even after a future N1–N4 feasibility PASS. This task promotes none.
