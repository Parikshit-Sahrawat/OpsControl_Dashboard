# PR #41 reconciliation and acceptance ledger

Status: **BLOCKED BY VALIDATION**, development verification in progress. This record does not transfer independent UAT acceptance between revisions. The owner subsequently authorized merging PR #41 with independent UAT retained as future scope; that authorization does not turn missing UAT evidence into PASS or waive the unchanged CI, coverage, security and preservation gates. No production deployment is authorized.

## Source baseline and reconciliation

- Repository: `Parikshit-Sahrawat/OpsControl_Dashboard`; feature worktree `/workspace/scratch/opscontrol-ui-alignment`.
- Feature starting HEAD: `ea456f023e7166e563bf97027750b1bb3aba13ec`. `1379d1d6cd135e51294c3bde80b5fd51b3f807cc` is an ancestor. The one intervening feature commit added guided ETL/API workspaces, browser checks, scalar report-filter compatibility and development evidence.
- Fetched `origin/main`: `4ebd8d8a64dff75ef7577c169c76e651e435dcc7` (Stage B PR #40). It was merged normally into this feature branch as `b4494b7879de2043862e46657b5873d1829c8b88`, with **no conflicts**. Stage B workflows, deployment scripts, evidence and migration/volume safeguards were preserved. No Stage B deployment was run.
- Protected PR #33 was not changed. PR #41 remains draft and unmerged.

## Independent UAT evidence boundary

PR #41's description says the owner reports an UI Alignment UAT PASS. Accessible repository docs, PR comments, GitHub deployment records and Stage B runs do **not** identify an independently tested feature commit, image digests, PostgreSQL revision, environment identity or dated case-level acceptance. Stage B's only visible main-push run was skipped, and its report explicitly says controlled deployment NOT RUN. The current branch is therefore **not INDEPENDENT UAT ACCEPTED** on available evidence. The required immutable-source record has been requested from the owner.

The owner confirmed during this reconciliation that the reported PASS has **unverified deployment provenance**: tested commit, backend/frontend digests, PostgreSQL revision, environment, dated results and independent sign-off have not been established. The owner then explicitly placed independent UAT in future scope while authorizing PR approval and merge. Independent acceptance for the PR head remains pending evidence reconciliation; no acceptance is inferred from the report.

The historical Sprint 14R results supplied for this task are retained as **UAT-01/02/05 PASS; UAT-03/04/06/07/08/09 FAIL**. Their detailed case definitions, source revision, environment and screenshots/logs have not been recovered in accessible repository files or issue #38. No historical result has been rewritten as a pass. Retesting these exact six failures against an accepted Sprint 14R revision requires the missing case-level record and an approved, pinned independent environment; synthetic browser fixtures do not substitute for it.

## Development corrections

- The full populated PostgreSQL acceptance run exposed positional direct-handler regressions after the additive `environments` parameter was inserted into resource and incident inventory signatures. The signatures now keep the original positional arguments and accept the new filter after the database dependency. Direct calls normalize FastAPI's default `Query` sentinel as no explicit list. This retains the additive HTTP filter and fails closed on ambiguous scalar-plus-list requests.
- Previous PR #41 CI failed Black formatting on these two touched API files. Scoped Black formatting was applied; no assertions or coverage thresholds were weakened.
- ETL/API guided forms now block review until the jobchain or valid DNS/port identity is supplied; browser regression assertions cover the blocked paths.

## Gate ledger

| Gate | Result | Evidence and limit |
| --- | --- | --- |
| Stage B state/migration policy unit tests | PASS | `python3 -m unittest discover -s scripts/uat -p test_stage_b.py -q`: 12 tests, 0 failures. No target-host deployment. |
| Workflow schema | PASS | `bash scripts/check-workflows.sh` with network access and repository-pinned actionlint. Initial restricted-network attempt failed connecting to proxy; retry passed. |
| Frontend lint, unit, build | PASS | `npm run lint --prefix frontend`; `npm test --prefix frontend` 5/5; `npm run build --prefix frontend` passed with existing >500 kB chunk warning. |
| Backend unit discovery | PASS | From `backend/`: `ENV=test .venv/bin/python -m unittest discover -s tests -q`: 503 tests, 210 skipped. Initial repository-root invocation failed import resolution and is not counted. |
| Populated PostgreSQL/migration preservation | IN PROGRESS | Disposable `scripts/test-quality.sh pentaho` rerun after direct-handler repair. Its first run failed 3 direct-call cases; preservation probes themselves recorded PASS. Final rerun result must be inserted before merge review. |
| Critical backend coverage >=80% | NOT VERIFIED | Previous unit-only measurement was 45.04%, below threshold. Complete instrumented acceptance and unchanged threshold still required. |
| Browser/responsive/accessibility | PARTIAL | Prior synthetic Chromium 97/97 at development source. New field guards and merged-main candidate require a fresh exact-revision run. Independent assistive-technology review open. |
| Customer isolation/RBAC/operational evidence | PARTIAL | Prior controlled negative and adapter-union tests; final populated PostgreSQL and current-candidate browser checks pending. No live provider certification. |
| GitHub CI for final PR head | BLOCKED | Earlier `ea456f0` PR run includes multiple failures. `verification` failed Black on two touched files (corrected locally); several other jobs report generic acceptance failures and artifacts could not be downloaded from this workspace (403). A new final-head run must be inspected. |
| Independent UAT, historical retest, image/schema provenance | FUTURE SCOPE / NOT VERIFIED | Exact deployment and case evidence absent. Owner-reported PASS cannot be attached to current head; owner explicitly deferred this gate for PR #41 merge, while retaining the historical results. |

Original IMP-001–062 sources remain unrecovered. Genuine Pentaho RT-001–RT-020 remain NOT RUN. Production remains NOT READY.
