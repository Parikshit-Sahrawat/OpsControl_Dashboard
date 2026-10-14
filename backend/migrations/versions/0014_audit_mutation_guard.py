"""Reject accidental UPDATE/DELETE of security audit history at SQL level.

This is defense in depth, NOT cryptographic immutability: a database owner
can disable triggers. Keep application database permissions least-privilege.
Revision ID: 0014_audit_mutation_guard
Revises: 0013_security_controls
"""
from alembic import op

revision = "0014_audit_mutation_guard"
down_revision = "0013_security_controls"
branch_labels = None
depends_on = None

def upgrade():
    op.execute("""
        CREATE FUNCTION opscontrol_reject_audit_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'Security audit events are append-only';
        END;
        $$
    """)
    op.execute("""
        CREATE TRIGGER opscontrol_audit_append_only
        BEFORE UPDATE OR DELETE ON security_audit_events
        FOR EACH ROW EXECUTE FUNCTION opscontrol_reject_audit_mutation()
    """)

def downgrade():
    op.execute("DROP TRIGGER opscontrol_audit_append_only ON security_audit_events")
    op.execute("DROP FUNCTION opscontrol_reject_audit_mutation()")
