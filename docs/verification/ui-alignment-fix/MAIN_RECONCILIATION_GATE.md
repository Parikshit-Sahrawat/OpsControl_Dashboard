# PR #41 main reconciliation gate — 2026-10-21 UTC

**Decision: BLOCKED; PR #41 is not merged.** The owner authorized merge with independent UAT retained as future scope. The separate mandatory CI, coverage, security, preservation, and regression gates have not passed. A complete *post-merge* validation on main cannot be run until the reviewed feature is actually integrated; calling a baseline-main run post-merge validation would misidentify the tested source.

## Immutable source comparison

| Reference | SHA | Evidence |
| --- | --- | --- |
| Current `origin/main` | `4ebd8d8a64dff75ef7577c169c76e651e435dcc7` | `git ls-remote origin refs/heads/main` on 2026-10-21; GitHub quality run 39462642072 concluded success for this SHA. |
| PR #41 pushed head | `11844b35dcca1ab0c6048daba9d08bcbe8919480` | `gh pr view 41 --json headRefOid,statusCheckRollup,mergeStateStatus`; draft, MERGEABLE at Git level but UNSTABLE with failing checks. |
| Feature/main reconciliation | `b4494b7879de2043862e46657b5873d1829c8b88` | Normal merge of main into feature, no conflicts; Stage B changes retained. |

`origin/main` does not yet contain the UI Alignment Fix. Prior green main CI is evidence for the baseline only. PR #33 was not touched. Independent UAT provenance is unverified, as the owner confirmed; it remains future scope and is not counted as PASS.

## Executed local gates

| Gate | Result | Actual execution/evidence |
| --- | --- | --- |
| Frontend lint, five unit suites, production build | PASS | `npm run lint --prefix frontend`, `npm test --prefix frontend`, `npm run build --prefix frontend`; build warns about an existing >500 kB chunk. |
| Backend unit regression | PASS | From `backend`, `ENV=test .venv/bin/python -m unittest discover -s tests -q`: 503 tests, 210 skipped. |
| Stage B deployment policy | PASS | `python3 -m unittest discover -s scripts/uat -p test_stage_b.py -q`: 12 tests; `bash scripts/check-workflows.sh` passed with network-enabled actionlint. No UAT deployment. |
| Populated PostgreSQL/preservation | PARTIAL | `scripts/test-quality.sh pentaho` against disposable PostgreSQL: 503 database-backed tests (2 skips), backup/restore REC-01–06, authenticated HTTP Sprint 03–09 and nine resilience scenarios passed. Backup size 1,468,298 bytes, SHA-256 `e1344059ce6d7748093ed2e01ce2081389411464372235b8d6036ec088de23bf`, backup 0.318 s, restore 0.79 s, migration head `0037_access_boundaries`; populated unsafe downgrade refused and schema drift absent. Whole command exited 1 on stale duplicate-create browser assertion. Focused corrected `scripts/v16-acceptance.py` retry with browser/API/ownership passed. Logs: `/tmp/opscontrol-ui-pr41-quality-r2`, `/tmp/opscontrol-ui-pr41-browser-v16-r2`. Local observations do not establish production recovery. |
| Critical backend coverage | **FAIL** | `OPSCONTROL_TEST_EVIDENCE_DIR=/tmp/opscontrol-ui-pr41-quality-r2 bash scripts/test-quality.sh coverage` measured **64.52%**, below unchanged 80%. |
| Owned runtime E2E | **FAIL / environment unresolved** | `scripts/test-quality.sh e2e` passed mapping preservation, customer/VM/ETL/API onboarding and native/incident/notification groups, then collector-version POST returned 422 instead of 201; diagnostics `/tmp/opscontrol-arch001-6lwnr8kx/failure.log`. The expected real OTel binary `/tmp/opscontrol-otel-bin/otelcol-contrib` was absent locally. The 422 cause needs reproduction with the response body before classifying a product defect. |
| Exact independent UAT | NOT RUN | Owner confirmed deployed SHA, image digests, schema revision, UAT environment and case-level sign-off cannot be established. Owner deferred this gate; no result was transferred to current PR head. |

The prior Sprint 14R historical results remain UAT-01/02/05 PASS and UAT-03/04/06/07/08/09 FAIL **as supplied**, without independently recovered source revision or case evidence. No historical result was rewritten.

## PR CI for `11844b3`

`gh pr view 41 --json statusCheckRollup` showed `verification`, `managed-telemetry-uat`, `etl`, `infrastructure`, `restore-retention-tls`, `access-rbac`, `golden-path`, `real-tls-evidence-alert`, `staging-smoke`, `private-https`, `demo-localhost` and `noc` failing; `native-monitoring` was still running at inspection. Several other jobs passed, including backend/frontend validation, pipeline contracts, network checks and dependency audits. Full CI logs are at GitHub Actions for this exact PR SHA.

Confirmed failures include pinned Prettier rejecting two feature-touched files in quality run `39600652536`; an HTTP golden-path browser selector matching two Data Source controls in run `39600652810`; and a private Carte fixture expecting SUCCESS from incomplete native result evidence in run `39600652600`. The conservative parser correctly returned UNKNOWN, so the expectation must be aligned with native evidence. ETL and infrastructure probe scripts also expect authoritative inventory/success from incomplete synthetic native records. Managed telemetry, access and release jobs reached browser acceptance and failed; their private diagnostic artifacts were not accessible from this workspace, so the precise browser assertion remains unverified. The private real-TLS job failed pulling PostgreSQL 17 from a public registry with a data-limit response. The demo-localhost job reported an empty organization list; root cause remains unverified.

## Remaining work before merge

1. Resolve feature-touched Prettier, current browser/acceptance regressions, and conservative native-evidence probe expectations without weakening security or evidence rules.
2. Reproduce the collector-version 422 with sanitized response details; rerun the owned-lab E2E using the actual digest-pinned OTel binary.
3. Reach the unchanged 80% critical-module coverage and obtain green required CI on an immutable final PR head.
4. Recheck `origin/main` immediately before any integration. Only after all mandatory gates pass should a normal merge occur, followed by targeted tests and CI verification on the resulting main SHA.

No main integration, production deployment, existing UAT volume reset, ETL workload execution, or PR #33 modification occurred. Pentaho RT-001–RT-020 remain NOT RUN; production readiness remains NOT READY.

## Follow-up validation after owner-directed coverage change

The owner explicitly instructed lowering the former 80% floor. The feature branch now proposes a **65%** critical-module minimum in both the quality workflow and local script. The measured instrumented local report was **72.40%**. The subsequent GitHub `verification` job on `c56d818` measured **66.32%** and failed its then-current 70% floor; it would clear the proposed 65% floor. This is a policy change, not an improvement in implementation coverage. The historical 64.52% partial measurement above remains recorded. No other security or CI threshold was reduced.

Focused corrections to legacy probes preserve fail-closed Carte outcomes and partial-inventory coverage, select an explicitly authorized customer in browser tests, and target the approved full-page Compute workspace. On disposable PostgreSQL and controlled Chromium, `ENV=test ACCESS_BROWSER_ACCEPTANCE=1 ... backend/.venv/bin/python scripts/access-acceptance.py` passed 25 access groups and seven browser groups. `ENV=test RELEASE_BROWSER_ACCEPTANCE=1 ... backend/.venv/bin/python scripts/release-acceptance.py` passed its RBAC/tenant, real local TLS, EKS, 205-resource browser pagination, resource CRUD, concurrent administrator, backup/restore and runtime checks. Release evidence: `/tmp/opscontrol-pr41-release-next8`. The restore fingerprint still compares all row hashes and constraint identities; only PostgreSQL's equivalent enum-array cast placement is canonicalized. No persistent UAT or production volume was used.

The two offline Pentaho/provider probes passed after requiring a native result indicator for SUCCESS and retaining UNKNOWN for incomplete evidence. Pinned Prettier, scoped Black/Ruff, frontend lint and build passed locally. Five frontend unit suites passed; 97.40% included-module line coverage is separate from the 72.40% backend critical-module measure. CI on a new immutable head and further owned runtime/browser suites remain required before merge. Independent UAT remains deferred and unverified.

## Subsequent branch validation (still pre-merge)

The controlled Sprint 2 infrastructure suite passed configured, healthy, failed and recovered browser phases, PostgreSQL evidence checks and tenant negatives in `/tmp/opscontrol-pr41-infra-run.log`. The private HTTPS golden path passed configured, healthy, failed and recovered browser phases, TLS probe evidence, scoped onboarding, authorization negatives and network egress denial using a disposable nonconflicting Docker subnet; evidence is in `/tmp/opscontrol-pr41-golden-next5` and `/tmp/opscontrol-pr41-golden-run5.log`. Neither run touched persistent UAT storage. Frontend lint, five unit suites and Vite build passed after restoring registered job-order execution investigation beside the six current operational pipeline pages. `scripts/test-quality.sh quality` passed Black, Ruff, Prettier, ESLint and build. Node/Python syntax checks, `git diff --check`, and `scripts/check-workflows.sh` passed.

The legacy controlled Carte fixture had two invalid assumptions: an empty, incomplete inventory was treated as proof of `NO_RUN`, and a finished job with zero errors but no native result was treated as `SUCCESS`. The probe now requires **no fabricated NO_RUN** from the former; the separate complete-inventory transactional test still checks defensible NO_RUN. The clearly synthetic recovery fixture now carries an explicit native `Y` result. The controlled ETL suite passed all configured, empty-inventory, running, long-running, SLA-breach, failed, poll-failed and recovered browser phases; PostgreSQL, idempotency, tenant, read-only TLS and audit checks passed. Evidence: `/tmp/opscontrol-pr41-etl-run6.log` and `/tmp/opscontrol-pr41-etl-next6`. This does not establish genuine Pentaho RT-001–RT-020 acceptance. New CI on the final branch SHA remains pending, so the merge decision remains **BLOCKED**.
