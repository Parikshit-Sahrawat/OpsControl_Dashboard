"""Pentaho occurrence provenance and independent historical notice obligations.

Revision ID: 0035_pentaho_history
Revises: 0034_pentaho_review
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0035_pentaho_history"
down_revision = "0034_pentaho_review"
branch_labels = None
depends_on = None
STATEMENTS = [
    "\nCREATE TABLE pentaho_historical_notices (\n\tresource_id UUID NOT NULL, \n\thistory_id UUID NOT NULL, \n\tevent_id UUID NOT NULL, \n\tdestination_id UUID NOT NULL, \n\tpayload JSONB NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\tattempts INTEGER NOT NULL, \n\tlease_token UUID, \n\tlease_until TIMESTAMP WITH TIME ZONE, \n\tnext_attempt_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tsent_at TIMESTAMP WITH TIME ZONE, \n\tlast_error VARCHAR(160), \n\texternal_reference VARCHAR(500), \n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT fk_pentaho_notice_history FOREIGN KEY(organization_id, resource_id, history_id) REFERENCES job_order_histories (pentaho_customer_id, pentaho_resource_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT fk_pentaho_notice_event FOREIGN KEY(organization_id, resource_id, event_id) REFERENCES normalized_telemetry_events (organization_id, resource_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT fk_pentaho_notice_destination FOREIGN KEY(organization_id, destination_id) REFERENCES notification_destinations (organization_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT uq_pentaho_historical_obligation UNIQUE (history_id, destination_id), \n\tCONSTRAINT uq_pentaho_notice_scope UNIQUE (organization_id, id), \n\tCONSTRAINT ck_pentaho_notice_status CHECK (status IN ('PENDING','PROCESSING','SENT','FAILED','BLOCKED') AND attempts>=0), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n)\n\n",
    "CREATE INDEX ix_pentaho_notice_due ON pentaho_historical_notices (status, next_attempt_at)",
]


def upgrade():
    op.add_column(
        "expected_execution_windows",
        sa.Column("pentaho_authority", postgresql.JSONB(), nullable=True),
    )
    op.create_unique_constraint(
        "uq_notification_destination_scope",
        "notification_destinations",
        ["organization_id", "id"],
    )
    for statement in STATEMENTS:
        op.execute(sa.text(statement))
    op.add_column(
        "in_app_notifications",
        sa.Column("historical_notice_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.alter_column(
        "in_app_notifications",
        "delivery_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.create_foreign_key(
        "fk_in_app_historical_scope",
        "in_app_notifications",
        "pentaho_historical_notices",
        ["organization_id", "historical_notice_id"],
        ["organization_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_in_app_historical_user",
        "in_app_notifications",
        ["historical_notice_id", "user_id"],
    )
    op.create_check_constraint(
        "ck_in_app_notice_origin",
        "in_app_notifications",
        "(delivery_id IS NULL) <> (historical_notice_id IS NULL)",
    )
    op.execute(
        """CREATE FUNCTION pentaho_notice_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Pentaho historical notification evidence is protected'; END IF;
      IF (NEW.id,NEW.organization_id,NEW.resource_id,NEW.history_id,NEW.event_id,NEW.destination_id,NEW.payload,NEW.created_at) IS DISTINCT FROM (OLD.id,OLD.organization_id,OLD.resource_id,OLD.history_id,OLD.event_id,OLD.destination_id,OLD.payload,OLD.created_at)
      THEN RAISE EXCEPTION 'Pentaho historical notification evidence is immutable'; END IF;
      RETURN NEW;
    END $$"""
    )
    op.execute(
        "CREATE TRIGGER pentaho_notice_immutable BEFORE UPDATE OR DELETE ON pentaho_historical_notices FOR EACH ROW EXECUTE FUNCTION pentaho_notice_guard()"
    )
    op.execute(
        """CREATE FUNCTION pentaho_occurrence_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF OLD.pentaho_authority IS NOT NULL THEN
        IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Pentaho occurrence history is protected'; END IF;
        IF (NEW.id,NEW.organization_id,NEW.resource_id,NEW.scheduled_at,NEW.deadline,NEW.parameter_version,NEW.pentaho_authority) IS DISTINCT FROM (OLD.id,OLD.organization_id,OLD.resource_id,OLD.scheduled_at,OLD.deadline,OLD.parameter_version,OLD.pentaho_authority)
        THEN RAISE EXCEPTION 'Pentaho occurrence authority is immutable'; END IF;
      END IF;
      IF TG_OP='DELETE' THEN RETURN OLD; END IF;
      RETURN NEW;
    END $$"""
    )
    op.execute(
        "CREATE TRIGGER pentaho_occurrence_immutable BEFORE UPDATE OR DELETE ON expected_execution_windows FOR EACH ROW EXECUTE FUNCTION pentaho_occurrence_guard()"
    )
    op.execute(
        """CREATE FUNCTION pentaho_inbox_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF OLD.historical_notice_id IS NOT NULL THEN RAISE EXCEPTION 'Historical inbox evidence is protected'; END IF;
      IF TG_OP='DELETE' THEN RETURN OLD; END IF; RETURN NEW;
    END $$"""
    )
    op.execute(
        "CREATE TRIGGER pentaho_inbox_immutable BEFORE UPDATE OR DELETE ON in_app_notifications FOR EACH ROW EXECUTE FUNCTION pentaho_inbox_guard()"
    )
    for key, description in [
        (
            "etl.replay",
            "Request bounded Pentaho evidence reconciliation (explicit grant)",
        ),
        (
            "etl.approve_replay",
            "Independently approve high-risk Pentaho replay (explicit grant)",
        ),
    ]:
        op.execute(
            sa.text(
                "INSERT INTO permissions(key,description,delegable) VALUES(:key,:description,true) ON CONFLICT(key) DO NOTHING"
            ).bindparams(key=key, description=description)
        )


def downgrade():
    db = op.get_bind()
    if db.scalar(
        sa.text(
            "SELECT EXISTS(SELECT 1 FROM pentaho_historical_notices) OR EXISTS(SELECT 1 FROM expected_execution_windows WHERE pentaho_authority IS NOT NULL) OR EXISTS(SELECT 1 FROM pipeline_operations WHERE configuration->>'mode'='ACCEPTED_PENTAHO_EVIDENCE')"
        )
    ):
        raise RuntimeError(
            "Pentaho schedule/replay/notification evidence exists; retain schema or restore verified backup"
        )
    op.execute(
        "DELETE FROM permissions WHERE key IN ('etl.replay','etl.approve_replay')"
    )
    op.execute("DROP TRIGGER pentaho_inbox_immutable ON in_app_notifications")
    op.execute(
        "DROP TRIGGER pentaho_occurrence_immutable ON expected_execution_windows"
    )
    op.drop_constraint("ck_in_app_notice_origin", "in_app_notifications")
    op.drop_constraint("uq_in_app_historical_user", "in_app_notifications")
    op.drop_constraint("fk_in_app_historical_scope", "in_app_notifications")
    op.drop_column("in_app_notifications", "historical_notice_id")
    op.alter_column(
        "in_app_notifications",
        "delivery_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.drop_table("pentaho_historical_notices")
    op.drop_constraint("uq_notification_destination_scope", "notification_destinations")
    op.drop_column("expected_execution_windows", "pentaho_authority")
    for name in (
        "pentaho_notice_guard",
        "pentaho_occurrence_guard",
        "pentaho_inbox_guard",
    ):
        op.execute("DROP FUNCTION " + name + "()")
