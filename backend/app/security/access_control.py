"""Effective permission computation. Never take a cross-product of roles and customers."""

from collections import defaultdict
import hashlib, json
from uuid import UUID
from fastapi import HTTPException, Request
from sqlalchemy import select
from app.security.permission_catalog import (
    PERMISSIONS,
    LEGACY_ROLES,
    role_id,
    PROVIDER_ID,
)

# This context is consumed by ORM read/write isolation, not by the UI.
from contextvars import ContextVar

request_permissions: ContextVar[tuple[str, ...]] = ContextVar(
    "request_permissions", default=()
)


def route_permissions(method: str, path: str) -> tuple[str, ...]:
    read = method in {"GET", "HEAD"}
    path = path.rstrip("/")
    if path in {
        "/api/v1/auth/me",
        "/api/v1/auth/logout",
        "/api/v1/auth/customer-scope",
    }:
        return ()
    if path.startswith("/api/v1/data-pipelines"):
        return ("etl.view",) if read else ("etl.configure",)
    if path.startswith("/api/v1/notifications"):
        return ("alerts.view",)
    if path.startswith("/api/v1/attribute-registry"):
        return ("resources.view", "collectors.view", "etl.view")
    if path.startswith("/api/v1/resource-drafts"):
        return ("resources.create",)
    if path.startswith("/api/v1/native-incidents"):
        return (
            ("incidents.view",)
            if read
            else ("incidents.acknowledge", "incidents.manage")
        )
    if path.startswith("/api/v1/unified/"):
        if path == "/api/v1/unified/import/validate":
            return ("templates.view",)
        if "/parameters/" in path:
            return (
                ("templates.view",)
                if read or path.endswith("/preview") or path.endswith("/import")
                else ("templates.manage",)
            )
        if path.endswith("/alert-setup"):
            return ("alerts.view",) if read else ("templates.manage",)
        if "/pipeline-platforms/" in path:
            return ("etl.view",)
        if path.endswith("/test-connection"):
            return ("etl.configure",)
        if path.endswith("/start-probe"):
            return ("collectors.manage",)
        if path.endswith("/activate") or "/dependencies" in path:
            return ("resources.view",) if read else ("resources.update",)
        if "/executions/" in path:
            return ("etl.view",) if read else ("etl.investigate",)
        if path.endswith("/executions") or path.endswith("/schedule-windows"):
            return ("etl.view",)
        if "/reports" in path:
            return ("reports.view",)
        if "/overview" in path:
            return ("overview.view",)
        if path.endswith("/domain-state/ETL"):
            return ("etl.view",)
        if path == "/api/v1/unified/alerts":
            return ("alerts.view",)
        if "/correlations" in path:
            return ("alerts.view",)
        return (
            ("resources.view",)
            if read
            else (
                {
                    "POST": "resources.create",
                    "PUT": "resources.update",
                    "DELETE": "resources.delete",
                }.get(method, "unsupported"),
            )
        )
    if path.startswith("/api/v1/agent-control"):
        return ("collectors.view",) if read else ("collectors.manage",)
    if path.startswith("/api/v1/event-parameters") or path.startswith(
        "/api/v1/notification-delivery"
    ):
        return ("templates.view",) if read else ("templates.manage",)
    if path.startswith("/api/v1/access"):
        return ("access.view",)  # Individual services require their exact action too.
    if path.startswith("/api/v1/auth/"):
        return ("audit.view",) if path == "/api/v1/auth/audit" else ("access.view",)
    if (
        path.startswith("/api/v1/organizations")
        or path == "/api/v1/monitoring/organizations"
    ):
        return (
            ("customers.view",)
            if read
            else (("customers.create",) if method == "POST" else ("customers.update",))
        )
    if path.startswith("/api/v1/etl/"):
        return (
            ("etl.view",)
            if read
            else (
                ("etl.investigate",)
                if "/investigation" in path or path.endswith("/correlation")
                else ("etl.configure",)
            )
        )
    if path.startswith("/api/v1/operations/overview"):
        return ("overview.view",)
    if path.startswith("/api/v1/operations/alerts"):
        return ("alerts.view",) if read else ("alerts.acknowledge",)
    if path.startswith("/api/v1/operations/reports") or path.startswith(
        "/api/v1/operations/history"
    ):
        return ("reports.view",)
    if path.startswith("/api/v1/operations/jobs"):
        return ("etl.view",)
    if path.startswith("/api/v1/operations/collectors"):
        return ("collectors.view",)
    if path.startswith("/api/v1/operations/services") or path.startswith(
        "/api/v1/infrastructure"
    ):
        return ("resources.view",)
    if path.startswith("/api/v1/resource-discovery"):
        return ("resources.view",) if read else ("collectors.manage",)
    if (
        path.startswith("/api/v1/rule-catalogs")
        or "/templates" in path
        or "/alert-rules" in path
    ):
        return ("templates.view",) if read else ("templates.manage",)
    if path.startswith("/api/v1/remote-probes"):
        return ("collectors.view",) if read else ("collectors.manage",)
    if path.startswith("/api/v1/data-sources"):
        return ("collectors.view",) if read else ("collectors.manage",)
    if path.startswith(("/api/v1/resource-management/", "/api/v1/monitoring/")):
        if "/collectors" in path:
            return ("collectors.view",) if read else ("collectors.manage",)
        if "/alerts" in path or "/correlations" in path:
            return ("alerts.view",)
        if "/logs" in path:
            return ("logs.view",) if read else ("logs.manage",)
        return (
            ("resources.view",)
            if read
            else (
                {
                    "POST": ("resources.create",),
                    "PATCH": ("resources.update",),
                    "PUT": ("resources.update",),
                    "DELETE": ("resources.delete",),
                }.get(method, ("unsupported",))
            )
        )
    return ("unsupported",)


def require_permission(key: str, customer_id: UUID | None = None):
    from app.security.scope import current_principal

    p = current_principal.get()
    if p is None:
        raise HTTPException(401, "Authentication required")
    if not p.allows(key, customer_id):
        raise HTTPException(403, "Permission required")
    return p


def authorize_route(request: Request):
    # Explicit API/service dependency is defense in depth to the middleware.
    path = request.url.path.rstrip("/")
    if (
        not path.startswith("/api/")
        or path == "/api/v1/auth/login"
        or path.startswith("/api/v1/worker/")
    ):
        return
    keys = route_permissions(request.method, path)
    from app.security.scope import current_principal

    p = current_principal.get()
    if p is None:
        raise HTTPException(401, "Authentication required")
    if keys and not any(p.allows(k) for k in keys):
        raise HTTPException(403, "Permission required")


def resolve_access(db, user):
    from app.models import Organization
    from app.security.models import OrganizationMembership
    from app.security.access_models import (
        ServiceProvider,
        Department,
        DepartmentMembership,
        Role,
        RolePermission,
        UserRoleAssignment,
        DepartmentRoleAssignment,
        CustomerAccessGrant,
    )
    from app.security.scope import Principal

    provider = db.get(ServiceProvider, user.service_provider_id)
    if (
        provider is None
        or not provider.active
        or user.service_provider_id != PROVIDER_ID
    ):
        return None
    roles = {
        r.id: r
        for r in db.scalars(
            select(Role).where(
                Role.service_provider_id == user.service_provider_id,
                Role.active.is_(True),
            )
        )
    }
    permissions = defaultdict(set)
    for rid, key in db.execute(
        select(RolePermission.role_id, RolePermission.permission_key).where(
            RolePermission.active.is_(True)
        )
    ):
        if key not in PERMISSIONS:
            continue
        if rid in roles:
            permissions[rid].add(key)
    assignments = list(
        db.scalars(
            select(UserRoleAssignment).where(UserRoleAssignment.user_id == user.id)
        )
    )
    direct = {
        a.role_id for a in assignments if a.effect == "ALLOW" and a.role_id in roles
    }
    deny = (
        set().union(
            *(permissions[a.role_id] for a in assignments if a.effect == "DENY")
        )
        if assignments
        else set()
    )
    departments = set(
        db.scalars(
            select(DepartmentMembership.department_id)
            .join(Department, Department.id == DepartmentMembership.department_id)
            .where(
                DepartmentMembership.user_id == user.id,
                DepartmentMembership.active.is_(True),
                Department.active.is_(True),
                Department.service_provider_id == user.service_provider_id,
            )
        )
    )
    protected_roles = {a.role_id for a in assignments}
    dept_roles = defaultdict(set)
    for a in db.scalars(
        select(DepartmentRoleAssignment).where(
            DepartmentRoleAssignment.department_id.in_(departments)
        )
    ):
        protected_roles.add(a.role_id)
        if a.role_id in roles:
            dept_roles[a.department_id].add(a.role_id)
    all_roles = (
        direct | set().union(*dept_roles.values()) if dept_roles else direct.copy()
    )
    global_keys = {
        k
        for rid in all_roles
        for k in permissions[rid]
        if k.startswith("access.") or k in {"audit.view", "customers.create"}
    }
    customer_keys = defaultdict(set)
    provenance = []
    for source, subject_id, assigned in [("employee", user.id, direct)] + [
        ("department", did, assigned) for did, assigned in dept_roles.items()
    ]:
        for rid in assigned:
            keys = {
                k
                for k in permissions[rid]
                if k.startswith("access.") or k in {"audit.view", "customers.create"}
            } - deny
            provenance.append(
                {
                    "source": source,
                    "subject_id": str(subject_id),
                    "scope": "provider",
                    "role_id": str(rid),
                    "role": roles[rid].name,
                    "permissions": sorted(keys),
                    "customer_scope_required": any(
                        not (
                            key.startswith("access.")
                            or key in {"audit.view", "customers.create"}
                        )
                        for key in permissions[rid]
                    ),
                }
            )
    grants = list(
        db.scalars(
            select(CustomerAccessGrant).where(
                CustomerAccessGrant.service_provider_id == user.service_provider_id,
                (CustomerAccessGrant.user_id == user.id)
                | CustomerAccessGrant.department_id.in_(departments),
            )
        )
    )
    denied_customers = {
        g.organization_id for g in grants if g.user_id == user.id and g.effect == "DENY"
    }
    legacy_memberships = list(
        db.scalars(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user.id
            )
        )
    )
    candidates = {g.organization_id for g in grants} | {
        m.organization_id for m in legacy_memberships
    }
    customer_stmt = select(Organization.id, Organization.name, Organization.code).where(
        Organization.active.is_(True)
    )
    if not user.platform_admin:
        customer_stmt = customer_stmt.where(Organization.id.in_(candidates))
    directory = {row.id: (row.name, row.code) for row in db.execute(customer_stmt)}
    active_customers = set(directory)
    for g in grants:
        if (
            g.effect != "ALLOW"
            or g.legacy_membership_id
            or g.organization_id not in active_customers
        ):
            continue
        applies = (g.user_id == user.id and g.role_id in direct) or (
            g.department_id in departments and g.role_id in dept_roles[g.department_id]
        )
        if applies:
            customer_keys[g.organization_id].update(
                k
                for k in permissions[g.role_id]
                if not k.startswith("access.")
                and k not in {"audit.view", "customers.create"}
            )
            provenance.append(
                {
                    "source": "department" if g.department_id else "employee",
                    "subject_id": str(g.department_id or user.id),
                    "customer_id": str(g.organization_id),
                    "role_id": str(g.role_id),
                    "role": roles[g.role_id].name,
                    "permissions": sorted(permissions[g.role_id]),
                }
            )
    # Legacy consumers and direct CLI seeds remain equivalent customer grants,
    # not departments or global administration. Re-read them every request.
    for m in legacy_memberships:
        rid = role_id(LEGACY_ROLES.get(m.role, ""))
        if m.organization_id in active_customers and rid in roles:
            all_roles.add(rid)
            protected_roles.add(rid)
            customer_keys[m.organization_id].update(permissions[rid])
            provenance.append(
                {
                    "source": "legacy_customer_membership",
                    "subject_id": str(m.id),
                    "customer_id": str(m.organization_id),
                    "role_id": str(rid),
                    "role": roles[rid].name,
                    "permissions": sorted(permissions[rid]),
                }
            )
    for org in list(customer_keys):
        customer_keys[org].difference_update(deny)
        if org in denied_customers:
            customer_keys.pop(org)
    global_keys.difference_update(deny)
    effective_global = global_keys | {
        k for keys in customer_keys.values() for k in keys
    }
    compatibility = {
        org: (
            "org_admin"
            if "resources.update" in keys
            else (
                "operator"
                if {"etl.investigate", "incidents.manage"} & keys
                else "viewer"
            )
        )
        for org, keys in customer_keys.items()
        if keys
    }
    revision = hashlib.sha256(
        json.dumps(
            {
                "global": sorted(effective_global),
                "customers": {str(k): sorted(v) for k, v in customer_keys.items()},
                "admin": user.platform_admin,
                "authorization_roles": sorted(str(rid) for rid in protected_roles),
                "customer_directory": {
                    str(cid): directory[cid]
                    for cid in sorted(directory, key=str)
                    if user.platform_admin or cid in compatibility
                },
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()
    return Principal(
        user.id,
        user.username,
        user.platform_admin,
        compatibility,
        user.service_provider_id,
        frozenset(effective_global),
        {k: frozenset(v) for k, v in customer_keys.items()},
        tuple(provenance),
        frozenset(protected_roles),
        frozenset(denied_customers),
        frozenset(deny),
        revision,
    )


def effective_document(p):
    return {
        "user_id": str(p.user_id),
        "service_provider_id": str(p.service_provider_id),
        "platform_admin": p.platform_admin,
        "permissions": sorted(PERMISSIONS if p.platform_admin else p.permissions),
        "customer_permissions": {
            str(k): sorted(v) for k, v in (p.customer_permissions or {}).items()
        },
        "inherited_and_direct": list(p.provenance),
        "role_ids": sorted(str(rid) for rid in p.role_ids),
        "denied_customers": [str(k) for k in p.denied_customers],
        "denied_permissions": sorted(p.denied_permissions),
        "authorization_revision": p.authorization_revision,
        "break_glass": p.platform_admin,
    }
