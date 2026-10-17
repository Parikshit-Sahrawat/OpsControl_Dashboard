"""Explicit administration budgets layered on existing provider checks."""

from fastapi import HTTPException
from sqlalchemy import select, and_, or_, String
from app.security.boundaries import delegation


def budget(p):
    d = delegation(p)
    if not p.platform_admin and not d["departments"]:
        raise HTTPException(403, "Explicit administrative delegation required")
    return d


def visible_users(p):
    from app.security.access_models import DepartmentMembership as M
    from app.security.models import User

    d = delegation(p)
    deps = list(d["departments"])
    m = M.__table__
    u = User.__table__
    inside = select(m.c.user_id).where(
        m.c.active.is_(True), m.c.department_id.in_(deps)
    )
    outside = select(m.c.user_id).where(
        m.c.active.is_(True), ~m.c.department_id.in_(deps)
    )
    return select(u.c.id).where(
        or_(u.c.id == p.user_id, and_(u.c.id.in_(inside), ~u.c.id.in_(outside)))
    )


def check_record(db, model, row, p):
    if p.platform_admin:
        return
    from app.security.access_models import (
        Department,
        UserRoleAssignment,
        DepartmentRoleAssignment,
        CustomerAccessGrant,
    )
    from app.security.models import User

    d = budget(p)
    if model is Department:
        db.info["delegation_departments"] = {row.id}
    if model is User:
        from app.security.access_models import DepartmentMembership

        m = DepartmentMembership.__table__
        db.info["delegation_departments"] = set(
            db.scalars(
                select(m.c.department_id).where(
                    m.c.user_id == row.id, m.c.active.is_(True)
                )
            )
        )
    if model is Department and str(row.id) not in d["departments"]:
        raise HTTPException(404, "Department outside delegation")
    if model is User and not db.scalar(
        select(User.id).where(User.id == row.id, User.id.in_(visible_users(p)))
    ):
        raise HTTPException(404, "Employee outside delegation")
    if model is UserRoleAssignment:
        if not db.scalar(
            select(User.id).where(User.id == row.user_id, User.id.in_(visible_users(p)))
        ):
            raise HTTPException(404, "Assignment outside delegation")
    if (
        model is DepartmentRoleAssignment
        and str(row.department_id) not in d["departments"]
    ):
        raise HTTPException(404, "Assignment outside delegation")
    if model is CustomerAccessGrant and str(row.organization_id) not in d["customers"]:
        raise HTTPException(404, "Customer outside delegation")


def check_role(db, role, p, edit=False):
    if p.platform_admin:
        return
    from app.security.access_models import (
        RolePermission,
        UserRoleAssignment as U,
        DepartmentRoleAssignment as D,
        CustomerAccessGrant as G,
    )

    U = U.__table__
    D = D.__table__
    G = G.__table__
    d = budget(p)
    keys = set(
        db.scalars(
            select(RolePermission.permission_key).where(
                RolePermission.role_id == role.id, RolePermission.active.is_(True)
            )
        )
    )
    if not covers(
        p,
        departments=db.info.get("delegation_departments", ()),
        customers=db.info.get("delegation_customers", ()),
        permissions=keys,
    ):
        raise HTTPException(
            403,
            "One explicit delegation must cover this complete role, subject and customer operation",
        )
    if not keys <= d["permissions"]:
        raise HTTPException(403, "Role exceeds explicitly delegated permissions")
    if not edit:
        return
    footprint_departments = set(
        db.scalars(select(D.c.department_id).where(D.c.role_id == role.id))
    )
    from app.security.access_models import DepartmentMembership

    members = DepartmentMembership.__table__
    footprint_departments.update(
        db.scalars(
            select(members.c.department_id).where(
                members.c.active.is_(True),
                members.c.user_id.in_(
                    select(U.c.user_id).where(U.c.role_id == role.id)
                ),
            )
        )
    )
    footprint_customers = set(
        db.scalars(select(G.c.organization_id).where(G.c.role_id == role.id))
    )
    if not covers(
        p,
        departments=footprint_departments
        | set(db.info.get("delegation_departments", ())),
        customers=footprint_customers | set(db.info.get("delegation_customers", ())),
        permissions=keys,
    ):
        raise HTTPException(403, "Shared role crosses separate delegation budgets")
    if (
        db.scalar(
            select(U.c.id)
            .where(U.c.role_id == role.id, ~U.c.user_id.in_(visible_users(p)))
            .limit(1)
        )
        or db.scalar(
            select(D.c.id)
            .where(D.c.role_id == role.id, ~D.c.department_id.in_(d["departments"]))
            .limit(1)
        )
        or db.scalar(
            select(G.c.id)
            .where(G.c.role_id == role.id, ~G.c.organization_id.in_(d["customers"]))
            .limit(1)
        )
    ):
        raise HTTPException(403, "Shared role has assignments outside delegation")


def check_inherited(db, department, p):
    """A membership change also delegates existing paired customer grants."""
    if p.platform_admin:
        return
    from app.security.access_models import CustomerAccessGrant as G

    G = G.__table__
    d = budget(p)
    if db.scalar(
        select(G.c.id)
        .where(
            G.c.department_id == department, ~G.c.organization_id.in_(d["customers"])
        )
        .limit(1)
    ):
        raise HTTPException(403, "Department customer grants exceed delegation")
    from app.security.access_models import RolePermission

    rp = RolePermission.__table__
    paired = {}
    for org, rid, key in db.execute(
        select(G.c.organization_id, G.c.role_id, rp.c.permission_key)
        .select_from(G.join(rp, G.c.role_id == rp.c.role_id))
        .where(G.c.department_id == department, rp.c.active.is_(True))
    ):
        paired.setdefault((org, rid), set()).add(key)
    if any(
        not covers(p, departments=[department], customers=[org], permissions=keys)
        for (org, _), keys in paired.items()
    ):
        raise HTTPException(
            403, "Inherited role/customer pair crosses delegation budgets"
        )
    from app.security.access_models import AccessBoundary

    if db.scalar(
        select(AccessBoundary.id)
        .where(
            AccessBoundary.department_id == department, AccessBoundary.active.is_(True)
        )
        .limit(1)
    ):
        raise HTTPException(403, "Department has protected authorization boundaries")


from sqlalchemy import event
from sqlalchemy.orm import Session, with_loader_criteria


@event.listens_for(Session, "do_orm_execute")
def administration_reads(state):
    if not state.is_select or not state.session.info.get("access_administration"):
        return
    from app.security.http import actor
    from app.security.access_models import (
        Department,
        DepartmentMembership,
        UserRoleAssignment,
        DepartmentRoleAssignment,
        CustomerAccessGrant,
    )
    from app.security.models import User, SecurityAuditEvent
    from app.models import Organization

    p = actor()
    if p.platform_admin:
        return
    d = delegation(p)
    users = visible_users(p)
    stmt = state.statement
    criteria = [
        (User, User.id.in_(users)),
        (Department, Department.id.in_(d["departments"])),
        (
            DepartmentMembership,
            and_(
                DepartmentMembership.user_id.in_(users),
                DepartmentMembership.department_id.in_(d["departments"]),
            ),
        ),
        (UserRoleAssignment, UserRoleAssignment.user_id.in_(users)),
        (
            DepartmentRoleAssignment,
            DepartmentRoleAssignment.department_id.in_(d["departments"]),
        ),
        (
            CustomerAccessGrant,
            and_(
                CustomerAccessGrant.organization_id.in_(d["customers"]),
                or_(
                    CustomerAccessGrant.user_id.in_(users),
                    CustomerAccessGrant.department_id.in_(d["departments"]),
                ),
            ),
        ),
        (Organization, Organization.id.in_(d["customers"])),
        (
            SecurityAuditEvent,
            and_(
                SecurityAuditEvent.actor_id.in_(users),
                or_(
                    SecurityAuditEvent.organization_id.in_(d["customers"]),
                    and_(
                        SecurityAuditEvent.organization_id.is_(None),
                        SecurityAuditEvent.target_type == "employee",
                        SecurityAuditEvent.target_id.in_(
                            select(User.__table__.c.id.cast(String)).where(
                                User.__table__.c.id.in_(users)
                            )
                        ),
                    ),
                ),
            ),
        ),
    ]
    for model, criterion in criteria:
        stmt = stmt.options(
            with_loader_criteria(model, criterion, include_aliases=True)
        )
    state.statement = stmt


def covers(p, *, departments=(), customers=(), permissions=()):
    if p.platform_admin:
        return True
    departments = {str(v) for v in departments}
    customers = {str(v) for v in customers}
    permissions = set(permissions)
    return any(
        b["kind"] == "DELEGATE"
        and departments <= set(b["specification"]["departments"])
        and customers <= set(b["specification"]["customers"])
        and permissions <= set(b["specification"]["permissions"])
        for b in p.boundaries
    )
