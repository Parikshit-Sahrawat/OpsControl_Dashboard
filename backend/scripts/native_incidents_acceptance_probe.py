"""Owned disposable PostgreSQL + actual HTTP acceptance for native incidents.

This creates explicitly labelled controlled samples; it never claims live
telemetry. The recovery-window clock boundary is backdated only in this owned
fixture, and reported separately from real-time/Agent acceptance.
"""

import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func
from app.core.config import settings
from app.db.session import SessionLocal
from app.models import (
    MetricDefinition,
    MetricSample,
    AlertRule,
    AlertState,
    OperationalIncident,
    IncidentActivity,
)
from app.native_incidents.models import NativeIncidentDetails, NativeIncidentAlert
from app.native_incidents.service import process_incidents
from app.worker.alert_engine import evaluate_metric_sample

PREFIX = "/api/v1/native-incidents"
ORIGIN = "CONTROLLED_INCIDENT_API_FIXTURE_NOT_LIVE_TELEMETRY"


def guarded():
    if (
        settings.environment != "test"
        or os.getenv("OPSCONTROL_ARCH001_ACCEPTANCE") != "1"
    ):
        raise RuntimeError(
            "Native incident fixtures require the explicitly owned ARCH001 test environment"
        )


def emit_metric(organization_id, label, channels=None):
    with SessionLocal() as db:
        metric = MetricDefinition(
            organization_id=uuid.UUID(organization_id),
            name="Controlled incident " + label,
            resource_type="CONTROLLED_ACCEPTANCE",
            metric_type="GAUGE",
            unit="%",
            query_config={"origin": ORIGIN},
        )
        db.add(metric)
        db.flush()
        rule = AlertRule(
            organization_id=metric.organization_id,
            metric_definition_id=metric.id,
            name="Controlled incident threshold " + label,
            severity="CRITICAL",
            operator="GT",
            threshold_value="80",
            evaluation_window_seconds=60,
            consecutive_breaches=1,
            enabled=True,
            notification_channels=channels if channels is not None else ["IN_APP"],
        )
        db.add(rule)
        db.flush()
        sample = MetricSample(
            organization_id=metric.organization_id,
            metric_definition_id=metric.id,
            value_numeric=95,
            unit="%",
            observed_at=datetime.now(timezone.utc) - timedelta(seconds=120),
            dimensions={
                "origin": ORIGIN,
                "clock_origin": "CONTROLLED_INITIAL_BREACH_120_SECONDS_AGO",
            },
        )
        db.add(sample)
        db.flush()
        alert = evaluate_metric_sample(db, sample)
        if not alert or alert.status != "OPEN":
            raise AssertionError("Controlled persisted breach did not open an alert")
        result = str(alert.id), str(metric.id), str(rule.id)
        db.commit()
    for _ in range(30):
        with SessionLocal() as db:
            process_incidents(db)
            db.commit()
            incident = db.scalar(
                select(OperationalIncident).where(
                    OperationalIncident.episode_key == "metric:" + result[0]
                )
            )
            if incident:
                return {
                    "alert_id": result[0],
                    "metric_id": result[1],
                    "rule_id": result[2],
                    "incident_id": str(incident.id),
                }
        time.sleep(0.1)
    raise AssertionError("Native worker hook did not create the controlled incident")


def controlled_recovery(facts, backdate_window=False):
    with SessionLocal() as db:
        sample = MetricSample(
            organization_id=db.get(
                AlertState, uuid.UUID(facts["alert_id"])
            ).organization_id,
            metric_definition_id=uuid.UUID(facts["metric_id"]),
            value_numeric=20,
            unit="%",
            observed_at=datetime.now(timezone.utc)
            - timedelta(seconds=0 if backdate_window else 62),
            dimensions={
                "origin": ORIGIN,
                "clock_origin": "CONTROLLED_RECOVERY_BASELINE",
            },
        )
        db.add(sample)
        db.flush()
        evaluate_metric_sample(db, sample)
        if backdate_window:
            detail = db.get(NativeIncidentDetails, uuid.UUID(facts["incident_id"]))
            detail.monitoring_started_at = datetime.now(timezone.utc) - timedelta(
                seconds=61
            )
            detail.evidence = {
                **(detail.evidence or {}),
                "clock_origin": "CONTROLLED_RECOVERY_WINDOW_BACKDATE_TEST_ONLY",
            }
        db.commit()
    # Settle the durable source transition before HTTP optimistic revisions are
    # fetched; a concurrent worker may own the advisory lease for this pass.
    for _ in range(30):
        with SessionLocal() as db:
            process_incidents(db)
            db.commit()
            incident = db.get(OperationalIncident, uuid.UUID(facts["incident_id"]))
            if incident.condition_status == "RECOVERED":
                return
        time.sleep(0.1)
    raise AssertionError("Controlled resolved alert did not update native source facts")


def run(fixture, call):
    guarded()
    admin = fixture["token"]
    suffix = uuid.uuid4().hex[:10]
    facts = emit_metric(fixture["org"], suffix)
    other = emit_metric(fixture["other"], suffix + "-other")
    endpoint = PREFIX + "/" + facts["incident_id"]
    incident = call(endpoint, token=admin)
    assert incident["status"] == "OPEN" and any(
        a["id"] == facts["alert_id"] for a in incident["alerts"]
    )
    snapshot = next(
        a["incident_evidence"]
        for a in incident["alerts"]
        if a["id"] == facts["alert_id"]
    )
    assert snapshot["initial_value"] == 95 and snapshot["rule_threshold"] == "80"
    assert (
        snapshot["initial_sample_id"]
        and snapshot["metric_definition_id"] == facts["metric_id"]
    )
    page = call(
        PREFIX + "?organization_id=" + fixture["org"] + "&status=OPEN&limit=1",
        token=admin,
    )
    assert page["total"] >= 1 and len(page["items"]) == 1 and page["limit"] == 1
    call(PREFIX, expected=401)
    reader = call(
        "/api/v1/auth/login",
        "POST",
        {"username": "arch001-reader", "password": fixture["password"]},
    )["access_token"]
    call(PREFIX, token=reader, expected=403)
    call(endpoint, token=reader, expected=403)
    call(endpoint + "/notes", "POST", {"text": "Unauthorized"}, reader, 403)
    department = call(
        "/api/v1/access/departments",
        "POST",
        {"name": "Controlled incident team " + suffix},
        admin,
        201,
    )
    role = call(
        "/api/v1/access/roles",
        "POST",
        {
            "name": "Controlled incident authority " + suffix,
            "permissions": [
                "incidents.view",
                "incidents.acknowledge",
                "incidents.manage",
            ],
        },
        admin,
        201,
    )
    users = []
    for organization, tail in ((fixture["org"], "north"), (fixture["other"], "south")):
        user = call(
            "/api/v1/access/employees",
            "POST",
            {
                "username": "incident-" + tail + "-" + suffix,
                "full_name": "Controlled incident employee",
                "password": fixture["password"],
                "department_id": department["id"],
            },
            admin,
            201,
        )
        call(
            "/api/v1/access/employees/" + user["id"] + "/roles",
            "POST",
            {"role_id": role["id"], "effect": "ALLOW"},
            admin,
            201,
        )
        call(
            "/api/v1/access/customer-grants",
            "POST",
            {
                "user_id": user["id"],
                "organization_id": organization,
                "role_id": role["id"],
                "effect": "ALLOW",
            },
            admin,
            201,
        )
        token = call(
            "/api/v1/auth/login",
            "POST",
            {
                "username": "incident-" + tail + "-" + suffix,
                "password": fixture["password"],
            },
        )["access_token"]
        users.append((user, token))
    operator, token = users[0]
    outsider, other_token = users[1]
    call(endpoint, token=other_token, expected=404)
    call(PREFIX + "/" + other["incident_id"], token=token, expected=404)
    call(endpoint + "/notes", "POST", {"text": "Cross-customer"}, other_token, 404)
    call(PREFIX + "?organization_id=" + fixture["other"], token=token, expected=403)
    authorized = call(PREFIX, token=token)
    assert all(
        item["organization_id"] == fixture["org"] for item in authorized["items"]
    )
    assert not any(item["id"] == other["incident_id"] for item in authorized["items"])
    incident = call(
        endpoint + "/notes",
        "POST",
        {
            "text": "Controlled investigation note; no live provider claim",
            "evidence_reference": "controlled://" + suffix,
        },
        token,
    )
    revision = incident["details"]["revision"]
    call(
        endpoint + "/assignment",
        "POST",
        {"assigned_user_id": outsider["id"], "revision": revision},
        token,
        422,
    )
    incident = call(
        endpoint + "/assignment",
        "POST",
        {"assigned_user_id": operator["id"], "revision": revision},
        token,
    )
    assert incident["details"]["assigned_user_id"] == operator["id"]
    incident = call(
        endpoint + "/escalate",
        "POST",
        {"revision": incident["details"]["revision"], "note": "Controlled escalation"},
        token,
    )
    assert incident["details"]["escalation_level"] == 1
    stale = incident["details"]["revision"] - 1
    call(
        endpoint + "/transition",
        "POST",
        {"status": "ACKNOWLEDGED", "revision": stale},
        token,
        409,
    )
    call(
        endpoint + "/transition",
        "POST",
        {"status": "RESOLVED", "revision": incident["details"]["revision"]},
        token,
        409,
    )
    for state in (
        "ACKNOWLEDGED",
        "INVESTIGATING",
        "RECOVERY_IN_PROGRESS",
        "MONITORING",
    ):
        incident = call(
            endpoint + "/transition",
            "POST",
            {
                "status": state,
                "revision": incident["details"]["revision"],
                "note": ORIGIN,
            },
            token,
        )
        assert incident["status"] == state
    call(
        endpoint + "/recovery-validation",
        "POST",
        {"revision": incident["details"]["revision"]},
        token,
        409,
    )
    controlled_recovery(facts)
    incident = call(endpoint, token=token)
    assert any(
        "observation window" in reason.lower()
        for reason in incident["recovery"]["reasons"]
    )
    rejected_recovery = call(
        endpoint + "/transition",
        "POST",
        {"status": "RESOLVED", "revision": incident["details"]["revision"]},
        token,
        409,
    )
    assert rejected_recovery["detail"]["message"] == "Recovery is not verified"
    # Test deterministic clock boundary explicitly; this is not elapsed-time UAT.
    controlled_recovery(facts, backdate_window=True)
    incident = call(endpoint, token=token)
    assert incident["recovery"]["ready"]
    proof = call(
        endpoint + "/recovery-validation",
        "POST",
        {"revision": incident["details"]["revision"]},
        token,
    )
    assert proof["ready"]
    incident = proof["incident"]
    for state in ("RESOLVED", "CLOSED", "OPEN"):
        incident = call(
            endpoint + "/transition",
            "POST",
            {
                "status": state,
                "revision": incident["details"]["revision"],
                "note": ORIGIN,
            },
            token,
        )
        assert incident["status"] == state
    assert (
        incident["resolved_at"] is None and incident["details"]["verified_at"] is None
    )
    call(
        endpoint + "/transition",
        "POST",
        {
            "status": "INVESTIGATING",
            "revision": incident["details"]["revision"],
            "organization_id": fixture["other"],
        },
        token,
        422,
    )
    detail = call(endpoint, token=token)
    final_snapshot = next(
        a["incident_evidence"] for a in detail["alerts"] if a["id"] == facts["alert_id"]
    )
    assert (
        final_snapshot == snapshot
    ), "Recovery must preserve original incident evidence"
    actions = {a["event_type"] for a in detail["activities"]}
    assert {
        "CREATED",
        "ALERT_LINKED",
        "NOTE",
        "ASSIGNED",
        "ESCALATED",
        "TRANSITION",
        "REOPENED",
        "RECOVERY_VERIFIED",
    } <= actions
    assert all(a["organization_id"] == fixture["org"] for a in detail["activities"])
    with SessionLocal() as db:
        before = db.scalar(
            select(func.count())
            .select_from(OperationalIncident)
            .where(OperationalIncident.episode_key == "metric:" + facts["alert_id"])
        )
        process_incidents(db)
        process_incidents(db)
        db.commit()
        after = db.scalar(
            select(func.count())
            .select_from(OperationalIncident)
            .where(OperationalIncident.episode_key == "metric:" + facts["alert_id"])
        )
        links = db.scalar(
            select(func.count())
            .select_from(NativeIncidentAlert)
            .where(
                NativeIncidentAlert.incident_id == uuid.UUID(facts["incident_id"]),
                NativeIncidentAlert.alert_state_id == uuid.UUID(facts["alert_id"]),
            )
        )
        assert before == after == 1 and links == 1
    return {
        "status": "PASS",
        "origin": ORIGIN,
        "real_http_api": True,
        "actual_postgresql": True,
        "default_deny_and_cross_customer": True,
        "assignment_notes_escalation": True,
        "full_lifecycle": True,
        "fresh_recovery_and_immediate_recovery_denied": True,
        "clock_boundary": "CONTROLLED_BACKDATE_NOT_REAL_TIME_WAIT",
        "episode_and_association_idempotency": True,
        "not_live_provider_acceptance": True,
    }
