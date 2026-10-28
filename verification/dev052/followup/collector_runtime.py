"""Evaluate all five generated methods with a real candidate; do not lift guard."""

import hashlib, json, os, re, socket, subprocess, sys, tempfile, threading, time, urllib.request
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
import yaml
from tests.test_collection_v15 import CollectionV15Tests

BINARY = Path("/tmp/dev052a1-runtime/otelcol-contrib")
assert (
    hashlib.sha256(BINARY.read_bytes()).hexdigest()
    == "dbd12d55073b70add777895457040f8ede59fc1ee7198d6ae179a37087eea8bb"
)
OUT = ROOT / "docs/verification/dev052/security/2026-10-25-followup"
sys.path.insert(0, str(ROOT / "agent"))
from service_health import envelope

received = []
lock = threading.Lock()
process = None


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"# TYPE followup_requests counter\nfollowup_requests 9\n"
        self.send_response(200)
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        with lock:
            received.append(json.loads(body))
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"{}")

    def log_message(self, *args):
        pass


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
result = {
    "candidate": "0.163.2",
    "methods": [
        "HOST_METRICS",
        "SERVICES",
        "SYSLOG_RECEIVER",
        "FILE_LOG",
        "METRIC_SCRAPE",
    ],
    "status": "FAIL",
    "guard_changed": False,
}
try:
    with tempfile.TemporaryDirectory(prefix="dev052a2-five-method-") as directory:
        root = Path(directory)
        log = root / "application.log"
        log.write_text("five-method-record " + "a" * 1100 + "\n")
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            syslog_port = s.getsockname()[1]
        h = CollectionV15Tests()
        cfg = yaml.safe_load(
            h.compile(
                [
                    h.method("HOST_METRICS", {"interval_seconds": 5}),
                    h.method(
                        "SERVICES", {"processes": ["python"], "interval_seconds": 5}
                    ),
                    h.method("SYSLOG_RECEIVER", {"port": syslog_port}),
                    h.method(
                        "FILE_LOG", {"paths": [str(log)], "start_at": "beginning"}
                    ),
                    h.method(
                        "METRIC_SCRAPE",
                        {
                            "targets": [f"127.0.0.1:{server.server_port}"],
                            "interval_seconds": 5,
                            "timeout_seconds": 2,
                            "metric_include": ["followup_.*"],
                        },
                    ),
                ]
            )
        )
        cfg["extensions"]["health_check"]["endpoint"] = "127.0.0.1:0"
        cfg["service"]["telemetry"] = {"metrics": {"level": "none"}}
        cfg["exporters"]["otlphttp/opscontrol"] = {
            "endpoint": f"http://127.0.0.1:{server.server_port}",
            "encoding": "json",
            "compression": "none",
        }
        cfg["processors"]["batch"]["timeout"] = "200ms"
        config = root / "config.yaml"
        config.write_text(yaml.safe_dump(cfg))
        (OUT / "collector-evaluation-config.yaml").write_text(yaml.safe_dump(cfg))
        (root / "private").mkdir()
        env = os.environ.copy()
        env["OPSCONTROL_AGENT_STATE_DIR"] = str(root / "private")
        invalid = root / "invalid.yaml"
        invalid.write_text("receivers:\n  nonexistent_receiver: {}\nservice: {}\n")
        negative = subprocess.run(
            [str(BINARY), "validate", "--config", str(invalid)],
            env=env,
            capture_output=True,
            text=True,
        )
        assert negative.returncode != 0
        result["invalid_config_rejected"] = True
        with (OUT / "collector-five-method-process.log").open("w") as out:
            process = subprocess.Popen(
                [str(BINARY), "--config", str(config)],
                env=env,
                stdout=out,
                stderr=subprocess.STDOUT,
            )
            # SERVICES is emitted by the supervisor, not the collector hostmetrics scraper.
            process_name = Path("/proc/self/comm").read_text().strip()
            telemetry, failures = envelope(
                [], "Linux", "dev052a2-lab", [process_name], True
            )
            assert not failures, failures
            process_metric = next(
                m
                for m in telemetry["resourceMetrics"][0]["scopeMetrics"][0]["metrics"]
                if m["name"] == "opscontrol.process.count"
            )
            assert int(process_metric["gauge"]["dataPoints"][0]["asInt"]) > 0
            # Direct local sink tests serialization only; authenticated supervisor dispatch
            # remains covered by existing agent tests, not inferred from this sink.
            with urllib.request.urlopen(
                urllib.request.Request(
                    f"http://127.0.0.1:{server.server_port}/otlp/v1/metrics",
                    data=json.dumps(telemetry).encode(),
                    headers={"Content-Type": "application/json"},
                )
            ) as response:
                assert response.status == 200
            result["services_scope"] = (
                "real Linux process/uptime observation + local OTLP serialization; not genuine systemd/Windows certification"
            )
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                assert (
                    process.poll() is None
                ), "candidate exited during five-method startup"
                try:
                    with socket.create_connection(
                        ("127.0.0.1", syslog_port), timeout=0.5
                    ) as s:
                        s.sendall(
                            b"<34>1 2026-10-25T09:00:00Z lab app 1 TEST - five-method-syslog\n"
                        )
                except OSError:
                    pass
                with lock:
                    doc = json.dumps(received)
                if all(
                    x in doc
                    for x in [
                        "opscontrol.process.count",
                        "system.cpu.",
                        "followup_requests",
                        "five-method-record",
                        "five-method-syslog",
                    ]
                ):
                    result["functional_evidence"] = [
                        "opscontrol.process.count",
                        "system.cpu",
                        "HTTP scrape",
                        "file log",
                        "TCP syslog",
                    ]
                    result["status"] = "PASS"
                    break
                time.sleep(0.2)
            assert (
                result["status"] == "PASS"
            ), "all five functional signals were not observed"
except Exception as error:
    result["error"] = str(error)
finally:
    if process and process.poll() is None:
        process.terminate()
        process.wait(timeout=15)
    server.shutdown()
    server.server_close()
    (OUT / "collector-five-method-runtime.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(json.dumps(result))
    sys.exit(0 if result["status"] == "PASS" else 1)
