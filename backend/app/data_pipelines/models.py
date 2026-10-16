"""Additive customer-scoped integrations and fenced physical collection units."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


def now():
    return datetime.now(timezone.utc)


class Scoped:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=now
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


def scope_args(name, *constraints):
    return (
        UniqueConstraint("organization_id", "id", name="uq_" + name + "_scope"),
        *constraints,
    )


def scoped_fk(table, column, name):
    return ForeignKeyConstraint(
        ["organization_id", column],
        [table + ".organization_id", table + ".id"],
        name=name,
        ondelete="RESTRICT",
    )


class PipelineIntegration(Scoped, Base):
    __tablename__ = "pipeline_integrations"
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    platform: Mapped[str] = mapped_column(String(30), nullable=False)
    environment: Mapped[str] = mapped_column(String(20), nullable=False)
    vm_resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    configuration: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    stage: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    last_discovery_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_redetection_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    __table_args__ = scope_args(
        "pipeline_integration",
        scoped_fk("monitoring_resources", "vm_resource_id", "fk_pipeline_vm_scope"),
        CheckConstraint("stage BETWEEN 1 AND 8", name="ck_pipeline_stage"),
        CheckConstraint(
            "environment IN ('PROD','QA','TEST','DEV','SANDBOX')",
            name="ck_pipeline_environment",
        ),
    )


class PipelineConnection(Scoped, Base):
    __tablename__ = "pipeline_connections"
    integration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    configuration: Mapped[dict] = mapped_column(JSONB, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    __table_args__ = scope_args(
        "pipeline_connection",
        scoped_fk(
            "pipeline_integrations", "integration_id", "fk_pipeline_connection_scope"
        ),
        UniqueConstraint(
            "integration_id", "version", name="uq_pipeline_connection_version"
        ),
    )


class PipelineCapability(Scoped, Base):
    __tablename__ = "pipeline_capabilities"
    integration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    platform_version: Mapped[str] = mapped_column(String(100), nullable=False)
    edition: Mapped[str] = mapped_column(String(100), nullable=False)
    deployment_type: Mapped[str] = mapped_column(String(50), nullable=False)
    definition: Mapped[dict] = mapped_column(JSONB, nullable=False)
    compatibility: Mapped[str] = mapped_column(
        String(20), nullable=False, default="UNVERIFIED"
    )
    evidence_status: Mapped[str] = mapped_column(
        String(25), nullable=False, default="UNKNOWN"
    )
    verification_evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True)
    )
    __table_args__ = scope_args(
        "pipeline_capability",
        scoped_fk(
            "pipeline_integrations", "integration_id", "fk_pipeline_capability_scope"
        ),
        scoped_fk(
            "pipeline_evidence",
            "verification_evidence_id",
            "fk_pipeline_capability_proof_scope",
        ),
        CheckConstraint(
            "compatibility IN ('SUPPORTED','CONDITIONAL','UNSUPPORTED','UNVERIFIED')",
            name="ck_pipeline_compatibility",
        ),
        CheckConstraint(
            "evidence_status IN ('DOCUMENTED','RUNTIME_VERIFIED','UNKNOWN')",
            name="ck_pipeline_capability_evidence",
        ),
    )


class PipelineSource(Scoped, Base):
    __tablename__ = "pipeline_sources"
    method_type: Mapped[str] = mapped_column(String(30), nullable=False)
    canonical_key: Mapped[str] = mapped_column(String(64), nullable=False)
    identity: Mapped[dict] = mapped_column(JSONB, nullable=False)
    generation: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, default=uuid.uuid4
    )
    fence: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    lease_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="LIVE")
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    live_checkpoint: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    recovery_checkpoint: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    continuity_validated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    health: Mapped[str] = mapped_column(String(30), nullable=False, default="NO_DATA")
    last_received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    legacy_collector_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("collectors.id"), unique=True
    )
    __table_args__ = scope_args(
        "pipeline_source",
        UniqueConstraint(
            "organization_id", "canonical_key", name="uq_pipeline_canonical_source"
        ),
        CheckConstraint("fence >= 0", name="ck_pipeline_fence"),
    )


class PipelineMethod(Scoped, Base):
    __tablename__ = "pipeline_methods"
    integration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    capability_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    transport: Mapped[str] = mapped_column(String(15), nullable=False)
    configuration: Mapped[dict] = mapped_column(JSONB, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    validation: Mapped[str] = mapped_column(
        String(20), nullable=False, default="UNVALIDATED"
    )
    last_error: Mapped[str | None] = mapped_column(String(80))
    __table_args__ = scope_args(
        "pipeline_method",
        *(
            scoped_fk(table, field, "fk_method_" + field)
            for table, field in (
                ("pipeline_integrations", "integration_id"),
                ("pipeline_sources", "source_id"),
                ("pipeline_connections", "connection_id"),
                ("pipeline_capabilities", "capability_id"),
            )
        ),
        UniqueConstraint(
            "integration_id", "source_id", name="uq_pipeline_method_source"
        ),
        CheckConstraint(
            "transport IN ('BACKEND','AGENT')", name="ck_pipeline_transport"
        )
    )


class PipelineJob(Scoped, Base):
    __tablename__ = "pipeline_jobs"
    integration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    native_id: Mapped[str] = mapped_column(String(500), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    origin: Mapped[str] = mapped_column(String(20), nullable=False)
    selected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    quarantined: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    stale_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    __table_args__ = scope_args(
        "pipeline_job",
        scoped_fk("pipeline_integrations", "integration_id", "fk_pipeline_job_scope"),
        scoped_fk(
            "monitoring_resources", "resource_id", "fk_pipeline_job_resource_scope"
        ),
        UniqueConstraint("integration_id", "native_id", name="uq_pipeline_native_job"),
    )


class PipelineAssociation(Scoped, Base):
    __tablename__ = "pipeline_associations"
    method_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    generation: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    confirmed_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    __table_args__ = scope_args(
        "pipeline_association",
        scoped_fk("pipeline_methods", "method_id", "fk_association_method_scope"),
        scoped_fk("pipeline_jobs", "job_id", "fk_association_job_scope"),
        UniqueConstraint(
            "method_id", "job_id", "generation", name="uq_pipeline_association"
        ),
    )


class PipelineHold(Scoped, Base):
    __tablename__ = "pipeline_holds"
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    reference: Mapped[str] = mapped_column(String(120), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    released_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    __table_args__ = scope_args(
        "pipeline_hold",
        scoped_fk("pipeline_sources", "source_id", "fk_pipeline_hold_scope"),
        UniqueConstraint(
            "source_id", "kind", "reference", name="uq_pipeline_hold_reference"
        ),
        CheckConstraint(
            "kind IN ('INTEGRATION','MANUAL','LEGAL','CONTINUITY')",
            name="ck_pipeline_hold_kind",
        ),
    )


class PipelineEvidence(Scoped, Base):
    __tablename__ = "pipeline_evidence"
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    generation: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    external_key: Mapped[str] = mapped_column(String(500), nullable=False)
    native_job_id: Mapped[str | None] = mapped_column(String(500))
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    outcome: Mapped[str] = mapped_column(String(30), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    __table_args__ = scope_args(
        "pipeline_evidence",
        scoped_fk("pipeline_sources", "source_id", "fk_pipeline_evidence_scope"),
        UniqueConstraint(
            "source_id",
            "generation",
            "external_key",
            name="uq_pipeline_evidence_identity",
        ),
    )


class PipelineOperation(Scoped, Base):
    __tablename__ = "pipeline_operations"
    integration_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    state: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    configuration: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    result: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    fence: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = scope_args(
        "pipeline_operation",
        scoped_fk(
            "pipeline_integrations",
            "integration_id",
            "fk_pipeline_operation_integration",
        ),
        scoped_fk("pipeline_sources", "source_id", "fk_pipeline_operation_source"),
        UniqueConstraint(
            "organization_id",
            "kind",
            "idempotency_key",
            name="uq_pipeline_operation_idempotency",
        ),
    )


TABLES = [
    PipelineIntegration,
    PipelineConnection,
    PipelineCapability,
    PipelineSource,
    PipelineMethod,
    PipelineJob,
    PipelineAssociation,
    PipelineHold,
    PipelineEvidence,
    PipelineOperation,
]
