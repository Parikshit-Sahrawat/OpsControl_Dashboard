# Issue #47 source-to-requirement traceability

Source snapshot: `ae4df971d07fa65bbe9e50fbdacba2c68ceae7be`. Audit comparison: [PR #43](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/pull/43) at `2b1ade567dd4c0ad4967f3d603e3fdd84cffb782` (audited main `65aa131`); controlled [Issue #46 report](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/365a1202314c8a744f3cb0cef60cec45976dac54/docs/verification/issue-46/REPORT.md) at `365a120` tested `ae4df971`. File paths below are repository-root relative. **Path/test presence indicates a trace, not full behavior or independent acceptance.** `models/entities.py` means `backend/app/models/entities.py`; similarly abbreviated `api.py` paths are stated fully at least once per family. DB head at Issue #46: `0037_access_boundaries`; family references to migrations are not claims that a new migration is needed. All independent-UAT and production columns for this snapshot are **PENDING**; real Pentaho RT-001–020 are **NOT RUN**.

## The 26 audit capability families — cross-references, not requirement IDs

`C`/`P` are PR #43's bounded-source COMPLETE/PARTIAL assessment; they preserve its **14 C / 12 P** counts as historical audit classifications. The current Phase 1 status is held by the [canonical register](../../planning/DEVELOPMENT_COMPLETION_REGISTER.md), not computed from these counts. API path is the relevant route family, not an exhaustive OpenAPI listing. Test paths identify concrete existing suites; Issue #46 execution is recorded separately in its report.

| Audit family | Canonical IDs / DEV | Source / UI → API → service/model and migration | Existing test/evidence | Audit source |
| --- | --- | --- | --- | --- |
| Customer organizations | RM-01; DEV-01 | `frontend/src/pages/UnifiedResourceManagement.jsx` → `backend/app/api/organizations.py` `/api/v1/organizations` → `backend/app/models/entities.py:Organization`; `backend/app/security/scope.py` | `scripts/access-acceptance.py`, `scripts/arch001-acceptance.py`; Issue #46 HTTP negatives | C |
| Authentication and sessions | AM-01; DEV-01/06 | `frontend/src/auth.js`, `components/AuthGate.jsx` → `backend/app/security/http.py`, `models.py:User,AccessSession`; access migrations through `0037_access_boundaries` | `backend/tests/test_remote_auth.py`, `test_access_control.py`; Issue #46 | C |
| VM and application ownership | CMP-02, RM-02; DEV-01/03 | `UnifiedResourceManagement.jsx` → `backend/app/unified/api.py` `/api/v1/unified/resources` → `backend/app/models/entities.py:VM,Application`, `backend/app/unified/models.py:MonitoringResource` | `scripts/arch001-acceptance.py`, `scripts/release-acceptance.py`; Issue #46 | C |
| Kubernetes/EKS discovery | K8S-01/02; DEV-04 | `backend/app/api/discovery.py`, `backend/app/worker/provider_discovery.py` → DataSource in `models/entities.py`; cluster association model **not located** | `scripts/infrastructure-acceptance.py`; controlled fixtures, real EKS pending | P |
| Resource draft/configuration/activation | RM-02, UI-003/004/006/007/009/023; DEV-01 | `UnifiedResourceManagement.jsx`, `frontend/src/resourceApi.js` → `backend/app/registry/api.py` `/api/v1/resource-drafts`, `backend/app/unified/api.py` verification/activate → `registry/models.py:ResourceDraft`, `unified/models.py` | `scripts/arch001-acceptance.py`, `frontend/scripts/arch001_acceptance.mjs`; Issue #46 | P |
| Attribute registry/templates | RM-02; DEV-01 | `DynamicConfigurationForm.jsx` → `backend/app/registry/api.py` attribute registry; `backend/app/api/monitoring.py` templates → `models/entities.py:MonitoringTemplate*` | `backend/tests/test_registry_contracts.py` | C |
| Collector/method configuration | RM-04, UI-008; DEV-02 | `frontend/src/pages/CollectorControl.jsx` → `backend/app/telemetry/api.py` → `telemetry/models.py:CollectorMethod,CollectorConfigVersion` | `scripts/access-acceptance.py`, `backend/tests/test_unified_monitoring.py` | C |
| Agent enrollment/runtime | TEL-01; DEV-02 | `agent/opscontrol_agent.py`, installers → `backend/app/telemetry/api.py` → `telemetry/models.py:ManagedAgent,AgentDeployment` | Agent/controlled owned-runtime scripts; actual installed Windows pending | P |
| Remote probe/telemetry ingestion | TEL-02/03; DEV-02 | `backend/app/worker/remote_scheduler.py`, `backend/app/telemetry/ingestion.py` → `/api/v1/agent/*`, `telemetry/models.py:TelemetryReceipt,TraceSpan` | `backend/tests/test_unified_monitoring.py`, controlled probes | P |
| Source ownership/fencing | RM-05; DEV-02 | `backend/app/data_pipelines/service.py` acquire/check_ticket/accept/checkpoint → `data_pipelines/models.py:PipelineSource,PipelineMethod,PipelineEvidence`; `/api/v1/data-pipelines/sources/*` | `backend/tests/test_pipeline_ownership_v16.py`, `scripts/v16-acceptance.py` | C |
| Evidence replay/holds | DP-01, PLT-03; DEV-03/06 | `backend/app/unified/pentaho_replay.py`, `data_pipelines/service.py` → replay/hold routes; `data_pipelines/models.py:PipelineHold` | `backend/tests/test_pipeline_ownership_v16.py`, Sprint 09/Issue #46 controlled | C |
| Compute operations | CMP-01, UI-017; DEV-03 | `frontend/src/pages/VMHealth.jsx`, `DomainMonitoring.jsx` → `backend/app/api/infrastructure.py`, `unified/reporting.py:domain_state` → `InfrastructureEvidence` | `scripts/infrastructure-acceptance.py`; Issue #46 | C |
| API service probes | API-01, UI-019; DEV-03 | `frontend/src/pages/APIs.jsx`, `DomainMonitoring.jsx` → `backend/app/api/operations.py`, `worker/collector_runtime.py:ApiAdapter` → `InfrastructureEvidence` | `scripts/release-acceptance.py`, controlled HTTP/TLS | C |
| Pipeline inventory/configuration | RM-02, DP-01, UI-013/018; DEV-01/03 | `UnifiedResourceManagement.jsx`, `DataPipelineIntegrations.jsx` → `backend/app/data_pipelines/api.py`, `unified/api.py` → `data_pipelines/models.py`, `MonitoringResource` | `scripts/v16-acceptance.py`, Sprint 07 browser | C |
| Pentaho read-only adapters | DP-01; DEV-03 | `PipelineWorkspace.jsx` → `backend/app/pipeline_adapters/pentaho_carte.py`, `pentaho_observations.py`, `worker/pentaho_status.py` → execution/evidence models | `backend/tests/test_pipeline_adapters.py`, native fixtures; RT-001–020 NOT RUN | P |
| Attempts/evidence/reviews | DP-01; DEV-03 | `ExecutionViews.jsx`, `ReviewView.jsx` → `backend/app/unified/pentaho_execution.py`, `pentaho_review.py` → `pentaho_models.py`; `/api/v1/unified/resources/{id}/executions` | `scripts/v16-acceptance.py`; controlled database/HTTP | C |
| Schedule/recovery | DP-01, OPS-03; DEV-03/05 | `ScheduleView.jsx`, `RecoveryView.jsx` → `backend/app/unified/pentaho_schedule.py`, `pentaho_recovery.py` → `pentaho_models.py` | Sprint 05/06, `scripts/v16-acceptance.py`; actual scheduler pending | C |
| Other pipeline adapters | DP-02; DEV-03 | `backend/app/pipeline_adapters/core.py`, `http.py`, `native.py`, `unified/compatibility.py` → shared pipeline models | `backend/tests/test_pipeline_adapters.py`; eight installed platforms pending | P |
| Native incidents/correlation | OPS-01/03, UI-021; DEV-05 | `NativeIncidents.jsx`, `IncidentView.jsx` → `backend/app/native_incidents/api.py`, `service.py`, `pentaho.py` → `native_incidents/models.py` | `backend/tests/test_native_incidents_v15.py`, `scripts/v16-acceptance.py` | C |
| Topology/dependency graph | TOP-01; DEV-04 | `backend/app/unified/api.py` details/dependency_history/add_dependency → `unified/models.py:ResourceDependency`; customer composite FKs | `backend/tests/test_unified_v15_contracts.py`; AUD-02 performance unmeasured | P |
| Alerts/notifications | OPS-01, UI-020; DEV-05 | `frontend/src/pages/Alerts.jsx`, `EventDelivery.jsx` → `worker/alert_engine.py`, `worker/notifications.py`, `telemetry/delivery.py` → `models/entities.py:AlertState,AlertNotificationDelivery` | `backend/tests/test_unified_monitoring.py`; real destination pending | P |
| Reports/SLO governance | OPS-02/04; DEV-05 | `frontend/src/pages/Reports.jsx` → `backend/app/api/operations.py`, `unified/reporting.py` `/api/v1/unified/reports/{domain}`; **dedicated versioned SLO model not located** | `frontend/scripts/operations_acceptance.mjs`; controlled report count | P |
| Cloud/provider monitoring | CMP-01, K8S-02; DEV-03/04 | `backend/app/worker/provider_checks.py`, `provider_discovery.py` → `api/discovery.py`; `InfrastructureEvidence` | `scripts/infrastructure-acceptance.py`; genuine AWS/EKS pending | P |
| Access Management/RBAC | AM-01/02/03, UI-014/015; DEV-01 | `AccessManagement.jsx`, `AccessBoundaries.jsx` → `backend/app/api/access.py`, `access_boundaries.py`, `security/access_control.py`, `scope.py`, `delegation.py` → access models; `0037_access_boundaries` | `scripts/access-acceptance.py`, `backend/tests/test_access_control.py`; Issue #46 | C |
| Migration/backup/legal hold | PLT-01/03; DEV-06 | `backend/migrations/versions/0001*`–`0037_access_boundaries.py`, `backend/scripts/database_backup.py`, `backend/app/services/retention.py`, pipeline holds | `scripts/release-acceptance.py`, Issue #46 disposable restore | P |
| Deployment/CI | PLT-02/04; DEV-06 | `.github/workflows/`, `deploy/uat/`, `scripts/uat/`, `scripts/test-quality.sh` | `.github/workflows/v15-quality.yml`, Stage B state tests; actual UAT runner pilot disabled | P |

## Approved UI-001–UI-023: one row per original ID

Wording and priorities remain authoritative in the [UI source register](../ui-alignment-fix/source/UI_001_023_REGISTER.md). `V` means controlled implementation/test evidence (not independent UAT); `P` means only partial implemented-scope evidence; see the audit's [individual source mapping](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/2b1ade567dd4c0ad4967f3d603e3fdd84cffb782/docs/verification/development-audit/FEATURE_TRACEABILITY.md). Every row has **independent UAT PENDING** and **production certification PENDING**.

| ID | Canonical parent / DEV | Current source and relevant contract | Existing automated evidence | Development state | Next bounded task |
| --- | --- | --- | --- | --- | --- |
| UI-001 | RM-03 / 01 | `frontend/src/components/TopNav.jsx`, `navigation.js`, `App.jsx` | `frontend/scripts/navigation.test.mjs`, `ui_recovery_acceptance.mjs` | IMPLEMENTED_VERIFIED | Candidate-SHA keyboard/mobile/persistence UAT |
| UI-002 | RM-02 / 01 | `pages/UnifiedResourceManagement.jsx` component selector | `frontend/scripts/ui_recovery_acceptance.mjs` | IMPLEMENTED_VERIFIED | Check refresh/deep-link |
| UI-003 | RM-02 / 01 | `UnifiedResourceManagement.jsx:ResourceForm`, `registry/api.py` drafts | `frontend/scripts/arch001_acceptance.mjs`; Issue #46 | IMPLEMENTED_VERIFIED | Full Compute UAT |
| UI-004 | RM-02 / 01 | `UnifiedResourceManagement.jsx` guidedSteps, `resource-v2.css` | `frontend/scripts/arch001_acceptance.mjs` | IMPLEMENTED_VERIFIED | Mobile/desktop focus checks |
| UI-005 | RM-03 / 01 | `frontend/src/visual-system.css`, `resource-v2.css` | Browser screenshots in prior sprint | PARTIALLY_IMPLEMENTED | Reproduce clipping at 390/768/1366 |
| UI-006 | RM-02 / 01 | `UnifiedResourceManagement.jsx:ResourceForm` VM/API/ETL actions | `frontend/scripts/arch001_acceptance.mjs` | PARTIALLY_IMPLEMENTED | One primary action, validation per state |
| UI-007 | RM-02 / 01 | `registry/api.py`, `unified/api.py`, `resourceApi.js` | Issue #46 draft/activation HTTP | PARTIALLY_IMPLEMENTED | Reproduce historical Not Found with persisted draft |
| UI-008 | RM-04 / 02 | `pages/CollectorControl.jsx`, `telemetry/api.py:CollectorMethod` | `scripts/access-acceptance.py` | IMPLEMENTED_VERIFIED | Multi-method UAT, real agent separate |
| UI-009 | RM-02 / 01 | `unified/api.py` verification/activate | `scripts/arch001-acceptance.py`; Issue #46 | PARTIALLY_IMPLEMENTED | Prove backend-confirmed actual readiness per target |
| UI-010 | RM-01/AM-01 / 01 | `models/entities.py:Organization`, `security/access_models.py:Department` | `scripts/access-acceptance.py`; Issue #46 | IMPLEMENTED_VERIFIED | Preserve cross-entity negative UAT |
| UI-011 | RM-02/CMP-01/DP-01/API-01 / 01 | `navigation.js`, Resource/Operations pages | `frontend/scripts/navigation.test.mjs` | IMPLEMENTED_VERIFIED | Check no duplicate create in Operations |
| UI-012 | RM-03 / 01 | `frontend/src/theme.js`, `TopNav.jsx`, `visual-system.css` | `frontend/scripts/ui_recovery_acceptance.mjs` | PARTIALLY_IMPLEMENTED | Responsive/theme/reduced-motion independent pass |
| UI-013 | DP-01 / 01 | `UnifiedResourceManagement.jsx` ETL workspace, `DataPipelineIntegrations.jsx` | `frontend/scripts/pipeline_v16_acceptance.mjs` | PARTIALLY_IMPLEMENTED | Verify credentials remain references and layout |
| UI-014 | AM-01 / 01 | `pages/AccessBoundaries.jsx`, `access-management.css` | `scripts/access-acceptance.py` | IMPLEMENTED_VERIFIED | LIMIT/DENY form independent UAT |
| UI-015 | AM-01/03 / 01 | `pages/AccessManagement.jsx`, `api/access.py` effective projection | `scripts/access-acceptance.py` | PARTIALLY_IMPLEMENTED | Employee→permission origin UX |
| UI-016 | OPS-04 / 01 | `pages/UnifiedOverview.jsx`, `unified/reporting.py:overview` | `frontend/scripts/operations_acceptance.mjs` | IMPLEMENTED_VERIFIED | Actual outage vs valid zero state |
| UI-017 | CMP-01 / 03 | `pages/VMHealth.jsx`, `DomainMonitoring.jsx` | `scripts/infrastructure-acceptance.py`; Issue #46 | IMPLEMENTED_VERIFIED | Real adapter acceptance separate |
| UI-018 | DP-01 / 03 | `pipelines/PipelineWorkspace.jsx`, `pipelines.css` | Sprint 07 CI run `39827607578` | IMPLEMENTED_VERIFIED | Readability/overflow independent UAT |
| UI-019 | API-01 / 03 | `pages/APIs.jsx`, `DomainMonitoring.jsx` | `scripts/release-acceptance.py` | IMPLEMENTED_VERIFIED | Real probe acceptance separate |
| UI-020 | OPS-01 / 05 | `pages/Alerts.jsx` filter toolbar | Browser source/audit review | PARTIALLY_IMPLEMENTED | Labels only; no Alerts redesign |
| UI-021 | OPS-01 / 05 | `pages/NativeIncidents.jsx`, `native_incidents/api.py` pagination | `backend/tests/test_native_incidents_v15.py` | PARTIALLY_IMPLEMENTED | Filtered totals/duplicates browser test |
| UI-022 | RM-02 / 01 | `navigation.js`, `UnifiedResourceManagement.jsx` Event Parameters/Rules | `frontend/scripts/navigation.test.mjs` | IMPLEMENTED_VERIFIED | Deep-link/permissions UAT |
| UI-023 | RM-02/DP-01 / 01 | `UnifiedResourceManagement.jsx` VM/ETL stepper, `MonitoringSetup.jsx` | `frontend/scripts/arch001_acceptance.mjs` | PARTIALLY_IMPLEMENTED | Step action/focus parity test |

## OC-IMP-001–018: individually **PROPOSED_OWNER_REVIEW**, not additional approved scope

Original wording, proposed priority, dependencies and measurable criteria are in the [Sprint 12 proposal baseline](../arch-etl-001-v16-r1/sprint12/OC_IMP_V20_BASELINE.md). The columns below map overlaps and a **conditional** bounded task; no row authorizes a new feature. `P` means PARTIALLY_IMPLEMENTED overlap, `B` means BLOCKED_ARCHITECTURE for the precise proposed contract. Actual database/API additions require a separate approved design and migration review. All independent UAT and production certification remain pending.

| Proposal | DEV / overlap path (frontend; backend/API; persistence or migration) | Test lead; state | Dependency and next conditional task |
| --- | --- | --- | --- |
| OC-IMP-001 | 02/05; `ScheduleView.jsx`; `unified/pentaho_schedule.py`; pipeline evidence models | `scripts/v16-acceptance.py`; P | Approve per-service signal/freshness contract; missing/stale/complete scoped tests |
| OC-IMP-002 | 02/06; `CollectorControl.jsx`; `telemetry/api.py`; `ManagedAgent`/credential controls | Agent tests; B | Provider CA policy/test CA; expiry, overlap, revocation negatives |
| OC-IMP-003 | 06; `APIs.jsx`; `worker/egress.py`; no new schema asserted | TLS/probe acceptance; B | Approved private route/trust topology; isolated allow/deny tests |
| OC-IMP-004 | 02; Collector UI; `telemetry/ingestion.py`; `TelemetryReceipt` | ingestion tests; P | Approved loss/storage contract; numbered disconnect/restart accounting |
| OC-IMP-005 | 03; `APIs.jsx`; `collector_runtime.py:ApiAdapter`; InfrastructureEvidence | `scripts/release-acceptance.py`; P | Target consent and read-only synthetic journey boundaries |
| OC-IMP-006 | 02/05; pipeline coverage views; `pentaho_schedule.py`; source-health evidence | `scripts/v16-acceptance.py`; P | OC-IMP-001 approval; missing-source inventory without false healthy/NO_RUN |
| OC-IMP-007 | 02/06; pipeline evidence views; `telemetry/ingestion.py`; native timestamp fields | native fixture tests; B | Clock authority/bounds; record uncertainty without rewriting evidence |
| OC-IMP-008 | 02; `CollectorControl.jsx`; `telemetry/api.py`; `CollectorConfigVersion` | Agent apply tests; B | CA and build matrix; canary/rollback without lost checkpoints |
| OC-IMP-009 | 06; report views; `services/retention.py`; hold/evidence models | restore/hold tests; B | Data policy and cost model; measure customer cardinality, held-data survival |
| OC-IMP-010 | 05/06; operational health views; `api/health.py`, ingestion/worker diagnostics | controlled outage test lead; P | OC-IMP-004/006; distinct worker/queue/collector stale states |
| OC-IMP-011 | 06; no UI required; `backend/scripts/database_backup.py`; PostgreSQL/holds | `scripts/release-acceptance.py`; P | Recovery site/key custody; measured encrypted restore/DR later |
| OC-IMP-012 | 05; incident views; `native_incidents/service.py`, `worker/notifications.py`; delivery models | `test_native_incidents_v15.py`; B | Scoped service owner/escalation policy; A/B recipient negatives |
| OC-IMP-013 | 03; pipeline views; `unified/compatibility.py`, adapters; existing profiles | `test_pipeline_adapters.py`; P | Authorized exact builds; capability registry/witness evidence |
| OC-IMP-014 | 05; incident views; native incident/audit services and models | incident tests; B | Versioned change-event authority; no inferred causality |
| OC-IMP-015 | 06/release; CI/workflow evidence; no production sign-off model asserted | CI run evidence; P | Independent seven-gate owner approval; exact-revision sign-off |
| OC-IMP-016 | 06; no feature UI presumed; `security/secret_refs.py`, `services/retention.py`; holds | security/restore tests; B | Residency/classification policy; deny unauthorized export |
| OC-IMP-017 | 04; discovery views; `api/discovery.py`; canonical cluster association **not located** | customer-negative test lead; B | Shared-VM wording superseded; approve Kubernetes-only versioned association design |
| OC-IMP-018 | 04/05; incident/topology/report views; `unified/models.py:ResourceDependency`, `unified/reporting.py` | `test_unified_v15_contracts.py`; B | Original IMP-055–062 definitions missing; approve distinct graph/SLO/recovery contracts |

## AUD-01–AUD-08: tracked findings, not approved requirement IDs

Original evidence and classifications are in [Sprint 10 code audit](../arch-etl-001-v16-r1/sprint10/CODE_AUDIT_FINDINGS.md). A later source observation may change a finding's disposition but does not erase historical evidence.

| Finding | DEV / source | Current disposition / next verification |
| --- | --- | --- |
| AUD-01 | 04; `backend/app/unified/api.py:details,dependency_history` | Historical unbounded detail defect **addressed in source** by 50-edge preview and bounded 1–200 history; run large scoped pages to verify no loss. |
| AUD-02 | 04; `unified/api.py:add_dependency` | Performance risk: per-node traversal capped at 1000; measure graph/lock/query counts before optimization. |
| AUD-03 | 03/06; `frontend/src/pipelines/usePipelineFeed.js` | Performance risk: per-row enrichment with three-worker bound; measure page-size fanout. |
| AUD-04 | 06; `backend/app/security/boundaries.py:transaction_authority` | Open performance question: advisory authorization fence; preserve revocation correctness in concurrent benchmark. |
| AUD-05 | 05/06; `backend/app/api/health.py` | Verification/monitoring gap: `/health` and DB SELECT 1 do not prove delivery path; inject worker/queue outage. |
| AUD-06 | 02; `backend/app/telemetry/ingestion.py:validate_method_identity` | Open compatibility/security question: legacy absent method ID; decide explicit compatibility policy before any rejection change. |
| AUD-07 | 05; `backend/app/unified/reporting.py` | SLO source/implementation question; no dedicated approved versioned SLO engine located; do not infer from thresholds. |
| AUD-08 | 06; backup/agent/deployment sources | Real infrastructure trust/DR/provider evidence missing; controlled tests cannot certify production. |

## Historical IMP-001–IMP-062 original source status

The original approved requirement text and approval revision are unavailable; see the [Sprint 11 source recovery](../arch-etl-001-v16-r1/sprint11/SOURCE_RECOVERY.md). The eight known titles for IMP-055–062 are retained in the Sprint 11 register but are not reconstructed below. Each ID independently has `SOURCE_NOT_RECOVERED`; **no implementation, priority or sprint is inferred**. Exact source/approval record is an owner input, not a development ticket.

| Original ID | Source status | Original ID | Source status | Original ID | Source status | Original ID | Source status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| IMP-001 | SOURCE_NOT_RECOVERED | IMP-002 | SOURCE_NOT_RECOVERED | IMP-003 | SOURCE_NOT_RECOVERED | IMP-004 | SOURCE_NOT_RECOVERED |
| IMP-005 | SOURCE_NOT_RECOVERED | IMP-006 | SOURCE_NOT_RECOVERED | IMP-007 | SOURCE_NOT_RECOVERED | IMP-008 | SOURCE_NOT_RECOVERED |
| IMP-009 | SOURCE_NOT_RECOVERED | IMP-010 | SOURCE_NOT_RECOVERED | IMP-011 | SOURCE_NOT_RECOVERED | IMP-012 | SOURCE_NOT_RECOVERED |
| IMP-013 | SOURCE_NOT_RECOVERED | IMP-014 | SOURCE_NOT_RECOVERED | IMP-015 | SOURCE_NOT_RECOVERED | IMP-016 | SOURCE_NOT_RECOVERED |
| IMP-017 | SOURCE_NOT_RECOVERED | IMP-018 | SOURCE_NOT_RECOVERED | IMP-019 | SOURCE_NOT_RECOVERED | IMP-020 | SOURCE_NOT_RECOVERED |
| IMP-021 | SOURCE_NOT_RECOVERED | IMP-022 | SOURCE_NOT_RECOVERED | IMP-023 | SOURCE_NOT_RECOVERED | IMP-024 | SOURCE_NOT_RECOVERED |
| IMP-025 | SOURCE_NOT_RECOVERED | IMP-026 | SOURCE_NOT_RECOVERED | IMP-027 | SOURCE_NOT_RECOVERED | IMP-028 | SOURCE_NOT_RECOVERED |
| IMP-029 | SOURCE_NOT_RECOVERED | IMP-030 | SOURCE_NOT_RECOVERED | IMP-031 | SOURCE_NOT_RECOVERED | IMP-032 | SOURCE_NOT_RECOVERED |
| IMP-033 | SOURCE_NOT_RECOVERED | IMP-034 | SOURCE_NOT_RECOVERED | IMP-035 | SOURCE_NOT_RECOVERED | IMP-036 | SOURCE_NOT_RECOVERED |
| IMP-037 | SOURCE_NOT_RECOVERED | IMP-038 | SOURCE_NOT_RECOVERED | IMP-039 | SOURCE_NOT_RECOVERED | IMP-040 | SOURCE_NOT_RECOVERED |
| IMP-041 | SOURCE_NOT_RECOVERED | IMP-042 | SOURCE_NOT_RECOVERED | IMP-043 | SOURCE_NOT_RECOVERED | IMP-044 | SOURCE_NOT_RECOVERED |
| IMP-045 | SOURCE_NOT_RECOVERED | IMP-046 | SOURCE_NOT_RECOVERED | IMP-047 | SOURCE_NOT_RECOVERED | IMP-048 | SOURCE_NOT_RECOVERED |
| IMP-049 | SOURCE_NOT_RECOVERED | IMP-050 | SOURCE_NOT_RECOVERED | IMP-051 | SOURCE_NOT_RECOVERED | IMP-052 | SOURCE_NOT_RECOVERED |
| IMP-053 | SOURCE_NOT_RECOVERED | IMP-054 | SOURCE_NOT_RECOVERED | IMP-055 | SOURCE_NOT_RECOVERED | IMP-056 | SOURCE_NOT_RECOVERED |
| IMP-057 | SOURCE_NOT_RECOVERED | IMP-058 | SOURCE_NOT_RECOVERED | IMP-059 | SOURCE_NOT_RECOVERED | IMP-060 | SOURCE_NOT_RECOVERED |
| IMP-061 | SOURCE_NOT_RECOVERED | IMP-062 | SOURCE_NOT_RECOVERED |  |  |  |  |

## Canonical requirements outside a one-to-one audit family

The families above cross-reference the rest of the 31 canonical product IDs. These seven require an explicit additional trace so absence or UI-only evidence is not mistaken for implementation. `—` means no matching route/model/test was established by the bounded current-main search; it is not evidence that no related code exists anywhere.

| Canonical ID | Frontend; backend/API; model/migration | Current test and development assessment | Exact next verification |
| --- | --- | --- | --- |
| RM-03 | `frontend/src/components/TopNav.jsx`, `navigation.js`, `visual-system.css`; no new backend; no new DB | `frontend/scripts/navigation.test.mjs`, `ui_recovery_acceptance.mjs`; PARTIALLY_IMPLEMENTED | Reproduce visual/focus defects in supported viewports before changing CSS. |
| AM-02 | `frontend/src/pages/AccessManagement.jsx`; `backend/app/api/access.py` employee endpoints; `security/access_models.py`, migration `0037_access_boundaries` | `scripts/access-acceptance.py` covers API/RBAC but separate Name/Username/Email and header-action UAT has not been tied to an exact source revision; IMPLEMENTED_UNVERIFIED | Inspect rendered employee table and UAT Cycle 2 reproduction. |
| AM-03 | `frontend/src/pages/AccessManagement.jsx`; `backend/app/api/access.py` departments/memberships; `security/access_models.py:Department,DepartmentMembership` | `scripts/access-acceptance.py` covers grants; exact Members & access navigation/action remains IMPLEMENTED_UNVERIFIED | Browser authorized assignment and read-only negative check. |
| SET-01 | `frontend/src/components/InAppNotifications.jsx` uses `/api/v1/notifications/preferences`; `backend/app/security/models.py:User.notification_preferences`; complete profile/account UI and API not established | Notification preference overlap only; PARTIALLY_IMPLEMENTED | Inventory profile/auth contracts and test self/other-user preference mutations. |
| SET-02 | No admin-editable global settings route/UI/model located in `frontend/src/navigation.js`, `frontend/src/App.jsx`, `backend/app/main.py`, `backend/app/api/` or `security/permission_catalog.py`; deployment `backend/app/core/config.py` is configuration, not an audited settings control plane | NOT_IMPLEMENTED for the approved UI+audited persistence behavior; no matching test established | Owner specifies safe keys and audit/secret contract before API, UI or DB change. |
| HELP-01 | `frontend/src/pages/CollectorControl.jsx` links an Agent manual; repository docs exist; no integrated Help/Knowledge route in `frontend/src/navigation.js`/`App.jsx` located | PARTIALLY_IMPLEMENTED content overlap; no end-to-end Help UI/API test | Inventory eligible content and SOP audience before navigation/workspace implementation. |
| TEL-04 | `backend/app/security/deployment.py`, `worker/egress.py`, Agent enrollment; `telemetry/models.py`; no provider CA/private-route integration evidence | Controlled TLS/Agent tests only; BLOCKED_ARCHITECTURE for complete certificate/private trust policy | Approve provider CA, rotation/revocation and target-network rules; then test with disposable CA. |
