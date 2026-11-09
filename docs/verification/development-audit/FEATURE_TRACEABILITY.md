# Approved requirement traceability on merged main

Source snapshot `65aa131`. Classification is **source implementation / verification**, not release acceptance. `C` = bounded source COMPLETE, `P` = PARTIAL, `U` = UNKNOWN. `F` = automated fixture or controlled local verification found; `I` = independent UAT accepted for **this exact SHA**. No `I` evidence was established. The owner-reported earlier UI UAT PASS lacks deployed SHA, image digests, schema revision and dated case evidence; it cannot be transferred to merged main. See the [approved UI register](../ui-alignment-fix/source/UI_001_023_REGISTER.md) and [UAT Test 1](../ui-alignment-fix/source/UAT_TEST_1_UI_ALIGNMENT_FIX.txt).

| UI ID | Main implementation path | Source / verification assessment | Required Phase 1 follow-up |
| --- | --- | --- | --- |
| UI-001 | `frontend/src/components/TopNav.jsx`, `navigation.js`, `App.jsx`; `frontend/scripts/navigation.test.mjs`, `ui_recovery_acceptance.mjs` | C/F; I pending | Repeat keyboard/mobile preference checks at candidate SHA. |
| UI-002 | `pages/UnifiedResourceManagement.jsx` grouped component selector | C/F; I pending | Confirm selector/deep link refresh in independent UAT. |
| UI-003 | `UnifiedResourceManagement.jsx:Modal` workspace branch, `ResourceForm` | C/F; I pending | Validate full Compute journey against persisted draft. |
| UI-004 | `UnifiedResourceManagement.jsx` ten `guidedSteps`, `resource-v2.css` | C/F; I pending | Repeat desktop/mobile focus and stepper checks. |
| UI-005 | `visual-system.css`, `resource-v2.css`, page styles | P/F; I pending | Fix any reproduced clipping at 390/768/1366; no universal absence claim from screenshots. |
| UI-006 | `UnifiedResourceManagement.jsx:ResourceForm` conditional VM/API/ETL action rows | P/F; I pending | Verify each step's validation and one primary action; no duplicate visible Next in tested state. |
| UI-007 | `registry/api.py`, `unified/api.py`, `resourceApi.js`, onboarding workspace | P/F; I pending | Reproduce historical Not Found against persisted draft/current customer and assert exact API response before declaring closed. |
| UI-008 | `telemetry/api.py:CollectorMethod`, `pages/CollectorControl.jsx` | C/F; I pending | Validate multiple enabled methods on one VM Agent in independent UAT. |
| UI-009 | `unified/api.py` verification/activate routes, `UnifiedResourceManagement.jsx` | P/F; I pending | Prove backend rejects missing prerequisite and confirms actual readiness before activation. |
| UI-010 | `models/entities.py:Organization`, `security/access_models.py:Department`, Resource/Access views | C/F; I pending | Negative cross-entity/customer UAT. |
| UI-011 | `navigation.js`, Resource Management, `VMHealth.jsx`, `PipelineWorkspace.jsx`, `APIs.jsx` | C/F; I pending | Check no duplicate resource creation in Operations. |
| UI-012 | `theme.js`, `TopNav.jsx`, `visual-system.css`, browser scripts | P/F; I pending | Independent responsive, keyboard, light/dark and reduced-motion review. |
| UI-013 | `UnifiedResourceManagement.jsx` ETL workspace, `DataPipelineIntegrations.jsx` existing-source edit | P/F; I pending | Verify credentials are refs and installed-build capability status is honest. |
| UI-014 | `AccessBoundaries.jsx`, `access-management.css` | C/F; I pending | Independent explicit LIMIT/DENY boundary form UAT. |
| UI-015 | `AccessManagement.jsx`, `access.py:effective`; direct/inherited projection | P/F; I pending | Review effective grant origin legibility and mutation boundaries. |
| UI-016 | `UnifiedOverview.jsx`, `unified/reporting.py:overview` | C/F; I pending | Check zero-data, stale and error states with actual source outage. |
| UI-017 | `VMHealth.jsx`, `DomainMonitoring.jsx`, `reporting.py:domain_state` | C/F; I pending | Real adapter evidence remains separate from registered inventory. |
| UI-018 | `pipelines/PipelineWorkspace.jsx`, `pipelines.css` | C/F; I pending | Retest six-page browser check; merged main CI currently fails it. |
| UI-019 | `APIs.jsx`, `DomainMonitoring.jsx`, `ApiAdapter` | C/F; I pending | Verify observed probe versus configured endpoint in independent UAT. |
| UI-020 | `Alerts.jsx` filter labels/toolbar | P/F; I pending | No full Alerts redesign; only approved label/cross-page scope. |
| UI-021 | `NativeIncidents.jsx`, `native_incidents/api.py` pagination | P/F; I pending | Compare server total, page boundaries, filters and record count in browser. |
| UI-022 | `navigation.js`, `UnifiedResourceManagement.jsx` Event Parameters/Rules | C/F; I pending | Check deep link and permission visibility. |
| UI-023 | `UnifiedResourceManagement.jsx` VM/ETL stepper and `MonitoringSetup.jsx` | P/F; I pending | Cross-journey action/focus/validation consistency review. |

Current source and test evidence for the UAT Test 1 sections: sidebar/navigation (`TopNav.jsx`, `navigation.js`, `ui_recovery_acceptance.mjs`); global header/multi-environment selection (`TopNav.jsx`, `environment_scope_acceptance.mjs`); Dashboard (`UnifiedOverview.jsx`, `/api/v1/unified/overview`); six pipeline pages (`PipelineWorkspace.jsx`, `pipeline_sprint07_acceptance.mjs`); Compute/API operations (`VMHealth.jsx`, `APIs.jsx`, `DomainMonitoring.jsx`, `adapter_environment_union_acceptance.mjs`); Resource Management/full-page onboarding (`UnifiedResourceManagement.jsx`, `resourceApi.js`, `/api/v1/resource-drafts`); collector methods (`CollectorControl.jsx`, `telemetry/api.py`); Access Management (`AccessManagement.jsx`, `access.py`, `access_boundaries.py`); Reports (`Reports.jsx`, `reporting.py`). Controlled tests and prior screenshots are development evidence only. UAT Test 1's complete human workflow remains independent acceptance, not a demonstrated PASS for merged main.

## OC-IMP-001–018 and AUD-01–08

The [OC-IMP V2.0 register](../arch-etl-001-v16-r1/sprint12/OC_IMP_V20_BASELINE.md) states **all 18 rows are proposals**, not individually approved requirements. Source overlap below is not approval or implementation proof. `CONDITIONAL` means owner approval and an exact contract are needed before coding.

| Proposal | Current source overlap | Status / program placement |
| --- | --- | --- |
| OC-IMP-001 | `unified/pentaho_schedule.py`, source health | PARTIAL; DEV-02/05 conditional signal contract. |
| OC-IMP-002 | Agent registration and credential rotation in `telemetry/api.py` | PARTIAL; DEV-02, test-CA/real-CA lifecycle pending. |
| OC-IMP-003 | `worker/egress.py`, TLS probe controls | PARTIAL; DEV-06/Phase 4 private-route acceptance pending. |
| OC-IMP-004 | `telemetry/ingestion.py`, `TelemetryReceipt` | PARTIAL; DEV-02 durability/loss accounting conditional. |
| OC-IMP-005 | `collector_runtime.py:ApiAdapter` | PARTIAL; DEV-03/Phase 2 approved synthetic journey evidence. |
| OC-IMP-006 | Schedule/source coverage projection | PARTIAL; DEV-02 blind-spot inventory conditional. |
| OC-IMP-007 | Timestamp guards and native evidence time | PARTIAL; DEV-02 clock-skew bounds undecided. |
| OC-IMP-008 | `CollectorConfigVersion`, Agent apply | PARTIAL; DEV-02 fleet canary/rollback unverified. |
| OC-IMP-009 | Retention/holds in `services/retention.py` | PARTIAL; DEV-06 cardinality/cost/data policy pending. |
| OC-IMP-010 | `/health`, `/health/db`, worker diagnostics | PARTIAL; DEV-06 data-path self-observability missing acceptance. |
| OC-IMP-011 | `backend/scripts/database_backup.py`, local restore probe | PARTIAL; Phase 4 production DR evidence pending. |
| OC-IMP-012 | `native_incidents/service.py`, notification destinations | PARTIAL; DEV-05 service owner/escalation contract pending. |
| OC-IMP-013 | `unified/compatibility.py`, nine platform profiles | PARTIAL; DEV-03 installed-build registry pending. |
| OC-IMP-014 | Audit events and incident correlation | PARTIAL; DEV-05 authorized change-event semantics pending. |
| OC-IMP-015 | CI and seven release gates documented | PARTIAL; Phase 4 independent sign-off pending. |
| OC-IMP-016 | Secret redaction, holds and retention code | PARTIAL; DEV-06 residency/classification policy pending. |
| OC-IMP-017 | Existing canonical single-owner VM model | **SUPERSEDED FOR VMs** by latest owner one-customer rule; multi-customer Kubernetes cluster association needs separate approved design. Do not implement shared VM. |
| OC-IMP-018 | `ResourceDependency`, native incidents, reporting | PARTIAL; DEV-04/05 exact versioned topology/SLO contract pending. |

| Audit finding | Current disposition |
| --- | --- |
| AUD-01 | **Addressed in source, unverified at scale**: `unified/api.py:details` limits embedded dependencies to 50; `/resources/{id}/dependencies` supplies bounded 1–200 pages. |
| AUD-02 | Performance risk: `unified/api.py:add_dependency` still uses per-node graph traversal, capped at 1000; measured workload needed. |
| AUD-03 | Performance risk: `pipelines/usePipelineFeed.js` makes per-row enrichment requests with three-worker concurrency; measured workload needed. |
| AUD-04 | Open question: `security/boundaries.py:transaction_authority` serializes sensitive decisions; revocation fence must be preserved. |
| AUD-05 | Verification gap: `/health`/DB liveness does not prove worker, ingestion or collector delivery. |
| AUD-06 | Identity-policy question: `telemetry/ingestion.py:validate_method_identity` accepts missing legacy method IDs under collector authentication. |
| AUD-07 | Source/implementation uncertainty: versioned SLO authority not recovered, dedicated engine not located. |
| AUD-08 | Real-infrastructure trust/DR/provider certification gap; local scripts and fixtures insufficient. |

Full original IMP-001–062 definitions remain `SOURCE_NOT_RECOVERED`; eight known titles are insufficient to reconstruct requirements. These dispositions supersede only the current assessment, not historical audit evidence.

Approved architecture authority: [ARCH-001 V1.6](../../ARCH_001_V16.md), [ARCH-ETL-001 V1.6](../../architecture/ARCH_ETL_001_V16.md). The [reconciled ENG-001](../../engineering/ENG_001.md) explicitly lacks original full wording, so full ENG-001 compliance is UNKNOWN. The [Product Alignment addendum](../../architecture/PRODUCT_ALIGNMENT_ADDENDUM.md) and [OPS-DEPLOY-001](../../architecture/OPS_DEPLOY_001.md) record owner-approved direction, with actual deployment compatibility unverified. Historical Sprint 12 shared-VM positive-association planning is superseded by the owner's newer one-owner-per-VM decision; no schema change is proposed in this audit.
