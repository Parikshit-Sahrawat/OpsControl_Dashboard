"""Append-only source-owned template revisions; no historical backfill or purge."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision = "0042_source_configuration"
down_revision = "0041_etl_authority_writer"
branch_labels = depends_on = None


def upgrade():
    op.add_column(
        "data_sources",
        sa.Column(
            "configuration_revision", sa.Integer(), server_default="0", nullable=False
        ),
    )
    op.create_unique_constraint(
        "uq_data_source_configuration_owner", "data_sources", ["id", "organization_id"]
    )
    op.create_table(
        "source_configuration_revisions",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("data_source_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("previous_revision", sa.Integer()),
        sa.Column("restores_revision", sa.Integer()),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column(
            "actor_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("actor_name", sa.String(200), nullable=False),
        sa.Column("command_key", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("canonical_document", sa.Text(), nullable=False),
        sa.Column("document", pg.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["data_source_id", "organization_id"],
            ["data_sources.id", "data_sources.organization_id"],
            ondelete="RESTRICT",
            name="fk_source_revision_owner",
        ),
        sa.UniqueConstraint(
            "data_source_id", "revision", name="uq_source_configuration_revision"
        ),
        sa.UniqueConstraint(
            "data_source_id",
            "actor_id",
            "command_key",
            name="uq_source_configuration_command",
        ),
        sa.ForeignKeyConstraint(
            ["data_source_id", "previous_revision"],
            [
                "source_configuration_revisions.data_source_id",
                "source_configuration_revisions.revision",
            ],
            name="fk_source_revision_previous",
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.ForeignKeyConstraint(
            ["data_source_id", "restores_revision"],
            [
                "source_configuration_revisions.data_source_id",
                "source_configuration_revisions.revision",
            ],
            name="fk_source_revision_restore",
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.CheckConstraint(
            "revision > 0 AND (previous_revision IS NULL OR previous_revision = revision - 1)",
            name="ck_source_revision_sequence",
        ),
    )
    op.execute(
        """
    CREATE FUNCTION source_configuration_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN RAISE EXCEPTION 'Configuration history is append-only; rollback creates a new revision'; END $$;
    CREATE TRIGGER source_configuration_immutable BEFORE UPDATE OR DELETE ON source_configuration_revisions
      FOR EACH ROW EXECUTE FUNCTION source_configuration_immutable();
    CREATE TRIGGER source_template_version_immutable BEFORE UPDATE OR DELETE ON monitoring_template_versions
      FOR EACH ROW EXECUTE FUNCTION source_configuration_immutable();
    CREATE FUNCTION source_configuration_writer() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE sid uuid; fenced boolean;
    BEGIN
      IF TG_TABLE_NAME = 'data_sources' THEN
        sid := OLD.id;
        IF NEW.organization_id IS DISTINCT FROM OLD.organization_id AND OLD.configuration_revision > 0 THEN
          RAISE EXCEPTION 'Revisioned source ownership is immutable';
        END IF;
        fenced := OLD.configuration_revision > 0 AND (NEW.connection_config::jsonb IS DISTINCT FROM OLD.connection_config::jsonb OR NEW.source_type IS DISTINCT FROM OLD.source_type OR NEW.configuration_revision IS DISTINCT FROM OLD.configuration_revision);
      ELSE
        IF TG_OP = 'DELETE' THEN sid := OLD.data_source_id; ELSE sid := NEW.data_source_id; END IF;
        SELECT configuration_revision > 0 INTO fenced FROM data_sources WHERE id = sid FOR UPDATE;
        IF TG_OP = 'UPDATE' AND NEW.data_source_id IS DISTINCT FROM OLD.data_source_id THEN
          RAISE EXCEPTION 'Template attachment ownership is immutable';
        END IF;
      END IF;
      IF fenced AND current_setting('opscontrol.configuration_source', true) IS DISTINCT FROM sid::text THEN
        RAISE EXCEPTION 'LEGACY_WRITER_FENCED: use revision-checked source configuration command';
      END IF;
      IF TG_OP = 'DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
    END $$;
    CREATE TRIGGER source_configuration_writer BEFORE UPDATE ON data_sources FOR EACH ROW EXECUTE FUNCTION source_configuration_writer();
    CREATE TRIGGER source_configuration_writer BEFORE INSERT OR UPDATE OR DELETE ON monitoring_template_attachments FOR EACH ROW EXECUTE FUNCTION source_configuration_writer();
    CREATE FUNCTION source_configuration_head_check() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF NEW.configuration_revision > 0 AND NOT EXISTS (SELECT 1 FROM source_configuration_revisions WHERE data_source_id=NEW.id AND revision=NEW.configuration_revision AND organization_id=NEW.organization_id) THEN
        RAISE EXCEPTION 'Configuration head has no committed history';
      END IF;
      RETURN NEW;
    END $$;
    CREATE CONSTRAINT TRIGGER source_configuration_head_check AFTER UPDATE ON data_sources DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION source_configuration_head_check();
    """
    )


def downgrade():
    # Central preflight locks and refuses populated history before any DDL.
    op.execute("DROP TRIGGER source_configuration_head_check ON data_sources")
    op.execute("DROP TRIGGER source_configuration_writer ON data_sources")
    op.execute(
        "DROP TRIGGER source_configuration_writer ON monitoring_template_attachments"
    )
    op.execute(
        "DROP TRIGGER source_template_version_immutable ON monitoring_template_versions"
    )
    op.drop_table("source_configuration_revisions")
    for name in (
        "source_configuration_head_check",
        "source_configuration_writer",
        "source_configuration_immutable",
    ):
        op.execute(f"DROP FUNCTION {name}()")
    op.drop_constraint(
        "uq_data_source_configuration_owner", "data_sources", type_="unique"
    )
    op.drop_column("data_sources", "configuration_revision")
