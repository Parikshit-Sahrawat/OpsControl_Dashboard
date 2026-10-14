"""Store provider execution identity for idempotent ETL run ingestion.
Revision ID: 0018_pentaho_execution_identity
Revises: 0017_rule_catalogs_activation
"""
from alembic import op
import sqlalchemy as sa
revision="0018_pentaho_execution_identity"
down_revision="0017_rule_catalogs_activation"
branch_labels=None
depends_on=None
def upgrade():
    op.add_column("job_order_histories",sa.Column("provider_execution_id",sa.String(200),nullable=True))
    op.create_index("uq_etl_job_provider_execution","job_order_histories",
                    ["job_order_id","provider_execution_id"],unique=True)
def downgrade():
    op.drop_index("uq_etl_job_provider_execution",table_name="job_order_histories")
    op.drop_column("job_order_histories","provider_execution_id")
