# OC-ETL-007 — native authority and writer compatibility

2026-11-06 UTC. Branch `dev/post-pr78-architecture-closure-20261105`; existing **draft PR80**. Baseline `a061bdbabe7e250fe7141861c193ca837ef14dbe`. Implementation **`882e7b7cf354666ae5dfa3d7213efb193ff855b9`**; exact application/test source **`2b8eada577d0a56358d599c2f3a5e02d687b30a1`**. Additional commits refine the refusal matrix fixture, independent ID/replay reconciliation and shared-reader opt-in refusal. Only documentation differed during final execution; application and test files matched the tested commit. Initial opt-in over an enabled integration or shared collector is now refused both by the current API and the database guard exercised through the old API. Existing opted-in mixed batches still require a reviewed handoff. Final evidence HEAD and hosted CI conclusions are recorded in the PR80 closure comment after that commit completes.

**Outcome: PARTIAL/BLOCKED.** Provider-independent verification and older-writer fence enforcement are proven within the stated lab. Genuine native authority, positive qualified confirmation/receipt admission, active cutover and operational older-image rollback are **not** certified or called complete.

[Attestation specification](NATIVE_AUTHORITY_ATTESTATION.md) · [Receipt/cutover matrix](CUTOVER_AND_RECEIPT_MATRIX.md) · [Older-writer compatibility and recovery](OLDER_WRITER_COMPATIBILITY.md) · [Machine test matrix](TEST_MATRIX.json) · [Validation](VALIDATION.json) · [Source identity](SOURCE_SHA256.json) · [Unchanged applied migrations and Agent](UNCHANGED_MIGRATIONS_AGENT_SHA256.json).

## Workstream dispositions

| Workstream | Implemented and actually verified | Still incomplete |
|---|---|---|
| A — authority | Ed25519/domain-separated strict envelope, typed native/source/generation/reader/evidence/build/time references; server-owned issuer/target allowlist; test-only issuers cannot qualify; signature/time/tamper/alias/scope checks and current-generation validation | No genuine exact-build read-only target/qualified issuer is authorized or configured. Contract signature validity is not provider truth |
| B — confirmation/receipts | Conditional confirmation requires current genuine attestation; canonical qualified ownership index; immutable proof/revocation records; exact staged-version reuse rules; existing raw source/generation/key identities retained; receipt authority rechecked before commit and by deferred constraints | No qualified attestation or qualified receipt is seeded. Positive confirmation, canonical owner conflict under genuine proof, qualified admission/replay/expiry lifecycle are BLOCKED/NOT RUN |
| C — cutover | Existing lease/fence/generation/continuity/hold gates retained; staged replacement and failed transaction/restart regressions; conditional quiescent confirmed retirement end-dates qualification with binding | Active and stale-generation replacement refuse. Multi-source live interruption/cutover attribution is not proven and no bypass is added |
| D — older writers | New **0041_etl_authority_writer**, parent0040; protocol1 DB fence; all23 target-table refusal branches tested; old source APIs, restart, pool-marker reset, opt-in race, full backup/restore and refusal to remove fence with opted-in rows | Old handlers return500 on DB refusal and do not understand new readiness. They are fenced, not safe operational rollback images. Shared legacy batches involving opted-in sources can be wholly refused |
| E — readiness/UI | Six existing dimensions consume current authority only; unqualified test previews cannot persist or activate. Proof references/selection added to existing workspace. Actual browser checks keep BLOCKED/UNVERIFIED and reject self-confirmation | Aggregate Workflow activation and operational health remain blocked/unverified without independently qualified evidence; genuine positive UI path NOT RUN |

D01–D06 owner scope remains approved. This task authorizes the provider-independent D09 contract; it does not grant an exact external provider target, accountable verifier certification, security/DBA clearance or owner UAT acceptance. No named signatures are fabricated. Existing etl.view/etl.configure, fresh authorization/revocation locks and actor separation remain; no new permission catalog or provider workload-control capability.

## Actual final execution

| Check | Actual result | Evidence |
|---|---|---|
| Owned PostgreSQL17.11/API/browser/RBAC/ETL suite | **117 PASS, 0 failures/errors/skips**, exit0 at `2b8eada577d0a56358d599c2f3a5e02d687b30a1` | [regressions](final/regressions.log), [source/commands/cleanup](final/RESULTS.json) |
| Retained OC-ETL-002–006 cases | All104 retained, included above | Existing scope, DAG, native, preservation, incident, role and browser logs |
| New authority/writer cases | 13 included above; **50 new ordinary HTTP assertions**, 116 in new+retained lifecycle JSONs; other retained fixed HTTP artifacts are separate | final/test_*.json, TEST_MATRIX.json; counts overlap |
| Actual Chromium | **4 new contract/denial +28 retained groups PASS**, included in three Python browser cases | [authority browser](final/authority-browser-results.json), new screenshot; retained9 native binding/19 Workflow groups |
| Every fence table | **23/23** old SQL mutations refused with exact PG diagnostic, not incidental NOT NULL/FK errors | [table matrix](final/writer-table-fence-results.json) |
| Exact old source processes | a915322 pre-temporal and a061bdb OC-ETL-006: each old read/health200, unaffected legacy write201, three opted-in writes500 from DB fence, including restart | [versions/archive hashes/counts](final/older-writer-results.json), old-api logs. Current API refusal409 |
| Independently reconciled old writes | Accepted legacy stable IDs2, persisted distinct2, physical rows2, missing0/duplicates0. Opted-in old attempts6 refused; persisted0, no accepted IDs falsely missing | older-writer-results.json; raw request statuses and DB assertions |
| Raw quarantine/replay | DB layer: two attempts, one unique raw row, no physical duplicates/missing expected key, **zero qualified binding receipts**; failed old evidence/checkpoint batch rolls back | [raw reconciliation](final/raw-receipt-reconciliation.json). Not a positive qualified provider replay test |
| Migration/restore | New downgrade0040 refuses with any opted-in history even when new proof tables empty. All107 tables' row counts/hashes, columns and FKs equal actual restored DB; restored old SQL write still fenced | [writer restore](final/writer-restore-results.json), refusal log and synthetic backup |
| Existing migration/restart | Six inherited migration/recovery groups; terminated DB transaction rollback and current API SIGKILL after acknowledged commit/restart retained | final/rollback-results.json, binding-api-restart-results.json |
| Frontend | **46 PASS, 0 failures/skips**, lint/build exit0 | frontend-tests.log, frontend-lint.log, frontend-build.log |
| Full existing quality/pipeline | Exact make test-quality exit0. Pipeline14 transport tests +56 PostgreSQL tests and9 HTTP groups PASS (overlap) | quality.log, pipeline.log, pipeline-regression/ |
| Dependency addition | cryptography50.0.2 pinned; strict requirements audit found no known vulnerabilities at execution | dependency-install.log, dependency-audit.json/log; not image/security/legal clearance |

The quarantined/raw legacy `accepted` counter is not a count of verified binding projections. No old duplicate is reattached to a new version. Prior accepted evidence/identity hashes are preserved; unqualified evidence cannot produce qualified receipts or Workflow health. Genuinely positive cases remain separately BLOCKED in TEST_MATRIX.json, not hidden skips or PASS.

Source-version processes use exact archived app code with the **current installed test dependencies**, not a certified historical image/dependency set. Direct SQL probes exercise the actual DB guard (including superuser fixtures); real HTTP separately exercises existing authentication/RBAC. No scope/write hook or PostgreSQL transaction is mocked.

## Failed and intermediate attempts

| Directory | Observed result | Disposition |
|---|---|---|
| attempt1 | API startup failed: cryptography not installed | Added/pinned required verifier dependency; preserved log and scoped cleanup |
| attempt2 | 104 cases, one error | Trusted raw-receipt fixture had not declared current writer protocol; two trusted fixture setup transactions now mark current protocol. Original assertions remain |
| attempt3 | 112 cases, one failure/one error | Older generic500 text was parsed as JSON by a new helper; now explicitly tests plain500 and exact fence diagnostic. Retained browser ECONNRESET preserved; exact reset cause unconfirmed |
| attempt4 | 112 PASS | Intermediate subset, not final qualification |
| attempt5 | 114 cases, one failure (120 versus150) | Retained browser reloaded immediately after Save, before awaiting PATCH. Added actual200 response/duration150 assertions before reload; original reload expectation unchanged |
| attempt6 | 115 PASS | Expanded precommit subset |
| committed-attempt1 | 116 cases, one fixture error at46e5516 | Source/collector identity guard correctly rejected an inconsistent matrix fixture. Repaired source relationship; no guard relaxed |
| committed-attempt2 | 116 PASS at4baa83a | Complete refusal matrix |
| committed-attempt3 | 116 PASS at0c573cb | Accepted-ID reconciliation |
| shared-prequalification | 117 PASS | Shared-reader guard added; final old-API assertion qualified below |
| final | 117 PASS at `2b8eada577d0a56358d599c2f3a5e02d687b30a1` | Final shared-reader and old-API checks; only documentation differed from commit |

Early development runs are recorded with their original end-of-run SHA/diffs, not misrepresented as immutable feature qualification. Transient synthetic bearer headers in failed browser logs are redacted; no genuine credentials used. Private test keys stay in memory; the retained public key/envelope are explicitly CONTRACT_TEST_ONLY. The first local audit failed because its default cache was read-only; rerun with a task-owned /tmp cache passed. No failure became a skip or false PASS.

## Remaining gates and deployment disposition

No genuine provider positive attestation or qualified binding row exists in [the fixture inventory](final/native-authority-inventory.json). No external target has been probed. Authorize a specific read-only exact-build target and accountable verifier evidence/issuer governance before qualification. Test qualified confirmation, native alias owner conflict, receipt replay/expiry/revocation and active cutover using independent original receipts. Mathematical signatures and pre-existing RUNTIME_VERIFIED reader labels are not that evidence.

**Older full writer rollback remains BLOCKED.** Data safety is enforced by refusal, not old-code compatibility. An old health200 cannot authorize automated rollback; shared mixed-version source batches are deliberately refused. Qualify an authority-aware rollback image or explicit safe read-only/degraded mode with version/capacity/security/DB-role prerequisites and genuine receipt accounting. The DB protocol assumes trusted current app/DB roles; it does not defend against privileged SQL disabling triggers or maliciously asserting protocol1. External trust-file changes are not a distributed atomic DB transaction; drain/revoke procedure remains mandatory.

**Immutable non-production candidate preparation/separate deployment: BLOCKED / NOT PERFORMED.** Fully qualified rollback, adequate isolated Docker build capacity, approved candidate identities and required security/DB grants are not demonstrated. The managed writable layer becomes full while its PostgreSQL clone exists; it recovers on exact scoped removal. No unrelated cleanup, host reconfiguration, live UAT access or unsafe deployment is used to work around prerequisites.

Declared new component licenses are recorded in DEPENDENCY_METADATA.json: cryptography Apache-2.0 OR BSD-3-Clause, cffi MIT-0, pycparser BSD-3-Clause. This is metadata, not accountable license/NOTICE/source-offer clearance; vendored/image obligations and independent security certification remain pending. No unrelated pip/CVE/license remediation or waiver.

All task PostgreSQL containers/tmpfs, current/old/restart APIs and Vite processes stop; private browser/trust/code-extraction directories are removed. Backup exports are synthetic only. Original OC-ETL-002–006 evidence and applied migrations0040 and earlier are unchanged. D07/D08, independent UAT, all31 included journeys/30 missing numbered definitions and nine earlier bounded approvals remain unchanged; Journey20 excluded, Journey32 skipped. No merge, production/owner UAT deployment, collector pin change, scheduler or provider workload action.

**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**

## Reproduction command

```sh
ETL_WORKFLOW_UI_ACCEPTANCE=1 PLAYWRIGHT_MODULE=/tmp/oc-closure-tools/node_modules/playwright/index.mjs PLAYWRIGHT_BROWSERS_PATH=/tmp/oc-etl003a-browsers ETL_SCOPE_EVIDENCE_DIR=/tmp/etl007-qualified backend/.venv/bin/python scripts/etl-scope-acceptance.py
```

Requires the documented test virtual environment, Chromium, local Docker and PostgreSQL image. The harness creates its own synthetic trust fixture and disposable database. No provider credentials are required or supplied.

## Hosted checkout correction

First evidence HEAD `dbdc7b32c4857e8d39e34aece4469e5ee30545a6` failed pipeline-contracts run42268856494:117 cases,115 passed and2 errors, no skips. Both errors occurred at `git archive` because actions/checkout's default shallow history omitted pinned a915322/a061bdb sources. [Raw regression log](hosted-attempt1/regressions.log), [workflow failure](hosted-attempt1/workflow-failure.log), [cleanup and exact commands](hosted-attempt1/RESULTS.json).

Only pipeline-v16 checkout now requests complete history and verifies both exact historical `backend/app/main.py` objects before tests. No assertion, product behavior or safety guard changed. Local YAML parse and both `git cat-file -e` checks pass. Full final-HEAD hosted results are recorded in the PR closure comment after completion.
