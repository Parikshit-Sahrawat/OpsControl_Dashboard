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


if __name__ == "__main__":
    globals()[sys.argv[1]]()
