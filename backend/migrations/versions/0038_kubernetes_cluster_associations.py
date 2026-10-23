"""Add canonical verified EKS identity and audited customer associations.

Existing customer-owned DataSource and VM rows are not modified. No historical
EKS source is automatically associated; it must be rediscovered and approved.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0038_k8s_cluster_associations"
down_revision = "0037_access_boundaries"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "kubernetes_clusters",
        sa.Column("id", UUID(), primary_key=True),
        sa.Column("provider_identity", sa.String(512), nullable=False),
        sa.Column("provider_cluster_id", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "provider_identity",
            "provider_cluster_id",
            name="uq_k8s_verified_cluster_identity",
        ),
    )
    op.create_table(
        "kubernetes_cluster_associations",
        sa.Column("id", UUID(), primary_key=True),
        sa.Column(
            "cluster_id",
            UUID(),
            sa.ForeignKey("kubernetes_clusters.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            UUID(),
            sa.ForeignKey("organizations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "cluster_id", "organization_id", name="uq_k8s_cluster_customer"
        ),
        sa.CheckConstraint("revision > 0", name="ck_k8s_association_revision"),
    )
    op.create_index(
        "ix_kubernetes_cluster_associations_organization_id",
        "kubernetes_cluster_associations",
        ["organization_id"],
    )
    op.create_table(
        "kubernetes_cluster_association_decisions",
        sa.Column("id", UUID(), primary_key=True),
        sa.Column(
            "association_id",
            UUID(),
            sa.ForeignKey("kubernetes_cluster_associations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "actor_id",
            UUID(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.String(2000), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "association_id", "revision", name="uq_k8s_association_decision_revision"
        ),
        sa.CheckConstraint("revision > 0", name="ck_k8s_decision_revision"),
    )
    op.execute(
        """CREATE FUNCTION k8s_association_decision_guard() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'Kubernetes association history is immutable'; END $$"""
    )
    op.execute(
        "CREATE TRIGGER k8s_association_decision_immutable BEFORE UPDATE OR DELETE ON kubernetes_cluster_association_decisions FOR EACH ROW EXECUTE FUNCTION k8s_association_decision_guard()"
    )
    op.execute(
        """CREATE FUNCTION k8s_cluster_identity_guard() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'Canonical Kubernetes cluster identity is immutable'; END $$"""
    )
    op.execute(
        "CREATE TRIGGER k8s_cluster_identity_immutable BEFORE UPDATE OR DELETE ON kubernetes_clusters FOR EACH ROW EXECUTE FUNCTION k8s_cluster_identity_guard()"
    )
    op.execute(
        """CREATE FUNCTION k8s_association_revision_guard() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'Kubernetes association cannot be deleted';
          END IF;
          IF NEW.id != OLD.id OR NEW.cluster_id != OLD.cluster_id OR
             NEW.organization_id != OLD.organization_id OR NEW.created_at != OLD.created_at OR
             NEW.revision != OLD.revision + 1 OR NEW.active = OLD.active THEN
            RAISE EXCEPTION 'Invalid Kubernetes association revision';
          END IF;
          RETURN NEW;
        END $$"""
    )
    op.execute(
        "CREATE TRIGGER k8s_association_revision_valid BEFORE UPDATE OR DELETE ON kubernetes_cluster_associations FOR EACH ROW EXECUTE FUNCTION k8s_association_revision_guard()"
    )


def downgrade():
    if op.get_bind().scalar(
        sa.text(
            "SELECT EXISTS(SELECT 1 FROM kubernetes_clusters) OR "
            "EXISTS(SELECT 1 FROM kubernetes_cluster_associations) OR "
            "EXISTS(SELECT 1 FROM kubernetes_cluster_association_decisions)"
        )
    ):
        raise RuntimeError(
            "Canonical cluster or association evidence exists; restore a verified backup"
        )
    op.drop_table("kubernetes_cluster_association_decisions")
    op.drop_table("kubernetes_cluster_associations")
    op.drop_table("kubernetes_clusters")
    op.execute("DROP FUNCTION k8s_association_decision_guard()")
    op.execute("DROP FUNCTION k8s_cluster_identity_guard()")
    op.execute("DROP FUNCTION k8s_association_revision_guard()")
