"""Actual local Agent/Contrib/TLS pipeline with explicitly controlled ETL logs."""

import json, os, socket, subprocess, sys, time
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy import select, func
from app.main import app  # Register scoped and unified mappings in this test process.
from app.db.session import SessionLocal
from app.models import JobOrderHistory, LogEvent, MetricSample, MetricDefinition
from app.telemetry.models import TraceSpan
from app.unified.models import MonitoringResource
from app.unified.engines import cycle
from scripts.arch001_acceptance_probe import call

assert (
    os.environ.get("ENVIRONMENT") == "test"
    and os.environ.get("OPSCONTROL_ARCH001_ACCEPTANCE") == "1"
)
private = Path(os.environ["ARCH001_PRIVATE_DIR"])
out = Path(os.environ["ARCH001_EVIDENCE_DIR"])
f = json.loads((private / "fixture.json").read_text())
token = f["token"]
vm = f["linux_resource"]
base = os.environ["ARCH001_API_URL"]
prefix = "/api/v1/agent-control/collectors/" + vm["primary_collector_id"]
logfile = private / "pipeline.log"
logfile.write_text("")
logfile.chmod(0o600)
etl = call(
    "/api/v1/unified/resources/etl",
    "POST",
    {
        "name": "Controlled runtime pipeline",
        "platform": "PENTAHO",
        "vm_resource_id": vm["id"],
        "jobchain": "Runtime pipeline",
        "log_paths": [str(logfile)],
    },
    token,
    201,
)
with socket.socket() as s:
    s.bind(("127.0.0.1", 0))
    otlp = s.getsockname()[1]
call(
    prefix + "/methods",
    "POST",
    {
        "name": "Explicit application signals",
        "method_type": "OTLP_RECEIVER",
        "configuration": {"signals": ["Logs", "Metrics", "Traces"], "port": otlp},
    },
    token,
    201,
)
version = call(prefix + "/versions", "POST", token=token, expected=201)
assert version["validation_status"] == "VALIDATED"
enroll = call(prefix + "/registration", "POST", token=token, expected=201)
home = private / "runtime-agent"
home.mkdir(mode=0o700)
enrollment = home / "enrollment"
enrollment.write_text(enroll["enrollment_token"])
enrollment.chmod(0o600)
log = open(private / "runtime-agent.log", "w")
p = subprocess.Popen(
    [
        sys.executable,
        str(Path(__file__).resolve().parents[2] / "agent/opscontrol_agent.py"),
        "--home",
        str(home),
        "--backend",
        base,
        "--runtime",
        os.environ["OPSCONTROL_OTEL_BINARY"],
        "--enrollment-file",
        str(enrollment),
        "--poll-seconds",
        "5",
    ],
    env=os.environ.copy(),
    stdout=log,
    stderr=subprocess.STDOUT,
)


def wait_for(predicate, label, attempts=150):
    for _ in range(attempts):
        if predicate():
            return
        if p.poll() is not None:
            raise RuntimeError("Owned agent exited during " + label)
        time.sleep(0.2)
    raise AssertionError("Actual pipeline timed out: " + label)


try:
    wait_for(lambda: (home / "identity.json").exists(), "enrollment")
    call(
        prefix + "/apply",
        "POST",
        {"revision": version["revision"], "approve": True},
        token,
    )
    wait_for(
        lambda: call(prefix, token=token)["agent"]["applied_revision"]
        == version["revision"],
        "configuration",
    )
    # The actual upstream receiver must forward all selected signals before activation.
    from urllib.request import Request, urlopen

    timestamp = str(time.time_ns())
    trace = {
        "resourceSpans": [
            {
                "scopeSpans": [
                    {
                        "spans": [
                            {
                                "traceId": "1123456789abcdef0123456789abcdef",
                                "spanId": "1123456789abcdef",
                                "name": "controlled-arch001-span",
                                "startTimeUnixNano": timestamp,
                                "endTimeUnixNano": str(time.time_ns()),
                            }
                        ]
                    }
                ]
            }
        ]
    }
    with urlopen(
        Request(
            f"http://127.0.0.1:{otlp}/v1/traces",
            data=json.dumps(trace).encode(),
            headers={"Content-Type": "application/json"},
        ),
        timeout=10,
    ) as response:
        assert response.status == 200
    with logfile.open("a") as stream:
        stream.write(
            json.dumps(
                {
                    "execution_id": "runtime-run-1",
                    "event": "START",
                    "status": "RUNNING",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
            + "\n"
        )
    wait_for(
        lambda: call(
            "/api/v1/unified/resources/" + vm["id"] + "/verification", token=token
        )["ready"],
        "actual signal reception",
        300,
    )
    for root, domain in [(vm, "VM"), (etl, "ETL")]:
        saved = call(
            "/api/v1/unified/parameters/" + root["id"],
            "POST",
            {
                "expected_resource_revision": root["revision"],
                "configuration": {"domain": domain},
            },
            token,
            201,
        )
        call(
            "/api/v1/unified/parameters/" + root["id"] + "/activate",
            "POST",
            {"version": saved["version"], "approve": True},
            token,
        )
        call(
            "/api/v1/unified/resources/" + root["id"] + "/activate",
            "POST",
            {"approve": True},
            token,
        )
    with logfile.open("a") as stream:
        stream.write(
            json.dumps(
                {
                    "execution_id": "runtime-run-1",
                    "event": "END",
                    "status": "FAILED",
                    "error": "controlled runtime failure",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
            + "\n"
        )

    def reconstructed():
        cycle()
        with SessionLocal() as db:
            history = db.scalar(
                select(JobOrderHistory).where(
                    JobOrderHistory.job_order_id == etl["job_order_id"],
                    JobOrderHistory.provider_execution_id == "runtime-run-1",
                )
            )
            return history and history.status.value == "FAILED"

    wait_for(reconstructed, "authenticated filelog execution reconstruction", 300)
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(LogEvent)) > 0
        assert (
            db.scalar(
                select(func.count())
                .select_from(TraceSpan)
                .where(TraceSpan.name == "controlled-arch001-span")
            )
            > 0
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(MetricSample)
                .join(MetricDefinition)
                .where(MetricDefinition.data_source_id == vm["data_source_id"])
            )
            > 0
        )
    alerts = call(
        "/api/v1/unified/alerts?organization_id=" + vm["organization_id"], token=token
    )
    assert any(
        a.get("resource_id") == etl["id"] and a["status"] == "OPEN"
        for a in alerts["alerts"]
    )
    with logfile.open("a") as stream:
        for event, status in [("START", "RUNNING"), ("END", "SUCCESS")]:
            stream.write(
                json.dumps(
                    {
                        "execution_id": "runtime-run-2",
                        "event": event,
                        "status": status,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )
                + "\n"
            )

    def recovered():
        cycle()
        entries = call(
            "/api/v1/unified/alerts?organization_id=" + vm["organization_id"],
            token=token,
        )["alerts"]
        failures = [
            a
            for a in entries
            if a.get("resource_id") == etl["id"] and "ETL_FAILURE" in a["metric_name"]
        ]
        return failures and all(a["status"] == "RESOLVED" for a in failures)

    wait_for(recovered, "actual successful run recovery", 300)
    # Native API and IICS-style adapters must execute through real verified TLS.
    from urllib.parse import urlsplit

    target = urlsplit(os.environ["ARCH001_TARGET_URL"])
    api = call(
        "/api/v1/unified/resources/api",
        "POST",
        {
            "name": "Controlled native HTTPS probe",
            "organization_id": vm["organization_id"],
            "environment": "QA",
            "dns": target.hostname,
            "port": target.port,
            "frequency_seconds": 5,
            "path": "/health",
        },
        token,
        201,
    )
    cloud = call(
        "/api/v1/unified/resources/etl",
        "POST",
        {
            "name": "Controlled cloud metadata",
            "organization_id": vm["organization_id"],
            "environment": "QA",
            "platform": "IICS",
            "jobchain": "Cloud pipeline",
            "connector_url": os.environ["ARCH001_TARGET_URL"] + "/records",
            "credential_ref": "env:ARCH001_PROVIDER_TOKEN",
            "frequency_seconds": 5,
        },
        token,
        201,
    )
    for root, domain in [(api, "API"), (cloud, "ETL")]:
        saved = call(
            "/api/v1/unified/parameters/" + root["id"],
            "POST",
            {
                "expected_resource_revision": root["revision"],
                "configuration": {"domain": domain},
            },
            token,
            201,
        )
        call(
            "/api/v1/unified/parameters/" + root["id"] + "/activate",
            "POST",
            {"version": saved["version"], "approve": True},
            token,
        )
        call(
            "/api/v1/unified/resources/" + root["id"] + "/start-probe",
            "POST",
            {"approve": True},
            token,
        )
    worker_log = open(private / "native-worker.log", "w")
    worker = subprocess.Popen(
        [sys.executable, "-m", "scripts.run_collector_worker"],
        cwd=Path(__file__).resolve().parents[1],
        env=os.environ.copy(),
        stdout=worker_log,
        stderr=subprocess.STDOUT,
    )
    try:
        for root in [api, cloud]:
            wait_for(
                lambda: call(
                    "/api/v1/unified/resources/" + root["id"] + "/verification",
                    token=token,
                )["ready"],
                "real native TLS evidence",
                300,
            )
            call(
                "/api/v1/unified/resources/" + root["id"] + "/activate",
                "POST",
                {"approve": True},
                token,
            )
        state = {
            "http_status": 503,
            "records": [
                {
                    "execution_id": "cloud-runtime-1",
                    "status": "FAILED",
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "ended_at": datetime.now(timezone.utc).isoformat(),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ],
        }
        (private / "target.json").write_text(json.dumps(state))

        def native_open():
            entries = call(
                "/api/v1/unified/alerts?organization_id=" + vm["organization_id"],
                token=token,
            )["alerts"]
            return any(
                a.get("resource_id") == api["id"]
                and a.get("condition_type") == "API_UNAVAILABLE"
                and a["status"] == "OPEN"
                for a in entries
            ) and any(
                a.get("resource_id") == cloud["id"]
                and "ETL_FAILURE" in a["metric_name"]
                and a["status"] == "OPEN"
                for a in entries
            )

        wait_for(
            native_open, "real TLS native API failure and metadata reconstruction", 600
        )
        state["http_status"] = 200
        (private / "target.json").write_text(json.dumps(state))

        def native_recovered():
            entries = call(
                "/api/v1/unified/alerts?organization_id=" + vm["organization_id"],
                token=token,
            )["alerts"]
            matched = [
                a
                for a in entries
                if a.get("resource_id") == api["id"]
                and a.get("condition_type") == "API_UNAVAILABLE"
            ]
            return matched and all(a["status"] == "RESOLVED" for a in matched)

        wait_for(native_recovered, "real native HTTPS recovery", 600)
    finally:
        worker.terminate()
        try:
            worker.wait(timeout=15)
        except subprocess.TimeoutExpired:
            worker.kill()
            worker.wait(timeout=10)
        worker_log.close()
    (out / "runtime.json").write_text(
        json.dumps(
            {
                "status": "PASS",
                "origin": "ACTUAL_AGENT_1.1_CONTRIB_0.123_VERIFIED_TLS",
                "controlled_etl_logs": True,
                "actual_metrics_logs_traces": True,
                "actual_reconstructed_failure_alert": True,
                "actual_native_https_failure_recovery": True,
                "controlled_iics_style_metadata_over_tls": True,
                "production_modified": False,
            },
            indent=2,
        )
    )
    print(
        "Actual Agent + pinned Contrib logs/metrics/traces over verified TLS; filelog execution reconstruction and native failure alert PASS"
    )
finally:
    p.terminate()
    try:
        p.wait(timeout=15)
    except subprocess.TimeoutExpired:
        p.kill()
        p.wait(timeout=10)
    log.close()
