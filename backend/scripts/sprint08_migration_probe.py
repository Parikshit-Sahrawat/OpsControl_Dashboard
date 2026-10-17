"""Preserve existing access/history/hold identities across migration 0037."""

import os, json, uuid, hashlib, sys
from pathlib import Path
from sqlalchemy import select, text
import app.main  # noqa: F401 - register all preservation snapshot models
from app.db.session import SessionLocal, Base
from app.security.models import User
from app.security.access_models import (
    Department,
    DepartmentMembership,
    DepartmentRoleAssignment,
    UserRoleAssignment,
    CustomerAccessGrant,
)
from app.security.permission_catalog import PROVIDER_ID, role_id
from app.security.passwords import hash_password
from app.models import Organization

assert os.environ.get("OPSCONTROL_V16_ACCEPTANCE") == "1"
private = Path(os.environ["V16_PRIVATE_DIR"])
out = Path(os.environ["V16_EVIDENCE_DIR"])


def snapshot(db):
    names = [
        "users",
        "departments",
        "department_memberships",
        "roles",
        "role_permissions",
        "user_role_assignments",
        "department_role_assignments",
        "customer_access_grants",
        "organization_memberships",
        "security_audit_events",
        "pipeline_holds",
        "pipeline_sources",
        "pentaho_evidence_reviews",
        "native_incident_failures",
        "native_recovery_assessments",
    ]
    result = {}
    for name in names:
        t = Base.metadata.tables[name]
        rows = [dict(r) for r in db.execute(select(t)).mappings()]
        payload = json.dumps(
            sorted(rows, key=lambda r: json.dumps(r, default=str, sort_keys=True)),
            default=str,
            sort_keys=True,
        )
        result[name] = {
            "count": len(rows),
            "sha256": hashlib.sha256(payload.encode()).hexdigest(),
        }
    return result


with SessionLocal() as db:
    if sys.argv[1] == "seed":
        u = User(
            username="s08-legacy-" + uuid.uuid4().hex,
            full_name="Preserved legacy multi-department employee",
            password_hash=hash_password(uuid.uuid4().hex),
            service_provider_id=PROVIDER_ID,
            active=True,
        )
        db.add(u)
        db.flush()
        org = db.scalar(select(Organization.id).where(Organization.active.is_(True)))
        rid = role_id("read-only-viewer")
        db.add(
            UserRoleAssignment(
                user_id=u.id, role_id=rid, service_provider_id=PROVIDER_ID
            )
        )
        db.flush()
        db.execute(
            text(
                "ALTER TABLE department_memberships DISABLE TRIGGER trg_single_department"
            )
        )
        for index in range(2):
            d = Department(
                name="Preserved legacy " + uuid.uuid4().hex,
                service_provider_id=PROVIDER_ID,
                active=True,
            )
            db.add(d)
            db.flush()
            db.add_all(
                [
                    DepartmentMembership(
                        user_id=u.id,
                        department_id=d.id,
                        service_provider_id=PROVIDER_ID,
                    ),
                    DepartmentRoleAssignment(
                        department_id=d.id, role_id=rid, service_provider_id=PROVIDER_ID
                    ),
                ]
            )
            db.flush()
            db.add(
                CustomerAccessGrant(
                    department_id=d.id,
                    role_id=rid,
                    organization_id=org,
                    service_provider_id=PROVIDER_ID,
                )
            )
        db.execute(
            text(
                "ALTER TABLE department_memberships ENABLE TRIGGER trg_single_department"
            )
        )
        db.commit()
        (private / "s08-legacy-user.txt").write_text(str(u.id))
        (private / "s08-authorization-before.json").write_text(
            json.dumps(snapshot(db), indent=2)
        )
    else:
        before = json.loads((private / "s08-authorization-before.json").read_text())
        after = snapshot(db)
        assert before == after
        from app.security.access_models import AccessBoundary, AccessBoundaryDecision
        from app.security.access_control import resolve_access

        u = db.get(User, uuid.UUID((private / "s08-legacy-user.txt").read_text()))
        p = resolve_access(db, u)
        assert (
            sum(
                s["source"] == "department" and "customer_id" in s for s in p.provenance
            )
            == 2
        )
        assert (
            not p.all_customers
            and not db.scalar(select(AccessBoundary.id))
            and not db.scalar(select(AccessBoundaryDecision.id))
        )
        (out / "sprint08-migration-preservation.json").write_text(
            json.dumps(
                {
                    "status": "PASS",
                    "before": before,
                    "after": after,
                    "legacy_multi_department_access_preserved": True,
                    "implicit_grants_added": False,
                },
                indent=2,
            )
        )
        print("Sprint 08 existing authorization/history/holds preservation PASS")
