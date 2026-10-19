"""Add immutable failure associations and independent recovery assessments."""

from alembic import op
import sqlalchemy as sa

revision = "0036_native_recovery"
down_revision = "0035_pentaho_history"
branch_labels = None
depends_on = None
STATEMENTS = [
    "\nCREATE TABLE native_incident_failures (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tincident_id UUID NOT NULL, \n\tresource_id UUID NOT NULL, \n\thistory_id UUID NOT NULL, \n\tevent_id UUID NOT NULL, \n\troot_key VARCHAR(64), \n\toccurred_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tdiscovered_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tevidence JSONB NOT NULL, \n\treassessment JSONB NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT fk_native_failure_incident FOREIGN KEY(organization_id, incident_id) REFERENCES operational_incidents (organization_id, id), \n\tCONSTRAINT fk_native_failure_history FOREIGN KEY(organization_id, resource_id, history_id) REFERENCES job_order_histories (pentaho_customer_id, pentaho_resource_id, id), \n\tCONSTRAINT fk_native_failure_event FOREIGN KEY(organization_id, resource_id, event_id) REFERENCES normalized_telemetry_events (organization_id, resource_id, id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tUNIQUE (event_id)\n)\n\n",
    "CREATE INDEX ix_native_incident_failures_history_id ON native_incident_failures (history_id)",
    "CREATE INDEX ix_native_incident_failures_incident_id ON native_incident_failures (incident_id)",
    "CREATE INDEX ix_native_incident_failures_organization_id ON native_incident_failures (organization_id)",
    "CREATE INDEX ix_native_incident_failures_root_key ON native_incident_failures (root_key)",
    "\nCREATE TABLE native_recovery_assessments (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tincident_id UUID NOT NULL, \n\tactor_id UUID NOT NULL, \n\trequest_key VARCHAR(120) NOT NULL, \n\trequest_hash VARCHAR(64) NOT NULL, \n\trevision INTEGER NOT NULL, \n\tresult VARCHAR(30) NOT NULL, \n\tassessed_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tevidence JSONB NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT fk_native_assessment_incident FOREIGN KEY(organization_id, incident_id) REFERENCES operational_incidents (organization_id, id), \n\tCONSTRAINT uq_native_assessment_request UNIQUE (organization_id, request_key), \n\tCONSTRAINT ck_native_assessment_result CHECK (revision > 0 AND result IN ('RECOVERY_CANDIDATE','VALIDATION_PENDING','VALIDATED_RECOVERY','VALIDATION_FAILED','INSUFFICIENT_EVIDENCE')), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tFOREIGN KEY(actor_id) REFERENCES users (id)\n)\n\n",
    "CREATE INDEX ix_native_recovery_assessments_incident_id ON native_recovery_assessments (incident_id)",
    "CREATE INDEX ix_native_recovery_assessments_organization_id ON native_recovery_assessments (organization_id)",
]


def upgrade():
    for statement in STATEMENTS:
        op.execute(sa.text(statement))
    op.execute(
        """CREATE FUNCTION native_recovery_evidence_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN RAISE EXCEPTION 'Native incident failure and recovery evidence is immutable and protected'; END $$"""
    )
    for table in ("native_incident_failures", "native_recovery_assessments"):
        op.execute(
            "CREATE TRIGGER native_recovery_immutable BEFORE UPDATE OR DELETE ON "
            + table
            + " FOR EACH ROW EXECUTE FUNCTION native_recovery_evidence_guard()"
        )


def downgrade():
    if op.get_bind().scalar(
        sa.text(
            "SELECT EXISTS(SELECT 1 FROM native_incident_failures) OR EXISTS(SELECT 1 FROM native_recovery_assessments)"
        )
    ):
        raise RuntimeError(
            "Native incident recovery evidence exists; retain schema or restore verified backup"
        )
    op.drop_table("native_recovery_assessments")
    op.drop_table("native_incident_failures")
    op.execute("DROP FUNCTION native_recovery_evidence_guard()")
