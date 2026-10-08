"""add persisted monitoring templates and version history

Revision ID: 0009_monitoring_templates
Revises: 0008_correlation_engine
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0009_monitoring_templates"
down_revision = "0008_correlation_engine"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "monitoring_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False, unique=True),
        sa.Column("description", sa.Text()),
        sa.Column("scope", sa.String(200), nullable=False, server_default="VM + Application / Services"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(30), nullable=False, server_default="COMMITTED"),
        sa.Column("package_config", sa.JSON(), nullable=False),
        sa.Column("committed_at", sa.DateTime(timezone=True)),
        sa.Column("committed_by", sa.String(200)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "monitoring_template_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("monitoring_templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="COMMITTED"),
        sa.Column("package_config", sa.JSON(), nullable=False),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("committed_by", sa.String(200)),
        sa.UniqueConstraint("template_id", "version", name="uq_monitoring_template_version"),
    )
    op.create_index("ix_monitoring_template_versions_template_id", "monitoring_template_versions", ["template_id"])


def downgrade():
    op.drop_index("ix_monitoring_template_versions_template_id", table_name="monitoring_template_versions")
    op.drop_table("monitoring_template_versions")
    op.drop_table("monitoring_templates")
