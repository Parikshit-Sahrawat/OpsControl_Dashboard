"""Organization-owned immutable rule definitions and idempotent activations."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base

def utc_now(): return datetime.now(timezone.utc)

class MonitoringRuleCatalog(Base):
    __tablename__="monitoring_rule_catalogs"
    id:Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    organization_id:Mapped[uuid.UUID]=mapped_column(ForeignKey("organizations.id",ondelete="CASCADE"),nullable=False,index=True)
    kind:Mapped[str]=mapped_column(String(12),nullable=False)
    name:Mapped[str]=mapped_column(String(160),nullable=False)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=utc_now)
    __table_args__=(UniqueConstraint("organization_id","kind","name",name="uq_monitoring_catalog_org_kind_name"),
                    CheckConstraint("kind IN ('METRIC','LOG','ALERT')",name="ck_monitoring_catalog_kind"))

class MonitoringRuleVersion(Base):
    __tablename__="monitoring_rule_versions"
    id:Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    catalog_id:Mapped[uuid.UUID]=mapped_column(ForeignKey("monitoring_rule_catalogs.id",ondelete="CASCADE"),nullable=False)
    version:Mapped[int]=mapped_column(Integer,nullable=False)
    definition:Mapped[dict]=mapped_column(JSON,nullable=False)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=utc_now)
    __table_args__=(UniqueConstraint("catalog_id","version",name="uq_monitoring_rule_version"),
                    CheckConstraint("version >= 1",name="ck_monitoring_rule_version_positive"))

class MonitoringActivation(Base):
    __tablename__="monitoring_activations"
    id:Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    organization_id:Mapped[uuid.UUID]=mapped_column(ForeignKey("organizations.id",ondelete="CASCADE"),nullable=False,index=True)
    data_source_id:Mapped[uuid.UUID]=mapped_column(ForeignKey("data_sources.id",ondelete="CASCADE"),nullable=False,unique=True)
    collector_id:Mapped[uuid.UUID|None]=mapped_column(ForeignKey("collectors.id",ondelete="SET NULL"))
    status:Mapped[str]=mapped_column(String(24),nullable=False)
    fingerprint:Mapped[str]=mapped_column(String(64),nullable=False)
    version:Mapped[int]=mapped_column(Integer,nullable=False)
    applied_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=utc_now)
    details:Mapped[dict]=mapped_column(JSON,nullable=False,default=dict)

class MonitoringRuleBinding(Base):
    __tablename__="monitoring_rule_bindings"
    id:Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    activation_id:Mapped[uuid.UUID]=mapped_column(ForeignKey("monitoring_activations.id",ondelete="CASCADE"),nullable=False,index=True)
    rule_version_id:Mapped[uuid.UUID]=mapped_column(ForeignKey("monitoring_rule_versions.id"),nullable=False)
    materialized_id:Mapped[uuid.UUID|None]=mapped_column(UUID(as_uuid=True))
    kind:Mapped[str]=mapped_column(String(12),nullable=False)
    __table_args__=(UniqueConstraint("activation_id","rule_version_id",name="uq_monitoring_activation_rule"),)
