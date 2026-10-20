# Stage B branch-aware UAT — implementation and acceptance ledger

Status: **IMPLEMENTED FOR REVIEW; CONTROLLED DEPLOYMENT NOT RUN.** Automatic deployment remains disabled. This is a Feature UAT policy increment, not production readiness or real-provider acceptance.

## Source and boundaries

- Verified implementation baseline: `origin/main` at `eb7fb17dfae40fe580fc49e2dadeb3e7f0ad5167` on 20 October 2026. Dedicated branch: `feat/stage-b-branch-aware-uat`.
- Controlling architecture: [ARCH-001 V1.6](../../ARCH_001_V16.md), [ARCH-ETL-001 V1.6](../../architecture/ARCH_ETL_001_V16.md), [deployment reconciliation](../../architecture/OPS_DEPLOY_001.md). No approved architecture or application authorization contract changed.
- Existing Sprint 14 disposable harness remains at `scripts/uat/local_environment.py`; Stage B does not run its reset operation. Existing Demo, Development, Pentaho and Production are untouched.
- Existing `docker-compose.demo.yml` and `backend/Dockerfile.demo` are unsuitable for persistent UAT: they contain demo-specific settings and the API image runs Alembic/bootstrap at startup. Stage B uses `backend/Dockerfile.uat` and an image-only override on an **existing operator-owned UAT Compose file**. Neither a UAT database nor its volumes are created or reset by the deployment driver.

## Implemented policy

| Requirement | Implementation | Evidence / limit |
| --- | --- | --- |
| FEATURE_UAT default; MAIN; MAINTENANCE | Private atomic state, append-only event ledger and `flock` in `scripts/uat/stage_b_state.py` | Focused transition tests. No live state initialized. |
| Immutable branch/SHA | Manual dispatch checks branch tip and completed successful check suites; hosted builder checks out exact SHA; UAT runner pulls GHCR digests | Workflow lint passed; remote image build not run. |
| Main cannot overwrite Feature UAT | Main push records latest SHA only after explicit record-only enablement; MAIN deploy requires release transition and matching pending SHA | Focused tests. Record-only trigger remains disabled. |
| Restricted serialized runner | Dedicated `opscontrol-stage-b-uat` label, workflow concurrency, UAT marker, protected environment check, private file lock | Runner/environments not verified or provisioned from this workspace. |
| Migration separation | API CMD runs API only; migration is separate one-shot Compose service and hash-triggered gate | Backend image and script inspection; no database migration run. |
| Backup/review/approval | Private checksum-verified recent custom archive, `pg_restore --list`, independent reviewer field, required protected environment reviewers with self-review disabled | Unit tests for stale/corrupt/missing backup. A real restore drill and environment protection are still required. |
| Data/secret/CSP preservation | Overlay changes images and API command only; database service must already be running; no volume removal/reset or secret replacement | Compose preflight tests. Existing UAT base Compose and its values were unavailable for inspection. |
| Runtime smoke | API/DB and frontend HTTP checks plus authenticated session, customer/RBAC negative and monitoring probe | Script exists; no live Stage B UAT credentials/environment, so NOT RUN. |
| Failure handling | Failure enters MAINTENANCE, preserves last verified identity and pending-main state; recovery requires operator verification | Transition tests. Rollback is never automatic after possible schema change. |

## Verification actually executed

The reproducible commands and exact outcomes are in [ACCEPTANCE.md](ACCEPTANCE.md). Focused state, backup and Compose boundary tests pass. `bash scripts/check-workflows.sh` passes with the repository's checksum-pinned actionlint. No image was built, no UAT container was changed, no migration was executed and no runtime smoke was claimed.

## Acceptance blockers and next controlled gate

The GitHub API returned `403 Resource not accessible by integration` for self-hosted runner inventory, and no UAT environment was listed. The operator-owned persistent UAT Compose path, project ownership, private backup/restore evidence, credential files, required reviewers and independent smoke identities are not available here. Therefore Feature UAT deployment, protection during an incoming main commit, feature acceptance and main reconciliation have **not** been demonstrated on the target environment. Keep `STAGE_B_UAT_ENABLED` and `STAGE_B_UAT_RECORD_MAIN_ENABLED` unset/false. The [runbook](RUNBOOK.md) gives a gated pilot sequence; only after its recorded end-to-end pass may operators enable manual dispatch and record-only main observation. There is no automatic deployment path.

Pentaho RT-001–RT-020 remain **NOT RUN**; production remains **NOT READY**. Protected PR #33, existing application runtime, migrations, databases and volumes were not modified.
