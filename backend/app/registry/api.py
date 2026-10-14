import json, uuid
from typing import Annotated, Literal
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import Field, TypeAdapter, ValidationError
from sqlalchemy import select, func
from app.db.session import get_db
from app.security.scope import current_principal
from app.security.access_control import require_permission
from app.security.secret_refs import require_safe_config
from app.security.audit import log_event
from app.registry.models import AttributeRegistryVersion, ResourceDraft
from app.unified.schemas import Strict, VMCreate, ETLCreate, APICreate
from app.unified.api import document, commit, resource

router = APIRouter(tags=["Attribute Registry and Onboarding"])


class DraftInput(Strict):
    domain: Literal["VM", "ETL", "API"]
    name: str = Field(min_length=1, max_length=160)
    organization_id: uuid.UUID | None = None
    stage: int = Field(ge=1, le=10)
    configuration: dict
    expected_revision: int | None = Field(default=None, ge=1)


def validate_draft(payload, db=None):
    require_safe_config(payload.configuration)
    if len(json.dumps(payload.configuration, default=str)) > 256 * 1024:
        raise ValueError("Draft exceeds256KiB")
    schema = {"VM": VMCreate, "ETL": ETLCreate, "API": APICreate}[payload.domain]
    for key, value in payload.configuration.items():
        if key == "resource_id":
            if value:
                id = uuid.UUID(str(value))
                if db is not None:
                    linked = resource(db, id)
                    if linked.domain != payload.domain or (
                        payload.organization_id
                        and linked.organization_id != payload.organization_id
                    ):
                        raise ValueError("Draft resource scope does not match")
            continue
        if key not in schema.model_fields:
            raise ValueError("Unsupported draft attribute: " + key)
        if value == "" or value is None:
            continue  # Incomplete fields are allowed only in drafts.
        field = schema.model_fields[key]
        TypeAdapter(Annotated[field.annotation, field]).validate_python(value)
    org = payload.configuration.get("organization_id")
    if org and str(payload.organization_id) != str(org):
        raise ValueError("Draft customer fields must agree")
    return payload.configuration


def owner(db):
    p = current_principal.get()
    if not p or not p.service_provider_id:
        raise HTTPException(403, "Provider identity required")
    return p


def lookup(db, id, write=False):
    p = owner(db)
    q = select(ResourceDraft).where(
        ResourceDraft.id == id,
        ResourceDraft.owner_id == p.user_id,
        ResourceDraft.service_provider_id == p.service_provider_id,
    )
    value = db.scalar(q.with_for_update() if write else q)
    if not value:
        raise HTTPException(404, "Draft unavailable")
    if value.organization_id:
        require_permission("resources.create", value.organization_id)
    return value


@router.get("/api/v1/attribute-registry")
def registry(version: int | None = None, db=Depends(get_db)):
    q = select(AttributeRegistryVersion)
    if version:
        q = q.where(AttributeRegistryVersion.version == version)
    value = db.scalar(q.order_by(AttributeRegistryVersion.version.desc()).limit(1))
    if not value:
        raise HTTPException(503, "Attribute registry migration is not installed")
    return {
        "version": value.version,
        "definitions": value.definitions,
        "capabilities": value.capabilities,
        "sha256": value.sha256,
    }


@router.get("/api/v1/resource-drafts")
def drafts(
    domain: Literal["VM", "ETL", "API"] | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db=Depends(get_db),
):
    p = owner(db)
    q = select(ResourceDraft).where(
        ResourceDraft.owner_id == p.user_id,
        ResourceDraft.service_provider_id == p.service_provider_id,
    )
    if domain:
        q = q.where(ResourceDraft.domain == domain)
    return {
        "items": [
            document(v)
            for v in db.scalars(
                q.order_by(ResourceDraft.updated_at.desc(), ResourceDraft.id)
                .offset(offset)
                .limit(limit)
            )
        ],
        "total": db.scalar(select(func.count()).select_from(q.subquery())),
    }


@router.get("/api/v1/resource-drafts/{id}")
def get_draft(id: uuid.UUID, db=Depends(get_db)):
    return document(lookup(db, id))


@router.post("/api/v1/resource-drafts", status_code=201)
def create_draft(payload: DraftInput, db=Depends(get_db)):
    p = owner(db)
    if payload.organization_id:
        require_permission("resources.create", payload.organization_id)
    try:
        configuration = validate_draft(payload, db)
    except ValueError:
        raise HTTPException(
            422, "Draft configuration contains invalid attributes or unsafe values"
        ) from None
    value = ResourceDraft(
        service_provider_id=p.service_provider_id,
        owner_id=p.user_id,
        domain=payload.domain,
        name=payload.name,
        organization_id=payload.organization_id,
        stage=payload.stage,
        configuration=configuration,
    )
    db.add(value)
    db.flush()
    log_event(
        db,
        event_type="RESOURCE_DRAFT_CREATE",
        outcome="SUCCESS",
        actor_id=p.user_id,
        organization_id=payload.organization_id,
        target_type="resource_draft",
        target_id=value.id,
    )
    commit(db)
    return document(value)


@router.put("/api/v1/resource-drafts/{id}")
def update_draft(id: uuid.UUID, payload: DraftInput, db=Depends(get_db)):
    value = lookup(db, id, True)
    p = owner(db)
    if payload.domain != value.domain:
        raise HTTPException(409, "Draft domain is immutable")
    if payload.expected_revision != value.revision:
        raise HTTPException(409, "Draft changed; refresh before saving")
    if payload.organization_id:
        require_permission("resources.create", payload.organization_id)
    try:
        configuration = validate_draft(payload, db)
    except ValueError:
        raise HTTPException(
            422, "Draft configuration contains invalid attributes or unsafe values"
        ) from None
    value.name = payload.name
    value.organization_id = payload.organization_id
    value.stage = payload.stage
    value.configuration = configuration
    value.revision += 1
    log_event(
        db,
        event_type="RESOURCE_DRAFT_UPDATE",
        outcome="SUCCESS",
        actor_id=p.user_id,
        organization_id=value.organization_id,
        target_type="resource_draft",
        target_id=value.id,
    )
    commit(db)
    return document(value)


@router.delete("/api/v1/resource-drafts/{id}", status_code=204)
def delete_draft(id: uuid.UUID, db=Depends(get_db)):
    value = lookup(db, id, True)
    db.delete(value)
    commit(db)
    return Response(status_code=204)
