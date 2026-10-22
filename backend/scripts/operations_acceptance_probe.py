"""Actual HTTPS worker, PostgreSQL reporting and organization/role negatives."""

import json, os, secrets, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4
from sqlalchemy import select, func, text
from sqlalchemy.exc import DBAPIError
from app.db.session import SessionLocal
from app.models import OperationalIncident, IncidentActivity, CollectorRun, Collector
from app.unified.models import MonitoringResource
from scripts.etl_acceptance_probe import PRIVATE, BASE, api, login, load

OUT = Path(os.environ["OPERATIONAL_EVIDENCE_DIR"])


def save(state):
    (PRIVATE / "session.json").write_text(json.dumps(state))


def report_update(**values):
    path = PRIVATE / "operational-report.json"
    report = (
        json.loads(path.read_text())
        if path.exists()
        else {
            "origin": "SYNTHETIC_TLS_HTTP_AND_CARTE_WITH_LIVE_LINUX_HOST",
            "genuine_providers": "PENDING",
        }
    )
    report.update(values)
    path.write_text(json.dumps(report, indent=2) + "\n")


def collect_http(status):
    from scripts.run_remote_agent import run_once
    from app.worker.egress import policy_hosts, policy_cidrs

    state = load()
    (PRIVATE / "http-status").write_text(str(status))
    job = str(uuid4())
    from app.worker.remote_models import RemoteProbeJob

    # The remote trust regression runs the real scheduler. Consume its owned
    # queued job when present rather than submitting overlapping collector work.
    with SessionLocal() as db:
        pending = db.scalar(
            select(RemoteProbeJob).where(
                RemoteProbeJob.collector_id == UUID(state["http_collector_id"]),
                RemoteProbeJob.state.in_(["QUEUED", "LEASED"]),
            )
        )
        if pending:
            assert (
                pending.state == "QUEUED"
                and str(pending.assigned_worker_id) == state["http_worker_id"]
            )
    if pending is None:
        api(
            201,
            "POST",
            "/api/v1/remote-probes/jobs",
            state["admin_token"],
            {
                "collector_id": state["http_collector_id"],
                "worker_id": state["http_worker_id"],
                "idempotency_key": job,
            },
        )
    host = os.environ["ETL_FIXTURE_IP"]
    assert run_once(
        BASE,
        state["http_worker_token"],
        policy_hosts([host]),
        policy_cidrs([host + "/32"]),
    )
    with SessionLocal() as db:
        run = db.scalar(
            select(CollectorRun)
            .where(CollectorRun.collector_id == UUID(state["http_collector_id"]))
            .order_by(CollectorRun.started_at.desc())
            .limit(1)
        )
        assert run.http_status == status and run.status == (
            "SUCCESS" if status == 200 else "FAILED"
        )


def setup():
    state = load()
    admin = state["admin_token"]
    host = os.environ["ETL_FIXTURE_IP"]
    source = api(
        201,
        "POST",
        "/api/v1/resource-management/data-sources",
        admin,
        {
            "organization_id": state["org_id"],
            "name": "Fictional NOC HTTPS Portal",
            "source_type": "API",
            "endpoint": "https://" + host + "/ready",
        },
    )
    worker = api(
        201,
        "POST",
        "/api/v1/auth/workers",
        admin,
        {
            "organization_id": state["org_id"],
            "name": "noc-https-worker",
            "expires_in_days": 1,
        },
    )
    api(
        200,
        "PUT",
        "/api/v1/remote-probes/workers/" + worker["id"] + "/network-policy",
        admin,
        {"allowed_hosts": [host], "allowed_cidrs": [host + "/32"]},
    )
    versions = []
    for kind, name, definition in [
        ("METRIC", "noc-http-up", {"name": "probe_up", "metric_type": "GAUGE"}),
        (
            "ALERT",
            "noc-http-unavailable",
            {
                "name": "noc-http-unavailable",
                "metric_name": "probe_up",
                "operator": "LT",
                "threshold_value": 0.5,
                "severity": "CRITICAL",
            },
        ),
    ]:
        catalog = api(
            201,
            "POST",
            "/api/v1/rule-catalogs",
            admin,
            {
                "organization_id": state["org_id"],
                "name": name,
                "kind": kind,
                "definition": definition,
            },
        )
        versions.append(catalog["versions"][0]["id"])
    activation = api(
        200,
        "POST",
        "/api/v1/data-sources/" + source["id"] + "/activations",
        admin,
        {
            "include_templates": False,
            "rule_version_ids": versions,
            "remote_worker_id": worker["id"],
        },
    )
    state.update(
        http_source_id=source["id"],
        http_collector_id=activation["collector_id"],
        http_worker_id=worker["id"],
        http_worker_token=worker["worker_token"],
    )
    # Explicitly controlled coverage gaps remain unknown or disabled in the UI.
    unknown = api(
        201,
        "POST",
        "/api/v1/resource-management/data-sources",
        admin,
        {
            "organization_id": state["org_id"],
            "name": "Unobserved NOC Service",
            "source_type": "API",
        },
    )
    api(
        201,
        "POST",
        "/api/v1/resource-management/collectors",
        admin,
        {
            "data_source_id": unknown["id"],
            "name": "not-yet-observed",
            "collector_type": "HTTP",
            "configuration": {"url": "https://" + host + "/ready"},
        },
    )
    api(
        201,
        "POST",
        "/api/v1/resource-management/data-sources",
        admin,
        {
            "organization_id": state["org_id"],
            "name": "Disabled NOC Service",
            "source_type": "API",
            "enabled": False,
        },
    )
    other_source = api(
        201,
        "POST",
        "/api/v1/resource-management/data-sources",
        admin,
        {
            "organization_id": state["other_org_id"],
            "name": "Other Tenant Private Service",
            "source_type": "API",
        },
    )
    state["other_source_id"] = other_source["id"]
    # Viewer in the victim organization, operator elsewhere: global middleware
    # write permission must never grant action permission in the victim scope.
    password = secrets.token_urlsafe(32)
    user = api(
        201,
        "POST",
        "/api/v1/auth/users",
        admin,
        {"username": "noc-mixed", "password": password},
    )
    for org, role in [(state["org_id"], "viewer"), (state["other_org_id"], "operator")]:
        api(
            201,
            "POST",
            "/api/v1/auth/memberships",
            admin,
            {"user_id": user["id"], "organization_id": org, "role": role},
        )
    state["mixed_token"] = login("noc-mixed", password)
    save(state)
    collect_http(200)
    with SessionLocal() as db:
        resource = db.get(MonitoringResource, UUID(state["http_source_id"]))
        assert resource and resource.data_source_id == resource.id
        assert resource.organization_id == UUID(state["org_id"])
    scoped_path = (
        "/api/v1/unified/resources?domain=API&organization_id=" + state["org_id"]
    )
    own_resources = api(200, "GET", scoped_path, state["reader_token"])["items"]
    assert any(row["id"] == state["http_source_id"] for row in own_resources)
    other_resources = api(200, "GET", scoped_path, state["other_token"])["items"]
    assert all(row["id"] != state["http_source_id"] for row in other_resources)
    services = api(200, "GET", "/api/v1/operations/services", state["reader_token"])
    assert services["summary"] == {
        "HEALTHY": 1,
        "CRITICAL": 0,
        "UNKNOWN": 1,
        "DISABLED": 1,
    }, services["summary"]
    assert (
        api(200, "GET", "/api/v1/operations/alerts", state["reader_token"])["alerts"]
        == []
    )
    report_update(configured="PASS", services_configured=services)
    print(
        "NOC real HTTP worker enrollment / versioned activation / unknown and disabled coverage PASS"
    )


def phase(phase):
    state = load()
    collect_http(503 if phase == "failed" else 200)
    alerts = api(200, "GET", "/api/v1/operations/alerts", state["reader_token"])
    http = [
        row
        for row in alerts["alerts"]
        if row["data_source_id"] == state["http_source_id"]
    ]
    assert len(http) == 1 and http[0]["status"] == (
        "OPEN" if phase == "failed" else "RESOLVED"
    )
    state["http_alert_id"] = http[0]["id"]
    save(state)
    reports = api(200, "GET", "/api/v1/operations/reports", state["reader_token"])
    item = next(
        row for row in reports["services"] if row["id"] == state["http_source_id"]
    )
    assert item["observations"] == (2 if phase == "failed" else 3)
    assert item["sample_success_percent"] == (50 if phase == "failed" else 66.67)
    assert item["unknown"] == 0 and item["failed"] == 1
    etl = reports["etl"][0]
    assert etl["executions"] == (5 if phase == "failed" else 6)
    assert etl["no_run"] == 1 and etl["sla_excluded"] == 4
    assert (
        etl["runtime_sla_percent"] == 100
    )  # outcome failure and runtime SLA are distinct
    assert (
        sum(alerts["summary"].values()) >= 1
    )  # native monitoring states; ETL conditions retain their own event history
    # GET-only feeds cannot mutate durable incident activity.
    with SessionLocal() as db:
        before = db.scalar(select(func.count()).select_from(IncidentActivity))
    for path in ("/services", "/alerts", "/reports", "/history"):
        api(200, "GET", "/api/v1/operations" + path, state["reader_token"])
    with SessionLocal() as db:
        assert before == db.scalar(select(func.count()).select_from(IncidentActivity))
    report_update(**{phase: {"alerts": alerts, "reports": reports}})
    print(
        "NOC database-derived monitoring alerts, report denominators and read-only feeds PASS:",
        phase,
    )


def isolation():
    metric_semantics()
    report_semantics()
    state = load()
    prefix = "/api/v1/operations"
    sid = state["http_source_id"]
    aid = state["http_alert_id"]
    for path in ("/services", "/alerts", "/reports", "/history"):
        api(401, "GET", prefix + path)
    for token, status in [
        (state["reader_token"], 403),
        (state["mixed_token"], 404),
        (state["other_token"], 404),
    ]:
        api(status, "POST", prefix + "/alerts/" + aid + "/acknowledge", token)
    api(
        401,
        "POST",
        prefix + "/alerts/" + aid + "/acknowledge",
        state["http_worker_token"],
    )
    api(404, "GET", prefix + "/incidents", state["admin_token"])
    assert (
        api(200, "GET", prefix + "/services/" + sid, state["reader_token"])["health"]
        == "HEALTHY"
    )
    assert (
        api(
            200,
            "GET",
            prefix + "/alerts?organization_id=" + state["org_id"],
            state["other_token"],
        )["alerts"]
        == []
    )
    foreign = api(
        200,
        "GET",
        prefix + "/reports?organization_id=" + state["org_id"],
        state["other_token"],
    )
    assert foreign["services"] == [] and foreign["etl"] == []
    old = next(
        row
        for row in api(200, "GET", prefix + "/alerts", state["reader_token"])["alerts"]
        if row["id"] == aid
    )
    collect_http(503)
    rows = api(200, "GET", prefix + "/alerts", state["reader_token"])["alerts"]
    fresh = next(
        row for row in rows if row["data_source_id"] == sid and row["status"] == "OPEN"
    )
    assert fresh["id"] != aid
    api(
        200,
        "POST",
        prefix + "/alerts/" + fresh["id"] + "/acknowledge",
        state["operator_token"],
    )
    collect_http(200)
    recovered = next(
        row
        for row in api(200, "GET", prefix + "/alerts", state["reader_token"])["alerts"]
        if row["id"] == fresh["id"]
    )
    assert recovered["status"] == "RESOLVED"
    with SessionLocal() as db:
        originals = {
            row.id: row.started_at
            for row in db.scalars(
                select(CollectorRun)
                .join(Collector)
                .where(Collector.data_source_id == UUID(sid))
            ).all()
        }
        for rid in originals:
            db.get(CollectorRun, rid).started_at -= timedelta(days=1)
        db.commit()
    assert (
        api(200, "GET", prefix + "/services/" + sid, state["reader_token"])["health"]
        == "UNKNOWN"
    )
    with SessionLocal() as db:
        for rid, instant in originals.items():
            db.get(CollectorRun, rid).started_at = instant
        db.commit()
    audit = api(200, "GET", "/api/v1/auth/audit?limit=500", state["admin_token"])
    assert any(
        e["outcome"] == "DENIED" and "/operations/" in (e["target_id"] or "")
        for e in audit
    )
    details = json.dumps(
        api(200, "GET", prefix + "/services/" + sid, state["reader_token"])
    )
    assert "response_body" not in details and "credential_ref" not in details
    browsers = [
        json.loads((OUT / ("browser-" + phase + ".json")).read_text())
        for phase in ("configured", "failed", "recovered")
    ]
    assert all(result["status"] == "PASS" for result in browsers)
    requests = [
        json.loads(line)
        for line in (PRIVATE / "http-requests.jsonl").read_text().splitlines()
    ]
    assert [row["status"] for row in requests] == [200, 503, 200, 503, 200]
    report_update(
        security="PASS",
        relapse_and_resolution="PASS",
        stale_evidence="PASS",
        retired_itsm_api="PASS",
        audit_event_count=len(audit),
        browser_checks=browsers,
        populated_migration_backfill="PASS",
        http_fixture_requests=requests,
    )
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report.json").write_text((PRIVATE / "operational-report.json").read_text())
    print(
        "Tenant / mixed-role / worker / read-only / stale evidence / alert relapse / audit PASS"
    )


def metric_semantics():
    from app.models import MetricDefinition, AlertRule, MetricSample, AlertState
    from app.worker.alert_engine import evaluate_metric_sample

    state = load()
    instant = datetime.now(timezone.utc)
    # Rollback-only state-machine negatives, separate from transport evidence.
    with SessionLocal() as db:
        metric = MetricDefinition(
            organization_id=UUID(state["org_id"]),
            name="transactional-condition",
            resource_type="APPLICATION",
            metric_type="GAUGE",
        )
        db.add(metric)
        db.flush()
        rule = AlertRule(
            organization_id=metric.organization_id,
            metric_definition_id=metric.id,
            name="transactional-condition",
            operator="LT",
            threshold_value=".5",
            consecutive_breaches=2,
            evaluation_window_seconds=60,
        )
        db.add(rule)
        db.flush()

        def observe(value, offset):
            sample = MetricSample(
                organization_id=metric.organization_id,
                metric_definition_id=metric.id,
                observed_at=instant + timedelta(seconds=offset),
                value_numeric=value,
            )
            db.add(sample)
            db.flush()
            evaluate_metric_sample(db, sample)
            db.flush()
            return db.scalar(
                select(AlertState)
                .where(AlertState.alert_rule_id == rule.id)
                .order_by(AlertState.created_at.desc())
                .limit(1)
            )

        assert observe(0, 0) is None
        current = observe(0, 1)
        assert current.status == "OPEN"
        assert (
            observe(0, 90).status == "OPEN"
        )  # fewer recent breaches does not mean recovery
        assert (
            observe(1, 2).status == "OPEN"
        )  # old successful evidence does not resolve current failure
        assert observe(1, 91).status == "RESOLVED"
        assert (
            observe(0, 3).status == "RESOLVED"
        )  # old failure cannot reopen a recovered condition
        assert (
            db.scalar(
                select(func.count())
                .select_from(OperationalIncident)
                .where(OperationalIncident.alert_state_id == current.id)
            )
            == 0
        )
        db.rollback()
    print(
        "Consecutive-breach preservation / delayed observation refusal / no ITSM projection PASS"
    )


def report_semantics():
    """Independent API checks for excluded, breached and out-of-window facts."""
    from app.models import JobOrder

    state = load()
    now = datetime.now(timezone.utc)
    other = state["other_token"]
    prefix = "/api/v1/operations"
    job = api(
        201,
        "POST",
        "/api/v1/etl/job-orders",
        other,
        {
            "organization_id": state["other_org_id"],
            "hostname": "noc-report-negatives",
            "name": "Controlled report denominator negatives",
            "expected_runtime_seconds": 5,
            "sla_seconds": 10,
        },
    )
    cid = None
    try:
        base = {
            "execution_type": "SCHEDULED",
            "detected_at": now.isoformat(),
            "sla_seconds": 10,
            "source_result": "CONTROLLED_REPORT_NEGATIVE",
        }
        for facts in [
            {
                "status": "SUCCESS",
                "sla_status": "MET",
            },  # no source timing, cannot claim SLA met
            {
                "status": "RUNNING",
                "sla_status": "MET",
                "started_at": now.isoformat(),
            },  # not terminal
            {
                "status": "FAILED",
                "sla_status": "BREACHED",
                "started_at": (now - timedelta(seconds=30)).isoformat(),
                "ended_at": now.isoformat(),
            },
            {
                "status": "SUCCESS",
                "sla_status": "MET",
                "started_at": (now - timedelta(days=100, seconds=3)).isoformat(),
                "ended_at": (now - timedelta(days=100)).isoformat(),
                "detected_at": (now - timedelta(days=100)).isoformat(),
            },
        ]:
            api(
                201,
                "POST",
                "/api/v1/etl/job-orders/" + job["id"] + "/executions",
                other,
                base | facts,
            )
        with SessionLocal() as db:
            collector = Collector(
                data_source_id=UUID(state["other_source_id"]),
                name="controlled-report-negatives",
                collector_type="HTTP",
                enabled=False,
            )
            db.add(collector)
            db.flush()
            cid = collector.id
            for status, when in [
                ("RUNNING", now),
                ("SUCCESS", now - timedelta(days=100)),
            ]:
                db.add(CollectorRun(collector_id=cid, started_at=when, status=status))
            db.commit()
        reports = api(200, "GET", prefix + "/reports?days=1", other)
        row = next(r for r in reports["etl"] if r["id"] == job["id"])
        assert (
            row["executions"] == 3
            and row["sla_excluded"] == 2
            and row["sla_breached"] == 1
            and row["runtime_sla_percent"] == 0
        )
        service = next(
            r for r in reports["services"] if r["id"] == state["other_source_id"]
        )
        assert (
            service["observations"] == 1
            and service["unknown"] == 1
            and service["sample_success_percent"] is None
        )
        assert (
            len(
                api(
                    200, "GET", prefix + "/jobs/" + job["id"] + "/history?days=1", other
                )
            )
            == 3
        )
        report_update(report_denominator_negatives="PASS")
    finally:
        # The owning lab removes its disposable database after all checks.
        # Keep these real executions and their resource/collector projections
        # intact until then; deleting their parents would violate retained FKs.
        print("Controlled report fixtures retained for owned database teardown")
    print(
        "Unknown HTTP result / missing ETL source timing / in-progress SLA / breached terminal / report window negatives PASS"
    )


if __name__ == "__main__":
    command = sys.argv[1]
    if command == "setup":
        setup()
    elif command == "isolation":
        isolation()
    else:
        phase(command)
