"""Controlled local HTTP/archive/performance acceptance; no vendor runtimes."""

import json
import os
import platform
import secrets
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from app.models import (
    Organization,
    JobOrder,
    JobOrderHistory,
    DataSource,
    Collector,
    IncidentActivity,
)
from app.unified.models import MonitoringResource, ExpectedExecutionWindow
from app.security.models import WorkerIdentity
from app.security.http import token_digest
from app.security.passwords import hash_password
from app.telemetry.models import ManagedAgent
from app.unified.pentaho_models import PentahoAlias
from scripts.acceptance_scope import probe_headers
from tests.test_pentaho_incident_r1 import PentahoIncidentTests

assert (
    os.getenv("OPSCONTROL_V16_ACCEPTANCE") == "1" and os.getenv("ENVIRONMENT") == "test"
)
base = os.environ["V16_API_URL"]
private, out = Path(os.environ["V16_PRIVATE_DIR"]), Path(os.environ["V16_EVIDENCE_DIR"])
fixture = json.loads((private / "api-fixture.json").read_text())
checks, measurements = [], []


def req(path, token=None, scope=None, method="GET", body=None, expected=200):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    if scope is not None:
        headers["X-OpsControl-Customers"] = scope
    try:
        with urlopen(
            Request(
                base + "/api/v1/" + path,
                headers=headers,
                method=method,
                data=json.dumps(body).encode() if body is not None else None,
            ),
            timeout=30,
        ) as r:
            status, data = r.status, json.load(r)
    except HTTPError as e:
        status, data = e.code, json.load(e)
    assert status in (expected if isinstance(expected, tuple) else (expected,)), (
        path,
        status,
        expected,
        data,
    )
    return data


def login(user, password):
    return req(
        "auth/login", method="POST", body={"username": user, "password": password}
    )["access_token"]


def measure(name, paths, token, scope, concurrency, count):
    def read(i):
        started = time.perf_counter()
        try:
            data = req(paths[i % len(paths)], token, scope)
            assert len(data["items"]) <= 50
            return (time.perf_counter() - started) * 1000, None
        except Exception as e:
            return (time.perf_counter() - started) * 1000, type(e).__name__

    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        values = list(pool.map(read, range(count)))
    elapsed = time.perf_counter() - start
    times = sorted(v[0] for v in values)
    failures = [e for _, e in values if e]
    measurements.append(
        {
            "name": name,
            "requests": count,
            "concurrency": concurrency,
            "duration_seconds": round(elapsed, 4),
            "throughput_rps": round(count / elapsed, 3),
            "p50_ms": round(times[int((count - 1) * 0.50)], 3),
            "p95_ms": round(times[int((count - 1) * 0.95)], 3),
            "p99_ms": round(times[int((count - 1) * 0.99)], 3),
            "failures": len(failures),
            "failure_types": failures,
        }
    )
    assert not failures, measurements[-1]


lab = PentahoIncidentTests()
lab.setUp()
try:
    now = datetime.now(timezone.utc)
    password = fixture["viewer_password"]
    lab.user.password_hash = hash_password(password)
    lab.resource.name = "Sprint 09 archive pipeline"
    lab.db.commit()
    lab.grant(lab.user, ["resources.view", "etl.view", "incidents.view"])
    original_org = lab.org
    orgs = [lab.org]
    for i in range(4):
        org = Organization(
            name="Sprint09 customer " + str(i),
            code="S09-" + uuid.uuid4().hex[:12],
            active=True,
        )
        lab.db.add(org)
        lab.db.commit()
        orgs.append(org)
        lab.org = org
        lab.grant(lab.user, ["resources.view", "etl.view", "incidents.view"])
    lab.org = original_org
    customers = [str(o.id) for o in orgs]
    organization, resource = str(lab.org.id), str(lab.resource.id)
    user_id = str(lab.user.id)
    jobs = [
        JobOrder(
            id=uuid.uuid4(),
            organization_id=orgs[i % 5].id,
            name="S09 inventory " + str(i),
            environment="TEST",
            monitoring_enabled=False,
        )
        for i in range(1200)
    ]
    lab.db.add_all(jobs)
    lab.db.flush()
    for i in range(1200):
        lab.db.add(
            MonitoringResource(
                organization_id=orgs[i % 5].id,
                domain="ETL",
                job_order_id=jobs[i].id,
                name="S09 inventory " + str(i),
                environment="TEST",
                configuration={"platform": "AIRFLOW"},
            )
        )
    _, history, failure = lab.failure("s09-failed")
    for _ in range(103):
        _, archived = lab.emit(lab.raw(invocation="archive-proof", outcome="SUCCESS"))
    attempt = lab.attempts(archived)[0]
    lab.db.add_all(
        [
            PentahoAlias(
                organization_id=lab.org.id,
                resource_id=lab.resource.id,
                history_id=archived.id,
                attempt_id=attempt.id,
                alias_key=uuid.uuid4().hex,
                kind="INVOCATION",
                native_identity={},
            )
            for _ in range(205)
        ]
    )
    for i in range(205):
        lab.db.add(
            JobOrderHistory(
                job_order_id=history.job_order_id,
                execution_type=history.execution_type,
                status=history.status,
                created_at=now - timedelta(minutes=i),
                source_evidence={"fixture": "CONTROLLED_PAGINATION_ONLY"},
            )
        )
    lab.db.add_all(
        [
            ExpectedExecutionWindow(
                organization_id=lab.org.id,
                resource_id=lab.resource.id,
                scheduled_at=now - timedelta(hours=i),
                deadline=now - timedelta(hours=i) + timedelta(seconds=60),
                status="INCOMPLETE" if i % 2 else "UNKNOWN",
                parameter_version=1,
            )
            for i in range(603)
        ]
    )
    lab.db.add_all(
        [
            IncidentActivity(
                organization_id=lab.org.id,
                incident_id=failure.incident_id,
                event_type="NOTE",
                actor="controlled-fixture",
                occurred_at=now - timedelta(seconds=i),
                text="Controlled pagination fixture",
            )
            for i in range(205)
        ]
    )
    lab.db.commit()
    token = login(lab.user.username, password)
    admin = login("v16-api-admin", fixture["password"])
    selected = ",".join(customers)
    prefix = "unified/resources/" + resource
    first = req("unified/resources?limit=50", token, selected)
    assert first["total"] == 1201
    second = req("unified/resources?limit=50&offset=50", token, selected)
    assert not {r["id"] for r in first["items"]} & {r["id"] for r in second["items"]}
    assert req("unified/resources?limit=50", token)["total"] == 0
    req(prefix + "/executions?limit=201", token, selected, expected=422)
    req(prefix + "/executions?offset=-1", token, selected, expected=422)
    req(prefix + "/executions?outcome=OVERRIDE", token, selected, expected=422)
    assert req(prefix + "/executions?outcome=FAILED", token, selected)["total"] == 206
    a = req(prefix + "/schedule-occurrences?limit=20&offset=500", token, selected)
    assert a["total"] == 603 and len(a["items"]) == 20
    assert (
        req(prefix + "/schedule-occurrences?status=NO_RUN", token, selected)["total"]
        == 0
    )
    req(prefix + "/schedule-occurrences?status=SUCCESS", token, selected, expected=422)
    checks.append(
        "Large inventory, stable scoped pages, validated bounds, server outcome and schedule filtering; no implicit scope or NO_RUN"
    )
    path = prefix + "/executions/" + str(archived.id) + "/attempts/" + str(attempt.id)
    revisions = req(path + "/revisions?limit=20&offset=100", token, selected)
    assert revisions["total"] > 100 and revisions["items"]
    aliases = req(path + "/aliases?limit=20&offset=200", token, selected)
    assert aliases["total"] > 200 and aliases["items"]
    req(path + "/unknown", token, selected, expected=422)
    req(
        path.replace(str(archived.id), str(history.id)) + "/aliases",
        token,
        selected,
        expected=404,
    )
    req(path + "/revisions", token, customers[1], expected=(403, 404))
    req(
        "data-pipelines/integrations/" + str(lab.integration.id) + "/records/unknown",
        token,
        selected,
        expected=422,
    )
    checks.append(
        "Retained aliases/revisions beyond preview caps; nested IDOR, foreign scope and collection validation"
    )
    incident = "native-incidents/" + str(failure.incident_id)
    assert req(incident + "/activities?offset=200", token, selected)["total"] >= 205
    exact = req(
        "native-incidents?resource_id=" + resource + "&history_id=" + str(history.id),
        token,
        selected,
    )
    assert exact["total"] == 1
    assert (
        req("native-incidents?resource_id=" + str(uuid.uuid4()), token, selected)[
            "total"
        ]
        == 0
    )
    req(incident + "/activities", token, customers[1], expected=(403, 404))
    checks.append(
        "Incident archive activity, exact failure association filtering and cross-customer isolation"
    )
    assert (
        probe_headers(base, token, "/api/v1/unified/resources")[
            "X-OpsControl-Customers"
        ]
        != "ALL"
    )
    assert set(
        probe_headers(base, token, "/api/v1/unified/resources")[
            "X-OpsControl-Customers"
        ].split(",")
    ) == set(customers)
    assert probe_headers(base, "invalid", "/api/v1/unified/resources") == {
        "X-OpsControl-Customers": ""
    }
    checks.append(
        "Owned client compatibility helper sends explicit current UUID snapshot and fails closed on invalid authority"
    )
    # Genuine separate agent credentials must reach the existing bound-source
    # check, while human and invalid tokens remain rejected by authenticate().
    ds = DataSource(
        organization_id=lab.org.id,
        name="S09 transport fixture",
        source_type="VM",
        enabled=True,
    )
    lab.db.add(ds)
    lab.db.flush()
    c = Collector(
        data_source_id=ds.id,
        name="S09 offline agent",
        collector_type="OTEL_AGENT",
        enabled=True,
    )
    secret = secrets.token_urlsafe(32)
    worker = WorkerIdentity(
        organization_id=lab.org.id,
        name=uuid.uuid4().hex,
        token_hash=token_digest(secret),
        expires_at=now + timedelta(hours=1),
    )
    lab.db.add_all([c, worker])
    lab.db.flush()
    lab.db.add(
        ManagedAgent(
            organization_id=lab.org.id,
            collector_id=c.id,
            worker_id=worker.id,
            hostname="controlled.invalid",
            version="fixture",
            runtime_version="fixture",
        )
    )
    lab.db.commit()
    req(
        "agent/pipeline-claim",
        secret,
        method="POST",
        body={"source_id": str(uuid.uuid4())},
        expected=404,
    )
    req(
        "agent/pipeline-claim",
        token,
        method="POST",
        body={"source_id": str(uuid.uuid4())},
        expected=401,
    )
    worker.enabled = False
    lab.db.commit()
    req(
        "agent/pipeline-claim",
        secret,
        method="POST",
        body={"source_id": str(uuid.uuid4())},
        expected=401,
    )
    checks.append(
        "Separate agent session reaches bound-source validation; human and revoked agent tokens denied; no source activated"
    )
    measure(
        "inventory_one_customer",
        ["unified/resources?limit=50&offset=50"],
        token,
        organization,
        1,
        20,
    )
    measure(
        "inventory_five_customers",
        ["unified/resources?limit=50&offset=50"],
        token,
        selected,
        4,
        40,
    )
    measure(
        "concurrent_execution_evidence_schedule",
        [
            prefix + "/executions?limit=20&offset=20",
            path + "/revisions?limit=20",
            prefix + "/schedule-occurrences?limit=20&offset=500",
        ],
        token,
        selected,
        8,
        60,
    )

    # Active read load overlaps the authoritative revocation. Requests begun
    # after the mutation returns must see current restrictions; older in-flight
    # reads can complete under the established per-request snapshot contract.
    def reading(_):
        start = time.perf_counter()
        body = req(
            prefix + "/executions?limit=20", token, selected, expected=(200, 403, 404)
        )
        return start, "items" in body

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(reading, i) for i in range(24)]
        policy = req(
            "access/boundaries",
            admin,
            method="POST",
            body={
                "user_id": user_id,
                "kind": "DENY",
                "specification": {
                    "permissions": ["etl.view"],
                    "customers": [organization],
                },
                "idempotency_key": uuid.uuid4().hex,
                "reason": "Controlled revocation under concurrent reads",
            },
            expected=201,
        )
        revoked = time.perf_counter()
        values = [f.result() for f in futures]
    assert not any(success for started, success in values if started > revoked)
    for _ in range(5):
        req(prefix + "/executions?limit=20", token, selected, expected=(403, 404))
    req(
        "access/boundaries/" + policy["id"],
        admin,
        method="PATCH",
        body={
            "user_id": user_id,
            "kind": "DENY",
            "active": False,
            "specification": policy["specification"],
            "expected_revision": policy["revision"],
            "idempotency_key": uuid.uuid4().hex,
            "reason": "Restore controlled fixture after revocation measurement",
        },
    )
    checks.append(
        "Revocation overlaps 24 active reads; five subsequent reads denied and no post-revocation-started read succeeds"
    )
    (private / "sprint09-fixture.json").write_text(
        json.dumps(
            {
                "username": lab.user.username,
                "password": password,
                "organization": organization,
                "resource": resource,
                "history": str(archived.id),
                "attempt": str(attempt.id),
                "incident": str(failure.incident_id),
            }
        )
    )
    (private / "sprint09-fixture.json").chmod(0o600)
    (out / "sprint09-performance.json").write_text(
        json.dumps(
            {
                "status": "PASS",
                "dataset": {
                    "authorized_customers": 5,
                    "resources": 1201,
                    "executions": 207,
                    "schedule_occurrences": 603,
                    "attempt_revisions": revisions["total"],
                    "attempt_aliases": aliases["total"],
                    "incident_activities": 205,
                },
                "measurements": measurements,
                "revocation": {
                    "concurrent_reads": 24,
                    "subsequent_denials": 5,
                    "post_revocation_started_successes": 0,
                },
                "environment": {
                    "python": platform.python_version(),
                    "os": platform.system(),
                    "cpu_visible": os.cpu_count(),
                    "api_workers": 1,
                    "database": "Owned local PostgreSQL container",
                    "tls": False,
                    "scope": "bounded local only",
                },
                "production_scale_certification": False,
                "genuine_runtime_acceptance": False,
            },
            indent=2,
        )
    )
    (out / "sprint09-http.json").write_text(
        json.dumps(
            {"status": "PASS", "checks": checks, "genuine_runtime_acceptance": False},
            indent=2,
        )
    )
    print(
        "Sprint 09 authenticated archive, compatibility and resilience PASS:",
        len(checks),
        "groups",
    )
finally:
    lab.doCleanups()
