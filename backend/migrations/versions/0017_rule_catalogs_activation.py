"""Independent immutable rule versions and applied monitoring bindings.

Revision ID: 0017_rule_catalogs_activation
Revises: 0016_remote_collector_assignment
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0017_rule_catalogs_activation"
down_revision = "0016_remote_collector_assignment"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("monitoring_rule_catalogs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("organizations.id",ondelete="CASCADE"), nullable=False),
        sa.Column("kind",sa.String(12),nullable=False),
        sa.Column("name",sa.String(160),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("organization_id","kind","name",name="uq_monitoring_catalog_org_kind_name"),
        sa.CheckConstraint("kind IN ('METRIC','LOG','ALERT')",name="ck_monitoring_catalog_kind"))
    op.create_index("ix_monitoring_rule_catalogs_organization_id","monitoring_rule_catalogs",["organization_id"])
    op.create_table("monitoring_rule_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("catalog_id",postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("monitoring_rule_catalogs.id",ondelete="CASCADE"),nullable=False),
        sa.Column("version",sa.Integer(),nullable=False),
        sa.Column("definition",postgresql.JSONB(),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("catalog_id","version",name="uq_monitoring_rule_version"),
        sa.CheckConstraint("version >= 1",name="ck_monitoring_rule_version_positive"))
    op.create_table("monitoring_activations",
        sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),
        sa.Column("organization_id",postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("organizations.id",ondelete="CASCADE"),nullable=False),
        sa.Column("data_source_id",postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("data_sources.id",ondelete="CASCADE"),nullable=False,unique=True),
        sa.Column("collector_id",postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("collectors.id",ondelete="SET NULL"),nullable=True),
        sa.Column("status",sa.String(24),nullable=False),
        sa.Column("fingerprint",sa.String(64),nullable=False),
        sa.Column("version",sa.Integer(),nullable=False),
        sa.Column("applied_at",sa.DateTime(timezone=True),nullable=False),
        sa.Column("details",postgresql.JSONB(),nullable=False))
    op.create_index("ix_monitoring_activations_organization_id","monitoring_activations",["organization_id"])
    op.create_table("monitoring_rule_bindings",
        sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),
        sa.Column("activation_id",postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("monitoring_activations.id",ondelete="CASCADE"),nullable=False),
        sa.Column("rule_version_id",postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("monitoring_rule_versions.id"),nullable=False),
        sa.Column("materialized_id",postgresql.UUID(as_uuid=True),nullable=True),
        sa.Column("kind",sa.String(12),nullable=False),
        sa.UniqueConstraint("activation_id","rule_version_id",name="uq_monitoring_activation_rule"))
    op.create_index("ix_monitoring_rule_bindings_activation_id","monitoring_rule_bindings",["activation_id"])

def downgrade():
    op.drop_table("monitoring_rule_bindings")
    op.drop_table("monitoring_activations")
    op.drop_table("monitoring_rule_versions")
    op.drop_table("monitoring_rule_catalogs")
