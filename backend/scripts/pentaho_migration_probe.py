"""Populated 0032→0033 preservation in the explicitly owned disposable lab."""

import hashlib
import json
import os
import sys
import uuid
from pathlib import Path
from sqlalchemy import text
import app.main  # noqa: F401
from app.db.session import SessionLocal
from app.models import Organization, JobOrder
from app.security.models import User
from app.security.passwords import hash_password
from app.security.permission_catalog import PROVIDER_ID
from app.data_pipelines.models import PipelineSource, PipelineEvidence, PipelineHold

assert (
    os.getenv("ENVIRONMENT") == "test" and os.getenv("OPSCONTROL_V16_ACCEPTANCE") == "1"
), "Owned disposable test database required"
path = Path(os.environ["V16_EVIDENCE_DIR"]) / "migration-preservation.json"
with SessionLocal() as db:
    if sys.argv[1] == "seed":
        org = Organization(
            name="Controlled migration " + uuid.uuid4().hex,
            code="R1-MIG-" + uuid.uuid4().hex[:12],
            active=True,
        )
        user = User(
            username="r1-migration-" + uuid.uuid4().hex,
            full_name="Controlled preserved employee",
            password_hash=hash_password(uuid.uuid4().hex),
            active=True,
            service_provider_id=PROVIDER_ID,
        )
        db.add_all([org, user])
        db.flush()
        job = JobOrder(
            organization_id=org.id,
            name="Controlled legacy execution " + uuid.uuid4().hex,
            environment="TEST",
            active=True,
            monitoring_enabled=False,
        )
        source = PipelineSource(
            organization_id=org.id,
            method_type="PLATFORM_API",
            canonical_key=uuid.uuid4().hex.ljust(64, "0"),
            identity={"physical_scope": "controlled-migration-source"},
            continuity_validated=False,
        )
        db.add_all([job, source])
        db.flush()
        evidence = PipelineEvidence(
            organization_id=org.id,
            source_id=source.id,
            generation=source.generation,
            external_key="controlled-held-evidence",
            payload={"origin": "CONTROLLED_FIXTURE", "preserve": True},
            outcome="QUARANTINED_IDENTITY",
            observed_at=__import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ),
        )
        hold = PipelineHold(
            organization_id=org.id,
            source_id=source.id,
            kind="LEGAL",
            reference="migration-preservation",
            actor_id=user.id,
        )
        db.add_all([evidence, hold])
        history_id = uuid.uuid4()
        db.execute(
            text(
                """INSERT INTO job_order_histories(id,job_order_id,provider_execution_id,execution_type,status,created_at,source_evidence)
          VALUES (:id,:job,'controlled-preserved-native','MANUAL','FAILED',now(),CAST(:evidence AS JSON))"""
            ),
            {
                "id": history_id,
                "job": job.id,
                "evidence": json.dumps(
                    {"origin": "CONTROLLED_FIXTURE", "preserve": True}
                ),
            },
        )
        db.commit()
        path.write_text(
            json.dumps(
                {
                    "organization_id": str(org.id),
                    "user_id": str(user.id),
                    "password_hash_sha256": hashlib.sha256(
                        user.password_hash.encode()
                    ).hexdigest(),
                    "job_id": str(job.id),
                    "history_id": str(history_id),
                    "source_id": str(source.id),
                    "evidence_id": str(evidence.id),
                    "hold_id": str(hold.id),
                    "before_status": "FAILED",
                },
                indent=2,
            )
        )
        print(
            "Seeded preserved customer/user/native history/raw evidence/legal hold at 0032"
        )
    elif sys.argv[1] == "verify":
        from app.models import JobOrderHistory

        before = json.loads(path.read_text())
        h = db.get(JobOrderHistory, uuid.UUID(before["history_id"]))
        user = db.get(User, uuid.UUID(before["user_id"]))
        assert (
            h.status.value == "FAILED"
            and h.provider_execution_id == "controlled-preserved-native"
        )
        assert (
            h.pentaho_resource_id is None
            and h.pentaho_customer_id is None
            and h.pentaho_lifecycle is None
        )
        assert (
            hashlib.sha256(user.password_hash.encode()).hexdigest()
            == before["password_hash_sha256"]
        )
        assert db.get(Organization, uuid.UUID(before["organization_id"]))
        assert db.get(JobOrder, uuid.UUID(before["job_id"]))
        assert (
            db.get(PipelineEvidence, uuid.UUID(before["evidence_id"])).payload[
                "preserve"
            ]
            is True
        )
        assert db.get(PipelineHold, uuid.UUID(before["hold_id"])).released_at is None
        before.update(
            status="PASS",
            unchanged_legacy_history=True,
            unchanged_user_hash=True,
            customer_preserved=True,
            raw_evidence_preserved=True,
            legal_hold_preserved=True,
        )
        path.write_text(json.dumps(before, indent=2))
        print(
            "Populated 0032→0033 customer/user/history/evidence/legal hold preservation PASS"
        )
    else:
        raise ValueError("seed or verify required")
