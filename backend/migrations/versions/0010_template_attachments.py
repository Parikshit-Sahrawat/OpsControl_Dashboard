"""add normalized data source to monitoring template attachments

Revision ID: 0010_template_attachments
Revises: 0009_monitoring_templates
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0010_template_attachments"
down_revision = "0009_monitoring_templates"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "monitoring_template_attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("data_source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("monitoring_templates.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("template_version", sa.Integer(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("overrides", sa.JSON()),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("data_source_id", "template_id", name="uq_template_attachment_source_template"),
    )
    op.create_index("ix_template_attachment_data_source_id", "monitoring_template_attachments", ["data_source_id"])
    op.create_index("ix_template_attachment_template_id", "monitoring_template_attachments", ["template_id"])

def downgrade():
    op.drop_index("ix_template_attachment_template_id", table_name="monitoring_template_attachments")
    op.drop_index("ix_template_attachment_data_source_id", table_name="monitoring_template_attachments")
    op.drop_table("monitoring_template_attachments")
