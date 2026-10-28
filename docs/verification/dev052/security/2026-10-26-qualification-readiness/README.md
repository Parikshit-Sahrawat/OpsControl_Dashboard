# DEV-05.2A.3H — qualification readiness, 2026-10-26 UTC

**Documentation/evidence only. Candidate BLOCKED; N1–N4 NOT RUN.**
**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**

Verified task-start HEAD, local branch and remote branch/PR head:
`1ebea8869205b770348e5ce543dc901efd9e09f5` on `release/dev-05-2-hardening`.
The worktree was clean. PR69 was open/draft; no unrelated work was overwritten.
The completion commit is the Git commit containing this new directory; internal
tracking records that exact SHA after push. Original product baseline remains
`f617cc653a965c2ad1bb7edf9e20237e40044b97`, not a new tested H product revision.

## Findings and package

[Upstream issue16236](https://github.com/open-telemetry/opentelemetry-collector/issues/16236)
exists, created by `Parikshit-Sahrawat` at `2026-10-26T12:48:16Z`. Captured status:
open, zero comments, no assignees, no milestone. No maintainer response or supported
correction is established. Its references from our issue and third-party automated
digests are not maintainer acceptance. The body retains the old draft's phrase
"not submitted"; the API confirms publication. We neither edited the upstream
issue nor rewrote G's accurate historical unpublished-draft record.

New source observation: core v0.164.0 at
`f532e15ef29b6ed7fefad2b23a0fefd27120ef9b` and current main
`30add0562534958c3b4173fa307b5a3497d0bc9c` retain byte-identical persistent queue
source to G's v0.163.0: SHA-256
`a98bd9990c2405d0b24cdee951ccacec01b58b4dc347ceb6b7c256ceea789d98`.
Contrib source latest is also v0.164.0; official distribution latest still returns
v0.163.2. The specific distribution v0.164.0 release lookup returned404 and is
retained. Neither a newer source release nor a release-note binary link establishes
an available verified corrected binary. No binary/image was acquired or executed.

| Deliverable | Purpose |
|---|---|
| [UPSTREAM_RESPONSE_REGISTER.md](UPSTREAM_RESPONSE_REGISTER.md) | Timestamped statements, links, source changes and support classifications |
| [N1_N4_QUALIFICATION_READINESS.md](N1_N4_QUALIFICATION_READINESS.md) | Setup, provenance, receipt oracle and exact execution blockers; no tests run |
| [RECOVERY_INVARIANT_FAILURE_MATRIX.md](RECOVERY_INVARIANT_FAILURE_MATRIX.md) | Invariant, failure cuts, safety/delivery distinctions |
| [ROLLBACK_CHK002_DECISION_MATRIX.md](ROLLBACK_CHK002_DECISION_MATRIX.md) | Separate queue, filelog and safe recovery decisions |
| [OPEN_DECISIONS.md](OPEN_DECISIONS.md) | Accountable roles and conditional next decisions, no invented approvals |
| [EVIDENCE_REFERENCES.json](EVIDENCE_REFERENCES.json) | Prior immutable commit/file hashes and source evidence bindings |
| [ARTIFACT_SHA256.json](ARTIFACT_SHA256.json) | Every new artifact except the manifest itself |
| [VALIDATION.json](VALIDATION.json) | Independent checks, commands, results and limitations |

Supporting files: [FETCH_LOG.json](FETCH_LOG.json), [READINESS_STATUS.json](READINESS_STATUS.json),
[SOURCE_IDENTITIES.json](SOURCE_IDENTITIES.json), raw GitHub GET responses and
verbatim source captures. No new receipt exports exist because no runtime ran.
Expected/persisted/missing/attempt/duplicate counts for new tests are **null**.

## Historical results remain historical

The original staggered reference has **267 expected / 257 distinct persisted /
10 missing / 257 accepted record attempts / 257 physical rows / zero duplicates**.
Experimental newer recovery of populated legacy state after a partial replacement
has **267 / 258 / 9**, 258 accepted attempts/rows, zero duplicates. Neither was
rerun here. The newer result is not a steady-state qmv0 runtime test. D's selected
4 PASS/13 FAIL, 91 regression PASS, three finite replay recoveries, retention expiry,
corruption and permanent-rejection failures remain preserved observations, not H
results or production recovery certification.

## Validation, scope and cleanup

Validation checks prior hashes against both worktree bytes and exact Git commits,
new source Git blob/SHA identities, local Markdown links, JSON structure, manifest
coverage, response counts, cross-document gate consistency and changed-path scope.
Only documentation validation can PASS in H; qualification readiness is BLOCKED
and runtime execution is NOT RUN. Commands and the independent checking procedure
are retained in [VALIDATION.json](VALIDATION.json).

Only this directory changes. Production Contrib0.123.0 pin/guards, product code,
checkpoint/replay tools, deployment files and E/F/G plus earlier evidence remain
unchanged. No tests, collectors, migrations, synthetic runtime experiments, custom
builds, production changes, upstream writes/contact, image publication, merge,
branch deletion, waiver or DEV-05.2B. No Docker resource or synthetic credential
was created; cleanup is NOT APPLICABLE and no Docker cleanup command ran.
PR69 remains draft. Upstream tracking is a dated snapshot, not continuous monitoring.
