from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import AlertRule, Collector, CollectorRun, DataSource, LogSource, MetricDefinition, Organization
from app.schemas.monitoring import (
    AlertRuleCreate,
    AlertRuleOut,
    AlertRuleUpdate,
    CollectorCreate,
    CollectorOut,
    CollectorUpdate,
    CollectorRunOut,
    DataSourceCreate,
    DataSourceOut,
    DataSourceUpdate,
    LogSourceCreate,
    LogSourceOut,
    LogSourceUpdate,
    MetricDefinitionCreate,
    MetricDefinitionOut,
    MetricDefinitionUpdate,
    OrganizationOut,
)

router = APIRouter(prefix="/api/v1/monitoring", tags=["Monitoring Configuration"])


def _get_or_404(model, item_id: UUID, db: Session, label: str):
    item = db.get(model, item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"{label} not found")
    return item


@router.get("/data-sources", response_model=list[DataSourceOut])
def list_data_sources(
    organization_id: UUID | None = None,
    source_type: str | None = None,
    enabled: bool | None = None,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    stmt = select(DataSource).order_by(DataSource.name).limit(limit)
    if organization_id:
        stmt = stmt.where(DataSource.organization_id == organization_id)
    if source_type:
        stmt = stmt.where(DataSource.source_type == source_type)
    if enabled is not None:
        stmt = stmt.where(DataSource.enabled == enabled)
    return db.scalars(stmt).all()


@router.get("/data-sources/{item_id}", response_model=DataSourceOut)
def get_data_source(item_id: UUID, db: Session = Depends(get_db)):
    return _get_or_404(DataSource, item_id, db, "Data source")


@router.post("/data-sources", response_model=DataSourceOut, status_code=201)
def create_data_source(payload: DataSourceCreate, db: Session = Depends(get_db)):
    item = DataSource(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/data-sources/{item_id}", response_model=DataSourceOut)
def update_data_source(item_id: UUID, payload: DataSourceUpdate, db: Session = Depends(get_db)):
    item = _get_or_404(DataSource, item_id, db, "Data source")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/data-sources/{item_id}", status_code=204)
def disable_data_source(item_id: UUID, db: Session = Depends(get_db)):
    item = _get_or_404(DataSource, item_id, db, "Data source")
    item.enabled = False
    db.commit()


@router.get("/collectors", response_model=list[CollectorOut])
def list_collectors(
    data_source_id: UUID | None = None,
    enabled: bool | None = None,
    status: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    stmt = select(Collector).order_by(Collector.name).limit(limit)
    if data_source_id:
        stmt = stmt.where(Collector.data_source_id == data_source_id)
    if enabled is not None:
        stmt = stmt.where(Collector.enabled == enabled)
    if status:
        stmt = stmt.where(Collector.status == status)
    return db.scalars(stmt).all()


@router.get("/collectors/{item_id}", response_model=CollectorOut)
def get_collector(item_id: UUID, db: Session = Depends(get_db)):
    return _get_or_404(Collector, item_id, db, "Collector")


@router.get("/collectors/{item_id}/runs", response_model=list[CollectorRunOut])
def list_collector_runs(
    item_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    _get_or_404(Collector, item_id, db, "Collector")
    stmt = (
        select(CollectorRun)
        .where(CollectorRun.collector_id == item_id)
        .order_by(CollectorRun.started_at.desc())
        .limit(limit)
    )
    return db.scalars(stmt).all()


@router.post("/collectors", response_model=CollectorOut, status_code=201)
def create_collector(payload: CollectorCreate, db: Session = Depends(get_db)):
    _get_or_404(DataSource, payload.data_source_id, db, "Data source")
    item = Collector(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/collectors/{item_id}", response_model=CollectorOut)
def update_collector(item_id: UUID, payload: CollectorUpdate, db: Session = Depends(get_db)):
    item = _get_or_404(Collector, item_id, db, "Collector")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/collectors/{item_id}", status_code=204)
def disable_collector(item_id: UUID, db: Session = Depends(get_db)):
    item = _get_or_404(Collector, item_id, db, "Collector")
    item.enabled = False
    item.status = "STOPPED"
    db.commit()


@router.get("/metrics", response_model=list[MetricDefinitionOut])
def list_metrics(
    organization_id: UUID | None = None,
    resource_type: str | None = None,
    resource_id: UUID | None = None,
    enabled: bool | None = None,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    stmt = select(MetricDefinition).order_by(MetricDefinition.name).limit(limit)
    if organization_id:
        stmt = stmt.where(MetricDefinition.organization_id == organization_id)
    if resource_type:
        stmt = stmt.where(MetricDefinition.resource_type == resource_type)
    if resource_id:
        stmt = stmt.where(MetricDefinition.resource_id == resource_id)
    if enabled is not None:
        stmt = stmt.where(MetricDefinition.enabled == enabled)
    return db.scalars(stmt).all()


@router.get("/metrics/{item_id}", response_model=MetricDefinitionOut)
def get_metric(item_id: UUID, db: Session = Depends(get_db)):
    return _get_or_404(MetricDefinition, item_id, db, "Metric definition")


@router.post("/metrics", response_model=MetricDefinitionOut, status_code=201)
def create_metric(payload: MetricDefinitionCreate, db: Session = Depends(get_db)):
    item = MetricDefinition(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/metrics/{item_id}", response_model=MetricDefinitionOut)
def update_metric(item_id: UUID, payload: MetricDefinitionUpdate, db: Session = Depends(get_db)):
    item = _get_or_404(MetricDefinition, item_id, db, "Metric definition")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/metrics/{item_id}", status_code=204)
def disable_metric(item_id: UUID, db: Session = Depends(get_db)):
    item = _get_or_404(MetricDefinition, item_id, db, "Metric definition")
    item.enabled = False
    db.commit()


@router.get("/logs", response_model=list[LogSourceOut])
def list_log_sources(
    organization_id: UUID | None = None,
    resource_type: str | None = None,
    resource_id: UUID | None = None,
    enabled: bool | None = None,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    stmt = select(LogSource).order_by(LogSource.name).limit(limit)
    if organization_id:
        stmt = stmt.where(LogSource.organization_id == organization_id)
    if resource_type:
        stmt = stmt.where(LogSource.resource_type == resource_type)
    if resource_id:
        stmt = stmt.where(LogSource.resource_id == resource_id)
    if enabled is not None:
        stmt = stmt.where(LogSource.enabled == enabled)
    return db.scalars(stmt).all()


@router.get("/logs/{item_id}", response_model=LogSourceOut)
def get_log_source(item_id: UUID, db: Session = Depends(get_db)):
    return _get_or_404(LogSource, item_id, db, "Log source")


@router.post("/logs", response_model=LogSourceOut, status_code=201)
def create_log_source(payload: LogSourceCreate, db: Session = Depends(get_db)):
    item = LogSource(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/logs/{item_id}", response_model=LogSourceOut)
def update_log_source(item_id: UUID, payload: LogSourceUpdate, db: Session = Depends(get_db)):
    item = _get_or_404(LogSource, item_id, db, "Log source")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/logs/{item_id}", status_code=204)
def disable_log_source(item_id: UUID, db: Session = Depends(get_db)):
    item = _get_or_404(LogSource, item_id, db, "Log source")
    item.enabled = False
    db.commit()


@router.get("/organizations", response_model=list[OrganizationOut])
def list_organizations(
    active: bool | None = True,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    stmt = select(Organization).order_by(Organization.name).limit(limit)
    if active is not None:
        stmt = stmt.where(Organization.active == active)
    return db.scalars(stmt).all()


@router.get("/alert-rules", response_model=list[AlertRuleOut])
def list_alert_rules(organization_id: UUID | None = None, metric_definition_id: UUID | None = None, enabled: bool | None = None, limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db)):
    stmt = select(AlertRule).order_by(AlertRule.name).limit(limit)
    if organization_id: stmt = stmt.where(AlertRule.organization_id == organization_id)
    if metric_definition_id: stmt = stmt.where(AlertRule.metric_definition_id == metric_definition_id)
    if enabled is not None: stmt = stmt.where(AlertRule.enabled == enabled)
    return db.scalars(stmt).all()

@router.get("/alert-rules/{item_id}", response_model=AlertRuleOut)
def get_alert_rule(item_id: UUID, db: Session = Depends(get_db)):
    return _get_or_404(AlertRule, item_id, db, "Alert rule")

@router.post("/alert-rules", response_model=AlertRuleOut, status_code=201)
def create_alert_rule(payload: AlertRuleCreate, db: Session = Depends(get_db)):
    metric = _get_or_404(MetricDefinition, payload.metric_definition_id, db, "Metric definition")
    if metric.organization_id != payload.organization_id:
        raise HTTPException(status_code=409, detail="Metric definition belongs to a different organization")
    item = AlertRule(**payload.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    return item

@router.patch("/alert-rules/{item_id}", response_model=AlertRuleOut)
def update_alert_rule(item_id: UUID, payload: AlertRuleUpdate, db: Session = Depends(get_db)):
    item = _get_or_404(AlertRule, item_id, db, "Alert rule")
    values = payload.model_dump(exclude_unset=True)
    if "metric_definition_id" in values:
        metric = _get_or_404(MetricDefinition, values["metric_definition_id"], db, "Metric definition")
        if metric.organization_id != item.organization_id:
            raise HTTPException(status_code=409, detail="Metric definition belongs to a different organization")
    for key, value in values.items(): setattr(item, key, value)
    db.commit(); db.refresh(item)
    return item

@router.delete("/alert-rules/{item_id}", status_code=204)
def disable_alert_rule(item_id: UUID, db: Session = Depends(get_db)):
    item = _get_or_404(AlertRule, item_id, db, "Alert rule")
    item.enabled = False
    db.commit()
