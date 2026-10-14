from datetime import datetime, timezone
import uuid
from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    DateTime,
    Index,
    UniqueConstraint,
    ForeignKeyConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


def now():
    return datetime.now(timezone.utc)


class AttributeRegistryVersion(Base):
    __tablename__ = "attribute_registry_versions"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    definitions: Mapped[dict] = mapped_column(JSONB, nullable=False)
    capabilities: Mapped[dict] = mapped_column(JSONB, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=now
    )
    __table_args__ = (
        CheckConstraint("version > 0", name="ck_attribute_registry_version"),
    )


class ResourceDraft(Base):
    __tablename__ = "resource_drafts"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    service_provider_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("service_providers.id"), nullable=False
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id")
    )
    domain: Mapped[str] = mapped_column(String(8), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    stage: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    configuration: Mapped[dict] = mapped_column(JSONB, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=now, onupdate=now
    )
    __table_args__ = (
        ForeignKeyConstraint(
            ["owner_id", "service_provider_id"],
            ["users.id", "users.service_provider_id"],
            name="fk_draft_owner_provider",
        ),
        CheckConstraint(
            "domain IN ('VM','ETL','API')", name="ck_resource_draft_domain"
        ),
        CheckConstraint("stage BETWEEN 1 AND 10", name="ck_resource_draft_stage"),
        Index(
            "ix_draft_owner_updated", "service_provider_id", "owner_id", "updated_at"
        ),
    )


class CollectorRuntimeState(Base):
    """Provider checkpoints are runtime facts, separate from desired configuration."""

    __tablename__ = "collector_runtime_states"
    collector_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("collectors.id"), primary_key=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    checkpoint: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_error: Mapped[str | None] = mapped_column(String(80))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=now, onupdate=now
    )
