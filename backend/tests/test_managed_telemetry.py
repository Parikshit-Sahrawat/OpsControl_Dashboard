"""Real configuration and security contracts for the managed telemetry slice."""

import unittest, yaml
from types import SimpleNamespace as S
from uuid import uuid4
from pydantic import ValidationError
from app.telemetry.configuration import MethodInput, validate_method, generate, host_os
from app.telemetry.rules import EventInput
from scripts.export_api_inventory import inventory


class ManagedTelemetryTests(unittest.TestCase):
    def source(self, os="Linux"):
        return S(connection_config={"opscontrol": {"os_type": os}})

    def method(self, type, configuration, enabled=True):
        return S(
            id=uuid4(),
            **MethodInput(
                name="source",
                method_type=type,
                configuration=configuration,
                enabled=enabled,
            ).model_dump()
        )

    def test_same_type_methods_have_independent_receiver_identities(self):
        a = self.method("FILE_LOG", {"paths": ["/var/log/a.log"]})
        b = self.method("FILE_LOG", {"paths": ["/var/log/b.log"]})
        config = yaml.safe_load(
            generate(
                S(configuration={}),
                self.source(),
                [a, b],
                "https://ingest.example.test",
            )
        )
        self.assertEqual(len(config["receivers"]), 2)
        self.assertEqual(len(config["service"]["pipelines"]["logs"]["receivers"]), 2)

    def test_only_explicit_signals_enabled_and_disabled_methods_excluded(self):
        selected = self.method("OTLP_RECEIVER", {"signals": ["Traces"]})
        disabled = self.method("FILE_LOG", {"paths": ["/var/log/a.log"]}, False)
        config = yaml.safe_load(
            generate(
                S(configuration={}),
                self.source(),
                [selected, disabled],
                "https://ingest.example.test",
            )
        )
        self.assertEqual(set(config["service"]["pipelines"]), {"traces"})
        self.assertEqual(len(config["receivers"]), 1)

    def test_binding_paths_and_os_fail_closed(self):
        invalid = [
            self.method("FILE_LOG", {"paths": ["../private"]}),
            self.method("FILE_LOG", {"source": "WINDOWS_EVENT"}),
            self.method("OTLP_RECEIVER", {"signals": ["Logs"], "bind": "0.0.0.0"}),
        ]
        for method in invalid:
            with self.subTest(type=method.method_type), self.assertRaises(ValueError):
                validate_method(method, "Linux")
        with self.assertRaises(ValueError):
            validate_method(self.method("FILE_LOG", {"paths": ["/var/log/a"]}), "Other")

    def test_no_raw_credentials_or_invalid_signal_fields(self):
        for c in (
            {"signals": ["Logs"], "password": "raw"},
            {"signals": []},
            {"signals": ["Fake"]},
        ):
            with self.assertRaises(ValidationError):
                MethodInput(name="x", method_type="OTLP_RECEIVER", configuration=c)

    def test_invalid_duplicate_listeners_and_exporter_origins(self):
        methods = [
            self.method("OTLP_RECEIVER", {"signals": ["Logs"]}),
            self.method("OTLP_RECEIVER", {"signals": ["Metrics"]}),
        ]
        with self.assertRaises(ValueError):
            generate(
                S(configuration={}),
                self.source(),
                methods,
                "https://ingest.example.test",
            )
        with self.assertRaises(ValueError):
            generate(
                S(configuration={}),
                self.source(),
                methods[:1],
                "http://ingest.example.test",
            )

    def test_itsm_routes_removed_alert_routes_present(self):
        paths = {r["path"] for r in inventory()}
        self.assertFalse(any("/operations/incidents" in path for path in paths))
        self.assertIn("/api/v1/operations/alerts", paths)

    def test_percentage_rule_requires_valid_minimum_duration_count(self):
        values = {
            "organization_id": uuid4(),
            "metric_definition_id": uuid4(),
            "name": "cpu",
            "threshold_percentage": 80,
        }
        rule = EventInput(**values)
        self.assertEqual(rule.time_window_minutes, 5)
        for patch in (
            {"minimum_event_count": 1},
            {"threshold_percentage": 101},
            {"unit": "seconds"},
        ):
            with self.assertRaises(ValidationError):
                EventInput(**{**values, **patch})


class AgentPermissionTests(unittest.TestCase):
    def agent(self, home):
        import importlib.util
        from pathlib import Path

        path = Path(__file__).resolve().parents[2] / "agent" / "opscontrol_agent.py"
        spec = importlib.util.spec_from_file_location("tested_opscontrol_agent", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        agent = module.Agent.__new__(module.Agent)
        agent.home = home
        return agent

    def test_actual_file_access_missing_source_and_private_state(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            state = root / "state"
            state.mkdir()
            agent = self.agent(state)
            method = lambda path: {
                "method_snapshot": [
                    {
                        "enabled": True,
                        "method_type": "FILE_LOG",
                        "configuration": {"source": "FILE", "paths": [str(path)]},
                    }
                ]
            }
            with self.assertRaisesRegex(RuntimeError, "LOG_PATH_NOT_FOUND"):
                agent.preflight(method(root / "missing.log"))
            private = state / "identity.json"
            private.write_text("private-fixture-placeholder")
            with self.assertRaisesRegex(RuntimeError, "AGENT_PRIVATE_PATH_DENIED"):
                agent.preflight(method(private))
            source = root / "app.log"
            source.write_text("controlled application log")
            agent.preflight(method(source))

    def test_management_secret_cannot_be_scrape_authentication(self):
        from app.telemetry.configuration import env_reference

        with self.assertRaises(ValueError):
            env_reference("env:OPSCONTROL_AGENT_TOKEN")


class EvaluationBoundaryTests(unittest.TestCase):
    def test_sustained_breach_requires_complete_duration_and_contiguous_evidence(self):
        from datetime import datetime, timedelta, timezone
        from app.telemetry.rules import sustained

        now = datetime.now(timezone.utc)
        current = S(observed_at=now, metric_definition_id=uuid4())
        rule = S(
            operator="GT",
            evaluation_config={
                "time_window_minutes": 5,
                "minimum_event_count": 3,
                "maximum_sample_gap_seconds": 90,
            },
        )

        def database(offsets, low_at=None):
            rows = [
                S(
                    observed_at=now - timedelta(seconds=n),
                    value_numeric=10 if n == low_at else 95,
                )
                for n in offsets
            ]
            return S(scalars=lambda query: S(all=lambda: rows))

        self.assertFalse(sustained(database([0, 60, 120]), rule, current, 80))
        self.assertFalse(sustained(database([0, 60, 300]), rule, current, 80))
        self.assertFalse(
            sustained(database([0, 60, 120, 180, 240, 300], 120), rule, current, 80)
        )
        self.assertTrue(
            sustained(database([0, 60, 120, 180, 240, 300]), rule, current, 80)
        )

    def test_dynamic_baseline_requires_history_and_combined_uses_stricter_threshold(
        self,
    ):
        from datetime import datetime, timezone
        from app.telemetry.rules import dynamic_threshold

        rule = S(
            operator="GT",
            metric_definition_id=uuid4(),
            threshold_value="80",
            evaluation_config={
                "threshold_mode": "DYNAMIC",
                "time_window_minutes": 5,
                "baseline_minutes": 60,
                "baseline_minimum_samples": 3,
                "standard_deviations": 2,
            },
        )
        current = S(observed_at=datetime.now(timezone.utc))
        db = lambda points: S(scalars=lambda query: S(all=lambda: points))
        self.assertIsNone(dynamic_threshold(db([10, 10]), rule, current))
        self.assertEqual(dynamic_threshold(db([10, 10, 10]), rule, current), 10)
        rule.evaluation_config["threshold_mode"] = "COMBINED"
        self.assertEqual(dynamic_threshold(db([10, 10, 10]), rule, current), 80)
        self.assertEqual(dynamic_threshold(db([90, 90, 90]), rule, current), 90)

    def test_unavailable_collector_validator_fails_with_actionable_safe_error(self):
        from app.telemetry.configuration import validate_binary

        with self.assertRaisesRegex(ValueError, "unavailable"):
            validate_binary("service: {}", "/nonexistent/opscontrol-validator")
