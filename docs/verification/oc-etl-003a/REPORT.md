# OC-ETL-003A.1 — protected migration CI compatibility

2026-11-06 UTC (continuing 2026-11-05 evidence). Branch dev/post-pr78-architecture-closure-20261105, draft PR #80. Baseline `a420dbc12e66196e00832f450d46a739b7cd0e99`. Implementation commits `64098b03a6ac43ec551b791df2078f0c8b19af4a` and `3a9726b` (test-output retention); artifact source HEAD `3a9726b44fb1fdacc058b5a337267d3c532824b4`. Final evidence commit adds this report and workflow-validator coverage, with no application changes. Owner approval of nine controlled functional scopes comes from the OC-ETL-003A.1 conversation, not CI. Independent UAT remains pending.

**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**

## Four original failures and corrections

All four hosted failures were at `a420dbc12e66196e00832f450d46a739b7cd0e99`. Original logs/metadata are in hosted-baseline and ../oc-etl-004/preflight; previous partial local report is initial-progress-report.md.

| Run / job | Root cause and precise state | Correction |
|---|---|---|
| 42095133058 / pipeline-contracts | Nine HTTP groups passed, then v16-acceptance.py final populated downgrade-to-0031 assertion accepted only old revision-specific errors, while central guard refused earlier at current head | Require nonzero refusal, stable central guard/recovery fragments, and equal logical dumps before/after covering all rows, schema, constraints and Alembic version |
| 42095133805 / staging-smoke | At empty 0024_notification_leases, relative downgrade -1 is explicitly unsupported | Use 0023_worker_heartbeat, the immutable down_revision of 0024; actual empty downgrade/re-upgrade and populated upgrade probe retained |
| 42095132761 / noc | At 0024 after incident backfill verification, old harness attempted downgrade to 0020, deleting populated incident/activity tables | Preserve initial empty 0024→0019→0024 and empty 0024→0020 paths. On populated state require refusal, recovery guidance, identical dump, then repeat upgrade and verify stable incident IDs/history |
| 42095132932 / verification | Restored current-head database: sprint13 recovery probe did not recognize central preservation error | Accept stable central error only with backup/restoration guidance; retain nonzero return, unchanged revision and independent persisted projection comparison. New positive/negative guard tests reject missing guidance or changed revision |

No application code, migration guard, auth, DAG lock, applied migration, branch protection, collector binary/configuration or release policy changed. PROTECTED_SOURCE_SHA256.json independently compares protected bytes with baseline. No guard bypass, forced rollback, populated deletion, synthetic certification or skip conversion.

## Actual local execution

PostgreSQL: PostgreSQL 17.11 on x86_64-pc-linux-musl, compiled by gcc (Alpine 15.2.0) 15.2.0, 64-bit. Isolated postgres:17-alpine; PostgreSQL 17.11 image identity is in regression/RESULTS.json. Local Node24 differs from hosted staging Node20; hosted final-head results remain necessary. Dependencies/build cache were redirected to /tmp for space; no product configuration changed.

| Command / suite | Actual result and evidence |
|---|---|
| `(cd backend && .venv/bin/python -m unittest tests.test_pipeline_transport_v16 tests.test_sprint13_recovery_probe -v)` | 18 PASS, 0 failures/errors/skips; oc-etl003a-focused.log, exit 0 |
| `DOCKER_HOST=unix:///var/run/docker.sock V16_API_ACCEPTANCE=1 V16_EVIDENCE_DIR=/tmp/oc-etl003a-pipeline backend/.venv/bin/python scripts/v16-acceptance.py` | Previously preserved nine HTTP groups PASS and populated refusal/dump equality, exit 0; pipeline/ |
| `backend/.venv/bin/python staging-reproduction.py` | Explicit 0024→0023→0024 smoke, populated historical upgrade and model alignment PASS, exit 0; staging/result.json and raw command logs |
| `backend/.venv/bin/python staging-full-reproduction.py` | All executable staging workflow checks including real HTTP auth/tenancy/security and browser checks PASS, exit 0; staging-full/result.json. Dependency installation reused existing pinned tools; no check removed |
| `ETL_SCOPE_EVIDENCE_DIR=/tmp/oc-etl003a-regression backend/.venv/bin/python scripts/etl-scope-acceptance.py` | 84 PASS, 0 failures/errors/skips; 21 HTTP status assertions included; six preservation/restore groups PASS; source identity and cleanup in regression/RESULTS.json |
| `DOCKER_HOST=unix:///var/run/docker.sock PLAYWRIGHT_MODULE=/tmp/oc-closure-tools/node_modules/playwright/index.mjs OPERATIONAL_EVIDENCE_DIR=/tmp/oc-etl003a-noc-verified OPSCONTROL_UI_THEME_ACCEPTANCE=1 backend/.venv/bin/python scripts/operational-acceptance.py` | PASS, exit 0; 8 ETL browser phases, 3 NOC phases, theme and tenant/stale/recovery negatives; noc-verified/ artifacts and raw log |
| `DOCKER_HOST=unix:///var/run/docker.sock OPSCONTROL_TEST_EVIDENCE_DIR=/tmp/oc-etl003a-v15-final PLAYWRIGHT_MODULE=/tmp/oc-closure-tools/node_modules/playwright/index.mjs OPSCONTROL_OTEL_BINARY=/tmp/oc-closure-tools/otelcol-contrib bash scripts/test-quality.sh pentaho` | PASS, exit 0; 595 unittest cases executed, 569 PASS, 26 skipped under existing explicit environment gates; raw per-test reasons in v15-final/pentaho-postgres/unittest.log. Restore REC-01–06 PASS; HTTP group counts in command log; six-page browser regressions PASS |
| `python scripts/check-ci-roadmap.py`; `bash scripts/check-workflows.sh`; focused Ruff and compile | PASS; pinned actionlint now covers both modified workflows as well as existing six |

Counts overlap intentionally; do not sum suites as unique tests. Existing skipped tests remain skipped with actual raw reasons, never represented as passing. The separately executed owned PostgreSQL/HTTP suite has zero skips. Full local staging reproduction is task-owned, not access to an existing staging/UAT system.

## Preservation, attempts and cleanup

pipeline/preservation.json and noc-verified/etl/populated-migration-preservation.json retain independently generated equal before/after logical dump hashes and nonzero refusal. Only PostgreSQL randomized restrict/unrestrict keys are normalized. regression/rollback-results.json contains every-table content hashes, columns, FKs, native identity/evidence refusal and actual custom-format backup/restore comparison. v15-final/pentaho-postgres/sprint13-recovery.json records REC-01–06 and restoration/evidence preservation without claiming real WAL/PITR/DR certification.

Earlier local failures are retained: direct NOC invocation omitted OPERATIONAL_EVIDENCE_DIR; corrected by using the actual wrapper. A staging helper initially saw PostgreSQL's temporary startup server and later omitted PYTHONPATH; corrected to TCP readiness and the workflow's PYTHONPATH. Browser cache and frontend build attempts hit ENOSPC; task dependencies/cache/build output moved to /tmp. One attempted dependency relocation had a parent-directory module-resolution error; restored node_modules directory semantics. The first full staging attempt lacked the matching Playwright headless executable; the pinned matching Chromium was installed in /tmp and the full staging workflow rerun passed. These are environment/test invocation failures, not quietly skipped application defects. Original CI and all failed attempt logs remain preserved.

Every database/container is task-owned; teardown removes exact named containers/volumes only. Staging helpers and regression/RESULTS.json record cleanup and stopped processes. NOC and V1.6 harness finally blocks remove their specific containers; CLEANUP.json independently inventories absence afterward. Failed private service logs are retained with restrictive permissions; credentials/session fixtures are not exported. No production, owner UAT or genuine-provider target was accessed.

## Roadmap and acceptance governance

[CI requirements matrix](../ci-roadmap-alignment/CI_REQUIREMENTS_MATRIX.md) maps 56 recovered canonical/design IDs with source/test paths and actual workflow/jobs. It retains 31 included journeys, Journey20 excluded, Journey32 skipped and 30 SOURCE_NOT_RECOVERED numbered definitions. No arbitrary numbered crosswalk or missing historical authority is invented. Nine owner decisions use OWNER_APPROVED_CONTROLLED_SCOPE — INDEPENDENT_UAT_PENDING; no genuine-provider or independent UAT promotion. Existing relevant denial/revocation/method-ownership/freshness/configuration/recovery tests are reused; one focused refusal regression was added. No duplicate tests for counts.

## Hosted closure and next task

Final-head Actions results are recorded in the PR80 closure comment after this evidence commit is pushed; local PASS is not a claim that hosted jobs passed. Closure requires the actual four final-head workflow conclusions and no failing/running required check. If a hosted failure persists, it remains a blocker and its raw log must be retained. Final response cites the exact source SHA and closure comment.

OC-ETL-004 Workflow/Job Configuration UI remains a **separate subsequent implementation task** after CI closure, with missing recurrence/threshold/readiness authority explicit. It is not implemented by this CI correction. Historical downgrade and older-application compatibility limitations in ../oc-etl-003/ROLLBACK_COMPATIBILITY.md remain applicable. Owner review, genuine providers, independent UAT, CHK-001, CHK-002 and security/legal/image gates remain independent.
