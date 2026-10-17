"""Audited, revision/idempotency protected controls on existing access grants."""

import hashlib, json, uuid
from typing import Literal
from fastapi import Depends, HTTPException
from pydantic import Field
from sqlalchemy import select
from app.api.access import router, session, Strict, own, allowed, commit
from app.security.http import actor
from app.security.access_models import (
    AccessBoundary,
    AccessBoundaryDecision,
    UserRoleAssignment,
    DepartmentRoleAssignment,
    Department,
    Role,
)
from app.security.models import User
from app.security.boundaries import Specification, specification
from app.models import Organization
from app.unified.models import MonitoringResource


class BoundaryInput(Strict):
    user_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    kind: Literal["LIMIT", "DENY", "DELEGATE", "ALL_CUSTOMERS"]
    specification: Specification
    active: bool = True
    expected_revision: int | None = Field(default=None, ge=1)
    idempotency_key: str = Field(min_length=1, max_length=120)
    reason: str = Field(min_length=10, max_length=2000)


def document(row):
    return {
        k: (
            str(getattr(row, k))
            if k in {"id", "user_id", "department_id"} and getattr(row, k)
            else getattr(row, k)
        )
        for k in (
            "id",
            "user_id",
            "department_id",
            "kind",
            "specification",
            "active",
            "revision",
        )
    }


@router.get("/boundaries")
def boundaries(db=Depends(session)):
    allowed("access.view")
    if not actor().platform_admin:
        return {"items": list(actor().boundaries), "editable": False}
    rows = db.scalars(
        select(AccessBoundary)
        .where(AccessBoundary.service_provider_id == actor().service_provider_id)
        .order_by(AccessBoundary.id)
    ).all()
    return {"items": [document(r) for r in rows], "editable": True}


def save(db, payload, id=None):
    allowed("access.manage_permissions")
    if not actor().platform_admin:
        raise HTTPException(
            403, "Explicit boundary/delegation/ALL authority is platform-controlled"
        )
    if (payload.user_id is None) == (payload.department_id is None):
        raise HTTPException(422, "Choose exactly one employee or department")
    if payload.expected_revision is not None and id is None:
        raise HTTPException(422, "Creation has no prior revision")
    if id and payload.expected_revision is None:
        raise HTTPException(422, "Expected revision required")
    target = own(
        db,
        User if payload.user_id else Department,
        payload.user_id or payload.department_id,
        lock=True,
    )
    try:
        spec = specification(
            payload.kind, payload.specification.model_dump(mode="json")
        )
    except ValueError as e:
        raise HTTPException(422, str(e)) from None
    for model, ids in (
        (Organization, spec["customers"]),
        (Department, spec["departments"]),
    ):
        if len(set(db.scalars(select(model.id).where(model.id.in_(ids))))) != len(ids):
            raise HTTPException(422, "Unknown scoped identity")
    if spec["resources"]:
        rows = list(
            db.scalars(
                select(MonitoringResource).where(
                    MonitoringResource.id.in_(spec["resources"])
                )
            )
        )
        if len(rows) != len(spec["resources"]) or any(
            str(r.organization_id) not in spec["customers"] for r in rows
        ):
            raise HTTPException(422, "Resource/customer ownership mismatch")
    if payload.kind == "ALL_CUSTOMERS" and payload.active:
        own(db, Role, uuid.UUID(spec["role_id"]))
        assignment = UserRoleAssignment if payload.user_id else DepartmentRoleAssignment
        subject = assignment.user_id if payload.user_id else assignment.department_id
        query = select(assignment.id).where(
            subject == target.id, assignment.role_id == uuid.UUID(spec["role_id"])
        )
        if payload.user_id:
            query = query.where(assignment.effect == "ALLOW")
        if not db.scalar(query):
            raise HTTPException(
                422, "ALL requires the matching existing role assignment"
            )
        from app.security.access_models import RolePermission

        keys = set(
            db.scalars(
                select(RolePermission.permission_key).where(
                    RolePermission.role_id == uuid.UUID(spec["role_id"]),
                    RolePermission.active.is_(True),
                )
            )
        )
        if not set(spec["permissions"]) <= keys or any(
            k.startswith("access.") or k in {"audit.view", "customers.create"}
            for k in spec["permissions"]
        ):
            raise HTTPException(
                422, "ALL cannot invent role permissions or administrative access"
            )
    signature = hashlib.sha256(
        json.dumps(
            {"id": str(id), "body": payload.model_dump(mode="json")}, sort_keys=True
        ).encode()
    ).hexdigest()
    previous = db.scalar(
        select(AccessBoundaryDecision).where(
            AccessBoundaryDecision.actor_id == actor().user_id,
            AccessBoundaryDecision.request_key == payload.idempotency_key,
        )
    )
    if previous:
        if previous.request_hash != signature:
            raise HTTPException(
                409, "Idempotency key already used for different boundary decision"
            )
        return previous.evidence["after"]
    if id:
        row = own(db, AccessBoundary, id, lock=True)
        if row.revision != payload.expected_revision:
            raise HTTPException(409, "Boundary revision changed")
        if (
            row.user_id != payload.user_id
            or row.department_id != payload.department_id
            or row.kind != payload.kind
        ):
            raise HTTPException(422, "Boundary subject/kind is immutable")
        before = document(row)
        row.specification = spec
        row.active = payload.active
        row.revision += 1
    else:
        row = AccessBoundary(
            service_provider_id=actor().service_provider_id,
            user_id=payload.user_id,
            department_id=payload.department_id,
            kind=payload.kind,
            specification=spec,
            active=payload.active,
            revision=1,
        )
        db.add(row)
        db.flush()
        before = None
    after = document(row)
    db.add(
        AccessBoundaryDecision(
            boundary_id=row.id,
            actor_id=actor().user_id,
            request_key=payload.idempotency_key,
            request_hash=signature,
            reason=payload.reason,
            revision=row.revision,
            evidence={"before": before, "after": after},
        )
    )
    commit(db, "ACCESS_BOUNDARY_DECISION", "access_boundary", row.id)
    return after


@router.post("/boundaries", status_code=201)
def create_boundary(payload: BoundaryInput, db=Depends(session)):
    return save(db, payload)


@router.patch("/boundaries/{boundary_id}")
def update_boundary(
    boundary_id: uuid.UUID, payload: BoundaryInput, db=Depends(session)
):
    return save(db, payload, boundary_id)
