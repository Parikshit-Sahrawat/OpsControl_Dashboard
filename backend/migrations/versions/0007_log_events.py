"""add native log event storage

Revision ID: 0007_log_events
Revises: 0006_alert_state
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0007_log_events"
down_revision = "0006_alert_state"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "log_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("log_source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("log_sources.id"), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("severity", sa.String(30)),
        sa.Column("event_type", sa.String(100)),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("parser_type", sa.String(100)),
        sa.Column("source_offset", sa.String(200)),
        sa.Column("fingerprint", sa.String(128)),
        sa.Column("attributes", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_log_events_organization_id", "log_events", ["organization_id"])
    op.create_index("ix_log_events_log_source_id", "log_events", ["log_source_id"])
    op.create_index("ix_log_events_observed_at", "log_events", ["observed_at"])
    op.create_index("ix_log_events_fingerprint", "log_events", ["fingerprint"])
    op.create_index("ix_log_events_source_observed", "log_events", ["log_source_id", "observed_at"])
    op.create_index("ix_log_events_org_observed", "log_events", ["organization_id", "observed_at"])


def downgrade():
    op.drop_index("ix_log_events_org_observed", table_name="log_events")
    op.drop_index("ix_log_events_source_observed", table_name="log_events")
    op.drop_index("ix_log_events_fingerprint", table_name="log_events")
    op.drop_index("ix_log_events_observed_at", table_name="log_events")
    op.drop_index("ix_log_events_log_source_id", table_name="log_events")
    op.drop_index("ix_log_events_organization_id", table_name="log_events")
    op.drop_table("log_events")
