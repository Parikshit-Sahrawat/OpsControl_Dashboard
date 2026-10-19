"""Additive bindings reuse customer, source, VM, execution and alert identities."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


def now():
    return datetime.now(timezone.utc)


class MonitoringResource(Base):
    __tablename__ = "monitoring_resources"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    domain: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    environment: Mapped[str] = mapped_column(String(20), nullable=False)
    vm_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("vms.id"), unique=True)
    job_order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("job_orders.id"), unique=True
    )
    data_source_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("data_sources.id"), unique=True
    )
    primary_collector_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("collectors.id")
    )
    linked_vm_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("vms.id"), index=True
    )
    configuration: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    activation_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="CONFIGURED"
    )
    schedule_watermark: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_engine_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    last_engine_success_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    last_engine_error: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=now, onupdate=now
    )
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_monitoring_resource_org_id"),
        UniqueConstraint(
            "organization_id", "id", "job_order_id", name="uq_resource_job_scope"
        ),
        CheckConstraint("domain IN ('VM','ETL','API')", name="ck_resource_domain"),
        CheckConstraint(
            "environment IN ('PROD','QA','TEST','DEV','SANDBOX')",
            name="ck_resource_environment",
        ),
        CheckConstraint(
            "(domain='VM' AND vm_id IS NOT NULL AND job_order_id IS NULL) OR (domain='ETL' AND job_order_id IS NOT NULL AND vm_id IS NULL) OR (domain='API' AND data_source_id IS NOT NULL AND vm_id IS NULL AND job_order_id IS NULL)",
            name="ck_resource_binding",
        ),
        Index(
            "ix_resource_domain_inventory",
            "organization_id",
            "domain",
            "environment",
            "name",
            "id",
        ),
    )


class ResourceDependency(Base):
    __tablename__ = "resource_dependencies"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    depends_on_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    relationship_type: Mapped[str] = mapped_column(String(30), nullable=False)
    service_identity: Mapped[str] = mapped_column(
        String(200), nullable=False, default=""
    )
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=now
    )
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "resource_id"],
            ["monitoring_resources.organization_id", "monitoring_resources.id"],
            name="fk_dependency_resource_scope",
        ),
        ForeignKeyConstraint(
            ["organization_id", "depends_on_id"],
            ["monitoring_resources.organization_id", "monitoring_resources.id"],
            name="fk_dependency_parent_scope",
        ),
        CheckConstraint("resource_id <> depends_on_id", name="ck_dependency_not_self"),
        CheckConstraint(
            "relationship_type IN ('HOSTED_ON','REQUIRES_SERVICE','DEPENDS_ON')",
            name="ck_dependency_type",
        ),
        Index(
            "uq_dependency_current",
            "resource_id",
            "depends_on_id",
            "relationship_type",
            "service_identity",
            unique=True,
            postgresql_where=__import__("sqlalchemy").text("valid_to IS NULL"),
        ),
    )


class ParameterVersion(Base):
    __tablename__ = "resource_parameter_versions"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    configuration: Mapped[dict] = mapped_column(JSONB, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="VALIDATED")
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=now
    )
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "resource_id"],
            ["monitoring_resources.organization_id", "monitoring_resources.id"],
            name="fk_parameter_resource_scope",
        ),
        UniqueConstraint(
            "resource_id", "version", name="uq_resource_parameter_version"
        ),
        CheckConstraint(
            "status IN ('VALIDATED','ACTIVE','SUPERSEDED')", name="ck_parameter_status"
        ),
        Index(
            "uq_parameter_active",
            "resource_id",
            unique=True,
            postgresql_where=__import__("sqlalchemy").text("status='ACTIVE'"),
        ),
    )


class NormalizedEvent(Base):
    __tablename__ = "normalized_telemetry_events"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    external_key: Mapped[str] = mapped_column(String(200), nullable=False)
    source_kind: Mapped[str] = mapped_column(String(30), nullable=False)
    log_event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("log_events.id"), index=True
    )
    history_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("job_order_histories.id"), index=True
    )
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=now
    )
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    processing_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING"
    )
    processing_error: Mapped[str | None] = mapped_column(String(80))
    parameter_version: Mapped[int | None] = mapped_column(Integer)
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "resource_id"],
            ["monitoring_resources.organization_id", "monitoring_resources.id"],
            name="fk_normalized_resource_scope",
        ),
        UniqueConstraint("resource_id", "external_key", name="uq_normalized_event_key"),
        UniqueConstraint(
            "organization_id", "resource_id", "id", name="uq_normalized_event_scope"
        ),
        Index(
            "ix_normalized_pending",
            "resource_id",
            "processing_status",
            "observed_at",
            "id",
        ),
    )


class ExpectedExecutionWindow(Base):
    pentaho_authority: Mapped[dict | None] = mapped_column(JSONB)
    __tablename__ = "expected_execution_windows"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="EXPECTED")
    history_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("job_order_histories.id")
    )
    parameter_version: Mapped[int] = mapped_column(Integer, nullable=False)
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    evidence: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "resource_id"],
            ["monitoring_resources.organization_id", "monitoring_resources.id"],
            name="fk_schedule_resource_scope",
        ),
        UniqueConstraint(
            "resource_id", "scheduled_at", name="uq_expected_execution_window"
        ),
        Index("ix_expected_evaluate", "resource_id", "status", "scheduled_at"),
        CheckConstraint("deadline >= scheduled_at", name="ck_schedule_deadline"),
    )


class ResourceCondition(Base):
    __tablename__ = "resource_conditions"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    condition_key: Mapped[str] = mapped_column(String(200), nullable=False)
    condition_type: Mapped[str] = mapped_column(String(60), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    first_observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    last_observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    alert_state_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("alert_states.id"), index=True
    )
    evidence: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "resource_id"],
            ["monitoring_resources.organization_id", "monitoring_resources.id"],
            name="fk_condition_resource_scope",
        ),
        UniqueConstraint("resource_id", "condition_key", name="uq_resource_condition"),
        UniqueConstraint("organization_id", "id", name="uq_condition_org_id"),
    )


class EventCorrelationGroup(Base):
    __tablename__ = "event_correlation_groups"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    environment: Mapped[str] = mapped_column(String(20), nullable=False)
    group_key: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")
    confidence: Mapped[str] = mapped_column(String(40), nullable=False)
    evidence: Mapped[dict] = mapped_column(JSONB, nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_correlation_group_org_id"),
        Index(
            "ix_correlation_group_inventory",
            "organization_id",
            "environment",
            "opened_at",
            "id",
        ),
    )


class EventCorrelationMember(Base):
    __tablename__ = "event_correlation_members"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    condition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    relationship_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("resource_dependencies.id")
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=now
    )
    evidence: Mapped[dict] = mapped_column(JSONB, nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "group_id"],
            ["event_correlation_groups.organization_id", "event_correlation_groups.id"],
            name="fk_member_group_scope",
        ),
        ForeignKeyConstraint(
            ["organization_id", "condition_id"],
            ["resource_conditions.organization_id", "resource_conditions.id"],
            name="fk_member_condition_scope",
        ),
        UniqueConstraint("group_id", "condition_id", name="uq_correlation_member"),
    )


class ResourceMappingIssue(Base):
    __tablename__ = "resource_mapping_issues"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reason: Mapped[str] = mapped_column(String(100), nullable=False)
    candidates: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", name="uq_mapping_issue_entity"),
    )


class ParameterActivation(Base):
    __tablename__ = "resource_parameter_activations"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    parameter_version: Mapped[int] = mapped_column(Integer, nullable=False)
    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=now
    )
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "resource_id"],
            ["monitoring_resources.organization_id", "monitoring_resources.id"],
            name="fk_parameter_activation_scope",
        ),
        ForeignKeyConstraint(
            ["resource_id", "parameter_version"],
            [
                "resource_parameter_versions.resource_id",
                "resource_parameter_versions.version",
            ],
            name="fk_parameter_activation_version",
        ),
        Index(
            "uq_current_parameter_activation",
            "resource_id",
            unique=True,
            postgresql_where=__import__("sqlalchemy").text("effective_to IS NULL"),
        ),
    )
