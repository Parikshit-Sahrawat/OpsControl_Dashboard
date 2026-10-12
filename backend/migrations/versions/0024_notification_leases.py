"""Short delivery claims and fencing for multi-replica external notifications.

Revision ID: 0024_notification_leases
Revises: 0023_worker_heartbeat
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision = '0024_notification_leases'
down_revision = '0023_worker_heartbeat'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('alert_notification_deliveries',sa.Column('lease_token',postgresql.UUID(as_uuid=True),nullable=True))
    op.add_column('alert_notification_deliveries',sa.Column('lease_expires_at',sa.DateTime(timezone=True),nullable=True))

def downgrade():
    op.drop_column('alert_notification_deliveries','lease_expires_at')
    op.drop_column('alert_notification_deliveries','lease_token')
