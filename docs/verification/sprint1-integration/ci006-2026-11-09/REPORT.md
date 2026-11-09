# OC-S1-CI-006 — recovery gate correction

2026-11-09 UTC / Asia/Calcutta. Draft PR89; branch integration/sprint1-pr80-81-82-83-84-86. Baseline41cfb3773824242db7fda4f1e9a082d088631c08; main2e4fe5d8cb0f39170b0d789fdd7e07be4ac0219a unchanged. Candidate/tested source d23bb413ff6c7618e0e5ff36b7e7c12d296461fc. Final evidence-only commit/CI trigger recorded in PR handoff.

**Disposition: bounded test-harness correction locally verified; exact original exception NOT REPRODUCED locally; final hosted result PENDING. Sprint1 NOT COMPLETE.** No product UI, backend API/model/migration, auth/RBAC, TLS/network policy, collector version, quality threshold or ruleset behavior changed.

## Inspect before edit: exact failure and provenance

Requested artifact13666480538 (recovery.zip), run42601175165/job129105733189, reports **no failed assertion**. It exits on an unhandled `route.fulfill: Route is already handled!` at `frontend/scripts/resource_crud_acceptance.mjs:308:19`, while a genuine configuration-context response is delayed. The prior route-drain correction was insufficient; do not describe this as a failed persistence, keyboard or native-validation assertion.

A second independent hosted occurrence at the same PR head is retained: dispatch42598486316, artifact13664587389 (dispatch-recovery.zip), same exception/location. Both archive hashes match GitHub API metadata (DOWNLOAD_SHA256.json). PR artifact cleanup identifies actual checkout9c5b2f993f2a2635c8d46fd20cdd6e6a0cf74216, the synthetic merge of41cfb377 into main; dispatch source is41cfb377 itself. merge-source.json preserves the actual parent proof. Do not relabel those source identities as this fix.

Before editing, ran the unchanged41cfb377 complete real PostgreSQL/API/browser recovery: exit0, all13 top-level groups passed (baseline-recovery/). A separate40-iteration real-browser/native-HTTP old-route probe with overlapping cross-origin requests/abort also produced0 exceptions (route-repro.mjs/json). Thus the exact local reproduction remains **NOT REPRODUCED**; these passes do not invalidate the2 hosted failures or prove the route mechanism safe. We have not established the internal upstream double-handling race or claimed to patch Playwright.

## Correction and preserved contracts

The confirmed failing component is acceptance instrumentation attempting late fulfillment of a route already handled. The keyboard pending-revision test needs delayed delivery of an authentic response, not a second HTTP request plus CDP fulfillment. `browser_response_gate.mjs` now wraps only the owned test page's native fetch return:

- The original fetch receives identical arguments and performs the real browser request, credentials, CORS and TLS checks. Only matching GET responses wait after native fetch returns. The original Response object/status/headers/body are returned unchanged; no fabricated response, request replay or network-security relaxation.
- Release restores native fetch, resolves all pending deliveries and waits for a zero pending count. It uses no Playwright Route, late fulfill, ignoreErrors, exception suppression or arbitrary delay/timeout increase.
- Existing keyboard assertions remain: blocked Enter yields0 mutation requests and preserves unsaved edits/focus; after genuine revision delivery, button Enter and text-input Enter commit exactly once each, include expected revisions/child maps, advance revisions and survive persisted reload.
- Other inventory-ordering/browser assertions and all backend negative security tests remain intact. No source-context ownership/write guard changed. The held-context case is now explicitly synchronized to receipt of a genuine response before release.

Added3 real Chromium/native HTTP cases, invoked by the existing disposable recovery browser runner:2 simultaneous cross-origin responses stay held while an unrelated POST and request headers remain native;10 repeated gate/release cycles preserve403 responses, restore fetch and make repeated release idempotent; native CORS denial and transport failure remain rejected. Fixtures use only owned ephemeral loopback HTTP ports; they do not certify providers or replace the actual FastAPI/PostgreSQL/TLS recovery tests.

The first draft failed1 of3 helper cases because gate reinstallation checked the release flag at the wrong nesting level. That failure is retained (gate-tests-attempt1.log/exit), corrected before candidate commit; all3 now pass. This was a new harness-draft defect, not the original hosted exception.

## Actual verification and counts

Environment: Python3.12.14, Node24.19.0, Playwright1.56.1/Chromium141, PostgreSQL17.11, Docker28.4.0/vfs. Hosted failure used Node24.22.2; no unsupported causal claim about that difference. Task-owned databases/ports/processes only. Full Docker image rebuilds/scans are not claimed locally: backing storage reached100% while owned fixtures ran. No broad prune, daemon restart or shared UAT access.

| Command / runner | Actual result | Evidence |
|---|---|---|
|`node --test frontend/scripts/browser_response_gate.test.mjs` with recorded Playwright env|3 PASS,0 FAIL,0 SKIP;3 distinct cases including10 cleanup cycles|gate-tests.log/exit; also executed inside both full recovery attempts|
|`RELEASE_BROWSER_ACCEPTANCE=1 RELEASE_EVIDENCE_DIR=<owned> PLAYWRIGHT_MODULE=/tmp/oc-closure-tools/node_modules/playwright/index.mjs PLAYWRIGHT_CHROMIUM_EXECUTABLE=/tmp/oc-etl003a-browsers/chromium-1194/chrome-linux/chrome backend/.venv/bin/python scripts/release-acceptance.py`|2 candidate runs, each exit0 and13 top-level groups PASS. Includes205-resource pagination, resource CRUD8 nested groups, authenticated tenant/RBAC/remote worker/lease/replay/alert recovery negatives, backup/restore/retention/TLS|fixed-recovery-1/ and fixed-recovery-2/ report.json, commands.log, cleanup.json|
|Keyboard revision contract in both runs|0 premature writes;2 committed commands; focus, button Enter, native text-input Enter, revision advancement, reload and response-gate drain PASS|both keyboard-regression.json; resource-keyboard-desktop.png|
|`ARCH001_API_ACCEPTANCE=1 ARCH001_ENGINE_ACCEPTANCE=1 ARCH001_BROWSER_ACCEPTANCE=1 ARCH001_EVIDENCE_DIR=<owned> ... backend/.venv/bin/python scripts/arch001-acceptance.py`|exit0; native hostname/DNS validation negatives with independently unchanged DB PASS;5 Access browser checks PASS; actual migrated PG/FastAPI/production React/Playwright|arch-browser/identity-validation.json, access-v15-browser.json, report.json, cleanup.json|
|`backend/.venv/bin/python -m unittest discover -s tests -v` from root|112 PASS,0 FAIL,0 SKIP|unit.log/exit|
|`npm test --prefix frontend`; lint; build|55 PASS,0 FAIL,0 SKIP; lint/build exit0, existing bundle-size warning retained|frontend-*.log/exit|
|`python -m unittest tests.test_ci_e2e_alignment -v`|8 PASS,0 FAIL,0 SKIP; subset of112, not additional unique cases|alignment-tests.log/exit|
|`python scripts/ci/e2e_alignment.py --prepare-history`|register integrity PASS,7 rows,0 whole paths certified; existing6 PARTIAL/1 BLOCKED dispositions unchanged|alignment.json|
|`python scripts/ci/policy.py`; `bash scripts/check-workflows.sh`|817 records,786 UNKNOWN still RUN; all814 prior rows unchanged; all28 workflow definitions validate;13 required identities retained|policy.json, SCOPE_REVIEW.json, actionlint.log/exit|

Counts are nested/subset executions, not summed unique requirement coverage. No skipped required case is converted to PASS. Real fixtures remain controlled development evidence, not formal UAT/genuine provider or durability certification.

## Verification check and security disposition

Confirmed **verification SUCCESS** at the requested41cfb377 head: PR run42601175092/job129105732820; windows-source-checks also SUCCESS. Raw job log and VERIFICATION_RESULT.json retained. Its configured combined coverage measurement was82.34%, not whole-product coverage; no quality threshold changed. Dispatch42598505623 is also successful. No new verification regression was observed in that evidence. This historical success is not a result for the new final SHA.

At the requested head,16 of18 PR-safe workflows succeeded; recovery and image security failed (runs.json). All7 image-role jobs and security-sbom remain FAILED in image-jobs.json. Their actual existing raw SBOM/Grype/licence evidence is preserved under previous packages; no image substitution, scanner exclusion, severity change, waiver or fabricated legal/NOTICE signoff. Local image work is blocked by capacity, and final hosted image scans remain subject to the same enforcing gates.

Final combined commit will be pushed only to PR89 and all18 PR-safe workflows explicitly triggered. Mandatory **Trigger-and-Exit**: record accepted triggers/available links, report **CI TRIGGERED — RESULT PENDING**, and stop without monitoring completion. No manual publisher, deployment, formal UAT or live provider workflow is authorized.

Independent engineering review remains PENDING. Preserve the owner-accepted54f26e5 visual baseline without inferring acceptance of later interactions,9 pending owner selections, UAT or release. Task-owned containers/processes/private secrets removed by harness cleanup (all3 recovery cleanup.json plus arch-browser/cleanup.json); no unrelated resources removed. No merge, deployment, collector upgrade, Sprint2 or gate promotion.

**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO · Sprint1 NOT COMPLETE.**
