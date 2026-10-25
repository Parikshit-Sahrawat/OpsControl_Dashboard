"""Real local Linux process lifecycle in the disposable API container only."""

import asyncio
import json
from pathlib import Path
import subprocess
import sys
from uuid import UUID
from app.worker.collector_runtime import execute_collector
from scripts import http_golden_path_probe as golden

s = json.loads(golden.PRIVATE.read_text())
token = s["admin_token"]
process = None
rows = []
try:
    process = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(300)"])
    source = golden.api(
        201,
        "POST",
        "/api/v1/resource-management/data-sources",
        token,
        {
            "organization_id": s["org_id"],
            "name": "DEV05 local Linux process",
            "source_type": "LINUX_HOST",
            "connection_config": {"disk_path": "/", "process_pid": process.pid},
        },
    )
    versions = []
    for kind, name, definition in [
        (
            "METRIC",
            "DEV05 Linux availability",
            {"name": "infrastructure_up", "metric_type": "GAUGE"},
        ),
        (
            "ALERT",
            "DEV05 Linux process missing",
            {
                "name": "process-health",
                "metric_name": "infrastructure_up",
                "operator": "LT",
                "threshold_value": 0.5,
                "consecutive_breaches": 1,
                "severity": "CRITICAL",
            },
        ),
    ]:
        catalog = golden.api(
            201,
            "POST",
            "/api/v1/rule-catalogs",
            token,
            {
                "organization_id": s["org_id"],
                "kind": kind,
                "name": name,
                "definition": definition,
            },
        )
        versions.append(catalog["versions"][0]["id"])
    payload = {
        "include_templates": False,
        "rule_version_ids": versions,
        "remote_worker_id": None,
    }
    activated = golden.api(
        200, "POST", f"/api/v1/data-sources/{source['id']}/activations", token, payload
    )
    for phase in ("healthy", "failed", "recovered"):
        if phase == "failed":
            process.terminate()
            process.wait(timeout=5)
        if phase == "recovered":
            process = subprocess.Popen(
                [sys.executable, "-c", "import time;time.sleep(300)"]
            )
            golden.api(
                200,
                "PATCH",
                f"/api/v1/resource-management/data-sources/{source['id']}",
                token,
                {"connection_config": {"disk_path": "/", "process_pid": process.pid}},
            )
            activated = golden.api(
                200,
                "POST",
                f"/api/v1/data-sources/{source['id']}/activations",
                token,
                payload,
            )
        asyncio.run(execute_collector(UUID(activated["collector_id"])))
        item = golden.api(
            200,
            "GET",
            f"/api/v1/infrastructure/resources/{source['id']}",
            s["operator_token"],
        )
        assert item["health"] == ("CRITICAL" if phase == "failed" else "HEALTHY"), (
            phase,
            item["health"],
        )
        assert item["open_alert_count"] == (1 if phase == "failed" else 0)
        if phase == "recovered":
            assert (
                len(item["alerts"]) == 1 and item["alerts"][0]["status"] == "RESOLVED"
            )
        history = golden.api(
            200,
            "GET",
            f"/api/v1/infrastructure/resources/{source['id']}/history",
            s["operator_token"],
        )
        assert len(history) == len(rows) + 1
        rows.append(
            {
                "phase": phase,
                "health": item["health"],
                "history_count": len(history),
                "open_alerts": item["open_alert_count"],
            }
        )
    golden.api(
        404, "GET", f"/api/v1/infrastructure/resources/{source['id']}", s["other_token"]
    )
    print(
        "Live disposable Linux process monitoring, persisted history, alerts and tenant isolation PASS"
    )
finally:
    if process and process.poll() is None:
        process.terminate()
        process.wait(timeout=5)
    Path("/golden/evidence/infrastructure.json").write_text(
        json.dumps(
            {"origin": "DISPOSABLE_CONTAINER_LOCAL_LINUX", "phases": rows}, indent=2
        )
        + "\n"
    )
