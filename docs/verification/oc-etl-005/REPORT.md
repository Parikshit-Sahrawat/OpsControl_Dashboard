# OC-ETL-005 — native binding and authoritative readiness contract study

Date: 2026-11-06 UTC. Branch dev/post-pr78-architecture-closure-20261105, draft PR80. Verified clean product baseline `9c021bbb94de3017bdc9f41b6a774d7b378ae9a7`. Test-only increment and exact committed-source PostgreSQL run: **`3852c8d81f6fad4628c30f3cd0f8adaea6dc52f7`**. Final evidence commit adds the proposed contracts, references and traceability; it adds no application behavior.

**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**

## Outcome and implementation boundary

Delivered [native binding contract](../../architecture/etl/OC_ETL_005_NATIVE_BINDING_CONTRACT.md), [readiness contract](../../architecture/etl/OC_ETL_005_READINESS_CONTRACT.md), and [decision/security register](../../architecture/etl/OC_ETL_005_DECISION_REGISTER.md). New storage/command/state/cardinality choices are PROPOSED / PENDING accountable approval, not silently approved requirements. The technical security review records current mitigations, actual negative tests and remaining design blockers; independent accountable security/architecture/database/provider approval remains pending.

No product handler, frontend, model, migration, permission, collector pin, provider adapter or activation behavior changed. Only a test module plus its entry in the existing owned-PostgreSQL harness were added. PROTECTED_SOURCE_SHA256.json compares application, migrations, Agent and prior guard/test bytes with baseline. No speculative provider call or new orchestration engine exists.

## Implemented contract found

The existing indirect chain is PipelineJob.resource_id → MonitoringResource.job_order_id → JobOrder.workflow_id. Registration with an existing Workflow child's Resource can stage a native candidate under **LEGACY_PENDING / quarantined / unselected**, with current scope and identity conflict checks. Method association separately stamps the locked source generation and actor. This is more existing support than a direct WorkflowJob field inventory reveals; it does not make G3 complete.

Current reviewed source handoff and activation machinery already provide independent-review, generation/fence, reader/capability, hold/continuity and recent-resource evidence gates. They are not a generic temporal native-binding replacement or aggregate Workflow activation contract. No new Workflow ACTIVE state is served. Current OC-ETL-004 BLOCKED/UNVERIFIED and supported-child-runtime-only metadata remain untouched.

A confirmed limitation: current association DELETE removes the link row. The test independently proves that canonical history and old-generation quarantined evidence remain, but does **not** assert that a complete historical binding tuple survives. The stronger provenance/cardinality/replacement/hold contract requires D01/D02/D06 review and a forward-additive design. This is an open design/security blocker, not a waived guarantee or a claim that raw receipt history was lost.

## Actual tests

PostgreSQL: `PostgreSQL 17.11 on x86_64-pc-linux-musl, compiled by gcc (Alpine 15.2.0) 15.2.0, 64-bit`. Exact local image identity is in final/RESULTS.json. The fixture uses disposable PostgreSQL Docker/tmpfs plus owned loopback API/Vite and Chromium; no production, owner UAT, customer endpoint or genuine provider target was accessed.

| Execution | Actual result | Evidence |
|---|---|---|
| New current-contract test | 1 PASS containing **36 authenticated HTTP status assertions** | final/native-binding-contract-results.json; final/regressions.log |
| Retained OC-ETL-002/003/004 lab plus new test | **86 PASS, 0 failures/errors/skips** | final/regressions.log; source SHA and cleanup in final/RESULTS.json |
| Existing actual browser | **19 groups PASS** included in the retained lab | final/workflow-browser-results.json, workflow-browser.log, screenshots |
| Existing migration/preservation/actual dump-restore | **6 groups PASS** | final/rollback-results.json; refused-downgrade logs and synthetic backup |
| Existing scope HTTP assertions | **21 PASS**, included in retained tests | final/http-results.json |
| Existing DAG/authorization concurrency cases | **7 PASS**, included in retained tests | final/regressions.log and persisted graph/lock JSON |
| New test/harness Black/Ruff/compile | PASS | black.log; ruff-check.log; validation |
| All attempts scoped teardown | No owned container left, API/UI stopped | per-attempt RESULTS.json |

Counts overlap; do not sum browser groups, assertions and test cases as unique tests. No new production functionality was implemented; verified behavior is the existing staged path and existing source/authorization lifecycle only.

### Tested versus blocked qualification

| Required area | Actual observation | Qualification |
|---|---|---|
| Correct binding | FK-resolved Resource/Job/Workflow chain, native candidate UUID, quarantined/unselected state and unchanged target | PASS **staged structural path**, not full confirmed/versioned native binding |
| Duplicate/conflicting binding | Exact operation retry retains UUID; different-operation native duplicate409; known configured native conflict409; failed operation absent from DB | PASS current constraints/rollback; future concurrent temporal-owner registry BLOCKED |
| Tenant/environment | Foreign Resource404 and wrong-environment Resource422; header cannot widen editor directory | PASS current actual HTTP denial |
| Revocation | Editor can register a draft, actual authenticated role PATCH removes etl.configure, same session write403 and no revoked candidate persists | PASS; no mocked authorization |
| Missing/stale source | Missing resource verification not ready, integration/resource activation409; reviewed handoff makes old generation association stale and blocks activation | PASS current missing/generation gates. New clock/policy aggregate and genuine active-positive source qualification NOT TESTED/BLOCKED |
| Replacement | Distinct reviewer approval required for **existing source** change; source generation changes and old association remains stale before removal | PASS existing source handoff only. New atomic native-target replacement NOT IMPLEMENTED / BLOCKED |
| History/evidence | Canonical receipt hash identical; old quarantined PipelineEvidence retained after generation change/removal | PASS receipt preservation; complete temporal binding provenance is a KNOWN GAP because association row is deleted |
| Audit/transaction | Association removal domain audit event exists; failed duplicate operation not persisted; history unchanged | PASS current checks; complete immutable before/after registry/audit contract D06 pending |
| Activation prerequisites | Quarantined selection409; absent/unverified source/profile and post-handoff activation409; Workflow remains BLOCKED/UNVERIFIED | PASS negative gate behavior; no simulated certification or successful new Workflow activation |
| Monitoring-only | Only config/staging/verification/source-review/role calls; no provider reads or workload control; synthetic metadata stays unverified | PASS bounded path; proposed broader contracts not qualified |

## Commands and failed attempts

From repo root with installed locked dependencies and existing pinned browser tools:

```sh
ETL_WORKFLOW_UI_ACCEPTANCE=1 PLAYWRIGHT_MODULE=/tmp/oc-closure-tools/node_modules/playwright/index.mjs PLAYWRIGHT_BROWSERS_PATH=/tmp/oc-etl003a-browsers ETL_SCOPE_EVIDENCE_DIR=/tmp/etl005-final backend/.venv/bin/python scripts/etl-scope-acceptance.py
backend/.venv/bin/black --check backend/tests/test_etl_native_binding_contract.py scripts/etl-scope-acceptance.py
backend/.venv/bin/ruff check backend/tests/test_etl_native_binding_contract.py scripts/etl-scope-acceptance.py
backend/.venv/bin/python -m compileall -q backend/tests/test_etl_native_binding_contract.py scripts/etl-scope-acceptance.py
```

First static check found an unused fixture result; the test now verifies that persisted editor-created candidate. Attempt1: 86 cases, 85 PASS +1 failure because the fixture sent Pentaho connection base_url instead of its approved url field. Source inspection corrected the fixture; no endpoint schema/assertion was relaxed. Attempt2:86 PASS /19 existing browser groups on the uncommitted test increment. Final:86 PASS /19 groups at committed `3852c8d81f6fad4628c30f3cd0f8adaea6dc52f7`, exit0. All raw attempts and cleanup retained. No failure became a skip or fabricated PASS.

The new test guards ENVIRONMENT=test, explicit owned-lab flag, task container provenance and loopback API before seeding. Fixtures use synthetic IDs/credentials and no runtime-verified capability proof. Real authenticated routes enforce their normal hooks, permissions and transaction boundaries. The private browser credential fixture is removed by its existing context manager; exported JSON contains no bearer credentials. Finally cleanup removes only the exact random owned container and API/UI processes; no broad Docker cleanup.

## Contracts, review and remaining authority

D01/D02: representation/cardinality/identity and immutable parent rules. D03: six authoritative dimensions and aggregate monitoring-only activation. D04: least-privilege/independent approval actions. D05: explicit versioned freshness/clock basis. D06: temporal history, cutover/in-flight routing, holds and additive migration. D07/D08: exact recurrence/calendar and long-running override authority. D09: separately authorized genuine exact-build provider verification. D10: unchanged independent release gates. Every request has options, recommendation, owner roles and acceptance prerequisites in the decision register; no signoff inferred.

G1–G6 are classified explicitly. Existing staging is approved-contract-compatible and verified; new confirmed binding, temporal replacement/retirement and full Workflow readiness remain BLOCKED pending the relevant decisions and provider evidence. No schema migration is proposed as already reviewed or reversible; unsafe populated downgrade and older-application limitations remain those of OC-ETL-003 until a new reviewed migration is tested.

The 31 included journeys, 30 SOURCE_NOT_RECOVERED numbered definitions, excluded Journey20 and skipped Journey32 remain unchanged. Nine prior owner approvals remain OWNER_APPROVED_CONTROLLED_SCOPE — INDEPENDENT_UAT_PENDING. No new ETL owner acceptance, independent UAT, provider certification, legal clearance, security waiver or release acceptance follows from this study.

Final-head hosted CI conclusions will be recorded in the PR80 closure comment after the documentation/evidence commit. Local PASS is not reported as hosted PASS. Recommended next task is accountable review/selection of D01–D06, followed only by the approved additive binding/schema/command implementation and its full PostgreSQL/receipt/cutover tests. No merge or deployment.
