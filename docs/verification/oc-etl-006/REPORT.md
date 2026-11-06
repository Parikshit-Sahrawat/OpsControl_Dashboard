# OC-ETL-006 — native binding and readiness implementation

Date: 2026-11-06 UTC. Branch `dev/post-pr78-architecture-closure-20261105`, existing **draft PR80**. Baseline `a915322b5c5c80b0d37dea71f6b7f70237082340`. Initial implementation `b94f7ed45209d7bd856193ee4da45da64097b241`; test corrections `8258ef387bb13563acbe835e684923542833afd6`, `aa466c4` / `3355dbd`; final ownership guard and **exact clean tested source `8e7cdf91d70f19a19c1cdf8d763818446b1c179f`**. The final evidence commit changes documentation/traceability/artifacts only; its exact SHA and hosted conclusions are recorded in the PR80 closure comment.

**Outcome: implemented and verified bounded subset; full OC-ETL-006 Definition of Done INCOMPLETE / BLOCKED.** No product-owner authorization is missing for D01–D06. The remaining native authority evidence, qualified/live positive paths, rollback compatibility and independent certification are not replaced by that approval.

[Approval/source/scope](APPROVAL_AND_SCOPE.md) · [Migration/recovery](MIGRATION_AND_RECOVERY.md) · [Readiness transitions](READINESS_TRANSITIONS.md) · [Test matrix](TEST_MATRIX.json) · [Validation](VALIDATION.json) · [Environment](ENVIRONMENT.json) · [Source hashes](SOURCE_SHA256.json) · [Unchanged safeguards](UNCHANGED_SAFEGUARDS_SHA256.json).

## Implemented behavior

| Area | Actual implementation | Limits |
|---|---|---|
| D01/D02 identity and cardinality | `app/etl_bindings/models.py`: scoped immutable versions retain Workflow, JobOrder, Resource and PipelineJob identities; canonical native **claim** tuple includes platform/environment/namespace/native ID; partial uniqueness for one current Job version and one current claim owner, including SQL tuple index independent of its hash | The new namespace is an operator claim. Verified cross-method/provider alias equivalence is not inferred. D09-qualified ownership remains BLOCKED |
| D06 temporal provenance | New `0040_etl_native_bindings` (parent `0039_etl_workflow_foundation`); RESTRICT scoped FKs, validity intervals, immutable snapshots, causal operations, retired terminal versions, append-only receipt links, deferred atomic-successor trigger, parent identity guards | No uncertain backfill; old association rows may still be physically removed, but an opted-in version's tuple/method hashes remain. No new accepted receipts were falsely linked to an unverified version |
| D04 security | Current `etl.view`/`etl.configure`, existing fresh transaction authority/session/revocation lock, per-Job row/per-claim locks and five-second timeout, independent reviewer check, atomic version/domain audit/operation result; bounded deterministic conflicts | No new permission catalog or provider execution privilege. Independent accountable security/DBA signatures pending |
| D03/D05 readiness | Six backend dimensions, schema version1, evaluated_at and `ETL_SOURCE_RECEIPT_V1`; contextual max(120, interval×3), strictest selected method, both source/receipt ages and future-clock uncertainty | Missing, legacy and quarantined evidence cannot become qualified receipt/HEALTHY. Aggregate activation remains BLOCKED and operational health UNVERIFIED; positive native qualification/Workflow ACTIVE not implemented |
| Configuration lifecycle | Secured STAGE, same-identity staged REPLACE, RETIRE and confirmation prerequisite denials; snapshots include method revision, connection version/checksum, capability/proof IDs, source generation/fence and reader hash | Refuses active integration/selected native Job/enabled legacy collector, active lease or retention/continuity hold. No active-reader cutover or checkpoint manipulation. Different native identity/reparenting refuses |
| UI | Existing Resource Management workspace: candidate/method selection, authority claim, history, replacement/retirement, errors, read-only controls, six backend dimensions, save/reload, failed-save input retention, tenant cancellation and post-save refresh generation guard | Candidates must already explicitly reference this Job's canonical Resource. No auto-binding/discovery or workload Run/Retry/Stop/Terminate controls |
| Compatibility | Existing Jobs and unassigned legacy routes unchanged unless explicitly opted into the registry. Opted-in unconfirmed/stale versions refuse integration/resource readiness and V1.6 event routing/quiet-completeness projections | Running older writers is unsafe because they do not implement the new opt-in routing fence. Mixed-version/old-binary rollback is BLOCKED pending version fencing and rehearsal |

Primary changed application paths: `backend/app/etl_bindings/`, `api/etl.py`, `data_pipelines/service.py`, `unified/engines.py`, scope/resource-scope/transaction registration, `migrations/env.py`, `db/etl_rollback.py`; new migration0040; `frontend/src/ETLNativeBindings.jsx`, existing Workflow page and selection helper. Tests: `backend/tests/test_etl_binding_lifecycle.py`, `frontend/scripts/native_binding_acceptance.mjs`, existing harness and selection regression. Applied migrations0039 and earlier, prior ETL regression test bytes and collector pin are unchanged. No unrelated security remediation or execution engine.

## Actual final verification

| Check | Result | Exact evidence |
|---|---|---|
| Clean committed-source PostgreSQL/API/RBAC/ETL regression lab | **104 PASS, 0 failures/errors/skips**, exit0 | [regressions](final/regressions.log), [commands/source/cleanup](final/RESULTS.json) |
| New tests | 18 cases included above; **66 ordinary authenticated HTTP status assertions** plus separately reconciled concurrent responses | TEST_MATRIX.json; final/test_*.json |
| Existing OC-ETL-002–005 | All retained 86 cases included; 21 scope HTTP +36 old native-contract assertions and seven DAG/security cases retained | final/http-results.json, native-binding-contract-results.json, regressions.log |
| Actual Chromium | **9 new +19 retained groups PASS**, included in test-case count, not 28 additional unit tests | [new browser](final/native-binding-browser-results.json), [retained browser](final/workflow-browser-results.json); history/viewer and retained desktop/mobile screenshots |
| Existing migration/recovery probe | **6 groups PASS**, including fresh/legacy populated upgrade, safe empty/unassigned rollback, refusal and dump/restore | final/rollback-results.json; rollback-commands.json retains expected nonzero refusals |
| New populated temporal downgrade and restoration | Explicit0039 downgrade refused before DDL; schema/revision/content unchanged; actual custom-format pg_dump/pg_restore; **104 tables** compared for counts, row SHA-256, columns and FKs | [comparison](final/temporal-preservation-results.json), refusal log, synthetic-temporal-backup.dump |
| Crash/transaction rollback | Backend terminated after closure/before successor; old version stays current. Deferred orphan closure/delete/snapshot tamper refuse. After acknowledged HTTP commit, owned API **SIGKILL** and same-version restart preserve the exact version/identity | final/test_database_immutability_and_interrupted_closure_rollback.json, [restart proof](final/binding-api-restart-results.json), restart log |
| Frontend unit/lint/build | **46 PASS, 0 FAIL/SKIP**, lint/build exit0. Frontend runtime source unchanged from `b94f7ed`; later commits change backend/test-only files | frontend-tests.log, frontend-lint.log, frontend-build.log |
| Static | Black/Ruff/compile PASS; git diff whitespace and 56-ID roadmap checks PASS | black.log, ruff.log, VALIDATION.json |
| Hosted final HEAD | Recorded only after evidence commit in PR80 closure comment; no local result substituted for hosted status | PR80 final-HEAD check URLs/conclusions |

Counts overlap. Synthetic accepted-row negative probes are not certified native receipts. Freshness's six clock/boundary assertions are one unit test, not a genuine-provider health test. Concurrent ownership gives one201/one409; independent targets both201. No test or assertion was weakened to permit activation.

Exact main lab command from repository root:

```sh
ETL_WORKFLOW_UI_ACCEPTANCE=1 PLAYWRIGHT_MODULE=/tmp/oc-closure-tools/node_modules/playwright/index.mjs PLAYWRIGHT_BROWSERS_PATH=/tmp/oc-etl003a-browsers ETL_SCOPE_EVIDENCE_DIR=/tmp/etl006-qualified-source backend/.venv/bin/python scripts/etl-scope-acceptance.py
```

PostgreSQL17.11, local immutable image ID `sha256:ab20e934b27ba3ff927c1b4c9ff8cf6c32f315f743efe68dd3441182a87fb085`; full owned container identity in RESULTS. All data/credentials are synthetic. API/Vite/Chromium run on task-owned loopback ports against disposable PostgreSQL Docker/tmpfs. This is controlled integration testing, not a new API/frontend image deployment or access to owner UAT.

## Failed and intermediate attempts retained

| Directory | Actual outcome | Meaning |
|---|---|---|
| attempt1 | 86 PASS | Initial retained baseline on dirty development source; not final feature qualification |
| attempt2 | 96 cases, 1 FAIL +1 ERROR | Wrong audit field/unsupported role GET in new test fixtures |
| attempt3 | 98 cases, 2 FAIL +1 ERROR | Generic route audit did not provide required binding-version domain event: fixed by atomic version-specific audit. Role revision field and browser scoping corrected |
| attempt4 | 98 cases, 2 FAIL | Fixture role contract and accessible candidate label/select targeting; explicit label association repaired |
| attempt5 | 98 PASS | Intermediate subset |
| attempt6 | 102 PASS | Expanded precommit subset |
| committed-attempt1 | 102 cases, 1 FAIL at b94f7ed | Browser delayed fulfiller raced the real tenant-switch abort; production cancellation was correct |
| committed-attempt2 | 102 PASS at8258ef3 | Test explicitly accepts only observed ERR_ABORTED, or safely fulfilled response; asserts no old-tenant state |
| restart-development | 103 cases, 16 ERROR | Missing base_url helper argument caught by Ruff; development run changed during authoring and is **not qualified** by its end-of-run SHA. Fixed and rerun clean |
| final | 104 PASS at `8e7cdf91d70f19a19c1cdf8d763818446b1c179f` | Final qualified source, including restart and reader ownership guard |

The initial local formatter path was unavailable; isolated pinned Prettier3.6.2 was used without changing application dependencies. No failure was converted into a skip. Earlier development end-of-run SHAs/diffs do not certify their intermediate uncommitted source. Raw logs, exit codes, failure screenshots and scoped cleanup are preserved.

## Deployment and remaining blockers

No separate containerized deployment was performed. **BLOCKED** until immutable reviewed application candidates and version-fenced old-writer rollback are qualified. Empty schema downgrade and restored database hashes do not prove older applications respect the new temporal fence. The managed Docker writable layer also reached capacity while its disposable PostgreSQL layer existed; it recovered on scoped removal. No unrelated Docker cleanup was used to free space. Provision adequate isolated build capacity before image deployment.

D09 exact native authority/namespace proof is absent: reader capability proof alone cannot safely prove cross-surface identity aliases. Confirmation therefore denies; active replacement, new qualified receipt routing and positive Workflow activation/health remain BLOCKED/NOT TESTED. No successful provider status or independent certification is synthesized. D07 recurrence/calendar, D08 separate threshold and independent UAT remain open. D01–D06 owner approval is already recorded; do not re-request it or mislabel those decisions unapproved.

Next bounded work: define and validate the D09 provider authority attestation against an explicitly authorized exact-build read-only target; qualify confirmation and admitted receipt provenance with independent receipts; use the existing reviewed handoff for active-reader cutover. Separately implement/rehearse old-writer version fencing and rollback before candidate image deployment. These are remaining requirements, not waived limitations or completed phases.

All task containers/tmpfs, owned API/Vite and restart API processes stopped; private fixture credentials removed. Final RESULTs and restart tests verify teardown. Original OC-ETL-002–005 evidence is untouched. The 31 included journeys, 30 unrecovered exact numbered definitions, Journey20 excluded/Journey32 skipped, and nine old controlled-scope owner approvals with independent UAT pending remain unchanged. No new ETL functionality owner acceptance is inferred.

**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.** No merge, owner UAT access, deployment or release promotion.
