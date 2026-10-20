# Stage B acceptance evidence and remaining gates

Source snapshot: `origin/main` baseline `eb7fb17dfae40fe580fc49e2dadeb3e7f0ad5167`, isolated `feat/stage-b-branch-aware-uat` worktree. Date: 20 October 2026. Test environment: workspace Python 3.12, Docker Compose v2.40.3; no persistent UAT runner, database or credentials were accessed. Local Docker daemon access was denied, so no container/image execution is claimed.

| Gate | Status | Executed evidence / blocker |
| --- | --- | --- |
| FEATURE_UAT/MAIN/MAINTENANCE transition; latest pending SHA | PASS | `python3 -m unittest discover -s scripts/uat -p test_stage_b.py -v`; **12 passed, 0 failed**, including process-level file-lock serialization. |
| Main cannot replace feature deployment | PASS (unit) | Transition rejects `begin(main)` in FEATURE_UAT; current feature SHA remains after `record-main`. Target-host demonstration NOT RUN. |
| Concurrent operations and failure freeze | PASS (unit) | Private file lock, in-flight rejection, MAINTENANCE failure test. Multi-runner contention NOT RUN. |
| Migration gate and backup integrity | PASS (unit) | Missing/old/corrupt archive, reviewer separation and unchanged-hash cases. Real UAT backup and migration NOT RUN. |
| Existing UAT Compose/volume preservation | PASS (static/unit) | Overlay touches images and API command only; preflight requires existing postgres and UAT project. Actual owned Compose and volume identity UNVERIFIED. |
| Daemonless Compose rendering | PASS | `docker compose -f <temporary-synthetic-UAT-base> -f deploy/uat/compose.images.yml config --format json`; API command and unchanged PostgreSQL image asserted. No UAT container contacted. |
| Workflow schema | PASS | `bash scripts/check-workflows.sh` with checksum-pinned actionlint v1.7.7. |
| Python syntax/format/lint/whitespace | PASS | `python3 -m compileall -q scripts/uat/stage_b_state.py scripts/uat/stage_b_deploy.py scripts/uat/stage_b_smoke.py`; `black --check` (4 files); `ruff check` (4 files); `git diff --check`. |
| Immutable image build and pull | NOT RUN | No approved target/pilot; GHCR images not built. |
| Dedicated protected runner and reviewer approval | UNVERIFIED | GitHub runner inventory API returned HTTP 403; no environment was listed. |
| Feature UAT deployment and smoke | NOT RUN | No accessible existing persistent UAT configuration, backup or synthetic smoke identities. |
| Incoming main protection on target host | NOT RUN | Unit protection passes; record-only trigger disabled until pilot. |
| Feature acceptance and latest main reconciliation | NOT RUN | Requires witnessed end-to-end pilot and owner change record. |
| Production/Pentaho acceptance | NOT RUN | Outside Stage B; RT-001–RT-020 remain NOT RUN. |

No deployment success is claimed. The draft PR must remain gated until the runbook pilot is completed and evidence is added. Automatic deployment remains disabled by unset/false repository variables; the only future deployment workflow trigger is protected manual dispatch. The main-push trigger can **only record** a pending SHA after separate enablement.
