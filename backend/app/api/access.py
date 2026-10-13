"""Provider-scoped internal administration. Every service checks its exact permission."""

import re, uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select, func, delete, text, case, literal, union_all, Uuid
from sqlalchemy.exc import IntegrityError
from app.db.session import SessionLocal
from app.security.models import User, OrganizationMembership, SecurityAuditEvent
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
from app.security.access_control import (
    require_permission,
    resolve_access,
    effective_document,
)
from app.security.permission_catalog import (
    PERMISSIONS,
    PROVIDER_ID,
    LEGACY_ROLES,
    role_id,
    delegable,
)
from app.security.passwords import hash_password
from app.security.http import actor, revoke_sessions
from app.security.audit import log_event
from app.models import Organization

router = APIRouter(prefix="/api/v1/access", tags=["Internal Access Management"])


def session():
    # Internal objects are not customer-owned ORM objects. Provider constraints
    # and explicit service checks are mandatory here; global selector is ignored.
    with SessionLocal() as db:
        try:
            yield db
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                409, "Duplicate or invalid provider/assignment relationship"
            ) from None


def allowed(key):
    require_permission("access.view")
    return require_permission(key)


def own(db, model, id, *, lock=False):
    if lock or model is Role:
        # NO KEY UPDATE serializes authorization changes while remaining
        # compatible with FK KEY SHARE locks from audit/assignment inserts.
        row = db.scalar(
            select(model)
            .where(
                model.id == id, model.service_provider_id == actor().service_provider_id
            )
            .with_for_update(key_share=True)
        )
    else:
        row = db.get(model, id)
    if (
        row is None
        or getattr(row, "service_provider_id", None) != actor().service_provider_id
    ):
        raise HTTPException(404, "Provider record not found")
    return row


def protected_employee_ids(db, ids):
    """Protect credentials/lifecycle of assigned administration identities too.

    Include inactive roles/departments: support staff must not set a known
    password just before a protected account is reactivated. DENY assignments
    do not grant authority and are not a source of administrative capability.
    """
    keys = [key for key in PERMISSIONS if not delegable(key)]
    direct = (
        select(UserRoleAssignment.user_id)
        .join(RolePermission, RolePermission.role_id == UserRoleAssignment.role_id)
        .where(
            UserRoleAssignment.user_id.in_(ids),
            UserRoleAssignment.effect == "ALLOW",
            RolePermission.permission_key.in_(keys),
        )
    )
    inherited = (
        select(DepartmentMembership.user_id)
        .join(
            DepartmentRoleAssignment,
            DepartmentRoleAssignment.department_id
            == DepartmentMembership.department_id,
        )
        .join(
            RolePermission, RolePermission.role_id == DepartmentRoleAssignment.role_id
        )
        .where(
            DepartmentMembership.user_id.in_(ids),
            DepartmentMembership.active.is_(True),
            RolePermission.permission_key.in_(keys),
        )
    )
    return set(db.scalars(union_all(direct, inherited)))


def protect_employee(db, u, authorization=False):
    p = actor()
    if u.platform_admin and not p.platform_admin:
        raise HTTPException(403, "Break-glass account is protected")
    if authorization and u.id == p.user_id and not p.platform_admin:
        raise HTTPException(403, "Cannot change your own authorization")
    if (
        not p.platform_admin
        and u.id != p.user_id
        and u.id in protected_employee_ids(db, [u.id])
    ):
        raise HTTPException(
            403, "Reserved administration identity requires platform authority"
        )


def delegate(db, role):
    if role.code == "platform-administrator":
        raise HTTPException(
            422,
            "Use the protected employee platform-administrator control; a role cannot grant break-glass status",
        )
    keys = set(
        db.scalars(
            select(RolePermission.permission_key).where(
                RolePermission.role_id == role.id,
                RolePermission.permission_key.in_(PERMISSIONS),
            )
        )
    )
    if not actor().platform_admin and any(not delegable(k) for k in keys):
        raise HTTPException(
            403, "These permissions are outside your delegation authority"
        )


def affected_self(db, department_id):
    if not actor().platform_admin and db.scalar(
        select(DepartmentMembership.id).where(
            DepartmentMembership.department_id == department_id,
            DepartmentMembership.user_id == actor().user_id,
            DepartmentMembership.active.is_(True),
        )
    ):
        raise HTTPException(
            403, "Cannot change an inherited authorization path for your own account"
        )


def commit(db, event, target, row_id, customer=None):
    try:
        db.flush()
        log_event(
            db,
            event_type=event,
            outcome="SUCCESS",
            actor_id=actor().user_id,
            organization_id=customer,
            target_type=target,
            target_id=row_id,
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            409, "Duplicate or invalid provider/assignment relationship"
        ) from None


def page(items, total, limit, offset):
    return {"items": items, "total": total, "limit": limit, "offset": offset}


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EmployeeCreate(Strict):
    department_id: uuid.UUID
    username: str = Field(min_length=1, max_length=120)
    full_name: str = Field(min_length=1, max_length=160)
    employee_id: str | None = Field(default=None, max_length=80)
    work_email: str | None = Field(default=None, max_length=254)
    password: str = Field(min_length=12, max_length=1024)
    platform_admin: bool = False

    @field_validator(
        "username", "full_name", "employee_id", "work_email", mode="before"
    )
    @classmethod
    def trim(cls, v):
        return v.strip() or None if isinstance(v, str) else v

    @field_validator("work_email")
    @classmethod
    def email(cls, v):
        if v and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", v):
            raise ValueError("Invalid work email")
        return v


class EmployeePatch(Strict):
    full_name: str | None = Field(default=None, min_length=1, max_length=160)
    employee_id: str | None = Field(default=None, max_length=80)
    work_email: str | None = Field(default=None, max_length=254)
    active: bool | None = None
    platform_admin: bool | None = None

    @field_validator("full_name", "employee_id", "work_email", mode="before")
    @classmethod
    def trim(cls, v):
        return v.strip() or None if isinstance(v, str) else v

    @field_validator("work_email")
    @classmethod
    def email(cls, v):
        return EmployeeCreate.email(v)


class PasswordIn(Strict):
    new_password: str = Field(min_length=12, max_length=1024)


class DepartmentCreate(Strict):
    name: str = Field(min_length=1, max_length=160)
    code: str | None = Field(default=None, max_length=40)
    description: str | None = Field(default=None, max_length=1000)
    manager_id: uuid.UUID | None = None
    active: bool = True

    @field_validator("name", "code", "description", mode="before")
    @classmethod
    def trim(cls, v):
        return v.strip() or None if isinstance(v, str) else v

    @field_validator("code")
    @classmethod
    def code_value(cls, v):
        return v.upper() if v else None


class DepartmentPatch(DepartmentCreate):
    pass


class MemberIn(Strict):
    user_id: uuid.UUID


class RoleIn(Strict):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    permissions: list[str] = Field(default_factory=list, max_length=100)
    active: bool = True

    @field_validator("name", mode="before")
    @classmethod
    def trim(cls, v):
        return v.strip() if isinstance(v, str) else v


class RoleAssignmentIn(Strict):
    role_id: uuid.UUID
    effect: str = "ALLOW"

    @field_validator("effect")
    @classmethod
    def effect_value(cls, v):
        if v not in {"ALLOW", "DENY"}:
            raise ValueError("Unsupported effect")
        return v


class GrantIn(Strict):
    user_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    organization_id: uuid.UUID
    role_id: uuid.UUID | None = None
    effect: str = "ALLOW"


def employee_documents(db, people):
    ids = [u.id for u in people]
    memberships = list(
        db.scalars(
            select(DepartmentMembership).where(DepartmentMembership.user_id.in_(ids))
        )
    )
    roles = list(
        db.scalars(
            select(UserRoleAssignment).where(UserRoleAssignment.user_id.in_(ids))
        )
    )
    protected = protected_employee_ids(db, ids)
    return [
        {
            "id": str(u.id),
            "username": u.username,
            "full_name": u.full_name or u.username,
            "employee_id": u.employee_id,
            "work_email": u.work_email,
            "active": u.active,
            "platform_admin": u.platform_admin,
            "protected_administration": u.platform_admin or u.id in protected,
            "service_provider_id": str(u.service_provider_id),
            "departments": [
                {
                    "id": str(m.department_id),
                    "membership_id": str(m.id),
                    "active": m.active,
                }
                for m in memberships
                if m.user_id == u.id
            ],
            "roles": [
                {"id": str(a.role_id), "assignment_id": str(a.id), "effect": a.effect}
                for a in roles
                if a.user_id == u.id
            ],
        }
        for u in people
    ]


@router.get("/provider")
def provider_info(db=Depends(session)):
    allowed("access.view")
    p = db.get(ServiceProvider, actor().service_provider_id)
    return {"id": str(p.id), "name": p.name, "code": p.code, "active": p.active}


@router.get("/employees")
def employees(
    search: str = "",
    department_id: uuid.UUID | None = None,
    role_id: uuid.UUID | None = None,
    active: bool | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db=Depends(session),
):
    allowed("access.view")
    stmt = select(User).where(User.service_provider_id == actor().service_provider_id)
    if search:
        stmt = stmt.where(
            (User.username.ilike("%" + search[:160] + "%"))
            | (User.full_name.ilike("%" + search[:160] + "%"))
            | (User.employee_id.ilike("%" + search[:160] + "%"))
        )
    if active is not None:
        stmt = stmt.where(User.active == active)
    if department_id:
        own(db, Department, department_id)
        stmt = stmt.where(
            User.id.in_(
                select(DepartmentMembership.user_id).where(
                    DepartmentMembership.department_id == department_id,
                    DepartmentMembership.active.is_(True),
                )
            )
        )
    if role_id:
        own(db, Role, role_id)
        stmt = stmt.where(
            User.id.in_(
                select(UserRoleAssignment.user_id).where(
                    UserRoleAssignment.role_id == role_id
                )
            )
            | User.id.in_(
                select(DepartmentMembership.user_id)
                .join(
                    DepartmentRoleAssignment,
                    DepartmentRoleAssignment.department_id
                    == DepartmentMembership.department_id,
                )
                .join(Department, Department.id == DepartmentMembership.department_id)
                .where(
                    DepartmentRoleAssignment.role_id == role_id,
                    DepartmentMembership.active.is_(True),
                    Department.active.is_(True),
                )
            )
        )
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(User.username).limit(limit).offset(offset)).all()
    return page(employee_documents(db, rows), total, limit, offset)


@router.get("/employees/{user_id}")
def employee(user_id: uuid.UUID, db=Depends(session)):
    allowed("access.view")
    return employee_documents(db, [own(db, User, user_id)])[0]


@router.post("/employees", status_code=201)
def create_employee(payload: EmployeeCreate, db=Depends(session)):
    allowed("access.manage_users")
    if payload.platform_admin and not actor().platform_admin:
        raise HTTPException(
            403, "Only break-glass administration may create a platform administrator"
        )
    department = own(db, Department, payload.department_id, lock=True)
    if not department.active:
        raise HTTPException(422, "Select an active department")
    for assignment in db.scalars(
        select(DepartmentRoleAssignment).where(
            DepartmentRoleAssignment.department_id == department.id
        )
    ):
        delegate(db, own(db, Role, assignment.role_id))
    username = payload.username.lower()
    if db.scalar(select(User.id).where(func.lower(User.username) == username)):
        raise HTTPException(409, "Username already exists")
    u = User(
        username=username,
        full_name=payload.full_name,
        employee_id=payload.employee_id,
        work_email=payload.work_email,
        password_hash=hash_password(payload.password),
        platform_admin=payload.platform_admin,
        service_provider_id=actor().service_provider_id,
    )
    db.add(u)
    db.flush()
    db.add(
        DepartmentMembership(
            user_id=u.id,
            department_id=department.id,
            service_provider_id=department.service_provider_id,
        )
    )
    commit(db, "EMPLOYEE_CREATE", "employee", u.id)
    return employee_documents(db, [u])[0]


@router.patch("/employees/{user_id}")
def edit_employee(user_id: uuid.UUID, payload: EmployeePatch, db=Depends(session)):
    allowed("access.manage_users")
    db.execute(text("SELECT pg_advisory_xact_lock(782104, 1)"))
    u = own(db, User, user_id, lock=True)
    values = payload.model_dump(exclude_unset=True)
    protect_employee(
        db, u, authorization=bool({"active", "platform_admin"} & values.keys())
    )
    if "platform_admin" in values and not actor().platform_admin:
        raise HTTPException(403, "Break-glass status is not delegable")
    if any(
        v is None
        for k, v in values.items()
        if k in {"active", "platform_admin", "full_name"}
    ):
        raise HTTPException(422, "Required employee values cannot be null")
    if (
        u.active
        and u.platform_admin
        and (values.get("active") is False or values.get("platform_admin") is False)
    ):
        if (
            db.scalar(
                select(func.count())
                .select_from(User)
                .where(
                    User.active.is_(True),
                    User.platform_admin.is_(True),
                    User.service_provider_id == actor().service_provider_id,
                )
            )
            <= 1
        ):
            raise HTTPException(
                409, "Cannot remove the last active platform administrator"
            )
    for k, v in values.items():
        setattr(u, k, v)
    if {"active", "platform_admin"} & values.keys():
        revoke_sessions(db, u.id)
    commit(db, "EMPLOYEE_UPDATE", "employee", u.id)
    return employee_documents(db, [u])[0]


@router.post("/employees/{user_id}/password")
def password(user_id: uuid.UUID, payload: PasswordIn, db=Depends(session)):
    allowed("access.manage_users")
    u = own(db, User, user_id, lock=True)
    protect_employee(db, u)
    u.password_hash = hash_password(payload.new_password)
    revoke_sessions(db, u.id)
    commit(db, "EMPLOYEE_PASSWORD_RESET", "employee", u.id)
    return {"id": str(u.id), "sessions_revoked": True}


@router.get("/employees/{user_id}/effective-permissions")
def effective(user_id: uuid.UUID, db=Depends(session)):
    allowed("access.view")
    u = own(db, User, user_id)
    if not u.active:
        return {
            "user_id": str(u.id),
            "permissions": [],
            "customer_permissions": {},
            "inherited_and_direct": [],
            "disabled": True,
        }
    p = resolve_access(db, u)
    if p is None:
        raise HTTPException(403, "Employee provider is inactive")
    return effective_document(p)


@router.get("/departments")
def departments(
    search: str = "",
    active: bool | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db=Depends(session),
):
    allowed("access.view")
    stmt = select(Department).where(
        Department.service_provider_id == actor().service_provider_id
    )
    if search:
        stmt = stmt.where(
            Department.name.ilike("%" + search[:160] + "%")
            | Department.code.ilike("%" + search[:160] + "%")
        )
    if active is not None:
        stmt = stmt.where(Department.active == active)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(Department.name).limit(limit).offset(offset)).all()
    ids = [d.id for d in rows]
    counts = dict(
        db.execute(
            select(DepartmentMembership.department_id, func.count())
            .where(
                DepartmentMembership.department_id.in_(ids),
                DepartmentMembership.active.is_(True),
            )
            .group_by(DepartmentMembership.department_id)
        ).all()
    )
    assignments = list(
        db.scalars(
            select(DepartmentRoleAssignment).where(
                DepartmentRoleAssignment.department_id.in_(ids)
            )
        )
    )
    grants = list(
        db.scalars(
            select(CustomerAccessGrant).where(
                CustomerAccessGrant.department_id.in_(ids)
            )
        )
    )
    return page(
        [
            {
                "id": str(d.id),
                "service_provider_id": str(d.service_provider_id),
                "name": d.name,
                "code": d.code,
                "description": d.description,
                "active": d.active,
                "manager_id": str(d.manager_id) if d.manager_id else None,
                "employee_count": counts.get(d.id, 0),
                "roles": [
                    {"id": str(a.role_id), "assignment_id": str(a.id)}
                    for a in assignments
                    if a.department_id == d.id
                ],
                "customer_access": [
                    {
                        "id": str(g.id),
                        "organization_id": str(g.organization_id),
                        "role_id": str(g.role_id),
                    }
                    for g in grants
                    if g.department_id == d.id
                ],
            }
            for d in rows
        ],
        total,
        limit,
        offset,
    )


@router.post("/departments", status_code=201)
def create_department(payload: DepartmentCreate, db=Depends(session)):
    allowed("access.manage_departments")
    if payload.manager_id:
        own(db, User, payload.manager_id, lock=True)
    d = Department(
        **payload.model_dump(), service_provider_id=actor().service_provider_id
    )
    db.add(d)
    db.flush()
    commit(db, "DEPARTMENT_CREATE", "department", d.id)
    return {"id": str(d.id), "name": d.name, "code": d.code, "active": d.active}


@router.patch("/departments/{department_id}")
def edit_department(
    department_id: uuid.UUID, payload: DepartmentPatch, db=Depends(session)
):
    allowed("access.manage_departments")
    d = own(db, Department, department_id, lock=True)
    if d.active != payload.active:
        affected_self(db, d.id)
    if d.active != payload.active:
        # Lifecycle changes affect the existing roles again. A department-only
        # administrator cannot activate protected access roles for others.
        for assignment in db.scalars(
            select(DepartmentRoleAssignment).where(
                DepartmentRoleAssignment.department_id == d.id
            )
        ):
            delegate(db, own(db, Role, assignment.role_id))
    if payload.manager_id:
        own(db, User, payload.manager_id, lock=True)
    for k, v in payload.model_dump().items():
        setattr(d, k, v)
    commit(db, "DEPARTMENT_UPDATE", "department", d.id)
    return {"id": str(d.id), "name": d.name, "active": d.active}


@router.delete("/departments/{department_id}")
def delete_department(department_id: uuid.UUID, db=Depends(session)):
    allowed("access.manage_departments")
    own(db, Department, department_id, lock=True)
    raise HTTPException(
        409,
        "Departments are retained for identity/audit integrity. Use explicit soft deactivation; memberships and grants remain visible.",
    )


@router.get("/departments/{department_id}/members")
def department_members(department_id: uuid.UUID, db=Depends(session)):
    allowed("access.view")
    own(db, Department, department_id)
    rows = db.scalars(
        select(User)
        .join(DepartmentMembership, DepartmentMembership.user_id == User.id)
        .where(
            DepartmentMembership.department_id == department_id,
            DepartmentMembership.active.is_(True),
        )
        .order_by(User.username)
    ).all()
    return employee_documents(db, rows)


@router.post("/departments/{department_id}/members", status_code=201)
def add_member(department_id: uuid.UUID, payload: MemberIn, db=Depends(session)):
    allowed("access.manage_departments")
    allowed("access.manage_users")
    d = own(db, Department, department_id, lock=True)
    u = own(db, User, payload.user_id, lock=True)
    protect_employee(db, u, True)
    for a in db.scalars(
        select(DepartmentRoleAssignment).where(
            DepartmentRoleAssignment.department_id == d.id
        )
    ):
        delegate(db, own(db, Role, a.role_id))
    row = db.scalar(
        select(DepartmentMembership).where(
            DepartmentMembership.department_id == d.id,
            DepartmentMembership.user_id == u.id,
        )
    )
    if db.scalar(
        select(DepartmentMembership.id).where(
            DepartmentMembership.user_id == u.id,
            DepartmentMembership.active.is_(True),
            DepartmentMembership.department_id != d.id,
        )
    ):
        raise HTTPException(
            409,
            "Employee already has a department; use the explicit department transfer action",
        )
    if row and row.active:
        raise HTTPException(409, "Employee is already a member")
    if row:
        row.active = True
    else:
        row = DepartmentMembership(
            department_id=d.id, user_id=u.id, service_provider_id=d.service_provider_id
        )
        db.add(row)
    db.flush()
    commit(db, "DEPARTMENT_MEMBER_ADD", "department_membership", row.id)
    return {"id": str(row.id), "department_id": str(d.id), "user_id": str(u.id)}


@router.delete("/departments/{department_id}/members/{user_id}", status_code=204)
def remove_member(department_id: uuid.UUID, user_id: uuid.UUID, db=Depends(session)):
    allowed("access.manage_departments")
    allowed("access.manage_users")
    own(db, Department, department_id, lock=True)
    u = own(db, User, user_id, lock=True)
    protect_employee(db, u, True)
    row = db.scalar(
        select(DepartmentMembership).where(
            DepartmentMembership.department_id == department_id,
            DepartmentMembership.user_id == user_id,
        )
    )
    if row is None:
        raise HTTPException(404, "Membership not found")
    row.active = False
    commit(db, "DEPARTMENT_MEMBER_REMOVE", "department_membership", row.id)


@router.get("/permissions")
def permission_catalog(db=Depends(session)):
    allowed("access.view")
    return [
        {
            "key": k,
            "description": v,
            "module": k.split(".")[0],
            "action": k.split(".")[1],
            "delegable": delegable(k),
        }
        for k, v in PERMISSIONS.items()
    ]


@router.get("/roles")
def role_list(db=Depends(session)):
    allowed("access.view")
    rows = db.scalars(
        select(Role)
        .where(Role.service_provider_id == actor().service_provider_id)
        .order_by(Role.name)
    ).all()
    perms = list(
        db.execute(
            select(RolePermission.role_id, RolePermission.permission_key).where(
                RolePermission.permission_key.in_(PERMISSIONS)
            )
        ).all()
    )
    return [
        {
            "id": str(r.id),
            "name": r.name,
            "code": r.code,
            "description": r.description,
            "active": r.active,
            "system": r.system,
            "permissions": [k for rid, k in perms if rid == r.id and k in PERMISSIONS],
        }
        for r in rows
    ]


def checked_permissions(keys):
    if len(keys) != len(set(keys)) or not set(keys) <= PERMISSIONS.keys():
        raise HTTPException(422, "Unknown or duplicate implemented permission")
    if not actor().platform_admin and any(not delegable(k) for k in keys):
        raise HTTPException(403, "Permission is outside your delegation authority")


@router.post("/roles", status_code=201)
def create_role(payload: RoleIn, db=Depends(session)):
    allowed("access.manage_roles")
    allowed("access.manage_permissions")
    checked_permissions(payload.permissions)
    r = Role(
        name=payload.name,
        code="custom-" + str(uuid.uuid4()),
        description=payload.description,
        active=payload.active,
        service_provider_id=actor().service_provider_id,
    )
    db.add(r)
    db.flush()
    for key in payload.permissions:
        db.add(RolePermission(role_id=r.id, permission_key=key))
    commit(db, "ROLE_CREATE", "role", r.id)
    return {"id": str(r.id), "name": r.name}


@router.patch("/roles/{role_id}")
def update_role(role_id: uuid.UUID, payload: RoleIn, db=Depends(session)):
    allowed("access.manage_roles")
    allowed("access.manage_permissions")
    r = own(db, Role, role_id)
    if r.system:
        raise HTTPException(
            409,
            "Reviewed default/compatibility roles are immutable; create a custom role",
        )
    if r.id in actor().role_ids and not actor().platform_admin:
        raise HTTPException(403, "Cannot edit a role in your own authorization path")
    delegate(db, r)
    checked_permissions(payload.permissions)
    r.name = payload.name
    r.description = payload.description
    r.active = payload.active
    db.execute(delete(RolePermission).where(RolePermission.role_id == r.id))
    for key in payload.permissions:
        db.add(RolePermission(role_id=r.id, permission_key=key))
    commit(db, "ROLE_UPDATE", "role", r.id)
    return {"id": str(r.id), "name": r.name}


@router.post("/employees/{user_id}/roles", status_code=201)
def assign_employee_role(
    user_id: uuid.UUID, payload: RoleAssignmentIn, db=Depends(session)
):
    allowed("access.manage_roles")
    u = own(db, User, user_id, lock=True)
    protect_employee(db, u, True)
    r = own(db, Role, payload.role_id)
    delegate(db, r)
    a = UserRoleAssignment(
        user_id=u.id,
        role_id=r.id,
        service_provider_id=u.service_provider_id,
        effect=payload.effect,
    )
    db.add(a)
    db.flush()
    commit(db, "EMPLOYEE_ROLE_ASSIGN", "user_role_assignment", a.id)
    return {"id": str(a.id), "effect": a.effect}


@router.delete("/employees/{user_id}/roles/{assignment_id}", status_code=204)
def remove_employee_role(
    user_id: uuid.UUID, assignment_id: uuid.UUID, db=Depends(session)
):
    allowed("access.manage_roles")
    u = own(db, User, user_id, lock=True)
    protect_employee(db, u, True)
    a = own(db, UserRoleAssignment, assignment_id)
    if a.user_id != u.id:
        raise HTTPException(404, "Assignment not found")
    r = own(db, Role, a.role_id)
    delegate(db, r)
    # Remove matching legacy sources too; otherwise compatibility would restore
    # authority on the next request. This is explicit revocation, not relabeling.
    for m in db.scalars(
        select(OrganizationMembership).where(OrganizationMembership.user_id == u.id)
    ):
        if role_id_for_legacy(m.role) == r.id:
            db.delete(m)
    db.delete(a)
    commit(db, "EMPLOYEE_ROLE_REVOKE", "user_role_assignment", a.id)


def role_id_for_legacy(role):
    return role_id(LEGACY_ROLES.get(role, ""))


@router.post("/departments/{department_id}/roles", status_code=201)
def assign_department_role(
    department_id: uuid.UUID, payload: RoleAssignmentIn, db=Depends(session)
):
    allowed("access.manage_roles")
    d = own(db, Department, department_id, lock=True)
    affected_self(db, d.id)
    r = own(db, Role, payload.role_id)
    delegate(db, r)
    if payload.effect != "ALLOW":
        raise HTTPException(
            422, "Department roles allow; employee overrides implement denies"
        )
    a = DepartmentRoleAssignment(
        department_id=d.id, role_id=r.id, service_provider_id=d.service_provider_id
    )
    db.add(a)
    db.flush()
    commit(db, "DEPARTMENT_ROLE_ASSIGN", "department_role_assignment", a.id)
    return {"id": str(a.id)}


@router.delete("/departments/{department_id}/roles/{assignment_id}", status_code=204)
def remove_department_role(
    department_id: uuid.UUID, assignment_id: uuid.UUID, db=Depends(session)
):
    allowed("access.manage_roles")
    d = own(db, Department, department_id, lock=True)
    affected_self(db, d.id)
    a = own(db, DepartmentRoleAssignment, assignment_id)
    if a.department_id != d.id:
        raise HTTPException(404, "Assignment not found")
    delegate(db, own(db, Role, a.role_id))
    db.delete(a)
    commit(db, "DEPARTMENT_ROLE_REVOKE", "department_role_assignment", a.id)


@router.get("/customer-directory")
def customer_directory(db=Depends(session)):
    allowed("access.view")
    # Minimal grant-target directory, deliberately separate from operational APIs.
    return [
        {"id": str(o.id), "name": o.name, "code": o.code, "active": o.active}
        for o in db.scalars(select(Organization).order_by(Organization.name)).all()
    ]


@router.get("/customer-grants")
def grants(
    user_id: uuid.UUID | None = None,
    department_id: uuid.UUID | None = None,
    organization_id: uuid.UUID | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db=Depends(session),
):
    allowed("access.view")
    # Legacy API/CLI memberships created AFTER the migration remain real customer
    # grants. Union unmirrored sources without writes during a GET or double-counts.
    actual = select(
        CustomerAccessGrant.id,
        CustomerAccessGrant.service_provider_id,
        CustomerAccessGrant.user_id,
        CustomerAccessGrant.department_id,
        CustomerAccessGrant.organization_id,
        CustomerAccessGrant.role_id,
        CustomerAccessGrant.effect,
        case(
            (
                CustomerAccessGrant.legacy_membership_id.is_not(None),
                "legacy_customer_membership",
            ),
            (CustomerAccessGrant.user_id.is_not(None), "employee"),
            else_="department",
        ).label("source"),
    )
    legacy_code = case(
        *[
            (OrganizationMembership.role == code, mapped)
            for code, mapped in LEGACY_ROLES.items()
        ],
        else_="unsupported-legacy-role"
    )
    legacy = (
        select(
            OrganizationMembership.id,
            User.service_provider_id,
            OrganizationMembership.user_id,
            literal(None, type_=Uuid).label("department_id"),
            OrganizationMembership.organization_id,
            Role.id.label("role_id"),
            literal("ALLOW").label("effect"),
            literal("legacy_customer_membership").label("source"),
        )
        .select_from(OrganizationMembership)
        .join(User, User.id == OrganizationMembership.user_id)
        .join(
            Role,
            (Role.code == legacy_code)
            & (Role.service_provider_id == User.service_provider_id),
        )
        .outerjoin(
            CustomerAccessGrant,
            CustomerAccessGrant.legacy_membership_id == OrganizationMembership.id,
        )
        .where(CustomerAccessGrant.id.is_(None))
    )
    sources = union_all(actual, legacy).subquery()
    stmt = select(sources).where(
        sources.c.service_provider_id == actor().service_provider_id
    )
    if user_id:
        own(db, User, user_id)
        stmt = stmt.where(sources.c.user_id == user_id)
    if department_id:
        own(db, Department, department_id)
        stmt = stmt.where(sources.c.department_id == department_id)
    if organization_id:
        stmt = stmt.where(sources.c.organization_id == organization_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = (
        db.execute(stmt.order_by(sources.c.id).limit(limit).offset(offset))
        .mappings()
        .all()
    )
    return page(
        [
            {
                key: str(value) if isinstance(value, uuid.UUID) else value
                for key, value in row.items()
                if key != "service_provider_id"
            }
            for row in rows
        ],
        total,
        limit,
        offset,
    )


def prepare_grant(payload, db):
    allowed("access.manage_permissions")
    if (payload.user_id is None) == (payload.department_id is None):
        raise HTTPException(422, "Choose exactly one employee or department")
    if payload.effect not in {"ALLOW", "DENY"}:
        raise HTTPException(422, "Unknown grant effect")
    if payload.effect == "DENY" and (payload.department_id or payload.role_id):
        raise HTTPException(422, "Customer deny is employee-only and has no role")
    if payload.effect == "ALLOW" and payload.role_id is None:
        raise HTTPException(422, "Allow grant requires an assigned role")
    if db.get(Organization, payload.organization_id) is None:
        raise HTTPException(404, "Customer not found")
    if payload.user_id:
        u = own(db, User, payload.user_id, lock=True)
        protect_employee(db, u, True)
        if payload.effect == "ALLOW":
            assigned = db.scalar(
                select(UserRoleAssignment).where(
                    UserRoleAssignment.user_id == u.id,
                    UserRoleAssignment.role_id == payload.role_id,
                    UserRoleAssignment.effect == "ALLOW",
                )
            )
            if not assigned:
                raise HTTPException(
                    422,
                    "Assign this role to the employee before granting customer scope",
                )
            if db.scalar(
                select(CustomerAccessGrant.id).where(
                    CustomerAccessGrant.user_id == u.id,
                    CustomerAccessGrant.organization_id == payload.organization_id,
                    CustomerAccessGrant.effect == "DENY",
                )
            ):
                raise HTTPException(
                    409, "Remove the explicit customer deny before adding an allow"
                )
        elif db.scalar(
            select(CustomerAccessGrant.id).where(
                CustomerAccessGrant.user_id == u.id,
                CustomerAccessGrant.organization_id == payload.organization_id,
                CustomerAccessGrant.effect == "ALLOW",
                CustomerAccessGrant.legacy_membership_id.is_(None),
            )
        ):
            raise HTTPException(
                409,
                "Revoke direct allows before adding a customer deny; inherited/legacy scope may be narrowed",
            )
    else:
        d = own(db, Department, payload.department_id, lock=True)
        affected_self(db, d.id)
        if not db.scalar(
            select(DepartmentRoleAssignment.id).where(
                DepartmentRoleAssignment.department_id == d.id,
                DepartmentRoleAssignment.role_id == payload.role_id,
            )
        ):
            raise HTTPException(422, "Assign this role to the department first")
    if payload.role_id:
        delegate(db, own(db, Role, payload.role_id))
    g = CustomerAccessGrant(
        **payload.model_dump(), service_provider_id=actor().service_provider_id
    )
    db.add(g)
    db.flush()
    return g


@router.post("/customer-grants", status_code=201)
def create_grant(payload: GrantIn, db=Depends(session)):
    g = prepare_grant(payload, db)
    commit(db, "CUSTOMER_ACCESS_GRANT", "customer_grant", g.id, payload.organization_id)
    return {"id": str(g.id), "effect": g.effect}


@router.post("/customer-grants/preview")
def preview_grant(payload: GrantIn, db=Depends(session)):
    # Execute the same constraints and authorization as saving inside a savepoint.
    # No identity, grant or audit mutation survives this read-only proposal.
    with db.begin_nested() as savepoint:
        g = prepare_grant(payload, db)
        keys = (
            sorted(
                db.scalars(
                    select(RolePermission.permission_key).where(
                        RolePermission.role_id == g.role_id,
                        RolePermission.permission_key.in_(PERMISSIONS),
                    )
                )
            )
            if g.role_id
            else []
        )
        result = {"role_permissions": keys, "saved": False}
        if g.user_id:
            target = own(db, User, g.user_id, lock=True)
            result["effective"] = (
                effective_document(resolve_access(db, target))
                if target.active
                else {"disabled": True, "permissions": [], "customer_permissions": {}}
            )
        else:
            result["department_member_count"] = db.scalar(
                select(func.count())
                .select_from(DepartmentMembership)
                .join(User, User.id == DepartmentMembership.user_id)
                .where(
                    DepartmentMembership.department_id == g.department_id,
                    DepartmentMembership.active.is_(True),
                    User.active.is_(True),
                )
            )
        savepoint.rollback()
    return result


@router.delete("/customer-grants/{grant_id}", status_code=204)
def remove_grant(grant_id: uuid.UUID, db=Depends(session)):
    allowed("access.manage_permissions")
    g = db.get(CustomerAccessGrant, grant_id)
    if g is None:
        # Explicit compatibility revocation also removes its authoritative source.
        legacy = db.get(OrganizationMembership, grant_id)
        if legacy is None:
            raise HTTPException(404, "Customer grant not found")
        protect_employee(db, own(db, User, legacy.user_id, lock=True), True)
        delegate(db, own(db, Role, role_id_for_legacy(legacy.role)))
        db.delete(legacy)
        commit(
            db,
            "CUSTOMER_ACCESS_REVOKE",
            "legacy_customer_membership",
            legacy.id,
            legacy.organization_id,
        )
        return
    if g.service_provider_id != actor().service_provider_id:
        raise HTTPException(404, "Customer grant not found")
    if g.user_id:
        protect_employee(db, own(db, User, g.user_id, lock=True), True)
    else:
        own(db, Department, g.department_id, lock=True)
        affected_self(db, g.department_id)
    if g.role_id:
        delegate(db, own(db, Role, g.role_id))
    if g.legacy_membership_id:
        legacy = db.get(OrganizationMembership, g.legacy_membership_id)
        if legacy:
            db.delete(legacy)
    else:
        db.delete(g)
    commit(db, "CUSTOMER_ACCESS_REVOKE", "customer_grant", g.id, g.organization_id)


@router.get("/audit")
def access_audit(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db=Depends(session),
):
    allowed("audit.view")
    ids = select(User.id).where(User.service_provider_id == actor().service_provider_id)
    stmt = select(SecurityAuditEvent).where(SecurityAuditEvent.actor_id.in_(ids))
    stmt = stmt.where(
        SecurityAuditEvent.event_type.like("EMPLOYEE_%")
        | SecurityAuditEvent.event_type.like("DEPARTMENT_%")
        | SecurityAuditEvent.event_type.like("ROLE_%")
        | SecurityAuditEvent.event_type.like("CUSTOMER_ACCESS_%")
        | (
            (SecurityAuditEvent.outcome == "DENIED")
            & (SecurityAuditEvent.target_id.like("/api/v1/access%"))
        )
    )
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(
        stmt.order_by(SecurityAuditEvent.occurred_at.desc(), SecurityAuditEvent.id)
        .limit(limit)
        .offset(offset)
    ).all()
    return page(
        [
            {
                "id": str(e.id),
                "actor_id": str(e.actor_id),
                "action": e.event_type,
                "target_type": e.target_type,
                "target_id": e.target_id,
                "outcome": e.outcome,
                "timestamp": e.occurred_at.isoformat(),
            }
            for e in rows
        ],
        total,
        limit,
        offset,
    )


class DepartmentTransfer(Strict):
    department_id: uuid.UUID


@router.put("/employees/{user_id}/department")
def transfer_department(
    user_id: uuid.UUID, payload: DepartmentTransfer, db=Depends(session)
):
    allowed("access.manage_users")
    allowed("access.manage_departments")
    u = own(db, User, user_id, lock=True)
    protect_employee(db, u, True)
    d = own(db, Department, payload.department_id, lock=True)
    if not d.active:
        raise HTTPException(422, "Select an active department")
    for assignment in db.scalars(
        select(DepartmentRoleAssignment).where(
            DepartmentRoleAssignment.department_id == d.id
        )
    ):
        delegate(db, own(db, Role, assignment.role_id))
    rows = db.scalars(
        select(DepartmentMembership).where(DepartmentMembership.user_id == u.id)
    ).all()
    for row in rows:
        row.active = False
    db.flush()
    selected = next((r for r in rows if r.department_id == d.id), None)
    if selected:
        selected.active = True
    else:
        db.add(
            DepartmentMembership(
                user_id=u.id,
                department_id=d.id,
                service_provider_id=d.service_provider_id,
            )
        )
    commit(db, "EMPLOYEE_DEPARTMENT_TRANSFER", "employee", u.id)
    return employee_documents(db, [u])[0]
