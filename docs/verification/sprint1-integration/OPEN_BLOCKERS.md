# Remaining acceptance blockers

> Latest2026-11-09: [OC-S1-CI-003 results](ci003-2026-11-09/REPORT.md) and [current blockers](ci003-2026-11-09/REMAINING_BLOCKERS.md). Earlier dated results below remain historical; current coordinated-child and catalogue-CAS evidence supersedes those earlier implementation gaps.

> Historical snapshot at PR head4081fc7. The [current closure follow-up](closure-followup-2026-11-08/REPORT.md) and [remaining blockers](closure-followup-2026-11-08/REMAINING_BLOCKERS.md) supersede the single-source writer, history-UX and documented fault-test status below; earlier evidence remains preserved.

Sprint1 **NOT COMPLETE**; no owner visual acceptance or independent PR approval has been supplied for this integration.

| ID | Priority / type | Exact gap and dependency | Required closure evidence |
|---|---|---|---|
| S01-C01 | P0 implementation / compatibility | Complete atomic resource-context/OS/configuration update adapters and old/new client cutover. Current revisioned context edits fail closed; no implicit reparenting. | Real HTTP/browser resource edit after attachment; source expected-revision races; invalid OS change; unchanged history on refusal; mixed-version writer tests. |
| S01-C02 | P1 implementation / provider dependency | Host-method and explicit HTTPS settings applicability implemented. ETL provider-specific template mappings remain UNVERIFIED, not inferred from names. | Exact existing provider validator/schema mapping, negative incompatibility and controlled integration. Genuine qualification separately authorized. |
| S01-C03 | P1 frontend completion | Full history pagination/detail/diff, explicit detach review and staged-draft application UX remain incomplete. Current API supports history/revision/diff/new-revision rollback; UI shows first page and rollback. | Authenticated multi-page history/revision comparisons, detach/reattach and rollback negative browser cases. No secret/checkpoint restoration. |
| S01-C04 | P1 concurrency | Template publication retains immutable versions and serialization but no mandatory catalogue expected-version contract across all clients. | Approved catalogue/source authority boundary, stale publication conflicts and client adapters. Source CAS is not catalogue CAS. |
| S01-C05 | P0 verification | Controlled source command UPDATE failure and API concurrency are verified. Exact command concurrent permission revocation, process termination around COMMIT and application/collector provenance cutover remain incompletely exercised. | Persisted command/revision/projection reconciliation through each cut, actor/revocation locks, repeated retries and legacy-writer rejection without mutation. |
| S01-V01 | Owner acceptance | Single-panel navigation and desktop screenshots are a candidate, not visual approval. Screenshot reference is not a fully implemented later-sprint monitoring dashboard. | Owner compares admin/operator1920x1080,1440x900,1366x768 captures; reviews typography, density, navigation and deviations. |
| CI-01 | P0 hosted evidence | Final-HEAD TierA/B/C and legacy required results must be observed by owner under Trigger-and-Exit. Historical runs are not final passes. | Exact SHA/run/check identities, logs/artifacts and actual conclusions. |
| CI-02 | P0 external permissions | Ruleset26082467 PUT refused403 despite repository-admin flag. Original13 checks remain, no additions/removals. | Administration-write permission for the authorized integration; re-read drift and check identities; additive transition without removing unverified equivalents. |
| SEC-01 | P0 security | All seven historical image scans have unresolved policy findings; accountable component licence/NOTICE/source-offer review absent. No waivers. | Fresh immutable final-candidate scans/SBOMs, actual remediation/approved fixed candidates and accountable legal/security review. |
| ENV-01 | Environment | Docker backing filesystem intermittently0–350MiB free. No broad cleanup or unrelated data removal is authorized. | Adequate isolated build storage or hosted fresh runners; exact-image generation and scan evidence. |
| REL-01 | Independent durability | CHK-001 FAIL; CHK-002 BLOCKED. No collector/spool/checkpoint implementation or version change here. | Existing independent durability/recovery plan and separately authorized qualification; not closed by these configuration tests. |

Formal UAT, genuine Windows/Linux/EC2/Pentaho certification, D07/D08 decisions and nine owner-acceptance selections remain **PENDING/BLOCKED** where previously recorded. Historical controlled-scope approvals are preserved. They are not new signatures for this work. Sprint2 is not started.

No CI retirement or release promotion. SECURITY BLOCKED · RELEASE NO-GO.

## 2026-11-09 exact-head recovery follow-up

[Access/keyboard corrections and evidence](required-recovery-2026-11-09/REPORT.md) are locally verified within their recorded boundaries. The full local Access Docker build remains BLOCKED by owned-daemon backing-store capacity; final hosted checks are pending. All seven [image-security/licence failures](required-recovery-2026-11-09/IMAGE_FAILURE_REVIEW.md) remain unresolved. No branch-protection, release, provider, owner visual or independent-review gate is cleared.

## CI005 / issue95 handoff

Locally reproduced ARCH native validation mismatch and missing scope records are corrected with real-component evidence; final hosted results remain pending. [CI005](ci005-2026-11-09/REPORT.md) retains the same-SHA intermittent route failure and its drain regression. The [E2E matrix](E2E_WORKFLOW_MATRIX.md) keeps6 PARTIAL/1 BLOCKED whole paths, genuine provider/D07/D08/history aggregation/older-writer/external notification gaps. All7 image roles, legal/NOTICE and independent security/reliability gates remain blocked. No implication of owner acceptance for later interactions.
