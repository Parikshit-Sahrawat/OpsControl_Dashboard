"""Validate this additive schema; report existing schema/model drift separately."""

import json, os
from pathlib import Path
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
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
    with create_engine(settings.database_url).connect() as db:
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
        assert (
            db.exec_driver_sql("SELECT version_num FROM alembic_version").scalar()
            == "0025_provider_department_rbac"
        )
    report = {
        "status": "PASS",
        "validated_tables": sorted(tables),
        "new_schema_differences": 0,
        "existing_schema_model_differences": len(full),
        "existing_drift": repr(full),
        "global_alembic_check": "FAIL: existing non-access drift" if full else "PASS",
    }
    out = Path(os.environ["ACCESS_EVIDENCE_DIR"])
    out.mkdir(parents=True, exist_ok=True)
    (out / "schema.json").write_text(json.dumps(report, indent=2))
    print(
        f"New access schema / immutable additive migration head PASS; existing non-access drift groups: {len(full)}"
    )


if __name__ == "__main__":
    main()
