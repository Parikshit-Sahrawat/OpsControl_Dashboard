"""Owned 0034→0035 preservation of legacy alert inbox and schedule history."""

import os, sys, json, uuid
from pathlib import Path
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
import app.main
from app.db.session import SessionLocal
from app.models import (
    MetricDefinition,
    AlertRule,
    AlertState,
    AlertNotificationDelivery,
)
from app.unified.pentaho_execution import digest

assert (
    os.getenv("ENVIRONMENT") == "test" and os.getenv("OPSCONTROL_V16_ACCEPTANCE") == "1"
)
path = Path(os.environ["V16_EVIDENCE_DIR"]) / "history-migration-preservation.json"
prior = json.loads((path.parent / "migration-preservation.json").read_text())
resource = json.loads((path.parent / "review-migration-preservation.json").read_text())[
    "ids"
]["monitoring_resources"]


def snapshot(db, table, id, exclude=None):
    value = db.execute(
        text("SELECT row_to_json(t) FROM " + table + " t WHERE id=:id"),
        {"id": uuid.UUID(id)},
    ).scalar_one()
    if exclude:
        value.pop(exclude, None)
    return digest(value)


with SessionLocal() as db:
    if sys.argv[1] == "seed":
        org = uuid.UUID(prior["organization_id"])
        now = datetime.now(timezone.utc)
        metric = MetricDefinition(
            organization_id=org,
            name="Controlled preserved notification metric " + uuid.uuid4().hex,
            resource_type="CONTROLLED_FIXTURE",
            metric_type="GAUGE",
        )
        db.add(metric)
        db.flush()
        rule = AlertRule(
            organization_id=org,
            metric_definition_id=metric.id,
            name="Controlled preserved rule " + uuid.uuid4().hex,
            threshold_value="1",
            enabled=False,
        )
        db.add(rule)
        db.flush()
        state = AlertState(
            organization_id=org,
            alert_rule_id=rule.id,
            metric_definition_id=metric.id,
            status="RESOLVED",
            severity="WARNING",
            first_triggered_at=now,
            last_evaluated_at=now,
            resolved_at=now,
            last_value=0,
            message="CONTROLLED_PRESERVATION_FIXTURE",
        )
        db.add(state)
        db.flush()
        delivery = AlertNotificationDelivery(
            alert_state_id=state.id,
            channel="IN_APP",
            event_type="OPENED",
            status="SENT",
            external_reference="controlled-preservation-fixture",
        )
        db.add(delivery)
        db.flush()
        note_id = uuid.uuid4()
        window_id = uuid.uuid4()
        db.execute(
            text(
                "INSERT INTO in_app_notifications(id,organization_id,user_id,delivery_id,created_at) VALUES(:id,:org,:user,:delivery,:stamp)"
            ),
            {
                "id": note_id,
                "org": org,
                "user": uuid.UUID(prior["user_id"]),
                "delivery": delivery.id,
                "stamp": now,
            },
        )
        db.execute(
            text(
                "INSERT INTO expected_execution_windows(id,organization_id,resource_id,scheduled_at,deadline,status,parameter_version,evidence) VALUES(:id,:org,:resource,:stamp,:deadline,'EXPECTED',1,'{}')"
            ),
            {
                "id": window_id,
                "org": org,
                "resource": uuid.UUID(resource),
                "stamp": now,
                "deadline": now + timedelta(minutes=10),
            },
        )
        db.commit()
        ids = {
            "metric_definitions": str(metric.id),
            "alert_rules": str(rule.id),
            "alert_states": str(state.id),
            "alert_notification_deliveries": str(delivery.id),
            "in_app_notifications": str(note_id),
            "expected_execution_windows": str(window_id),
        }
        path.write_text(
            json.dumps(
                {
                    "ids": ids,
                    "before": {t: snapshot(db, t, id) for t, id in ids.items()},
                },
                indent=2,
            )
        )
        print("Populated 0034 legacy notification/inbox/schedule snapshot prepared")
    elif sys.argv[1] == "verify":
        before = json.loads(path.read_text())
        after = {
            t: snapshot(
                db,
                t,
                id,
                {
                    "in_app_notifications": "historical_notice_id",
                    "expected_execution_windows": "pentaho_authority",
                }.get(t),
            )
            for t, id in before["ids"].items()
        }
        assert before["before"] == after
        before.update(
            status="PASS",
            legacy_alert_inbox_preserved=True,
            legacy_schedule_occurrence_preserved=True,
        )
        path.write_text(json.dumps(before, indent=2))
        print(
            "Populated 0034→0035 legacy alerts/delivery/inbox/schedule preservation PASS"
        )
    else:
        raise ValueError("seed or verify required")
