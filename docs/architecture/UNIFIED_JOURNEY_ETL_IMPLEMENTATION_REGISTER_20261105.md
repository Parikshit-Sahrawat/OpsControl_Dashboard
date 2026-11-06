# OpsControl — Unified Journey 1–33 + ETL Implementation Register

Status: **scope approved; implementation and evidence reconciliation in progress**.
Authority: approved OpsControl Dashboard Journey 1–33 roadmap **plus** the approved ETL monitoring architecture. This register is a tracking instrument, not a declaration that any journey is implemented or accepted.

## Scope rules

- Include approved Dashboard Journeys **1–19, 21–31, and 33** (31 journeys).
- **Journey 20: Service Catalog — excluded**. **Journey 32: Kubernetes / Container Observability — skipped/not approved**. Do not implement either without a separate architecture decision.
- Journey 33: Product Lifecycle & Licensing — track LIC-001 through LIC-008, including unresolved evidence and acceptance gates.
- ETL v1.6/v1.7 is monitoring-only: observe externally scheduled work; never dispatch, schedule, retry, or terminate external jobs.
- Link duplicate requirements between roadmaps rather than duplicating implementation or counting them as independently accepted.
- A journey is **verified** only after code mapping, focused tests, integration/UAT evidence, owner acceptance, and required security/reliability gates. No unsupported PASS claims.

## Reconciliation ledger

| Journey | Architecture authority | Implementation evidence | Verification | Owner acceptance |
|---|---|---|---|---|
| 01 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 02 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 03 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 04 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 05 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 06 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 07 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 08 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 09 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 10 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 11 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 12 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 13 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 14 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 15 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 16 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 17 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 18 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 19 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 20 | EXCLUDED — Service Catalog | Out of scope | N/A | N/A |
| 21 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 22 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 23 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 24 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 25 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 26 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 27 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 28 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 29 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 30 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 31 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 32 | SKIPPED — Kubernetes / Container Observability | Out of scope | N/A | N/A |
| 33 | APPROVED — Product Lifecycle & Licensing (LIC-001–008; see detailed requirements below) | Pending code-to-requirement mapping | Not yet verified | Pending |

## ETL architecture delivery matrix

| Capability | Evidence to inspect | Status |
|---|---|---|
| Workflow → Job ownership, configuration, activation | ETL API, schemas, migration 0039, frontend | Partial; tests not yet certified |
| Read-only native execution evidence | persisted execution histories, provider collectors | Partial |
| Source polling / overlapping scans / checkpoint safety | collector/runtime and PostgreSQL acceptance | Not certified |
| Job events and workflow lifecycle | native monitoring engine | Pending reconciliation |
| Workflow SLA, expected windows, missing/late/incomplete runs | evaluation service and tests | Pending |
| Dependency DAG and violation detection | dependency APIs and event evaluator | Partial |
| Evidence correlation and alert separation | correlation and incident services | Partial |
| Operational React UI | workflow/job screens and monitoring integration | Pending |
| Authenticated UAT and genuine Pentaho certification | UAT evidence | Pending / blocked |
| Settings and remaining approved journeys | requirement register, backend and frontend | Pending reconciliation |

## Execution policy

- Implementation-first development with logical commits and focused tests. Full 13-workflow CI reconciliation at implementation milestones.
- Preserve tenant isolation, RBAC, migration compatibility, idempotency, and durable PostgreSQL acceptance semantics.
- Preserve all existing security and release controls; no merging, deployment, waivers, or branch-protection changes without separate authorization.
- Current release posture: **CHK-001 FAIL; CHK-002 BLOCKED; SECURITY BLOCKED; RELEASE NO-GO**.

## Next evidence tasks

1. Locate the exact signed-off Journey 1–33 requirements and ETL decision register; replace placeholder authority text with precise requirement IDs and source links.
2. Trace each requirement to implementation files, tests, UAT evidence, and responsible owner.
3. Identify shared ETL/journey requirements, dependencies, gaps, and safe implementation sequencing.
4. Implement and test missing scope in reviewable commits; record failures rather than converting unverified work into PASS.
5. Complete milestone-level CI, migration, authenticated UAT, reliability and security acceptance before requesting merge.

## Source-grounded requirements and evidence trace (2026-11-05)

**Authority limitation:** The exact signed-off descriptions for Journeys 01–19 and 21–31 are not present in the inspected repository sources or recovered conversation context. Their numbered ledger entries remain intentionally unresolved. Do **not** infer that canonical requirement IDs below correspond one-to-one with journey numbers. The rows below are precise source-grounded requirements, not fabricated journey allocations.

### Journey 33 — Product Lifecycle & Licensing (approved design, not verified implementation)

| Decision | Approved requirement | Implementation reference | Test evidence | Gap / owner acceptance |
|---|---|---|---|---|
| LIC-001 | Versioned editions and entitlements | Not mapped | No verified test | Pending implementation mapping; owner acceptance pending |
| LIC-002 | Signed entitlements bound to deployment identity | Not mapped | No verified test | Cryptographic and identity contract unverified; owner acceptance pending |
| LIC-003 | Offline entitlement verification | Not mapped | No verified test | Offline/expiry/replay proof missing; owner acceptance pending |
| LIC-004 | Safe grace periods and restrictions | Not mapped | No verified test | Grace and non-destructive restriction semantics unverified; owner acceptance pending |
| LIC-005 | Certified releases and compatibility | Not mapped | No verified test | Certification and compatibility evidence missing; owner acceptance pending |
| LIC-006 | Governed upgrades and recovery | Not mapped | No verified test | Rollback/recovery proof missing; owner acceptance pending |
| LIC-007 | Guided onboarding and verified telemetry | Not mapped | No verified test | End-to-end onboarding evidence missing; owner acceptance pending |
| LIC-008 | Licensing RBAC, tenant isolation and audit | Not mapped | No verified test | Negative security/audit proof missing; owner acceptance pending |

Journey 33 review recorded 28 unverified gates and LIC-029–050 open gaps; these remain unresolved, not passed.

### ETL v1.6/v1.7 — exact requirement-level trace

The starting authority is [ETL gap matrix](ETL_V16_V17_IMPLEMENTATION_GAP_MATRIX_20261105.md), [approved Pentaho architecture](ARCH_ETL_001_V16.md), and the PR #80 changes. References are source/test locations to inspect; existence is **not** execution evidence.

| ID | Approved requirement | Code / source reference | Test or historical evidence reference | Remaining gap |
|---|---|---|---|---|
| ETL-01 | Workflow → Job hierarchy | backend/app/models/entities.py; backend/migrations/versions/0039_etl_workflow_foundation.py; backend/app/api/etl.py | backend/tests/test_etl_workflow_foundation.py | Partial; no certified migration/UAT |
| ETL-02 | Workflow owns expected windows, calendar and SLA | backend/app/schemas/etl.py; backend/app/api/etl.py | backend/tests/test_etl_workflow_foundation.py | Partial; legacy JobOrder policy still present |
| ETL-03 | Job owns expected duration, not workflow timing | backend/app/schemas/etl.py; backend/app/api/etl.py | backend/tests/test_etl_workflow_foundation.py | Partial; legacy job-order schema still permits schedule/SLA |
| ETL-04 | Workflow job dependency DAG | backend/app/models/entities.py; backend/app/api/etl.py | backend/tests/test_etl_workflow_foundation.py | Partial; runtime violation evaluator missing |
| ETL-05 | Native execution identity and attempts | backend/app/models/entities.py; backend/app/api/etl.py | docs/architecture/ARCH_ETL_001_V16.md | Unverified native row-key/retry semantics |
| ETL-06 | Oracle/MSSQL/log evidence | backend/app/data_pipelines/service.py | docs/architecture/ETL_V16_V17_IMPLEMENTATION_GAP_MATRIX_20261105.md | Oracle genuine provider certification missing |
| ETL-07 | RUNNING to terminal same-row update | backend/app/data_pipelines/service.py; backend/app/data_pipelines/models.py | docs/architecture/ETL_V16_V17_IMPLEMENTATION_GAP_MATRIX_20261105.md | Active-run overlap/checkpoint unverified |
| ETL-08 | Actual elapsed job long-running event | backend/app/models/entities.py; backend/app/api/etl.py | docs/architecture/ETL_V16_V17_IMPLEMENTATION_GAP_MATRIX_20261105.md | Event correctness and freshness unverified |
| ETL-09 | ETL event rules distinct from alert rules | backend/app/worker/alert_engine.py | docs/architecture/ETL_V16_V17_IMPLEMENTATION_GAP_MATRIX_20261105.md | Missing independent ETL event layer |
| ETL-10 | Template → Workflow → Job policy inheritance | backend/app/models/entities.py; backend/app/worker/alert_engine.py | docs/architecture/ETL_V16_V17_IMPLEMENTATION_GAP_MATRIX_20261105.md | Missing verified effective-policy resolution |
| ETL-11 | Workflow and job event catalog | backend/app/api/etl.py; backend/app/worker/alert_engine.py | docs/architecture/ETL_V16_V17_IMPLEMENTATION_GAP_MATRIX_20261105.md | Incomplete event catalog |
| ETL-12 | Normal/Pending/Firing/Recovered; stale orthogonal | backend/app/worker/alert_engine.py | docs/architecture/ETL_V16_V17_IMPLEMENTATION_GAP_MATRIX_20261105.md | Lifecycle state separation unverified |
| ETL-13 | Email/PagerDuty/ServiceNow idempotent routing | backend/app/worker/alert_engine.py | docs/architecture/ETL_V16_V17_IMPLEMENTATION_GAP_MATRIX_20261105.md | ETL-specific delivery/correlation unverified |
| ETL-14 | Durable replay and atomic acceptance | docs/verification/stage-2a-full-development-closure/FINAL_REQUIREMENTS_MATRIX.md | TEL-03; CHK-001/CHK-002 gates | Blocked: CHK-001 FAIL; CHK-002 BLOCKED |
| ETL-15 | Workflow/Job configuration UI | frontend/src/pages/ETLJobs.jsx; backend/app/api/etl.py | frontend/scripts/etl_filters.test.mjs | Workflow editor missing |
| ETL-16 | Tenant isolation and monitoring-only | backend/app/api/etl.py; backend/app/security/access_control.py | backend/tests/test_etl_workflow_foundation.py | Negative DB/API integration not certified |

### Cross-cutting canonical requirements: traceable existing register

Source: [final requirements matrix](../verification/stage-2a-full-development-closure/FINAL_REQUIREMENTS_MATRIX.md). The statuses there are historical, not newly executed tests. Every active item below retains **owner acceptance pending**.

| Canonical ID | Exact requirement | Code reference | Named test/evidence | Gap / acceptance |
|---|---|---|---|---|
| RM-01 | Customer Organizations distinct from provider Departments | backend/app/api/organizations.py; backend/app/security/scope.py | backend/tests/test_sprint08_rbac.py | Independent UAT; pending owner |
| RM-04 | Collector configuration supports multiple independently added methods | backend/app/telemetry/api.py; frontend/src/pages/CollectorControl.jsx | backend/tests/test_managed_telemetry.py | Method attribution and genuine agent; pending owner |
| RM-05 | Method-specific canonical collection identity and one fenced active owner | backend/app/telemetry/api.py; backend/app/telemetry/models.py | backend/tests/test_managed_telemetry.py | Concurrency/fencing negatives; pending owner |
| AM-01 | Employees, Departments, inherited/direct roles, customer-scoped RBAC | backend/app/api/access.py; backend/app/security/access_models.py | backend/tests/test_sprint08_rbac.py | Independent authorization UAT; pending owner |
| CMP-01 | Windows/Linux VM/EC2 native operational health | backend/app/models/entities.py; backend/app/worker/collector_runtime.py | backend/tests/test_infrastructure_health_projection.py | Genuine telemetry UAT; pending owner |
| SET-01 | Profile, account security, display and notification preferences | frontend and backend settings routes require exact file mapping | FINAL_REQUIREMENTS_MATRIX.md | Partial; editable contract unresolved; pending owner |
| SET-02 | Admin platform settings, safe persistence and audit | No verified implementation | FINAL_REQUIREMENTS_MATRIX.md | Not implemented; authority pending; pending owner |
| TEL-03 | Durable ingestion, backpressure, replay and loss accounting | Collector runtime and PostgreSQL design require reconciliation | CHK-001; CHK-002 | Blocked; pending owner |
| DP-01 | Read-only Pentaho outcome, health, identity and evidence | backend/app/data_pipelines/service.py; backend/app/api/etl.py | ARCH_ETL_001_V16.md | Genuine Pentaho certification pending |
| PLT-03 | Security, residency, legal holds and retention | Security/release source review required | FINAL_REQUIREMENTS_MATRIX.md | BLOCKED_SECURITY; pending owner |

For the **nine individual owner acceptance cases**, use [OWNER_ACCEPTANCE_CASES.md](../verification/stage-2a-full-development-closure/OWNER_ACCEPTANCE_CASES.md) as the authoritative per-case checklist; do not substitute automated CI or this mapping for a signed owner decision. The table above includes five cases with independently visible source/test mappings; the remaining four must be extracted and linked from that document before declaring the nine-case register complete.

### Reconciliation blockers and next action

1. Recover the original **numbered** Journey 1–33 architecture decision text; only then assign requirements, code, tests and owners to individual J01–J19/J21–J31 rows.
2. Read current branch code and historical test reports for every mapping; record exact SHA, test command, environment, output, and owner decision.
3. Validate migration 0039 and scoped ETL endpoints with disposable PostgreSQL; current focused tests were committed but not executed in this reconciliation.
4. Preserve excluded Journey 20 and skipped Journey 32, plus Kubernetes scope removal.
5. No full acceptance or release qualification is inferred from this document.

## OC-ARCH-001 implementation baseline — 2026-11-05

The [numbered journey matrix](unified-implementation-baseline/JOURNEY_01_33_REQUIREMENTS_MATRIX.md), [complete inherited ETL trace](unified-implementation-baseline/ETL_ARCHITECTURE_IMPLEMENTATION_MATRIX.md), [dependency backlog](unified-implementation-baseline/UNIFIED_IMPLEMENTATION_BACKLOG.md), [conflicts](unified-implementation-baseline/ARCHITECTURE_CONFLICT_REGISTER.md), [tests/acceptance](unified-implementation-baseline/TEST_AND_OWNER_ACCEPTANCE_MATRIX.md) and [execution plan](unified-implementation-baseline/IMPLEMENTATION_EXECUTION_PLAN.md) refine this register at source e69528ad2b826398474382f34126feeca740f6a6 without inventing 30 missing numbered definitions. Journey 20 remains excluded and Journey 32 skipped.

Existing foundation tests actually executed: 16 backend PASS and two frontend source checks PASS. A separate real before_flush-handler probe reproduced 403 rejection for both new ETL models absent from the shared scope registry (CF-01); this is an integration defect, not missing architecture approval. Migration rollback, DAG concurrency, retired notification channel authority and genuine-provider evidence remain separate gaps. No product changes in the OC-ARCH-001 documentation checkpoint; OC-ETL-002 is the explicitly authorized follow-on scope repair.

## OC-ETL-002 scoped persistence integration — 2026-11-05

At product commit `a590f426ff6ed679968688ea9486c70456cf6cc2`, ETLWorkflow and ETLWorkflowDependency are integrated into the existing shared request scope and write hooks, with immutable parent/endpoint IDs, same-workflow/customer/environment validation, full-child resource visibility and transactional audit. [Actual PostgreSQL/HTTP report](../verification/oc-etl-002/REPORT.md): 77 tests passed, including 19 new scope tests and 21 real authenticated HTTP assertions; real fresh migration through 0039 and ORM compatibility passed. Failed fixture attempts are preserved. CF-01's reproduced write-hook defect is repaired, not waived; no global allowlist bypass.

ETL-01/04/16 advance only for scoped persistence, reads and existing updates; their broader lifecycle/UI/concurrency/provider requirements remain PARTIAL. CF-02 populated rollback and CF-03 concurrent DAG race remain open. Resource-limited unbound workflow creation deliberately remains denied. CI runs the new disposable harness, with evidence retained. No owner/provider acceptance or release gate changes.


## OC-ETL-004 — supported Workflow/Job UI verification (2026-11-06)

Implementation `1d3004d`, exact accepted technical source `6a9c7a2cc2eafbac76b6e7b48a54d35c9d115f19`: [evidence](../verification/oc-etl-004/2026-11-06/REPORT.md), [open contracts](../verification/oc-etl-004/2026-11-06/OPEN_GAPS.md). This is controlled verification, not owner acceptance. Historical baseline observations above remain unchanged.

| Requirement | Implemented and verified | Unimplemented/blocked | Acceptance |
|---|---|---|---|
| ETL-02 | Workflow list/create/edit/details, timezone/weekdays/windows/duration/SLA, persisted reload | Frequency/recurrence, detailed calendar and authoritative activation/occurrence semantics G1/G4/G5 | PARTIALLY_IMPLEMENTED; verified supported scope; owner pending |
| ETL-03 | Child name/host/runtime create/edit/reload; immutable parent/customer/environment; legacy unassigned rows preserved | Distinct long-running threshold and native PipelineJob binding G2/G3 | PARTIALLY_IMPLEMENTED; verified supported scope; owner pending |
| ETL-15 | Configuration workspace under Resource Management, directed dependencies, read-only receipt/freshness/readiness projection, tenant guards and failed-save preservation | Full operational Workflow readiness/outcomes and provider connectivity G4/G5/G6 | PARTIALLY_IMPLEMENTED; 19 authenticated browser groups; owner pending |
| ETL-16 | Actual secured APIs and UI role/tenant negatives; retained request hooks/audit/DAG locks; seven concurrency/security regressions | Broader security/release/provider gates remain independent | IMPLEMENTED_VERIFIED for this bounded configuration path; not full ETL acceptance |

85 PostgreSQL/HTTP regression cases pass, 45 frontend cases pass, six migration preservation/recovery groups pass. Exact raw outcomes and cleanup are in the evidence package. Backend configuration validity is explicitly supported-child-runtime-only; BLOCKED activation and UNVERIFIED provider states are not inferred healthy from persistence. All 31 included journeys, 30 SOURCE_NOT_RECOVERED numbered definitions, excluded Journey20 and skipped Journey32 are preserved. Nine prior owner decisions remain OWNER_APPROVED_CONTROLLED_SCOPE — INDEPENDENT_UAT_PENDING; no new ETL approval. CHK-001 FAIL, CHK-002 BLOCKED, SECURITY BLOCKED, RELEASE NO-GO.


## OC-ETL-005 — current native staging and proposed binding/readiness contracts (2026-11-06)

[Native contract](etl/OC_ETL_005_NATIVE_BINDING_CONTRACT.md), [readiness authority](etl/OC_ETL_005_READINESS_CONTRACT.md), [decision register](etl/OC_ETL_005_DECISION_REGISTER.md); [execution evidence](../verification/oc-etl-005/REPORT.md). Product baseline `9c021bbb94de3017bdc9f41b6a774d7b378ae9a7`; test-only source `3852c8d81f6fad4628c30f3cd0f8adaea6dc52f7`. ETL-03/05/14/15/16 and ETL-02 readiness authority reuse the existing resource→Job→Workflow chain and generation-fenced sources. One new current-contract test has 36 real HTTP assertions; full owned lab86 PASS including prior UI19 groups and migration6 groups. No product handlers, permissions, schemas or collector code changed.

Existing indirect native-candidate registration can stage a Workflow child under quarantine; this refines G3 without claiming a complete confirmed/temporal binding. Existing association removal deletes its tuple row while keeping tested history/evidence, so full binding provenance/replacement remains a D06 design blocker. D01–D10 new choices are PROPOSED / PENDING accountable approval. G1/G2 owner-source semantics, G3 temporal design, G4 aggregate activation, G5 lifecycle and G6 independent acceptance/provider evidence remain explicit. Next bounded slice: review D01–D06 then implement only the approved additive contract. No new ETL acceptance; nine prior controlled owner decisions, all31 included journeys,30 unrecovered definitions, Journey20 excluded and32 skipped remain. CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.


## OC-ETL-006 — owner-approved temporal claim registry and six-dimension readiness (2026-11-06)

Owner approval D01–D06 is recorded in `docs/verification/oc-etl-006/APPROVAL_AND_SCOPE.md`; it supersedes prior owner-pending design requests, not independent signoffs. Exact tested source `8e7cdf91d70f19a19c1cdf8d763818446b1c179f`. Additive0040, immutable scoped claim versions/method snapshots and terminal retirement, transactional ownership/authorization, receipt constraints, fail-closed opted-in routing, six backend dimensions and existing Resource Management UI are implemented. 104 PostgreSQL/API regression cases PASS, 9 new +19 retained browser groups, 46 frontend tests, six retained migration groups and actual104-table temporal restore comparison. Counts overlap.

ETL-02 remains PARTIAL (frequency/calendar authority D07). ETL-03 native claim/version/configuration is VERIFIED; qualified authority, positive confirmation and live cutover remain BLOCKED D09. ETL-05/14 receipt constraints/negative attribution verified; new qualified positive receipt routing NOT TESTED. ETL-15/16 supported configuration, saved/reloaded claims/history and six blocked/unverified readiness dimensions VERIFIED; full aggregate ACTIVE/HEALTHY and complete occurrence semantics remain BLOCKED. No acceptance or provider certification inferred.

Next implementation prerequisites: exact D09 authority attestation and qualification; active source handoff/receipt reconciliation; old-writer version fencing/rollback before container deployment. No repeat D01–D06 owner approval is required. D07/D08 and independent UAT remain open. All31 included journeys/30 SOURCE_NOT_RECOVERED numbered definitions, Journey20 excluded and32 skipped, nine previous owner controlled-scope approvals remain unchanged. [Execution, failures, cleanup and limits](../verification/oc-etl-006/REPORT.md) (repository-relative path; see PR80 for exact links). CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.


## OC-ETL-007 — authority verification and database writer fence (2026-11-06)

Exact tested source `2b8eada577d0a56358d599c2f3a5e02d687b30a1`; [report](../verification/oc-etl-007/REPORT.md). Implemented provider-independent signed/native-source envelopes, conditional genuine-attestation confirmation/receipt ownership and a PostgreSQL protocol1 fence. Actual117-case suite PASS, including104 retained +13 new, 23 table-specific refusal branches, two exact older source versions, 107-table restore comparison, four new browser contract/denial groups. Counts overlap. No genuine provider attestation/qualified receipt is seeded; test issuers cannot qualify. Old writers are fenced, not operationally rollback-certified.

ETL-03/05/14 native authority and provenance remain PARTIAL: structural/negative gates verified; qualified positive admission, canonical alias owner conflicts and live/stale-generation handoff BLOCKED. ETL-15/16 current UI/readiness support remains VERIFIED_BOUNDED_SUBSET, activation BLOCKED/health UNVERIFIED without evidence. D01–D06 approval is preserved; user OC-ETL-007 authorizes generic attestation design only, not an exact provider target. No new functional owner acceptance inferred. D07/D08 and independent UAT pending.

Next executable prerequisites: explicit exact-build read-only target + accountable verifier/issuer evidence; qualify confirmation/receipt/expiry/cutover; authority-aware rollback image or tested safe degraded mode before isolated candidate/deployment. 31 included journeys/30 SOURCE_NOT_RECOVERED numbered definitions retained; Journey20 excluded/32 skipped, nine controlled owner decisions unchanged. CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.
