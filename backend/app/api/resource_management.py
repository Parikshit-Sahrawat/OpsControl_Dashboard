from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Collector, DataSource, Organization
from app.schemas.monitoring import CollectorCreate, CollectorOut, CollectorUpdate, DataSourceCreate, DataSourceOut, DataSourceUpdate

router = APIRouter(prefix="/api/v1/resource-management", tags=["Resource Management"])


def _org(db: Session, organization_id: UUID, require_active: bool = False) -> Organization:
    item = db.get(Organization, organization_id)
    if not item:
        raise HTTPException(status_code=404, detail="Organization not found")
    if require_active and not item.active:
        raise HTTPException(status_code=409, detail="Organization is inactive")
    return item


def _source(db: Session, data_source_id: UUID) -> DataSource:
    item = db.get(DataSource, data_source_id)
    if not item:
        raise HTTPException(status_code=404, detail="Data source not found")
    return item


@router.get("/data-sources", response_model=list[DataSourceOut])
def list_scoped_data_sources(
    organization_id: list[UUID] = Query(default=[]),
    enabled: bool | None = None,
    limit: int = Query(500, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    stmt = select(DataSource).order_by(DataSource.name).limit(limit)
    if organization_id:
        stmt = stmt.where(DataSource.organization_id.in_(organization_id))
    if enabled is not None:
        stmt = stmt.where(DataSource.enabled == enabled)
    return db.scalars(stmt).all()


@router.post("/data-sources", response_model=DataSourceOut, status_code=201)
def create_scoped_data_source(payload: DataSourceCreate, db: Session = Depends(get_db)):
    _org(db, payload.organization_id, require_active=True)
    item = DataSource(**payload.model_dump())
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Data source name already exists in this organization")
    db.refresh(item)
    return item


@router.patch("/data-sources/{data_source_id}", response_model=DataSourceOut)
def update_scoped_data_source(
    data_source_id: UUID,
    payload: DataSourceUpdate,
    db: Session = Depends(get_db),
):
    item = _source(db, data_source_id)
    values = payload.model_dump(exclude_unset=True)
    for key, value in values.items():
        setattr(item, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Data source name already exists in this organization")
    db.refresh(item)
    return item


@router.delete("/data-sources/{data_source_id}", status_code=204)
def disable_scoped_data_source(data_source_id: UUID, db: Session = Depends(get_db)):
    item = _source(db, data_source_id)
    item.enabled = False
    db.commit()


@router.get("/collectors", response_model=list[CollectorOut])
def list_scoped_collectors(
    data_source_id: list[UUID] = Query(default=[]),
    limit: int = Query(500, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    stmt = select(Collector).order_by(Collector.name).limit(limit)
    if data_source_id:
        stmt = stmt.where(Collector.data_source_id.in_(data_source_id))
    else:
        return []
    return db.scalars(stmt).all()


@router.post("/collectors", response_model=CollectorOut, status_code=201)
def create_scoped_collector(payload: CollectorCreate, db: Session = Depends(get_db)):
    source = _source(db, payload.data_source_id)
    if not source.enabled:
        raise HTTPException(status_code=409, detail="Cannot add a collector to a disabled data source")
    item = Collector(**payload.model_dump())
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Collector name already exists for this data source")
    db.refresh(item)
    return item


@router.patch("/collectors/{collector_id}", response_model=CollectorOut)
def update_scoped_collector(
    collector_id: UUID,
    payload: CollectorUpdate,
    db: Session = Depends(get_db),
):
    item = db.get(Collector, collector_id)
    if not item:
        raise HTTPException(status_code=404, detail="Collector not found")
    values = payload.model_dump(exclude_unset=True)
    for key, value in values.items():
        setattr(item, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Collector name already exists for this data source")
    db.refresh(item)
    return item


@router.delete("/collectors/{collector_id}", status_code=204)
def disable_scoped_collector(collector_id: UUID, db: Session = Depends(get_db)):
    item = db.get(Collector, collector_id)
    if not item:
        raise HTTPException(status_code=404, detail="Collector not found")
    item.enabled = False
    item.status = "STOPPED"
    db.commit()
