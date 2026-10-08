"""add alert rules

Revision ID: 0003_alert_rules
Revises: 0002_monitoring_configuration
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_alert_rules"
down_revision = "0002_monitoring_configuration"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "alert_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("metric_definition_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("metric_definitions.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("severity", sa.String(50), nullable=False, server_default="WARNING"),
        sa.Column("operator", sa.String(20), nullable=False, server_default="GT"),
        sa.Column("threshold_value", sa.String(100), nullable=False),
        sa.Column("evaluation_window_seconds", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("consecutive_breaches", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "name", name="uq_alert_rule_org_name"),
    )
    op.create_index("ix_alert_rules_organization_id", "alert_rules", ["organization_id"])
    op.create_index("ix_alert_rules_metric_definition_id", "alert_rules", ["metric_definition_id"])


def downgrade():
    op.drop_table("alert_rules")
