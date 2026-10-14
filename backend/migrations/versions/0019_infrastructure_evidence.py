"""Persist scoped, sanitized infrastructure observations.

Revision ID: 0019_infrastructure_evidence
Revises: 0018_pentaho_execution_identity
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision='0019_infrastructure_evidence'
down_revision='0018_pentaho_execution_identity'
branch_labels=None
depends_on=None

def upgrade():
    op.add_column("data_sources",sa.Column("discovery_external_id",sa.String(512),nullable=True))
    op.create_unique_constraint("uq_data_source_org_discovery","data_sources",["organization_id","discovery_external_id"])
    # Preserve existing generated discovery inventory identities when still named by identity.
    op.execute("UPDATE data_sources SET discovery_external_id=name WHERE description='Approved read-only resource inventory; monitoring not yet activated' AND (name LIKE 'aws:%' OR name LIKE 'k8s:%')")
    op.create_table('infrastructure_evidence',
        sa.Column('id',postgresql.UUID(as_uuid=True),primary_key=True),
        sa.Column('organization_id',postgresql.UUID(as_uuid=True),sa.ForeignKey('organizations.id'),nullable=False),
        sa.Column('data_source_id',postgresql.UUID(as_uuid=True),sa.ForeignKey('data_sources.id'),nullable=False),
        sa.Column('collector_id',postgresql.UUID(as_uuid=True),sa.ForeignKey('collectors.id'),nullable=False),
        sa.Column('collector_run_id',postgresql.UUID(as_uuid=True),sa.ForeignKey('collector_runs.id',ondelete='CASCADE'),nullable=False,unique=True),
        sa.Column('observed_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('provider',sa.String(50),nullable=False),
        sa.Column('payload',sa.JSON(),nullable=False))
    for name in ('organization_id','data_source_id','collector_id'):
        op.create_index('ix_infrastructure_evidence_'+name,'infrastructure_evidence',[name])

def downgrade():
    op.drop_table('infrastructure_evidence')
    op.drop_constraint('uq_data_source_org_discovery','data_sources',type_='unique')
    op.drop_column('data_sources','discovery_external_id')
