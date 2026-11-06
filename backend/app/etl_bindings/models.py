"""Immutable version tuples. Only validity closure is mutable (DB enforced)."""

from datetime import datetime
from uuid import UUID
from sqlalchemy import String, DateTime, ForeignKey, CheckConstraint, Index, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base
from app.data_pipelines.models import Scoped, scope_args, scoped_fk


class ETLNativeBinding(Scoped, Base):
    __tablename__ = "etl_native_bindings"
    workflow_id: Mapped[UUID] = mapped_column(
        ForeignKey("etl_workflows.id", ondelete="RESTRICT"), nullable=False
    )
    job_order_id: Mapped[UUID] = mapped_column(
        ForeignKey("job_orders.id", ondelete="RESTRICT"), nullable=False
    )
    resource_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    native_job_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    integration_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    previous_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    identity_key: Mapped[str] = mapped_column(String(64), nullable=False)
    identity_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    method_snapshot: Mapped[list] = mapped_column(JSONB, nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actor_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    operation_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    __table_args__ = scope_args(
        "etl_native_binding",
        scoped_fk("monitoring_resources", "resource_id", "fk_binding_resource"),
        scoped_fk("pipeline_jobs", "native_job_id", "fk_binding_native"),
        scoped_fk("pipeline_integrations", "integration_id", "fk_binding_integration"),
        scoped_fk("pipeline_operations", "operation_id", "fk_binding_operation"),
        scoped_fk("etl_native_bindings", "previous_id", "fk_binding_previous"),
        CheckConstraint(
            "state IN ('STAGED','CONFIRMED','RETIRED')", name="ck_binding_state"
        ),
        CheckConstraint(
            "valid_until IS NULL OR valid_until >= valid_from",
            name="ck_binding_validity",
        ),
        Index(
            "uq_binding_current_job",
            "job_order_id",
            unique=True,
            postgresql_where=text("valid_until IS NULL"),
        ),
        Index(
            "uq_binding_current_target",
            "organization_id",
            "identity_key",
            unique=True,
            postgresql_where=text("valid_until IS NULL AND state <> 'RETIRED'"),
        ),
        Index("uq_binding_successor", "previous_id", unique=True),
    )


class ETLBindingReceipt(Scoped, Base):
    __tablename__ = "etl_binding_receipts"
    binding_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    evidence_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), nullable=False, unique=True
    )
    payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    __table_args__ = scope_args(
        "etl_binding_receipt",
        scoped_fk("etl_native_bindings", "binding_id", "fk_binding_receipt_binding"),
        scoped_fk("pipeline_evidence", "evidence_id", "fk_binding_receipt_evidence"),
    )


# Independently enforces the canonical tuple even if a caller supplies a wrong hash.
Index(
    "uq_binding_current_claim_tuple",
    ETLNativeBinding.organization_id,
    *(
        ETLNativeBinding.identity_snapshot[field].astext
        for field in (
            "platform",
            "environment",
            "authority_claim",
            "object_kind",
            "native_id",
        )
    ),
    unique=True,
    postgresql_where=text("valid_until IS NULL AND state <> 'RETIRED'"),
)


class ETLNativeAttestation(Scoped, Base):
    __tablename__ = "etl_native_attestations"
    binding_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    resource_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    target_key: Mapped[str] = mapped_column(String(64), nullable=False)
    envelope: Mapped[dict] = mapped_column(JSONB, nullable=False)
    envelope_sha256: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True
    )
    issuer_key_id: Mapped[str] = mapped_column(String(100), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    submitted_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    __table_args__ = scope_args(
        "etl_native_attestation",
        scoped_fk("etl_native_bindings", "binding_id", "fk_attestation_binding"),
        scoped_fk("monitoring_resources", "resource_id", "fk_attestation_resource"),
    )


class ETLAuthorityRevocation(Scoped, Base):
    __tablename__ = "etl_authority_revocations"
    attestation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), nullable=False, unique=True
    )
    actor_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    __table_args__ = scope_args(
        "etl_authority_revocation",
        scoped_fk(
            "etl_native_attestations", "attestation_id", "fk_authority_revocation"
        ),
    )


class ETLBindingQualification(Scoped, Base):
    __tablename__ = "etl_binding_qualifications"
    binding_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), nullable=False, unique=True
    )
    attestation_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    job_order_id: Mapped[UUID] = mapped_column(
        ForeignKey("job_orders.id", ondelete="RESTRICT"), nullable=False
    )
    target_key: Mapped[str] = mapped_column(String(64), nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = scope_args(
        "etl_binding_qualification",
        scoped_fk("etl_native_bindings", "binding_id", "fk_qualification_binding"),
        scoped_fk(
            "etl_native_attestations", "attestation_id", "fk_qualification_attestation"
        ),
        Index(
            "uq_native_qualified_owner",
            "organization_id",
            "target_key",
            unique=True,
            postgresql_where=text("valid_until IS NULL"),
        ),
    )
