"""Five methods through actual supervisor -> TLS API -> disposable PostgreSQL.

Only for run_lab.py's owned fixture. Never claims genuine systemd/Windows health.
"""

import json
import os
from pathlib import Path
import socket
import ssl
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError

sys.path.insert(0, "/work/agent")
from opscontrol_agent import Agent
from service_health import envelope

sys.path.insert(0, "/work/backend/scripts")
from acceptance_scope import probe_headers
from urllib.request import Request, urlopen


def call(path, method="GET", body=None, token=None, expected=200):
    req = Request(
        os.environ["ARCH001_API_URL"] + path,
        method=method,
        headers={
            "Content-Type": "application/json",
            **({"Authorization": "Bearer " + token} if token else {}),
            **probe_headers(os.environ["ARCH001_API_URL"], token, path),
        },
        data=json.dumps(body).encode() if body is not None else None,
    )
    try:
        with urlopen(req, timeout=15) as response:
            status, raw = response.status, response.read()
    except HTTPError as error:
        status, raw = error.code, error.read()
    assert status == expected, (method, path, status, expected)
    return json.loads(raw) if raw else None


assert os.environ["ENVIRONMENT"] == "test"
assert os.environ["DEV052A3_LAB"] == "1"
PRIVATE = Path("/fixture")
f = json.loads((PRIVATE / "fixture.json").read_text())
report = {"status": "FAIL", "scope": "synthetic isolated Linux fixture", "checks": []}
process = None


def passed(name):
    report["checks"].append(name)
    print(name + ": PASS", flush=True)


def wait(predicate, label, seconds=90):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        try:
            if predicate():
                passed(label)
                return
        except (URLError, ConnectionError):
            pass
        if process is not None:
            assert process.poll() is None, "Supervisor exited: " + label
        time.sleep(0.5)
    raise AssertionError("Timed out: " + label)


class Scrape(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"# TYPE dev052a3_requests counter\ndev052a3_requests 17\n")

    def log_message(self, *args):
        pass


server = ThreadingHTTPServer(("127.0.0.1", 0), Scrape)
threading.Thread(target=server.serve_forever, daemon=True).start()
try:
    assert os.getuid() != 0
    status = Path("/proc/self/status").read_text()
    assert "NoNewPrivs:\t1" in status and "CapEff:\t0000000000000000" in status
    report["uid"] = os.getuid()
    passed("non-root, no capabilities, no-new-privileges")
    token = call(
        "/api/v1/auth/login",
        "POST",
        {"username": "arch001-admin", "password": f["password"]},
    )["access_token"]
    f["token"] = token
    vm = call(
        "/api/v1/unified/resources/vm",
        "POST",
        {
            "name": "DEV052A3 isolated agent",
            "hostname": socket.gethostname(),
            "address": socket.gethostname(),
            "environment": "SANDBOX",
            "os_type": "Linux",
            "organization_id": f["org"],
            "native_os_metrics": False,
        },
        token,
        201,
    )
    f["vm_resource"] = vm
    (PRIVATE / "fixture.json").write_text(json.dumps(f))
    prefix = "/api/v1/agent-control/collectors/" + vm["primary_collector_id"]
    for method in call(prefix, token=token)["methods"]:
        call(prefix + "/methods/" + method["id"], "DELETE", token=token, expected=204)
    log = PRIVATE / "events.log"
    log.write_text("a3-initial " + "a" * 1200 + "\n")
    configurations = [
        ("HOST_METRICS", {"interval_seconds": 5, "scrapers": ["cpu", "memory"]}),
        ("SERVICES", {"interval_seconds": 5, "processes": ["python"]}),
        ("SYSLOG_RECEIVER", {"port": 15200}),
        ("FILE_LOG", {"paths": [str(log)], "start_at": "beginning"}),
        (
            "METRIC_SCRAPE",
            {
                "targets": [f"127.0.0.1:{server.server_port}"],
                "interval_seconds": 5,
                "timeout_seconds": 2,
                "metric_include": ["dev052a3_.*"],
            },
        ),
    ]
    methods = [
        call(
            prefix + "/methods",
            "POST",
            {"name": kind, "method_type": kind, "configuration": cfg},
            token,
            201,
        )
        for kind, cfg in configurations
    ]
    version = call(prefix + "/versions", "POST", token=token, expected=201)
    assert version["validation_status"] == "VALIDATED"
    assert version["runtime_version"] == "0.163.2"
    (PRIVATE / "generated.yaml").write_text(version["yaml_text"])
    report.update(
        collector_id=vm["primary_collector_id"],
        methods={m["method_type"]: m["id"] for m in methods},
        config_sha256=version["sha256"],
    )
    passed("five-method configuration validated by exact candidate")
    home = PRIVATE / "agent-home"
    home.mkdir(mode=0o700)
    enrollment = home / "enrollment"
    enrollment.write_text(
        call(prefix + "/registration", "POST", token=token, expected=201)[
            "enrollment_token"
        ]
    )
    enrollment.chmod(0o600)
    args = [
        sys.executable,
        "/work/agent/opscontrol_agent.py",
        "--home",
        str(home),
        "--backend",
        os.environ["ARCH001_API_URL"],
        "--runtime",
        "/runtime/otelcol-contrib",
        "--enrollment-file",
        str(enrollment),
        "--poll-seconds",
        "5",
    ]
    output = (PRIVATE / "supervisor.log").open("w")
    process = subprocess.Popen(args, stdout=output, stderr=subprocess.STDOUT)
    wait(lambda: (home / "identity.json").exists(), "authenticated enrollment")
    call(
        prefix + "/apply",
        "POST",
        {"revision": version["revision"], "approve": True},
        token,
    )
    wait(
        lambda: call(prefix, token=token)["agent"]["applied_revision"]
        == version["revision"],
        "supervisor applies approved checksum",
    )
    for _ in range(3):
        with socket.create_connection(("127.0.0.1", 15200), timeout=3) as stream:
            timestamp = datetime.now(timezone.utc).isoformat()
            stream.sendall(f"<34>1 {timestamp} lab app 1 CHECK - a3-syslog\n".encode())
    wait(
        lambda: all(
            m["record_count"] > 0 for m in call(prefix, token=token)["methods"]
        ),
        "all five methods have persisted, attributed API evidence",
    )
    wait(
        lambda: call(prefix, token=token)["agent"]["verified_revision"]
        == version["revision"],
        "server verifies runtime revision and authenticated receipts",
    )
    before = {
        m["method_type"]: m["record_count"]
        for m in call(prefix, token=token)["methods"]
    }
    file_id = report["methods"]["FILE_LOG"]

    def file_count():
        return next(
            m["record_count"]
            for m in call(prefix, token=token)["methods"]
            if m["id"] == file_id
        )

    log.rename(PRIVATE / "events.old")
    log.write_text("a3-rotated " + "b" * 1600 + "\n")
    wait(lambda: file_count() > before["FILE_LOG"], "file rotation delivered")
    count = file_count()
    log.write_text("a3-truncated " + "c" * 1100 + "\n")
    wait(lambda: file_count() > count, "file truncation delivered")
    process.terminate()
    process.wait(timeout=20)
    process = None
    checkpoint = home / "otel-checkpoints"
    assert any(checkpoint.iterdir())
    identity = json.loads((home / "identity.json").read_text())
    count = file_count()
    with log.open("a") as stream:
        stream.write("a3-after-restart " + "d" * 1200 + "\n")
    process = subprocess.Popen(args, stdout=output, stderr=subprocess.STDOUT)
    wait(lambda: file_count() > count, "checkpoint restart delivered appended record")
    restarted_identity = json.loads((home / "identity.json").read_text())
    assert all(
        restarted_identity[k] == identity[k] for k in ["agent_id", "access_token"]
    )
    passed("same identity preserved across restart")

    agent = Agent(home, os.environ["ARCH001_API_URL"], "/runtime/otelcol-contrib")
    telemetry, failures = envelope(
        [], "Linux", "dev052a3-lab", ["python"], True, version["method_snapshot"]
    )
    assert not failures
    agent.request("/otlp/v1/metrics", telemetry)
    passed("real supervisor envelope authenticated ingestion")
    good_token = agent.token
    agent.token = "invalid-synthetic-credential"
    try:
        agent.request("/otlp/v1/metrics", telemetry)
    except HTTPError as error:
        assert error.code == 401
    else:
        raise AssertionError("Invalid supervisor credential accepted")
    agent.token = good_token
    passed("invalid supervisor credential rejected")
    for body, expected in [
        ({"resourceMetrics": "malformed"}, 400),
        ({"unknown": 1}, 400),
    ]:
        try:
            agent.request("/otlp/v1/metrics", body)
        except HTTPError as error:
            assert error.code == expected
        else:
            raise AssertionError("Invalid supervisor envelope accepted")
    forged = json.loads(json.dumps(telemetry))
    for metric in forged["resourceMetrics"][0]["scopeMetrics"][0]["metrics"]:
        for point in metric.get("gauge", {}).get("dataPoints", []):
            point["attributes"] = [
                {
                    "key": "opscontrol.method.id",
                    "value": {"stringValue": str(uuid.uuid4())},
                }
            ]
    try:
        agent.request("/otlp/v1/metrics", forged)
    except HTTPError as error:
        assert error.code == 422
    else:
        raise AssertionError("Foreign method accepted")
    passed("malformed and foreign-method envelopes rejected")
    from urllib.parse import urlsplit

    parsed = urlsplit(os.environ["ARCH001_API_URL"])
    for context, hostname in [
        (
            ssl.create_default_context(cafile="/etc/ssl/certs/ca-certificates.crt"),
            parsed.hostname,
        ),
        (ssl.create_default_context(cafile="/fixture/ca.pem"), "wrong.example.test"),
    ]:
        try:
            with socket.create_connection(
                (parsed.hostname, parsed.port), timeout=3
            ) as sock:
                context.wrap_socket(sock, server_hostname=hostname)
        except ssl.SSLCertVerificationError:
            pass
        else:
            raise AssertionError("Untrusted CA or wrong TLS hostname accepted")
    passed("untrusted CA and TLS hostname mismatch rejected")
    try:
        Agent(PRIVATE / "http-denied", "http://localhost", "/runtime/otelcol-contrib")
    except ValueError:
        pass
    else:
        raise AssertionError("Plain HTTP management accepted")
    passed("HTTPS-only management enforced")
    target_hits = []

    class Redirect(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/target":
                target_hits.append(True)
                self.send_response(200)
            else:
                self.send_response(302)
                self.send_header(
                    "Location", f"https://127.0.0.1:{redirect.server_port}/target"
                )
            self.end_headers()

        def log_message(self, *args):
            pass

    redirect = ThreadingHTTPServer(("127.0.0.1", 0), Redirect)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain("/fixture/ca.pem", "/fixture/key.pem")
    redirect.socket = context.wrap_socket(redirect.socket, server_side=True)
    threading.Thread(target=redirect.serve_forever, daemon=True).start()
    try:
        redirected = Agent(
            PRIVATE / "redirect-test",
            f"https://127.0.0.1:{redirect.server_port}",
            "/runtime/otelcol-contrib",
        )
        try:
            redirected.request("/test")
        except RuntimeError as error:
            assert "redirects forbidden" in str(error)
        else:
            raise AssertionError("Management redirect followed")
        assert not target_hits
        passed("management redirects rejected before target contact")
    finally:
        redirect.shutdown()
        redirect.server_close()
    try:
        socket.create_connection((os.environ["DENIED_FIXTURE_IP"], 8080), timeout=2)
    except OSError:
        pass
    else:
        raise AssertionError("Disjoint isolated-network egress succeeded")
    passed("egress to owned disjoint fixture blocked")
    # Request an actual API outage from the host owner, not a manufactured HTTP response.
    outage_before = file_count()
    (PRIVATE / "request-api-outage").touch()
    wait(lambda: (PRIVATE / "api-down").exists(), "API outage acknowledged")
    try:
        agent.request("/configuration")
    except (URLError, ConnectionError, TimeoutError):
        pass
    else:
        raise AssertionError("API outage did not interrupt supervisor transport")
    with log.open("a") as stream:
        stream.write("a3-after-outage " + "e" * 1200 + "\n")
    wait(lambda: (PRIVATE / "api-restored").exists(), "same API endpoint restored")
    wait(lambda: file_count() > outage_before, "queued delivery after API interruption")
    listeners = {}
    for protocol, listen_state in [
        ("tcp", "0A"),
        ("tcp6", "0A"),
        ("udp", "07"),
        ("udp6", "07"),
    ]:
        path = Path("/proc/net") / protocol
        assert path.exists(), "Listener family unavailable: " + protocol
        endpoints = []
        for line in path.read_text().splitlines()[1:]:
            fields = line.split()
            if fields[3] != listen_state:
                continue
            address = fields[1].split(":")[0]
            if protocol.endswith("6"):
                loopback = address == "00000000000000000000000001000000" or (
                    address.startswith("0000000000000000FFFF0000")
                    and address.endswith("7F")
                )
            else:
                loopback = address.endswith("7F")
            assert loopback, (protocol, fields[1])
            endpoints.append(fields[1])
        listeners[protocol] = endpoints
    report["listeners"] = listeners
    passed("no non-loopback TCP/UDP IPv4/IPv6 listeners in agent container")
    # Retain real generated configuration acceptance on the guarded binary too.
    env = {
        **os.environ,
        "OPSCONTROL_AGENT_TOKEN": good_token,
        "OPSCONTROL_AGENT_STATE_DIR": str(home),
    }
    validation = subprocess.run(
        [
            "/runtime/otelcol-contrib-0.123.0",
            "validate",
            "--config",
            str(home / "otel.yaml"),
        ],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    assert validation.returncode == 0
    passed("generated config accepted by guarded rollback binary")
    process.terminate()
    process.wait(timeout=20)
    process = None
    old = subprocess.Popen(
        ["/runtime/otelcol-contrib-0.123.0", "--config", str(home / "otel.yaml")],
        stdout=output,
        stderr=subprocess.STDOUT,
        env=env,
    )
    try:
        time.sleep(5)
        assert old.poll() is None, "Guarded rollback binary failed startup"
        passed(
            "guarded rollback binary starts with generated config and existing storage"
        )
    finally:
        if old.poll() is None:
            old.terminate()
            old.wait(timeout=15)
    try:
        Agent(home, os.environ["ARCH001_API_URL"], "/runtime/otelcol-contrib-0.123.0")
    except RuntimeError as error:
        assert "version mismatch" in str(error)
    else:
        raise AssertionError("Experimental supervisor accepted old runtime")
    passed(
        "experimental contract rejects old runtime; full coordinated rollback not approved"
    )
    report["status"] = "PASS"
except Exception as error:
    report["error"] = type(error).__name__ + ": " + str(error)
    raise
finally:
    if process is not None and process.poll() is None:
        process.terminate()
        process.wait(timeout=20)
    server.shutdown()
    server.server_close()
    (PRIVATE / "e2e.json").write_text(json.dumps(report, indent=2) + "\n")
