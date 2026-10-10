"""Tenant-bound leased remote HTTP jobs and idempotent evidence.
Revision ID: 0015_remote_jobs
Revises: 0014_audit_mutation_guard
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision="0015_remote_jobs"
down_revision="0014_audit_mutation_guard"
branch_labels=None
depends_on=None

def upgrade():
    op.add_column("worker_identities",sa.Column("allowed_hosts",postgresql.JSONB(),nullable=False,server_default=sa.text("'[]'::jsonb")))
    op.add_column("worker_identities",sa.Column("allowed_cidrs",postgresql.JSONB(),nullable=False,server_default=sa.text("'[]'::jsonb")))
    op.create_table("remote_probe_jobs",
        sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),
        sa.Column("organization_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("organizations.id",ondelete="CASCADE"),nullable=False),
        sa.Column("collector_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("collectors.id",ondelete="CASCADE"),nullable=False),
        sa.Column("assigned_worker_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("worker_identities.id",ondelete="CASCADE"),nullable=False),
        sa.Column("planned_for",sa.DateTime(timezone=True),nullable=False),
        sa.Column("config_snapshot",postgresql.JSONB(),nullable=False),
        sa.Column("state",sa.String(24),nullable=False,server_default="QUEUED"),
        sa.Column("attempts",sa.Integer(),nullable=False,server_default="0"),
        sa.Column("lease_nonce_hash",sa.String(64),nullable=True),
        sa.Column("lease_expires_at",sa.DateTime(timezone=True),nullable=True),
        sa.Column("run_id",postgresql.UUID(as_uuid=True),nullable=True),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.Column("completed_at",sa.DateTime(timezone=True),nullable=True),
        sa.UniqueConstraint("collector_id","planned_for",name="uq_remote_collector_planned"),
        sa.CheckConstraint("attempts >= 0 AND attempts <= 3",name="ck_remote_job_attempts"))
    op.create_index("ix_remote_job_worker_state", "remote_probe_jobs",["assigned_worker_id","state","planned_for"])
    op.create_index("ix_remote_job_org_id","remote_probe_jobs",["organization_id"])
    op.create_table("remote_probe_evidence",
        sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),
        sa.Column("event_id",postgresql.UUID(as_uuid=True),nullable=False,unique=True),
        sa.Column("job_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("remote_probe_jobs.id",ondelete="CASCADE"),nullable=False,unique=True),
        sa.Column("organization_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("organizations.id",ondelete="CASCADE"),nullable=False),
        sa.Column("worker_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("worker_identities.id"),nullable=False),
        sa.Column("observed_at",sa.DateTime(timezone=True),nullable=False),
        sa.Column("result",postgresql.JSONB(),nullable=False),
        sa.Column("payload_sha256",sa.String(64),nullable=False),
        sa.Column("received_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_remote_evidence_org_observed","remote_probe_evidence",["organization_id","observed_at"])

def downgrade():
    op.drop_table("remote_probe_evidence")
    op.drop_table("remote_probe_jobs")
    op.drop_column("worker_identities","allowed_cidrs")
    op.drop_column("worker_identities","allowed_hosts")
