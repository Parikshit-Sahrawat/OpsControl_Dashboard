"""Validated boundaries consumed by the canonical resolver and scoped ORM.

Policy rows constrain existing role/customer assignments. Only an explicit ALL
policy can extend an assigned role to future customers. No defaults are seeded.
"""

from typing import Literal
from uuid import UUID
from contextvars import ContextVar
from datetime import datetime, timezone
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select, text

selected_customers: ContextVar[frozenset[UUID] | None] = ContextVar(
    "selected_customers", default=None
)


class Specification(BaseModel):
    model_config = ConfigDict(extra="forbid")
    permissions: list[str] = Field(default_factory=list, max_length=100)
    customers: list[UUID] = Field(default_factory=list, max_length=2000)
    departments: list[UUID] = Field(default_factory=list, max_length=500)
    environments: list[Literal["PROD", "QA", "TEST", "DEV", "SANDBOX"]] = Field(
        default_factory=list, max_length=5
    )
    resources: list[UUID] = Field(default_factory=list, max_length=2000)
    role_id: UUID | None = None
    include_future: bool = False
    create_departments: bool = False

    @model_validator(mode="after")
    def unique(self):
        from app.security.permission_catalog import PERMISSIONS

        for values in (
            self.permissions,
            self.customers,
            self.departments,
            self.environments,
            self.resources,
        ):
            if len(values) != len(set(values)):
                raise ValueError("Duplicate boundary values")
        if not set(self.permissions) <= PERMISSIONS.keys():
            raise ValueError("Unknown implemented permission")
        return self


def specification(kind, value):
    s = Specification.model_validate(value)
    if kind in {"LIMIT", "DENY"}:
        if (
            not s.permissions
            or not s.customers
            or s.departments
            or s.role_id
            or s.include_future
        ):
            raise ValueError("Restrictions require exact permissions/customers only")
        if kind == "LIMIT" and not (s.environments or s.resources):
            raise ValueError("A LIMIT requires environment or resource scope")
    elif kind == "DELEGATE":
        if (
            not s.departments
            or not s.permissions
            or s.role_id
            or s.include_future
            or s.environments
            or s.resources
        ):
            raise ValueError(
                "Delegation requires department, customer and permission budget; no ALL or resource ambiguity"
            )
    elif kind == "ALL_CUSTOMERS":
        if (
            not s.role_id
            or not s.permissions
            or s.departments
            or s.environments
            or s.resources
        ):
            raise ValueError(
                "ALL requires an assigned role and explicit permission snapshot"
            )
        if not s.include_future and not s.customers:
            raise ValueError("Snapshot ALL requires explicit current customers")
    else:
        raise ValueError("Unsupported boundary kind")
    if kind != "DELEGATE" and s.create_departments:
        raise ValueError("Department creation authority requires explicit delegation")
    return s.model_dump(mode="json")


def relevant(p, customer, permission):
    return [
        b
        for b in p.boundaries
        if b["kind"] in {"LIMIT", "DENY"}
        and str(customer) in b["specification"]["customers"]
        and permission in b["specification"]["permissions"]
    ]


def permits(p, key, customer, environment=None, resource=None):
    rows = relevant(p, customer, key)
    if not rows:
        return True

    def match(b):
        s = b["specification"]
        return (not s["environments"] or environment in s["environments"]) and (
            not s["resources"] or str(resource) in s["resources"]
        )

    limits = [b for b in rows if b["kind"] == "LIMIT"]
    return (not limits or all(map(match, limits))) and not any(
        match(b) for b in rows if b["kind"] == "DENY"
    )


def choose(principal, request):
    """No selection means empty. Query IDs and a strict header are filters only."""
    raw = request.headers.get("x-opscontrol-customers")
    explicit = request.query_params.getlist(
        "organization_id"
    ) + request.query_params.getlist("organization_ids")
    if raw is not None:
        if raw == "ALL":
            if not principal.all_customers:
                raise HTTPException(403, "Explicit ALL-customer authority required")
            chosen = set(principal.customer_directory_ids)
        elif raw == "":
            chosen = set()
        else:
            try:
                chosen = {UUID(v) for v in raw.split(",")}
            except (ValueError, TypeError):
                raise HTTPException(
                    422, "Use immutable customer UUIDs, not wildcard scope"
                ) from None
        if explicit:
            try:
                chosen.intersection_update(UUID(v) for v in explicit)
            except ValueError:
                raise HTTPException(422, "Invalid customer selection") from None
    else:
        try:
            chosen = {UUID(v) for v in explicit}
        except ValueError:
            raise HTTPException(422, "Invalid customer selection") from None
    return frozenset(chosen & set(principal.customer_directory_ids))


def transaction_authority(db):
    """Same lock as access mutations: revocation cannot race a decision commit."""
    from app.security.scope import current_principal
    from app.security.http import actor
    from app.security.access_control import resolve_access
    from app.security.models import User, AccessSession
    from app.db.session import SessionLocal

    p = actor()
    db.execute(text("SELECT pg_advisory_xact_lock(782104, 8)"))
    with SessionLocal() as auth:
        u = auth.get(User, p.user_id)
        fresh = resolve_access(auth, u) if u and u.active else None
        if fresh is None or fresh.authorization_revision != p.authorization_revision:
            raise HTTPException(403, "Authorization changed; refresh your session")
        # The middleware revalidates credentials for every request. A transaction
        # also checks that this exact session survived administrative revocation.
        from app.security.http import request_session_digest

        digest = request_session_digest.get()
        if digest and not auth.scalar(
            select(AccessSession.id).where(
                AccessSession.token_hash == digest,
                AccessSession.expires_at > datetime.now(timezone.utc),
            )
        ):
            raise HTTPException(401, "Session revoked")
    return current_principal.get()


def delegation(p):
    result = {"departments": set(), "customers": set(), "permissions": set()}
    for b in p.boundaries:
        if b["kind"] == "DELEGATE":
            for k in result:
                result[k].update(b["specification"][k])
    return result
