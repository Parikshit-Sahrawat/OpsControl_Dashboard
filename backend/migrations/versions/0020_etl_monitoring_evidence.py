"""Scoped ETL source evidence and explicit infrastructure association."""
from alembic import op
import sqlalchemy as sa
revision = '0020_etl_monitoring_evidence'
down_revision = '0019_infrastructure_evidence'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('job_orders', sa.Column('host_data_source_id', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_job_order_host_source', 'job_orders', 'data_sources', ['host_data_source_id'], ['id'])
    op.add_column('job_order_histories', sa.Column('source_evidence', sa.JSON(), nullable=True))

def downgrade():
    op.drop_column('job_order_histories', 'source_evidence')
    op.drop_constraint('fk_job_order_host_source', 'job_orders', type_='foreignkey')
    op.drop_column('job_orders', 'host_data_source_id')
