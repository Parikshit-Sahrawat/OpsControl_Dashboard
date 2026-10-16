"""Validate migration preservation on a nonempty PostgreSQL database.

Must run on a disposable CI database, NEVER a production database.
The script self-manages revision 0016 -> HEAD and verifies an organization
and Data Source existed beforehand and survive unchanged.
"""

import subprocess
import sys
from app.core.config import settings
import uuid
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from app.db.session import engine


def alembic(*args):
    subprocess.run([sys.executable, "-m", "alembic", *args], check=True)


def cleanup_fixture(connection, org, source):
    """Remove only this probe's identified fixture, in the caller's transaction.

    0027 projects the API Data Source into monitoring_resources. Never cascade:
    unexpected dependents must fail and roll back the entire cleanup.
    """
    expected_code = "UPGRADE-LAB-" + org.hex[:12]
    row = connection.execute(
        text(
            """
        SELECT d.organization_id, o.code FROM data_sources d
        JOIN organizations o ON o.id=d.organization_id
        WHERE d.id=:source FOR UPDATE OF d,o
    """
        ),
        {"source": source},
    ).one_or_none()
    if row is None or row.organization_id != org or row.code != expected_code:
        raise RuntimeError("Disposable migration fixture identity mismatch")
    dependents = connection.execute(
        text(
            """
        SELECT id,organization_id,domain,vm_id,job_order_id,primary_collector_id
        FROM monitoring_resources WHERE data_source_id=:source FOR UPDATE
    """
        ),
        {"source": source},
    ).all()
    if any(
        r.organization_id != org
        or r.domain != "API"
        or r.vm_id is not None
        or r.job_order_id is not None
        or r.primary_collector_id is not None
        for r in dependents
    ):
        raise RuntimeError("Unexpected monitoring dependency; fixture cleanup refused")
    for resource in dependents:
        connection.execute(
            text(
                """
            DELETE FROM monitoring_resources
            WHERE id=:id AND organization_id=:org AND data_source_id=:source
        """
            ),
            {"id": resource.id, "org": org, "source": source},
        )
    connection.execute(
        text("DELETE FROM data_sources WHERE id=:source AND organization_id=:org"),
        {"source": source, "org": org},
    )
    connection.execute(
        text("DELETE FROM organizations WHERE id=:org AND code=:code"),
        {"org": org, "code": expected_code},
    )


def main():
    if settings.environment != "test" or engine.url.host not in {
        "localhost",
        "127.0.0.1",
    }:
        raise SystemExit(
            "Disposable loopback test database required; no production downgrade"
        )
    with engine.connect() as connection:
        current = connection.scalar(text("SELECT version_num FROM alembic_version"))
        if current != "0024_notification_leases":
            raise SystemExit(
                "Run this preservation gate at disposable revision 0024 before the protected 0025 upgrade; do not downgrade populated access configuration"
            )
    alembic("downgrade", "0016_remote_collector_assignment")
    org = uuid.uuid4()
    source = uuid.uuid4()
    code = "UPGRADE-LAB-" + org.hex[:12]
    with engine.begin() as connection:
        connection.execute(
            text(
                """
            INSERT INTO organizations (id, name, code, active, created_at, updated_at)
            VALUES (:id, 'Existing Fictional Lab', :code, true, now(), now())
        """
            ),
            {"id": org, "code": code},
        )
        connection.execute(
            text(
                """
            INSERT INTO data_sources (id, organization_id, name, source_type, enabled, status, created_at, updated_at)
            VALUES (:id, :org, 'Pre-existing fictional source', 'API', true, 'UNKNOWN', now(), now())
        """
            ),
            {"id": source, "org": org},
        )
    alembic("upgrade", "head")
    with engine.begin() as connection:
        rows = connection.execute(
            text(
                """
            SELECT d.id,d.name,o.code
              FROM data_sources d
              JOIN organizations o ON o.id=d.organization_id
             WHERE d.id=:id
        """
            ),
            {"id": source},
        ).all()
        assert (
            len(rows) == 1
            and rows[0].name == "Pre-existing fictional source"
            and rows[0].code == code
        ), rows
        rev = connection.scalar(text("SELECT version_num FROM alembic_version"))
        expected_head = ScriptDirectory.from_config(
            Config("alembic.ini")
        ).get_current_head()
        assert rev == expected_head, (rev, expected_head)
        cleanup_fixture(connection, org, source)
    print("NONEMPTY DATABASE MIGRATION PRESERVATION PASSED")


if __name__ == "__main__":
    main()
