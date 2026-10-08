from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Organization
from app.schemas.organization import OrganizationCreate, OrganizationOut, OrganizationUpdate

router = APIRouter(prefix="/api/v1/organizations", tags=["Organizations"])


def _get(db: Session, organization_id: UUID) -> Organization:
    item = db.get(Organization, organization_id)
    if not item:
        raise HTTPException(status_code=404, detail="Organization not found")
    return item


@router.get("", response_model=list[OrganizationOut])
def list_organizations(
    active: bool | None = Query(default=None),
    limit: int = Query(500, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    stmt = select(Organization).order_by(Organization.name).limit(limit)
    if active is not None:
        stmt = stmt.where(Organization.active == active)
    return db.scalars(stmt).all()


@router.get("/{organization_id}", response_model=OrganizationOut)
def get_organization(organization_id: UUID, db: Session = Depends(get_db)):
    return _get(db, organization_id)


@router.post("", response_model=OrganizationOut, status_code=201)
def create_organization(payload: OrganizationCreate, db: Session = Depends(get_db)):
    item = Organization(**payload.model_dump())
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Organization name or code already exists")
    db.refresh(item)
    return item


@router.patch("/{organization_id}", response_model=OrganizationOut)
def update_organization(
    organization_id: UUID,
    payload: OrganizationUpdate,
    db: Session = Depends(get_db),
):
    item = _get(db, organization_id)
    values = payload.model_dump(exclude_unset=True)
    for key, value in values.items():
        setattr(item, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Organization name or code already exists")
    db.refresh(item)
    return item


@router.delete("/{organization_id}", response_model=OrganizationOut)
def disable_organization(organization_id: UUID, db: Session = Depends(get_db)):
    item = _get(db, organization_id)
    item.active = False
    db.commit()
    db.refresh(item)
    return item
