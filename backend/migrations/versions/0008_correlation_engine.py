"""add correlation records and evidence

Revision ID: 0008_correlation_engine
Revises: 0007_log_events
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008_correlation_engine"
down_revision = "0007_log_events"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "correlation_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("history_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("job_order_histories.id"), nullable=False, unique=True),
        sa.Column("anchor_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="ANALYZED"),
        sa.Column("primary_category", sa.String(100), nullable=False, server_default="NO_RELATED_EVIDENCE"),
        sa.Column("confidence", sa.String(30), nullable=False, server_default="NONE"),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("evidence_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("analysis_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_correlation_records_organization_id", "correlation_records", ["organization_id"])
    op.create_index("ix_correlation_records_history_id", "correlation_records", ["history_id"])

    op.create_table(
        "correlation_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("correlation_records.id"), nullable=False),
        sa.Column("evidence_type", sa.String(50), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resource_type", sa.String(100)),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True)),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("severity", sa.String(50)),
        sa.Column("relationship", sa.String(100), nullable=False),
        sa.Column("details", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_correlation_evidence_correlation_id", "correlation_evidence", ["correlation_id"])
    op.create_index("ix_correlation_evidence_source_id", "correlation_evidence", ["source_id"])
    op.create_index("ix_correlation_evidence_resource_id", "correlation_evidence", ["resource_id"])
    op.create_index("ix_correlation_evidence_corr_observed", "correlation_evidence", ["correlation_id", "observed_at"])
    op.create_index("ix_correlation_evidence_resource_observed", "correlation_evidence", ["resource_id", "observed_at"])


def downgrade():
    op.drop_index("ix_correlation_evidence_resource_observed", table_name="correlation_evidence")
    op.drop_index("ix_correlation_evidence_corr_observed", table_name="correlation_evidence")
    op.drop_index("ix_correlation_evidence_resource_id", table_name="correlation_evidence")
    op.drop_index("ix_correlation_evidence_source_id", table_name="correlation_evidence")
    op.drop_index("ix_correlation_evidence_correlation_id", table_name="correlation_evidence")
    op.drop_table("correlation_evidence")
    op.drop_index("ix_correlation_records_history_id", table_name="correlation_records")
    op.drop_index("ix_correlation_records_organization_id", table_name="correlation_records")
    op.drop_table("correlation_records")
