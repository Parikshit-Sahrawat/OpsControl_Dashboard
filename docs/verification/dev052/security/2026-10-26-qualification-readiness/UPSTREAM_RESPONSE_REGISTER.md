# Upstream response register — 2026-10-26 UTC

**Unresolved question / awaiting authoritative guidance. Candidate BLOCKED.**
The collection window and per-request times are preserved in
[FETCH_LOG.json](FETCH_LOG.json). Read-only snapshots are not a subscription or a
promise that comments will remain unchanged. No upstream message was sent in H.

Exact proposed G durability invariant, retained without relaxation:

> Every admitted, unacknowledged item remains durably reachable until a replacement is committed or delivery is independently confirmed committed.

## Issue and response classification

| Source and time | Observed statement/event | Classification and implication |
|---|---|---|
| [Issue16236](https://github.com/open-telemetry/opentelemetry-collector/issues/16236), created/updated `2026-10-26T12:48:16Z` | Reporter `Parikshit-Sahrawat`; open; 0 comments; no assignees, labels or milestone in capture | **UNRESOLVED QUESTION**, not acceptance. The reporter's historical observations and proposed invariant are not maintainer findings |
| [Comments API](raw/upstream-comments.json), observation recorded in FETCH_LOG | Empty array; issue reports comments=0 | No maintainer statement received; no support, refusal, ownership or ETA inferred from silence |
| [Timeline](raw/upstream-timeline.json), `2026-10-26T12:48:30Z` | Reporter cross-reference from internal Issue68 | Tracking only, not upstream investigation or acceptance |
| Same timeline, `2026-10-26T12:54:25Z` | `github-actions[bot]` daily digest reference from `o11y-dev/opentelemetry-skill#105` | Third-party automated reference, no authoritative support claim |
| Same timeline, `2026-10-26T14:23:52Z` | Same bot weekly digest reference from `o11y-dev/opentelemetry-skill#107` | Third-party automated reference, not a maintainer response |

Raw issue: [upstream-issue16236.json](raw/upstream-issue16236.json). All three
timeline events are cross-references; no linked implementation PR or release
resolution is established by that timeline. The issue body links the PRs below
as context. Its retained "not submitted" sentence conflicts with actual issue
existence; treat it as stale draft text. H does not correct or comment on it
without separate authorization. G's evidence remains immutable and historically
accurate for its observation time.

## Linked proposals and maintained-source observations

| Reference | Identity/time/status captured | Classification and OpsControl implication |
|---|---|---|
| [PR13330](https://github.com/open-telemetry/opentelemetry-collector/pull/13330) | Merged; merge `e2954b98139a839d31cd7ae4d826966f33a9180f`; updated `2025-07-06T12:02:43Z` | Authoritative merged metadata/capacity change, **not a supported correction for this invariant**. Does not atomically retire old payloads with replacements |
| [PR15993](https://github.com/open-telemetry/opentelemetry-collector/pull/15993) | Open draft/unmerged, head `b930d34a4f7f3f7acb0cf79c02e0372d09e06a88`; updated `2026-10-19T15:57:15Z` | **UNMERGED PROPOSAL / POC**. Not qualified or released; no approved custom build |
| [POC author comment](https://github.com/open-telemetry/opentelemetry-collector/pull/15993#issuecomment-6041392483) | `agoallikmaa`, `2026-10-07T15:43:53Z`: describes completion-frontier persistence and possible out-of-order duplicates | Author design/test claim, not independent evidence or commitment from a maintainer to issue16236 |
| [POC review request](https://github.com/open-telemetry/opentelemetry-collector/pull/15993#issuecomment-6127585713) | Author asks reviewers about leaving draft, `2026-10-12T15:42:06Z` | Review pending; not support acceptance. Recorded reviews are comments, not qualification results |
| [PR16230](https://github.com/open-telemetry/opentelemetry-collector/pull/16230) | Open/unmerged, head `6569043bc424937f7f85d52a185f9f32c86bfb3c`; updated `2026-10-25T14:40:29Z`; no submitted reviews captured | **UNMERGED PROPOSAL** for metadata-read startup failure. Does not replace delete-before-reenqueue recovery |
| [Core v0.164.0 release](raw/core-latest.json) | Published `2026-10-26T14:54:44Z`; tag resolves to `f532e15ef29b6ed7fefad2b23a0fefd27120ef9b` | New source release since G. Notes do not identify this correction; [queue bytes](source/queue164.txt) retain the same destructive sequence |
| [Core main](raw/core-main.json) | `30add0562534958c3b4173fa307b5a3497d0bc9c` | New inspected head; [queue](source/queue-main.txt) unchanged from G, not a candidate |
| [Contrib source latest](raw/contrib-latest.json) | v0.164.0, commit `18fcec7bd1f5b4702a40a1861e0b5eb95f9a3152`, published `2026-10-26T18:21:43Z` | Source-release metadata and tag resolution only; not an available verified corrected binary |
| [Official distribution latest](raw/dist-latest.json) | v0.163.2, published `2026-10-21T16:22:34Z` | G's immutable distribution mapping remains the reference: `6c65793ec707f673304e52dfcb642684fda1a048`, components0.163.0 |
| [Distribution v0.164.0 lookup](raw/dist164-release.json) | HTTP404; timestamp/error in FETCH_LOG and stderr | **BLOCKED availability evidence** for that release endpoint. Core notes link it, but that link is not verified publication; do not infer absence from every registry/channel |

PR body/comments/reviews are retained as `raw/pr*.json`; upstream test claims were
not run or promoted. There is no newly evidenced maintainer investigation of the
exact issue, supported corrective commit, support window, or candidate digest.
The public codeowner list still records exporterhelper owners `bogdandrutu`,
`dmitryax` and Collector approvers: [captured ownership](source/core-owners.txt).
Ownership identifies potential reviewers, not assignment or signoff.

Both new core queue captures have SHA-256
`a98bd9990c2405d0b24cdee951ccacec01b58b4dc347ceb6b7c256ceea789d98`, equal to
G's immutable captures at core release `5177a6a85ca3783068077e25aec6cebbe1d50d1f`
and main `82148555675e5a0a201189cd4220395eb8baa1ad`. Recovery still performs old
payload read, separate deletion Batch, then individual replacement commits.
The reused bbolt implementation commits each Batch separately; the generic Batch
API does not promise universal atomicity. qmv0 and legacy both call this path by
source inspection, not a new H runtime proof. Exact bindings are in
[SOURCE_IDENTITIES.json](SOURCE_IDENTITIES.json) and
[EVIDENCE_REFERENCES.json](EVIDENCE_REFERENCES.json).

## Tracking rule

On a later authorized refresh, record each response's author, timestamp, source
URL, exact claim, role evidence, linked commit/release, limitations and whether it
is investigation, unresolved question, unmerged proposal or supported correction.
Do not upgrade a classification because an issue closes, a version increases,
a reviewer comments or someone intends to merge. A supported candidate still
needs independently verified artifact/component bindings and scoped qualification
authorization. No inferred acceptance from silence or the issue's existence.

Current outcome: **candidate/readiness BLOCKED; N1–N4 NOT RUN**. Preserve
**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**
