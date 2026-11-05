"""Introduce ETL workflow expectations and ordered job dependencies.

Legacy job orders remain unassigned; no automatic grouping or policy rewrite.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0039_etl_workflow_foundation"
down_revision = "0038_k8s_cluster_associations"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "etl_workflows",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("environment", sa.String(50), nullable=False),
        sa.Column("schedule", sa.JSON(), nullable=False),
        sa.Column("expected_window_start", sa.String(10)),
        sa.Column("expected_window_end", sa.String(10)),
        sa.Column("expected_duration_seconds", sa.Integer()),
        sa.Column("sla_seconds", sa.Integer()),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "environment", "name", name="uq_etl_workflow_scope"),
        sa.CheckConstraint("expected_duration_seconds IS NULL OR expected_duration_seconds > 0", name="ck_etl_workflow_duration"),
        sa.CheckConstraint("sla_seconds IS NULL OR sla_seconds > 0", name="ck_etl_workflow_sla"),
    )
    op.create_index("ix_etl_workflows_organization_id", "etl_workflows", ["organization_id"])
    op.add_column("job_orders", sa.Column("workflow_id", UUID(as_uuid=True), sa.ForeignKey("etl_workflows.id", ondelete="RESTRICT"), nullable=True))
    op.create_index("ix_job_orders_workflow_id", "job_orders", ["workflow_id"])
    op.create_table(
        "etl_workflow_dependencies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workflow_id", UUID(as_uuid=True), sa.ForeignKey("etl_workflows.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("predecessor_job_id", UUID(as_uuid=True), sa.ForeignKey("job_orders.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("successor_job_id", UUID(as_uuid=True), sa.ForeignKey("job_orders.id", ondelete="RESTRICT"), nullable=False),
        sa.UniqueConstraint("workflow_id", "predecessor_job_id", "successor_job_id", name="uq_etl_workflow_dependency"),
        sa.CheckConstraint("predecessor_job_id <> successor_job_id", name="ck_etl_dependency_no_self"),
    )
    op.create_index("ix_etl_workflow_dependencies_workflow_id", "etl_workflow_dependencies", ["workflow_id"])


def downgrade():
    op.drop_index("ix_etl_workflow_dependencies_workflow_id", table_name="etl_workflow_dependencies")
    op.drop_table("etl_workflow_dependencies")
    op.drop_index("ix_job_orders_workflow_id", table_name="job_orders")
    op.drop_column("job_orders", "workflow_id")
    op.drop_index("ix_etl_workflows_organization_id", table_name="etl_workflows")
    op.drop_table("etl_workflows")
