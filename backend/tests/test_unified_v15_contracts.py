"""Security and semantic service-unit contracts; SQL stubs do not prove persistence."""

import json
import unittest
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace as Row
from unittest.mock import Mock, patch
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql

from app.models import Collector, DataSource, JobOrder, VM
from app.pipeline_adapters import AdapterError
from app.security.scope import Principal, current_principal
from app.unified import api, reporting
from app.unified.normalization import NormalizationError, normalize, timestamp
from app.unified.schemas import (
    APICreate,
    DuplicateMatching,
    LogParser,
    Threshold,
    validate_parameters,
)


class UnifiedServiceContracts(unittest.TestCase):
    def setUp(self):
        self.org, self.id = uuid4(), uuid4()
        self.root = Row(
            id=self.id,
            organization_id=self.org,
            domain="VM",
            revision=3,
            name="Compute",
            environment="QA",
            configuration={
                "hostname": "unit-host",
                "address": "unit-host.example.test",
                "os_type": "Linux",
                "alert_setup": {"enabled": True, "revision": 2},
                "log_method_ids": [str(uuid4())],
            },
            active=True,
            activation_status="ACTIVE",
            vm_id=uuid4(),
            data_source_id=uuid4(),
            primary_collector_id=uuid4(),
            job_order_id=None,
            linked_vm_id=None,
        )
        self.vm = Row(hostname="unit-host", environment="QA", monitoring_enabled=True)
        self.source = Row(
            endpoint="unit-host.example.test",
            connection_config={"opscontrol": {"os_type": "Linux", "environment": "QA"}},
            enabled=True,
        )
        self.collector = Row(
            configuration={"existing_runtime": "preserved"}, enabled=True
        )
        self.db = Mock()
        self.db.get.side_effect = lambda model, id: {
            VM: self.vm,
            DataSource: self.source,
            Collector: self.collector,
        }.get(model)
        self.db.scalars.return_value = []
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(api, "resource", return_value=self.root))
        self.stack.enter_context(patch.object(api, "audit"))
        self.committed = self.stack.enter_context(patch.object(api, "commit"))
        self.stack.enter_context(
            patch.object(
                api,
                "output",
                side_effect=lambda db, root: {"id": root.id, "active": root.active},
            )
        )
        token = current_principal.set(
            Principal(uuid4(), "unit-admin", True, {}, service_provider_id=uuid4())
        )
        self.addCleanup(current_principal.reset, token)

    def edit_payload(self, configuration=None, **changes):
        base = {
            "hostname": "unit-host",
            "address": "unit-host.example.test",
            "os_type": "Linux",
        }
        return api.ResourceEdit(
            expected_revision=3,
            name="Edited Compute",
            environment="QA",
            configuration=configuration if configuration is not None else base,
            **changes
        )

    def test_generic_edit_preserves_internal_alert_setup_and_bound_log_method_ids(self):
        original = dict(self.root.configuration)
        api.edit(self.id, self.edit_payload(), self.db)
        self.assertEqual(
            self.root.configuration["alert_setup"], original["alert_setup"]
        )
        self.assertEqual(
            self.root.configuration["log_method_ids"], original["log_method_ids"]
        )
        self.assertEqual(self.root.revision, 4)
        self.assertEqual(self.collector.configuration["existing_runtime"], "preserved")
        self.committed.assert_called_once()

    def test_generic_edit_cannot_escalate_or_erase_internal_alert_policy(self):
        for key, value in (
            ("alert_setup", {"enabled": False}),
            ("alert_setup", None),
            ("log_method_ids", []),
        ):
            with self.subTest(key=key, value=value):
                payload = self.edit_payload(
                    {
                        "hostname": "unit-host",
                        "address": "unit-host.example.test",
                        "os_type": "Linux",
                        key: value,
                    }
                )
                with self.assertRaises(HTTPException) as caught:
                    api.edit(self.id, payload, self.db)
                self.assertEqual(caught.exception.status_code, 403)
                self.assertEqual(self.root.revision, 3)
        self.committed.assert_not_called()

    def test_echoing_exact_internal_state_is_compatible_without_creating_privileges(
        self,
    ):
        api.edit(self.id, self.edit_payload(dict(self.root.configuration)), self.db)
        self.assertTrue(self.root.configuration["alert_setup"]["enabled"])
        self.assertEqual(self.root.configuration["alert_setup"]["revision"], 2)

    def test_stale_resource_revision_fails_before_making_any_changes(self):
        payload = self.edit_payload().model_copy(update={"expected_revision": 2})
        with self.assertRaises(HTTPException) as caught:
            api.edit(self.id, payload, self.db)
        self.assertEqual(caught.exception.status_code, 409)
        self.db.get.assert_not_called()
        self.committed.assert_not_called()

    def test_host_identity_and_os_cannot_be_repurposed_by_edit(self):
        for change in ({"hostname": "new-host"}, {"os_type": "Windows"}):
            configuration = {
                "hostname": "unit-host",
                "address": "unit-host.example.test",
                "os_type": "Linux",
                **change,
            }
            with self.subTest(change=change), self.assertRaises(
                HTTPException
            ) as caught:
                api.edit(self.id, self.edit_payload(configuration), self.db)
            self.assertEqual(caught.exception.status_code, 409)
        self.committed.assert_not_called()

    def test_pause_stops_source_collector_and_vm_without_erasing_history_or_policy(
        self,
    ):
        api.edit(self.id, self.edit_payload(active=False), self.db)
        self.assertEqual(self.root.activation_status, "PAUSED")
        self.assertFalse(self.source.enabled)
        self.assertFalse(self.collector.enabled)
        self.assertFalse(self.vm.monitoring_enabled)
        self.assertTrue(self.root.configuration["alert_setup"]["enabled"])

    def test_environment_propagation_retains_child_threshold_overrides(self):
        child = Row(
            domain="ETL",
            environment="QA",
            revision=5,
            job_order_id=uuid4(),
            data_source_id=None,
            configuration={"threshold_override": {"long_running_seconds": 42}},
        )
        job = Row(environment="QA")
        original_get = self.db.get.side_effect
        self.db.get.side_effect = lambda model, id: (
            job if model is JobOrder else original_get(model, id)
        )
        self.db.scalars.return_value = [child]
        payload = self.edit_payload().model_copy(update={"environment": "TEST"})
        api.edit(self.id, payload, self.db)
        self.assertEqual(
            (child.environment, job.environment, child.revision), ("TEST", "TEST", 6)
        )
        self.assertEqual(
            child.configuration["threshold_override"]["long_running_seconds"], 42
        )

    def test_monitoring_activation_does_not_require_optional_parameters_or_alert_setup(
        self,
    ):
        self.root.configuration = {}
        with patch(
            "app.unified.engines.source_readiness",
            return_value={"ready": True, "evidence_origin": "UNIT_READINESS_BOUNDARY"},
        ):
            api.activate_resource(self.id, api.Approval(approve=True), self.db)
        self.assertTrue(self.vm.monitoring_enabled)
        self.assertEqual(self.root.activation_status, "ACTIVE")
        self.committed.assert_called_once()

    def test_activation_requires_approval_and_actual_readiness_boundary(self):
        with self.assertRaises(HTTPException) as caught:
            api.activate_resource(self.id, api.Approval(approve=False), self.db)
        self.assertEqual(caught.exception.status_code, 422)
        with patch(
            "app.unified.engines.source_readiness",
            return_value={"ready": False, "missing": ["actual telemetry"]},
        ), self.assertRaises(HTTPException) as caught:
            api.activate_resource(self.id, api.Approval(approve=True), self.db)
        self.assertEqual(caught.exception.status_code, 409)
        self.committed.assert_not_called()

    def test_metric_selection_cannot_reference_another_customer_or_source(self):
        metric_id = uuid4()
        config = {
            "thresholds": [
                {
                    "metric_definition_id": str(metric_id),
                    "metric_name": "cpu",
                    "critical": 80,
                    "unit": "%",
                }
            ]
        }
        for metric in (
            None,
            Row(
                organization_id=uuid4(),
                data_source_id=self.root.data_source_id,
                metric_type="GAUGE",
                unit="%",
            ),
            Row(
                organization_id=self.org,
                data_source_id=uuid4(),
                metric_type="GAUGE",
                unit="%",
            ),
            Row(
                organization_id=self.org,
                data_source_id=self.root.data_source_id,
                metric_type="DERIVED_CONDITION",
                unit="%",
            ),
            Row(
                organization_id=self.org,
                data_source_id=self.root.data_source_id,
                metric_type="GAUGE",
                unit="bytes",
            ),
        ):
            self.db.get.side_effect = None
            self.db.get.return_value = metric
            with self.subTest(metric=metric), self.assertRaises(
                HTTPException
            ) as caught:
                api.checked_resource_parameters(self.db, self.root, config)
            self.assertEqual(caught.exception.status_code, 422)

    def test_native_connection_failure_is_not_success_and_never_echoes_secret_error(
        self,
    ):
        self.root.domain = "ETL"
        self.root.configuration = {
            "platform": "IICS",
            "integration_configuration": {"base_url": "https://example.test"},
        }
        with patch(
            "app.pipeline_adapters.test_platform_connection",
            side_effect=AdapterError("AUTHENTICATION", "private-provider-secret"),
        ), patch.object(api, "log_event") as logged:
            result = api.test_connection(self.id, self.db)
        self.assertEqual(
            result,
            {
                "connected": False,
                "error_kind": "AUTHENTICATION",
                "live_verified": False,
            },
        )
        self.assertEqual(logged.call_args.kwargs["outcome"], "FAILURE")
        self.db.commit.assert_called_once()

    def test_native_connection_requires_configured_pipeline_and_collectors_authority(
        self,
    ):
        with self.assertRaises(HTTPException) as caught:
            api.test_connection(self.id, self.db)
        self.assertEqual(caught.exception.status_code, 422)
        token = current_principal.set(
            Principal(
                uuid4(),
                "unit-reader",
                False,
                {},
                service_provider_id=uuid4(),
                customer_permissions={self.org: frozenset({"etl.configure"})},
            )
        )
        try:
            with self.assertRaises(HTTPException) as caught:
                api.test_connection(self.id, self.db)
            self.assertEqual(caught.exception.status_code, 403)
        finally:
            current_principal.reset(token)

    def test_enabled_alert_setup_requires_active_version_and_same_customer_destination(
        self,
    ):
        self.db.scalar.return_value = None
        with self.assertRaises(HTTPException) as caught:
            api.save_alert_setup(self.id, api.NativeAlertSetup(enabled=True), self.db)
        self.assertEqual(caught.exception.status_code, 422)
        target = uuid4()
        self.db.get.side_effect = None
        self.db.get.return_value = Row(organization_id=uuid4(), enabled=True)
        with self.assertRaises(HTTPException) as caught:
            api.save_alert_setup(
                self.id,
                api.NativeAlertSetup(enabled=False, destinations=[target]),
                self.db,
            )
        self.assertEqual(caught.exception.status_code, 422)
        self.committed.assert_not_called()


class ParameterSafetyContracts(unittest.TestCase):
    def test_overrides_cannot_change_identity_or_bypass_threshold_validation(self):
        for domain in ("VM", "ETL", "API"):
            for key in ("organization_id", "environment", "resource_id", "platform"):
                with self.subTest(domain=domain, key=key), self.assertRaises(
                    ValueError
                ):
                    validate_parameters(domain, {"overrides": {key: "injected"}})
        with self.assertRaises(ValidationError):
            validate_parameters(
                "API",
                {
                    "overrides": {
                        "warning_latency_ms": 5000,
                        "critical_latency_ms": 1000,
                    }
                },
            )
        config = validate_parameters(
            "ETL",
            {"long_running_seconds": 100, "overrides": {"long_running_seconds": 200}},
        )
        self.assertEqual(config["long_running_seconds"], 200)
        self.assertEqual(config["overrides"]["long_running_seconds"], 200)

    def test_percentage_and_recovery_direction_require_finite_coherent_values(self):
        for change in (
            {"critical": float("nan")},
            {"critical": float("inf")},
            {"critical": 101},
            {"warning": 90},
            {"recovery": 90},
        ):
            with self.subTest(change=change), self.assertRaises(ValidationError):
                Threshold(metric_name="cpu", unit="%", **{"critical": 80, **change})
        with self.assertRaises(ValidationError):
            Threshold(
                metric_name="disk.free",
                unit="bytes",
                operator="LT",
                critical=100,
                warning=90,
            )
        with self.assertRaises(ValidationError):
            Threshold(
                metric_name="disk.free",
                unit="bytes",
                operator="LT",
                critical=100,
                recovery=90,
            )
        self.assertEqual(
            Threshold(metric_name="cpu", unit="%", critical=80, recovery=60).recovery,
            60,
        )

    def test_duplicate_matching_never_uses_only_message_or_jobchain(self):
        for configuration in (
            {"attributes": ["jobchain"]},
            {"attributes": ["execution_id", "execution_id"]},
            {"conflict_resolution": "PREFER_CONFIGURED_SOURCE"},
        ):
            with self.subTest(configuration=configuration), self.assertRaises(
                ValidationError
            ):
                DuplicateMatching(**configuration)
        matching = DuplicateMatching(
            attributes=["order_id", "jobchain"],
            conflict_resolution="PREFER_CONFIGURED_SOURCE",
            source_precedence=["provider"],
        )
        self.assertEqual(matching.source_precedence, ["provider"])

    def test_api_configuration_rejects_tls_disable_auth_over_http_and_header_injection(
        self,
    ):
        base = {
            "name": "Endpoint",
            "organization_id": uuid4(),
            "environment": "QA",
            "dns": "api.example.test",
        }
        for change in (
            {"tls_validation": False},
            {
                "auth_type": "BASIC",
                "protocol": "HTTP",
                "credential_ref": "env:TEST_REF",
            },
            {"headers": {"Authorization": "raw-token"}},
            {"headers": {"X-Test": "unsafe\r\nInjected:true"}},
            {"path": "/#fragment"},
            {"dns": "https://api.example.test"},
        ):
            with self.subTest(change=change), self.assertRaises(ValidationError):
                APICreate(**{**base, **change})


class NormalizationAndReportContracts(unittest.TestCase):
    def setUp(self):
        self.observed = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def event(self, **changes):
        return {
            "execution_id": "run1",
            "event": "END",
            "status": "SUCCESS",
            "timestamp": "2026-01-01T00:00:00Z",
            **changes,
        }

    def test_timestamp_parsing_preserves_timezone_and_rejects_nonexistent_dst(self):
        self.assertEqual(
            timestamp("1767225600000", LogParser(timestamp_format="epoch_millis")),
            self.observed,
        )
        self.assertEqual(
            timestamp("1767225600", LogParser(timestamp_format="epoch_seconds")),
            self.observed,
        )
        self.assertEqual(
            timestamp(
                "2026-01-01 05:30:00",
                LogParser(
                    timestamp_format="%Y-%m-%d %H:%M:%S", timezone="Asia/Kolkata"
                ),
            ),
            self.observed,
        )
        for value, parser in (
            (None, LogParser()),
            ("invalid", LogParser()),
            ("2026-03-08T02:30:00", LogParser(timezone="America/New_York")),
        ):
            with self.subTest(value=value), self.assertRaises(NormalizationError):
                timestamp(value, parser)

    def test_event_identity_retry_and_execution_mode_rejections_are_explicit(self):
        for change, kind in (
            ({"execution_id": ""}, "EXECUTION_IDENTITY_REQUIRED"),
            ({"execution_id": "x" * 201}, "EXECUTION_IDENTITY_TOO_LONG"),
            ({"attempt": "not-an-int"}, "INVALID_ATTEMPT"),
            ({"attempt": 10001}, "INVALID_ATTEMPT"),
            ({"jobchain": "another"}, "OTHER_JOBCHAIN"),
            ({"execution_type": "INVENTED"}, "UNMAPPED_EXECUTION_TYPE"),
            (
                {"event": "STEP_FAILED", "step_id": None, "step_name": None},
                "STEP_IDENTITY_REQUIRED",
            ),
        ):
            with self.subTest(kind=kind), self.assertRaisesRegex(
                NormalizationError, kind
            ):
                normalize(self.event(**change), {}, self.observed, "Job")
        first, _ = normalize(
            self.event(order_id="native-order", attempt=2, execution_type="MANUAL"),
            {},
            self.observed,
            "Job",
        )
        self.assertEqual(
            (
                first["execution_id"],
                first["native_order_id"],
                first["attempt"],
                first["execution_type"],
            ),
            ("native-order", "native-order", 2, "MANUAL"),
        )

    def test_malformed_document_and_regex_mismatch_are_not_fabricated_executions(self):
        for message in ("not-json", json.dumps(["not-an-object"])):
            with self.assertRaises(NormalizationError):
                normalize(message, {}, self.observed, "Job")
        with self.assertRaisesRegex(NormalizationError, "PARSER_NOT_MATCHED"):
            normalize(
                "irrelevant line",
                {"format": "REGEX", "pattern": r"(?P<execution_id>run-\d+)"},
                self.observed,
                "Job",
            )

    def test_report_range_requires_aware_ordered_bounded_dates(self):
        for start, end in (
            (datetime(2026, 1, 1), self.observed),
            (self.observed, self.observed),
            (self.observed + timedelta(days=1), self.observed),
            (self.observed, self.observed + timedelta(days=367)),
        ):
            with self.subTest(start=start, end=end), self.assertRaises(
                HTTPException
            ) as caught:
                reporting.range_bounds(start, end)
            self.assertEqual(caught.exception.status_code, 422)
        start, end = reporting.range_bounds(None, self.observed)
        self.assertEqual(end - start, timedelta(days=7))

    def test_report_query_contains_customer_resource_environment_and_domain_filters(
        self,
    ):
        org, resource = uuid4(), uuid4()
        query = reporting.root_query([org], "QA", [resource], "ETL").compile(
            dialect=postgresql.dialect()
        )
        self.assertEqual(
            set(query.params),
            {"organization_id_1", "environment_1", "id_1", "domain_1"},
        )
        self.assertEqual(query.params["organization_id_1"], [org])
        self.assertEqual(query.params["id_1"], [resource])
        self.assertEqual(query.params["environment_1"], "QA")
        multi_query = reporting.root_query(
            [org], None, [resource], "ETL", ["QA", "DEV"]
        ).compile(dialect=postgresql.dialect())
        self.assertEqual(multi_query.params["environment_1"], ["QA", "DEV"])
