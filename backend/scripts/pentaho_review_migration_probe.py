"""Snapshot an owned populated 0033 attempt/alias/revision before 0034."""

import json
import os
import sys
import uuid
from pathlib import Path
from sqlalchemy import text
from app.db.session import SessionLocal
from app.unified.pentaho_execution import digest

assert (
    os.getenv("ENVIRONMENT") == "test" and os.getenv("OPSCONTROL_V16_ACCEPTANCE") == "1"
)
path = Path(os.environ["V16_EVIDENCE_DIR"]) / "review-migration-preservation.json"
prior = json.loads((path.parent / "migration-preservation.json").read_text())


def snapshots(db, ids):
    result = {}
    for table, id in ids.items():
        row = db.execute(
            text("SELECT row_to_json(t) FROM " + table + " t WHERE id=:id"),
            {"id": uuid.UUID(id)},
        ).scalar_one()
        result[table] = digest(row)
    return result


with SessionLocal() as db:
    if sys.argv[1] == "seed":
        ids = {
            k: str(uuid.uuid4())
            for k in (
                "monitoring_resources",
                "job_order_histories",
                "normalized_telemetry_events",
                "pentaho_execution_attempts",
                "pentaho_native_aliases",
                "pentaho_attempt_revisions",
            )
        }
        resource_id = db.scalar(
            text("SELECT id FROM monitoring_resources WHERE job_order_id=:job"),
            {"job": uuid.UUID(prior["job_id"])},
        )
        if resource_id:
            ids["monitoring_resources"] = str(resource_id)
        params = {
            "org": uuid.UUID(prior["organization_id"]),
            "job": uuid.UUID(prior["job_id"]),
            "raw": uuid.UUID(prior["evidence_id"]),
            **{k: uuid.UUID(v) for k, v in ids.items()},
        }
        statements = [
            "INSERT INTO monitoring_resources(id,organization_id,job_order_id,domain,name,environment,configuration,revision,active,activation_status,created_at,updated_at) VALUES(:monitoring_resources,:org,:job,'ETL','Controlled preserved R1','TEST','{}',1,false,'CONFIGURED',now(),now())",
            "INSERT INTO job_order_histories(id,job_order_id,provider_execution_id,execution_type,status,created_at,pentaho_customer_id,pentaho_resource_id,pentaho_lifecycle,pentaho_outcome,pentaho_identity_state,pentaho_completeness) VALUES(:job_order_histories,:job,'controlled-preserved-r1','MANUAL','SUCCESS',now(),:org,:monitoring_resources,'TERMINAL','SUCCESS','CONFIRMED','PARTIAL')",
            "INSERT INTO normalized_telemetry_events(id,organization_id,resource_id,external_key,source_kind,history_id,observed_at,received_at,payload,processing_status) VALUES(:normalized_telemetry_events,:org,:monitoring_resources,'controlled-preserved-r1-event','PENTAHO',:job_order_histories,now(),now(),'{\"pentaho_identity\":{\"origin\":\"CONTROLLED_FIXTURE\"}}','PROCESSED')",
            "INSERT INTO pentaho_execution_attempts(id,organization_id,resource_id,history_id,attempt_key,attempt_order,native_identity,outcome,completeness,retry_authority,revision,created_at) VALUES(:pentaho_execution_attempts,:org,:monitoring_resources,:job_order_histories,'controlled-preserved-alias',1,'{}','SUCCESS','PARTIAL','{}',1,now())",
            "INSERT INTO pentaho_native_aliases(id,organization_id,resource_id,history_id,attempt_id,alias_key,kind,native_identity,created_at) VALUES(:pentaho_native_aliases,:org,:monitoring_resources,:job_order_histories,:pentaho_execution_attempts,'controlled-preserved-alias','INVOCATION','{}',now())",
            "INSERT INTO pentaho_attempt_revisions(id,organization_id,resource_id,history_id,attempt_id,event_id,source_evidence_id,revision,observation_key,disposition,payload,created_at) VALUES(:pentaho_attempt_revisions,:org,:monitoring_resources,:job_order_histories,:pentaho_execution_attempts,:normalized_telemetry_events,:raw,1,'controlled-preserved-observation','ACCEPTED','{}',now())",
        ]
        for sql in statements[1:] if resource_id else statements:
            db.execute(text(sql), params)
        db.commit()
        path.write_text(
            json.dumps({"ids": ids, "before": snapshots(db, ids)}, indent=2)
        )
        print("Owned populated 0033 attempt/alias/revision snapshot prepared")
    elif sys.argv[1] == "verify":
        before = json.loads(path.read_text())
        # New nullable projection column is deliberately excluded from the
        # old row snapshot; all existing fields must remain byte-equivalent.
        after = snapshots(db, before["ids"])
        history = db.execute(
            text(
                "SELECT row_to_json(t)::jsonb - 'pentaho_review_state' FROM job_order_histories t WHERE id=:id"
            ),
            {"id": uuid.UUID(before["ids"]["job_order_histories"])},
        ).scalar_one()
        after["job_order_histories"] = digest(history)
        assert after == before["before"]
        before.update(
            status="PASS",
            populated_0033_preserved=True,
            immutable_alias_revision_preserved=True,
        )
        path.write_text(json.dumps(before, indent=2))
        print(
            "Populated 0033→0034 history/attempt/alias/evidence/revision preservation PASS"
        )
    else:
        raise ValueError("seed or verify required")
