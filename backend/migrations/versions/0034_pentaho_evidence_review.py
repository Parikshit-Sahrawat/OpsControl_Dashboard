"""Append-only Pentaho evidence review; no history rewrite or automatic grants.

Revision ID: 0034_pentaho_review
Revises: 0033_pentaho_attempts
"""

from alembic import op
import sqlalchemy as sa

revision = "0034_pentaho_review"
down_revision = "0033_pentaho_attempts"
branch_labels = None
depends_on = None

STATEMENTS = [
    "\nCREATE TABLE pentaho_evidence_reviews (\n\tresource_id UUID NOT NULL, \n\tjob_order_id UUID NOT NULL, \n\thistory_id UUID, \n\tevent_id UUID NOT NULL, \n\tsource_evidence_id UUID, \n\tcategory VARCHAR(40) NOT NULL, \n\tclaim VARCHAR(40) NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\trevision INTEGER NOT NULL, \n\tcontext JSONB NOT NULL, \n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT fk_pentaho_review_resource FOREIGN KEY(organization_id, resource_id, job_order_id) REFERENCES monitoring_resources (organization_id, id, job_order_id) ON DELETE RESTRICT, \n\tCONSTRAINT fk_pentaho_review_history FOREIGN KEY(job_order_id, history_id) REFERENCES job_order_histories (job_order_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT fk_pentaho_review_event FOREIGN KEY(organization_id, resource_id, event_id) REFERENCES normalized_telemetry_events (organization_id, resource_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT fk_pentaho_review_raw FOREIGN KEY(organization_id, source_evidence_id) REFERENCES pipeline_evidence (organization_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT uq_pentaho_review_event_category UNIQUE (event_id, category), \n\tCONSTRAINT uq_pentaho_review_scope UNIQUE (organization_id, resource_id, id), \n\tCONSTRAINT ck_pentaho_review_category CHECK (category IN ('AMBIGUOUS_IDENTITY','NATIVE_ALIAS_CONFLICT','RETRY_RELATIONSHIP','EXECUTION_OUTCOME','LEGACY_ADOPTION','RECOVERY_IDENTITY')), \n\tCONSTRAINT ck_pentaho_review_status CHECK (status IN ('OPEN','ACCEPTED','REJECTED') AND revision >= 1), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n)\n\n",
    "CREATE INDEX ix_pentaho_review_queue ON pentaho_evidence_reviews (organization_id, resource_id, status, created_at)",
    "CREATE INDEX ix_pentaho_review_raw ON pentaho_evidence_reviews (source_evidence_id)",
    "\nCREATE TABLE pentaho_evidence_decisions (\n\tresource_id UUID NOT NULL, \n\treview_id UUID NOT NULL, \n\trevision INTEGER NOT NULL, \n\tactor_id UUID NOT NULL, \n\taction VARCHAR(30) NOT NULL, \n\treason TEXT NOT NULL, \n\trequest_key VARCHAR(100) NOT NULL, \n\trequest_hash VARCHAR(64) NOT NULL, \n\tevidence JSONB NOT NULL, \n\tprojection_before JSONB NOT NULL, \n\tprojection_after JSONB NOT NULL, \n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT fk_pentaho_decision_review FOREIGN KEY(organization_id, resource_id, review_id) REFERENCES pentaho_evidence_reviews (organization_id, resource_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT uq_pentaho_evidence_decision_revision UNIQUE (review_id, revision), \n\tCONSTRAINT uq_pentaho_evidence_decision_request UNIQUE (organization_id, request_key), \n\tCONSTRAINT ck_pentaho_evidence_decision_action CHECK (action IN ('DEFER','REJECT_CLAIM','ACCEPT_VERIFIED_CLAIM','ADOPT_LEGACY')), \n\tFOREIGN KEY(actor_id) REFERENCES users (id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n)\n\n",
]


def upgrade():
    op.add_column(
        "job_order_histories",
        sa.Column("pentaho_review_state", sa.String(25), nullable=True),
    )
    op.create_unique_constraint(
        "uq_pentaho_history_job", "job_order_histories", ["job_order_id", "id"]
    )
    for statement in STATEMENTS:
        op.execute(sa.text(statement))
    op.execute(
        "CREATE TRIGGER pentaho_evidence_decisions_immutable BEFORE UPDATE OR DELETE ON pentaho_evidence_decisions FOR EACH ROW EXECUTE FUNCTION pentaho_append_only()"
    )
    op.execute(
        """CREATE FUNCTION pentaho_review_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Pentaho evidence review is protected'; END IF;
      IF (NEW.organization_id,NEW.resource_id,NEW.job_order_id,NEW.history_id,NEW.event_id,NEW.source_evidence_id,NEW.category,NEW.claim,NEW.context,NEW.created_at,NEW.id) IS DISTINCT FROM
         (OLD.organization_id,OLD.resource_id,OLD.job_order_id,OLD.history_id,OLD.event_id,OLD.source_evidence_id,OLD.category,OLD.claim,OLD.context,OLD.created_at,OLD.id)
      THEN RAISE EXCEPTION 'Pentaho evidence review identity/context is immutable'; END IF;
      RETURN NEW;
    END $$"""
    )
    op.execute(
        "CREATE TRIGGER pentaho_evidence_review_identity BEFORE UPDATE OR DELETE ON pentaho_evidence_reviews FOR EACH ROW EXECUTE FUNCTION pentaho_review_guard()"
    )
    # Catalog only: existing employees, department roles and customer grants
    # receive NO implicit privilege. Platform break-glass already bypasses RBAC.
    op.execute(
        "INSERT INTO permissions(key,description,delegable) VALUES ('etl.resolve_identity','Adjudicate verified Pentaho evidence and native identity (explicit grant)',true) ON CONFLICT (key) DO NOTHING"
    )


def downgrade():
    db = op.get_bind()
    if db.scalar(
        sa.text(
            "SELECT EXISTS(SELECT 1 FROM pentaho_evidence_reviews) OR EXISTS(SELECT 1 FROM pentaho_evidence_decisions)"
        )
    ):
        raise RuntimeError(
            "Pentaho evidence review/decisions exist; retain schema or restore verified backup"
        )
    if db.scalar(
        sa.text(
            "SELECT EXISTS(SELECT 1 FROM role_permissions WHERE permission_key='etl.resolve_identity')"
        )
    ):
        raise RuntimeError(
            "Pentaho review permission is assigned; retain schema or remove grants through authorized access management"
        )
    # Other permission-reference FKs also fail closed, transactionally.
    op.execute("DELETE FROM permissions WHERE key='etl.resolve_identity'")
    op.drop_table("pentaho_evidence_decisions")
    op.drop_table("pentaho_evidence_reviews")
    op.execute("DROP FUNCTION pentaho_review_guard()")
    op.drop_constraint("uq_pentaho_history_job", "job_order_histories")
    op.drop_column("job_order_histories", "pentaho_review_state")
