"""Owned 0035→0036 preservation of native incidents, assignments and histories."""

import os, sys, json, uuid
from pathlib import Path
from sqlalchemy import text
import app.main  # noqa: F401
from app.db.session import SessionLocal
from app.unified.pentaho_execution import digest

assert (
    os.getenv("ENVIRONMENT") == "test" and os.getenv("OPSCONTROL_V16_ACCEPTANCE") == "1"
)
path = Path(os.environ["V16_EVIDENCE_DIR"]) / "incident-migration-preservation.json"
tables = (
    "operational_incidents",
    "native_incident_details",
    "incident_activities",
    "native_incident_alerts",
    "job_order_histories",
    "pentaho_native_aliases",
    "pentaho_attempt_revisions",
    "pipeline_holds",
    "pipeline_evidence",
    "pentaho_historical_notices",
    "permissions",
    "users",
)


def snapshot(db):
    return {
        table: digest(
            sorted(
                db.execute(
                    text("SELECT row_to_json(t)::text FROM " + table + " t")
                ).scalars()
            )
        )
        for table in tables
    }


with SessionLocal() as db:
    if sys.argv[1] == "seed":
        org = db.scalar(text("SELECT id FROM organizations LIMIT 1"))
        user = db.scalar(text("SELECT id FROM users LIMIT 1"))
        id = uuid.uuid4()
        db.execute(
            text(
                "INSERT INTO operational_incidents(id,organization_id,episode_key,source_kind,source_reference,title,severity,status,condition_status,opened_at) VALUES(:id,:org,:key,'PENTAHO','preserved','Controlled preserved native incident','ERROR','CLOSED','RECOVERED',now())"
            ),
            {"id": id, "org": org, "key": "preserved-" + str(id)},
        )
        db.execute(
            text(
                "INSERT INTO native_incident_details(incident_id,organization_id,assigned_user_id,revision,escalation_level,monitoring_seconds,evidence) VALUES(:id,:org,:user,7,2,300,'{}')"
            ),
            {"id": id, "org": org, "user": user},
        )
        db.execute(
            text(
                "INSERT INTO incident_activities(id,organization_id,incident_id,event_type,actor,occurred_at,text) VALUES(:activity,:org,:id,'NOTE','controlled-reviewer',now(),'preserve audit')"
            ),
            {"activity": uuid.uuid4(), "org": org, "id": id},
        )
        db.commit()
        path.write_text(
            json.dumps({"before": snapshot(db), "incident_id": str(id)}, indent=2)
        )
    else:
        saved = json.loads(path.read_text())
        assert (
            snapshot(db) == saved["before"]
        ), "Preexisting incident/evidence data changed during 0036 upgrade"
        saved.update(status="PASS", preserved_tables=list(tables))
        path.write_text(json.dumps(saved, indent=2))
