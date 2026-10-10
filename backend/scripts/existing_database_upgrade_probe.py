"""Validate migration preservation on a nonempty PostgreSQL database.

Must run on a disposable CI database, NEVER a production database.
The script self-manages revision 0016 -> HEAD and verifies an organization
and Data Source existed beforehand and survive unchanged.
"""
import subprocess
import uuid
from sqlalchemy import text
from app.db.session import engine

def alembic(*args):
    subprocess.run(["alembic",*args],check=True)

def main():
    alembic("downgrade","0016_remote_collector_assignment")
    org=uuid.uuid4()
    source=uuid.uuid4()
    with engine.begin() as connection:
        connection.execute(text("""
            INSERT INTO organizations (id, name, code, active, created_at)
            VALUES (:id, 'Existing Fictional Lab', 'UPGRADE-LAB', true, now())
        """),{"id":org})
        connection.execute(text("""
            INSERT INTO data_sources (id, organization_id, name, source_type, enabled, created_at)
            VALUES (:id, :org, 'Pre-existing fictional source', 'API', true, now())
        """),{"id":source,"org":org})
    alembic("upgrade","head")
    with engine.begin() as connection:
        rows=connection.execute(text("""
            SELECT d.id,d.name,o.code
              FROM data_sources d
              JOIN organizations o ON o.id=d.organization_id
             WHERE d.id=:id
        """),{"id":source}).all()
        assert len(rows)==1 and rows[0].name=="Pre-existing fictional source" and rows[0].code=="UPGRADE-LAB",rows
        rev=connection.scalar(text("SELECT version_num FROM alembic_version"))
        assert rev=="0018_pentaho_execution_identity",rev
        connection.execute(text("DELETE FROM data_sources WHERE id=:id"),{"id":source})
        connection.execute(text("DELETE FROM organizations WHERE id=:id"),{"id":org})
    print("NONEMPTY DATABASE MIGRATION PRESERVATION PASSED")

if __name__=="__main__":
    main()
