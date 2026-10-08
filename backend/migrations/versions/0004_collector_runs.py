"""persist collector execution results

Revision ID: 0004_collector_runs
Revises: 0003_alert_rules
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_collector_runs"
down_revision = "0003_alert_rules"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "collector_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("collector_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("collectors.id"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("outcome", sa.String(100)),
        sa.Column("http_status", sa.Integer()),
        sa.Column("response_time_ms", sa.Integer()),
        sa.Column("response_size_bytes", sa.Integer()),
        sa.Column("response_body", sa.Text()),
        sa.Column("error_message", sa.Text()),
    )
    op.create_index("ix_collector_runs_collector_id", "collector_runs", ["collector_id"])


def downgrade():
    op.drop_table("collector_runs")
