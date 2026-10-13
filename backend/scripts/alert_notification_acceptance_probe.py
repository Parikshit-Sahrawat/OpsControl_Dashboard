"""Real populated-fixture alert/delivery acceptance, independent of ITSM."""

import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models import (
    Organization,
    MetricDefinition,
    MetricSample,
    AlertRule,
    AlertState,
    AlertNotificationDelivery,
)
from app.worker.alert_engine import evaluate_metric_sample
from app.worker.notifications import dispatch_pending_notifications, deliver


def main():
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        org = db.scalar(select(Organization).where(Organization.active.is_(True)))
        metric = MetricDefinition(
            organization_id=org.id,
            name="Independent notification fixture",
            resource_type="HOST",
            metric_type="GAUGE",
            unit="%",
        )
        db.add(metric)
        db.flush()
        rule = AlertRule(
            organization_id=org.id,
            metric_definition_id=metric.id,
            name="Controlled notification " + uuid.uuid4().hex[:8],
            operator="GT",
            threshold_value="80",
            consecutive_breaches=1,
            notification_channels=["IN_APP"],
        )
        db.add(rule)
        db.flush()
        for offset, value in [(0, 95), (1, 95), (2, 10)]:
            sample = MetricSample(
                organization_id=org.id,
                metric_definition_id=metric.id,
                value_numeric=value,
                observed_at=now + timedelta(seconds=offset),
                unit="%",
            )
            db.add(sample)
            db.flush()
            evaluate_metric_sample(db, sample)
        state = db.scalar(select(AlertState).where(AlertState.alert_rule_id == rule.id))
        assert state.status == "RESOLVED"
        state_id = state.id
        db.commit()
    # Fixture explicitly removes destination throttle so open/recovery can both
    # be tested without waiting; normal deployment keeps configured throttling.
    import os

    previous = os.environ.get("OPSCONTROL_NOTIFICATION_THROTTLE_SECONDS")
    os.environ["OPSCONTROL_NOTIFICATION_THROTTLE_SECONDS"] = "0"
    try:
        dispatch_pending_notifications()
    finally:
        if previous is None:
            os.environ.pop("OPSCONTROL_NOTIFICATION_THROTTLE_SECONDS", None)
        else:
            os.environ["OPSCONTROL_NOTIFICATION_THROTTLE_SECONDS"] = previous
    with SessionLocal() as db:
        deliveries = db.scalars(
            select(AlertNotificationDelivery).where(
                AlertNotificationDelivery.alert_state_id == state_id
            )
        ).all()
        assert len(deliveries) == 2 and all(row.status == "SENT" for row in deliveries)
    from types import SimpleNamespace

    try:
        deliver(SimpleNamespace(channel="SERVICENOW"), None)
    except RuntimeError:
        pass
    else:
        raise AssertionError("Retired ITSM adapter remained active")
    print(
        "Independent native alert OPEN/RESOLVED, idempotent in-app delivery and retired ITSM refusal PASS"
    )


if __name__ == "__main__":
    main()
