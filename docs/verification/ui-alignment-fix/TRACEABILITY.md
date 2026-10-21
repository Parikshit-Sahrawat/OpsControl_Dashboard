# UI Alignment Fix traceability — working assessment

Source authority: [approved UI register](source/UI_001_023_REGISTER.md) and [UAT Test 1](source/UAT_TEST_1_UI_ALIGNMENT_FIX.txt). Assessment is against `feat/ui-alignment-fix` beginning at `1379d1d6cd135e51294c3bde80b5fd51b3f807cc`, including the local continuation documented below. `main` advanced to `4ebd8d8a64dff75ef7577c169c76e651e435dcc7` through Stage B PR #40, which changes deployment workflows and scripts but does not overlap these frontend/runtime paths.

Status terms: **IMPLEMENTED_TESTED** means a relevant automated check executed; **PARTIAL** means a required path or independent evidence remains; **UNVERIFIED** means source behavior exists but no adequate test was found. Synthetic fixture checks are not live monitoring or independent UAT.

| ID | Current code / contract | Test evidence | Status and remaining work |
| --- | --- | --- | --- |
| UI-001 | `TopNav.jsx`, `navigation.js`, `App.jsx` grouped guarded sidebar, persisted collapse, mobile focus | `ui_recovery_acceptance.mjs`, `navigation.test.mjs` | IMPLEMENTED_TESTED; complete independent keyboard review |
| UI-002 | `UnifiedResourceManagement.jsx` component selector | `ui_recovery_acceptance.mjs` | IMPLEMENTED_TESTED |
| UI-003 | `UnifiedResourceManagement.jsx` Compute full-page `Modal` workspace | `ui_recovery_acceptance.mjs` | IMPLEMENTED_TESTED; functional end-to-end remains UI-007–009 |
| UI-004 | `UnifiedResourceManagement.jsx` ten-step VM list and compact mobile layout | `ui_recovery_acceptance.mjs` | IMPLEMENTED_TESTED; step transitions need deeper validation |
| UI-005 | `styles.css`, `visual-system.css`, form and table layouts | Chromium at 390, 768, 1366 px, including guided ETL/API workspace overflow checks | PARTIAL; ultrawide and independent visual review open |
| UI-006 | `ResourceForm` single save/continue controls | `ui_recovery_acceptance.mjs` | PARTIAL; later-step prerequisites and draft resume require testing |
| UI-007 | Canonical `data_source_id` and collector reads in `ResourceForm`; explicit error on missing association | `ui_alignment_onboarding_acceptance.mjs` | PARTIAL; synthetic create path passed, legacy/failed lookup recovery and independent UAT open |
| UI-008 | `CollectorControl` retains separate collection-method list on one collector | `ui_recovery_acceptance.mjs`, `ui_alignment_onboarding_acceptance.mjs` | PARTIAL; edit/disable/remove and real agent association need regression |
| UI-009 | `/api/v1/unified/resources/{id}/verification` and `/activate`, readiness guard in `ResourceForm` | `backend/tests/test_unified_v15_contracts.py`, `frontend/scripts/arch001_acceptance.mjs` | PARTIAL; blocked activation negative path and current UAT run not yet exercised in this workstream |
| UI-010 | Customer Organizations in Resource Management; provider Departments in Access Management | `ui_recovery_acceptance.mjs`, backend access tests | IMPLEMENTED_TESTED; independent UAT pending |
| UI-011 | Configuration pages under Resource Management; evidence-first Compute/API and six Pipeline operation pages | `ui_recovery_acceptance.mjs` | IMPLEMENTED_TESTED on synthetic fixtures; provider evidence not certified |
| UI-012 | Sidebar/mobile layout and theme system | Chromium at 390, 768, 1366 px; light/dark selection and refresh persistence | PARTIAL; ultrawide and independent accessibility audit open |
| UI-013 | ETL identity/configuration/review full-page workspace and `PLATFORM_PENTAHO` dynamic form in `UnifiedResourceManagement.jsx`; existing editor in `DataPipelineIntegrations.jsx` | Chromium stage/field navigation, one save action and 390 px overflow | PARTIAL; credential reference validation and independent UAT open |
| UI-014 | `AccessBoundaries.jsx` grouped form sections | `ui_recovery_acceptance.mjs` navigation only | PARTIAL; form layout at mobile/tablet and permission behavior open |
| UI-015 | `AccessOnboarding.jsx` department-scoped employee search and grant origin presentation | `access_onboarding_acceptance.mjs` | PARTIAL; broader permissions workflow and independent UAT open |
| UI-016 | `UnifiedOverview.jsx` running executions, alert groups, explicit unknown evidence | `ui_recovery_acceptance.mjs` | PARTIAL; detail links and empty/error states need deeper tests; missing running step/order source remains unknown |
| UI-017 | `DomainMonitoring.jsx`, `VMHealth.jsx`, infrastructure read API with canonical `LINUX`/`WINDOWS` source types | `ui_recovery_acceptance.mjs`, `adapter_environment_union_acceptance.mjs` | IMPLEMENTED_TESTED with synthetic evidence; live provider validation open |
| UI-018 | `PipelineWorkspace.jsx`, pipeline table styles | Six-page navigation check | PARTIAL; column readability and mobile table/browser checks open |
| UI-019 | `DomainMonitoring.jsx`, `APIs.jsx`, existing service probe API | `ui_recovery_acceptance.mjs`, `adapter_environment_union_acceptance.mjs` | IMPLEMENTED_TESTED with synthetic evidence; live probes open |
| UI-020 | `Alerts.jsx` labeled filters | `ui_recovery_acceptance.mjs` navigation | PARTIAL; visual toolbar test open; full Alerts redesign excluded by UAT source |
| UI-021 | `NativeIncidents.jsx` scoped page count/range | `ui_recovery_acceptance.mjs` | IMPLEMENTED_TESTED; multi-page data set not yet exercised |
| UI-022 | Guarded Event Parameters and Alert Rules Resource Management child routes | `ui_recovery_acceptance.mjs` | IMPLEMENTED_TESTED; configuration-form UAT remains open |
| UI-023 | Shared stepper navigation in `ResourceForm`: ten VM stages and three ETL/API stages; native integration editor retains its separate eight-stage workflow | Chromium VM/ETL/API stage, previous and single-action checks | PARTIAL; persisted draft/resume validation remains open |

## UAT Test 1 coverage

| Requirement group | Evidence / open condition |
| --- | --- |
| Global header and sidebar | Multi-environment, customer scope, clock, refresh, theme and grouped navigation exist in `TopNav.jsx`. Desktop/mobile synthetic checks passed. Administration/Help destinations cannot be claimed until a supported route and permission contract are verified. |
| Dashboard | Bounded current execution and alert projections exist in `UnifiedOverview.jsx`. Native running-step/order fields are absent from the list contract; keep them unknown. Detail-link and empty/error checks remain. |
| Data Pipelines | Six pages and native classification are retained. `PipelineWorkspace.jsx` still has a selected-pipeline selector because its detail APIs are resource-scoped; all-customer history/queue behavior cannot be represented as complete until an authorized aggregate API is verified. |
| Compute/API Operations | Existing adapter/probe evidence appears before registered resource context. Synthetic two-environment positive/negative HTTP checks passed; genuine adapter/probe evidence remains separate. |
| Reports | Three report domains have aligned filter fields and searchable resource choice in `DomainReports.jsx`; browser selection and export checks remain. |
| Resource Management/onboarding | Customer and provider identities remain separate. Compute draft/source/collector create path is fixture-tested; ETL/API configuration now uses full-page stages and was browser checked without saving. Installation, readiness, failed lookups, activation and persisted ETL/API form workflows require more coverage. Existing native integration read/edit controls were relocated before the duplicate create action was removed. |
| Access Management | Department first and guided employee search are present; job designation has no verified existing backend field and must not be stored as another attribute without a reviewed contract. |
| Alerts | Existing page retained; only labels and cross-page links in authorized scope. |

The continuation's backend unit gate exposed and fixed scalar report-environment parameter compatibility: scalar requests again compile as equality, explicit multi-selection as `IN`. The complete backend unit discovery then passed 503 tests (210 skipped); the skipped PostgreSQL cases are not credited as passing. Frontend unit tests passed 5/5, Chromium synthetic navigation passed 97/97, lint and build passed. Independent UAT, PostgreSQL preservation, critical coverage, CI and current-main integration remain mandatory gates. Pentaho RT-001–RT-020 remain NOT RUN.
