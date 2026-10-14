"""Rate limits, security audit and explicit agent identities.

Revision ID: 0013_security_controls
Revises: 0012_identity_and_memberships
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0013_security_controls"
down_revision = "0012_identity_and_memberships"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("auth_throttle_buckets",
        sa.Column("key_hash", sa.String(64), primary_key=True),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"))
    op.create_table("security_audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_type", sa.String(80), nullable=True),
        sa.Column("target_id", sa.String(120), nullable=True),
        sa.Column("outcome", sa.String(20), nullable=False),
        sa.Column("request_id", sa.String(100), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_security_audit_occurred_at", "security_audit_events", ["occurred_at"])
    op.create_index("ix_security_audit_actor_id", "security_audit_events", ["actor_id"])
    op.create_index("ix_security_audit_organization_id", "security_audit_events", ["organization_id"])
    op.create_table("worker_identities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "name", name="uq_worker_org_name"))
    op.create_index("ix_worker_identities_organization_id", "worker_identities", ["organization_id"])

def downgrade():
    op.drop_table("worker_identities")
    op.drop_table("security_audit_events")
    op.drop_table("auth_throttle_buckets")
