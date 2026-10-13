"""Additive host-agent control plane; customer ownership remains organizations."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


def now():
    return datetime.now(timezone.utc)


class CollectorMethod(Base):
    __tablename__ = "collector_methods"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    collector_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("collectors.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    method_type: Mapped[str] = mapped_column(String(30), nullable=False)
    configuration: Mapped[dict] = mapped_column(JSONB, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    validation_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="SAVED"
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=now
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ManagedAgent(Base):
    __tablename__ = "managed_agents"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    collector_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("collectors.id"), nullable=False, unique=True
    )
    worker_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worker_identities.id"), nullable=False, unique=True
    )
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(80), nullable=False)
    runtime_version: Mapped[str] = mapped_column(String(80), nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    desired_revision: Mapped[int | None] = mapped_column(Integer)
    applied_revision: Mapped[int | None] = mapped_column(Integer)
    health: Mapped[str] = mapped_column(
        String(30), nullable=False, default="REGISTERED"
    )
    last_error: Mapped[str | None] = mapped_column(String(500))
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class AgentRegistration(Base):
    __tablename__ = "agent_registrations"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    collector_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("collectors.id"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CollectorConfigVersion(Base):
    __tablename__ = "collector_config_versions"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    collector_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("collectors.id"), nullable=False, index=True
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    yaml_text: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    runtime_version: Mapped[str] = mapped_column(String(80), nullable=False)
    validation_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="VALIDATED"
    )
    agent_configuration: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    method_snapshot: Mapped[list] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=now
    )
    __table_args__ = (
        UniqueConstraint(
            "collector_id", "revision", name="uq_collector_config_revision"
        ),
    )


class AgentDeployment(Base):
    __tablename__ = "agent_deployments"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("managed_agents.id"), nullable=False, index=True
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_revision: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="APPROVED")
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=now
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TelemetryReceipt(Base):
    __tablename__ = "telemetry_receipts"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("managed_agents.id"), nullable=False, index=True
    )
    signal: Mapped[str] = mapped_column(String(10), nullable=False)
    record_count: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=now
    )
    __table_args__ = (
        Index("ix_telemetry_agent_signal_time", "agent_id", "signal", "received_at"),
        UniqueConstraint(
            "agent_id", "signal", "payload_hash", name="uq_telemetry_batch"
        ),
    )


class TraceSpan(Base):
    __tablename__ = "trace_spans"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("managed_agents.id"), nullable=False, index=True
    )
    trace_id: Mapped[str] = mapped_column(String(32), nullable=False)
    span_id: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attributes: Mapped[dict] = mapped_column(JSONB, nullable=False)


class NotificationDestination(Base):
    __tablename__ = "notification_destinations"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    configuration: Mapped[dict] = mapped_column(JSONB, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=now
    )
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "name", name="uq_notification_destination_name"
        ),
    )
