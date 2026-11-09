# Three-way merge decisions

Base main: `2e4fe5d8cb0f39170b0d789fdd7e07be4ac0219a`. Source tips are pinned in INTEGRATION_LEDGER.md. All six source tips are ancestors of the local integration candidate; no source branch or main was modified. No blanket ours/theirs resolution was used.

| Merge | Actual textual conflicts and resolution |
|---|---|
| #83 → `1b24df3` | `scripts/v16-acceptance.py`: identical cleanup logic, differing formatting. Keep main's formatting and all scoped cleanup/redaction. Policy, AUTH-694 and program imported. |
| #81 → `99aea37` | No textual conflicts. Preserve reconciliation evidence as historical baseline, not new verification. |
| #80 → `077e627` | `pipeline-v16.yml`: combine pinned actions, credential non-persistence and full history/pinned older-writer availability checks. `check-workflows.sh`: retain validation of **all** workflows, rather than old subset. Review clean merges: explicit safe0023 rollback, CI roadmap validator, ETL frontend test scripts and protected populated-downgrade full-dump comparison. |
| #82 → `e5f6cee` | `package.json`: union template, settings and ETL tests; retain main's patched dependency versions. `v16-acceptance.py`: keep populated-refusal/error/schema/content comparison, add restore probe and retain formatted cleanup. |
| #84 → `5bc997e` | `sprint1_restore_probe.py`: secure temporary synthetic backup disposal after verified restore. Template component: retain saved-effective preview. Unified Resource Management: combine ETL imports with catalogue/filter imports. Test script lists unioned. Harness retains performance/load and UI probes. Historical CI004 metadata collisions preserved byte-for-byte under source-evidence/main-ci and pr84-browser. |
| #86 → `100cb1f` | TopNav uses current FeatureDirectory instead of obsolete inline sections; both exclude incident UI. Browser scripts retain direct-route exclusion **and** background incident pagination/IDOR/end-bound assertions. Platform-admin exclusion and pipeline contract assertions retained. Historical logs/screenshots/metadata collisions stored under source-evidence/integrated-pr84 and pr86-scope, retaining main/root history. |

Historical manifest relative paths belong to their original source trees; consult the immutable source commit to reconstruct each complete evidence package. Relocation is not a rerun or a new PASS. Source-evidence copies preserve conflicting blobs; they are not competing current reports.

## Semantic follow-up

- Merged #80's added Node action initially escaped textual conflicts with an unpinned tag; re-pin to the already approved CI action-lock SHA. Preserve older-writer tests.
- Added resource-workspace workflow must follow main's immutable action pins, non-persistent checkout credentials and all-PR trigger policy. Keep its check identity, make artifact absence fail.
- Configuration writers now use source revision/idempotency contracts. Tests must submit explicit revisions instead of treating optional timestamps as sufficient. Negative security assertions remain.
- Reviewer: automated implementation review only. Independent engineering approval and owner visual acceptance remain **PENDING**.

CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.
