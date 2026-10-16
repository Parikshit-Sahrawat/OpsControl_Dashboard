"""Pentaho extensions to canonical JobOrderHistory; never a second run engine."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


def now():
    return datetime.now(timezone.utc)


class Scoped:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, nullable=False
    )


def history_fk(name):
    return ForeignKeyConstraint(
        ["organization_id", "resource_id", "history_id"],
        [
            "job_order_histories.pentaho_customer_id",
            "job_order_histories.pentaho_resource_id",
            "job_order_histories.id",
        ],
        name=name,
        ondelete="RESTRICT",
    )


class PentahoAttempt(Scoped, Base):
    __tablename__ = "pentaho_execution_attempts"
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    history_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    attempt_key: Mapped[str] = mapped_column(String(100), nullable=False)
    attempt_order: Mapped[int] = mapped_column(Integer, nullable=False)
    native_identity: Mapped[dict] = mapped_column(JSONB, nullable=False)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False, default="UNKNOWN")
    completeness: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PARTIAL"
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retry_authority: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    __table_args__ = (
        history_fk("fk_pentaho_attempt_history_scope"),
        UniqueConstraint(
            "organization_id",
            "resource_id",
            "attempt_key",
            name="uq_pentaho_attempt_key",
        ),
        UniqueConstraint(
            "history_id", "attempt_order", name="uq_pentaho_attempt_order"
        ),
        UniqueConstraint(
            "organization_id",
            "resource_id",
            "history_id",
            "id",
            name="uq_pentaho_attempt_scope",
        ),
        CheckConstraint(
            "attempt_order BETWEEN 1 AND 10000", name="ck_pentaho_attempt_order"
        ),
        CheckConstraint(
            "outcome IN ('RUNNING','SUCCESS','FAILED','CANCELLED','UNKNOWN')",
            name="ck_pentaho_attempt_outcome",
        ),
        CheckConstraint(
            "completeness IN ('PARTIAL','COMPLETE','UNKNOWN')",
            name="ck_pentaho_attempt_completeness",
        ),
    )


class PentahoAlias(Scoped, Base):
    __tablename__ = "pentaho_native_aliases"
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    history_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    attempt_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    alias_key: Mapped[str] = mapped_column(String(100), nullable=False)
    kind: Mapped[str] = mapped_column(String(25), nullable=False)
    native_identity: Mapped[dict] = mapped_column(JSONB, nullable=False)
    __table_args__ = (
        history_fk("fk_pentaho_alias_history_scope"),
        ForeignKeyConstraint(
            ["organization_id", "resource_id", "history_id", "attempt_id"],
            [
                "pentaho_execution_attempts.organization_id",
                "pentaho_execution_attempts.resource_id",
                "pentaho_execution_attempts.history_id",
                "pentaho_execution_attempts.id",
            ],
            name="fk_pentaho_alias_attempt_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "organization_id",
            "resource_id",
            "alias_key",
            name="uq_pentaho_native_alias",
        ),
        Index("ix_pentaho_alias_attempt", "attempt_id"),
        CheckConstraint(
            "kind IN ('INVOCATION','LOGICAL','SCHEDULER_ATTEMPT')",
            name="ck_pentaho_alias_kind",
        ),
    )


class PentahoRevision(Scoped, Base):
    __tablename__ = "pentaho_attempt_revisions"
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    history_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    attempt_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_evidence_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    observation_key: Mapped[str] = mapped_column(String(64), nullable=False)
    disposition: Mapped[str] = mapped_column(String(30), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    __table_args__ = (
        history_fk("fk_pentaho_revision_history_scope"),
        ForeignKeyConstraint(
            ["organization_id", "resource_id", "history_id", "attempt_id"],
            [
                "pentaho_execution_attempts.organization_id",
                "pentaho_execution_attempts.resource_id",
                "pentaho_execution_attempts.history_id",
                "pentaho_execution_attempts.id",
            ],
            name="fk_pentaho_revision_attempt_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "resource_id", "event_id"],
            [
                "normalized_telemetry_events.organization_id",
                "normalized_telemetry_events.resource_id",
                "normalized_telemetry_events.id",
            ],
            name="fk_pentaho_revision_event_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "source_evidence_id"],
            ["pipeline_evidence.organization_id", "pipeline_evidence.id"],
            name="fk_pentaho_revision_raw_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("attempt_id", "revision", name="uq_pentaho_attempt_revision"),
        UniqueConstraint("event_id", name="uq_pentaho_revision_event"),
        UniqueConstraint(
            "attempt_id", "observation_key", name="uq_pentaho_observation"
        ),
        Index("ix_pentaho_revision_raw_evidence", "source_evidence_id"),
    )


class PentahoRecoveryLink(Scoped, Base):
    __tablename__ = "pentaho_recovery_links"
    failed_history_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    recovery_history_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PROPOSED")
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    proposed_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "failed_history_id"],
            ["job_order_histories.pentaho_customer_id", "job_order_histories.id"],
            name="fk_pentaho_recovery_failed_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "recovery_history_id"],
            ["job_order_histories.pentaho_customer_id", "job_order_histories.id"],
            name="fk_pentaho_recovery_run_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "failed_history_id", "recovery_history_id", name="uq_pentaho_recovery_pair"
        ),
        UniqueConstraint("organization_id", "id", name="uq_pentaho_recovery_scope"),
        Index("ix_pentaho_recovery_target", "recovery_history_id"),
        CheckConstraint(
            "failed_history_id <> recovery_history_id",
            name="ck_pentaho_recovery_not_self",
        ),
        CheckConstraint(
            "status IN ('PROPOSED','CONFIRMED','REVERSED')",
            name="ck_pentaho_recovery_status",
        ),
    )


class PentahoRecoveryDecision(Scoped, Base):
    __tablename__ = "pentaho_recovery_decisions"
    link_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    request_key: Mapped[str] = mapped_column(String(100), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[list] = mapped_column(JSONB, nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "link_id"],
            ["pentaho_recovery_links.organization_id", "pentaho_recovery_links.id"],
            name="fk_pentaho_recovery_decision_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "link_id", "revision", name="uq_pentaho_recovery_decision_revision"
        ),
        UniqueConstraint(
            "organization_id", "request_key", name="uq_pentaho_recovery_request"
        ),
        CheckConstraint(
            "action IN ('PROPOSE','CONFIRM','REVERSE')",
            name="ck_pentaho_recovery_action",
        ),
    )
