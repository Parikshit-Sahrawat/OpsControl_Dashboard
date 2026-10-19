"""Add scoped Pentaho identity/attempt/recovery extensions without rewriting history."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0033_pentaho_attempts"
down_revision = "0032_pipeline_ownership"
branch_labels = None
depends_on = None

TABLES = [
    "pentaho_execution_attempts",
    "pentaho_native_aliases",
    "pentaho_attempt_revisions",
    "pentaho_recovery_links",
    "pentaho_recovery_decisions",
]
STATEMENTS = [
    "\nCREATE TABLE pentaho_execution_attempts (\n\tresource_id UUID NOT NULL, \n\thistory_id UUID NOT NULL, \n\tattempt_key VARCHAR(100) NOT NULL, \n\tattempt_order INTEGER NOT NULL, \n\tnative_identity JSONB NOT NULL, \n\toutcome VARCHAR(20) NOT NULL, \n\tcompleteness VARCHAR(20) NOT NULL, \n\tstarted_at TIMESTAMP WITH TIME ZONE, \n\tended_at TIMESTAMP WITH TIME ZONE, \n\tretry_authority JSONB NOT NULL, \n\trevision INTEGER NOT NULL, \n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT fk_pentaho_attempt_history_scope FOREIGN KEY(organization_id, resource_id, history_id) REFERENCES job_order_histories (pentaho_customer_id, pentaho_resource_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT uq_pentaho_attempt_key UNIQUE (organization_id, resource_id, attempt_key), \n\tCONSTRAINT uq_pentaho_attempt_order UNIQUE (history_id, attempt_order), \n\tCONSTRAINT uq_pentaho_attempt_scope UNIQUE (organization_id, resource_id, history_id, id), \n\tCONSTRAINT ck_pentaho_attempt_order CHECK (attempt_order BETWEEN 1 AND 10000), \n\tCONSTRAINT ck_pentaho_attempt_outcome CHECK (outcome IN ('RUNNING','SUCCESS','FAILED','CANCELLED','UNKNOWN')), \n\tCONSTRAINT ck_pentaho_attempt_completeness CHECK (completeness IN ('PARTIAL','COMPLETE','UNKNOWN')), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n)\n\n",
    "\nCREATE TABLE pentaho_native_aliases (\n\tresource_id UUID NOT NULL, \n\thistory_id UUID NOT NULL, \n\tattempt_id UUID, \n\talias_key VARCHAR(100) NOT NULL, \n\tkind VARCHAR(25) NOT NULL, \n\tnative_identity JSONB NOT NULL, \n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT fk_pentaho_alias_history_scope FOREIGN KEY(organization_id, resource_id, history_id) REFERENCES job_order_histories (pentaho_customer_id, pentaho_resource_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT fk_pentaho_alias_attempt_scope FOREIGN KEY(organization_id, resource_id, history_id, attempt_id) REFERENCES pentaho_execution_attempts (organization_id, resource_id, history_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT uq_pentaho_native_alias UNIQUE (organization_id, resource_id, alias_key), \n\tCONSTRAINT ck_pentaho_alias_kind CHECK (kind IN ('INVOCATION','LOGICAL','SCHEDULER_ATTEMPT')), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n)\n\n",
    "\nCREATE TABLE pentaho_attempt_revisions (\n\tresource_id UUID NOT NULL, \n\thistory_id UUID NOT NULL, \n\tattempt_id UUID NOT NULL, \n\tevent_id UUID NOT NULL, \n\tsource_evidence_id UUID, \n\trevision INTEGER NOT NULL, \n\tobservation_key VARCHAR(64) NOT NULL, \n\tdisposition VARCHAR(30) NOT NULL, \n\tpayload JSONB NOT NULL, \n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT fk_pentaho_revision_history_scope FOREIGN KEY(organization_id, resource_id, history_id) REFERENCES job_order_histories (pentaho_customer_id, pentaho_resource_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT fk_pentaho_revision_attempt_scope FOREIGN KEY(organization_id, resource_id, history_id, attempt_id) REFERENCES pentaho_execution_attempts (organization_id, resource_id, history_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT fk_pentaho_revision_event_scope FOREIGN KEY(organization_id, resource_id, event_id) REFERENCES normalized_telemetry_events (organization_id, resource_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT fk_pentaho_revision_raw_scope FOREIGN KEY(organization_id, source_evidence_id) REFERENCES pipeline_evidence (organization_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT uq_pentaho_attempt_revision UNIQUE (attempt_id, revision), \n\tCONSTRAINT uq_pentaho_revision_event UNIQUE (event_id), \n\tCONSTRAINT uq_pentaho_observation UNIQUE (attempt_id, observation_key), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n)\n\n",
    "\nCREATE TABLE pentaho_recovery_links (\n\tfailed_history_id UUID NOT NULL, \n\trecovery_history_id UUID NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\trevision INTEGER NOT NULL, \n\tproposed_by UUID NOT NULL, \n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT fk_pentaho_recovery_failed_scope FOREIGN KEY(organization_id, failed_history_id) REFERENCES job_order_histories (pentaho_customer_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT fk_pentaho_recovery_run_scope FOREIGN KEY(organization_id, recovery_history_id) REFERENCES job_order_histories (pentaho_customer_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT uq_pentaho_recovery_pair UNIQUE (failed_history_id, recovery_history_id), \n\tCONSTRAINT uq_pentaho_recovery_scope UNIQUE (organization_id, id), \n\tCONSTRAINT ck_pentaho_recovery_not_self CHECK (failed_history_id <> recovery_history_id), \n\tCONSTRAINT ck_pentaho_recovery_status CHECK (status IN ('PROPOSED','CONFIRMED','REVERSED')), \n\tFOREIGN KEY(proposed_by) REFERENCES users (id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n)\n\n",
    "\nCREATE TABLE pentaho_recovery_decisions (\n\tlink_id UUID NOT NULL, \n\trevision INTEGER NOT NULL, \n\taction VARCHAR(20) NOT NULL, \n\tactor_id UUID NOT NULL, \n\trequest_key VARCHAR(100) NOT NULL, \n\trequest_hash VARCHAR(64) NOT NULL, \n\treason TEXT NOT NULL, \n\tevidence JSONB NOT NULL, \n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT fk_pentaho_recovery_decision_scope FOREIGN KEY(organization_id, link_id) REFERENCES pentaho_recovery_links (organization_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT uq_pentaho_recovery_decision_revision UNIQUE (link_id, revision), \n\tCONSTRAINT uq_pentaho_recovery_request UNIQUE (organization_id, request_key), \n\tCONSTRAINT ck_pentaho_recovery_action CHECK (action IN ('PROPOSE','CONFIRM','REVERSE')), \n\tFOREIGN KEY(actor_id) REFERENCES users (id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n)\n\n",
    "CREATE INDEX ix_pentaho_alias_attempt ON pentaho_native_aliases (attempt_id)",
    "CREATE INDEX ix_pentaho_revision_raw_evidence ON pentaho_attempt_revisions (source_evidence_id)",
    "CREATE INDEX ix_pentaho_recovery_target ON pentaho_recovery_links (recovery_history_id)",
]


def upgrade():
    for name in ("pentaho_customer_id", "pentaho_resource_id"):
        op.add_column(
            "job_order_histories",
            sa.Column(name, postgresql.UUID(as_uuid=True), nullable=True),
        )
    for name, length in (
        ("pentaho_lifecycle", 25),
        ("pentaho_outcome", 25),
        ("pentaho_completeness", 20),
        ("pentaho_identity_state", 25),
    ):
        op.add_column(
            "job_order_histories", sa.Column(name, sa.String(length), nullable=True)
        )
    op.add_column(
        "job_order_histories",
        sa.Column("pentaho_schedule_occurrence", postgresql.JSONB(), nullable=True),
    )
    op.create_unique_constraint(
        "uq_resource_job_scope",
        "monitoring_resources",
        ["organization_id", "id", "job_order_id"],
    )
    op.create_unique_constraint(
        "uq_normalized_event_scope",
        "normalized_telemetry_events",
        ["organization_id", "resource_id", "id"],
    )
    op.create_unique_constraint(
        "uq_pentaho_history_customer",
        "job_order_histories",
        ["pentaho_customer_id", "id"],
    )
    op.create_unique_constraint(
        "uq_pentaho_history_scope",
        "job_order_histories",
        ["pentaho_customer_id", "pentaho_resource_id", "id"],
    )
    op.create_foreign_key(
        "fk_pentaho_history_resource_scope",
        "job_order_histories",
        "monitoring_resources",
        ["pentaho_customer_id", "pentaho_resource_id", "job_order_id"],
        ["organization_id", "id", "job_order_id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_pentaho_lifecycle",
        "job_order_histories",
        "pentaho_lifecycle IS NULL OR pentaho_lifecycle IN ('IDENTIFIED','RUNNING','WAITING_FOR_RETRY','TERMINAL')",
    )
    op.create_check_constraint(
        "ck_pentaho_outcome",
        "job_order_histories",
        "pentaho_outcome IS NULL OR pentaho_outcome IN ('SUCCESS','SUCCESS_AFTER_RETRY','FAILED','CANCELLED','UNKNOWN')",
    )
    op.create_check_constraint(
        "ck_pentaho_history_binding",
        "job_order_histories",
        "(pentaho_resource_id IS NULL AND pentaho_customer_id IS NULL AND pentaho_lifecycle IS NULL) OR (pentaho_resource_id IS NOT NULL AND pentaho_customer_id IS NOT NULL AND pentaho_lifecycle IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_pentaho_terminal_outcome",
        "job_order_histories",
        "pentaho_outcome IS NULL OR pentaho_lifecycle='TERMINAL'",
    )
    for statement in STATEMENTS:
        op.execute(sa.text(statement))
    op.execute(
        """CREATE FUNCTION pentaho_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN RAISE EXCEPTION 'Pentaho immutable identity/evidence/decision is protected'; END $$"""
    )
    for table in (
        "pentaho_native_aliases",
        "pentaho_attempt_revisions",
        "pentaho_recovery_decisions",
    ):
        op.execute(
            f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION pentaho_append_only()"
        )
    op.execute(
        """CREATE FUNCTION pentaho_attempt_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Pentaho attempt history is protected'; END IF;
      IF (NEW.organization_id,NEW.resource_id,NEW.history_id,NEW.attempt_key,NEW.attempt_order,NEW.native_identity) IS DISTINCT FROM
         (OLD.organization_id,OLD.resource_id,OLD.history_id,OLD.attempt_key,OLD.attempt_order,OLD.native_identity)
      THEN RAISE EXCEPTION 'Pentaho attempt identity is immutable'; END IF;
      RETURN NEW;
    END $$"""
    )
    op.execute(
        "CREATE TRIGGER pentaho_attempt_identity BEFORE UPDATE OR DELETE ON pentaho_execution_attempts FOR EACH ROW EXECUTE FUNCTION pentaho_attempt_guard()"
    )
    op.execute(
        """CREATE FUNCTION pentaho_history_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP='DELETE' THEN
        IF OLD.pentaho_resource_id IS NOT NULL THEN RAISE EXCEPTION 'Pentaho history is protected'; END IF;
        RETURN OLD;
      END IF;
      IF OLD.pentaho_resource_id IS NOT NULL AND (NEW.pentaho_customer_id,NEW.pentaho_resource_id,NEW.job_order_id,NEW.provider_execution_id) IS DISTINCT FROM (OLD.pentaho_customer_id,OLD.pentaho_resource_id,OLD.job_order_id,OLD.provider_execution_id)
      THEN RAISE EXCEPTION 'Pentaho logical execution identity is immutable'; END IF;
      RETURN NEW;
    END $$"""
    )
    op.execute(
        "CREATE TRIGGER pentaho_history_identity BEFORE UPDATE OR DELETE ON job_order_histories FOR EACH ROW EXECUTE FUNCTION pentaho_history_guard()"
    )
    op.execute(
        """CREATE FUNCTION pentaho_event_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF OLD.payload ? 'pentaho_identity' THEN
        IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Pentaho source evidence is protected'; END IF;
        IF NEW.payload IS DISTINCT FROM OLD.payload THEN RAISE EXCEPTION 'Pentaho source evidence is immutable'; END IF;
      END IF;
      IF TG_OP='DELETE' THEN RETURN OLD; END IF;
      RETURN NEW;
    END $$"""
    )
    op.execute(
        "CREATE TRIGGER pentaho_event_immutable BEFORE UPDATE OR DELETE ON normalized_telemetry_events FOR EACH ROW EXECUTE FUNCTION pentaho_event_guard()"
    )


def downgrade():
    db = op.get_bind()
    if db.scalar(
        sa.text(
            "SELECT EXISTS(SELECT 1 FROM job_order_histories WHERE pentaho_resource_id IS NOT NULL)"
        )
    ) or any(
        db.scalar(sa.text("SELECT EXISTS(SELECT 1 FROM " + table + ")"))
        for table in TABLES
    ):
        raise RuntimeError(
            "Pentaho attempts/identity/evidence/recovery exist; retain schema or restore verified backup"
        )
    op.execute("DROP TRIGGER pentaho_event_immutable ON normalized_telemetry_events")
    op.execute("DROP TRIGGER pentaho_history_identity ON job_order_histories")
    for table in reversed(TABLES):
        op.drop_table(table)
    for function in (
        "pentaho_append_only",
        "pentaho_attempt_guard",
        "pentaho_history_guard",
        "pentaho_event_guard",
    ):
        op.execute("DROP FUNCTION " + function + "()")
    for name in (
        "ck_pentaho_lifecycle",
        "ck_pentaho_outcome",
        "ck_pentaho_history_binding",
        "ck_pentaho_terminal_outcome",
        "fk_pentaho_history_resource_scope",
        "uq_pentaho_history_scope",
        "uq_pentaho_history_customer",
    ):
        op.drop_constraint(name, "job_order_histories")
    op.drop_constraint("uq_resource_job_scope", "monitoring_resources")
    op.drop_constraint("uq_normalized_event_scope", "normalized_telemetry_events")
    for name in (
        "pentaho_customer_id",
        "pentaho_resource_id",
        "pentaho_lifecycle",
        "pentaho_outcome",
        "pentaho_completeness",
        "pentaho_identity_state",
        "pentaho_schedule_occurrence",
    ):
        op.drop_column("job_order_histories", name)
