# Full feature inventory

This is a source/behavior assessment, not a product acceptance certificate. Every source/test reference below is pinned to PR80; main availability is explicit in FEATURES.json and the source index. Declared routes/tables/functions do not prove registration, authorization or working runtime behavior. Full symbols, handler names and line numbers are retained in SOURCE_SYMBOL_INDEX.json.

## Resource Management

Canonical crosslinks: RM-01, RM-02, RM-03, RM-04, RM-05, CMP-02, UI-002, UI-003, UI-006, UI-007, UI-008, UI-011, UI-022. One primary owner per requirement is in REQUIREMENTS_GAP_MATRIX.csv; crosslinks are not extra counts.

Existing scoped CRUD/drafts/configuration; one VM owner. Complete agent-onboarding and central collector UX still has historical acceptance gaps.

Source: [backend/app/api/resource_management.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/api/resource_management.py); [backend/app/models/entities.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/models/entities.py); [backend/app/registry/api.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/registry/api.py); [frontend/src/pages/ResourceManagementV2.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/frontend/src/pages/ResourceManagementV2.jsx); [frontend/src/pages/UnifiedResourceManagement.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/frontend/src/pages/UnifiedResourceManagement.jsx).

Backend test definitions: [backend/tests/test_registry_contracts.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/tests/test_registry_contracts.py); [backend/tests/test_database_integrity.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/tests/test_database_integrity.py); [backend/tests/test_removed_platform_scope.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/tests/test_removed_platform_scope.py).

Frontend/browser definitions: [frontend/scripts/resource_crud_acceptance.mjs](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/frontend/scripts/resource_crud_acceptance.mjs); [frontend/scripts/ui_alignment_onboarding_acceptance.mjs](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/frontend/scripts/ui_alignment_onboarding_acceptance.mjs). CI mapping: [.github/workflows/access-architecture.yml](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/.github/workflows/access-architecture.yml).

Declared handler examples: `backend/app/api/resource_management.py:list_scoped_data_sources` GET `/data-sources` (router prefix applies); `backend/app/api/resource_management.py:create_scoped_data_source` POST `/data-sources` (router prefix applies); `backend/app/api/resource_management.py:update_scoped_data_source` PATCH `/data-sources/{data_source_id}` (router prefix applies).

## Access Management / RBAC

Canonical crosslinks: AM-01, AM-02, AM-03, UI-010, UI-014, UI-015. One primary owner per requirement is in REQUIREMENTS_GAP_MATRIX.csv; crosslinks are not extra counts.

Direct/inherited scoped access and revocation have bounded execution evidence; effective-access UX and independent UAT remain.

Source: [backend/app/api/access.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/api/access.py); [backend/app/security/scope.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/security/scope.py); [backend/app/security/boundaries.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/security/boundaries.py); [frontend/src/pages/AccessManagement.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/frontend/src/pages/AccessManagement.jsx); [frontend/src/pages/AccessBoundaries.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/frontend/src/pages/AccessBoundaries.jsx).

Backend test definitions: [backend/tests/test_access_control.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/tests/test_access_control.py); [backend/tests/test_sprint08_rbac.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/tests/test_sprint08_rbac.py).

Frontend/browser definitions: [frontend/scripts/access_acceptance.mjs](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/frontend/scripts/access_acceptance.mjs); [frontend/scripts/sprint08_acceptance.mjs](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/frontend/scripts/sprint08_acceptance.mjs). CI mapping: [.github/workflows/access-architecture.yml](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/.github/workflows/access-architecture.yml).

Declared handler examples: `backend/app/api/access.py:provider_info` GET `/provider` (router prefix applies); `backend/app/api/access.py:employees` GET `/employees` (router prefix applies); `backend/app/api/access.py:employee` GET `/employees/{user_id}` (router prefix applies).

## Templates / activation

Canonical crosslinks: RM-04, RM-05, UI-009, ETL-10. One primary owner per requirement is in REQUIREMENTS_GAP_MATRIX.csv; crosslinks are not extra counts.

Template versions/attachments and preview/apply exist. ETL Template→Workflow→Job effective policy is not established; current tests are not proof of full ETL inheritance.

Source: [backend/app/api/monitoring.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/api/monitoring.py); [backend/app/services/template_resolution.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/services/template_resolution.py); [backend/app/services/activation_engine.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/services/activation_engine.py); [frontend/src/pages/MonitoringSetup.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/frontend/src/pages/MonitoringSetup.jsx).

Backend test definitions: [backend/tests/test_activation_hydration.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/tests/test_activation_hydration.py); [backend/tests/test_api_monitoring_config.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/tests/test_api_monitoring_config.py).

Frontend/browser definitions: [frontend/scripts/test_monitoring_setup.mjs](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/frontend/scripts/test_monitoring_setup.mjs). CI mapping: [.github/workflows/http-golden-path.yml](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/.github/workflows/http-golden-path.yml).

Declared handler examples: `backend/app/api/monitoring.py:list_data_sources` GET `/data-sources` (router prefix applies); `backend/app/api/monitoring.py:get_data_source` GET `/data-sources/{item_id}` (router prefix applies); `backend/app/api/monitoring.py:create_data_source` POST `/data-sources` (router prefix applies).

## Collector runtime / agent lifecycle

Canonical crosslinks: TEL-01, TEL-03, RM-05. One primary owner per requirement is in REQUIREMENTS_GAP_MATRIX.csv; crosslinks are not extra counts.

Pinned collector and fenced readers exist; CHK-001 loss and CHK-002 rollback persist. Windows genuine installer/provider readiness is separate.

Source: [agent/opscontrol_agent.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/agent/opscontrol_agent.py); [agent/install-linux.sh](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/agent/install-linux.sh); [agent/install-windows.ps1](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/agent/install-windows.ps1); [backend/app/worker/collector_runtime.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/worker/collector_runtime.py); [backend/app/api/remote_protocol.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/api/remote_protocol.py).

Backend test definitions: [backend/tests/test_collection_v15.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/tests/test_collection_v15.py); [backend/tests/test_agent_v15.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/tests/test_agent_v15.py); [backend/tests/test_remote_auth.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/tests/test_remote_auth.py).

Frontend/browser definitions: [frontend/scripts/arch001_acceptance.mjs](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/frontend/scripts/arch001_acceptance.mjs). CI mapping: [.github/workflows/arch001-native-monitoring.yml](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/.github/workflows/arch001-native-monitoring.yml).

Declared handler examples: `backend/app/api/remote_protocol.py:assign_collector` PUT `/collectors/{collector_id}/assignment` (router prefix applies); `backend/app/api/remote_protocol.py:unassign_collector` DELETE `/collectors/{collector_id}/assignment` (router prefix applies); `backend/app/api/remote_protocol.py:heartbeat` POST `/heartbeat` (router prefix applies).

## Telemetry ingestion / identities

Canonical crosslinks: TEL-02, TEL-03, TEL-04. One primary owner per requirement is in REQUIREMENTS_GAP_MATRIX.csv; crosslinks are not extra counts.

Authenticated OTLP logs/metrics/traces and transactional pipeline evidence/checkpoint exist. TelemetryReceipt is a batch hash receipt, not proof of a complete centralized durable-spool implementation or upstream zero loss.

Source: [backend/app/telemetry/ingestion.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/telemetry/ingestion.py); [backend/app/telemetry/models.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/telemetry/models.py); [backend/app/data_pipelines/service.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/data_pipelines/service.py); [backend/app/data_pipelines/models.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/data_pipelines/models.py).

Backend test definitions: [backend/tests/test_managed_telemetry.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/tests/test_managed_telemetry.py); [backend/tests/test_pipeline_ownership_v16.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/tests/test_pipeline_ownership_v16.py).

Frontend/browser definitions: [frontend/scripts/pipeline_v16_acceptance.mjs](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/frontend/scripts/pipeline_v16_acceptance.mjs). CI mapping: [.github/workflows/pipeline-v16.yml](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/.github/workflows/pipeline-v16.yml).

Declared handler examples: `backend/app/telemetry/ingestion.py:ingest` POST `/otlp/v1/{signal}` (router prefix applies).

## Metrics/logs/events / alert evaluation

Canonical crosslinks: TEL-02, OPS-01, ETL-09, ETL-12. One primary owner per requirement is in REQUIREMENTS_GAP_MATRIX.csv; crosslinks are not extra counts.

Metric/log rules and OPEN/RESOLVED states exist; separate ETL event layer/four-state conditions remain incomplete. No inferred ETL severity defaults.

Source: [backend/app/worker/alert_engine.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/worker/alert_engine.py); [backend/app/unified/engines.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/unified/engines.py); [backend/app/telemetry/rules.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/telemetry/rules.py); [backend/app/api/monitoring.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/api/monitoring.py).

Backend test definitions: [backend/tests/test_condition_refresh.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/tests/test_condition_refresh.py); [backend/tests/test_unified_monitoring.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/tests/test_unified_monitoring.py).

Frontend/browser definitions: [frontend/scripts/operations_acceptance.mjs](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/frontend/scripts/operations_acceptance.mjs). CI mapping: [.github/workflows/live-http-alert-recovery.yml](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/.github/workflows/live-http-alert-recovery.yml).

Declared handler examples: `backend/app/telemetry/rules.py:event_list` GET `/api/v1/event-parameters` (router prefix applies); `backend/app/telemetry/rules.py:event_create` POST `/api/v1/event-parameters` (router prefix applies); `backend/app/telemetry/rules.py:event_edit` PUT `/api/v1/event-parameters/{id}` (router prefix applies).

## ETL Workflow / Job configuration

Canonical crosslinks: ETL-01, ETL-02, ETL-03, ETL-04, ETL-15, ETL-16, DP-01, UI-013, UI-018, UI-023. One primary owner per requirement is in REQUIREMENTS_GAP_MATRIX.csv; crosslinks are not extra counts.

Main has legacy Jobs/history; first-class Workflow/DAG/configuration UI, temporal binding and new guards exist only in draft PR80. D07/D08 fields/readiness are incomplete.

Source: [backend/app/api/etl.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/api/etl.py); [backend/app/schemas/etl.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/schemas/etl.py); [backend/app/models/entities.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/models/entities.py); [frontend/src/pages/ETLJobs.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/frontend/src/pages/ETLJobs.jsx); [frontend/src/pages/ETLWorkflowConfiguration.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/frontend/src/pages/ETLWorkflowConfiguration.jsx); [backend/migrations/versions/0039_etl_workflow_foundation.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/migrations/versions/0039_etl_workflow_foundation.py).

Backend test definitions: [backend/tests/test_etl_workflow_scope.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/tests/test_etl_workflow_scope.py); [backend/tests/test_etl_dag_concurrency.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/tests/test_etl_dag_concurrency.py); [backend/tests/test_etl_workflow_ui.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/tests/test_etl_workflow_ui.py).

Frontend/browser definitions: [frontend/scripts/workflow_configuration_acceptance.mjs](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/frontend/scripts/workflow_configuration_acceptance.mjs). CI mapping: [.github/workflows/pipeline-v16.yml](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/.github/workflows/pipeline-v16.yml).

Declared handler examples: `backend/app/api/etl.py:list_executions` GET `/executions` (router prefix applies); `backend/app/api/etl.py:get_execution` GET `/executions/{execution_id}` (router prefix applies); `backend/app/api/etl.py:create_job_order` POST `/job-orders` (router prefix applies).

## Native identity / Pentaho qualification

Canonical crosslinks: DP-01, DP-02, ETL-05, ETL-06, ETL-14. One primary owner per requirement is in REQUIREMENTS_GAP_MATRIX.csv; crosslinks are not extra counts.

Read-only observation normalization and historical fixtures exist. PR80 adds unqualified authority contracts/fences; genuine confirmation/receipt admission and live cutover BLOCKED.

Source: [backend/app/pipeline_adapters/pentaho_observations.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/pipeline_adapters/pentaho_observations.py); [backend/app/pipeline_adapters/pentaho_carte.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/pipeline_adapters/pentaho_carte.py); [backend/app/unified/pentaho_execution.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/unified/pentaho_execution.py); [backend/app/etl_bindings/authority.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/etl_bindings/authority.py); [backend/app/etl_bindings/service.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/etl_bindings/service.py); [backend/migrations/versions/0040_etl_native_bindings.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/migrations/versions/0040_etl_native_bindings.py); [backend/migrations/versions/0041_etl_authority_writer.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/migrations/versions/0041_etl_authority_writer.py).

Backend test definitions: [backend/tests/test_pentaho_r1.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/tests/test_pentaho_r1.py); [backend/tests/test_pentaho_carte_compat.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/tests/test_pentaho_carte_compat.py).

Frontend/browser definitions: [frontend/scripts/pipeline_sprint07_acceptance.mjs](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/frontend/scripts/pipeline_sprint07_acceptance.mjs). CI mapping: [.github/workflows/pipeline-v16.yml](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/.github/workflows/pipeline-v16.yml).

## Native schedule observations / correlation

Canonical crosslinks: ETL-02, ETL-05, ETL-07, ETL-08, ETL-11. One primary owner per requirement is in REQUIREMENTS_GAP_MATRIX.csv; crosslinks are not extra counts.

Native export authority/occurrences are separate from monitoring expectations. Carte status is not Server scheduler authority. No OpsControl workload dispatch/run/retry/schedule controls.

Source: [backend/app/unified/pentaho_schedule.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/unified/pentaho_schedule.py); [backend/app/unified/pentaho_history.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/unified/pentaho_history.py); [backend/app/unified/pentaho_recovery.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/unified/pentaho_recovery.py).

Backend test definitions: [backend/tests/test_pentaho_history_contracts.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/tests/test_pentaho_history_contracts.py); [backend/tests/test_pentaho_execution_contracts.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/tests/test_pentaho_execution_contracts.py).

Frontend/browser definitions: [frontend/scripts/sprint09_acceptance.mjs](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/frontend/scripts/sprint09_acceptance.mjs). CI mapping: [.github/workflows/v15-quality.yml](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/.github/workflows/v15-quality.yml).

## VM Health / EC2

Canonical crosslinks: CMP-01, CMP-02, UI-017. One primary owner per requirement is in REQUIREMENTS_GAP_MATRIX.csv; crosslinks are not extra counts.

Inventory and observed compute evidence are distinct. Controlled projections exist; real Windows/Linux/EC2 certification and freshness/agent-on latency acceptance remain.

Source: [backend/app/api/infrastructure.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/api/infrastructure.py); [backend/app/api/investigations.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/api/investigations.py); [frontend/src/pages/VMHealth.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/frontend/src/pages/VMHealth.jsx).

Backend test definitions: [backend/tests/test_infrastructure_health_projection.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/tests/test_infrastructure_health_projection.py); [backend/tests/test_managed_telemetry.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/tests/test_managed_telemetry.py).

Frontend/browser definitions: [frontend/scripts/infrastructure_acceptance.mjs](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/frontend/scripts/infrastructure_acceptance.mjs). CI mapping: [.github/workflows/infrastructure-acceptance.yml](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/.github/workflows/infrastructure-acceptance.yml).

Declared handler examples: `backend/app/api/infrastructure.py:resources` GET `/resources` (router prefix applies); `backend/app/api/infrastructure.py:resource` GET `/resources/{source_id}` (router prefix applies); `backend/app/api/infrastructure.py:history` GET `/resources/{source_id}/history` (router prefix applies).

## API / HTTPS / TLS monitoring

Canonical crosslinks: API-01, UI-019. One primary owner per requirement is in REQUIREMENTS_GAP_MATRIX.csv; crosslinks are not extra counts.

GET/HEAD HTTPS contracts and saved settings hydration have merged DEV05.1 evidence. No arbitrary methods/headers or automatic target certification.

Source: [backend/app/services/api_monitoring_config.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/services/api_monitoring_config.py); [backend/app/api/activation.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/api/activation.py); [backend/app/worker/remote_scheduler.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/worker/remote_scheduler.py); [backend/scripts/run_remote_agent.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/scripts/run_remote_agent.py); [frontend/src/pages/APIs.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/frontend/src/pages/APIs.jsx); [frontend/src/pages/MonitoringSetup.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/frontend/src/pages/MonitoringSetup.jsx).

Backend test definitions: [backend/tests/test_api_monitoring_config.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/tests/test_api_monitoring_config.py); [backend/tests/test_activation_hydration.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/tests/test_activation_hydration.py); [backend/tests/test_api_service_health_projection.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/tests/test_api_service_health_projection.py).

Frontend/browser definitions: [frontend/scripts/http_golden_path.mjs](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/frontend/scripts/http_golden_path.mjs); [frontend/scripts/monitoring_settings.test.mjs](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/frontend/scripts/monitoring_settings.test.mjs). CI mapping: [.github/workflows/http-golden-path.yml](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/.github/workflows/http-golden-path.yml).

Declared handler examples: `backend/app/api/activation.py:activation_preview` POST `/{source_id}/activation-preview` (router prefix applies); `backend/app/api/activation.py:activation_apply` POST `/{source_id}/activations` (router prefix applies); `backend/app/api/activation.py:activation_state` GET `/{source_id}/activation` (router prefix applies).

## Incidents / correlation / recovery

Canonical crosslinks: OPS-01, OPS-03, UI-021. One primary owner per requirement is in REQUIREMENTS_GAP_MATRIX.csv; crosslinks are not extra counts.

Recovery/incident/history/61-ID pagination controlled evidence exists. Complete ETL correlation/occurrence recovery, escalation policy and independent downstream acceptance remain.

Source: [backend/app/native_incidents/service.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/native_incidents/service.py); [backend/app/services/correlation.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/services/correlation.py); [backend/app/unified/pentaho_recovery.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/unified/pentaho_recovery.py); [frontend/src/pages/NativeIncidents.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/frontend/src/pages/NativeIncidents.jsx).

Backend test definitions: [backend/tests/test_native_incidents_v15.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/tests/test_native_incidents_v15.py); [backend/tests/test_pentaho_incident_contracts.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/tests/test_pentaho_incident_contracts.py).

Frontend/browser definitions: [frontend/scripts/release_pagination_acceptance.mjs](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/frontend/scripts/release_pagination_acceptance.mjs). CI mapping: [.github/workflows/operational-acceptance.yml](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/.github/workflows/operational-acceptance.yml).

## Email / in-app / webhook

Canonical crosslinks: OPS-01, ETL-13, SET-01. One primary owner per requirement is in REQUIREMENTS_GAP_MATRIX.csv; crosslinks are not extra counts.

SMTP TLS, generic webhook and scoped in-app outbox paths exist. Live destinations, escalation windows and ETL-specific dedup policy need independent evidence/decisions.

Source: [backend/app/worker/notifications.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/worker/notifications.py); [backend/app/telemetry/delivery.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/telemetry/delivery.py); [backend/app/telemetry/inbox.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/telemetry/inbox.py); [backend/app/telemetry/rules.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/telemetry/rules.py).

Backend test definitions: [backend/tests/test_notification_transport.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/tests/test_notification_transport.py); [backend/tests/test_in_app_notifications.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/tests/test_in_app_notifications.py).

Frontend/browser definitions: [frontend/scripts/full_closure_acceptance.mjs](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/frontend/scripts/full_closure_acceptance.mjs). CI mapping: [.github/workflows/v15-quality.yml](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/.github/workflows/v15-quality.yml).

Declared handler examples: `backend/app/telemetry/inbox.py:inbox` GET `` (router prefix applies); `backend/app/telemetry/inbox.py:preferences` GET `/preferences` (router prefix applies); `backend/app/telemetry/inbox.py:save_preferences` PUT `/preferences` (router prefix applies).

## PagerDuty / ServiceNow

Canonical crosslinks: ETL-13, OPS-01. One primary owner per requirement is in REQUIREMENTS_GAP_MATRIX.csv; crosslinks are not extra counts.

Current channel dispatch rejects retired channels; generic webhook is not a native PagerDuty/ServiceNow adapter. CF-04 authority conflict: do not implement an unapproved restoration.

Source: [backend/app/worker/notifications.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/worker/notifications.py); [backend/app/telemetry/delivery.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/telemetry/delivery.py).

Backend test definitions: [backend/tests/test_notification_transport.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/tests/test_notification_transport.py).

Frontend/browser definitions: No dedicated journey definition mapped. CI mapping: [.github/workflows/v15-quality.yml](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/.github/workflows/v15-quality.yml).

## Overview / dashboards / reports

Canonical crosslinks: OPS-04, UI-016, UI-020. One primary owner per requirement is in REQUIREMENTS_GAP_MATRIX.csv; crosslinks are not extra counts.

Evidence projections/filters/reports and bounded Alerts label fixes exist; blind-spot denominators, missing-signal semantics and broad responsive coverage remain incomplete.

Source: [backend/app/api/operations.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/api/operations.py); [backend/app/unified/reporting.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/unified/reporting.py); [frontend/src/pages/UnifiedOverview.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/frontend/src/pages/UnifiedOverview.jsx); [frontend/src/pages/Reports.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/frontend/src/pages/Reports.jsx); [frontend/src/pages/Alerts.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/frontend/src/pages/Alerts.jsx).

Backend test definitions: [backend/tests/test_unified_v15_contracts.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/tests/test_unified_v15_contracts.py); [backend/tests/test_sprint09_contracts.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/tests/test_sprint09_contracts.py).

Frontend/browser definitions: [frontend/scripts/operations_acceptance.mjs](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/frontend/scripts/operations_acceptance.mjs). CI mapping: [.github/workflows/operational-acceptance.yml](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/.github/workflows/operational-acceptance.yml).

Declared handler examples: `backend/app/api/operations.py:services` GET `/services` (router prefix applies); `backend/app/api/operations.py:service_detail` GET `/services/{source_id}` (router prefix applies); `backend/app/api/operations.py:collector_detail` GET `/collectors/{collector_id}` (router prefix applies).

## Settings / profile / preferences / Help

Canonical crosslinks: SET-01, SET-02, HELP-01, UI-001, UI-005, UI-012. One primary owner per requirement is in REQUIREMENTS_GAP_MATRIX.csv; crosslinks are not extra counts.

Merged profile/preference/help fixes exist. Account security editing and admin settings keys/ranges/reauth/audit contract are not approved; SET02 has no safe editor implementation.

Source: [frontend/src/components/PersonalWorkspace.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/frontend/src/components/PersonalWorkspace.jsx); [frontend/src/components/TopNav.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/frontend/src/components/TopNav.jsx); [backend/app/telemetry/inbox.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/telemetry/inbox.py).

Backend test definitions: [backend/tests/test_in_app_notifications.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/tests/test_in_app_notifications.py).

Frontend/browser definitions: [frontend/scripts/full_closure_acceptance.mjs](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/frontend/scripts/full_closure_acceptance.mjs); [frontend/scripts/ui_theme_acceptance.mjs](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/frontend/scripts/ui_theme_acceptance.mjs). CI mapping: [.github/workflows/v15-quality.yml](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/.github/workflows/v15-quality.yml).

Declared handler examples: `backend/app/telemetry/inbox.py:inbox` GET `` (router prefix applies); `backend/app/telemetry/inbox.py:preferences` GET `/preferences` (router prefix applies); `backend/app/telemetry/inbox.py:save_preferences` PUT `/preferences` (router prefix applies).

## Audit / retention / recovery / multi-tenancy

Canonical crosslinks: PLT-01, PLT-03, AM-01. One primary owner per requirement is in REQUIREMENTS_GAP_MATRIX.csv; crosslinks are not extra counts.

Scoped audit/retention/hold and controlled restore paths exist; production WAL/PITR/DR, legal/residency and independent security signoffs remain unverified.

Source: [backend/app/security/audit.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/security/audit.py); [backend/app/services/retention.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/services/retention.py); [backend/app/data_pipelines/service.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/data_pipelines/service.py); [backend/app/db/etl_rollback.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/db/etl_rollback.py).

Backend test definitions: [backend/tests/test_audit_remediation.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/tests/test_audit_remediation.py); [backend/tests/test_database_integrity.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/tests/test_database_integrity.py).

Frontend/browser definitions: [frontend/scripts/access_acceptance.mjs](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/frontend/scripts/access_acceptance.mjs). CI mapping: [.github/workflows/release-reliability.yml](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/.github/workflows/release-reliability.yml).

## Security / image / dependency gates

Canonical crosslinks: PLT-03, TEL-04, LIC-005. One primary owner per requirement is in REQUIREMENTS_GAP_MATRIX.csv; crosslinks are not extra counts.

Automated gate success is separate from independent immutable-image/SBOM/license/NOTICE clearance; current release security remains BLOCKED.

Source: [backend/app/security/deployment.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/security/deployment.py); [backend/app/security/secret_refs.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/security/secret_refs.py); [backend/app/security/access_control.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/security/access_control.py).

Backend test definitions: [backend/tests/test_release_hardening.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/tests/test_release_hardening.py); [backend/tests/test_access_control.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/tests/test_access_control.py).

Frontend/browser definitions: No dedicated journey definition mapped. CI mapping: [.github/workflows/security-validation.yml](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/.github/workflows/security-validation.yml).

## Deployment / installation / configuration

Canonical crosslinks: PLT-02, PLT-04, LIC-006, TEL-01. One primary owner per requirement is in REQUIREMENTS_GAP_MATRIX.csv; crosslinks are not extra counts.

Pull controller/release authorization and isolated tests exist. Current main publication preflight fails; live target/digest/backup/capacity/rollback readiness is not established by this audit.

Source: [scripts/uat/local_auto_deploy.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/scripts/uat/local_auto_deploy.py); [scripts/uat/pull_release.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/scripts/uat/pull_release.py); [scripts/uat/release_handoff.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/scripts/uat/release_handoff.py); [agent/packaging/build-windows.ps1](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/agent/packaging/build-windows.ps1).

Backend test definitions: [backend/tests/test_worker_readiness.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/tests/test_worker_readiness.py).

Frontend/browser definitions: [frontend/scripts/arch001_acceptance.mjs](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/frontend/scripts/arch001_acceptance.mjs). CI mapping: [.github/workflows/local-uat-auto-deploy.yml](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/.github/workflows/local-uat-auto-deploy.yml).

## Topology / attribution / freshness

Canonical crosslinks: TOP-01, OPS-02. One primary owner per requirement is in REQUIREMENTS_GAP_MATRIX.csv; crosslinks are not extra counts.

Bounded customer-safe traversal exists; versioned freshness/expiry and SLO denominator/source policy require authority.

Source: [backend/app/unified/reconstruction.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/unified/reconstruction.py); [backend/app/api/investigations.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/api/investigations.py).

Backend test definitions: [backend/tests/test_topology_traversal.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/tests/test_topology_traversal.py).

Frontend/browser definitions: [frontend/scripts/operations_acceptance.mjs](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/frontend/scripts/operations_acceptance.mjs). CI mapping: [.github/workflows/operational-acceptance.yml](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/.github/workflows/operational-acceptance.yml).

Declared handler examples: `backend/app/api/investigations.py:get_investigation` GET `/etl/executions/{history_id}/investigation` (router prefix applies); `backend/app/api/investigations.py:transition` POST `/etl/executions/{history_id}/investigation/transitions` (router prefix applies); `backend/app/api/investigations.py:add_note` POST `/etl/executions/{history_id}/investigation/notes` (router prefix applies).

## Product lifecycle / licensing

Canonical crosslinks: LIC-001, LIC-002, LIC-003, LIC-004, LIC-005, LIC-006, LIC-007, LIC-008. One primary owner per requirement is in REQUIREMENTS_GAP_MATRIX.csv; crosslinks are not extra counts.

Adjacent release/RBAC code is not entitlement implementation. Journey33 has bounded principles; editions, issuer, offline clock/grace/permissions and 28 gates/LIC029–050 exact definitions remain unavailable. No license-specific tests located.

Source: [scripts/uat/verify_publish.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/scripts/uat/verify_publish.py); [backend/app/security/scope.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/security/scope.py).

Backend test definitions: No specific implementation tests mapped; shared foundations are not substitutes.

Frontend/browser definitions: No dedicated journey definition mapped. CI mapping: [.github/workflows/security-validation.yml](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/.github/workflows/security-validation.yml).

## Global responsiveness / ingestion load

Canonical crosslinks: PLT-04, OPS-04, TEL-02. One primary owner per requirement is in REQUIREMENTS_GAP_MATRIX.csv; crosslinks are not extra counts.

RM-DEF-036 is a global P0-provisional operator observation, not VM-only or causally proven. Existing prefetch batching is partial; all growing-data endpoints/polling need controlled load, query, latency and receipt accounting.

Source: [backend/app/api/infrastructure.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/api/infrastructure.py); [backend/app/api/operations.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/api/operations.py); [backend/app/api/resource_management.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/app/api/resource_management.py); [frontend/src/pages/UnifiedOverview.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/frontend/src/pages/UnifiedOverview.jsx).

Backend test definitions: [backend/tests/test_sprint09_hardening.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/backend/tests/test_sprint09_hardening.py).

Frontend/browser definitions: [frontend/scripts/sprint09_acceptance.mjs](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/frontend/scripts/sprint09_acceptance.mjs). CI mapping: [.github/workflows/v15-quality.yml](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/958193f266c89302b2f1919e3703faece591e0af/.github/workflows/v15-quality.yml).

Declared handler examples: `backend/app/api/infrastructure.py:resources` GET `/resources` (router prefix applies); `backend/app/api/infrastructure.py:resource` GET `/resources/{source_id}` (router prefix applies); `backend/app/api/infrastructure.py:history` GET `/resources/{source_id}/history` (router prefix applies).

## Inventory totals and omissions

Main: {'files': 565, 'declared_routes': 287, 'table_declarations': 99, 'python_test_definitions': 655, 'frontend_test_markers': 42, 'workflow_files': 23}. PR80: {'files': 596, 'declared_routes': 304, 'table_declarations': 106, 'python_test_definitions': 741, 'frontend_test_markers': 51, 'workflow_files': 23}. Python definition counts include historical harness/test sources, not executed tests or unique parametrized cases; frontend marker counts are lexical, not execution totals. No percentage of product completion is derived.23 workflows exist on each baseline. Retained Kubernetes-named tests/models are historical/denial/preservation artifacts, not supported capabilities.

Node tests inspect helpers/source/contracts; no mounted React component test framework was located in the inspected package setup. Existing Playwright scripts are actual browser definitions, with past executions separately identified; they are not rerun here as formal UAT. External targets, private deployment topology and unseen owner conversations are outside this audit. Proposals and licensing principles must not be implemented from source overlap alone.

**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**

