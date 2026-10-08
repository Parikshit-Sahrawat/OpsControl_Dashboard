from datetime import timedelta

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.models import (
    AlertState,
    Application,
    CorrelationEvidence,
    CorrelationRecord,
    JobOrderHistory,
    LogEvent,
    LogSource,
    MetricDefinition,
    MetricSample,
)


DEFAULT_WINDOW_BEFORE_SECONDS = 15 * 60
DEFAULT_WINDOW_AFTER_SECONDS = 15 * 60
MAX_METRIC_EVIDENCE = 100
MAX_LOG_EVIDENCE = 100
MAX_ALERT_EVIDENCE = 50


def _anchor(history: JobOrderHistory):
    return history.detected_at or history.ended_at or history.started_at


def _resource_ids(db: Session, vm_id):
    ids = [vm_id]
    app_ids = db.scalars(
        select(Application.id).where(Application.vm_id == vm_id)
    ).all()
    ids.extend(app_ids)
    return ids


def _confidence(alerts, logs):
    if alerts and any((a.severity or "").upper() == "CRITICAL" for a in alerts):
        return "HIGH"
    if logs and any((e.severity or "").upper() in {"ERROR", "CRITICAL"} for e in logs):
        return "HIGH"
    if alerts or logs:
        return "MEDIUM"
    return "NONE"


def _category(alerts, logs):
    if any((a.severity or "").upper() == "CRITICAL" for a in alerts):
        return "RESOURCE_ALERT"
    if any((e.severity or "").upper() in {"ERROR", "CRITICAL"} for e in logs):
        return "LOG_ERROR"
    if alerts:
        return "RESOURCE_ALERT"
    if logs:
        return "LOG_WARNING"
    return "NO_RELATED_EVIDENCE"


def _summary(category, confidence, alerts, logs, metrics):
    if not alerts and not logs and not metrics:
        return "No related monitoring evidence was found in the correlation window."
    parts = []
    if alerts:
        parts.append(f"{len(alerts)} alert state(s)")
    if logs:
        parts.append(f"{len(logs)} error/warning log event(s)")
    if metrics:
        parts.append(f"{len(metrics)} related metric sample(s)")
    evidence_text = ", ".join(parts)
    return (
        f"OpsControl found {evidence_text} in the execution correlation window. "
        f"Primary evidence category: {category}; confidence: {confidence}. "
        "This is correlation evidence, not a confirmed root cause."
    )


def correlate_execution(
    db: Session,
    history_id,
    window_before_seconds: int = DEFAULT_WINDOW_BEFORE_SECONDS,
    window_after_seconds: int = DEFAULT_WINDOW_AFTER_SECONDS,
):
    history = db.scalar(
        select(JobOrderHistory).where(JobOrderHistory.id == history_id)
    )
    if not history:
        return None

    job_order = history.job_order
    anchor = _anchor(history)
    if not job_order or not anchor:
        raise ValueError("Execution must have a Job Order and at least one execution timestamp")

    start = anchor - timedelta(seconds=window_before_seconds)
    end = anchor + timedelta(seconds=window_after_seconds)
    resource_ids = _resource_ids(db, job_order.vm_id)

    metrics = db.execute(
        select(MetricSample, MetricDefinition)
        .join(MetricDefinition, MetricDefinition.id == MetricSample.metric_definition_id)
        .where(
            MetricSample.organization_id == job_order.organization_id,
            MetricDefinition.resource_id.in_(resource_ids),
            MetricSample.observed_at >= start,
            MetricSample.observed_at <= end,
        )
        .order_by(MetricSample.observed_at.desc())
        .limit(MAX_METRIC_EVIDENCE)
    ).all()

    logs = db.scalars(
        select(LogEvent)
        .join(LogSource, LogSource.id == LogEvent.log_source_id)
        .where(
            LogEvent.organization_id == job_order.organization_id,
            LogSource.resource_id.in_(resource_ids),
            LogEvent.observed_at >= start,
            LogEvent.observed_at <= end,
            LogEvent.severity.in_([ "ERROR", "CRITICAL", "WARNING" ]),
        )
        .order_by(LogEvent.observed_at.desc())
        .limit(MAX_LOG_EVIDENCE)
    ).all()

    alerts = db.scalars(
        select(AlertState)
        .join(MetricDefinition, MetricDefinition.id == AlertState.metric_definition_id)
        .where(
            AlertState.organization_id == job_order.organization_id,
            MetricDefinition.resource_id.in_(resource_ids),
            or_(
                (AlertState.last_evaluated_at >= start) & (AlertState.last_evaluated_at <= end),
                ((AlertState.status == "OPEN") & (AlertState.first_triggered_at <= end)),
            ),
        )
        .order_by(AlertState.last_evaluated_at.desc())
        .limit(MAX_ALERT_EVIDENCE)
    ).all()

    record = db.scalar(
        select(CorrelationRecord).where(CorrelationRecord.history_id == history_id)
    )
    if record:
        record.window_start = start
        record.window_end = end
        record.anchor_at = anchor
        record.analysis_version += 1
        db.execute(delete(CorrelationEvidence).where(CorrelationEvidence.correlation_id == record.id))
    else:
        record = CorrelationRecord(
            organization_id=job_order.organization_id,
            history_id=history_id,
            anchor_at=anchor,
            window_start=start,
            window_end=end,
        )
        db.add(record)
        db.flush()

    evidence = []
    for sample, definition in metrics:
        evidence.append(CorrelationEvidence(
            correlation_id=record.id,
            evidence_type="METRIC_SAMPLE",
            source_id=sample.id,
            resource_type=definition.resource_type,
            resource_id=definition.resource_id,
            observed_at=sample.observed_at,
            severity=None,
            relationship="TEMPORAL_RESOURCE_MATCH",
            details={
                "metric_definition_id": str(definition.id),
                "metric_name": definition.name,
                "metric_type": definition.metric_type,
                "unit": sample.unit or definition.unit,
                "value": sample.value_numeric,
                "dimensions": sample.dimensions,
            },
        ))

    for event in logs:
        evidence.append(CorrelationEvidence(
            correlation_id=record.id,
            evidence_type="LOG_EVENT",
            source_id=event.id,
            resource_type=event.log_source.resource_type if event.log_source else None,
            resource_id=event.log_source.resource_id if event.log_source else None,
            observed_at=event.observed_at,
            severity=event.severity,
            relationship="TEMPORAL_RESOURCE_MATCH",
            details={
                "event_type": event.event_type,
                "message": event.message,
                "fingerprint": event.fingerprint,
                "attributes": event.attributes,
            },
        ))

    for alert in alerts:
        definition = db.get(MetricDefinition, alert.metric_definition_id)
        evidence.append(CorrelationEvidence(
            correlation_id=record.id,
            evidence_type="ALERT_STATE",
            source_id=alert.id,
            resource_type=definition.resource_type if definition else None,
            resource_id=definition.resource_id if definition else None,
            observed_at=alert.last_evaluated_at,
            severity=alert.severity,
            relationship="TEMPORAL_RESOURCE_MATCH",
            details={
                "alert_rule_id": str(alert.alert_rule_id),
                "metric_definition_id": str(alert.metric_definition_id),
                "status": alert.status,
                "message": alert.message,
                "last_value": alert.last_value,
                "breach_count": alert.breach_count,
            },
        ))

    confidence = _confidence(alerts, logs)
    category = _category(alerts, logs)
    record.primary_category = category
    record.confidence = confidence
    record.summary = _summary(category, confidence, alerts, logs, metrics)
    record.evidence_count = len(evidence)
    record.status = "ANALYZED"
    db.add_all(evidence)
    db.flush()
    return record
