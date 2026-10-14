import uuid
from datetime import datetime
from sqlalchemy import (
    String,
    Integer,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


class NativeIncidentDetails(Base):
    __tablename__ = "native_incident_details"
    incident_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    escalation_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    recovery_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    monitoring_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    monitoring_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    evidence: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "incident_id"],
            ["operational_incidents.organization_id", "operational_incidents.id"],
            name="fk_native_details_incident_scope",
        ),
        CheckConstraint(
            "revision > 0 AND escalation_level >= 0 AND monitoring_seconds >= 60",
            name="ck_native_details_limits",
        ),
    )


class NativeIncidentAlert(Base):
    __tablename__ = "native_incident_alerts"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    alert_state_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    evidence: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "incident_id"],
            ["operational_incidents.organization_id", "operational_incidents.id"],
            name="fk_native_alert_incident_scope",
        ),
        ForeignKeyConstraint(
            ["organization_id", "alert_state_id"],
            ["alert_states.organization_id", "alert_states.id"],
            name="fk_native_alert_scope",
        ),
        UniqueConstraint(
            "incident_id", "alert_state_id", name="uq_native_incident_alert"
        ),
    )
