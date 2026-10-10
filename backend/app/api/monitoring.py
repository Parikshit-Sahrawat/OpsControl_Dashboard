from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import AlertNotificationDelivery, AlertRule, AlertState, Collector, CollectorRun, CorrelationRecord, DataSource, LogEvent, LogSource, MetricDefinition, MetricSample, Organization, MonitoringTemplate, MonitoringTemplateVersion, MonitoringTemplateAttachment
from app.schemas.monitoring import (
    AlertRuleCreate,
    AlertRuleOut,
    AlertRuleUpdate,
    AlertNotificationDeliveryOut,
    AlertStateOut,
    MonitoringTemplateCreate,
    MonitoringTemplateOut,
    MonitoringTemplateUpdate,
    MonitoringTemplateVersionOut,
    MonitoringTemplateAttachmentCreate,
    MonitoringTemplateAttachmentUpdate,
    MonitoringTemplateAttachmentOut,
    CollectorCreate,
    CollectorOut,
    CollectorUpdate,
    CollectorRunOut,
    DataSourceCreate,
    DataSourceOut,
    DataSourceUpdate,
    LogSourceCreate,
    LogSourceOut,
    LogEventCreate,
    LogEventOut,
    LogSourceUpdate,
    MetricDefinitionCreate,
    MetricDefinitionOut,
    MetricDefinitionUpdate,
    MetricSampleOut,
    OrganizationOut,
    CorrelationRecordOut,
)

from app.services.template_resolution import attach_template, detach_template, list_template_attachments, resolve_data_source_configuration
from app.security.secret_refs import redact_config

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


@router.get("/data-sources/{item_id}/templates", response_model=list[MonitoringTemplateAttachmentOut])
def list_data_source_templates(item_id: UUID, db: Session = Depends(get_db)):
    _get_or_404(DataSource, item_id, db, "Data source")
    return list_template_attachments(db, item_id)


@router.post("/data-sources/{item_id}/templates", response_model=MonitoringTemplateAttachmentOut, status_code=201)
def attach_data_source_template(
    item_id: UUID,
    payload: MonitoringTemplateAttachmentCreate,
    db: Session = Depends(get_db),
):
    return attach_template(
        db,
        item_id,
        payload.template_id,
        payload.template_version,
        payload.priority,
        payload.overrides,
    )


@router.patch("/data-sources/{item_id}/templates/{template_id}", response_model=MonitoringTemplateAttachmentOut)
def update_data_source_template(
    item_id: UUID,
    template_id: UUID,
    payload: MonitoringTemplateAttachmentUpdate,
    db: Session = Depends(get_db),
):
    _get_or_404(DataSource, item_id, db, "Data source")
    attachment = db.scalar(
        select(MonitoringTemplateAttachment).where(
            MonitoringTemplateAttachment.data_source_id == item_id,
            MonitoringTemplateAttachment.template_id == template_id,
        )
    )
    if not attachment:
        raise HTTPException(status_code=404, detail="Template attachment not found")

    values = payload.model_dump(exclude_unset=True)
    if "template_version" in values:
        template = _get_or_404(MonitoringTemplate, template_id, db, "Monitoring template")
        version = db.scalar(
            select(MonitoringTemplateVersion).where(
                MonitoringTemplateVersion.template_id == template_id,
                MonitoringTemplateVersion.version == values["template_version"],
                MonitoringTemplateVersion.status == "COMMITTED",
            )
        )
        if not version:
            raise HTTPException(status_code=409, detail=f"Template version {values['template_version']} is not available")
    for key, value in values.items():
        setattr(attachment, key, value)
    db.commit()
    db.refresh(attachment)
    return attachment


@router.delete("/data-sources/{item_id}/templates/{template_id}", status_code=204)
def detach_data_source_template(item_id: UUID, template_id: UUID, db: Session = Depends(get_db)):
    _get_or_404(DataSource, item_id, db, "Data source")
    detach_template(db, item_id, template_id)


@router.get("/data-sources/{item_id}/effective-configuration")
def get_effective_data_source_configuration(item_id: UUID, db: Session = Depends(get_db)):
    return redact_config(resolve_data_source_configuration(db, item_id))


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


@router.get("/metrics/{item_id}/samples", response_model=list[MetricSampleOut])
def list_metric_samples(
    item_id: UUID,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = Query(500, ge=1, le=5000),
    db: Session = Depends(get_db),
):
    _get_or_404(MetricDefinition, item_id, db, "Metric definition")
    stmt = (
        select(MetricSample)
        .where(MetricSample.metric_definition_id == item_id)
        .order_by(MetricSample.observed_at.desc())
        .limit(limit)
    )
    if start:
        stmt = stmt.where(MetricSample.observed_at >= start)
    if end:
        stmt = stmt.where(MetricSample.observed_at <= end)
    return db.scalars(stmt).all()


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


@router.post("/logs/{item_id}/events", response_model=LogEventOut, status_code=201)
def create_log_event(
    item_id: UUID,
    payload: LogEventCreate,
    db: Session = Depends(get_db),
):
    source = _get_or_404(LogSource, item_id, db, "Log source")
    if payload.log_source_id != item_id:
        raise HTTPException(status_code=409, detail="Log source does not match path")
    if payload.organization_id != source.organization_id:
        raise HTTPException(status_code=409, detail="Log event belongs to a different organization")
    event = LogEvent(**payload.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.get("/logs/{item_id}/events", response_model=list[LogEventOut])
def list_log_events(
    item_id: UUID,
    start: datetime | None = None,
    end: datetime | None = None,
    severity: str | None = None,
    search: str | None = None,
    limit: int = Query(200, ge=1, le=5000),
    db: Session = Depends(get_db),
):
    _get_or_404(LogSource, item_id, db, "Log source")
    stmt = (
        select(LogEvent)
        .where(LogEvent.log_source_id == item_id)
        .order_by(LogEvent.observed_at.desc())
        .limit(limit)
    )
    if start:
        stmt = stmt.where(LogEvent.observed_at >= start)
    if end:
        stmt = stmt.where(LogEvent.observed_at <= end)
    if severity:
        stmt = stmt.where(LogEvent.severity == severity.upper())
    if search:
        stmt = stmt.where(LogEvent.message.ilike(f"%{search}%"))
    return db.scalars(stmt).all()


@router.get("/alerts", response_model=list[AlertStateOut])
def list_alert_states(
    organization_id: UUID | None = None,
    status: str | None = None,
    severity: str | None = None,
    alert_rule_id: UUID | None = None,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    stmt = select(AlertState).order_by(AlertState.last_evaluated_at.desc()).limit(limit)
    if organization_id:
        stmt = stmt.where(AlertState.organization_id == organization_id)
    if status:
        stmt = stmt.where(AlertState.status == status.upper())
    if severity:
        stmt = stmt.where(AlertState.severity == severity.upper())
    if alert_rule_id:
        stmt = stmt.where(AlertState.alert_rule_id == alert_rule_id)
    return db.scalars(stmt).all()


@router.get("/alerts/{item_id}", response_model=AlertStateOut)
def get_alert_state(item_id: UUID, db: Session = Depends(get_db)):
    return _get_or_404(AlertState, item_id, db, "Alert state")


@router.get("/alerts/{item_id}/notifications", response_model=list[AlertNotificationDeliveryOut])
def list_alert_notifications(
    item_id: UUID,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    _get_or_404(AlertState, item_id, db, "Alert state")
    stmt = (
        select(AlertNotificationDelivery)
        .where(AlertNotificationDelivery.alert_state_id == item_id)
        .order_by(AlertNotificationDelivery.created_at.desc())
        .limit(limit)
    )
    return db.scalars(stmt).all()


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


@router.get("/templates", response_model=list[MonitoringTemplateOut])
def list_monitoring_templates(
    status: str | None = None,
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
):
    stmt = select(MonitoringTemplate).order_by(MonitoringTemplate.name).limit(limit)
    if status:
        stmt = stmt.where(MonitoringTemplate.status == status.upper())
    return db.scalars(stmt).all()


@router.get("/templates/{item_id}", response_model=MonitoringTemplateOut)
def get_monitoring_template(item_id: UUID, db: Session = Depends(get_db)):
    return _get_or_404(MonitoringTemplate, item_id, db, "Monitoring template")


@router.get("/templates/{item_id}/versions", response_model=list[MonitoringTemplateVersionOut])
def list_monitoring_template_versions(
    item_id: UUID,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    _get_or_404(MonitoringTemplate, item_id, db, "Monitoring template")
    stmt = (
        select(MonitoringTemplateVersion)
        .where(MonitoringTemplateVersion.template_id == item_id)
        .order_by(MonitoringTemplateVersion.version.desc())
        .limit(limit)
    )
    return db.scalars(stmt).all()


@router.post("/templates", response_model=MonitoringTemplateOut, status_code=201)
def create_monitoring_template(payload: MonitoringTemplateCreate, db: Session = Depends(get_db)):
    item = MonitoringTemplate(
        name=payload.name,
        description=payload.description,
        scope=payload.scope,
        version=1,
        status="COMMITTED",
        package_config=payload.package_config,
        committed_at=datetime.utcnow(),
        committed_by=payload.committed_by or "Admin",
    )
    db.add(item)
    db.flush()
    db.add(MonitoringTemplateVersion(
        template_id=item.id,
        version=1,
        status="COMMITTED",
        package_config=payload.package_config,
        committed_at=item.committed_at,
        committed_by=item.committed_by,
    ))
    db.commit()
    db.refresh(item)
    return item


@router.patch("/templates/{item_id}", response_model=MonitoringTemplateOut)
def commit_monitoring_template(
    item_id: UUID,
    payload: MonitoringTemplateUpdate,
    db: Session = Depends(get_db),
):
    item = _get_or_404(MonitoringTemplate, item_id, db, "Monitoring template")
    values = payload.model_dump(exclude_unset=True)
    package = values.pop("package_config", None)
    committed_by = values.pop("committed_by", None) or "Admin"
    for key, value in values.items():
        setattr(item, key, value)

    if package is not None:
        next_version = int(item.version) + 1
        item.version = next_version
        item.status = "COMMITTED"
        item.package_config = package
        item.committed_at = datetime.utcnow()
        item.committed_by = committed_by
        db.add(MonitoringTemplateVersion(
            template_id=item.id,
            version=next_version,
            status="COMMITTED",
            package_config=package,
            committed_at=item.committed_at,
            committed_by=committed_by,
        ))
    db.commit()
    db.refresh(item)
    return item


@router.delete("/templates/{item_id}", status_code=204)
def disable_monitoring_template(item_id: UUID, db: Session = Depends(get_db)):
    item = _get_or_404(MonitoringTemplate, item_id, db, "Monitoring template")
    item.status = "DISABLED"
    db.commit()


@router.get("/correlations/{history_id}", response_model=CorrelationRecordOut)
def get_correlation(history_id: UUID, db: Session = Depends(get_db)):
    item = db.scalar(select(CorrelationRecord).where(CorrelationRecord.history_id == history_id))
    if not item:
        raise HTTPException(status_code=404, detail="Correlation record not found")
    return item
