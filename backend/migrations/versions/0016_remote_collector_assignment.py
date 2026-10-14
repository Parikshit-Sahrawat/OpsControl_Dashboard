"""Bind collectors to authorized remote worker and isolate local scheduler.
Revision ID: 0016_remote_collector_assignment
Revises: 0015_remote_jobs
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision="0016_remote_collector_assignment"
down_revision="0015_remote_jobs"
branch_labels=None
depends_on=None

def upgrade():
    op.add_column("collectors",sa.Column("remote_worker_id",postgresql.UUID(as_uuid=True),
         sa.ForeignKey("worker_identities.id",ondelete="SET NULL"),nullable=True))
    op.create_index("ix_collectors_remote_worker_id","collectors",["remote_worker_id"])

def downgrade():
    op.drop_index("ix_collectors_remote_worker_id",table_name="collectors")
    op.drop_column("collectors","remote_worker_id")
