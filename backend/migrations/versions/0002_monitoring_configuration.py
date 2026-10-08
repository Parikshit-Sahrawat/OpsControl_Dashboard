"""add dynamic monitoring configuration models"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_monitoring_configuration"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "data_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("source_type", sa.String(100), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("endpoint", sa.String(1000)),
        sa.Column("auth_type", sa.String(100)),
        sa.Column("connection_config", sa.JSON()),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("status", sa.String(50), nullable=False, server_default="UNKNOWN"),
        sa.Column("last_test_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "name", name="uq_data_source_org_name"),
    )
    op.create_index("ix_data_sources_organization_id", "data_sources", ["organization_id"])

    op.create_table(
        "collectors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("data_source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("data_sources.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("collector_type", sa.String(100), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("interval_seconds", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("configuration", sa.JSON()),
        sa.Column("status", sa.String(50), nullable=False, server_default="STOPPED"),
        sa.Column("last_run_at", sa.DateTime(timezone=True)),
        sa.Column("last_success_at", sa.DateTime(timezone=True)),
        sa.Column("last_error_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.Column("next_run_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("data_source_id", "name", name="uq_collector_source_name"),
    )
    op.create_index("ix_collectors_data_source_id", "collectors", ["data_source_id"])

    op.create_table(
        "metric_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("data_source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("data_sources.id")),
        sa.Column("collector_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("collectors.id")),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True)),
        sa.Column("metric_type", sa.String(50), nullable=False),
        sa.Column("unit", sa.String(50)),
        sa.Column("collection_interval_seconds", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("retention_days", sa.Integer(), nullable=False, server_default="365"),
        sa.Column("aggregation", sa.String(50), nullable=False, server_default="avg"),
        sa.Column("query_config", sa.JSON()),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_metric_definitions_organization_id", "metric_definitions", ["organization_id"])
    op.create_index("ix_metric_definitions_data_source_id", "metric_definitions", ["data_source_id"])
    op.create_index("ix_metric_definitions_collector_id", "metric_definitions", ["collector_id"])
    op.create_index("ix_metric_definitions_resource_id", "metric_definitions", ["resource_id"])

    op.create_table(
        "log_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("data_source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("data_sources.id")),
        sa.Column("collector_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("collectors.id")),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("source_type", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True)),
        sa.Column("location", sa.String(1000)),
        sa.Column("parser_type", sa.String(100), nullable=False, server_default="RAW"),
        sa.Column("parser_config", sa.JSON()),
        sa.Column("start_position", sa.String(50), nullable=False, server_default="NEW"),
        sa.Column("collection_interval_seconds", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("retention_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_log_sources_organization_id", "log_sources", ["organization_id"])
    op.create_index("ix_log_sources_data_source_id", "log_sources", ["data_source_id"])
    op.create_index("ix_log_sources_collector_id", "log_sources", ["collector_id"])
    op.create_index("ix_log_sources_resource_id", "log_sources", ["resource_id"])


def downgrade():
    op.drop_table("log_sources")
    op.drop_table("metric_definitions")
    op.drop_table("collectors")
    op.drop_table("data_sources")
