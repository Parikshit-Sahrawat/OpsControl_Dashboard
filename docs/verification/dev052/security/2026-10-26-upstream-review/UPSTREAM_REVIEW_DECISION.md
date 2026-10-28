# DEV-05.2A.3G — upstream atomic recovery review

Date: 2026-10-26; API observation times in [FETCH_LOG.json](FETCH_LOG.json) are UTC.
Baseline: `432afb6943c980cf027bc31df5bdb2b972bb7ad5`, clean worktree on
`release/dev-05-2-hardening`; [captured PR69](raw/internal-pr69.json) was open,
draft, on that head. This is design/evidence work, not a runtime qualification.

**Supported native candidate: BLOCKED.** No qualifying correction was established
in the refreshed authoritative sources. **N1–N4: NOT RUN**, candidate qualification
BLOCKED. **CHK-001 FAIL; CHK-002 BLOCKED; SECURITY BLOCKED; RELEASE NO-GO.**

## Source finding and support status

Core latest v0.163.0 still resolves to
`5177a6a85ca3783068077e25aec6cebbe1d50d1f`; inspected main is still
`82148555675e5a0a201189cd4220395eb8baa1ad`. Their persistent queue files are
byte-identical, SHA-256
`a98bd9990c2405d0b24cdee951ccacec01b58b4dc347ceb6b7c256ceea789d98`.
Recovery reads in-flight payloads, separately commits deletion of all old keys,
then commits replacement metadata/payloads individually. File storage implements
each Batch with a separate bbolt Update. This permits a committed cut with neither
old durable payload nor replacement for an unacknowledged item. Both qmv0 startup
and legacy migration call this recovery function; that is source analysis, not a
new current-schema crash experiment.

Official Contrib distribution v0.163.2 still resolves to
`6c65793ec707f673304e52dfcb642684fda1a048`. Its manifest binds 0.163.0 components;
OTLP/HTTP depends on exporterhelper0.163.0. Its release notes describe Go/CA updates,
not a queue correction. The earlier distribution/component naming ambiguity is
resolved; supported atomic recovery is not. No new binary, image, config or SBOM
was produced. Publisher artifact metadata is not fresh local binary verification.

PR13330 is merged but its recovery capacity-check removal leaves the transaction
gap. PR15993 is an open **draft** disk-queue POC with author claims about completion
position persistence; it is not a released or maintainer-supported correction.
PR16230 is open/unmerged and addresses metadata-read startup failure, not this
recovery sequence. The other reviewed proposals do not qualify. The
[support matrix](SUPPORT_AND_PROVENANCE_MATRIX.md) records exact identities,
comments, ownership and the distinction between review activity and commitment.

This finite research found no relevant new merged/released correction since F.
It cannot exclude an unpublished, unindexed or unexamined vendor fix. There is no
upstream refusal recorded either: review/support for this exact invariant is
**PENDING**, not declined. All upstream operations were read-only GETs.

## Historical observations, not new tests

| Preserved case | Expected | PG distinct | Missing | Accepted record attempts | Physical rows | Duplicate rows |
|---|---:|---:|---:|---:|---:|---:|
| Guarded 0.123.0 staggered queue, 256 waiting + ten in flight + one source tail | 267 | 257 | 10 | 257 | 257 | 0 |
| Experimental 0.163.2 recovery of populated **legacy** queue, kill after first replacement commit | 267 | 258 | 9 | 258 | 258 | 0 |

The second observation is legacy-to-newer recovery, not a demonstrated crash from
a steady-state qmv0 queue. D's later frozen-source repeats corroborate it; D's
initial instrumentation source-hash limitations remain disclosed. Source-read
reachability of the same function from qmv0 must not be labelled a runtime result.
References: [D decision](../2026-10-26-queue/QUEUE_DECISION.md),
[D causal proof](../2026-10-26-queue/ROOT_CAUSE.md),
[guarded receipts](../2026-10-26-queue/guarded-baseline/reconciliation.json),
[partial-requeue receipts](../2026-10-26-queue/boundaries-repeat/reconciliation.json),
[F reviewed counts](../2026-10-26-native-feasibility/HISTORICAL_BASELINE_REVIEW.json).

D's selected native **4 PASS / 13 FAIL**, historical **91 regression PASS**, three
bounded replay recoveries **267/267**, and retention/corruption/permanent-rejection
failures remain historical. No replay or regression suite ran here. A detected gap
is still failed delivery; independent receipts cannot recreate a lost payload.

## Review package and next narrowly scoped action

The [public-ready draft](MAINTAINER_ISSUE_DRAFT.md) is **unpublished**. Proposed
target: `open-telemetry/opentelemetry-collector` issue tracker, exporterhelper
persistent queue component, using its bug-report form. Current codeowners include
Bogdan Drutu (`bogdandrutu`) and Dmitrii Anoshin (`dmitryax`), with the Collector
approvers team. File-storage owners `swiatekm` and `VihasMakwana` are proposed
consultants for storage semantics, not assigned reviewers. No one has been
contacted, assigned, or represented as approving this package.

Recommended next task: **after explicit user approval of the exact draft and
target, submit the redacted recovery-invariant question for upstream triage**.
Request a supported source/release mapping, storage transaction contract,
maintainer-owned review path and observable acceptance boundaries. No custom
binary or implementation follows by implication. The proposed choices are in
[design options](ATOMIC_RECOVERY_DESIGN_OPTIONS.md); the invariant is that every
admitted, unacknowledged record stays durably reachable until replacement state
commits or delivery is independently confirmed committed.

If a supported candidate is identified later, request a separate scoped
qualification decision using [N1–N4 alignment](NATIVE_TEST_ALIGNMENT.md). If support
remains unavailable or is declined, return to an accountable ADR choice between
an explicitly approved maintained correction and enforceable production bounded
replay. Neither option is approved by this document. The existing
[ADR](../2026-10-26-adr/ADR-CHK-001.md) decision rule remains in force.

## Scope, validation and cleanup

Only this new evidence directory changes. Production Contrib **0.123.0** pin and
guards, product/runtime code, deployment files, checkpoint/replay tools and prior
evidence remain untouched. No collector execution, transition, fork/patch build,
runtime fixture, image publication, deployment, merge, waiver or DEV-05.2B occurred.
No Docker container/network/volume or synthetic credential was created; scoped
runtime cleanup is **NOT APPLICABLE**, and no Docker cleanup command ran.

[VALIDATION.json](VALIDATION.json) records link/path/hash/scope checks and retained
research failures. [ARTIFACT_SHA256.json](ARTIFACT_SHA256.json) binds new evidence,
excluding itself to avoid circular hashing. Full raw captures are internal review
evidence, **not** approved public attachments. Only the redacted draft is prepared
for a later submission decision. [Open decisions](OPEN_DECISIONS.md) and
[rollback constraints](ROLLBACK_AND_CHK002_IMPACT.md) remain blocking.

Validation reverified **728 prior artifact hashes**, **16 source Git blobs/SHA-256
identities**, and all authored local Markdown targets. The initial storage filename
lookup returned404; directory discovery resolved it. A first document check caught
an incorrect runbook link; it was corrected and the check passed. Both failed
attempts are retained. Authored Markdown/JSON whitespace passes; the global
whitespace check warns on five trailing-space lines preserved in verbatim upstream
captures. Those bytes are intentionally unchanged for source identity. The
[validation procedure](raw/review-validation.py.txt) records exact checks; it is
review evidence, not a collector fixture. No runtime PASS is inferred from these
document checks.
