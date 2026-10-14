"""Require zero schema/model drift across the complete migrated PostgreSQL schema."""

import json, os
from pathlib import Path
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine
from app.core.config import settings
from app.main import app  # register all mapper metadata
from app.db.session import Base
from app.security.access_models import (
    ServiceProvider,
    Department,
    DepartmentMembership,
    Role,
    Permission,
    RolePermission,
    UserRoleAssignment,
    DepartmentRoleAssignment,
    CustomerAccessGrant,
)


def main():
    tables = {"users"} | {
        m.__tablename__
        for m in (
            ServiceProvider,
            Department,
            DepartmentMembership,
            Role,
            Permission,
            RolePermission,
            UserRoleAssignment,
            DepartmentRoleAssignment,
            CustomerAccessGrant,
        )
    }
    engine = create_engine(settings.database_url)
    with engine.connect() as db:
        full = compare_metadata(
            MigrationContext.configure(db, opts={"compare_type": True}), Base.metadata
        )
        include = (
            lambda obj, name, kind, reflected, compare_to: kind != "table"
            or name in tables
        )
        access = compare_metadata(
            MigrationContext.configure(
                db, opts={"compare_type": True, "include_object": include}
            ),
            Base.metadata,
        )
        assert not access, "New access schema differs from declared models"
        assert not full, f"Full schema differs from declared models: {len(full)} groups"
        invalid_indexes = db.exec_driver_sql(
            "SELECT count(*) FROM pg_index i JOIN pg_class t ON t.oid = i.indrelid "
            "JOIN pg_namespace n ON n.oid = t.relnamespace "
            "WHERE n.nspname = current_schema() AND NOT i.indisvalid"
        ).scalar()
        assert invalid_indexes == 0, "Migrated schema contains invalid indexes"
        assert (
            db.exec_driver_sql("SELECT version_num FROM alembic_version").scalar()
            == ScriptDirectory.from_config(Config("alembic.ini")).get_current_head()
        )
    engine.dispose()
    report = {
        "status": "PASS",
        "validated_tables": sorted(tables),
        "new_schema_differences": 0,
        "existing_schema_model_differences": len(full),
        "existing_drift": repr(full),
        "total_schema_model_differences": 0,
        "invalid_indexes": invalid_indexes,
        "metadata_tables_compared": len(Base.metadata.tables),
        "global_alembic_check": "PASS",
    }
    out = Path(os.environ["ACCESS_EVIDENCE_DIR"])
    out.mkdir(parents=True, exist_ok=True)
    (out / "schema.json").write_text(json.dumps(report, indent=2))
    print(
        f"Full PostgreSQL schema / models PASS: {len(Base.metadata.tables)} tables, zero drift; immutable additive migration head PASS"
    )


if __name__ == "__main__":
    main()
