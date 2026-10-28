"""Read actual disposable DB evidence, then reuse unchanged scoped API assertions."""

import json
import os
from pathlib import Path
import uuid
from sqlalchemy import select
from app.main import app
from app.db.session import SessionLocal
from app.models import LogEvent, LogSource, MetricSample, MetricDefinition
from scripts.arch001_acceptance_probe import call
from scripts.agent_v15_acceptance_probe import run

assert os.environ["ENVIRONMENT"] == "test"
private = Path(os.environ["ARCH001_PRIVATE_DIR"])
out = Path(os.environ["ARCH001_EVIDENCE_DIR"])
fixture = json.loads((private / "fixture.json").read_text())
evidence = json.loads((private / "e2e.json").read_text())
assert evidence["status"] == "PASS"
collector = uuid.UUID(evidence["collector_id"])
with SessionLocal() as db:
    logs = (
        db.execute(
            select(LogEvent.message)
            .join(LogSource)
            .where(LogSource.collector_id == collector)
        )
        .scalars()
        .all()
    )
    markers = {
        marker: sum(marker in message for message in logs)
        for marker in [
            "a3-initial",
            "a3-rotated",
            "a3-truncated",
            "a3-after-restart",
            "a3-after-outage",
        ]
    }
    assert all(count == 1 for count in markers.values()), markers
    assert any("a3-syslog" in message for message in logs)
    metrics = db.execute(
        select(MetricSample, MetricDefinition)
        .join(MetricDefinition)
        .where(MetricSample.collector_id == collector)
    ).all()
    services = [
        (sample, definition)
        for sample, definition in metrics
        if (definition.query_config or {}).get("otel_metric_name")
        == "opscontrol.process.count"
        and (sample.dimensions or {}).get("opscontrol.method.id")
        == evidence["methods"]["SERVICES"]
    ]
    assert services and any(sample.value_numeric > 0 for sample, definition in services)
    assert any(
        (definition.query_config or {})
        .get("otel_metric_name", "")
        .startswith("system.cpu")
        for sample, definition in metrics
    )
    assert any(
        (definition.query_config or {}).get("otel_metric_name") == "dev052a3_requests"
        for sample, definition in metrics
    )
report = {
    "status": "PASS",
    "file_markers_exactly_once": markers,
    "syslog_persisted": True,
    "service_process_observation_persisted": True,
    "host_cpu_and_scrape_persisted": True,
    "collector_id": str(collector),
}
(out / "persisted-evidence.json").write_text(json.dumps(report, indent=2) + "\n")
admin = fixture["token"]
department = call(
    "/api/v1/access/departments", "POST", {"name": "DEV052A3 lab"}, admin, 201
)
employee = call(
    "/api/v1/access/employees",
    "POST",
    {
        "username": "arch001-reader",
        "full_name": "Synthetic restricted reader",
        "password": fixture["password"],
        "department_id": department["id"],
    },
    admin,
    201,
)
role = next(
    r
    for r in call("/api/v1/access/roles", token=admin)
    if r["name"] == "Read-Only Viewer"
)
call(
    "/api/v1/access/employees/" + employee["id"] + "/roles",
    "POST",
    {"role_id": role["id"], "effect": "ALLOW"},
    admin,
    201,
)
call(
    "/api/v1/access/customer-grants",
    "POST",
    {
        "user_id": employee["id"],
        "organization_id": fixture["org"],
        "role_id": role["id"],
        "effect": "ALLOW",
    },
    admin,
    201,
)
print(run(fixture, call))
