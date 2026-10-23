"""V1.5 collection compiler contracts; optional real pinned binary validation."""

import os
import unittest
from types import SimpleNamespace as S
from uuid import uuid4
import yaml
from app.telemetry.configuration import (
    METHOD_SCHEMAS,
    MethodInput,
    generate,
    validate_binary,
    validate_method,
)


class CollectionV15Tests(unittest.TestCase):
    def method(self, kind, config):
        return S(
            id=uuid4(),
            **MethodInput(
                name="source", method_type=kind, configuration=config
            ).model_dump(),
        )

    def compile(self, methods):
        return generate(
            S(configuration={}),
            S(connection_config={"opscontrol": {"os_type": "Linux"}}),
            methods,
            "https://ingest.example.test",
        )

    def test_five_schemas_and_advanced_transport(self):
        self.assertEqual(
            set(METHOD_SCHEMAS),
            {
                "HOST_METRICS",
                "SERVICES",
                "SYSLOG_RECEIVER",
                "FILE_LOG",
                "METRIC_SCRAPE",
                "OTLP_RECEIVER",
            },
        )

    def test_file_checkpoints_are_path_stable(self):
        method = self.method(
            "FILE_LOG",
            {
                "paths": ["/var/log/one.log", "/var/log/two.log"],
                "multiline_pattern": r"^\d{4}-",
            },
        )
        first = yaml.safe_load(self.compile([method]))
        method.configuration["paths"].reverse()
        second = yaml.safe_load(self.compile([method]))
        self.assertEqual(first["receivers"], second["receivers"])
        self.assertEqual(len(first["receivers"]), 2)
        for config in first["receivers"].values():
            self.assertEqual(config["storage"], "file_storage/opscontrol")
            self.assertTrue(config["include_file_path"])
            self.assertEqual(len(config["include"]), 1)
        self.assertTrue(
            first["extensions"]["file_storage/opscontrol"]["create_directory"]
        )

    def test_scrape_timeout_filter_labels_and_verified_tls(self):
        method = self.method(
            "METRIC_SCRAPE",
            {
                "targets": ["metrics.example.test:443"],
                "tls": True,
                "credential_ref": "env:SCRAPE_TOKEN",
                "metric_include": ["app_.*"],
                "metric_exclude": ["app_private"],
                "labels": {"environment": "QA"},
            },
        )
        scrape = next(
            iter(yaml.safe_load(self.compile([method]))["receivers"].values())
        )["config"]["scrape_configs"][0]
        self.assertFalse(scrape["tls_config"]["insecure_skip_verify"])
        self.assertEqual(scrape["scrape_timeout"], "10s")
        self.assertEqual(
            [r["action"] for r in scrape["metric_relabel_configs"]], ["keep", "drop"]
        )
        self.assertEqual(scrape["static_configs"][0]["labels"]["environment"], "QA")
        self.assertEqual(
            scrape["static_configs"][0]["labels"]["opscontrol_method_id"],
            str(method.id),
        )

    def test_concurrent_five_methods_reference_unique_receivers(self):
        methods = [
            self.method("HOST_METRICS", {}),
            self.method("SERVICES", {"services": ["application.service"]}),
            self.method("SYSLOG_RECEIVER", {}),
            self.method("FILE_LOG", {"paths": ["/var/log/app.log"]}),
            self.method("METRIC_SCRAPE", {"targets": ["localhost:9100"]}),
        ]
        config = yaml.safe_load(self.compile(methods))
        self.assertEqual(len(config["receivers"]), 5)
        self.assertEqual(
            {key.split("/")[0] for key in config["service"]["pipelines"]},
            {"logs", "metrics"},
        )
        host_pipeline = config["service"]["pipelines"][
            "metrics/" + str(methods[0].id).replace("-", "")
        ]
        self.assertEqual(len(host_pipeline["receivers"]), 1)
        self.assertTrue(host_pipeline["receivers"][0].startswith("hostmetrics/"))
        processor = next(
            p for p in host_pipeline["processors"] if p.startswith("resource/method_")
        )
        self.assertEqual(
            config["processors"][processor]["attributes"][0]["value"],
            str(methods[0].id),
        )
        for pipeline in config["service"]["pipelines"].values():
            self.assertTrue(set(pipeline["receivers"]) <= set(config["receivers"]))
        self.assertIn(
            "network",
            next(
                c
                for n, c in config["receivers"].items()
                if n.startswith("hostmetrics/")
            )["scrapers"],
        )

    def test_legacy_short_interval_gets_compatible_timeout(self):
        method = self.method(
            "METRIC_SCRAPE", {"targets": ["localhost:9100"], "interval_seconds": 5}
        )
        self.assertEqual(method.configuration["timeout_seconds"], 5)
        validate_method(method, "Linux")

    def test_invalid_source_configurations_fail_closed(self):
        cases = [
            ("HOST_METRICS", {"scrapers": ["cpu", "cpu"]}),
            ("SERVICES", {"services": ["service; rm -rf /"]}),
            ("SERVICES", {}),
            ("METRIC_SCRAPE", {"targets": ["localhost:80"], "timeout_seconds": 40}),
            (
                "METRIC_SCRAPE",
                {"targets": ["localhost:80"], "labels": {"__unsafe": "value"}},
            ),
        ]
        for kind, config in cases:
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                validate_method(self.method(kind, config), "Linux")

    @unittest.skipUnless(
        os.getenv("OPSCONTROL_OTEL_BINARY"), "Pinned Contrib binary not configured"
    )
    def test_actual_contrib_accepts_five_methods(self):
        methods = [
            self.method("HOST_METRICS", {}),
            self.method("SERVICES", {"processes": ["python"]}),
            self.method("SYSLOG_RECEIVER", {}),
            self.method("FILE_LOG", {"paths": ["/var/log/app.log"]}),
            self.method(
                "METRIC_SCRAPE",
                {"targets": ["localhost:9100"], "metric_include": ["app_.*"]},
            ),
        ]
        self.assertTrue(validate_binary(self.compile(methods)))


@unittest.skipUnless(
    os.getenv("OPSCONTROL_OTEL_BINARY"), "Pinned Contrib binary not configured"
)
class RealCollectionRuntimeTests(unittest.TestCase):
    """Real Contrib process and local HTTP targets; no production telemetry fixture."""

    def test_actual_scrape_and_log_rotation_truncation_restart(self):
        import gzip
        import json
        import subprocess
        import socket
        import tempfile
        import threading
        import time
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        from pathlib import Path

        received = []
        lock = threading.Lock()

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_GET(self):
                payload = b'# TYPE app_requests_total counter\napp_requests_total{route="health"} 7\n# TYPE private_requests gauge\nprivate_requests 9\n'
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; version=0.0.4")
                self.end_headers()
                self.wfile.write(payload)

            def do_POST(self):
                payload = self.rfile.read(int(self.headers["Content-Length"]))
                if self.headers.get("Content-Encoding") == "gzip":
                    payload = gzip.decompress(payload)
                with lock:
                    received.append((self.path, json.loads(payload)))
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b"{}")

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        port = server.server_address[1]
        process = None
        try:
            with tempfile.TemporaryDirectory(
                prefix="opscontrol-real-collection-"
            ) as directory:
                root = Path(directory)
                log = root / "application.log"
                log.write_text("first-record " + "a" * 1100 + "\n  multiline-detail\n")
                with socket.socket() as reservation:
                    reservation.bind(("127.0.0.1", 0))
                    syslog_port = reservation.getsockname()[1]
                helper = CollectionV15Tests()
                methods = [
                    helper.method("HOST_METRICS", {"interval_seconds": 5}),
                    helper.method("SYSLOG_RECEIVER", {"port": syslog_port}),
                    helper.method(
                        "FILE_LOG",
                        {
                            "paths": [str(log)],
                            "start_at": "beginning",
                            "multiline_pattern": "^(first|rotated|truncated|after)-",
                        },
                    ),
                    helper.method(
                        "METRIC_SCRAPE",
                        {
                            "targets": [f"127.0.0.1:{port}"],
                            "interval_seconds": 5,
                            "timeout_seconds": 2,
                            "metric_include": ["app_.*"],
                            "labels": {"scope": "controlled-test"},
                        },
                    ),
                ]
                config = yaml.safe_load(helper.compile(methods))
                config["extensions"]["health_check"]["endpoint"] = "127.0.0.1:0"
                # Isolate internal diagnostics: other owned labs may run Contrib
                # simultaneously. This does not disable collected host/scrape metrics.
                config["service"]["telemetry"] = {"metrics": {"level": "none"}}
                config["exporters"]["otlphttp/opscontrol"] = {
                    "endpoint": f"http://127.0.0.1:{port}",
                    "encoding": "json",
                    "compression": "none",
                }
                config["processors"]["batch"]["timeout"] = "200ms"
                configfile = root / "config.yaml"
                configfile.write_text(yaml.safe_dump(config))
                env = {
                    **os.environ,
                    "OPSCONTROL_AGENT_STATE_DIR": str(root / "private"),
                }
                (root / "private").mkdir(mode=0o700)
                diagnostic = root / "runtime.log"

                def start():
                    with diagnostic.open("ab") as output:
                        return subprocess.Popen(
                            [
                                os.environ["OPSCONTROL_OTEL_BINARY"],
                                "--config",
                                str(configfile),
                            ],
                            env=env,
                            stdout=output,
                            stderr=subprocess.STDOUT,
                        )

                def records():
                    with lock:
                        return [
                            record
                            for path, data in received
                            if path.endswith("logs")
                            for resource in data.get("resourceLogs", [])
                            for scope in resource.get("scopeLogs", [])
                            for record in scope.get("logRecords", [])
                        ]

                def contains(marker):
                    return any(
                        marker in r.get("body", {}).get("stringValue", "")
                        for r in records()
                    )

                def await_condition(predicate, description, seconds=20):
                    deadline = time.monotonic() + seconds
                    while time.monotonic() < deadline:
                        if predicate():
                            return
                        if process.poll() is not None:
                            self.fail("Contrib exited during " + description)
                        time.sleep(0.1)
                    self.fail("Timed out waiting for " + description)

                process = start()

                def send_syslog():
                    try:
                        with socket.create_connection(
                            ("127.0.0.1", syslog_port), timeout=1
                        ) as stream:
                            stream.sendall(
                                b"<34>1 2026-10-13T12:00:00Z test-host test-app 123 MSG47 - controlled-syslog-evidence\n"
                            )
                        return True
                    except OSError:
                        return False

                await_condition(send_syslog, "actual TCP syslog listener")
                await_condition(
                    lambda: contains("controlled-syslog-evidence"),
                    "actual syslog receipt",
                )
                await_condition(
                    lambda: contains("first-record"), "initial actual file receipt"
                )
                log.rename(root / "application.log.1")
                log.write_text("rotated-record " + "b" * 1100 + "\n")
                await_condition(
                    lambda: contains("rotated-record"), "rotated file receipt"
                )
                log.write_text("truncated-record " + "c" * 1100 + "\n")
                await_condition(
                    lambda: contains("truncated-record"), "truncated file receipt"
                )
                process.terminate()
                process.wait(timeout=15)
                process = start()
                with log.open("a") as f:
                    f.write("after-restart-record " + "d" * 1100 + "\n")
                await_condition(
                    lambda: contains("after-restart-record"),
                    "persistent checkpoint restart receipt",
                )
                await_condition(
                    lambda: any(
                        path.endswith("metrics")
                        and "app_requests_total" in json.dumps(data)
                        for path, data in received
                    ),
                    "actual HTTP scrape metric receipt",
                )
                # A quiet readable source with a running runtime is idle, not failed.
                self.assertIsNone(process.poll())
                self.assertTrue(os.access(log, os.R_OK))
                bodies = [r["body"]["stringValue"] for r in records()]
                for marker in [
                    "first-record",
                    "rotated-record",
                    "truncated-record",
                    "after-restart-record",
                ]:
                    self.assertEqual(
                        sum(marker in body for body in bodies),
                        1,
                        marker + " duplicated across restart",
                    )
                with lock:
                    metrics = [
                        m
                        for path, data in received
                        if path.endswith("metrics")
                        for resource in data.get("resourceMetrics", [])
                        for scope in resource.get("scopeMetrics", [])
                        for m in scope.get("metrics", [])
                    ]
                self.assertTrue(any(m["name"] == "app_requests_total" for m in metrics))
                self.assertTrue(
                    any(m["name"].startswith("system.cpu.") for m in metrics)
                )
                self.assertTrue(any(m["name"] == "up" for m in metrics))
                self.assertTrue(
                    any(
                        "first-record" in body and "multiline-detail" in body
                        for body in bodies
                    )
                )
                for record in records():
                    if "controlled-syslog-evidence" in record["body"].get(
                        "stringValue", ""
                    ):
                        self.assertTrue(
                            any(
                                attr["key"] == "opscontrol.method.id"
                                for attr in record["attributes"]
                            )
                        )
                        continue
                    self.assertTrue(
                        any(
                            attr["key"] == "opscontrol.log.source.id"
                            for attr in record["attributes"]
                        )
                    )
                self.assertFalse(any(m["name"] == "private_requests" for m in metrics))
                counter = next(m for m in metrics if m["name"] == "app_requests_total")
                attrs = counter["sum"]["dataPoints"][0]["attributes"]
                self.assertIn(
                    {"key": "scope", "value": {"stringValue": "controlled-test"}}, attrs
                )
        finally:
            if process is not None and process.poll() is None:
                process.terminate()
                process.wait(timeout=15)
            server.shutdown()
            server.server_close()


class MethodHealthTests(unittest.TestCase):
    def test_actual_quiet_file_is_idle_and_missing_file_is_error(self):
        import importlib.util
        import tempfile
        from pathlib import Path

        module_path = (
            Path(__file__).resolve().parents[2] / "agent" / "service_health.py"
        )
        spec = importlib.util.spec_from_file_location("collection_health", module_path)
        health = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(health)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            private = root / "private"
            private.mkdir()
            log = root / "quiet.log"
            log.write_text("")
            methods = [
                {
                    "id": str(uuid4()),
                    "enabled": True,
                    "method_type": "FILE_LOG",
                    "configuration": {"source": "FILE", "paths": [str(log)]},
                }
            ]
            idle = health.method_observations(methods, True, private)[0]
            self.assertEqual(idle["state"], "IDLE")
            self.assertEqual(idle["sources_readable"], 1)
            stopped = health.method_observations(methods, False, private)[0]
            self.assertEqual(stopped["state"], "STOPPED")
            log.unlink()
            error = health.method_observations(methods, True, private)[0]
            self.assertEqual(error["state"], "ERROR")
            self.assertEqual(error["error_code"], "LOG_PATH_NOT_FOUND")

    def test_idle_observation_is_distinct_from_real_reception(self):
        from datetime import datetime, timedelta, timezone
        from app.telemetry.api import method_collection_state, signal_delivery_state

        now = datetime.now(timezone.utc)
        method = S(id=uuid4(), enabled=True, method_type="FILE_LOG")
        agent = S(
            enabled=True,
            health="RUNNING",
            last_seen_at=now,
            method_health={
                str(method.id): {
                    "applied_revision": 3,
                    "state": "IDLE",
                    "sources_readable": 1,
                    "observed_at": now.isoformat(),
                }
            },
        )
        applied = S(revision=3)
        self.assertEqual(
            method_collection_state(method, agent, applied, True, {}), "IDLE"
        )
        self.assertEqual(
            method_collection_state(
                method, agent, applied, True, {"last_received_at": now}
            ),
            "RECEIVING",
        )
        agent.health = "STOPPED"
        self.assertEqual(
            method_collection_state(
                method, agent, applied, True, {"last_received_at": now}
            ),
            "STOPPED",
        )
        self.assertEqual(signal_delivery_state(agent, now), "STOPPED")
        self.assertEqual(signal_delivery_state(agent, None), "NO_DATA")
        agent.health = "ERROR"
        self.assertEqual(signal_delivery_state(agent, now), "ERROR")
        self.assertEqual(
            method_collection_state(
                method, agent, applied, True, {"last_received_at": now}
            ),
            "ERROR",
        )
        agent.health = "RUNNING"
        self.assertEqual(signal_delivery_state(agent, now), "RECEIVING")
        self.assertEqual(signal_delivery_state(agent, now, False), "DISABLED")
        self.assertEqual(
            method_collection_state(method, agent, applied, True, {}, False),
            "DISABLED",
        )
        agent.last_seen_at = now - timedelta(minutes=2)
        self.assertEqual(signal_delivery_state(agent, now), "DISCONNECTED")
        agent.last_seen_at = now
        agent.method_health[str(method.id)]["state"] = "ERROR"
        self.assertEqual(
            method_collection_state(
                method, agent, applied, True, {"last_received_at": now}
            ),
            "ERROR",
        )
        self.assertEqual(
            method_collection_state(method, agent, applied, False, {}), "NOT_APPLIED"
        )

    def test_observations_are_closed_and_bounded(self):
        from app.telemetry.api import Heartbeat
        from pydantic import ValidationError

        base = {"version": "test", "runtime_version": "0.123.0", "health": "RUNNING"}
        for invalid in [
            {"method_id": str(uuid4()), "state": "RECEIVING"},
            {"method_id": str(uuid4()), "state": "IDLE", "password": "forbidden"},
        ]:
            with self.assertRaises(ValidationError):
                Heartbeat(**base, method_observations=[invalid])


class MethodAttributionTests(unittest.TestCase):
    def test_selected_signals_are_enforced_for_attributed_telemetry(self):
        from app.telemetry.ingestion import (
            approved_method_signals,
            attributes,
            validate_method_attribution,
            validate_method_identity,
        )
        from fastapi import HTTPException
        from opentelemetry.proto.common.v1.common_pb2 import AnyValue, KeyValue

        key = str(uuid4())
        allowed = approved_method_signals(
            [
                S(
                    method_snapshot=[
                        {
                            "id": key,
                            "enabled": True,
                            "method_type": "OTLP_RECEIVER",
                            "configuration": {"signals": ["Logs", "Metrics"]},
                        }
                    ]
                )
            ]
        )
        self.assertEqual(
            validate_method_identity({"opscontrol.method.id": key}, allowed, "logs"),
            key,
        )
        for attrs, signal in [
            ({"opscontrol.method.id": key}, "traces"),
            ({"opscontrol.method.id": str(uuid4())}, "logs"),
            (
                {"opscontrol.method.id": key, "opscontrol_method_id": str(uuid4())},
                "metrics",
            ),
        ]:
            with self.assertRaises(HTTPException) as failure:
                validate_method_identity(attrs, allowed, signal)
            self.assertEqual(failure.exception.status_code, 422)
        self.assertIsNone(validate_method_identity({}, allowed, "metrics"))
        other = str(uuid4())
        allowed[other] = {"logs", "metrics"}
        self.assertEqual(
            validate_method_attribution(
                {"opscontrol.method.id": key}, {}, allowed, "metrics"
            ),
            key,
        )
        self.assertEqual(
            validate_method_attribution(
                {}, {"opscontrol_method_id": other}, allowed, "logs"
            ),
            other,
        )
        for resource_attrs, record_attrs in [
            ({"opscontrol.method.id": key}, {"opscontrol.method.id": other}),
            ({"opscontrol_method_id": key}, {"opscontrol.method.id": other}),
            ({"opscontrol.method.id": other}, {"opscontrol.method.id": key}),
        ]:
            with self.assertRaises(HTTPException) as failure:
                validate_method_attribution(
                    resource_attrs, record_attrs, allowed, "metrics"
                )
            self.assertEqual(failure.exception.status_code, 422)
        with self.assertRaises(HTTPException) as failure:
            validate_method_attribution(
                {"opscontrol.method.id": key},
                {"opscontrol.method.id": other},
                {key: {"traces"}, other: {"traces"}},
                "traces",
            )
        self.assertEqual(failure.exception.status_code, 422)
        with self.assertRaises(HTTPException) as failure:
            attributes(
                [
                    KeyValue(
                        key="opscontrol.method.id",
                        value=AnyValue(string_value=key),
                    ),
                    KeyValue(
                        key="opscontrol.method.id",
                        value=AnyValue(string_value=other),
                    ),
                ]
            )
        self.assertEqual(failure.exception.status_code, 422)
