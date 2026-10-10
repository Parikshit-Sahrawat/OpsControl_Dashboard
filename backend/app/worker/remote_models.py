"""Durable leased monitoring jobs; no untrusted code or remote shell."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base

def now_utc(): return datetime.now(timezone.utc)

class RemoteProbeJob(Base):
    __tablename__="remote_probe_jobs"
    id:Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    organization_id:Mapped[uuid.UUID]=mapped_column(ForeignKey("organizations.id",ondelete="CASCADE"),nullable=False)
    collector_id:Mapped[uuid.UUID]=mapped_column(ForeignKey("collectors.id",ondelete="CASCADE"),nullable=False)
    assigned_worker_id:Mapped[uuid.UUID]=mapped_column(ForeignKey("worker_identities.id",ondelete="CASCADE"),nullable=False)
    planned_for:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)
    config_snapshot:Mapped[dict]=mapped_column(JSON,nullable=False)
    state:Mapped[str]=mapped_column(String(24),nullable=False,default="QUEUED")
    attempts:Mapped[int]=mapped_column(Integer,nullable=False,default=0)
    lease_nonce_hash:Mapped[str|None]=mapped_column(String(64))
    lease_expires_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    run_id:Mapped[uuid.UUID|None]=mapped_column(UUID(as_uuid=True))
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=now_utc)
    completed_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    __table_args__=(UniqueConstraint("collector_id","planned_for",name="uq_remote_collector_planned"),
                     CheckConstraint("attempts >= 0 AND attempts <= 3",name="ck_remote_job_attempts"),
                     Index("ix_remote_job_worker_state","assigned_worker_id","state","planned_for"))

class RemoteProbeEvidence(Base):
    __tablename__="remote_probe_evidence"
    id:Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    event_id:Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),nullable=False,unique=True)
    job_id:Mapped[uuid.UUID]=mapped_column(ForeignKey("remote_probe_jobs.id",ondelete="CASCADE"),nullable=False,unique=True)
    organization_id:Mapped[uuid.UUID]=mapped_column(ForeignKey("organizations.id",ondelete="CASCADE"),nullable=False)
    worker_id:Mapped[uuid.UUID]=mapped_column(ForeignKey("worker_identities.id"),nullable=False)
    observed_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)
    result:Mapped[dict]=mapped_column(JSON,nullable=False)
    payload_sha256:Mapped[str]=mapped_column(String(64),nullable=False)
    received_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=now_utc)
    __table_args__=(Index("ix_remote_evidence_org_observed","organization_id","observed_at"),)
