"""Indexes for scheduler selection and deterministic newest-evidence lookups.

Revision ID: 0022_runtime_query_indexes
Revises: 0021_operational_incidents
"""
from alembic import op

revision = "0022_runtime_query_indexes"
down_revision = "0021_operational_incidents"
branch_labels = None
depends_on = None

def upgrade():
    # Concurrent builds avoid blocking collector writes on populated databases.
    with op.get_context().autocommit_block():
        op.execute("CREATE INDEX CONCURRENTLY ix_collectors_due_local ON collectors (next_run_at, id) WHERE enabled AND remote_worker_id IS NULL")
        op.execute("CREATE INDEX CONCURRENTLY ix_collector_runs_latest ON collector_runs (collector_id, started_at DESC, id DESC)")
        op.execute("CREATE INDEX CONCURRENTLY ix_infra_evidence_latest ON infrastructure_evidence (collector_id, observed_at DESC, id DESC)")
        op.execute("CREATE INDEX CONCURRENTLY ix_security_audit_occurred ON security_audit_events (occurred_at, id)")

def downgrade():
    with op.get_context().autocommit_block():
        for index in ('ix_security_audit_occurred', 'ix_infra_evidence_latest', 'ix_collector_runs_latest', 'ix_collectors_due_local'):
            op.execute(f"DROP INDEX CONCURRENTLY {index}")
