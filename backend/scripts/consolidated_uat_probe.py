"""Real HTTP/PostgreSQL and upstream Collector acceptance; all inputs are controlled."""

import gzip, hashlib, json, os, secrets, ssl, subprocess, time, uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from sqlalchemy import create_engine, select, func
from app.core.config import settings
from app.models import (
    MetricDefinition,
    MetricSample,
    LogEvent,
    AlertState,
    AlertNotificationDelivery,
    Organization,
)
from app.telemetry.models import TelemetryReceipt, TraceSpan, ManagedAgent
from app.worker.notifications import dispatch_pending_notifications
from app.telemetry.configuration import validate_binary

PRIVATE = Path(os.environ["UAT_PRIVATE_DIR"])
OUT = Path(os.environ["UAT_EVIDENCE_DIR"])
f = json.loads((PRIVATE / "fixture.json").read_text())
BASE = os.environ["UAT_BASE_URL"]
context = ssl.create_default_context(cafile=str(PRIVATE / "ca.pem"))
checks = []


def request(
    path,
    method="GET",
    body=None,
    token=None,
    expected=200,
    protobuf=None,
    compress=False,
):
    data = json.dumps(body).encode() if body is not None else protobuf
    headers = {
        "Content-Type": (
            "application/x-protobuf" if protobuf is not None else "application/json"
        )
    }
    if compress:
        data = gzip.compress(data)
        headers["Content-Encoding"] = "gzip"
    if token:
        headers["Authorization"] = "Bearer " + token
    req = Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urlopen(req, context=context, timeout=15) as r:
            assert r.status == expected, (path, r.status, expected)
            raw = r.read()
            return (
                json.loads(raw)
                if raw and headers["Content-Type"] == "application/json"
                else raw
            )
    except HTTPError as e:
        detail = json.loads(e.read() or b"{}").get("detail", "")
        assert e.code == expected, (
            path,
            e.code,
            expected,
            detail if isinstance(detail, str) else "Validation rejected",
        )
        return None


def passed(label):
    checks.append(label)
    print("PASS " + label, flush=True)


def main():
    admin = request(
        "/api/v1/auth/login",
        "POST",
        {"username": "uat-admin", "password": f["password"]},
    )["access_token"]
    org = f["organization"]
    other = f["other"]
    department = request(
        "/api/v1/access/departments",
        "POST",
        {"name": "Observability", "code": "UAT-NOC"},
        admin,
        201,
    )
    employee = request(
        "/api/v1/access/employees",
        "POST",
        {
            "username": "uat-viewer",
            "full_name": "UAT Viewer",
            "password": f["password"],
            "department_id": department["id"],
        },
        admin,
        201,
    )
    request(
        "/api/v1/access/employees",
        "POST",
        {"username": "no-department", "full_name": "UAT", "password": f["password"]},
        admin,
        422,
    )
    second = request(
        "/api/v1/access/departments",
        "POST",
        {"name": "Platform Engineering", "code": "UAT-OPS"},
        admin,
        201,
    )
    request(
        "/api/v1/access/departments/" + second["id"] + "/members",
        "POST",
        {"user_id": employee["id"]},
        admin,
        409,
    )
    roles = request("/api/v1/access/roles", token=admin)
    viewer = next(r for r in roles if r["name"] == "Read-Only Viewer")
    request(
        "/api/v1/access/employees/" + employee["id"] + "/roles",
        "POST",
        {"role_id": viewer["id"], "effect": "ALLOW"},
        admin,
        201,
    )
    request(
        "/api/v1/access/customer-grants",
        "POST",
        {
            "user_id": employee["id"],
            "organization_id": org,
            "role_id": viewer["id"],
            "effect": "ALLOW",
        },
        admin,
        201,
    )
    viewer_token = request(
        "/api/v1/auth/login",
        "POST",
        {"username": "uat-viewer", "password": f["password"]},
    )["access_token"]
    request("/api/v1/access/employees", token=viewer_token, expected=403)
    request(
        "/api/v1/access/employees/" + employee["id"] + "/department",
        "PUT",
        {"department_id": second["id"]},
        viewer_token,
        403,
    )
    passed(
        "Separate organizations/departments, exact-one creation, no self escalation and direct access denial"
    )
    source = request(
        "/api/v1/monitoring/data-sources",
        "POST",
        {
            "organization_id": org,
            "name": "UAT host",
            "source_type": "LINUX",
            "connection_config": {
                "opscontrol": {"os_type": "Linux", "hostname": "uat-host.example.test"}
            },
        },
        admin,
        201,
    )
    collector = request(
        "/api/v1/monitoring/collectors",
        "POST",
        {
            "data_source_id": source["id"],
            "name": "UAT logical Collector",
            "collector_type": "OTEL",
            "enabled": True,
            "configuration": {"os_metrics": True},
        },
        admin,
        201,
    )
    prefix = "/api/v1/agent-control/collectors/" + collector["id"]
    defaults = request(prefix + "/template-defaults", token=admin)
    assert defaults["methods"] == [] and defaults["saved"] is False
    request(prefix + "/template-defaults", token=viewer_token)

    logfile = PRIVATE / "controlled.log"
    logfile.write_text("controlled initial log\n")
    m = request(
        prefix + "/methods",
        "POST",
        {
            "name": "File logs A",
            "method_type": "FILE_LOG",
            "configuration": {"paths": [str(logfile)], "start_at": "beginning"},
        },
        admin,
        201,
    )
    second_method = request(
        prefix + "/methods",
        "POST",
        {
            "name": "File logs B",
            "method_type": "FILE_LOG",
            "configuration": {"paths": [str(logfile)], "start_at": "beginning"},
        },
        admin,
        201,
    )
    assert m["id"] != second_method["id"]
    invalid = {
        "name": "Bad",
        "method_type": "OTLP_RECEIVER",
        "configuration": {"signals": ["Logs"], "bind": "0.0.0.0"},
    }
    request(prefix + "/methods", "POST", invalid, admin, 422)
    request(
        prefix + "/methods",
        "POST",
        {
            "name": "Windows log",
            "method_type": "FILE_LOG",
            "configuration": {"source": "WINDOWS_EVENT"},
        },
        admin,
        422,
    )
    otlp = request(
        prefix + "/methods",
        "POST",
        {
            "name": "Local application OTLP",
            "method_type": "OTLP_RECEIVER",
            "configuration": {
                "signals": ["Logs", "Metrics", "Traces"],
                "port": int(os.environ["UAT_OTLP_PORT"]),
            },
        },
        admin,
        201,
    )
    update = {k: second_method[k] for k in ("name", "method_type", "configuration")}
    update.update(enabled=False, expected_revision=second_method["revision"])
    disabled = request(prefix + "/methods/" + second_method["id"], "PUT", update, admin)
    request(prefix + "/methods/" + second_method["id"], "PUT", update, admin, 409)
    request(prefix, token=viewer_token)
    request(
        prefix + "/methods",
        "POST",
        {
            "name": "Denied",
            "method_type": "FILE_LOG",
            "configuration": {"paths": [str(logfile)]},
        },
        viewer_token,
        403,
    )
    foreign = request(
        "/api/v1/monitoring/data-sources",
        "POST",
        {
            "organization_id": other,
            "name": "Other host",
            "source_type": "LINUX",
            "connection_config": {"opscontrol": {"os_type": "Linux"}},
        },
        admin,
        201,
    )
    foreign_c = request(
        "/api/v1/monitoring/collectors",
        "POST",
        {
            "data_source_id": foreign["id"],
            "name": "Other collector",
            "collector_type": "OTEL",
        },
        admin,
        201,
    )
    request(
        "/api/v1/agent-control/collectors/" + foreign_c["id"],
        token=viewer_token,
        expected=404,
    )
    request(
        prefix + "/methods/" + second_method["id"], "DELETE", token=admin, expected=204
    )
    passed(
        "Independent same-type method identities, CRUD/revision conflicts, OS/listener validation and tenant isolation"
    )
    preview = request(prefix + "/preview", token=admin)
    validate_binary(preview["yaml"])
    version = request(prefix + "/versions", "POST", token=admin, expected=201)
    assert version["validation_status"] == "VALIDATED"
    enroll = request(prefix + "/registration", "POST", token=admin, expected=201)
    registration = {
        "enrollment_token": enroll["enrollment_token"],
        "hostname": "uat-host.example.test",
        "os_type": "Linux",
        "version": "1.0.0",
        "runtime_version": "0.123.0",
    }
    request(
        "/api/v1/agent/register",
        "POST",
        {**registration, "os_type": "Windows"},
        expected=422,
    )
    agent_home = PRIVATE / "agent-state"
    agent_home.mkdir(mode=0o700)
    enrollment_file = agent_home / "enrollment"
    enrollment_file.write_text(enroll["enrollment_token"])
    enrollment_file.chmod(0o600)
    log = open(PRIVATE / "agent.log", "w")
    process = subprocess.Popen(
        [
            __import__("sys").executable,
            str(Path(__file__).resolve().parents[2] / "agent" / "opscontrol_agent.py"),
            "--home",
            str(agent_home),
            "--backend",
            BASE,
            "--runtime",
            os.environ["OPSCONTROL_OTEL_BINARY"],
            "--enrollment-file",
            str(enrollment_file),
            "--poll-seconds",
            "5",
        ],
        env=os.environ.copy(),
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    try:
        for _ in range(100):
            if (agent_home / "identity.json").exists():
                break
            if process.poll() is not None:
                raise RuntimeError("Actual agent enrollment failed")
            time.sleep(0.2)
        else:
            raise RuntimeError("Actual agent enrollment timed out")
        agent_token = json.loads((agent_home / "identity.json").read_text())[
            "access_token"
        ]
        request("/api/v1/agent/register", "POST", registration, expected=401)
        request(
            prefix + "/apply",
            "POST",
            {"revision": version["revision"], "approve": False},
            admin,
            422,
        )
        request(
            prefix + "/apply",
            "POST",
            {"revision": version["revision"], "approve": True},
            admin,
        )
        for _ in range(100):
            info = request(prefix, token=admin)
            if (
                info["agent"]["health"] == "RUNNING"
                and info["agent"]["applied_revision"] == version["revision"]
            ):
                break
            time.sleep(0.2)
        else:
            raise RuntimeError("Actual agent failed to apply the approved config")
        config = request("/api/v1/agent/configuration", token=agent_token)
        assert (
            config["sha256"] == hashlib.sha256(config["yaml_text"].encode()).hexdigest()
        )
        request(
            "/api/v1/agent/heartbeat",
            "POST",
            {
                "version": "1.0.0",
                "runtime_version": "0.123.0",
                "applied_revision": 999,
                "health": "RUNNING",
            },
            agent_token,
            409,
        )
        passed(
            "Pinned binary validates real YAML; one-time enrollment, authentication and approved runtime configuration"
        )
        with logfile.open("a") as stream:
            stream.write("actual filelog acceptance message\n")
        # Send a controlled span through the actual upstream OTLP receiver.
        trace = {
            "resourceSpans": [
                {
                    "resource": {
                        "attributes": [
                            {
                                "key": "service.name",
                                "value": {"stringValue": "controlled-uat"},
                            }
                        ]
                    },
                    "scopeSpans": [
                        {
                            "spans": [
                                {
                                    "traceId": "0123456789abcdef0123456789abcdef",
                                    "spanId": "0123456789abcdef",
                                    "name": "controlled-uat-span",
                                    "startTimeUnixNano": str(time.time_ns() - 1000000),
                                    "endTimeUnixNano": str(time.time_ns()),
                                }
                            ]
                        }
                    ],
                }
            ]
        }
        req = Request(
            "http://127.0.0.1:" + os.environ["UAT_OTLP_PORT"] + "/v1/traces",
            data=json.dumps(trace).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(req, timeout=10) as r:
            assert r.status == 200
        for _ in range(160):
            status = request(prefix, token=admin)
            if {s["signal"] for s in status["signals"] if s["count"] > 0} == {
                "logs",
                "metrics",
                "traces",
            }:
                break
            time.sleep(0.3)
        else:
            raise RuntimeError("Real Collector signal reception did not complete")
        assert process.poll() is None
        bad_method = request(
            prefix + "/methods",
            "POST",
            {
                "name": "Controlled missing file",
                "method_type": "FILE_LOG",
                "configuration": {"paths": [str(PRIVATE / "missing.log")]},
            },
            admin,
            201,
        )
        bad_version = request(prefix + "/versions", "POST", token=admin, expected=201)
        request(
            prefix + "/apply",
            "POST",
            {"revision": bad_version["revision"], "approve": True},
            admin,
        )
        for _ in range(100):
            info = request(prefix, token=admin)
            if info["agent"]["last_error"] == "LOG_PATH_NOT_FOUND":
                break
            time.sleep(0.2)
        else:
            raise RuntimeError("Actual agent did not report missing-file failure")
        assert info["agent"]["applied_revision"] == version["revision"]
        assert any(
            d["revision"] == bad_version["revision"] and d["status"] == "FAILED"
            for d in info["deployments"]
        )
        request(
            prefix + "/methods/" + bad_method["id"], "DELETE", token=admin, expected=204
        )
        request(
            prefix + "/apply",
            "POST",
            {"revision": version["revision"], "approve": True},
            admin,
        )
        for _ in range(100):
            info = request(prefix, token=admin)
            if (
                info["agent"]["health"] == "RUNNING"
                and info["agent"]["last_error"] is None
            ):
                break
            time.sleep(0.2)
        else:
            raise RuntimeError("Actual agent did not converge after rollback approval")
        passed(
            "Actual agent supervises Contrib, reports source-read failures, retains prior config and applies approved rollback"
        )
        passed(
            "Actual Contrib filelog, native hostmetrics and OTLP traces reach PostgreSQL over verified TLS"
        )
    finally:
        process.terminate()
        process.wait(timeout=15)
        log.close()

    # Actual protocol inputs are explicitly controlled, not production telemetry.
    def metric_batch(values):
        return {
            "resourceMetrics": [
                {
                    "resource": {
                        "attributes": [
                            {
                                "key": "service.name",
                                "value": {"stringValue": "controlled-rule-fixture"},
                            }
                        ]
                    },
                    "scopeMetrics": [
                        {
                            "metrics": [
                                {
                                    "name": "controlled.cpu.percent",
                                    "unit": "%",
                                    "gauge": {
                                        "dataPoints": [
                                            {
                                                "timeUnixNano": str(
                                                    int(t.timestamp() * 1e9)
                                                ),
                                                "asDouble": value,
                                            }
                                            for t, value in values
                                        ]
                                    },
                                }
                            ]
                        }
                    ],
                }
            ]
        }

    observed = datetime.now(timezone.utc)
    request(
        "/api/v1/agent/otlp/v1/metrics",
        "POST",
        metric_batch([(observed - timedelta(minutes=7), 10)]),
        agent_token,
    )
    engine = create_engine(settings.database_url)
    with engine.connect() as db:
        metric = db.execute(
            select(MetricDefinition.id).where(
                MetricDefinition.collector_id == uuid.UUID(collector["id"]),
                MetricDefinition.name.like("controlled.cpu.percent [%"),
            )
        ).scalar_one()
    destination = request(
        "/api/v1/notification-delivery",
        "POST",
        {
            "organization_id": org,
            "name": "UAT in-app",
            "channel": "IN_APP",
            "configuration": {},
        },
        admin,
        201,
    )
    event = {
        "organization_id": org,
        "metric_definition_id": str(metric),
        "name": "CPU sustained 80 percent",
        "threshold_percentage": 80,
        "time_window_minutes": 5,
        "minimum_event_count": 2,
        "destinations": [destination["id"]],
    }
    rule = request("/api/v1/event-parameters", "POST", event, admin, 201)
    request(
        "/api/v1/agent/otlp/v1/metrics",
        "POST",
        metric_batch([(observed - timedelta(minutes=6), 95)]),
        agent_token,
    )
    assert not request("/api/v1/operations/alerts", token=admin)[
        "alerts"
    ], "Single sample must not establish five minutes"
    values = [
        (observed - timedelta(minutes=5) + timedelta(minutes=i), 95) for i in range(6)
    ]
    batch = metric_batch(values)
    request("/api/v1/agent/otlp/v1/metrics", "POST", batch, agent_token)
    opened = request("/api/v1/operations/alerts", token=admin)["alerts"]
    assert len(opened) == 1 and opened[0]["status"] == "OPEN"
    request("/api/v1/agent/otlp/v1/metrics", "POST", batch, agent_token)
    assert len(request("/api/v1/operations/alerts", token=admin)["alerts"]) == 1
    request(
        "/api/v1/operations/alerts/" + opened[0]["id"] + "/acknowledge",
        "POST",
        token=viewer_token,
        expected=403,
    )
    request(
        "/api/v1/operations/alerts/" + opened[0]["id"] + "/acknowledge",
        "POST",
        token=admin,
    )
    request(
        "/api/v1/agent/otlp/v1/metrics",
        "POST",
        metric_batch([(observed + timedelta(seconds=10), 10)]),
        agent_token,
    )
    state = request("/api/v1/operations/alerts", token=admin)["alerts"][0]
    assert state["status"] == "RESOLVED"
    from app.db.session import SessionLocal
    from app.worker.notifications import deliver

    with SessionLocal() as db:
        pending = db.scalar(
            select(AlertNotificationDelivery).where(
                AlertNotificationDelivery.status == "PENDING"
            )
        )
        current = db.get(AlertState, pending.alert_state_id)
        try:
            assert deliver(pending, current).startswith("in-app:")
        except Exception as error:
            import traceback

            raise AssertionError(
                (
                    type(error).__name__,
                    [
                        (frame.name, frame.lineno)
                        for frame in traceback.extract_tb(error.__traceback__)
                    ],
                )
            ) from None
    dispatch_result = dispatch_pending_notifications()
    deliveries = request(
        "/api/v1/notification-delivery?organization_id=" + org, token=admin
    )["deliveries"]
    assert len(deliveries) == 2 and all(d["status"] == "SENT" for d in deliveries), (
        dispatch_result,
        [(d["status"], d["last_error"]) for d in deliveries],
    )
    passed(
        "Real stored metric window, deduplicated OPEN→RESOLVED, acknowledgment scope and independently delivered in-app notifications"
    )
    request("/api/v1/operations/incidents", token=admin, expected=404)
    request(
        "/api/v1/operations/incidents/00000000-0000-0000-0000-000000000000/transitions",
        "POST",
        {},
        admin,
        404,
    )
    request("/api/v1/agent/configuration", token=viewer_token, expected=401)
    request(
        "/api/v1/agent/otlp/v1/logs",
        "POST",
        {"resourceLogs": []},
        token="unknown-token",
        expected=401,
    )
    request(
        "/api/v1/notification-delivery?organization_id=" + other,
        token=viewer_token,
        expected=403,
    )
    request(
        "/api/v1/event-parameters?organization_id=" + other,
        token=viewer_token,
        expected=403,
    )
    request("/api/v1/agent-control/packages/windows", token=admin, expected=503)
    passed(
        "Removed ITSM APIs, unconfigured Windows package is unavailable, service/user identity separation and scoped rule/destination denial"
    )
    # Export non-secret browser fixture coordinates, never credentials.
    (PRIVATE / "browser-fixture.json").write_text(
        json.dumps(
            {
                "organization": org,
                "collector_id": collector["id"],
                "source_id": source["id"],
                "department_id": department["id"],
                "employee_id": employee["id"],
            }
        )
    )
    (OUT / "security-telemetry.json").write_text(
        json.dumps(
            {
                "status": "PASS",
                "checks": checks,
                "runtime": "otelcol-contrib 0.123.0",
                "synthetic_inputs_labeled": True,
                "live_host_metrics": True,
                "signals": ["logs", "metrics", "traces"],
                "production_data_modified": False,
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
