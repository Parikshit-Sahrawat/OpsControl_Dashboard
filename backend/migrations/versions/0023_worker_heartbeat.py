"""Server-observed worker liveness; separate from health evidence.

Revision ID: 0023_worker_heartbeat
Revises: 0022_runtime_query_indexes
"""
from alembic import op
import sqlalchemy as sa
revision = '0023_worker_heartbeat'
down_revision = '0022_runtime_query_indexes'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('worker_identities', sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True))

def downgrade():
    op.drop_column('worker_identities', 'last_seen_at')
