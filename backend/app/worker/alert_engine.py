"""Metric Alert Rule evaluation.

This module evaluates persisted native metric samples and maintains OPEN/RESOLVED
alert state. It deliberately keeps alert state separate from collector evidence.
"""

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AlertNotificationDelivery, AlertRule, AlertState, MetricSample


SUPPORTED_OPERATORS = {"GT", "GTE", "LT", "LTE", "EQ", "NE"}


def _breaches(value: float, operator: str, threshold: float) -> bool:
    if operator == "GT":
        return value > threshold
    if operator == "GTE":
        return value >= threshold
    if operator == "LT":
        return value < threshold
    if operator == "LTE":
        return value <= threshold
    if operator == "EQ":
        return value == threshold
    if operator == "NE":
        return value != threshold
    return False


def _consecutive_breaches(db: Session, rule: AlertRule, current: MetricSample, threshold: float) -> int:
    window_start = current.observed_at - timedelta(seconds=rule.evaluation_window_seconds)
    samples = db.scalars(
        select(MetricSample)
        .where(
            MetricSample.metric_definition_id == rule.metric_definition_id,
            MetricSample.observed_at >= window_start,
            MetricSample.observed_at <= current.observed_at,
        )
        .order_by(MetricSample.observed_at.desc())
    ).all()

    count = 0
    for sample in samples:
        if _breaches(sample.value_numeric, rule.operator, threshold):
            count += 1
        else:
            break
    return count


def _message(rule: AlertRule, value: float) -> str:
    return (
        f"{rule.name}: metric value {value:g} {rule.operator} "
        f"threshold {rule.threshold_value}; severity={rule.severity}"
    )


def _queue_notifications(db: Session, state: AlertState, rule: AlertRule, event_type: str, message: str):
    channels = [str(channel).upper() for channel in (rule.notification_channels or [])]
    allowed = {"EMAIL", "PAGERDUTY", "SERVICENOW"}
    for channel in channels:
        if channel not in allowed:
            continue
        db.add(
            AlertNotificationDelivery(
                alert_state_id=state.id,
                channel=channel,
                event_type=event_type,
                status="PENDING",
                payload={
                    "alert_state_id": str(state.id),
                    "alert_rule_id": str(rule.id),
                    "metric_definition_id": str(rule.metric_definition_id),
                    "severity": rule.severity,
                    "message": message,
                    "value": state.last_value,
                },
            )
        )


def evaluate_metric_sample(db: Session, sample: MetricSample) -> AlertState | None:
    """Evaluate all enabled rules for the sample's metric.

    Returns the state changed/updated by the evaluation. No state is created
    for a non-breaching sample unless an existing OPEN alert must be resolved.
    """
    rules = db.scalars(
        select(AlertRule).where(
            AlertRule.metric_definition_id == sample.metric_definition_id,
            AlertRule.organization_id == sample.organization_id,
            AlertRule.enabled.is_(True),
        )
    ).all()

    changed_state = None
    for rule in rules:
        try:
            threshold = float(rule.threshold_value)
        except (TypeError, ValueError):
            continue
        if rule.operator not in SUPPORTED_OPERATORS:
            continue

        breach_count = _consecutive_breaches(db, rule, sample, threshold)
        breached = _breaches(sample.value_numeric, rule.operator, threshold)
        state = db.scalar(
            select(AlertState)
            .where(
                AlertState.alert_rule_id == rule.id,
                AlertState.status == "OPEN",
            )
            .order_by(AlertState.created_at.desc())
            .limit(1)
        )

        if breached and breach_count >= rule.consecutive_breaches:
            message = _message(rule, sample.value_numeric)
            if state is None:
                state = AlertState(
                    organization_id=rule.organization_id,
                    alert_rule_id=rule.id,
                    metric_definition_id=rule.metric_definition_id,
                    status="OPEN",
                    severity=rule.severity,
                    first_triggered_at=sample.observed_at,
                    last_evaluated_at=sample.observed_at,
                    last_value=sample.value_numeric,
                    breach_count=breach_count,
                    message=message,
                )
                db.add(state)
                db.flush()
                _queue_notifications(db, state, rule, "OPENED", message)
            else:
                state.last_evaluated_at = sample.observed_at
                state.last_value = sample.value_numeric
                state.breach_count = breach_count
                state.severity = rule.severity
                state.message = message
            changed_state = state
        elif state is not None:
            state.status = "RESOLVED"
            state.resolved_at = sample.observed_at
            state.last_evaluated_at = sample.observed_at
            state.last_value = sample.value_numeric
            state.breach_count = breach_count
            state.message = f"Resolved: {rule.name}; metric value recovered to {sample.value_numeric:g}"
            _queue_notifications(db, state, rule, "RESOLVED", state.message)
            changed_state = state

    return changed_state
