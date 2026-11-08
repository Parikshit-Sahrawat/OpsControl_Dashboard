"""Fence metadata/auth-mode writers after source configuration cutover.

Revision ID: 0043_source_context_fence
Revises: 0042_source_configuration
"""

from alembic import op
from sqlalchemy import text

revision = "0043_source_context_fence"
down_revision = "0042_source_configuration"
branch_labels = None
depends_on = None


def writer(extra):
    # Preserve0042 tenant/attachment checks; add context fields without rewriting
    # an applied migration or changing stored rows/history.
    op.execute(
        """
    CREATE OR REPLACE FUNCTION source_configuration_writer() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE sid uuid; fenced boolean;
    BEGIN
      IF TG_TABLE_NAME = 'data_sources' THEN
        sid := OLD.id;
        IF NEW.organization_id IS DISTINCT FROM OLD.organization_id AND OLD.configuration_revision > 0 THEN
          RAISE EXCEPTION 'Revisioned source ownership is immutable';
        END IF;
        fenced := OLD.configuration_revision > 0 AND (NEW.connection_config::jsonb IS DISTINCT FROM OLD.connection_config::jsonb OR NEW.source_type IS DISTINCT FROM OLD.source_type OR NEW.endpoint IS DISTINCT FROM OLD.endpoint OR NEW.configuration_revision IS DISTINCT FROM OLD.configuration_revision"""
        + extra
        + """);
      ELSE
        IF TG_OP = 'DELETE' THEN sid := OLD.data_source_id; ELSE sid := NEW.data_source_id; END IF;
        PERFORM 1 FROM data_sources WHERE id = sid FOR UPDATE;
        fenced := true;
        IF TG_OP = 'UPDATE' AND NEW.data_source_id IS DISTINCT FROM OLD.data_source_id THEN
          RAISE EXCEPTION 'Template attachment ownership is immutable';
        END IF;
      END IF;
      IF fenced AND current_setting('opscontrol.configuration_source', true) IS DISTINCT FROM sid::text THEN
        RAISE EXCEPTION 'LEGACY_WRITER_FENCED: use revision-checked source configuration command';
      END IF;
      IF TG_OP = 'DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
      RETURN NEW;
    END $$;
    """
    )


def upgrade():
    writer(
        " OR NEW.name IS DISTINCT FROM OLD.name OR NEW.description IS DISTINCT FROM OLD.description OR NEW.auth_type IS DISTINCT FROM OLD.auth_type"
    )


def downgrade():
    # An old binary must not silently regain untracked metadata/auth writes.
    op.execute("LOCK TABLE source_configuration_revisions IN SHARE ROW EXCLUSIVE MODE")
    if op.get_bind().scalar(
        text("SELECT EXISTS(SELECT 1 FROM source_configuration_revisions)")
    ):
        raise RuntimeError(
            "Unsafe populated source-context downgrade blocked before DDL; retain current schema. Require verified full backup, isolated restoration and explicit compatibility review before rollback."
        )
    writer("")
