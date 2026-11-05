# Test results — integrated source fa3a9a24107f465dac6692b2a9ea69b910ff06ee

## Current-baseline executions (2026-11-05)

| Suite | Result | Exit | Raw log |
|---|---|---|---|
| PostgreSQL full regression and preservation | PASS | 0 | `raw/resumed/regressions.log` |
| Frontend unit tests | PASS | 0 | `raw/resumed/frontend.log` |
| Frontend lint | PASS | 0 | `raw/resumed/lint.log` |
| Initial relocated dependency build | FAIL | 1 | `raw/resumed/build.log` |
| Production build after package layout correction | PASS | 0 | `raw/resumed/build-retry.log` |
| Pinned actionlint six configured workflows | PASS | 0 | `raw/resumed/workflows.log` |
| Stage B unit tests | PASS | 0 | `raw/resumed/stageb.log` |
| Resumed release attempt | FAIL | 1 | `raw/resumed/release.log` |
| Current-baseline release/browser retry | PASS | 0 | `raw/resumed/release-retry.log` |
| Resumed V1.6 attempt | FAIL | 1 | `raw/resumed/v16.log` |
| Current-baseline V1.6 retry | PASS | 0 | `raw/resumed/v16-retry.log` |

Backend: **552 passed, 0 failed, 0 skipped** (`regressions/backend-full.log`). Actual pinned Contrib v0.123.0 was re-extracted from immutable image e39311df1f3d941923c00da79ac7ba6269124a870ee87e3c3ad24d60f8aee4d2 and SHA-256 verified as 6bca4ddd928b4b0880f7ec6c16511922f740c497b4efa4b33915b2d54a729213. No collector upgrade/qualification claim.

Frontend: **38 passed, 0 failed, 0 skipped**. Stage B: **12 passed, 0 failed**; no deployment performed. Build/lint are command outcomes, not testcase counts. Workflow checker covers its six named workflows; it is not a blanket security certification of all workflow files.

PostgreSQL fresh upgrade, populated preservation, provider/infrastructure unit probes and Python compile passed; exact commands/exit codes, image identity and scoped cleanup in `raw/resumed/regressions/results.json`. `preservation.json` records per-table hashes and legacy record protection. Release runner independently performs encrypted/populated dump/restore, retention and negative recovery checks when its full run passes.

## Historical executions retained (2026-10-29)

At b4d5010d482781f4032073b90c4d795356190906: release harness PASS, 67 HTTP checks, 17 removal-browser checks, 7 new profile/Help/incident browser groups. Independently committed 61 incident IDs reconcile across real pages, filter reset and tenant/permission denial. Logs/screenshots in `raw/release/`; source SHA recorded in cleanup.json. New browser groups are grouped assertions, not 7 unit test functions.

Architecture at 270a13ae2355c3d778e69f8c3289a25eb0f06d76: API/engine/browser PASS, five Access browser cases, draft resume/stale protection and readiness refusal; raw/arch2. Ten-stage screenshots are historical after #74, not current eight-stage acceptance. The optional ARCH001_RUNTIME_ACCEPTANCE mode was NOT RUN.

Failed attempts retained: initial Alerts accessible label timeout (fixed); initial architecture DB readiness failure (no browser assertions reached); V1.6 768px header overflow (fixed); new incident test expected 404 from a role correctly denied 403 (test corrected, added authorized-role cross-tenant 404 assertion). Paths raw/attempt1, raw/arch-attempt1.*, raw/v16-attempt1, raw/release-attempt3.

Unfinished late-October final runs lost /tmp during environment resume: **NOT TESTED**, no completion inferred. Current resumed release failure is ENOSPC at evidence output; resumed V1.6 attempt passed HTTP groups then failed build due to this task's temporary dependency relocation. Failure logs retained separately; retry outcomes above.

## Reproduction

Use a fresh disposable evidence directory and local Docker socket only. Never use live UAT or production. Sequential Docker runs avoid VFS disk pressure. PostgreSQL image is postgres:17-alpine, owned tmpfs data, loopback/private fixtures. Toolchain: Python 3.12, Node 24, system Chromium, Playwright 1.56.1; dependency versions from tracked lockfiles. No real customer endpoints or credentials.

```sh
export DOCKER_HOST=unix:///var/run/docker.sock
unset DOCKER_CONTEXT DOCKER_TLS DOCKER_TLS_VERIFY DOCKER_CERT_PATH
export OPSCONTROL_OTEL_BINARY=/path/to/hash-verified-0.123.0/otelcol-contrib
export PLAYWRIGHT_MODULE=/path/to/playwright/index.mjs
export PLAYWRIGHT_CHROMIUM_EXECUTABLE=/usr/bin/chromium
SCOPE_EVIDENCE_DIR=/tmp/new-scope-evidence backend/.venv/bin/python scripts/scope-removal-regressions.py
RELEASE_EVIDENCE_DIR=/tmp/new-release-evidence RELEASE_BROWSER_ACCEPTANCE=1 backend/.venv/bin/python scripts/release-acceptance.py
V16_EVIDENCE_DIR=/tmp/new-v16-evidence V16_API_ACCEPTANCE=1 V16_BROWSER_ACCEPTANCE=1 V16_PENTAHO_R1_ACCEPTANCE=1 V16_PENTAHO_REVIEW_ACCEPTANCE=1 V16_PENTAHO_HISTORY_ACCEPTANCE=1 V16_PENTAHO_INCIDENT_ACCEPTANCE=1 V16_SPRINT07_ACCEPTANCE=1 V16_SPRINT08_ACCEPTANCE=1 V16_SPRINT09_ACCEPTANCE=1 V16_SPRINT13_RECOVERY=1 backend/.venv/bin/python scripts/v16-acceptance.py
npm --prefix frontend test
npm --prefix frontend run lint
npm --prefix frontend run build
bash scripts/check-workflows.sh
backend/.venv/bin/python -m unittest discover -s scripts/uat -p test_stage_b.py -v
```

No genuine Windows/EC2/Pentaho provider certification, live WAL/PITR/DR, owner UAT, production capacity benchmark, CHK queue/rollback qualification or deployment was executed. These remain BLOCKED/NOT TESTED, independently of suite success. Hosted CI is recorded separately at the final PR head, not inferred from local tests.

## Final V1.6 outcome

Retry exit 0: eight-step actual browser flow PASS; Sprint 07 17 browser groups; Sprint 08 5 browser groups and 14 HTTP groups; Sprint 09 3 browser groups, 6 HTTP groups and 9 PostgreSQL resilience scenarios. Synthetic Pentaho suites and additive migration/ownership/recovery checks pass. Full raw outputs: raw/resumed/v16-final; failure attempts retained separately. These groups overlap other suites and are not summed into a fictitious total.

Current release retry exit 0: 67 scope HTTP assertions, 17 removal-browser checks and 7 full-closure browser groups; inspect individual JSONs for exact claims. Verified populated dump/restore and negative recovery. Current cleanup: CLEANUP.json and raw/resumed/release-final/cleanup.json.
