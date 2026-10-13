"""Event parameters reuse AlertRule/AlertState and the leased delivery queue."""

import math, statistics, uuid
from datetime import timedelta
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field, model_validator
from sqlalchemy import select
from app.db.session import get_db
from app.models import (
    MetricDefinition,
    MetricSample,
    AlertRule,
    AlertState,
    AlertNotificationDelivery,
)
from app.security.access_control import require_permission
from app.security.audit import log_event
from app.telemetry.configuration import Strict, env_reference
from app.telemetry.models import NotificationDestination
from app.telemetry.api import item
from app.security.secret_refs import require_safe_config

router = APIRouter(tags=["Events and Notifications"])


class EventInput(Strict):
    organization_id: uuid.UUID
    metric_definition_id: uuid.UUID
    name: str = Field(min_length=1, max_length=200)
    enabled: bool = True
    description: str = Field(default="", max_length=1000)
    severity: Literal["INFO", "WARNING", "CRITICAL"] = "WARNING"
    operator: Literal["GT", "GTE", "LT", "LTE"] = "GT"
    threshold_percentage: float = Field(ge=0, le=100)
    unit: Literal["%"] = "%"
    minimum_event_count: int = Field(default=2, ge=2, le=10000)
    time_window_minutes: int = Field(default=5, ge=1, le=1440)
    threshold_mode: Literal["STATIC", "DYNAMIC", "COMBINED"] = "STATIC"
    baseline_minutes: int = Field(default=60, ge=10, le=10080)
    baseline_minimum_samples: int = Field(default=30, ge=10, le=10000)
    standard_deviations: float = Field(default=3, ge=0.1, le=10)
    maximum_sample_gap_seconds: int = Field(default=90, ge=5, le=3600)
    aggregation: Literal["all"] = "all"
    destinations: list[uuid.UUID] = Field(default_factory=list, max_length=50)
    escalation_after_minutes: int | None = Field(default=None, ge=1, le=1440)
    escalation_destinations: list[uuid.UUID] = Field(
        default_factory=list, max_length=50
    )
    classes: list[str] = Field(default_factory=list, max_length=20)
    types: list[str] = Field(default_factory=list, max_length=20)
    components: list[str] = Field(default_factory=list, max_length=20)


@router.get("/api/v1/event-parameters")
def event_list(organization_id: uuid.UUID, db=Depends(get_db)):
    require_permission("templates.view", organization_id)
    return [
        item(r)
        for r in db.scalars(
            select(AlertRule)
            .where(
                AlertRule.organization_id == organization_id,
                AlertRule.evaluation_config.is_not(None),
            )
            .order_by(AlertRule.name)
        ).all()
    ]


def write_event(db, payload, row=None):
    if row is not None and row.metric_definition_id != payload.metric_definition_id:
        raise HTTPException(
            409,
            "Parameter binding is immutable; create a new rule to preserve existing alert history",
        )
    p = require_permission("templates.manage", payload.organization_id)
    metric = db.get(MetricDefinition, payload.metric_definition_id)
    if metric is None or metric.organization_id != payload.organization_id:
        raise HTTPException(404, "Metric unavailable")
    if metric.unit != "%":
        raise HTTPException(422, "Percentage thresholds require a percentage metric")
    for id in payload.destinations + payload.escalation_destinations:
        destination = db.get(NotificationDestination, id)
        if (
            not destination
            or destination.organization_id != payload.organization_id
            or not destination.enabled
        ):
            raise HTTPException(404, "Notification destination unavailable")
    row = row or AlertRule(
        organization_id=payload.organization_id,
        metric_definition_id=metric.id,
        name=payload.name,
    )
    row.name = payload.name
    row.enabled = payload.enabled
    row.severity = payload.severity
    row.operator = payload.operator
    row.threshold_value = str(payload.threshold_percentage)
    row.evaluation_window_seconds = (
        payload.time_window_minutes * 60 + payload.maximum_sample_gap_seconds
    )
    row.consecutive_breaches = payload.minimum_event_count
    row.notification_channels = [
        "DEST:" + str(id) for id in dict.fromkeys(payload.destinations)
    ]
    row.evaluation_config = payload.model_dump(mode="json")
    db.add(row)
    db.flush()
    log_event(
        db,
        event_type="EVENT_RULE_SAVE",
        outcome="SUCCESS",
        actor_id=p.user_id,
        organization_id=payload.organization_id,
        target_type="alert_rule",
        target_id=row.id,
    )
    db.commit()
    return item(row)


@router.post("/api/v1/event-parameters", status_code=201)
def event_create(payload: EventInput, db=Depends(get_db)):
    return write_event(db, payload)


@router.put("/api/v1/event-parameters/{id}")
def event_edit(id: uuid.UUID, payload: EventInput, db=Depends(get_db)):
    row = db.get(AlertRule, id)
    if row is None or row.organization_id != payload.organization_id:
        raise HTTPException(404, "Rule unavailable")
    return write_event(db, payload, row)


@router.get("/api/v1/event-parameters/metrics")
def metrics(organization_id: uuid.UUID, db=Depends(get_db)):
    require_permission("templates.view", organization_id)
    return [
        item(r)
        for r in db.scalars(
            select(MetricDefinition).where(
                MetricDefinition.organization_id == organization_id
            )
        ).all()
    ]


@router.post("/api/v1/event-parameters/preview")
def event_preview(payload: EventInput, db=Depends(get_db)):
    require_permission("templates.view", payload.organization_id)
    metric = db.get(MetricDefinition, payload.metric_definition_id)
    if not metric or metric.organization_id != payload.organization_id:
        raise HTTPException(404, "Metric unavailable")
    samples = db.scalars(
        select(MetricSample)
        .where(MetricSample.metric_definition_id == metric.id)
        .order_by(MetricSample.observed_at.desc())
        .limit(200)
    ).all()
    return {
        "origin": "STORED_TELEMETRY",
        "live_evaluation": False,
        "samples": [
            {"observed_at": s.observed_at, "value": s.value_numeric, "unit": s.unit}
            for s in samples
        ],
    }


class DestinationInput(Strict):
    organization_id: uuid.UUID
    name: str = Field(min_length=1, max_length=160)
    channel: Literal["SMTP", "WEBHOOK", "IN_APP"]
    configuration: dict
    enabled: bool = True

    @model_validator(mode="after")
    def safe(self):
        require_safe_config(self.configuration)
        from app.telemetry.delivery import validate_destination

        validate_destination(self.channel, self.configuration)
        return self


@router.get("/api/v1/notification-delivery")
def destinations(organization_id: uuid.UUID, db=Depends(get_db)):
    require_permission("templates.view", organization_id)
    rows = db.scalars(
        select(NotificationDestination).where(
            NotificationDestination.organization_id == organization_id
        )
    ).all()
    deliveries = db.execute(
        select(AlertNotificationDelivery, AlertState)
        .join(AlertState, AlertState.id == AlertNotificationDelivery.alert_state_id)
        .where(
            AlertState.organization_id == organization_id,
            (
                AlertNotificationDelivery.channel.in_(["EMAIL", "IN_APP"])
                | AlertNotificationDelivery.channel.startswith("DEST:")
            ),
        )
        .order_by(AlertNotificationDelivery.created_at.desc())
        .limit(100)
    ).all()
    from app.telemetry.api import utc

    pending = [
        d for d, state in deliveries if d.status in ("PENDING", "PROCESSING", "FAILED")
    ]
    lag = max(((utc() - d.created_at).total_seconds() for d in pending), default=0)
    return {
        "queue_lag_seconds": lag,
        "provider_health": "NOT_PROBED; inspect actual delivery outcomes",
        "destinations": [item(r) for r in rows],
        "deliveries": [{**item(d), "severity": s.severity} for d, s in deliveries],
        "additional_providers": "UNCONFIGURED",
        "delivery_worker_required": True,
    }


@router.post("/api/v1/notification-delivery", status_code=201)
def destination_create(payload: DestinationInput, db=Depends(get_db)):
    p = require_permission("templates.manage", payload.organization_id)
    r = NotificationDestination(**payload.model_dump())
    db.add(r)
    db.flush()
    log_event(
        db,
        event_type="NOTIFICATION_DESTINATION_CREATE",
        outcome="SUCCESS",
        actor_id=p.user_id,
        organization_id=r.organization_id,
        target_type="notification_destination",
        target_id=r.id,
    )
    db.commit()
    return item(r)


@router.put("/api/v1/notification-delivery/{id}")
def destination_edit(id: uuid.UUID, payload: DestinationInput, db=Depends(get_db)):
    p = require_permission("templates.manage", payload.organization_id)
    r = db.get(NotificationDestination, id)
    if r is None or r.organization_id != payload.organization_id:
        raise HTTPException(404, "Destination unavailable")
    for k, v in payload.model_dump().items():
        setattr(r, k, v)
    log_event(
        db,
        event_type="NOTIFICATION_DESTINATION_UPDATE",
        outcome="SUCCESS",
        actor_id=p.user_id,
        organization_id=r.organization_id,
        target_type="notification_destination",
        target_id=r.id,
    )
    db.commit()
    return item(r)


def dynamic_threshold(db, rule, current):
    cfg = rule.evaluation_config
    static = float(rule.threshold_value)
    if not cfg or cfg["threshold_mode"] == "STATIC":
        return static
    end = current.observed_at - timedelta(minutes=cfg["time_window_minutes"])
    points = db.scalars(
        select(MetricSample.value_numeric)
        .where(
            MetricSample.metric_definition_id == rule.metric_definition_id,
            MetricSample.observed_at
            >= end - timedelta(minutes=cfg["baseline_minutes"]),
            MetricSample.observed_at < end,
        )
        .order_by(MetricSample.observed_at.desc())
        .limit(10000)
    ).all()
    if len(points) < cfg["baseline_minimum_samples"]:
        return None
    dynamic = statistics.mean(points) + (
        1 if rule.operator in ("GT", "GTE") else -1
    ) * cfg["standard_deviations"] * statistics.pstdev(points)
    if cfg["threshold_mode"] == "DYNAMIC":
        return dynamic
    return (
        max(static, dynamic) if rule.operator in ("GT", "GTE") else min(static, dynamic)
    )


def sustained(db, rule, current, threshold):
    from app.worker.alert_engine import _breaches

    cfg = rule.evaluation_config
    if not cfg:
        return True
    start = current.observed_at - timedelta(minutes=cfg["time_window_minutes"])
    points = db.scalars(
        select(MetricSample)
        .where(
            MetricSample.metric_definition_id == current.metric_definition_id,
            MetricSample.observed_at
            >= start - timedelta(seconds=cfg["maximum_sample_gap_seconds"]),
            MetricSample.observed_at <= current.observed_at,
        )
        .order_by(MetricSample.observed_at.desc())
        .limit(10001)
    ).all()
    if len(points) > 10000:
        return False
    run = []
    for point in points:
        if not _breaches(point.value_numeric, rule.operator, threshold):
            break
        run.append(point)
    if len(run) < cfg["minimum_event_count"] or run[-1].observed_at > start:
        return False
    return all(
        (a.observed_at - b.observed_at).total_seconds()
        <= cfg["maximum_sample_gap_seconds"]
        for a, b in zip(run, run[1:])
    )


@router.get("/api/v1/operations/alerts")
def alerts(
    organization_id: list[uuid.UUID] = Query(default=[]),
    limit: int = Query(100, ge=1, le=500),
    db=Depends(get_db),
):
    stmt = select(AlertState)
    if organization_id:
        stmt = stmt.where(AlertState.organization_id.in_(organization_id))
    records = db.scalars(
        stmt.order_by(AlertState.last_evaluated_at.desc()).limit(limit)
    ).all()
    definitions = {
        m.id: m
        for m in db.scalars(
            select(MetricDefinition).where(
                MetricDefinition.id.in_([r.metric_definition_id for r in records])
            )
        ).all()
    }
    return {
        "alerts": [
            {
                **item(r),
                "data_source_id": (
                    definitions[r.metric_definition_id].data_source_id
                    if r.metric_definition_id in definitions
                    else None
                ),
                "metric_name": (
                    definitions[r.metric_definition_id].name
                    if r.metric_definition_id in definitions
                    else None
                ),
            }
            for r in records
        ],
        "summary": {
            status: db.scalar(
                select(__import__("sqlalchemy").func.count()).select_from(
                    stmt.where(AlertState.status == status).subquery()
                )
            )
            for status in ("OPEN", "RESOLVED")
        },
    }


@router.post("/api/v1/operations/alerts/{id}/acknowledge")
def acknowledge(id: uuid.UUID, db=Depends(get_db)):
    row = db.scalar(select(AlertState).where(AlertState.id == id).with_for_update())
    if not row:
        raise HTTPException(404, "Alert unavailable")
    p = require_permission("alerts.acknowledge", row.organization_id)
    from app.telemetry.api import utc

    if row.acknowledged_at is None:
        row.acknowledged_at = utc()
        row.acknowledged_by = p.user_id
    log_event(
        db,
        event_type="ALERT_ACKNOWLEDGE",
        outcome="SUCCESS",
        actor_id=p.user_id,
        organization_id=row.organization_id,
        target_type="alert",
        target_id=row.id,
    )
    db.commit()
    return item(row)
