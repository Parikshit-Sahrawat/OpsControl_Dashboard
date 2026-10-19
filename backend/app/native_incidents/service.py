"""Durable native episodes. Recovery requires fresh persisted monitoring facts."""

from datetime import datetime, timezone, timedelta
import uuid
import math
from fastapi import HTTPException
from sqlalchemy import select, text, exists, cast, String, and_
from app.models import (
    OperationalIncident,
    IncidentActivity,
    AlertState,
    Organization,
    MetricSample,
    AlertRule,
)
from app.unified.models import (
    ResourceCondition,
    EventCorrelationGroup,
    EventCorrelationMember,
    MonitoringResource,
)
from app.native_incidents.models import (
    NativeIncidentDetails,
    NativeIncidentAlert,
    NativeIncidentFailure,
)
from app.security.audit import log_event

STATES = frozenset(
    {
        "OPEN",
        "ACKNOWLEDGED",
        "INVESTIGATING",
        "RECOVERY_IN_PROGRESS",
        "MONITORING",
        "RESOLVED",
        "CLOSED",
    }
)
TRANSITIONS = {
    "OPEN": {"ACKNOWLEDGED", "INVESTIGATING"},
    "ACKNOWLEDGED": {"INVESTIGATING", "RECOVERY_IN_PROGRESS"},
    "INVESTIGATING": {"RECOVERY_IN_PROGRESS"},
    "RECOVERY_IN_PROGRESS": {"MONITORING", "INVESTIGATING"},
    "MONITORING": {"RESOLVED", "INVESTIGATING"},
    "RESOLVED": {"CLOSED", "OPEN"},
    "CLOSED": {"OPEN"},
}


def utc():
    return datetime.now(timezone.utc)


def record(
    db,
    incident,
    event,
    actor="native-engine",
    note=None,
    previous=None,
    now=None,
    actor_id=None,
):
    db.add(
        IncidentActivity(
            organization_id=incident.organization_id,
            incident_id=incident.id,
            event_type=event,
            actor=actor,
            occurred_at=now or utc(),
            text=note,
            previous_status=previous,
            new_status=incident.status,
        )
    )
    log_event(
        db,
        event_type="native_incident." + event.lower(),
        outcome="SUCCESS",
        actor_id=actor_id,
        organization_id=incident.organization_id,
        target_type="incident",
        target_id=incident.id,
    )


def details(db, incident):
    row = next(
        (
            r
            for r in db.new
            if isinstance(r, NativeIncidentDetails) and r.incident_id == incident.id
        ),
        None,
    )
    if row is None:
        row = db.get(NativeIncidentDetails, incident.id)
    if row is None:
        row = NativeIncidentDetails(
            incident_id=incident.id,
            organization_id=incident.organization_id,
            revision=1,
            escalation_level=0,
            monitoring_seconds=60,
            evidence={},
        )
        db.add(row)
    return row


def linked_alerts(db, incident):
    ids = set(
        db.scalars(
            select(NativeIncidentAlert.alert_state_id).where(
                NativeIncidentAlert.incident_id == incident.id,
                NativeIncidentAlert.organization_id == incident.organization_id,
            )
        )
    )
    if incident.alert_state_id:
        ids.add(incident.alert_state_id)
    return (
        list(
            db.scalars(
                select(AlertState).where(
                    AlertState.organization_id == incident.organization_id,
                    AlertState.id.in_(ids),
                )
            )
        )
        if ids
        else []
    )


def evaluate_recovery(
    alerts,
    conditions,
    monitoring_started_at,
    monitoring_seconds,
    now,
    observations=None,
):
    observations = observations or {}
    reasons = []
    if not alerts:
        reasons.append("No linked alert evidence; recovery cannot be inferred")
    if not monitoring_started_at:
        reasons.append("Enter MONITORING to begin a recovery observation window")
    elif now < monitoring_started_at + timedelta(seconds=max(60, monitoring_seconds)):
        reasons.append("Recovery observation window is not complete")
    for alert in alerts:
        observation = observations.get(alert.id)
        matching = [
            c for c in conditions if getattr(c, "alert_state_id", None) == alert.id
        ]
        observed = max(
            [c.last_observed_at for c in matching],
            default=observation or alert.last_evaluated_at,
        )
        if alert.status != "RESOLVED" or not alert.resolved_at:
            reasons.append(f"Alert {alert.id} remains unresolved")
        if (
            not observed
            or observed < now - timedelta(seconds=120)
            or observed > now + timedelta(seconds=5)
        ):
            reasons.append(f"Alert {alert.id} lacks fresh monitoring evidence")
        if monitoring_started_at and (not observed or observed < monitoring_started_at):
            reasons.append(
                f"Alert {alert.id} has not been evaluated in this recovery window"
            )
    for condition in conditions:
        if condition.active or not condition.resolved_at:
            reasons.append(f"Condition {condition.id} remains active")
        if (
            not condition.evidence
            or condition.last_observed_at < now - timedelta(seconds=120)
            or condition.last_observed_at > now + timedelta(seconds=5)
            or (
                monitoring_started_at
                and condition.last_observed_at < monitoring_started_at
            )
        ):
            reasons.append(f"Condition {condition.id} lacks fresh supporting evidence")
    return {
        "ready": not reasons,
        "reasons": reasons,
        "evidence": {
            "alert_ids": [str(a.id) for a in alerts],
            "condition_ids": [str(c.id) for c in conditions],
            "checked_at": now.isoformat(),
            "monitoring_started_at": (
                monitoring_started_at.isoformat() if monitoring_started_at else None
            ),
        },
    }


def recovery(db, incident, now=None):
    from app.native_incidents.pentaho import recovery as pentaho_recovery

    if getattr(incident, "source_kind", None) == "PENTAHO" or (
        isinstance(incident, OperationalIncident)
        and db.scalar(
            select(NativeIncidentFailure.id)
            .where(NativeIncidentFailure.incident_id == incident.id)
            .limit(1)
        )
    ):
        return pentaho_recovery(db, incident, now or utc()) or {
            "ready": False,
            "reasons": ["Verified failure evidence unavailable"],
            "evidence": {},
        }
    d = details(db, incident)
    alerts = linked_alerts(db, incident)
    conditions = (
        list(
            db.scalars(
                select(ResourceCondition).where(
                    ResourceCondition.organization_id == incident.organization_id,
                    ResourceCondition.alert_state_id.in_([a.id for a in alerts]),
                )
            )
        )
        if alerts
        else []
    )
    observations = {}
    extra_reasons = []
    from app.worker.alert_engine import _breaches, SUPPORTED_OPERATORS

    from app.unified.models import MonitoringResource
    from app.unified.engines import source_readiness

    for resource_id in {c.resource_id for c in conditions}:
        resource = db.scalar(
            select(MonitoringResource).where(
                MonitoringResource.id == resource_id,
                MonitoringResource.organization_id == incident.organization_id,
            )
        )
        if not resource or not source_readiness(db, resource, now or utc())["ready"]:
            extra_reasons.append(
                f"Resource {resource_id} has no verified current collection evidence"
            )

    for alert in alerts:
        if d.monitoring_started_at:
            renewed = db.scalar(
                select(AlertState.id).where(
                    AlertState.organization_id == incident.organization_id,
                    AlertState.alert_rule_id == alert.alert_rule_id,
                    AlertState.id != alert.id,
                    AlertState.first_triggered_at >= d.monitoring_started_at,
                )
            )
            if renewed:
                extra_reasons.append(
                    f"Alert rule {alert.alert_rule_id} breached during the recovery window"
                )
            if not alert.resolved_at or alert.resolved_at > d.monitoring_started_at:
                extra_reasons.append(
                    f"Alert {alert.id} recovered after the recovery window began; restart monitoring"
                )
        active = db.scalar(
            select(AlertState.id).where(
                AlertState.organization_id == incident.organization_id,
                AlertState.alert_rule_id == alert.alert_rule_id,
                AlertState.status == "OPEN",
            )
        )
        if active:
            extra_reasons.append(
                f"Alert rule {alert.alert_rule_id} has an active breach"
            )
        if any(c.alert_state_id == alert.id for c in conditions):
            continue
        sample = db.scalar(
            select(MetricSample)
            .where(
                MetricSample.organization_id == incident.organization_id,
                MetricSample.metric_definition_id == alert.metric_definition_id,
            )
            .order_by(MetricSample.observed_at.desc())
            .limit(1)
        )
        rule = db.get(AlertRule, alert.alert_rule_id)
        if sample and rule:
            try:
                threshold = float(rule.threshold_value)
                if (
                    rule.operator not in SUPPORTED_OPERATORS
                    or not math.isfinite(threshold)
                    or not math.isfinite(sample.value_numeric)
                    or _breaches(sample.value_numeric, rule.operator, threshold)
                ):

                    extra_reasons.append(
                        f"Latest sample for alert {alert.id} has not recovered"
                    )
                else:
                    observations[alert.id] = sample.observed_at
                    if d.monitoring_started_at:
                        samples = list(
                            db.scalars(
                                select(MetricSample)
                                .where(
                                    MetricSample.organization_id
                                    == incident.organization_id,
                                    MetricSample.metric_definition_id
                                    == alert.metric_definition_id,
                                    MetricSample.observed_at >= d.monitoring_started_at,
                                    MetricSample.observed_at <= (now or utc()),
                                )
                                .order_by(MetricSample.observed_at)
                                .limit(1001)
                            )
                        )
                        if len(samples) > 1000:
                            extra_reasons.append(
                                f"Recovery window for alert {alert.id} exceeds the bounded evidence review"
                            )
                        elif any(
                            not math.isfinite(s.value_numeric)
                            or _breaches(s.value_numeric, rule.operator, threshold)
                            for s in samples
                        ):
                            extra_reasons.append(
                                f"Alert {alert.id} has an unhealthy sample during the recovery window"
                            )
            except (TypeError, ValueError):
                extra_reasons.append(f"Alert {alert.id} has an unsupported threshold")
    result = evaluate_recovery(
        alerts,
        conditions,
        d.monitoring_started_at,
        d.monitoring_seconds,
        now or utc(),
        observations,
    )
    result["reasons"].extend(extra_reasons)
    result["ready"] = not result["reasons"]
    return result


def transition(
    db, incident, target, revision, actor, actor_id=None, note=None, now=None
):
    from app.security.access_control import require_permission

    principal = require_permission(
        "incidents.acknowledge" if target == "ACKNOWLEDGED" else "incidents.manage",
        incident.organization_id,
    )
    actor = principal.username
    actor_id = principal.user_id
    now = now or utc()
    d = details(db, incident)
    if d.revision != revision:
        raise HTTPException(409, "Incident changed; refresh before saving")
    if target not in TRANSITIONS.get(incident.status, set()):
        raise HTTPException(409, "Invalid incident state transition")
    proof = None
    if target in {"RESOLVED", "CLOSED"}:
        proof = recovery(db, incident, now)
        if not proof["ready"]:
            raise HTTPException(409, {"message": "Recovery is not verified", **proof})
    previous = incident.status
    incident.status = target
    d.revision += 1
    if target == "RECOVERY_IN_PROGRESS":
        d.recovery_started_at = now
    if target == "MONITORING":
        d.monitoring_started_at = now
        d.verified_at = None
    if target == "RESOLVED":
        incident.resolved_at = now
        d.verified_at = now
        d.evidence = {**(d.evidence or {}), **proof["evidence"]}
    if target == "OPEN":
        incident.resolved_at = None
        d.monitoring_started_at = None
        d.verified_at = None
    record(
        db,
        incident,
        "REOPENED" if target == "OPEN" else "TRANSITION",
        actor,
        note,
        previous,
        now,
        actor_id,
    )
    return incident


def attach_alert(db, incident, alert, now):
    existing = db.scalar(
        select(NativeIncidentAlert).where(
            NativeIncidentAlert.incident_id == incident.id,
            NativeIncidentAlert.alert_state_id == alert.id,
        )
    )
    if not existing:
        rule = db.scalar(
            select(AlertRule).where(
                AlertRule.id == alert.alert_rule_id,
                AlertRule.organization_id == incident.organization_id,
            )
        )
        first_sample = db.scalar(
            select(MetricSample)
            .where(
                MetricSample.organization_id == incident.organization_id,
                MetricSample.metric_definition_id == alert.metric_definition_id,
                MetricSample.observed_at >= alert.first_triggered_at,
                MetricSample.observed_at <= alert.last_evaluated_at,
            )
            .order_by(MetricSample.observed_at, MetricSample.id)
            .limit(1)
        )
        initial_value = first_sample.value_numeric if first_sample else alert.last_value
        snapshot = {
            "alert_id": str(alert.id),
            "alert_rule_id": str(alert.alert_rule_id),
            "metric_definition_id": str(alert.metric_definition_id),
            "first_triggered_at": alert.first_triggered_at.isoformat(),
            "initial_sample_id": str(first_sample.id) if first_sample else None,
            "initial_value": initial_value if math.isfinite(initial_value) else None,
            "initial_unit": first_sample.unit if first_sample else None,
            "severity": alert.severity,
            "rule_operator": rule.operator if rule else None,
            "rule_threshold": rule.threshold_value if rule else None,
        }
        db.add(
            NativeIncidentAlert(
                organization_id=incident.organization_id,
                incident_id=incident.id,
                alert_state_id=alert.id,
                added_at=now,
                evidence=snapshot,
            )
        )
        details(db, incident).revision += 1
        record(db, incident, "ALERT_LINKED", now=now)


def process_incidents(db, now=None, limit=100):
    """Caller owns transaction. Advisory lock + stable keys prevent replica duplicates.

    Never closes or resolves incidents. Recovery and lifecycle remain explicit.
    """
    now = now or utc()
    if not db.scalar(text("SELECT pg_try_advisory_xact_lock(8415030)")):
        return {"processed": 0, "locked": True}
    count = 0
    # Verified Pentaho failures are correlated per execution, never through the
    # generic shared-job alert or potential-common-cause heuristic.
    pentaho_failure_alerts = (
        select(ResourceCondition.alert_state_id)
        .join(
            MonitoringResource, MonitoringResource.id == ResourceCondition.resource_id
        )
        .where(
            MonitoringResource.configuration["platform"].astext == "PENTAHO",
            ResourceCondition.condition_type == "ETL_FAILURE",
            ResourceCondition.alert_state_id.is_not(None),
        )
    )
    alerts = list(
        db.scalars(
            select(AlertState)
            .join(Organization, Organization.id == AlertState.organization_id)
            .where(
                Organization.active.is_(True),
                AlertState.status == "OPEN",
                AlertState.id.notin_(pentaho_failure_alerts),
                ~exists(
                    select(NativeIncidentAlert.id).where(
                        NativeIncidentAlert.alert_state_id == AlertState.id
                    )
                ),
            )
            .order_by(AlertState.last_evaluated_at.desc(), AlertState.id)
            .limit(limit)
        )
    )
    for alert in alerts:
        key = "metric:" + str(alert.id)
        incident = db.scalar(
            select(OperationalIncident)
            .where(OperationalIncident.episode_key == key)
            .with_for_update()
        )
        if not incident:
            incident = OperationalIncident(
                id=uuid.uuid4(),
                organization_id=alert.organization_id,
                episode_key=key,
                source_kind="METRIC",
                source_reference=str(alert.id),
                alert_state_id=alert.id,
                title=alert.message[:300],
                severity=alert.severity,
                status="OPEN",
                condition_status="ACTIVE",
                opened_at=alert.first_triggered_at,
            )
            db.add(incident)
            db.flush()
            details(db, incident)
            record(db, incident, "CREATED", now=now)
        attach_alert(db, incident, alert, now)
        count += 1
    # Correlation is evidence-supported grouping, never a root-cause assertion.
    groups = list(
        db.scalars(
            select(EventCorrelationGroup)
            .join(
                Organization, Organization.id == EventCorrelationGroup.organization_id
            )
            .outerjoin(
                OperationalIncident,
                and_(
                    OperationalIncident.source_kind == "CORRELATION",
                    OperationalIncident.source_reference
                    == cast(EventCorrelationGroup.id, String),
                    OperationalIncident.organization_id
                    == EventCorrelationGroup.organization_id,
                ),
            )
            .outerjoin(
                NativeIncidentDetails,
                NativeIncidentDetails.incident_id == OperationalIncident.id,
            )
            .where(
                Organization.active.is_(True),
                EventCorrelationGroup.status == "OPEN",
                ~exists(
                    select(EventCorrelationMember.id)
                    .join(
                        ResourceCondition,
                        ResourceCondition.id == EventCorrelationMember.condition_id,
                    )
                    .where(
                        EventCorrelationMember.group_id == EventCorrelationGroup.id,
                        ResourceCondition.alert_state_id.in_(pentaho_failure_alerts),
                    )
                ),
            )
            .order_by(
                NativeIncidentDetails.last_checked_at.asc().nullsfirst(),
                EventCorrelationGroup.opened_at,
            )
            .limit(limit)
        )
    )
    for group in groups:
        grouped_alerts = list(
            db.scalars(
                select(AlertState)
                .join(
                    ResourceCondition, ResourceCondition.alert_state_id == AlertState.id
                )
                .join(
                    EventCorrelationMember,
                    MonitoringResource,
                    EventCorrelationMember.condition_id == ResourceCondition.id,
                )
                .where(
                    EventCorrelationMember.group_id == group.id,
                    AlertState.organization_id == group.organization_id,
                    ResourceCondition.organization_id == group.organization_id,
                    EventCorrelationMember.organization_id == group.organization_id,
                )
            ).unique()
        )
        if not grouped_alerts:
            continue
        key = "correlation:" + str(group.id)
        incident = db.scalar(
            select(OperationalIncident)
            .where(OperationalIncident.episode_key == key)
            .with_for_update()
        )
        if not incident:
            incident = OperationalIncident(
                id=uuid.uuid4(),
                organization_id=group.organization_id,
                episode_key=key,
                source_kind="CORRELATION",
                source_reference=str(group.id),
                title=group.title[:300],
                severity=max(
                    grouped_alerts,
                    key=lambda a: {
                        "CRITICAL": 4,
                        "ERROR": 3,
                        "WARNING": 2,
                        "INFO": 1,
                    }.get(a.severity.upper(), 0),
                ).severity,
                status="OPEN",
                condition_status="ACTIVE",
                opened_at=group.opened_at,
            )
            db.add(incident)
            db.flush()
            details(db, incident).evidence = {
                "correlation_group_id": str(group.id),
                "confidence": group.confidence,
                "causation": "Not proven; inspect linked evidence",
            }
            record(db, incident, "CREATED", now=now)
        d = details(db, incident)
        d.last_checked_at = now
        if (
            not db.scalar(
                select(NativeIncidentFailure.id)
                .where(NativeIncidentFailure.incident_id == incident.id)
                .limit(1)
            )
            and incident.status in {"RESOLVED", "CLOSED"}
            and any(a.status == "OPEN" for a in grouped_alerts)
        ):
            previous = incident.status
            incident.status = "OPEN"
            incident.resolved_at = None
            d.monitoring_started_at = None
            d.verified_at = None
            d.revision += 1
            record(db, incident, "REOPENED", previous=previous, now=now)
        for alert in grouped_alerts:
            attach_alert(db, incident, alert, now)
        count += 1
    db.flush()
    # Scan unresolved episodes fairly; source facts can recover without auto-resolution.
    for incident in db.scalars(
        select(OperationalIncident)
        .join(Organization, Organization.id == OperationalIncident.organization_id)
        .where(
            Organization.active.is_(True),
            OperationalIncident.status.notin_(["CLOSED", "RESOLVED"]),
        )
        .outerjoin(
            NativeIncidentDetails,
            NativeIncidentDetails.incident_id == OperationalIncident.id,
        )
        .order_by(
            NativeIncidentDetails.last_checked_at.asc().nullsfirst(),
            OperationalIncident.opened_at,
        )
        .limit(limit)
        .with_for_update(of=OperationalIncident, skip_locked=True)
    ):
        details(db, incident).last_checked_at = now
        if incident.source_kind == "PENTAHO" or db.scalar(
            select(NativeIncidentFailure.id)
            .where(NativeIncidentFailure.incident_id == incident.id)
            .limit(1)
        ):
            # Explicit assessments govern restoration; no alert-only reset.
            continue
        linked = linked_alerts(db, incident)
        recovered = bool(linked) and all(
            a.status == "RESOLVED" and a.resolved_at for a in linked
        )
        new_condition = "RECOVERED" if recovered else "ACTIVE"
        if new_condition != incident.condition_status:
            incident.condition_status = new_condition
            incident.recovered_at = (
                max(a.resolved_at for a in linked) if recovered else None
            )
            details(db, incident).revision += 1
            record(
                db,
                incident,
                "SOURCE_RECOVERED" if recovered else "SOURCE_ACTIVE",
                now=now,
            )
        if not recovered and incident.status == "MONITORING":
            previous = incident.status
            incident.status = "INVESTIGATING"
            d = details(db, incident)
            d.revision += 1
            d.monitoring_started_at = None
            record(db, incident, "RECOVERY_FAILED", previous=previous, now=now)
    return {"processed": count, "locked": False}
