"""add alert state and notification delivery

Revision ID: 0006_alert_state
Revises: 0005_metric_samples
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006_alert_state"
down_revision = "0005_metric_samples"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("alert_rules", sa.Column("notification_channels", sa.JSON(), nullable=True))

    op.create_table(
        "alert_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("alert_rule_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("alert_rules.id"), nullable=False),
        sa.Column("metric_definition_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("metric_definitions.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="OPEN"),
        sa.Column("severity", sa.String(50), nullable=False),
        sa.Column("first_triggered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("last_value", sa.Float(), nullable=False),
        sa.Column("breach_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("external_references", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_alert_states_organization_id", "alert_states", ["organization_id"])
    op.create_index("ix_alert_states_alert_rule_id", "alert_states", ["alert_rule_id"])
    op.create_index("ix_alert_states_metric_definition_id", "alert_states", ["metric_definition_id"])
    op.create_index(
        "uq_alert_states_open_rule",
        "alert_states",
        ["alert_rule_id"],
        unique=True,
        postgresql_where=sa.text("status = 'OPEN'"),
    )

    op.create_table(
        "alert_notification_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("alert_state_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("alert_states.id"), nullable=False),
        sa.Column("channel", sa.String(50), nullable=False),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("external_reference", sa.String(500)),
        sa.Column("last_error", sa.Text()),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("payload", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_alert_notification_deliveries_alert_state_id", "alert_notification_deliveries", ["alert_state_id"])
    op.create_index(
        "ix_alert_notification_pending",
        "alert_notification_deliveries",
        ["status", "created_at"],
    )


def downgrade():
    op.drop_table("alert_notification_deliveries")
    op.drop_index("uq_alert_states_open_rule", table_name="alert_states")
    op.drop_table("alert_states")
    op.drop_column("alert_rules", "notification_channels")
