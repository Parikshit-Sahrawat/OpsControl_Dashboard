# OC-ETL-003 — ETL rollback and DAG integrity

Date: 2026-11-05 UTC. Baseline `a9fe107816fb91583b4262746a5c0a2c244c0e15`.
Implementation and exact clean-tree tested commit: `f57153836615fb07d748ede6b49af6a11dba96fe`.
Branch `dev/post-pr78-architecture-closure-20261105`; [draft PR #80](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/pull/80).

**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**

## Result

Both bounded foundation risks have enforceable safeguards and real PostgreSQL evidence. This is controlled development verification, pending owner review; no genuine-provider, release or production acceptance. No collector, application scheduling/execution/retry controls, schema revision, applied migration file, or production/UAT resource changed.

| Verification | Final result | Evidence |
|---|---|---|
| Existing scope, foundation, RBAC and imported Pentaho/incident regressions | 77 PASS | [Raw suite](final/regressions.log) |
| New real HTTP concurrency/security cases | 7 PASS | same suite; four independent persisted-graph JSON exports |
| Combined unittest suite | **84 PASS, 0 failures/errors, 0 skipped** | final/regressions.log |
| PostgreSQL migration/preservation/recovery | **6 PASS groups** (not additional unittest cases) | [Snapshot hashes, database version, commands](final/rollback-results.json) |
| Existing authenticated HTTP acceptance assertions | **21 PASS**, included in the 77 | [HTTP results](final/http-results.json) |
| Fresh head migration and model alignment | PASS | final/migration-upgrade.log; final/migration-model-check.log |
| Focused Ruff / Python compilation / diff whitespace | PASS | oc-etl003-lint.log; oc-etl003-compile.log; VALIDATION.json |
| Scoped cleanup | PASS for every attempt | Each attempt RESULTS.json; no owned container left; API stopped |

PostgreSQL: `PostgreSQL 17.11 on x86_64-pc-linux-musl, compiled by gcc (Alpine 15.2.0) 15.2.0, 64-bit`. Exact local image identity and container IDs are in final/RESULTS.json; no image publication occurred.

## Implementation and findings

`backend/app/db/etl_rollback.py` and `backend/migrations/env.py` preflight the full explicit downgrade path in the same transactional-DDL transaction. Protected tables are locked in deterministic order, then checked for populated tables/non-null fields before any migration runs. A populated workflow, dependency, job link, native identity or source evidence refuses rollback with an actionable error. Applied migrations remain byte-identical; this is runner protection, not a new schema migration. Offline downgrade SQL and ambiguous relative/range targets are refused. Existing per-revision guards remain effective.

`backend/app/api/etl.py` locks the already-authorized workflow row before reading its complete graph. READ COMMITTED ensures a waiter sees the previous writer's committed edge. The existing immutable workflow/edge ownership hook remains in place. A cycle, duplicate or self edge cannot commit through this path; row-lock timeout returns actionable HTTP 409 and rolls back. Scope filtering cannot hide a graph path from internal validation; the internal complete graph is never returned to the caller.

The first concurrency attempt exposed existing global exclusive authorization serialization, not a demonstrated baseline HTTP cycle. `backend/app/db/session.py` opts **only the exact dependency-create POST route** into a shared authorization advisory lock. `backend/app/security/boundaries.py` retains exclusive locking by default for every authority/session mutation. Both modes use the same key; authorization changes exclude graph writes. Principal revision and session revalidation are unchanged. The new test proves this exclusion; other workflows now progress concurrently. No security hook is bypassed. The original graph-check race was identified by source inspection; no fabricated baseline race reproduction is claimed.

## Reproduction and failure history

Run from repository root with installed backend dependencies and a usable Docker daemon:

```sh
ETL_SCOPE_EVIDENCE_DIR=/tmp/oc-etl003-reproduction backend/.venv/bin/python scripts/etl-scope-acceptance.py
```

The harness creates a random, labeled task-owned PostgreSQL container on a loopback ephemeral port with generated synthetic credentials and tmpfs data. It runs migrations, actual dump/restore, a local API, authenticated requests and regressions, and removes only its exact container in finally. The inherited `oc-etl002-` prefix is intentional compatibility with the existing harness. It never uses the owner's UAT database. Logs redact the generated database password. The backup contains only synthetic fixture rows, created before login/user fixtures.

- **run1 FAIL:** new preflight caught the wrong Alembic exception while distinguishing forward ancestry. Fixed to handle RangeNotAncestorError; log retained.
- **run2 FAIL:** 83 tests ran: 78 passed, 4 failed, 1 error, 0 skipped. Existing exclusive authorization lock prevented two requests reaching graph locks and blocked unrelated workflows. These are retained failed concurrency assertions, not ignored skips.
- **run3 PASS:** 84 tests and six migration groups, dirty implementation tree; preliminary evidence only.
- **final PASS:** same 84 tests and six groups at exact committed clean source above. Raw command exit codes, graphs, before/after table hashes and cleanup retained.

See [rollback contract](ROLLBACK_COMPATIBILITY.md), [concurrency matrix](CONCURRENCY.md), [source identities](SOURCE_SHA256.json) and [artifact manifest](ARTIFACT_SHA256.json).

## Remaining boundaries and next task

No guarantee is made for privileged raw SQL, older checkouts lacking this runner, arbitrary historical downgrade combinations, non-READ-COMMITTED deployments, or a future graph mutation route that omits the workflow lock. Production roles must not have unrestricted schema/graph write privileges. Older protected revisions are conservatively checked; only the paths listed in the rollback contract were executed. Backup recovery was proven on synthetic local PostgreSQL, not a customer database or deployment rollback.

Next bounded task: implement the approved Workflow configuration UI and readiness journeys against the now-tested scope/graph API; first recover any missing exact journey authority. Workflow occurrence evaluation, full provider certification and owner acceptance remain separate gaps. No merge, deployment or Stage/release promotion is authorized by this report.
