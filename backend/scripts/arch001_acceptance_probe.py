"""Explicit controlled ARCH-001 fixture; never a production bootstrap."""

import hashlib, json, os, secrets, sys, uuid
from pathlib import Path
from sqlalchemy import create_engine, text, select, func
from app.core.config import settings
from app.security.passwords import hash_password
from app.db.session import SessionLocal
from app.models import *
from app.unified.models import *

assert (
    os.getenv("OPSCONTROL_ARCH001_ACCEPTANCE") == "1" and settings.environment == "test"
)
PRIVATE = Path(os.environ["ARCH001_PRIVATE_DIR"])
OUT = Path(os.environ["ARCH001_EVIDENCE_DIR"])


def seed():
    f = {
        k: str(uuid.uuid4())
        for k in (
            "admin",
            "org",
            "other",
            "vm",
            "unknown_vm",
            "source",
            "other_source",
            "job",
            "history",
            "step",
            "api_source",
        )
    }
    f["password"] = secrets.token_urlsafe(32)
    e = create_engine(settings.database_url)
    with e.begin() as c:
        for key, name in [
            ("org", "Fictional Platform North"),
            ("other", "Fictional Platform South"),
        ]:
            c.execute(
                text(
                    "INSERT INTO organizations(id,name,code,active,created_at,updated_at) VALUES (:id,:name,:code,true,now(),now())"
                ),
                {"id": f[key], "name": name, "code": key + "-" + f[key][:6]},
            )
        c.execute(
            text(
                "INSERT INTO users(id,username,password_hash,active,platform_admin,service_provider_id,created_at) VALUES (:id,'arch001-admin',:hash,true,true,(SELECT id FROM service_providers LIMIT 1),now())"
            ),
            {"id": f["admin"], "hash": hash_password(f["password"])},
        )
        for key, hostname, env in [
            ("vm", "native-host.example.test", "PROD"),
            ("unknown_vm", "legacy-host.example.test", "LEGACY"),
        ]:
            c.execute(
                text(
                    "INSERT INTO vms(id,organization_id,hostname,environment,os,monitoring_enabled,created_at) VALUES (:id,:org,:hostname,:env,'Linux',true,now())"
                ),
                {"id": f[key], "org": f["org"], "hostname": hostname, "env": env},
            )
        for key, org, name, type, endpoint in [
            (
                "source",
                "org",
                "native-host.example.test",
                "LINUX",
                "native-host.example.test",
            ),
            (
                "other_source",
                "other",
                "other-host.example.test",
                "LINUX",
                "other-host.example.test",
            ),
            (
                "api_source",
                "org",
                "Legacy API",
                "API",
                "https://api.example.test/status",
            ),
        ]:
            c.execute(
                text(
                    "INSERT INTO data_sources(id,organization_id,name,source_type,endpoint,enabled,status,connection_config,created_at,updated_at) VALUES (:id,:org,:name,:type,:endpoint,true,'STOPPED','{}',now(),now())"
                ),
                {
                    "id": f[key],
                    "org": f[org],
                    "name": name,
                    "type": type,
                    "endpoint": endpoint,
                },
            )
        c.execute(
            text(
                "INSERT INTO job_orders(id,organization_id,vm_id,name,environment,active,monitoring_enabled,created_at) VALUES (:id,:org,:vm,'Legacy ETL','PROD',true,true,now())"
            ),
            {"id": f["job"], "org": f["org"], "vm": f["vm"]},
        )
        c.execute(
            text(
                "INSERT INTO job_order_histories(id,job_order_id,provider_execution_id,execution_type,status,started_at,created_at) VALUES (:id,:job,'preserved-order','SCHEDULED','SUCCESS',now()-interval '1 hour',now())"
            ),
            {"id": f["history"], "job": f["job"]},
        )
        c.execute(
            text(
                "INSERT INTO job_step_executions(id,history_id,name,status) VALUES (:id,:h,'Legacy step','SUCCESS')"
            ),
            {"id": f["step"], "h": f["history"]},
        )
        f["before"] = {
            t: [
                list(map(str, row))
                for row in c.execute(
                    text("SELECT " + cols + " FROM " + t + " ORDER BY id")
                )
            ]
            for t, cols in [
                ("organizations", "id,name,code"),
                ("users", "id,password_hash,active"),
                ("vms", "id,organization_id,hostname,environment"),
                ("job_orders", "id,organization_id,vm_id,name"),
                ("job_order_histories", "id,job_order_id,provider_execution_id,status"),
                ("job_step_executions", "id,history_id,name,status"),
            ]
        }
    (PRIVATE / "fixture.json").write_text(json.dumps(f))
    (PRIVATE / "fixture.json").chmod(0o600)
    print(
        "Populated existing identities/history and one explicit legacy mapping exception seeded"
    )


def migration():
    f = json.loads((PRIVATE / "fixture.json").read_text())
    e = create_engine(settings.database_url)
    with e.connect() as c:
        actual = {
            t: [
                list(map(str, row))
                for row in c.execute(
                    text("SELECT " + cols + " FROM " + t + " ORDER BY id")
                )
            ]
            for t, cols in [
                ("organizations", "id,name,code"),
                ("users", "id,password_hash,active"),
                ("vms", "id,organization_id,hostname,environment"),
                ("job_orders", "id,organization_id,vm_id,name"),
                ("job_order_histories", "id,job_order_id,provider_execution_id,status"),
                ("job_step_executions", "id,history_id,name,status"),
            ]
        }
        assert actual == f["before"]
    with SessionLocal() as db:
        r = db.get(MonitoringResource, uuid.UUID(f["vm"]))
        assert r and str(r.data_source_id) == f["source"]
        assert db.get(
            MonitoringResource, uuid.UUID(f["job"])
        ).linked_vm_id == uuid.UUID(f["vm"])
        assert db.get(MonitoringResource, uuid.UUID(f["api_source"])).domain == "API"
        assert (
            db.scalar(
                select(ResourceMappingIssue).where(
                    ResourceMappingIssue.entity_id == uuid.UUID(f["unknown_vm"])
                )
            ).reason
            == "UNSUPPORTED_LEGACY_ENVIRONMENT"
        )
        try:
            with db.begin_nested():
                db.execute(
                    text(
                        "UPDATE monitoring_resources SET data_source_id=:s WHERE id=:r"
                    ),
                    {"s": f["other_source"], "r": f["vm"]},
                )
        except Exception as exc:
            assert "scope mismatch" in str(exc)
        else:
            raise AssertionError(
                "Cross-customer resource source constraint did not reject"
            )
        db.rollback()
    (OUT / "migration.json").write_text(
        json.dumps(
            {
                "status": "PASS",
                "identities_passwords_history_preserved": True,
                "legacy_exception_retained": True,
                "cross_customer_constraint": True,
            },
            indent=2,
        )
        + "\n"
    )
    print(
        "Populated ARCH-001 mapping preserves customer/VM/execution/step/password identities; invalid legacy environment staged; cross-tenant FK trigger PASS"
    )


from urllib.request import Request, urlopen
from urllib.error import HTTPError


def call(path, method="GET", body=None, token=None, expected=200):
    req = Request(
        os.environ["ARCH001_API_URL"] + path,
        method=method,
        headers={
            "Content-Type": "application/json",
            **({"Authorization": "Bearer " + token} if token else {}),
        },
        data=json.dumps(body).encode() if body is not None else None,
    )
    try:
        with urlopen(req, timeout=15) as response:
            status = response.status
            raw = response.read()
    except HTTPError as error:
        status = error.code
        raw = error.read()
    assert status == expected, (method, path, status, expected)
    return json.loads(raw) if raw else None


def api():
    f = json.loads((PRIVATE / "fixture.json").read_text())
    token = call(
        "/api/v1/auth/login",
        "POST",
        {"username": "arch001-admin", "password": f["password"]},
    )["access_token"]
    vm_body = {
        "name": "Windows operations host",
        "hostname": "windows-arch001.example.test",
        "address": "windows-arch001.example.test",
        "environment": "PROD",
        "os_type": "Windows",
        "organization_id": f["org"],
        "services": ["Scheduler Service"],
    }
    vm = call("/api/v1/unified/resources/vm", "POST", vm_body, token, 201)
    assert (
        vm["id"] == vm["vm_id"]
        and vm["primary_collector_id"]
        and vm["activation_status"] == "CONFIGURED"
    )
    call("/api/v1/unified/resources/vm", "POST", vm_body, token, 409)
    linux = call(
        "/api/v1/unified/resources/vm",
        "POST",
        {
            "name": "Linux onboarding",
            "hostname": "linux-arch001.example.test",
            "address": "linux-arch001.example.test",
            "environment": "QA",
            "os_type": "Linux",
            "new_customer": {
                "name": "Fictional Inline Customer",
                "code": "ARCH001INLINE",
            },
        },
        token,
        201,
    )
    assert linux["organization_id"] != f["org"]
    registry = call("/api/v1/attribute-registry", token=token)
    assert {
        "VM",
        "ETL",
        "API",
        "PARAM_ETL",
        "HOST_METRICS",
        "PLATFORM_AIRFLOW",
    } <= registry["definitions"].keys()
    draft = call(
        "/api/v1/resource-drafts",
        "POST",
        {
            "domain": "VM",
            "name": "Controlled saved draft",
            "organization_id": f["org"],
            "stage": 2,
            "configuration": {
                "name": "Draft",
                "hostname": "",
                "organization_id": f["org"],
                "environment": "QA",
                "os_type": "Linux",
            },
        },
        token,
        201,
    )
    assert call("/api/v1/resource-drafts/" + draft["id"], token=token)["stage"] == 2
    call(
        "/api/v1/resource-drafts/" + draft["id"],
        "PUT",
        {
            "domain": "VM",
            "name": "Controlled saved draft",
            "organization_id": f["org"],
            "stage": 3,
            "configuration": draft["configuration"],
            "expected_revision": draft["revision"],
        },
        token,
    )
    call(
        "/api/v1/resource-drafts/" + draft["id"],
        "PUT",
        {
            "domain": "VM",
            "name": "Stale draft",
            "organization_id": f["org"],
            "stage": 3,
            "configuration": draft["configuration"],
            "expected_revision": draft["revision"],
        },
        token,
        409,
    )

    call(
        "/api/v1/unified/parameters/" + linux["id"] + "/preview",
        "POST",
        {
            "expected_resource_revision": linux["revision"],
            "configuration": {
                "domain": "VM",
                "thresholds": [
                    {
                        "metric_name": "system.cpu.utilization",
                        "metric_definition_id": str(uuid.uuid4()),
                        "unit": "%",
                        "critical": 80,
                    }
                ],
            },
        },
        token,
        422,
    )

    etl = call(
        "/api/v1/unified/resources/etl",
        "POST",
        {
            "name": "Host workload",
            "platform": "PENTAHO",
            "vm_resource_id": vm["id"],
            "jobchain": "Warehouse load",
            "log_paths": ["C:\\Logs\\etl-a.log", "C:\\Logs\\etl-b.log"],
        },
        token,
        201,
    )
    assert (
        etl["organization_id"] == f["org"]
        and etl["environment"] == "PROD"
        and etl["inherited"]["collector_id"] == vm["primary_collector_id"]
    )
    methods = call(
        "/api/v1/agent-control/collectors/" + vm["primary_collector_id"], token=token
    )["methods"]
    assert len(methods) == 2 and methods[0]["id"] != methods[1]["id"]
    call(
        "/api/v1/unified/resources/etl",
        "POST",
        {
            "name": "Wrong scope",
            "platform": "PENTAHO",
            "vm_resource_id": vm["id"],
            "organization_id": f["other"],
            "jobchain": "Bad",
        },
        token,
        422,
    )
    cloud = call(
        "/api/v1/unified/resources/etl",
        "POST",
        {
            "name": "Cloud workload",
            "platform": "IICS",
            "connector_url": "https://metadata.example.test/records",
            "credential_ref": "env:CONTROLLED_PROVIDER_TOKEN",
            "organization_id": f["org"],
            "environment": "PROD",
            "jobchain": "Cloud task",
        },
        token,
        201,
    )
    assert cloud["linked_vm_id"] is None and cloud["job_order_id"]
    endpoint = call(
        "/api/v1/unified/resources/api",
        "POST",
        {
            "name": "Native endpoint",
            "organization_id": f["org"],
            "environment": "PROD",
            "dns": "api-arch001.example.test",
            "port": 8443,
            "path": "/health",
            "frequency_seconds": 15,
            "linked_vm_resource_id": vm["id"],
        },
        token,
        201,
    )
    assert endpoint["configuration"]["port"] == 8443
    preview = call(
        "/api/v1/unified/parameters/" + etl["id"] + "/preview",
        "POST",
        {
            "expected_resource_revision": 1,
            "configuration": {
                "domain": "ETL",
                "overrides": {"long_running_seconds": 90},
            },
        },
        token,
    )
    attributes = {a["name"]: a for a in preview["attributes"]}
    assert (
        attributes["customer_id"]["provenance"] == "INHERITED"
        and attributes["long_running_seconds"]["provenance"] == "OVERRIDDEN"
    )
    call(
        "/api/v1/unified/parameters/" + etl["id"] + "/preview",
        "POST",
        {
            "expected_resource_revision": 1,
            "configuration": {"overrides": {"customer_id": f["other"]}},
        },
        token,
        422,
    )
    call(
        "/api/v1/unified/parameters/" + etl["id"] + "/import",
        "POST",
        {
            "expected_resource_revision": 1,
            "format": "YAML",
            "content": "!!python/object/apply:os.system [echo forbidden]",
        },
        token,
        422,
    )
    imported = call(
        "/api/v1/unified/parameters/" + etl["id"] + "/import",
        "POST",
        {
            "expected_resource_revision": 1,
            "format": "YAML",
            "content": "domain: ETL\nno_run_grace_seconds: 60",
            "save": True,
        },
        token,
        201,
    )
    active = call(
        "/api/v1/unified/parameters/" + etl["id"] + "/activate",
        "POST",
        {"approve": True, "version": imported["version"]},
        token,
    )
    assert active["status"] == "ACTIVE"
    call(
        "/api/v1/unified/resources/" + etl["id"] + "/activate",
        "POST",
        {"approve": True},
        token,
        409,
    )
    evidence = call(
        "/api/v1/unified/resources/" + vm["id"] + "/verification", token=token
    )
    assert evidence["ready"] is False
    call(
        "/api/v1/unified/resources/" + vm["id"] + "/dependencies",
        "POST",
        {"depends_on_id": etl["id"]},
        token,
        409,
    )
    department = call(
        "/api/v1/access/departments", "POST", {"name": "ARCH001 operations"}, token, 201
    )
    employee = call(
        "/api/v1/access/employees",
        "POST",
        {
            "username": "arch001-reader",
            "full_name": "Controlled reader",
            "password": f["password"],
            "department_id": department["id"],
        },
        token,
        201,
    )
    role = next(
        r
        for r in call("/api/v1/access/roles", token=token)
        if r["name"] == "Read-Only Viewer"
    )
    call(
        "/api/v1/access/employees/" + employee["id"] + "/roles",
        "POST",
        {"role_id": role["id"], "effect": "ALLOW"},
        token,
        201,
    )
    call(
        "/api/v1/access/customer-grants",
        "POST",
        {
            "user_id": employee["id"],
            "organization_id": f["org"],
            "role_id": role["id"],
            "effect": "ALLOW",
        },
        token,
        201,
    )
    reader = call(
        "/api/v1/auth/login",
        "POST",
        {"username": "arch001-reader", "password": f["password"]},
    )["access_token"]
    assert call("/api/v1/unified/resources/" + vm["id"], token=reader)["id"] == vm["id"]
    call("/api/v1/unified/resources/" + linux["id"], token=reader, expected=404)
    call("/api/v1/unified/resources/vm", "POST", vm_body, reader, 403)
    call(
        "/api/v1/unified/parameters/" + etl["id"],
        "POST",
        {"expected_resource_revision": 1, "configuration": {}},
        reader,
        403,
    )
    call("/api/v1/access/employees", token=reader, expected=403)
    page = call("/api/v1/unified/resources?domain=VM&limit=1", token=token)
    assert len(page["items"]) == 1 and page["total"] >= 2 and page["has_more"]
    with SessionLocal() as db:
        assert db.get(JobOrder, uuid.UUID(cloud["job_order_id"])).vm_id is None
        try:
            with db.begin_nested():
                db.execute(
                    text(
                        "UPDATE resource_parameter_versions SET configuration='{}' WHERE id=:id"
                    ),
                    {"id": imported["id"]},
                )
        except Exception as error:
            assert "immutable" in str(error)
        else:
            raise AssertionError("Parameter document mutated")
    f.update(
        vm_resource=vm,
        linux_resource=linux,
        etl_resource=etl,
        cloud_resource=cloud,
        api_resource=endpoint,
        token=token,
    )
    active = call("/api/v1/unified/parameters/" + etl["id"], token=token)
    version = next(v["version"] for v in active["versions"] if v["status"] == "ACTIVE")
    call(
        "/api/v1/unified/resources/" + etl["id"] + "/alert-setup",
        "POST",
        {
            "enabled": True,
            "parameter_version": version,
            "severities": ["WARNING", "CRITICAL"],
            "in_app": True,
        },
        token,
    )
    (PRIVATE / "fixture.json").write_text(json.dumps(f))
    (OUT / "api.json").write_text(
        json.dumps(
            {
                "status": "PASS",
                "inline_customer": True,
                "windows_linux": True,
                "etl_inheritance": True,
                "saas_without_vm": True,
                "safe_import_and_immutable_versions": True,
                "backend_scope_negatives": True,
                "activation_requires_real_evidence": True,
            },
            indent=2,
        )
        + "\n"
    )
    print(
        "ARCH-001 VM/customer/ETL/API onboarding, inheritance, safe imports/versioning, telemetry-gated activation and scope negatives PASS"
    )


def engines():
    from datetime import datetime, timedelta, timezone
    from unittest.mock import patch
    from app.unified.reconstruction import ingest_logs
    from app.unified.engines import (
        evaluate_executions,
        evaluate_schedule,
        condition,
        correlate,
    )

    f = json.loads((PRIVATE / "fixture.json").read_text())
    now = datetime.now(timezone.utc)
    base = now - timedelta(hours=3)
    with SessionLocal() as db:
        r = db.get(MonitoringResource, uuid.UUID(f["etl_resource"]["id"]))
        r.created_at = base - timedelta(hours=1)
        p = db.scalar(
            select(ParameterVersion).where(
                ParameterVersion.resource_id == r.id,
                ParameterVersion.status == "ACTIVE",
            )
        )
        parent = db.get(MonitoringResource, uuid.UUID(f["vm_resource"]["id"]))
        logs = LogSource(
            organization_id=r.organization_id,
            data_source_id=parent.data_source_id,
            collector_id=parent.primary_collector_id,
            name="Controlled reconstruction fixture",
            source_type="FILE",
            resource_type="ETL",
        )
        db.add(logs)
        db.flush()
        path = r.configuration["log_paths"][0]

        def add(identity, event, offset, status="RUNNING", step=None, attempt=1):
            payload = {
                "execution_id": identity,
                "event": event,
                "status": status,
                "jobchain": r.configuration["jobchain"],
                "step": step,
                "attempt": attempt,
                "timestamp": (base + timedelta(seconds=offset)).isoformat(),
            }
            db.add(
                LogEvent(
                    organization_id=r.organization_id,
                    log_source_id=logs.id,
                    observed_at=base + timedelta(seconds=offset),
                    message=json.dumps(payload),
                    attributes={
                        "log.file.path": path,
                        "origin": "CONTROLLED_TEST_FIXTURE",
                    },
                )
            )
            db.flush()

        add("complete-1", "END", 10, "SUCCESS")
        ingest_logs(db, r, p)
        h = db.scalar(
            select(JobOrderHistory).where(
                JobOrderHistory.job_order_id == r.job_order_id,
                JobOrderHistory.provider_execution_id == "complete-1",
            )
        )
        assert h.status == ExecutionStatus.SUCCESS and h.started_at is None
        add("complete-1", "START", 0)
        add("complete-1", "STEP_START", 1, step="Load")
        add("complete-1", "STEP_FAILED", 3, "FAILED", step="Load")
        add("complete-1", "STEP_START", 4, step="Load", attempt=2)
        add("complete-1", "STEP_END", 8, "SUCCESS", step="Load", attempt=2)
        add("complete-1", "END", 10, "SUCCESS")
        add("parallel-2", "START", 2)
        ingest_logs(db, r, p)
        db.flush()
        assert h.started_at == base and h.ended_at == base + timedelta(seconds=10)
        assert (
            db.scalar(
                select(func.count())
                .select_from(JobOrderHistory)
                .where(JobOrderHistory.job_order_id == r.job_order_id)
            )
            == 2
        )
        steps = db.scalars(
            select(JobStepExecution)
            .where(JobStepExecution.history_id == h.id)
            .order_by(JobStepExecution.attempt)
        ).all()
        assert [(step.attempt, step.status) for step in steps] == [
            (1, "FAILED"),
            (2, "SUCCESS"),
        ]
        before = db.scalar(
            select(func.count())
            .select_from(NormalizedEvent)
            .where(NormalizedEvent.resource_id == r.id)
        )
        ingest_logs(db, r, p)
        assert (
            db.scalar(
                select(func.count())
                .select_from(NormalizedEvent)
                .where(NormalizedEvent.resource_id == r.id)
            )
            == before
        )
        # The source readiness substitution is explicitly a controlled engine
        # boundary fixture, never live telemetry or production health evidence.
        config = {
            **p.configuration,
            "long_running_seconds": 5,
            "no_response_seconds": 30,
            "schedule": {
                "frequency": "HOURLY",
                "time": "00:00",
                "timezone": "UTC",
                "weekdays": list(range(7)),
                "month_day": 1,
                "cron": None,
                "exceptions": [],
                "dst_policy": "FIRST",
                "catchup_hours": 24,
            },
            "no_run_grace_seconds": 5,
        }
        newer = ParameterVersion(
            organization_id=r.organization_id,
            resource_id=r.id,
            version=p.version + 1,
            configuration=config,
            sha256="0" * 64,
            status="VALIDATED",
        )
        db.add(newer)
        db.flush()
        with patch(
            "app.unified.engines.source_readiness",
            return_value={
                "ready": True,
                "checks": [],
                "origin": "CONTROLLED_ENGINE_FIXTURE",
            },
        ):
            evaluate_executions(db, r, newer, base + timedelta(seconds=120))
        running = db.scalar(
            select(JobOrderHistory).where(
                JobOrderHistory.job_order_id == r.job_order_id,
                JobOrderHistory.provider_execution_id == "parallel-2",
            )
        )
        assert (
            running.status == ExecutionStatus.RUNNING
            and running.monitoring_conditions["LONG_RUNNING"]
            and running.monitoring_conditions["NO_RESPONSE"]
        )
        long_condition = db.scalar(
            select(ResourceCondition).where(
                ResourceCondition.resource_id == r.id,
                ResourceCondition.condition_type == "LONG_RUNNING",
                ResourceCondition.active.is_(True),
            )
        )
        assert long_condition.alert_state_id
        add("parallel-2", "END", 150, "SUCCESS")
        ingest_logs(db, r, p)
        with patch(
            "app.unified.engines.source_readiness",
            return_value={"ready": True, "checks": []},
        ):
            evaluate_executions(db, r, newer, base + timedelta(seconds=151))
        assert running.status == ExecutionStatus.SUCCESS and not long_condition.active
        assert db.get(AlertState, long_condition.alert_state_id).status == "RESOLVED"
        r.schedule_watermark = now.replace(
            minute=0, second=0, microsecond=0
        ) - timedelta(hours=2)
        with patch(
            "app.unified.engines.source_readiness",
            return_value={
                "ready": False,
                "checks": [],
                "origin": "CONTROLLED_OUTAGE_FIXTURE",
            },
        ):
            evaluate_schedule(db, r, newer, now)
        windows = db.scalars(
            select(ExpectedExecutionWindow).where(
                ExpectedExecutionWindow.resource_id == r.id
            )
        ).all()
        assert windows and any(w.status == "UNKNOWN" for w in windows)
        count = len(windows)
        with patch(
            "app.unified.engines.source_readiness",
            return_value={
                "ready": True,
                "checks": [],
                "origin": "CONTROLLED_ENGINE_FIXTURE",
            },
        ):
            evaluate_schedule(db, r, newer, now)
        assert (
            db.scalar(
                select(func.count())
                .select_from(ExpectedExecutionWindow)
                .where(ExpectedExecutionWindow.resource_id == r.id)
            )
            == count
        )
        assert any(w.status == "NO_RUN" for w in windows)
        no_run = db.scalar(
            select(ResourceCondition).where(
                ResourceCondition.resource_id == r.id,
                ResourceCondition.condition_type == "NO_RUN",
                ResourceCondition.active.is_(True),
            )
        )
        assert no_run and no_run.alert_state_id
        first_alert = no_run.alert_state_id
        with patch(
            "app.unified.engines.source_readiness",
            return_value={"ready": True, "checks": []},
        ):
            evaluate_schedule(db, r, newer, now + timedelta(seconds=1))
        assert no_run.alert_state_id == first_alert
        parent_condition = condition(
            db,
            parent,
            "SERVICE:Scheduler",
            "SERVICE_DOWN",
            True,
            "CRITICAL",
            "Observed scheduler stopped",
            {"service_identity": "Scheduler", "origin": "CONTROLLED_TEST_FIXTURE"},
            now,
        )
        child_condition = condition(
            db,
            r,
            "DEPENDENCY_TEST",
            "DEPENDENCY_BLOCKED",
            True,
            "WARNING",
            "Observed dependency prevented start",
            {"origin": "CONTROLLED_TEST_FIXTURE"},
            now,
        )
        link = ResourceDependency(
            organization_id=r.organization_id,
            resource_id=r.id,
            depends_on_id=parent.id,
            relationship_type="REQUIRES_SERVICE",
            service_identity="Scheduler",
        )
        db.add(link)
        db.flush()
        correlate(db, r.organization_id, r.environment, now)
        group = db.scalar(
            select(EventCorrelationGroup).where(
                EventCorrelationGroup.group_key.like(
                    "dependency:" + str(link.id) + ":%"
                )
            )
        )
        assert group and group.confidence == "RELATIONSHIP_SUPPORTED"
        assert "not proven" in group.evidence["statement"]
        assert (
            db.scalar(
                select(func.count())
                .select_from(EventCorrelationMember)
                .where(EventCorrelationMember.group_id == group.id)
            )
            >= 2
        )
        # Recover all independently observed group members; changing only the
        # relation would not count as recovery evidence.
        for member in db.scalars(
            select(ResourceCondition)
            .join(
                EventCorrelationMember,
                EventCorrelationMember.condition_id == ResourceCondition.id,
            )
            .where(EventCorrelationMember.group_id == group.id)
        ):
            condition(
                db,
                db.get(MonitoringResource, member.resource_id),
                member.condition_key,
                member.condition_type,
                False,
                member.severity,
                "Controlled recovery observation",
                {"origin": "CONTROLLED_TEST_FIXTURE"},
                now + timedelta(seconds=2),
            )
        correlate(db, r.organization_id, r.environment, now + timedelta(seconds=2))
        assert group.status == "RESOLVED"
        db.commit()
    for domain in ("ETL", "VM", "API"):
        report = call("/api/v1/unified/reports/" + domain, token=f["token"])
        assert report["domain"] == domain and isinstance(report["history"], list)
    assert (
        call("/api/v1/unified/reports/ETL", token=f["token"])["summary"][
            "observed_executions"
        ]
        > 0
    )
    assert "domains" in call("/api/v1/unified/overview", token=f["token"])
    assert "items" in call("/api/v1/unified/domain-state/VM", token=f["token"])
    (OUT / "engines.json").write_text(
        json.dumps(
            {
                "status": "PASS",
                "origin": "CONTROLLED_EVENTS_AND_ACTUAL_POSTGRES",
                "terminal_before_start": True,
                "duplicate_idempotency": True,
                "parallel_runs_and_step_retries": True,
                "terminal_status_separate_from_conditions": True,
                "persisted_schedule_restart": True,
                "collector_outage_not_job_failure": True,
                "alert_dedup_recovery": True,
                "dependency_evidence_correlation": True,
                "not_genuine_provider_acceptance": True,
            },
            indent=2,
        )
        + "\n"
    )
    print(
        "Native reconstruction/retry/parallel/late events, durable schedule windows, outage uncertainty, alert dedup/recovery and relationship correlation PASS (controlled engine boundary fixtures)"
    )


def incidents():
    from scripts.native_incidents_acceptance_probe import run

    result = run(json.loads((PRIVATE / "fixture.json").read_text()), call)
    (OUT / "native-incidents.json").write_text(json.dumps(result, indent=2) + "\n")
    print("Native incident HTTP lifecycle / recovery / customer authorization PASS")
    from scripts.native_incidents_acceptance_probe import emit_metric
    from app.worker.notifications import dispatch_pending_notifications
    from app.security.models import User

    fixture = json.loads((PRIVATE / "fixture.json").read_text())
    reader = call(
        "/api/v1/auth/login",
        "POST",
        {"username": "arch001-reader", "password": fixture["password"]},
    )["access_token"]
    with SessionLocal() as db:
        employee = db.scalar(select(User).where(User.username == "arch001-reader"))
        recipient_id = str(employee.id)
    destination = call(
        "/api/v1/notification-delivery",
        "POST",
        {
            "organization_id": fixture["org"],
            "name": "Controlled directed in-app " + uuid.uuid4().hex,
            "channel": "IN_APP",
            "configuration": {"user_ids": [recipient_id]},
        },
        fixture["token"],
        201,
    )
    call(
        "/api/v1/notification-delivery",
        "POST",
        {
            "organization_id": fixture["other"],
            "name": "Denied recipient scope",
            "channel": "IN_APP",
            "configuration": {"user_ids": [recipient_id]},
        },
        fixture["token"],
        422,
    )
    call("/api/v1/notifications/preferences", "PUT", {"in_app": False}, reader)
    before = call("/api/v1/notifications", token=reader)["total"]
    disabled = emit_metric(
        fixture["org"], "Controlled preference-off", ["DEST:" + destination["id"]]
    )
    dispatch_pending_notifications()
    assert call("/api/v1/notifications", token=reader)["total"] == before
    call("/api/v1/notifications/preferences", "PUT", {"in_app": True}, reader)
    facts = emit_metric(
        fixture["org"],
        "Controlled directed notification",
        ["DEST:" + destination["id"]],
    )
    dispatch_pending_notifications()
    notes = call("/api/v1/notifications", token=reader)
    assert any(row["alert_state_id"] == facts["alert_id"] for row in notes["items"])
    assert not any(
        row["alert_state_id"] == facts["alert_id"]
        for row in call("/api/v1/notifications", token=fixture["token"])["items"]
    )
    with SessionLocal() as db:
        from app.telemetry.models import InAppNotification

        count = db.scalar(select(func.count()).select_from(InAppNotification))
    dispatch_pending_notifications()
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(InAppNotification)) == count
    (OUT / "notifications.json").write_text(
        json.dumps(
            {
                "status": "PASS",
                "origin": "CONTROLLED_ALERTS_ACTUAL_QUEUE_HTTP_POSTGRES",
                "recipient_isolation": True,
                "customer_authorization": True,
                "preferences": True,
                "delivery_idempotency": True,
            },
            indent=2,
        )
        + "\n"
    )
    print(
        "Actual queued user-targeted in-app delivery / preferences / customer scopes / idempotency PASS"
    )


if __name__ == "__main__":
    globals()[sys.argv[1]]()
