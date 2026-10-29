# Implementation and execution evidence

All current source links use immutable baseline `a2f7460904fbab2a99c258616516054f21689687`. Passing suites do not automatically verify every UI state or full requirement. The requirement classification is deliberately narrower than suite coverage. Absent links for unrecovered requirements mean no authoritative mapping can be established, not missing implementation. Historical shorthand traces are retained verbatim in requirements.json.

## RM-01

VERIFIED_PENDING_OWNER. Verified (controlled; not genuine-provider or owner UAT).

Source: [backend/app/api/organizations.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/api/organizations.py); [backend/app/security/scope.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/security/scope.py); [frontend/src/pages/ResourceManagementV2.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/pages/ResourceManagementV2.jsx)

Tests: [backend/tests/test_sprint08_rbac.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/tests/test_sprint08_rbac.py)

New baseline PostgreSQL run [backend-full.log](raw/regressions/backend-full.log):

- `test_all_future_and_snapshot_semantics (test_sprint08_rbac.Sprint08RBAC.test_all_future_and_snapshot_semantics) ... ok`
- `test_all_requires_separate_authority (test_sprint08_rbac.Sprint08RBAC.test_all_requires_separate_authority) ... ok`
- `test_boundary_decision_history_cannot_be_rewritten_or_deleted (test_sprint08_rbac.Sprint08RBAC.test_boundary_decision_history_cannot_be_rewritten_or_deleted) ... ok`
- `test_delegation_budget_prevents_role_escalation (test_sprint08_rbac.Sprint08RBAC.test_delegation_budget_prevents_role_escalation) ... ok`
- `test_delegation_is_not_inferred_from_access_role (test_sprint08_rbac.Sprint08RBAC.test_delegation_is_not_inferred_from_access_role) ... ok`
- `test_deny_overrides_limit_and_inherited_allow (test_sprint08_rbac.Sprint08RBAC.test_deny_overrides_limit_and_inherited_allow) ... ok`
- `test_direct_and_legacy_multi_department_inheritance_preserved (test_sprint08_rbac.Sprint08RBAC.test_direct_and_legacy_multi_department_inheritance_preserved) ... ok`
- `test_environment_limit_filters_before_pagination (test_sprint08_rbac.Sprint08RBAC.test_environment_limit_filters_before_pagination) ... ok`
- `test_global_employee_deny_survives_other_grants (test_sprint08_rbac.Sprint08RBAC.test_global_employee_deny_survives_other_grants) ... ok`
- `test_invalid_persisted_policy_fails_closed (test_sprint08_rbac.Sprint08RBAC.test_invalid_persisted_policy_fails_closed) ... ok`
- `test_inventory_query_count_is_not_per_row (test_sprint08_rbac.Sprint08RBAC.test_inventory_query_count_is_not_per_row) ... ok`
- `test_large_customer_selection_keeps_restriction_sql_bounded (test_sprint08_rbac.Sprint08RBAC.test_large_customer_selection_keeps_restriction_sql_bounded) ... ok`
- `test_multiple_limits_intersect_instead_of_bypassing_a_restriction (test_sprint08_rbac.Sprint08RBAC.test_multiple_limits_intersect_instead_of_bypassing_a_restriction) ... ok`
- `test_no_selection_is_empty (test_sprint08_rbac.Sprint08RBAC.test_no_selection_is_empty) ... ok`
- `test_omitted_selection_and_wildcard_fail_closed (test_sprint08_rbac.Sprint08RBAC.test_omitted_selection_and_wildcard_fail_closed) ... ok`
- `test_one_customer_sql_scope (test_sprint08_rbac.Sprint08RBAC.test_one_customer_sql_scope) ... ok`
- `test_resource_limit_allows_exact_id (test_sprint08_rbac.Sprint08RBAC.test_resource_limit_allows_exact_id) ... ok`
- `test_revocation_changes_existing_session_projection (test_sprint08_rbac.Sprint08RBAC.test_revocation_changes_existing_session_projection) ... ok`
- `test_scope_revision_explains_restrictions (test_sprint08_rbac.Sprint08RBAC.test_scope_revision_explains_restrictions) ... ok`
- `test_separate_delegations_cannot_form_permission_customer_cross_product (test_sprint08_rbac.Sprint08RBAC.test_separate_delegations_cannot_form_permission_customer_cross_product) ... ok`
- `test_unassigned_all_role_never_grants (test_sprint08_rbac.Sprint08RBAC.test_unassigned_all_role_never_grants) ... ok`
- `test_worker_replay_rechecks_resource_restrictions (test_sprint08_rbac.Sprint08RBAC.test_worker_replay_rechecks_resource_restrictions) ... ok`

CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## RM-02

PARTIALLY_IMPLEMENTED. Unverified as complete requirement; bounded tests may pass.

Source: [backend/app/registry/api.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/registry/api.py); [backend/app/unified/api.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/unified/api.py); [frontend/src/pages/UnifiedResourceManagement.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/pages/UnifiedResourceManagement.jsx)

Tests: [backend/tests/test_registry_contracts.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/tests/test_registry_contracts.py)

New baseline PostgreSQL run [backend-full.log](raw/regressions/backend-full.log):

- `test_customer_fields_must_agree_and_resource_id_is_valid_uuid (test_registry_contracts.DraftValidationTests.test_customer_fields_must_agree_and_resource_id_is_valid_uuid) ... ok`
- `test_linked_resource_cannot_change_domain_or_customer (test_registry_contracts.DraftValidationTests.test_linked_resource_cannot_change_domain_or_customer) ... ok`
- `test_partial_draft_retains_empty_fields_without_claiming_activation (test_registry_contracts.DraftValidationTests.test_partial_draft_retains_empty_fields_without_claiming_activation) ... ok`
- `test_unknown_attributes_bad_types_and_embedded_credentials_are_rejected (test_registry_contracts.DraftValidationTests.test_unknown_attributes_bad_types_and_embedded_credentials_are_rejected) ... ok`
- `test_nullable_refs_defaults_and_validation_render_without_secret_values (test_registry_contracts.RegistryDefinitionTests.test_nullable_refs_defaults_and_validation_render_without_secret_values) ... ok`
- `test_package_checksum_is_stable_and_covers_capabilities (test_registry_contracts.RegistryDefinitionTests.test_package_checksum_is_stable_and_covers_capabilities) ... ok`
- `test_supported_sources_and_nine_adapters_have_typed_definitions (test_registry_contracts.RegistryDefinitionTests.test_supported_sources_and_nine_adapters_have_typed_definitions) ... ok`
- `test_bad_payload_is_422_without_persistence_or_secret_error_echo (test_registry_contracts.RegistryRouteGuardTests.test_bad_payload_is_422_without_persistence_or_secret_error_echo) ... ok`
- `test_customer_permission_denial_precedes_any_draft_write (test_registry_contracts.RegistryRouteGuardTests.test_customer_permission_denial_precedes_any_draft_write) ... ok`
- `test_lookup_query_binds_id_provider_and_owner_before_returning_data (test_registry_contracts.RegistryRouteGuardTests.test_lookup_query_binds_id_provider_and_owner_before_returning_data) ... ok`
- `test_owner_context_requires_authenticated_provider (test_registry_contracts.RegistryRouteGuardTests.test_owner_context_requires_authenticated_provider) ... ok`
- `test_runtime_model_defaults_are_timezone_aware_and_scoped (test_registry_contracts.RegistryRouteGuardTests.test_runtime_model_defaults_are_timezone_aware_and_scoped) ... ok`
- `test_stale_revision_and_domain_changes_are_conflicts_before_mutation (test_registry_contracts.RegistryRouteGuardTests.test_stale_revision_and_domain_changes_are_conflicts_before_mutation) ... ok`
- `test_uninstalled_registry_is_503_not_a_fake_default (test_registry_contracts.RegistryRouteGuardTests.test_uninstalled_registry_is_503_not_a_fake_default) ... ok`

CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## RM-03

PARTIALLY_IMPLEMENTED. Unverified as complete requirement; bounded tests may pass.

Source: [frontend/src/components/TopNav.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/components/TopNav.jsx); [frontend/src/visual-system.css](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/visual-system.css)

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## RM-04

VERIFIED_PENDING_OWNER. Verified (controlled; not genuine-provider or owner UAT).

Source: [backend/app/telemetry/api.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/telemetry/api.py); [frontend/src/pages/CollectorControl.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/pages/CollectorControl.jsx)

Tests: [backend/tests/test_managed_telemetry.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/tests/test_managed_telemetry.py)

New baseline PostgreSQL run [backend-full.log](raw/regressions/backend-full.log):

- `test_actual_file_access_missing_source_and_private_state (test_managed_telemetry.AgentPermissionTests.test_actual_file_access_missing_source_and_private_state) ... ok`
- `test_management_secret_cannot_be_scrape_authentication (test_managed_telemetry.AgentPermissionTests.test_management_secret_cannot_be_scrape_authentication) ... ok`
- `test_dynamic_baseline_requires_history_and_combined_uses_stricter_threshold (test_managed_telemetry.EvaluationBoundaryTests.test_dynamic_baseline_requires_history_and_combined_uses_stricter_threshold) ... ok`
- `test_sustained_breach_requires_complete_duration_and_contiguous_evidence (test_managed_telemetry.EvaluationBoundaryTests.test_sustained_breach_requires_complete_duration_and_contiguous_evidence) ... ok`
- `test_unavailable_collector_validator_fails_with_actionable_safe_error (test_managed_telemetry.EvaluationBoundaryTests.test_unavailable_collector_validator_fails_with_actionable_safe_error) ... ok`
- `test_binding_paths_and_os_fail_closed (test_managed_telemetry.ManagedTelemetryTests.test_binding_paths_and_os_fail_closed) ... ok`
- `test_invalid_duplicate_listeners_and_exporter_origins (test_managed_telemetry.ManagedTelemetryTests.test_invalid_duplicate_listeners_and_exporter_origins) ... ok`
- `test_itsm_routes_removed_alert_routes_present (test_managed_telemetry.ManagedTelemetryTests.test_itsm_routes_removed_alert_routes_present) ... ok`
- `test_no_raw_credentials_or_invalid_signal_fields (test_managed_telemetry.ManagedTelemetryTests.test_no_raw_credentials_or_invalid_signal_fields) ... ok`
- `test_only_explicit_signals_enabled_and_disabled_methods_excluded (test_managed_telemetry.ManagedTelemetryTests.test_only_explicit_signals_enabled_and_disabled_methods_excluded) ... ok`
- `test_percentage_rule_requires_valid_minimum_duration_count (test_managed_telemetry.ManagedTelemetryTests.test_percentage_rule_requires_valid_minimum_duration_count) ... ok`
- `test_same_type_methods_have_independent_receiver_identities (test_managed_telemetry.ManagedTelemetryTests.test_same_type_methods_have_independent_receiver_identities) ... ok`

CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## RM-05

VERIFIED_PENDING_OWNER. Verified (controlled; not genuine-provider or owner UAT).

Source: [backend/app/telemetry/api.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/telemetry/api.py); [backend/app/telemetry/models.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/telemetry/models.py)

Tests: [backend/tests/test_managed_telemetry.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/tests/test_managed_telemetry.py)

New baseline PostgreSQL run [backend-full.log](raw/regressions/backend-full.log):

- `test_actual_file_access_missing_source_and_private_state (test_managed_telemetry.AgentPermissionTests.test_actual_file_access_missing_source_and_private_state) ... ok`
- `test_management_secret_cannot_be_scrape_authentication (test_managed_telemetry.AgentPermissionTests.test_management_secret_cannot_be_scrape_authentication) ... ok`
- `test_dynamic_baseline_requires_history_and_combined_uses_stricter_threshold (test_managed_telemetry.EvaluationBoundaryTests.test_dynamic_baseline_requires_history_and_combined_uses_stricter_threshold) ... ok`
- `test_sustained_breach_requires_complete_duration_and_contiguous_evidence (test_managed_telemetry.EvaluationBoundaryTests.test_sustained_breach_requires_complete_duration_and_contiguous_evidence) ... ok`
- `test_unavailable_collector_validator_fails_with_actionable_safe_error (test_managed_telemetry.EvaluationBoundaryTests.test_unavailable_collector_validator_fails_with_actionable_safe_error) ... ok`
- `test_binding_paths_and_os_fail_closed (test_managed_telemetry.ManagedTelemetryTests.test_binding_paths_and_os_fail_closed) ... ok`
- `test_invalid_duplicate_listeners_and_exporter_origins (test_managed_telemetry.ManagedTelemetryTests.test_invalid_duplicate_listeners_and_exporter_origins) ... ok`
- `test_itsm_routes_removed_alert_routes_present (test_managed_telemetry.ManagedTelemetryTests.test_itsm_routes_removed_alert_routes_present) ... ok`
- `test_no_raw_credentials_or_invalid_signal_fields (test_managed_telemetry.ManagedTelemetryTests.test_no_raw_credentials_or_invalid_signal_fields) ... ok`
- `test_only_explicit_signals_enabled_and_disabled_methods_excluded (test_managed_telemetry.ManagedTelemetryTests.test_only_explicit_signals_enabled_and_disabled_methods_excluded) ... ok`
- `test_percentage_rule_requires_valid_minimum_duration_count (test_managed_telemetry.ManagedTelemetryTests.test_percentage_rule_requires_valid_minimum_duration_count) ... ok`
- `test_same_type_methods_have_independent_receiver_identities (test_managed_telemetry.ManagedTelemetryTests.test_same_type_methods_have_independent_receiver_identities) ... ok`

CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## AM-01

VERIFIED_PENDING_OWNER. Verified (controlled; not genuine-provider or owner UAT).

Source: [backend/app/api/access.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/api/access.py); [backend/app/security/access_models.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/security/access_models.py)

Tests: [backend/tests/test_sprint08_rbac.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/tests/test_sprint08_rbac.py)

New baseline PostgreSQL run [backend-full.log](raw/regressions/backend-full.log):

- `test_all_future_and_snapshot_semantics (test_sprint08_rbac.Sprint08RBAC.test_all_future_and_snapshot_semantics) ... ok`
- `test_all_requires_separate_authority (test_sprint08_rbac.Sprint08RBAC.test_all_requires_separate_authority) ... ok`
- `test_boundary_decision_history_cannot_be_rewritten_or_deleted (test_sprint08_rbac.Sprint08RBAC.test_boundary_decision_history_cannot_be_rewritten_or_deleted) ... ok`
- `test_delegation_budget_prevents_role_escalation (test_sprint08_rbac.Sprint08RBAC.test_delegation_budget_prevents_role_escalation) ... ok`
- `test_delegation_is_not_inferred_from_access_role (test_sprint08_rbac.Sprint08RBAC.test_delegation_is_not_inferred_from_access_role) ... ok`
- `test_deny_overrides_limit_and_inherited_allow (test_sprint08_rbac.Sprint08RBAC.test_deny_overrides_limit_and_inherited_allow) ... ok`
- `test_direct_and_legacy_multi_department_inheritance_preserved (test_sprint08_rbac.Sprint08RBAC.test_direct_and_legacy_multi_department_inheritance_preserved) ... ok`
- `test_environment_limit_filters_before_pagination (test_sprint08_rbac.Sprint08RBAC.test_environment_limit_filters_before_pagination) ... ok`
- `test_global_employee_deny_survives_other_grants (test_sprint08_rbac.Sprint08RBAC.test_global_employee_deny_survives_other_grants) ... ok`
- `test_invalid_persisted_policy_fails_closed (test_sprint08_rbac.Sprint08RBAC.test_invalid_persisted_policy_fails_closed) ... ok`
- `test_inventory_query_count_is_not_per_row (test_sprint08_rbac.Sprint08RBAC.test_inventory_query_count_is_not_per_row) ... ok`
- `test_large_customer_selection_keeps_restriction_sql_bounded (test_sprint08_rbac.Sprint08RBAC.test_large_customer_selection_keeps_restriction_sql_bounded) ... ok`
- `test_multiple_limits_intersect_instead_of_bypassing_a_restriction (test_sprint08_rbac.Sprint08RBAC.test_multiple_limits_intersect_instead_of_bypassing_a_restriction) ... ok`
- `test_no_selection_is_empty (test_sprint08_rbac.Sprint08RBAC.test_no_selection_is_empty) ... ok`
- `test_omitted_selection_and_wildcard_fail_closed (test_sprint08_rbac.Sprint08RBAC.test_omitted_selection_and_wildcard_fail_closed) ... ok`
- `test_one_customer_sql_scope (test_sprint08_rbac.Sprint08RBAC.test_one_customer_sql_scope) ... ok`
- `test_resource_limit_allows_exact_id (test_sprint08_rbac.Sprint08RBAC.test_resource_limit_allows_exact_id) ... ok`
- `test_revocation_changes_existing_session_projection (test_sprint08_rbac.Sprint08RBAC.test_revocation_changes_existing_session_projection) ... ok`
- `test_scope_revision_explains_restrictions (test_sprint08_rbac.Sprint08RBAC.test_scope_revision_explains_restrictions) ... ok`
- `test_separate_delegations_cannot_form_permission_customer_cross_product (test_sprint08_rbac.Sprint08RBAC.test_separate_delegations_cannot_form_permission_customer_cross_product) ... ok`
- `test_unassigned_all_role_never_grants (test_sprint08_rbac.Sprint08RBAC.test_unassigned_all_role_never_grants) ... ok`
- `test_worker_replay_rechecks_resource_restrictions (test_sprint08_rbac.Sprint08RBAC.test_worker_replay_rechecks_resource_restrictions) ... ok`

CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## AM-02

IMPLEMENTED_UNVERIFIED. Unverified as complete requirement; bounded tests may pass.

Source: [frontend/src/pages/AccessManagement.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/pages/AccessManagement.jsx); [backend/app/api/access.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/api/access.py)

Tests: [backend/tests/test_sprint08_rbac.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/tests/test_sprint08_rbac.py)

New baseline PostgreSQL run [backend-full.log](raw/regressions/backend-full.log):

- `test_all_future_and_snapshot_semantics (test_sprint08_rbac.Sprint08RBAC.test_all_future_and_snapshot_semantics) ... ok`
- `test_all_requires_separate_authority (test_sprint08_rbac.Sprint08RBAC.test_all_requires_separate_authority) ... ok`
- `test_boundary_decision_history_cannot_be_rewritten_or_deleted (test_sprint08_rbac.Sprint08RBAC.test_boundary_decision_history_cannot_be_rewritten_or_deleted) ... ok`
- `test_delegation_budget_prevents_role_escalation (test_sprint08_rbac.Sprint08RBAC.test_delegation_budget_prevents_role_escalation) ... ok`
- `test_delegation_is_not_inferred_from_access_role (test_sprint08_rbac.Sprint08RBAC.test_delegation_is_not_inferred_from_access_role) ... ok`
- `test_deny_overrides_limit_and_inherited_allow (test_sprint08_rbac.Sprint08RBAC.test_deny_overrides_limit_and_inherited_allow) ... ok`
- `test_direct_and_legacy_multi_department_inheritance_preserved (test_sprint08_rbac.Sprint08RBAC.test_direct_and_legacy_multi_department_inheritance_preserved) ... ok`
- `test_environment_limit_filters_before_pagination (test_sprint08_rbac.Sprint08RBAC.test_environment_limit_filters_before_pagination) ... ok`
- `test_global_employee_deny_survives_other_grants (test_sprint08_rbac.Sprint08RBAC.test_global_employee_deny_survives_other_grants) ... ok`
- `test_invalid_persisted_policy_fails_closed (test_sprint08_rbac.Sprint08RBAC.test_invalid_persisted_policy_fails_closed) ... ok`
- `test_inventory_query_count_is_not_per_row (test_sprint08_rbac.Sprint08RBAC.test_inventory_query_count_is_not_per_row) ... ok`
- `test_large_customer_selection_keeps_restriction_sql_bounded (test_sprint08_rbac.Sprint08RBAC.test_large_customer_selection_keeps_restriction_sql_bounded) ... ok`
- `test_multiple_limits_intersect_instead_of_bypassing_a_restriction (test_sprint08_rbac.Sprint08RBAC.test_multiple_limits_intersect_instead_of_bypassing_a_restriction) ... ok`
- `test_no_selection_is_empty (test_sprint08_rbac.Sprint08RBAC.test_no_selection_is_empty) ... ok`
- `test_omitted_selection_and_wildcard_fail_closed (test_sprint08_rbac.Sprint08RBAC.test_omitted_selection_and_wildcard_fail_closed) ... ok`
- `test_one_customer_sql_scope (test_sprint08_rbac.Sprint08RBAC.test_one_customer_sql_scope) ... ok`
- `test_resource_limit_allows_exact_id (test_sprint08_rbac.Sprint08RBAC.test_resource_limit_allows_exact_id) ... ok`
- `test_revocation_changes_existing_session_projection (test_sprint08_rbac.Sprint08RBAC.test_revocation_changes_existing_session_projection) ... ok`
- `test_scope_revision_explains_restrictions (test_sprint08_rbac.Sprint08RBAC.test_scope_revision_explains_restrictions) ... ok`
- `test_separate_delegations_cannot_form_permission_customer_cross_product (test_sprint08_rbac.Sprint08RBAC.test_separate_delegations_cannot_form_permission_customer_cross_product) ... ok`
- `test_unassigned_all_role_never_grants (test_sprint08_rbac.Sprint08RBAC.test_unassigned_all_role_never_grants) ... ok`
- `test_worker_replay_rechecks_resource_restrictions (test_sprint08_rbac.Sprint08RBAC.test_worker_replay_rechecks_resource_restrictions) ... ok`

CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## AM-03

IMPLEMENTED_UNVERIFIED. Unverified as complete requirement; bounded tests may pass.

Source: [frontend/src/pages/AccessManagement.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/pages/AccessManagement.jsx); [backend/app/api/access.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/api/access.py)

Tests: [backend/tests/test_sprint08_rbac.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/tests/test_sprint08_rbac.py)

New baseline PostgreSQL run [backend-full.log](raw/regressions/backend-full.log):

- `test_all_future_and_snapshot_semantics (test_sprint08_rbac.Sprint08RBAC.test_all_future_and_snapshot_semantics) ... ok`
- `test_all_requires_separate_authority (test_sprint08_rbac.Sprint08RBAC.test_all_requires_separate_authority) ... ok`
- `test_boundary_decision_history_cannot_be_rewritten_or_deleted (test_sprint08_rbac.Sprint08RBAC.test_boundary_decision_history_cannot_be_rewritten_or_deleted) ... ok`
- `test_delegation_budget_prevents_role_escalation (test_sprint08_rbac.Sprint08RBAC.test_delegation_budget_prevents_role_escalation) ... ok`
- `test_delegation_is_not_inferred_from_access_role (test_sprint08_rbac.Sprint08RBAC.test_delegation_is_not_inferred_from_access_role) ... ok`
- `test_deny_overrides_limit_and_inherited_allow (test_sprint08_rbac.Sprint08RBAC.test_deny_overrides_limit_and_inherited_allow) ... ok`
- `test_direct_and_legacy_multi_department_inheritance_preserved (test_sprint08_rbac.Sprint08RBAC.test_direct_and_legacy_multi_department_inheritance_preserved) ... ok`
- `test_environment_limit_filters_before_pagination (test_sprint08_rbac.Sprint08RBAC.test_environment_limit_filters_before_pagination) ... ok`
- `test_global_employee_deny_survives_other_grants (test_sprint08_rbac.Sprint08RBAC.test_global_employee_deny_survives_other_grants) ... ok`
- `test_invalid_persisted_policy_fails_closed (test_sprint08_rbac.Sprint08RBAC.test_invalid_persisted_policy_fails_closed) ... ok`
- `test_inventory_query_count_is_not_per_row (test_sprint08_rbac.Sprint08RBAC.test_inventory_query_count_is_not_per_row) ... ok`
- `test_large_customer_selection_keeps_restriction_sql_bounded (test_sprint08_rbac.Sprint08RBAC.test_large_customer_selection_keeps_restriction_sql_bounded) ... ok`
- `test_multiple_limits_intersect_instead_of_bypassing_a_restriction (test_sprint08_rbac.Sprint08RBAC.test_multiple_limits_intersect_instead_of_bypassing_a_restriction) ... ok`
- `test_no_selection_is_empty (test_sprint08_rbac.Sprint08RBAC.test_no_selection_is_empty) ... ok`
- `test_omitted_selection_and_wildcard_fail_closed (test_sprint08_rbac.Sprint08RBAC.test_omitted_selection_and_wildcard_fail_closed) ... ok`
- `test_one_customer_sql_scope (test_sprint08_rbac.Sprint08RBAC.test_one_customer_sql_scope) ... ok`
- `test_resource_limit_allows_exact_id (test_sprint08_rbac.Sprint08RBAC.test_resource_limit_allows_exact_id) ... ok`
- `test_revocation_changes_existing_session_projection (test_sprint08_rbac.Sprint08RBAC.test_revocation_changes_existing_session_projection) ... ok`
- `test_scope_revision_explains_restrictions (test_sprint08_rbac.Sprint08RBAC.test_scope_revision_explains_restrictions) ... ok`
- `test_separate_delegations_cannot_form_permission_customer_cross_product (test_sprint08_rbac.Sprint08RBAC.test_separate_delegations_cannot_form_permission_customer_cross_product) ... ok`
- `test_unassigned_all_role_never_grants (test_sprint08_rbac.Sprint08RBAC.test_unassigned_all_role_never_grants) ... ok`
- `test_worker_replay_rechecks_resource_restrictions (test_sprint08_rbac.Sprint08RBAC.test_worker_replay_rechecks_resource_restrictions) ... ok`

CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## SET-01

PARTIALLY_IMPLEMENTED. Unverified as complete requirement; bounded tests may pass.

Source: [frontend/src/components/InAppNotifications.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/components/InAppNotifications.jsx); [backend/app/security/models.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/security/models.py)

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## SET-02

NOT_IMPLEMENTED. Unverified as complete requirement; bounded tests may pass.

Source: [frontend/src/App.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/App.jsx); [frontend/src/navigation.js](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/navigation.js); [backend/app/main.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/main.py); [backend/app/core/config.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/core/config.py)

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## HELP-01

PARTIALLY_IMPLEMENTED. Unverified as complete requirement; bounded tests may pass.

Source: [frontend/src/pages/CollectorControl.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/pages/CollectorControl.jsx); [frontend/src/navigation.js](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/navigation.js)

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## TEL-01

PARTIALLY_IMPLEMENTED. Unverified as complete requirement; bounded tests may pass.

Source: [backend/app/telemetry/api.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/telemetry/api.py); [backend/app/telemetry/models.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/telemetry/models.py)

Tests: [backend/tests/test_agent_v15.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/tests/test_agent_v15.py)

New baseline PostgreSQL run [backend-full.log](raw/regressions/backend-full.log):

- `test_applied_is_not_verified_without_all_receipts (test_agent_v15.AgentLifecycleTests.test_applied_is_not_verified_without_all_receipts) ... ok`
- `test_failed_runtime_start_restores_previous_yaml (test_agent_v15.AgentLifecycleTests.test_failed_runtime_start_restores_previous_yaml) ... ok`
- `test_first_runtime_launch_exception_leaves_no_unapproved_config (test_agent_v15.AgentLifecycleTests.test_first_runtime_launch_exception_leaves_no_unapproved_config) ... ok`
- `test_handoff_flag_follows_actual_config_for_validate_start_and_rollback (test_agent_v15.AgentLifecycleTests.test_handoff_flag_follows_actual_config_for_validate_start_and_rollback) ... ok`
- `test_invalid_configuration_never_stops_working_runtime (test_agent_v15.AgentLifecycleTests.test_invalid_configuration_never_stops_working_runtime) ... ok`
- `test_missing_or_private_log_path_is_not_healthy (test_agent_v15.AgentLifecycleTests.test_missing_or_private_log_path_is_not_healthy) ... ok`
- `test_offline_handoff_restart_uses_same_checked_contract (test_agent_v15.AgentLifecycleTests.test_offline_handoff_restart_uses_same_checked_contract) ... ok`
- `test_offline_restart_rejects_modified_local_yaml (test_agent_v15.AgentLifecycleTests.test_offline_restart_rejects_modified_local_yaml) ... ok`
- `test_offline_restart_uses_validated_private_configuration (test_agent_v15.AgentLifecycleTests.test_offline_restart_uses_validated_private_configuration) ... ok`
- `test_private_write_and_checkpoint_survives_apply (test_agent_v15.AgentLifecycleTests.test_private_write_and_checkpoint_survives_apply) ... ok`
- `test_rotation_grace_expires (test_agent_v15.AgentLifecycleTests.test_rotation_grace_expires) ... ok`
- `test_runtime_launch_exception_restores_previous_yaml (test_agent_v15.AgentLifecycleTests.test_runtime_launch_exception_restores_previous_yaml) ... ok`

CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## TEL-02

PARTIALLY_IMPLEMENTED. Unverified as complete requirement; bounded tests may pass.

Source: [backend/app/telemetry/api.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/telemetry/api.py); [backend/app/telemetry/models.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/telemetry/models.py)

Tests: [backend/tests/test_managed_telemetry.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/tests/test_managed_telemetry.py)

New baseline PostgreSQL run [backend-full.log](raw/regressions/backend-full.log):

- `test_actual_file_access_missing_source_and_private_state (test_managed_telemetry.AgentPermissionTests.test_actual_file_access_missing_source_and_private_state) ... ok`
- `test_management_secret_cannot_be_scrape_authentication (test_managed_telemetry.AgentPermissionTests.test_management_secret_cannot_be_scrape_authentication) ... ok`
- `test_dynamic_baseline_requires_history_and_combined_uses_stricter_threshold (test_managed_telemetry.EvaluationBoundaryTests.test_dynamic_baseline_requires_history_and_combined_uses_stricter_threshold) ... ok`
- `test_sustained_breach_requires_complete_duration_and_contiguous_evidence (test_managed_telemetry.EvaluationBoundaryTests.test_sustained_breach_requires_complete_duration_and_contiguous_evidence) ... ok`
- `test_unavailable_collector_validator_fails_with_actionable_safe_error (test_managed_telemetry.EvaluationBoundaryTests.test_unavailable_collector_validator_fails_with_actionable_safe_error) ... ok`
- `test_binding_paths_and_os_fail_closed (test_managed_telemetry.ManagedTelemetryTests.test_binding_paths_and_os_fail_closed) ... ok`
- `test_invalid_duplicate_listeners_and_exporter_origins (test_managed_telemetry.ManagedTelemetryTests.test_invalid_duplicate_listeners_and_exporter_origins) ... ok`
- `test_itsm_routes_removed_alert_routes_present (test_managed_telemetry.ManagedTelemetryTests.test_itsm_routes_removed_alert_routes_present) ... ok`
- `test_no_raw_credentials_or_invalid_signal_fields (test_managed_telemetry.ManagedTelemetryTests.test_no_raw_credentials_or_invalid_signal_fields) ... ok`
- `test_only_explicit_signals_enabled_and_disabled_methods_excluded (test_managed_telemetry.ManagedTelemetryTests.test_only_explicit_signals_enabled_and_disabled_methods_excluded) ... ok`
- `test_percentage_rule_requires_valid_minimum_duration_count (test_managed_telemetry.ManagedTelemetryTests.test_percentage_rule_requires_valid_minimum_duration_count) ... ok`
- `test_same_type_methods_have_independent_receiver_identities (test_managed_telemetry.ManagedTelemetryTests.test_same_type_methods_have_independent_receiver_identities) ... ok`

CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## TEL-03

BLOCKED_RELIABILITY. Unverified as complete requirement; bounded tests may pass.

Source: [verification/dev052/queue_restart/replay.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/verification/dev052/queue_restart/replay.py)

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## TEL-04

BLOCKED_ARCHITECTURE. Unverified as complete requirement; bounded tests may pass.

Source: [backend/app/security/deployment.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/security/deployment.py); [backend/app/worker/egress.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/worker/egress.py)

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## CMP-01

VERIFIED_PENDING_OWNER. Verified (controlled; not genuine-provider or owner UAT).

Source: [backend/app/models/entities.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/models/entities.py); [backend/app/worker/collector_runtime.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/worker/collector_runtime.py)

Tests: [backend/tests/test_infrastructure_health_projection.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/tests/test_infrastructure_health_projection.py)

New baseline PostgreSQL run [backend-full.log](raw/regressions/backend-full.log):

- `test_stopped_collector_with_recent_success_is_not_healthy (test_infrastructure_health_projection.InfrastructureHealthProjectionTests.test_stopped_collector_with_recent_success_is_not_healthy) ... ok`

CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## CMP-02

VERIFIED_PENDING_OWNER. Verified (controlled; not genuine-provider or owner UAT).

Source: [backend/app/unified/api.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/unified/api.py); [backend/app/models/entities.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/models/entities.py)

Tests: [backend/tests/test_unified_v15_contracts.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/tests/test_unified_v15_contracts.py)

New baseline PostgreSQL run [backend-full.log](raw/regressions/backend-full.log):

- `test_event_identity_retry_and_execution_mode_rejections_are_explicit (test_unified_v15_contracts.NormalizationAndReportContracts.test_event_identity_retry_and_execution_mode_rejections_are_explicit) ... ok`
- `test_malformed_document_and_regex_mismatch_are_not_fabricated_executions (test_unified_v15_contracts.NormalizationAndReportContracts.test_malformed_document_and_regex_mismatch_are_not_fabricated_executions) ... ok`
- `test_report_query_contains_customer_resource_environment_and_domain_filters (test_unified_v15_contracts.NormalizationAndReportContracts.test_report_query_contains_customer_resource_environment_and_domain_filters) ... ok`
- `test_report_range_requires_aware_ordered_bounded_dates (test_unified_v15_contracts.NormalizationAndReportContracts.test_report_range_requires_aware_ordered_bounded_dates) ... ok`
- `test_timestamp_parsing_preserves_timezone_and_rejects_nonexistent_dst (test_unified_v15_contracts.NormalizationAndReportContracts.test_timestamp_parsing_preserves_timezone_and_rejects_nonexistent_dst) ... ok`
- `test_api_configuration_rejects_tls_disable_auth_over_http_and_header_injection (test_unified_v15_contracts.ParameterSafetyContracts.test_api_configuration_rejects_tls_disable_auth_over_http_and_header_injection) ... ok`
- `test_duplicate_matching_never_uses_only_message_or_jobchain (test_unified_v15_contracts.ParameterSafetyContracts.test_duplicate_matching_never_uses_only_message_or_jobchain) ... ok`
- `test_overrides_cannot_change_identity_or_bypass_threshold_validation (test_unified_v15_contracts.ParameterSafetyContracts.test_overrides_cannot_change_identity_or_bypass_threshold_validation) ... ok`
- `test_percentage_and_recovery_direction_require_finite_coherent_values (test_unified_v15_contracts.ParameterSafetyContracts.test_percentage_and_recovery_direction_require_finite_coherent_values) ... ok`
- `test_activation_requires_approval_and_actual_readiness_boundary (test_unified_v15_contracts.UnifiedServiceContracts.test_activation_requires_approval_and_actual_readiness_boundary) ... ok`
- `test_echoing_exact_internal_state_is_compatible_without_creating_privileges (test_unified_v15_contracts.UnifiedServiceContracts.test_echoing_exact_internal_state_is_compatible_without_creating_privileges) ... ok`
- `test_enabled_alert_setup_requires_active_version_and_same_customer_destination (test_unified_v15_contracts.UnifiedServiceContracts.test_enabled_alert_setup_requires_active_version_and_same_customer_destination) ... ok`
- `test_environment_propagation_retains_child_threshold_overrides (test_unified_v15_contracts.UnifiedServiceContracts.test_environment_propagation_retains_child_threshold_overrides) ... ok`
- `test_generic_edit_cannot_escalate_or_erase_internal_alert_policy (test_unified_v15_contracts.UnifiedServiceContracts.test_generic_edit_cannot_escalate_or_erase_internal_alert_policy) ... ok`
- `test_generic_edit_preserves_internal_alert_setup_and_bound_log_method_ids (test_unified_v15_contracts.UnifiedServiceContracts.test_generic_edit_preserves_internal_alert_setup_and_bound_log_method_ids) ... ok`
- `test_host_identity_and_os_cannot_be_repurposed_by_edit (test_unified_v15_contracts.UnifiedServiceContracts.test_host_identity_and_os_cannot_be_repurposed_by_edit) ... ok`
- `test_metric_selection_cannot_reference_another_customer_or_source (test_unified_v15_contracts.UnifiedServiceContracts.test_metric_selection_cannot_reference_another_customer_or_source) ... ok`
- `test_monitoring_activation_does_not_require_optional_parameters_or_alert_setup (test_unified_v15_contracts.UnifiedServiceContracts.test_monitoring_activation_does_not_require_optional_parameters_or_alert_setup) ... ok`
- `test_native_connection_failure_is_not_success_and_never_echoes_secret_error (test_unified_v15_contracts.UnifiedServiceContracts.test_native_connection_failure_is_not_success_and_never_echoes_secret_error) ... ok`
- `test_native_connection_requires_configured_pipeline_and_collectors_authority (test_unified_v15_contracts.UnifiedServiceContracts.test_native_connection_requires_configured_pipeline_and_collectors_authority) ... ok`
- `test_pause_stops_source_collector_and_vm_without_erasing_history_or_policy (test_unified_v15_contracts.UnifiedServiceContracts.test_pause_stops_source_collector_and_vm_without_erasing_history_or_policy) ... ok`
- `test_stale_resource_revision_fails_before_making_any_changes (test_unified_v15_contracts.UnifiedServiceContracts.test_stale_resource_revision_fails_before_making_any_changes) ... ok`

CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## DP-01

PARTIALLY_IMPLEMENTED. Unverified as complete requirement; bounded tests may pass.

Source: [backend/app/pipeline_adapters/pentaho_carte.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/pipeline_adapters/pentaho_carte.py); [backend/app/unified/pentaho_execution.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/unified/pentaho_execution.py); [backend/app/unified/pentaho_history.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/unified/pentaho_history.py)

Tests: [backend/tests/test_pentaho_execution_contracts.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/tests/test_pentaho_execution_contracts.py); [backend/tests/test_pentaho_execution_r1.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/tests/test_pentaho_execution_r1.py)

New baseline PostgreSQL run [backend-full.log](raw/regressions/backend-full.log):

- `test_declared_retry_authority_needs_native_scheduler_evidence (test_pentaho_execution_contracts.PentahoExecutionContracts.test_declared_retry_authority_needs_native_scheduler_evidence) ... ok`
- `test_names_and_time_matching_configuration_cannot_group_r1_invocations (test_pentaho_execution_contracts.PentahoExecutionContracts.test_names_and_time_matching_configuration_cannot_group_r1_invocations) ... ok`
- `test_native_cancelled_terminal_does_not_invent_sla_success_or_staleness (test_pentaho_execution_contracts.PentahoExecutionContracts.test_native_cancelled_terminal_does_not_invent_sla_success_or_staleness) ... ok`
- `test_native_completion_proof_and_cancellation_are_monitoring_only (test_pentaho_execution_contracts.PentahoExecutionContracts.test_native_completion_proof_and_cancellation_are_monitoring_only) ... ok`
- `test_native_lifecycle_outcome_and_completeness_are_separate (test_pentaho_execution_contracts.PentahoExecutionContracts.test_native_lifecycle_outcome_and_completeness_are_separate) ... ok`
- `test_routes_require_view_or_investigation_not_resource_creation (test_pentaho_execution_contracts.PentahoExecutionContracts.test_routes_require_view_or_investigation_not_resource_creation) ... ok`
- `test_unattested_observation_never_self_certifies_identity (test_pentaho_execution_contracts.PentahoExecutionContracts.test_unattested_observation_never_self_certifies_identity) ... ok`
- `test_cancelled_is_native_outcome_without_execution_controls (test_pentaho_execution_r1.PentahoExecutionTests.test_cancelled_is_native_outcome_without_execution_controls) ... ok`
- `test_conflicting_native_alias_does_not_retarget_confirmed_run (test_pentaho_execution_r1.PentahoExecutionTests.test_conflicting_native_alias_does_not_retarget_confirmed_run) ... ok`
- `test_cross_customer_history_and_relation_are_rejected (test_pentaho_execution_r1.PentahoExecutionTests.test_cross_customer_history_and_relation_are_rejected) ... ok`
- `test_duplicate_observations_keep_raw_records_but_not_duplicate_attempts_revisions (test_pentaho_execution_r1.PentahoExecutionTests.test_duplicate_observations_keep_raw_records_but_not_duplicate_attempts_revisions) ... ok`
- `test_identity_quarantine_blocks_recovery_confirmation (test_pentaho_execution_r1.PentahoExecutionTests.test_identity_quarantine_blocks_recovery_confirmation) ... ok`
- `test_known_retry_predecessor_cannot_point_back_from_an_earlier_attempt (test_pentaho_execution_r1.PentahoExecutionTests.test_known_retry_predecessor_cannot_point_back_from_an_earlier_attempt) ... ok`
- `test_legal_hold_and_referenced_raw_history_survive_cleanup (test_pentaho_execution_r1.PentahoExecutionTests.test_legal_hold_and_referenced_raw_history_survive_cleanup) ... ok`
- `test_manual_recovery_keeps_failed_original_and_distinct_identity (test_pentaho_execution_r1.PentahoExecutionTests.test_manual_recovery_keeps_failed_original_and_distinct_identity) ... ok`
- `test_many_to_many_recovery_links_and_reversal_are_append_only (test_pentaho_execution_r1.PentahoExecutionTests.test_many_to_many_recovery_links_and_reversal_are_append_only) ... ok`
- `test_missing_retry_authority_never_implies_exhaustion (test_pentaho_execution_r1.PentahoExecutionTests.test_missing_retry_authority_never_implies_exhaustion) ... ok`
- `test_native_retry_revision_advances_without_rewriting_prior_evidence (test_pentaho_execution_r1.PentahoExecutionTests.test_native_retry_revision_advances_without_rewriting_prior_evidence) ... ok`
- `test_out_of_order_start_and_earlier_retry_do_not_regress_success (test_pentaho_execution_r1.PentahoExecutionTests.test_out_of_order_start_and_earlier_retry_do_not_regress_success) ... ok`
- `test_process_exit_alone_unknown_and_scheduler_alone_not_success (test_pentaho_execution_r1.PentahoExecutionTests.test_process_exit_alone_unknown_and_scheduler_alone_not_success) ... ok`
- `test_recovery_self_confirmation_and_viewer_mutation_are_denied (test_pentaho_execution_r1.PentahoExecutionTests.test_recovery_self_confirmation_and_viewer_mutation_are_denied) ... ok`
- `test_revision_and_alias_mutations_and_history_deletion_rejected (test_pentaho_execution_r1.PentahoExecutionTests.test_revision_and_alias_mutations_and_history_deletion_rejected) ... ok`
- `test_single_success_has_canonical_history_attempt_and_aliases (test_pentaho_execution_r1.PentahoExecutionTests.test_single_success_has_canonical_history_attempt_and_aliases) ... ok`
- `test_stale_source_generation_does_not_accept_attempt_or_advance_checkpoint (test_pentaho_execution_r1.PentahoExecutionTests.test_stale_source_generation_does_not_accept_attempt_or_advance_checkpoint) ... ok`
- `test_unverified_retry_proposal_remains_separate_and_quarantined (test_pentaho_execution_r1.PentahoExecutionTests.test_unverified_retry_proposal_remains_separate_and_quarantined) ... ok`
- `test_verified_failed_attempt_pending_then_success_after_retry (test_pentaho_execution_r1.PentahoExecutionTests.test_verified_failed_attempt_pending_then_success_after_retry) ... ok`
- `test_verified_final_failure_exhausted_is_terminal (test_pentaho_execution_r1.PentahoExecutionTests.test_verified_final_failure_exhausted_is_terminal) ... ok`

CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## DP-02

PARTIALLY_IMPLEMENTED. Unverified as complete requirement; bounded tests may pass.

Source: [backend/app/pipeline_adapters/native.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/pipeline_adapters/native.py); [backend/app/data_pipelines/runtime.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/data_pipelines/runtime.py)

Tests: [backend/tests/test_pipeline_adapters.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/tests/test_pipeline_adapters.py)

New baseline PostgreSQL run [backend-full.log](raw/regressions/backend-full.log):

- `test_adf_body_window_continuation_and_failure (test_pipeline_adapters.PipelineAdapterTests.test_adf_body_window_continuation_and_failure) ... ok`
- `test_adf_embedded_activity_and_on_demand_continuation (test_pipeline_adapters.PipelineAdapterTests.test_adf_embedded_activity_and_on_demand_continuation) ... ok`
- `test_airflow_pagination_and_steps (test_pipeline_adapters.PipelineAdapterTests.test_airflow_pagination_and_steps) ... ok`
- `test_airflow_steps_bounded_paginated_resume_and_attempt (test_pipeline_adapters.PipelineAdapterTests.test_airflow_steps_bounded_paginated_resume_and_attempt) ... ok`
- `test_configuration_registry_helpers_types_and_closed_properties (test_pipeline_adapters.PipelineAdapterTests.test_configuration_registry_helpers_types_and_closed_properties) ... ok`
- `test_custom_checkpoint_partial_rotation_and_distinct_raw (test_pipeline_adapters.PipelineAdapterTests.test_custom_checkpoint_partial_rotation_and_distinct_raw) ... ok`
- `test_custom_explicit_step_record_does_not_end_parent_execution (test_pipeline_adapters.PipelineAdapterTests.test_custom_explicit_step_record_does_not_end_parent_execution) ... ok`
- `test_custom_identical_records_remain_distinct_and_resume (test_pipeline_adapters.PipelineAdapterTests.test_custom_identical_records_remain_distinct_and_resume) ... ok`
- `test_glue_sdk_read_only_checkpoint (test_pipeline_adapters.PipelineAdapterTests.test_glue_sdk_read_only_checkpoint) ... ok`
- `test_http_auth_rate_limit_schema_and_redirection (test_pipeline_adapters.PipelineAdapterTests.test_http_auth_rate_limit_schema_and_redirection) ... ok`
- `test_iics_embedded_activity_detail_and_invalid_inventory (test_pipeline_adapters.PipelineAdapterTests.test_iics_embedded_activity_detail_and_invalid_inventory) ... ok`
- `test_iics_warnings_unknown_and_paging (test_pipeline_adapters.PipelineAdapterTests.test_iics_warnings_unknown_and_paging) ... ok`
- `test_invalid_time_rejected_and_distinct_sources_preserved (test_pipeline_adapters.PipelineAdapterTests.test_invalid_time_rejected_and_distinct_sources_preserved) ... ok`
- `test_nifi_async_flow_semantics (test_pipeline_adapters.PipelineAdapterTests.test_nifi_async_flow_semantics) ... ok`
- `test_pentaho_preserves_carte_step_evidence (test_pipeline_adapters.PipelineAdapterTests.test_pentaho_preserves_carte_step_evidence) ... ok`
- `test_pentaho_untimed_step_failure_preserved_without_fake_duration (test_pipeline_adapters.PipelineAdapterTests.test_pentaho_untimed_step_failure_preserved_without_fake_duration) ... ok`
- `test_platform_normalization (test_pipeline_adapters.PipelineAdapterTests.test_platform_normalization) ... ok`
- `test_registry_all_nine_and_closed_configs (test_pipeline_adapters.PipelineAdapterTests.test_registry_all_nine_and_closed_configs) ... ok`
- `test_retries_preserve_checkpoint_and_auth_is_not_retried (test_pipeline_adapters.PipelineAdapterTests.test_retries_preserve_checkpoint_and_auth_is_not_retried) ... ok`
- `test_ssis_active_runs_revisited (test_pipeline_adapters.PipelineAdapterTests.test_ssis_active_runs_revisited) ... ok`
- `test_terminal_snapshot_does_not_invent_execution_end (test_pipeline_adapters.PipelineAdapterTests.test_terminal_snapshot_does_not_invent_execution_end) ... ok`
- `test_tls_egress_fails_closed (test_pipeline_adapters.PipelineAdapterTests.test_tls_egress_fails_closed) ... ok`

CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## API-01

VERIFIED_PENDING_OWNER. Verified (controlled; not genuine-provider or owner UAT).

Source: [frontend/src/pages/MonitoringSetup.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/pages/MonitoringSetup.jsx); [backend/app/services/activation_engine.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/services/activation_engine.py); [backend/app/api/remote_protocol.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/api/remote_protocol.py)

Tests: [backend/tests/test_activation_hydration.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/tests/test_activation_hydration.py)

New baseline PostgreSQL run [backend-full.log](raw/regressions/backend-full.log):

- `test_legacy_activation_infers_template_selection_from_persisted_plan (test_activation_hydration.ActivationHydrationTests.test_legacy_activation_infers_template_selection_from_persisted_plan) ... ok`
- `test_missing_activation_returns_not_configured (test_activation_hydration.ActivationHydrationTests.test_missing_activation_returns_not_configured) ... ok`
- `test_persisted_selection_metadata_excludes_configuration_and_secrets (test_activation_hydration.ActivationHydrationTests.test_persisted_selection_metadata_excludes_configuration_and_secrets) ... ok`
- `test_unauthorized_source_cannot_read_activation_metadata (test_activation_hydration.ActivationHydrationTests.test_unauthorized_source_cannot_read_activation_metadata) ... ok`

CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## K8S-01

REMOVED_FROM_SCOPE. Verified (controlled; not genuine-provider or owner UAT).

Source: [backend/app/services/excluded_platforms.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/services/excluded_platforms.py); [backend/app/models/entities.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/models/entities.py)

Tests: [backend/tests/test_removed_platform_scope.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/tests/test_removed_platform_scope.py)

New baseline PostgreSQL run [backend-full.log](raw/regressions/backend-full.log):

- `test_configuration_depth_is_bounded (test_removed_platform_scope.OperationalConfigurationTests.test_configuration_depth_is_bounded) ... ok`
- `test_legacy_source_cannot_be_relabelled_by_collector (test_removed_platform_scope.OperationalConfigurationTests.test_legacy_source_cannot_be_relabelled_by_collector) ... ok`
- `test_nested_operational_aliases_rejected_without_erasing_generic_labels (test_removed_platform_scope.OperationalConfigurationTests.test_nested_operational_aliases_rejected_without_erasing_generic_labels) ... ok`
- `test_nested_source_template_and_collector_configs_are_rejected (test_removed_platform_scope.OperationalConfigurationTests.test_nested_source_template_and_collector_configs_are_rejected) ... ok`
- `test_no_cluster_routes_or_capabilities (test_removed_platform_scope.RemovedPlatformTests.test_no_cluster_routes_or_capabilities) ... ok`
- `test_removed_source_inputs_rejected (test_removed_platform_scope.RemovedPlatformTests.test_removed_source_inputs_rejected) ... ok`
- `test_supported_source_inputs_preserved (test_removed_platform_scope.RemovedPlatformTests.test_supported_source_inputs_preserved) ... ok`

CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## K8S-02

REMOVED_FROM_SCOPE. Verified (controlled; not genuine-provider or owner UAT).

Source: [backend/app/services/excluded_platforms.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/services/excluded_platforms.py); [backend/app/worker/remote_scheduler.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/worker/remote_scheduler.py)

Tests: [backend/tests/test_removed_platform_scope.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/tests/test_removed_platform_scope.py)

New baseline PostgreSQL run [backend-full.log](raw/regressions/backend-full.log):

- `test_configuration_depth_is_bounded (test_removed_platform_scope.OperationalConfigurationTests.test_configuration_depth_is_bounded) ... ok`
- `test_legacy_source_cannot_be_relabelled_by_collector (test_removed_platform_scope.OperationalConfigurationTests.test_legacy_source_cannot_be_relabelled_by_collector) ... ok`
- `test_nested_operational_aliases_rejected_without_erasing_generic_labels (test_removed_platform_scope.OperationalConfigurationTests.test_nested_operational_aliases_rejected_without_erasing_generic_labels) ... ok`
- `test_nested_source_template_and_collector_configs_are_rejected (test_removed_platform_scope.OperationalConfigurationTests.test_nested_source_template_and_collector_configs_are_rejected) ... ok`
- `test_no_cluster_routes_or_capabilities (test_removed_platform_scope.RemovedPlatformTests.test_no_cluster_routes_or_capabilities) ... ok`
- `test_removed_source_inputs_rejected (test_removed_platform_scope.RemovedPlatformTests.test_removed_source_inputs_rejected) ... ok`
- `test_supported_source_inputs_preserved (test_removed_platform_scope.RemovedPlatformTests.test_supported_source_inputs_preserved) ... ok`

CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## TOP-01

PARTIALLY_IMPLEMENTED. Unverified as complete requirement; bounded tests may pass.

Source: [backend/app/unified/reporting.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/unified/reporting.py)

Tests: [backend/tests/test_topology_traversal.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/tests/test_topology_traversal.py)

New baseline PostgreSQL run [backend-full.log](raw/regressions/backend-full.log):

- `test_concurrent_duplicate_creates_one_current_edge (test_topology_traversal.TopologyTraversalTests.test_concurrent_duplicate_creates_one_current_edge) ... ok`
- `test_deadlock_aborts_one_transaction_without_partial_edge (test_topology_traversal.TopologyTraversalTests.test_deadlock_aborts_one_transaction_without_partial_edge) ... ok`
- `test_eight_adversarial_concurrent_additions_remain_acyclic (test_topology_traversal.TopologyTraversalTests.test_eight_adversarial_concurrent_additions_remain_acyclic) ... ok`
- `test_lock_timeout_rolls_back_without_partial_edge (test_topology_traversal.TopologyTraversalTests.test_lock_timeout_rolls_back_without_partial_edge) ... ok`
- `test_paths_duplicates_and_rollback (test_topology_traversal.TopologyTraversalTests.test_paths_duplicates_and_rollback) ... ok`
- `test_resource_limit_rejects_hidden_parent_without_exposing_edges (test_topology_traversal.TopologyTraversalTests.test_resource_limit_rejects_hidden_parent_without_exposing_edges) ... ok`
- `test_validation_bound_allows_999_reachable_nodes_but_rejects_1000 (test_topology_traversal.TopologyTraversalTests.test_validation_bound_allows_999_reachable_nodes_but_rejects_1000) ... ok`

CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## OPS-01

PARTIALLY_IMPLEMENTED. Unverified as complete requirement; bounded tests may pass.

Source: [backend/app/worker/alert_engine.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/worker/alert_engine.py); [backend/app/worker/notifications.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/worker/notifications.py); [backend/app/native_incidents/service.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/native_incidents/service.py)

Tests: [backend/tests/test_in_app_notifications.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/tests/test_in_app_notifications.py); [backend/tests/test_notifications.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/tests/test_notifications.py)

New baseline PostgreSQL run [backend-full.log](raw/regressions/backend-full.log):

- `test_audience_respects_opt_out_and_current_customer_permission (test_in_app_notifications.RecipientTests.test_audience_respects_opt_out_and_current_customer_permission) ... ok`
- `test_authorized_active_recipient_accepted (test_in_app_notifications.RecipientTests.test_authorized_active_recipient_accepted) ... ok`
- `test_fanout_is_bounded_and_mismatched_evidence_rejected (test_in_app_notifications.RecipientTests.test_fanout_is_bounded_and_mismatched_evidence_rejected) ... ok`
- `test_inactive_foreign_provider_or_customer_denied (test_in_app_notifications.RecipientTests.test_inactive_foreign_provider_or_customer_denied) ... ok`
- `test_malformed_or_unbounded_targets_fail_validation (test_in_app_notifications.RecipientTests.test_malformed_or_unbounded_targets_fail_validation) ... ok`
- `test_plain_credentials_and_unknown_settings_rejected (test_in_app_notifications.RecipientTests.test_plain_credentials_and_unknown_settings_rejected) ... ok`
- `test_email_recipient_and_secret_boundaries (test_notifications.NotificationSecurityTests.test_email_recipient_and_secret_boundaries) ... ok`
- `test_idempotent_in_app_reference (test_notifications.NotificationSecurityTests.test_idempotent_in_app_reference) ... ok`
- `test_only_secure_webhooks (test_notifications.NotificationSecurityTests.test_only_secure_webhooks) ... ok`
- `test_provider_error_never_contains_secrets (test_notifications.NotificationSecurityTests.test_provider_error_never_contains_secrets) ... ok`
- `test_retired_itsm_cannot_deliver (test_notifications.NotificationSecurityTests.test_retired_itsm_cannot_deliver) ... ok`
- `test_valid_smtp_configuration_accepts_real_address_syntax (test_notifications.NotificationSecurityTests.test_valid_smtp_configuration_accepts_real_address_syntax) ... ok`

CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## OPS-02

BLOCKED_ARCHITECTURE. Unverified as complete requirement; bounded tests may pass.

Source: [backend/app/unified/reporting.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/unified/reporting.py)

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## OPS-03

VERIFIED_PENDING_OWNER. Verified (controlled; not genuine-provider or owner UAT).

Source: [backend/app/worker/alert_engine.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/worker/alert_engine.py); [backend/app/native_incidents/service.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/native_incidents/service.py)

Tests: [backend/tests/test_native_incidents_v15.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/tests/test_native_incidents_v15.py)

New baseline PostgreSQL run [backend-full.log](raw/regressions/backend-full.log):

- `test_acknowledgement_requires_exact_permission (test_native_incidents_v15.NativeRecoveryTests.test_acknowledgement_requires_exact_permission) ... ok`
- `test_active_or_evidenceless_condition_blocks (test_native_incidents_v15.NativeRecoveryTests.test_active_or_evidenceless_condition_blocks) ... ok`
- `test_authorized_transition_uses_authenticated_actor (test_native_incidents_v15.NativeRecoveryTests.test_authorized_transition_uses_authenticated_actor) ... ok`
- `test_duplicate_worker_lease_performs_no_writes (test_native_incidents_v15.NativeRecoveryTests.test_duplicate_worker_lease_performs_no_writes) ... ok`
- `test_empty_evidence_never_proves_recovery (test_native_incidents_v15.NativeRecoveryTests.test_empty_evidence_never_proves_recovery) ... ok`
- `test_future_evidence_cannot_verify (test_native_incidents_v15.NativeRecoveryTests.test_future_evidence_cannot_verify) ... ok`
- `test_mass_assignment_is_rejected (test_native_incidents_v15.NativeRecoveryTests.test_mass_assignment_is_rejected) ... ok`
- `test_observation_window_cannot_be_skipped (test_native_incidents_v15.NativeRecoveryTests.test_observation_window_cannot_be_skipped) ... ok`
- `test_open_alert_blocks (test_native_incidents_v15.NativeRecoveryTests.test_open_alert_blocks) ... ok`
- `test_pending_detail_is_reused_before_flush (test_native_incidents_v15.NativeRecoveryTests.test_pending_detail_is_reused_before_flush) ... ok`
- `test_recovery_failure_preserves_state (test_native_incidents_v15.NativeRecoveryTests.test_recovery_failure_preserves_state) ... ok`
- `test_recovery_rejects_nan_sample (test_native_incidents_v15.NativeRecoveryTests.test_recovery_rejects_nan_sample) ... ok`
- `test_recovery_rejects_resolved_transient_rebreach (test_native_incidents_v15.NativeRecoveryTests.test_recovery_rejects_resolved_transient_rebreach) ... ok`
- `test_recovery_rejects_unhealthy_sample_inside_window (test_native_incidents_v15.NativeRecoveryTests.test_recovery_rejects_unhealthy_sample_inside_window) ... ok`
- `test_service_denies_cross_customer (test_native_incidents_v15.NativeRecoveryTests.test_service_denies_cross_customer) ... ok`
- `test_service_denies_unauthenticated (test_native_incidents_v15.NativeRecoveryTests.test_service_denies_unauthenticated) ... ok`
- `test_stable_fresh_resolved_evidence_verifies (test_native_incidents_v15.NativeRecoveryTests.test_stable_fresh_resolved_evidence_verifies) ... ok`
- `test_stale_alert_uses_real_fresh_condition (test_native_incidents_v15.NativeRecoveryTests.test_stale_alert_uses_real_fresh_condition) ... ok`
- `test_stale_revision_preserves_state (test_native_incidents_v15.NativeRecoveryTests.test_stale_revision_preserves_state) ... ok`
- `test_state_graph_forbids_unverified_shortcuts (test_native_incidents_v15.NativeRecoveryTests.test_state_graph_forbids_unverified_shortcuts) ... ok`

CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## OPS-04

PARTIALLY_IMPLEMENTED. Unverified as complete requirement; bounded tests may pass.

Source: [backend/app/unified/reporting.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/unified/reporting.py); [frontend/src/pages/Reports.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/pages/Reports.jsx)

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## PLT-01

PARTIALLY_IMPLEMENTED. Unverified as complete requirement; bounded tests may pass.

Source: [backend/scripts/database_backup.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/scripts/database_backup.py)

Tests: [backend/tests/test_sprint13_recovery_probe.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/tests/test_sprint13_recovery_probe.py)

New baseline PostgreSQL run [backend-full.log](raw/regressions/backend-full.log):

- `test_earlier_guard_rolls_back_the_whole_downgrade (test_sprint13_recovery_probe.PreservedDowngradeTests.test_earlier_guard_rolls_back_the_whole_downgrade) ... ok`
- `test_kubernetes_history_guard_keeps_current_revision (test_sprint13_recovery_probe.PreservedDowngradeTests.test_kubernetes_history_guard_keeps_current_revision) ... ok`
- `test_unknown_failure_or_changed_revision_is_not_preservation (test_sprint13_recovery_probe.PreservedDowngradeTests.test_unknown_failure_or_changed_revision_is_not_preservation) ... ok`

CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## PLT-02

PARTIALLY_IMPLEMENTED. Unverified as complete requirement; bounded tests may pass.

Source: [scripts/uat/stage_b_deploy.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/scripts/uat/stage_b_deploy.py); [scripts/uat/stage_b_state.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/scripts/uat/stage_b_state.py)

Tests: `scripts/uat/test_stage_b.py`: new controlled run **12 PASS, 0 FAIL, 0 SKIP**, [raw log](raw/stageb.log). State/backup/migration contracts only; live pilot NOT TESTED.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## PLT-03

BLOCKED_SECURITY. Unverified as complete requirement; bounded tests may pass.

Source: [backend/app/security/deployment.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/security/deployment.py); [backend/app/core/config.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/core/config.py)

Tests: [backend/tests/test_remote_auth.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/tests/test_remote_auth.py)

New baseline PostgreSQL run [backend-full.log](raw/regressions/backend-full.log):

- `test_approved_reference_sends_basic_only_to_pinned_verified_transport (test_remote_auth.RemoteBasicAuthTests.test_approved_reference_sends_basic_only_to_pinned_verified_transport) ... ok`
- `test_colon_account_rejected_before_transport (test_remote_auth.RemoteBasicAuthTests.test_colon_account_rejected_before_transport) ... ok`
- `test_reference_validation_never_resolves_credentials (test_remote_auth.RemoteBasicAuthTests.test_reference_validation_never_resolves_credentials) ... ok`
- `test_unapproved_reference_is_denied_before_secret_retrieval_and_transport (test_remote_auth.RemoteBasicAuthTests.test_unapproved_reference_is_denied_before_secret_retrieval_and_transport) ... ok`

CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## PLT-04

PARTIALLY_IMPLEMENTED. Unverified as complete requirement; bounded tests may pass.

Source: [frontend/src/pagination.js](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/pagination.js); [backend/app/worker/remote_scheduler.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/worker/remote_scheduler.py)

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## UI-001

IMPLEMENTED_UNVERIFIED. Unverified as complete requirement; bounded tests may pass.

Source: [frontend/src/App.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/App.jsx); [frontend/src/components/TopNav.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/components/TopNav.jsx); [frontend/src/navigation.js](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/navigation.js)

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## UI-002

IMPLEMENTED_UNVERIFIED. Unverified as complete requirement; bounded tests may pass.

Source: [frontend/src/pages/UnifiedResourceManagement.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/pages/UnifiedResourceManagement.jsx)

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## UI-003

IMPLEMENTED_UNVERIFIED. Unverified as complete requirement; bounded tests may pass.

Source: [backend/app/registry/api.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/registry/api.py); [frontend/src/pages/UnifiedResourceManagement.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/pages/UnifiedResourceManagement.jsx)

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## UI-004

IMPLEMENTED_UNVERIFIED. Unverified as complete requirement; bounded tests may pass.

Source: [frontend/src/pages/UnifiedResourceManagement.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/pages/UnifiedResourceManagement.jsx); [frontend/src/resource-v2.css](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/resource-v2.css)

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## UI-005

PARTIALLY_IMPLEMENTED. Unverified as complete requirement; bounded tests may pass.

Source: [frontend/src/resource-v2.css](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/resource-v2.css); [frontend/src/visual-system.css](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/visual-system.css)

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## UI-006

PARTIALLY_IMPLEMENTED. Unverified as complete requirement; bounded tests may pass.

Source: [frontend/src/pages/UnifiedResourceManagement.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/pages/UnifiedResourceManagement.jsx)

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## UI-007

PARTIALLY_IMPLEMENTED. Unverified as complete requirement; bounded tests may pass.

Source: [backend/app/registry/api.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/registry/api.py); [backend/app/unified/api.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/unified/api.py); [frontend/src/resourceApi.js](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/resourceApi.js)

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## UI-008

IMPLEMENTED_UNVERIFIED. Unverified as complete requirement; bounded tests may pass.

Source: [backend/app/telemetry/api.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/telemetry/api.py); [frontend/src/pages/CollectorControl.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/pages/CollectorControl.jsx); [scripts/access-acceptance.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/scripts/access-acceptance.py)

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## UI-009

PARTIALLY_IMPLEMENTED. Unverified as complete requirement; bounded tests may pass.

Source: [backend/app/unified/api.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/unified/api.py); [scripts/arch001-acceptance.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/scripts/arch001-acceptance.py)

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## UI-010

VERIFIED_PENDING_OWNER. Verified (controlled; not genuine-provider or owner UAT).

Source: [backend/app/models/entities.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/models/entities.py); [backend/app/security/access_models.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/security/access_models.py); [scripts/access-acceptance.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/scripts/access-acceptance.py)

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## UI-011

IMPLEMENTED_UNVERIFIED. Unverified as complete requirement; bounded tests may pass.

Source: [frontend/src/navigation.js](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/navigation.js)

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## UI-012

PARTIALLY_IMPLEMENTED. Unverified as complete requirement; bounded tests may pass.

Source: [frontend/src/components/TopNav.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/components/TopNav.jsx); [frontend/src/theme.js](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/theme.js); [frontend/src/visual-system.css](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/visual-system.css)

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## UI-013

PARTIALLY_IMPLEMENTED. Unverified as complete requirement; bounded tests may pass.

Source: [frontend/src/pages/DataPipelineIntegrations.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/pages/DataPipelineIntegrations.jsx); [frontend/src/pages/UnifiedResourceManagement.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/pages/UnifiedResourceManagement.jsx)

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## UI-014

IMPLEMENTED_UNVERIFIED. Unverified as complete requirement; bounded tests may pass.

Source: [frontend/src/access-management.css](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/access-management.css); [frontend/src/pages/AccessBoundaries.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/pages/AccessBoundaries.jsx); [scripts/access-acceptance.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/scripts/access-acceptance.py)

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## UI-015

PARTIALLY_IMPLEMENTED. Unverified as complete requirement; bounded tests may pass.

Source: [backend/app/api/access.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/api/access.py); [frontend/src/pages/AccessManagement.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/pages/AccessManagement.jsx); [scripts/access-acceptance.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/scripts/access-acceptance.py)

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## UI-016

IMPLEMENTED_UNVERIFIED. Unverified as complete requirement; bounded tests may pass.

Source: [backend/app/unified/reporting.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/unified/reporting.py); [frontend/src/pages/UnifiedOverview.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/pages/UnifiedOverview.jsx)

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## UI-017

IMPLEMENTED_UNVERIFIED. Unverified as complete requirement; bounded tests may pass.

Source: [frontend/src/pages/DomainMonitoring.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/pages/DomainMonitoring.jsx); [frontend/src/pages/VMHealth.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/pages/VMHealth.jsx); [scripts/infrastructure-acceptance.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/scripts/infrastructure-acceptance.py)

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## UI-018

IMPLEMENTED_UNVERIFIED. Unverified as complete requirement; bounded tests may pass.

Source: [frontend/src/pipelines/PipelineWorkspace.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/pipelines/PipelineWorkspace.jsx); [frontend/src/pipelines/pipelines.css](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/pipelines/pipelines.css)

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## UI-019

IMPLEMENTED_UNVERIFIED. Unverified as complete requirement; bounded tests may pass.

Source: [frontend/src/pages/APIs.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/pages/APIs.jsx); [frontend/src/pages/DomainMonitoring.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/pages/DomainMonitoring.jsx); [scripts/release-acceptance.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/scripts/release-acceptance.py)

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## UI-020

PARTIALLY_IMPLEMENTED. Unverified as complete requirement; bounded tests may pass.

Source: [frontend/src/pages/Alerts.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/pages/Alerts.jsx)

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## UI-021

PARTIALLY_IMPLEMENTED. Unverified as complete requirement; bounded tests may pass.

Source: [backend/app/native_incidents/api.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/app/native_incidents/api.py); [backend/tests/test_native_incidents_v15.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/tests/test_native_incidents_v15.py); [frontend/src/pages/NativeIncidents.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/pages/NativeIncidents.jsx)

Tests: [backend/tests/test_native_incidents_v15.py](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/backend/tests/test_native_incidents_v15.py)

New baseline PostgreSQL run [backend-full.log](raw/regressions/backend-full.log):

- `test_acknowledgement_requires_exact_permission (test_native_incidents_v15.NativeRecoveryTests.test_acknowledgement_requires_exact_permission) ... ok`
- `test_active_or_evidenceless_condition_blocks (test_native_incidents_v15.NativeRecoveryTests.test_active_or_evidenceless_condition_blocks) ... ok`
- `test_authorized_transition_uses_authenticated_actor (test_native_incidents_v15.NativeRecoveryTests.test_authorized_transition_uses_authenticated_actor) ... ok`
- `test_duplicate_worker_lease_performs_no_writes (test_native_incidents_v15.NativeRecoveryTests.test_duplicate_worker_lease_performs_no_writes) ... ok`
- `test_empty_evidence_never_proves_recovery (test_native_incidents_v15.NativeRecoveryTests.test_empty_evidence_never_proves_recovery) ... ok`
- `test_future_evidence_cannot_verify (test_native_incidents_v15.NativeRecoveryTests.test_future_evidence_cannot_verify) ... ok`
- `test_mass_assignment_is_rejected (test_native_incidents_v15.NativeRecoveryTests.test_mass_assignment_is_rejected) ... ok`
- `test_observation_window_cannot_be_skipped (test_native_incidents_v15.NativeRecoveryTests.test_observation_window_cannot_be_skipped) ... ok`
- `test_open_alert_blocks (test_native_incidents_v15.NativeRecoveryTests.test_open_alert_blocks) ... ok`
- `test_pending_detail_is_reused_before_flush (test_native_incidents_v15.NativeRecoveryTests.test_pending_detail_is_reused_before_flush) ... ok`
- `test_recovery_failure_preserves_state (test_native_incidents_v15.NativeRecoveryTests.test_recovery_failure_preserves_state) ... ok`
- `test_recovery_rejects_nan_sample (test_native_incidents_v15.NativeRecoveryTests.test_recovery_rejects_nan_sample) ... ok`
- `test_recovery_rejects_resolved_transient_rebreach (test_native_incidents_v15.NativeRecoveryTests.test_recovery_rejects_resolved_transient_rebreach) ... ok`
- `test_recovery_rejects_unhealthy_sample_inside_window (test_native_incidents_v15.NativeRecoveryTests.test_recovery_rejects_unhealthy_sample_inside_window) ... ok`
- `test_service_denies_cross_customer (test_native_incidents_v15.NativeRecoveryTests.test_service_denies_cross_customer) ... ok`
- `test_service_denies_unauthenticated (test_native_incidents_v15.NativeRecoveryTests.test_service_denies_unauthenticated) ... ok`
- `test_stable_fresh_resolved_evidence_verifies (test_native_incidents_v15.NativeRecoveryTests.test_stable_fresh_resolved_evidence_verifies) ... ok`
- `test_stale_alert_uses_real_fresh_condition (test_native_incidents_v15.NativeRecoveryTests.test_stale_alert_uses_real_fresh_condition) ... ok`
- `test_stale_revision_preserves_state (test_native_incidents_v15.NativeRecoveryTests.test_stale_revision_preserves_state) ... ok`
- `test_state_graph_forbids_unverified_shortcuts (test_native_incidents_v15.NativeRecoveryTests.test_state_graph_forbids_unverified_shortcuts) ... ok`

CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## UI-022

IMPLEMENTED_UNVERIFIED. Unverified as complete requirement; bounded tests may pass.

Source: [frontend/src/navigation.js](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/navigation.js); [frontend/src/pages/UnifiedResourceManagement.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/pages/UnifiedResourceManagement.jsx)

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## UI-023

PARTIALLY_IMPLEMENTED. Unverified as complete requirement; bounded tests may pass.

Source: [frontend/src/pages/MonitoringSetup.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/pages/MonitoringSetup.jsx); [frontend/src/pages/UnifiedResourceManagement.jsx](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/a2f7460904fbab2a99c258616516054f21689687/frontend/src/pages/UnifiedResourceManagement.jsx)

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## OC-IMP-001

BLOCKED_ARCHITECTURE. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## OC-IMP-002

BLOCKED_ARCHITECTURE. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## OC-IMP-003

BLOCKED_ARCHITECTURE. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## OC-IMP-004

BLOCKED_ARCHITECTURE. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## OC-IMP-005

BLOCKED_ARCHITECTURE. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## OC-IMP-006

BLOCKED_ARCHITECTURE. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## OC-IMP-007

BLOCKED_ARCHITECTURE. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## OC-IMP-008

BLOCKED_ARCHITECTURE. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## OC-IMP-009

BLOCKED_ARCHITECTURE. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## OC-IMP-010

BLOCKED_ARCHITECTURE. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## OC-IMP-011

BLOCKED_ARCHITECTURE. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## OC-IMP-012

BLOCKED_ARCHITECTURE. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## OC-IMP-013

BLOCKED_ARCHITECTURE. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## OC-IMP-014

BLOCKED_ARCHITECTURE. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## OC-IMP-015

BLOCKED_ARCHITECTURE. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## OC-IMP-016

BLOCKED_ARCHITECTURE. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## OC-IMP-017

SUPERSEDED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## OC-IMP-018

BLOCKED_ARCHITECTURE. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-001

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-002

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-003

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-004

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-005

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-006

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-007

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-008

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-009

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-010

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-011

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-012

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-013

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-014

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-015

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-016

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-017

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-018

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-019

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-020

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-021

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-022

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-023

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-024

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-025

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-026

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-027

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-028

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-029

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-030

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-031

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-032

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-033

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-034

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-035

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-036

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-037

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-038

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-039

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-040

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-041

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-042

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-043

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-044

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-045

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-046

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-047

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-048

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-049

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-050

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-051

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-052

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-053

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-054

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-055

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-056

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-057

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-058

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-059

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-060

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-061

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

## IMP-062

SOURCE_NOT_RECOVERED. Not tested — missing authority.

Source: No authoritative source mapping; see requirements.json authority/trace and next action.

Tests: No requirement-complete execution mapping established; retained historical traces are not promoted.


CI: raw/main-checks.json at a2f7460904fbab2a99c258616516054f21689687; suite result is not per-feature owner acceptance.

See [capability coverage](CAPABILITY_COVERAGE.md) for monitoring signals, integrations, operations pages, template/version and enterprise-path details.
