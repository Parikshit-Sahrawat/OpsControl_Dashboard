# Exact-head Access and keyboard recovery

Date: 2026-11-09 UTC / Asia/Calcutta. PR [89](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/pull/89) remains draft. Disposition: **corrections implemented; local focused verification passed; hosted final-head result pending; Sprint 1 NOT COMPLETE**.

## Baseline and root causes

Starting head `874c481a2446022b693e6660c59af15f03c5476c`, main `2e4fe5d8cb0f39170b0d789fdd7e07be4ac0219a`. No newer remote work was overwritten. [BASELINE.json](BASELINE.json) distinguishes PR head, synthetic merge source, and local tested commits.

1. [Access run42588850838](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/actions/runs/42588850838), job129065189749: `hosted/customer-department-access-evidence/docker/failed.log` says `additional privileges requested: pass "--allow=fs.read=/etc/ssl/certs/ca-certificates.crt"`. Compose delegates to Bake, which refuses the CA file outside build contexts. The secret was supplied; this was an entitlement rejection. `scripts/ci/compose_build.py` now obtains **Compose's own** Bake plan and invokes Bake with a single canonical, certificate-validated file entitlement and `--load`. Project image tags, targets, build secrets and Compose configuration are preserved. No wildcard/directory entitlement, entitlement-check disable, host networking, TLS bypass, optional secret, secret-in-layer copy or broad Docker cleanup was added.
2. [Recovery run42588850746](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/actions/runs/42588850746), job129065189865: keyboard helper could not reach Save at resource_crud_acceptance.mjs:305. Its screenshot shows the authorized revision request pending and Save natively disabled. The current revision requirement was correct; skipping that guard would be unsafe. Save now remains keyboard-reachable with `aria-disabled` while revisions are unavailable; submission reports the blocking reason without a request or focus loss. Resource identity fields use a native form and an explicitly associated submit button, supporting Enter from a text field as well as the button. A synchronous in-flight fence prevents duplicate submits. Existing revision/child-source maps, tenant-scoped API and backend conflict enforcement remain intact.

`frontend/scripts/resource_crud_acceptance.mjs` delays a **genuine** authenticated context response, tests the blocked Enter path with zero writes and preserved edits/focus, then releases it and proves button Enter, text-input Enter, increasing resource revisions, one command per submission and persisted reload. No response/revision/database value is fabricated. Existing keyboard traversal bound and browser timeouts were not increased.

## Verification and exact counts

Counts below describe separate runners and nested groups; do not sum overlapping tests as unique coverage. Commands ran against source snapshots identified below; the final evidence-only/formatting commits preserve the tested runtime and browser file hashes.

| Boundary / command | Source | Result | Evidence |
|---|---|---|---|
| `backend/.venv/bin/python -m unittest discover -s tests -v` (repository root) |9164a98 working tree; only later helper/test formatting|100 PASS, 0 FAIL, 0 SKIP|ci-unit-final.log|
| `python -m unittest discover -s tests -p 'test_ci_*.py' -v` |final formatted helper/tests|33 PASS,0 FAIL,0 SKIP; subset of100|ci-policy-final.log|
| Focused `python -m unittest tests.test_ci_compose_build tests.test_ci_build_trust -v` |final formatted helper/tests|5 PASS, including 3 new entitlement tests; subset of100, not additional unique tests|focused-tests.log|
| `cd backend && .venv/bin/python -m unittest discover -s tests -v` |9164a98|670 discovered:374 PASS,0 FAIL,296 SKIP|backend-unit.log; BACKEND_SKIPS.json lists every skip/reason|
| `npm test --prefix frontend` |1f430a4 frontend; later focus change affects UI only, not these helper tests|55 PASS,0 FAIL,0 SKIP|frontend-tests.log|
| `npm run lint --prefix frontend`; `npm run build --prefix frontend` |9164a98|both exit0; existing >500kB bundle warning retained|frontend-lint.log; frontend-build.log|
| `bash scripts/check-workflows.sh` |9164a98|exit0; all28 workflows validated with checksum-pinned actionlint1.7.7|workflows.log and workflows.exit|
| Tiny actual Compose/Bake/required CA-secret build |1f430a4 helper (later formatting only)|missing entitlement rejected; exact-file build PASS; runtime secret absent; owned image removed|bake-probe-3/result.json, logs, cleanup.json|
| `ACCESS_BROWSER_ACCEPTANCE=1 ACCESS_EVIDENCE_DIR=... backend/.venv/bin/python scripts/access-acceptance.py` |1f430a4|exit0;25 authenticated API/security groups +8 browser groups; schema/migration refusal checks PASS|access-1.log; access-1/security.json, browser.json, migration.json, schema.json|
| `RELEASE_BROWSER_ACCEPTANCE=1 RELEASE_EVIDENCE_DIR=... backend/.venv/bin/python scripts/release-acceptance.py` |753e372|exit0;13 top-level groups PASS; resource CRUD8 nested groups, keyboard regression PASS;205-resource pagination, tenant negatives, real HTTPS/worker/alert recovery, backup/restore and TLS|release-2.log; release-2/report.json, resource-crud.json, keyboard-regression.json|
| `S01_EVIDENCE_DIR=... backend/.venv/bin/python scripts/sprint1-configuration-acceptance.py` |9164a98|exit0;46 real PG/HTTP tests PASS,0 FAIL,0 SKIP; pre/postcommit SIGKILL/restart/replay probes PASS; migration/refusal and restore PASS|configuration-1/authenticated-contracts.log, backup-restore.json, context-fence-preservation.json, cleanup.json|
| Full five-service Access Docker application build |new helper|BLOCKED locally by backing-store capacity (243MiB free of32GiB,100% use); NOT RUN here, final hosted job pending|No full-build PASS inferred from tiny probe or non-container app acceptance|

Backend baseline skips are explicit environment/owned-fixture conditions, **not successful integration tests**. The separate actual PG/HTTP/browser runners supply their own executed evidence. We did not enable live providers, certify durability or claim every skipped requirement covered. No quality threshold was changed. The documentation check flagged three raw `eks.json` artifacts whose producer appends a literal backslash-n rather than JSON whitespace. Their objects and exact suffix were independently checked while preserving original bytes; this format limitation remains in VALIDATION.json, without a blanket JSON-validity claim.

Environment: Python3.12.14, Node24.19.0, Playwright1.56.1/Chromium141, PostgreSQL17.11, Docker Engine28.4.0 usable, Compose2.40.3, Buildx0.31.0. Docker-backed capacity is constrained; no shared daemon restart or broad prune was attempted. API/UI ran on task-owned loopback ports with disposable PG tmpfs fixtures; this is not disk-crash spool certification.

## Preserved failures and recovery comparisons

- Exact-head historical artifacts and raw job logs remain under `hosted/` and `job-*.log`. [ARTIFACT_DOWNLOAD_VERIFICATION.json](ARTIFACT_DOWNLOAD_VERIFICATION.json) proves all9 archive digests against GitHub API metadata.
- Local Bake attempt1 failed because default Buildx state was under read-only HOME. Attempt2 used owned Buildx state but correctly refused an unrelated out-of-working-directory build context. Attempt3 ran in its owned context, reproduced missing CA entitlement, then succeeded with **only** the CA-file grant. All attempts/logs/cleanup retained; no additional context entitlement or disabled filesystem checks.
- First recovery test at1f430a4 failed the new focus assertion: its rejected save set busy and briefly disabled the focused button. `753e372` moved this guard before busy/in-flight state. `release-1/failed-command.log` and screenshot retain this failure; `release-2/keyboard-regression.json` proves0 pending-snapshot writes and2 later committed commands with focus and revision/reload assertions.
- Final restore compared108 tables,1202 fixture rows and564 constraints. Source dump SHA `eb89988862d18bcc17e660fbe619e9a03f7e89797c78fdd1cd837823b52a98c5`; restore evidence includes every row/constraint comparison. Configuration migration0043 refusal preserved the complete normalized dump hash `d2816491af39a1114a0220382645027f94b4770a4038da1e7f1f7cf6b3634971` before and after. Application migrations were not modified.

## Security, CI and acceptance limits

[IMAGE_FAILURE_REVIEW.md](IMAGE_FAILURE_REVIEW.md) and image-summary.json retain all seven exact historical candidate identities and984 scanner matches, including41 Critical/371 High. All licence reviewers remain null/PENDING. Grype `wont-fix` is not a waiver. No image findings were suppressed, no image replaced, and collector0.123.0/guards remain unchanged. New-head scans have not yet produced reviewed results.

Ruleset26082467 was read only; all13 strict required checks and GitHub integration15368 remain unchanged (ruleset.json). No workflow, job name, threshold, permission or branch protection changed. Push triggers applicable legacy and Tier A/B/C PR workflows on the final head. Under mandatory **Trigger-and-Exit**, final run URLs are recorded in the PR handoff and conclusions are **CI TRIGGERED — RESULT PENDING**. No polling/waiting or green final-head claim is authorized by this evidence package.

[Persisted keyboard result screenshot](release-2/resource-keyboard-desktop.png); [original disabled-save screenshot](hosted/release-reliability-evidence/resource-failure.png); [first local failure](release-1/resource-failure.png). These are automated development evidence, not owner visual acceptance. Owner review and independent PR approval remain required before any future merge.

Owned containers/processes were stopped and removed: release-1/cleanup.json, release-2/cleanup.json, configuration-1/cleanup.json. Access success removes its owned PG/private directory. Failed-attempt private dumps/secrets were removed after retaining redacted evidence and hashes (failed-attempt-private-cleanup.json). Bake tags/private state were removed; shared build cache was not pruned. No deployment, merge, provider access, live UAT, collector upgrade or Sprint2 work occurred.

**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO · Sprint1 NOT COMPLETE.**
