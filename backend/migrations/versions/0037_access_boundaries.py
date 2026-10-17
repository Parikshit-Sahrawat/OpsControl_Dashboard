"""Add explicit access boundaries without granting authority or rewriting history."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "0037_access_boundaries"
down_revision = "0036_native_recovery"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "access_boundaries",
        sa.Column("id", UUID(), primary_key=True),
        sa.Column(
            "service_provider_id",
            UUID(),
            sa.ForeignKey("service_providers.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("user_id", UUID()),
        sa.Column("department_id", UUID()),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("specification", JSONB(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "(user_id IS NULL) <> (department_id IS NULL)", name="ck_boundary_subject"
        ),
        sa.CheckConstraint(
            "kind IN ('LIMIT','DENY','DELEGATE','ALL_CUSTOMERS') AND revision > 0",
            name="ck_boundary_kind",
        ),
        sa.CheckConstraint(
            "kind != 'DELEGATE' OR user_id IS NOT NULL",
            name="ck_boundary_delegate_employee",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(specification) = 'object'", name="ck_boundary_specification"
        ),
        sa.ForeignKeyConstraint(
            ["user_id", "service_provider_id"],
            ["users.id", "users.service_provider_id"],
            name="fk_boundary_user",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["department_id", "service_provider_id"],
            ["departments.id", "departments.service_provider_id"],
            name="fk_boundary_department",
            ondelete="RESTRICT",
        ),
    )
    for col in ["service_provider_id", "user_id", "department_id"]:
        op.create_index("ix_access_boundaries_" + col, "access_boundaries", [col])
    op.create_table(
        "access_boundary_decisions",
        sa.Column("id", UUID(), primary_key=True),
        sa.Column(
            "boundary_id",
            UUID(),
            sa.ForeignKey("access_boundaries.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "actor_id",
            UUID(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("request_key", sa.String(120), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("reason", sa.String(2000), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("evidence", JSONB(), nullable=False),
        sa.UniqueConstraint(
            "actor_id", "request_key", name="uq_boundary_decision_request"
        ),
        sa.CheckConstraint("revision > 0", name="ck_boundary_decision_revision"),
    )
    op.execute(
        """CREATE FUNCTION access_boundary_audit_guard() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Access boundary decision history is immutable'; END $$"""
    )
    op.execute(
        "CREATE TRIGGER access_boundary_audit_immutable BEFORE UPDATE OR DELETE ON access_boundary_decisions FOR EACH ROW EXECUTE FUNCTION access_boundary_audit_guard()"
    )


def downgrade():
    if op.get_bind().scalar(
        sa.text(
            "SELECT EXISTS(SELECT 1 FROM access_boundaries) OR EXISTS(SELECT 1 FROM access_boundary_decisions)"
        )
    ):
        raise RuntimeError(
            "Access boundaries or decisions exist; preserve authorization/audit schema or restore a verified backup"
        )
    op.drop_table("access_boundary_decisions")
    op.drop_table("access_boundaries")
    op.execute("DROP FUNCTION access_boundary_audit_guard()")
