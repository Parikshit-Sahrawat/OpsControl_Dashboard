"""Additional synthetic HTTP/database checks; extends the baseline golden probe."""

import json
import sys
from uuid import UUID
from sqlalchemy import select
from scripts import http_golden_path_probe as golden
from app.db.session import SessionLocal
from app.models import Collector
from app.worker.remote_models import RemoteProbeEvidence


def state():
    return json.loads(golden.PRIVATE.read_text())


def regression():
    s = state()
    token = s["operator_token"]
    orgs = golden.api(200, "GET", "/api/v1/organizations", token)
    assert s["org_id"] in {o["id"] for o in orgs}
    source = golden.api(
        201,
        "POST",
        "/api/v1/resource-management/data-sources",
        token,
        {
            "organization_id": s["org_id"],
            "name": "DEV05 template fixture",
            "source_type": "API",
            "endpoint": "https://portal.example.test/ready",
        },
    )
    template = golden.api(
        201,
        "POST",
        "/api/v1/monitoring/templates",
        s["admin_token"],
        {
            "name": "DEV05 synthetic API template",
            "scope": "API",
            "package_config": {
                "collector": {"type": "API", "interval_seconds": 30},
                "metrics": [
                    {
                        "name": "Availability",
                        "metric": "probe_up",
                        "method": "HTTP",
                        "extract": "AVAILABILITY",
                    }
                ],
                "alerts": [],
                "logs": [],
                "attributes": [],
            },
        },
    )
    golden.api(
        201,
        "POST",
        f"/api/v1/monitoring/data-sources/{source['id']}/templates",
        token,
        {"template_id": template["id"], "template_version": 1},
    )
    effective = golden.api(
        200,
        "GET",
        f"/api/v1/monitoring/data-sources/{source['id']}/effective-configuration",
        token,
    )
    assert effective["valid"]
    # Attachment saves a draft. Explicit activation is the supported materialization boundary.
    applied = golden.api(
        200,
        "POST",
        f"/api/v1/data-sources/{source['id']}/activations",
        token,
        {
            "remote_worker_id": s["worker_id"],
            "rule_version_ids": [],
            "include_templates": True,
        },
    )
    assert applied["status"] == "ACTIVE"
    collectors = golden.api(
        200,
        "GET",
        f"/api/v1/monitoring/collectors?data_source_id={source['id']}",
        token,
    )
    assert collectors
    golden.api(200, "POST", f"/api/v1/data-sources/{source['id']}/deactivation", token)
    # No local scheduler runs in this stack, so template collectors cannot access targets.
    print(
        "Synthetic organizations, scoped sources, versioned template materialization and collectors PASS"
    )


def configure_head():
    s = state()
    with SessionLocal() as db:
        collector = db.get(Collector, UUID(s["collector_id"]))
        collector.configuration = {
            **(collector.configuration or {}),
            "method": "HEAD",
            "max_response_time_ms": 10000,
            "headers": {"x-opscontrol-check": "dev05"},
        }
        db.commit()
    golden.schedule()


def verify_head():
    s = state()
    with SessionLocal() as db:
        from app.worker.remote_models import RemoteProbeJob

        job = db.scalars(
            select(RemoteProbeJob)
            .where(RemoteProbeJob.collector_id == UUID(s["collector_id"]))
            .order_by(RemoteProbeJob.created_at.desc())
        ).first()
        assert job.state == "COMPLETED" and job.config_snapshot["method"] == "HEAD"
        result = db.scalar(
            select(RemoteProbeEvidence).where(RemoteProbeEvidence.job_id == job.id)
        ).result
        assert result["outcome"] == "SUCCESS" and result["http_status"] == 200
        assert (
            result["response_size_bytes"] == 0
            and 0 <= result["response_time_ms"] <= 10000
        )
    diagnostics = golden.api(
        200,
        "GET",
        "/api/v1/data-sources/" + s["source_id"] + "/diagnostics",
        s["operator_token"],
    )
    assert diagnostics["metric_sample_count"] == 4
    print(
        "Real HEAD with approved header, latency assertion and persisted evidence PASS"
    )


def authorization():
    s = state()
    golden.api(401, "POST", "/api/v1/worker/heartbeat", body={})
    golden.api(401, "POST", "/api/v1/worker/heartbeat", "invalid-synthetic-token", {})
    golden.api(401, "POST", "/api/v1/worker/heartbeat", s["operator_token"], {})
    golden.api(200, "POST", "/api/v1/worker/heartbeat", s["worker_token"], {})
    golden.api(
        422,
        "POST",
        "/api/v1/worker/heartbeat",
        s["worker_token"],
        {"last_seen_at": "2030-01-01T00:00:00Z"},
    )
    # A worker identity cannot perform human administration.
    golden.api(401, "GET", "/api/v1/organizations", s["worker_token"])
    other = golden.api(
        201,
        "POST",
        "/api/v1/auth/workers",
        s["admin_token"],
        {
            "organization_id": s["other_org_id"],
            "name": "DEV05 cross-tenant worker",
            "expires_in_days": 1,
        },
    )
    golden.api(
        403,
        "PUT",
        "/api/v1/remote-probes/collectors/" + s["collector_id"] + "/assignment",
        s["admin_token"],
        {"worker_id": other["id"]},
    )
    from datetime import datetime, timezone
    from uuid import uuid4

    with SessionLocal() as db:
        from app.worker.remote_models import RemoteProbeJob

        job = db.scalars(
            select(RemoteProbeJob).where(
                RemoteProbeJob.collector_id == UUID(s["collector_id"])
            )
        ).first()
        job_id = str(job.id)
    golden.api(
        404,
        "POST",
        "/api/v1/worker/results",
        other["worker_token"],
        {
            "event_id": str(uuid4()),
            "job_id": job_id,
            "lease_nonce": "synthetic-invalid-lease-" * 3,
            "outcome": "SUCCESS",
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "http_status": 200,
            "response_time_ms": 1,
            "response_size_bytes": 0,
        },
    )
    for cfg in (
        {"method": "POST"},
        {"headers": {"Authorization": "synthetic"}},
        {"headers": {"x-opscontrol-check": "bad\r\nHeader: value"}},
    ):
        golden.api(
            422,
            "POST",
            "/api/v1/data-sources/" + s["source_id"] + "/activation-preview",
            s["operator_token"],
            {
                "remote_worker_id": s["worker_id"],
                "rule_version_ids": s["versions"],
                "include_templates": False,
                "api_config": cfg,
            },
        )
    from app.security.models import WorkerIdentity

    with SessionLocal() as db:
        worker = db.get(WorkerIdentity, UUID(s["worker_id"]))
        worker.enabled = False
        db.commit()
    golden.api(401, "POST", "/api/v1/worker/heartbeat", s["worker_token"], {})
    print(
        "Anonymous, invalid, human, revoked worker and forged heartbeat boundaries PASS"
    )


if __name__ == "__main__":
    import os

    assert (
        os.environ.get("ENVIRONMENT") == "demo"
        and os.environ.get("OPSCONTROL_GOLDEN_PATH") == "1"
    )
    command = sys.argv[1]
    commands = {
        "setup": golden.setup,
        "schedule": golden.schedule,
        "isolation": golden.isolation,
        "regression": regression,
        "configure-head": configure_head,
        "verify-head": verify_head,
        "authorization": authorization,
    }
    if command == "infrastructure":
        import runpy

        runpy.run_path("/verification/infrastructure.py", run_name="__main__")
    elif command in commands:
        commands[command]()
        if command == "setup":
            s = state()
            from pathlib import Path

            Path("/golden/private/worker-session.json").write_text(
                json.dumps({"worker_token": s["worker_token"]})
            )
            keys = (
                "operator_username",
                "operator_password",
                "other_username",
                "other_password",
                "source_id",
            )
            Path("/golden/private/browser-session.json").write_text(
                json.dumps({key: s[key] for key in keys})
            )
    else:
        golden.verify(command)
