"""add native metric samples

Revision ID: 0005_metric_samples
Revises: 0004_collector_runs
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_metric_samples"
down_revision = "0004_collector_runs"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "metric_samples",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("metric_definition_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("metric_definitions.id"), nullable=False),
        sa.Column("collector_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("collectors.id")),
        sa.Column("collector_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("collector_runs.id")),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("value_numeric", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(50)),
        sa.Column("dimensions", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_metric_samples_org_observed", "metric_samples", ["organization_id", "observed_at"])
    op.create_index("ix_metric_samples_metric_observed", "metric_samples", ["metric_definition_id", "observed_at"])
    op.create_index("ix_metric_samples_metric_definition_id", "metric_samples", ["metric_definition_id"])
    op.create_index("ix_metric_samples_collector_id", "metric_samples", ["collector_id"])
    op.create_index("ix_metric_samples_collector_run_id", "metric_samples", ["collector_run_id"])


def downgrade():
    op.drop_table("metric_samples")
