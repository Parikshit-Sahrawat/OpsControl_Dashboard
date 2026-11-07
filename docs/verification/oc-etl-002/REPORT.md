# OC-ETL-002 — Workflow/Job scope repair

Branch: `dev/post-pr78-architecture-closure-20261105`; PR #80 remains draft. Original inspected source: `e69528ad2b826398474382f34126feeca740f6a6`. Architecture baseline commit: `092ed07` (full identity in git history). Product/test implementation and exact final PostgreSQL test source: **`a590f426ff6ed679968688ea9486c70456cf6cc2`**. Subsequent evidence/CI wiring changes add no product behavior; a test import comment explains its necessary hook-registration side effect.

## Root cause and minimal repair

The workflow and dependency models were not in `security/scope.py::_PATHS`. The existing before_flush hook therefore rejected their writes even after route-level `etl.configure` succeeded. Mocked route tests skipped the actual request-session boundary.

- `backend/app/models/entities.py`: view-only Organization/Workflow relationships support the existing organization traversal. These relationships cannot mutate ownership FKs.
- `backend/app/security/scope.py`: register both models; preserve deny-by-default. Validate workflow/job customer and environment, dependency endpoints in the same workflow, self-edge refusal, immutable workflow/endpoint/customer IDs, and refusal to change a populated workflow's environment. Existing transactional audit remains active.
- `backend/app/security/resource_scope.py`: resource/environment-limited users must see every child job resource to see a workflow. Empty/unbound workflows fail closed under restrictions. Dependencies require workflow and both endpoint visibility. Existing other resource rules remain intact.
- `backend/tests/test_etl_workflow_scope.py`: 19 new tests execute actual SQLAlchemy scoped sessions, commit hooks and real authenticated HTTP; no hook mocks.
- `scripts/etl-scope-acceptance.py`: task-owned PostgreSQL, fresh real migrations, ORM schema check, loopback API, sanitized logs and finally cleanup.
- `.github/workflows/pipeline-v16.yml`: invokes that dedicated harness and retains its artifacts, so the guarded integration class is not silently skipped by ordinary CI discovery alone.

No schema revision rewritten, new schema added, production/UAT accessed or collector guard changed. No permissions added to global allowlists and no write hook bypassed.

## Actual results

| Execution | Results | Evidence |
|---|---|---|
| Pre-fix actual in-memory request hook | Both new models denied HTTP 403 even for admin; reproduced integration defect | ../../architecture/unified-implementation-baseline/evidence/workflow-scope-probe.json |
| Attempt 1 | 76 tests: 58 passed, 18 errors; fixture organization/role names violated existing uniqueness | attempt-1/regressions.log; migration and schema checks passed |
| Attempt 2 | 76 tests: 75 passed, 1 failed; test incorrectly assumed existing JobOrder hooks did not create canonical resource bindings | attempt-2/regressions.log; HTTP already passed |
| Attempt 3 | 77 passed, 0 failed, 0 skipped | attempt-3/regressions.log |
| Final committed source | **77 passed, 0 failed, 0 skipped** | final/regressions.log; final/RESULTS.json |
| Authenticated HTTP | **21 expected status assertions passed** within the new regression class | final/http-results.json |
| Migration | Fresh upgrade through 0039 and `alembic check` passed | final/migration-upgrade.log; final/migration-model-check.log |
| Workflow syntax/static | Six configured workflows pass pinned actionlint; Python compile passes | workflow-validation.log/.exit; compile.log/.exit |
| New fixture/harness lint | Initial F401 for intentional app.main side-effect import; explicit explanation added, final lint PASS | focused-lint.log; focused-lint-final.log |

The 77 tests comprise 19 new scope tests, 16 existing foundation tests, 22 existing Sprint 08 RBAC tests and 20 existing Pentaho incident tests imported by that suite. HTTP checks are part of the 19, not 21 additional unit tests. No assertions weakened. The test expectation correction adds explicit empty-workflow, denied-environment and partially visible child cases.

HTTP proves administrator workflow creation, scoped editor workflow edits and job creation/updates, dependency creation, viewer reads, monitoring projection, role-denied mutation, cross-customer workflow/job/dependency refusal, same-customer wrong-workflow refusal, ordinary cycle refusal, inactive workflow activation refusal and anonymous denial. ORM commits independently prove immutable owners/parents/endpoints, missing parent rejection, FK rejection, audit persistence/rollback and existing VM/customer isolation.

## Reproduce

```sh
ETL_SCOPE_EVIDENCE_DIR=/tmp/oc-etl002-new \
  backend/.venv/bin/python scripts/etl-scope-acceptance.py
bash scripts/check-workflows.sh
backend/.venv/bin/ruff check backend/tests/test_etl_workflow_scope.py scripts/etl-scope-acceptance.py
```

PostgreSQL `postgres:17-alpine`, immutable image ID and exact commands/exit codes are recorded in final/RESULTS.json. Harness pins the local Docker socket, random task name, loopback service ports and tmpfs database. HTTP uses synthetic short-lived users and credentials only. A framework `Session` without a request principal remains the pre-existing trusted CLI/worker path; this task does not claim new DB-level composite tenant constraints against unrestricted direct SQL.

## Cleanup and residual boundaries

All four runs stopped their API and removed their own database container; final remaining_container=false, api_stopped=true, cleanup_exit=0. No named data volumes or broad cleanup. Synthetic passwords/tokens were not published.

- **CF-01 scope integration repaired and controlled verification PASS.** Owner review remains pending; this is not full ETL architecture acceptance.
- Resource-limited creation of an empty workflow remains deliberately denied until resource authority can be established. No grant expansion or global bypass. Broader initial-creation semantics require explicit policy; unsupported path remains BLOCKED.
- Legacy job reassignment and dependency endpoint mutation remain forbidden; this task does not introduce a new dependency-update route or destructive data reassignment. Workflow and Job updates use existing PATCH routes.
- Concurrent DAG-cycle race (CF-03) is NOT TESTED by this task; sequential cycle denial is tested. Populated downgrade safety (CF-02) is still BLOCKED, and no populated downgrade was run. Do not infer these are fixed by successful fresh migration.
- Source polling, event lifecycle, genuine providers, licensing and unknown journey decisions remain as in the architecture baseline. No genuine provider certification.

**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.** No merge, deployment, waiver or branch-protection change.
