"""Tenant-scoped NOC evidence and bounded, observation-based reporting."""
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, case
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import (DataSource, Collector, CollectorRun, MetricDefinition, AlertState,
    JobOrder, JobOrderHistory, Organization)
from app.security.http import actor
from app.unified.models import MonitoringResource
from app.unified.schemas import Environment

router = APIRouter(prefix="/api/v1/operations", tags=["Operational Dashboards"])
HTTP_TYPES = ("API", "HTTP", "HTTPS")
def iso(value): return value.isoformat() if value else None
def scoped(stmt, model, organization_id):
    return stmt.where(model.organization_id.in_(organization_id)) if organization_id else stmt

def run_item(run):
    # Response bodies and transport credentials never belong in dashboard feeds.
    return {"id": str(run.id), "collector_id": str(run.collector_id), "observed_at": iso(run.started_at),
        "ended_at": iso(run.ended_at), "status": run.status, "outcome": run.outcome,
        "http_status": run.http_status, "response_time_ms": run.response_time_ms}

def prefetch_services(sources, db):
    """Constant query count per page instead of queries per source/collector."""
    if not sources:
        return {}
    ids = [source.id for source in sources]
    result = {sid: {"collectors": [], "runs": {}, "alerts": [], "open_count": 0} for sid in ids}
    collectors = db.scalars(select(Collector).where(Collector.data_source_id.in_(ids)).order_by(Collector.name, Collector.id)).all()
    collector_sources = {row.id: row.data_source_id for row in collectors}
    for row in collectors:
        result[row.data_source_id]["collectors"].append(row)
    runs = db.scalars(select(CollectorRun).where(CollectorRun.collector_id.in_(collector_sources))
        .distinct(CollectorRun.collector_id).order_by(CollectorRun.collector_id, CollectorRun.started_at.desc(), CollectorRun.id.desc())).all()
    for row in runs:
        result[collector_sources[row.collector_id]]["runs"][row.collector_id] = row
    rank = select(AlertState.id.label("alert_id"), func.row_number().over(
        partition_by=MetricDefinition.data_source_id,
        order_by=(AlertState.last_evaluated_at.desc(), AlertState.id.desc())).label("position"))
    rank = rank.join(MetricDefinition, MetricDefinition.id == AlertState.metric_definition_id).where(MetricDefinition.data_source_id.in_(ids)).subquery()
    alerts = db.execute(select(AlertState, MetricDefinition.data_source_id).select_from(AlertState)
        .join(MetricDefinition, MetricDefinition.id == AlertState.metric_definition_id)
        .join(rank, rank.c.alert_id == AlertState.id).where(rank.c.position <= 100)
        .order_by(AlertState.last_evaluated_at.desc(), AlertState.id.desc())).all()
    for alert, sid in alerts:
        result[sid]["alerts"].append(alert)
    counts = db.execute(select(MetricDefinition.data_source_id, func.count(AlertState.id)).select_from(AlertState)
        .join(MetricDefinition, MetricDefinition.id == AlertState.metric_definition_id)
        .where(MetricDefinition.data_source_id.in_(ids), AlertState.status == "OPEN")
        .group_by(MetricDefinition.data_source_id)).all()
    for sid, count in counts:
        result[sid]["open_count"] = count
    return result

def service_snapshot(source, db, preloaded=None):
    collectors = preloaded["collectors"] if preloaded is not None else db.scalars(select(Collector).where(Collector.data_source_id == source.id).order_by(Collector.name)).all()
    values = []; now = datetime.now(timezone.utc)
    for collector in collectors:
        run = preloaded["runs"].get(collector.id) if preloaded is not None else db.scalar(select(CollectorRun).where(CollectorRun.collector_id == collector.id)
            .order_by(CollectorRun.started_at.desc(), CollectorRun.id.desc()).limit(1))
        observed = run.started_at if run else None
        if observed and not observed.tzinfo: observed = observed.replace(tzinfo=timezone.utc)
        freshness = "NO_EVIDENCE" if not observed else "STALE" if (now-observed).total_seconds() > max(120, collector.interval_seconds*2+30) else "CURRENT"
        values.append({"id": str(collector.id), "name": collector.name, "enabled": collector.enabled,
            "status": collector.status, "freshness": freshness, "latest_run": run_item(run) if run else None})
    metric_ids = select(MetricDefinition.id).where(MetricDefinition.data_source_id == source.id)
    alerts = preloaded["alerts"] if preloaded is not None else db.scalars(select(AlertState).where(AlertState.metric_definition_id.in_(metric_ids))
        .order_by(AlertState.last_evaluated_at.desc()).limit(100)).all()
    open_count = preloaded["open_count"] if preloaded is not None else db.scalar(select(func.count()).select_from(AlertState).where(
        AlertState.metric_definition_id.in_(metric_ids), AlertState.status == "OPEN")) or 0
    enabled = [row for row in values if row["enabled"]]
    if not source.enabled or not enabled: health = "DISABLED"
    elif any(row["freshness"] != "CURRENT" for row in enabled): health = "UNKNOWN"
    elif open_count or any(row["latest_run"]["status"] == "FAILED" for row in enabled): health = "CRITICAL"
    elif any(row["status"] == "ERROR" for row in enabled): health = "CRITICAL"
    elif any(row["status"] not in {"HEALTHY", "SUCCESS"} for row in enabled): health = "UNKNOWN"
    elif any(row["latest_run"]["status"] != "SUCCESS" for row in enabled): health = "UNKNOWN"
    else: health = "HEALTHY"
    return {"id": str(source.id), "organization_id": str(source.organization_id), "name": source.name,
        "health": health, "collectors": values, "open_alert_count": open_count,
        "alerts": [{"id": str(row.id), "severity": row.severity, "status": row.status,
            "message": row.message, "opened_at": iso(row.first_triggered_at), "resolved_at": iso(row.resolved_at)} for row in alerts]}

@router.get("/services")
def services(organization_id: list[UUID] = Query(default=[]), limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0, le=1000000), environments: list[Environment] = Query(default=[]), db: Session = Depends(get_db)):
    stmt = scoped(select(DataSource).where(DataSource.source_type.in_(HTTP_TYPES)), DataSource, organization_id)
    if environments:
        scoped_sources = select(MonitoringResource.data_source_id).where(
            MonitoringResource.domain == "API",
            MonitoringResource.environment.in_(set(environments)),
        )
        stmt = stmt.where(DataSource.id.in_(scoped_sources))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    sources = db.scalars(stmt.order_by(DataSource.name, DataSource.id).offset(offset).limit(limit)).all()
    preloaded = prefetch_services(sources, db)
    rows = [service_snapshot(source, db, preloaded[source.id]) for source in sources]
    return {"services": rows, "total": total, "offset": offset, "limit": limit,
        "has_more": offset + len(rows) < total, "truncated": total > len(rows), "summary_scope": "page",
        "summary": {state: sum(row["health"] == state for row in rows) for state in ("HEALTHY", "CRITICAL", "UNKNOWN", "DISABLED")}}

@router.get("/services/{source_id}")
def service_detail(source_id: UUID, limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db)):
    source = db.get(DataSource, source_id)
    if not source or source.source_type not in HTTP_TYPES: raise HTTPException(404, "Service unavailable")
    result = service_snapshot(source, db)
    runs = db.scalars(select(CollectorRun).join(Collector).where(Collector.data_source_id == source.id)
        .order_by(CollectorRun.started_at.desc(), CollectorRun.id.desc()).limit(limit)).all()
    result["history"] = [run_item(run) for run in runs]
    return result

@router.get("/collectors/{collector_id}")
def collector_detail(collector_id: UUID, limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db)):
    collector = db.get(Collector, collector_id)
    source = db.get(DataSource, collector.data_source_id) if collector else None
    if not collector or not source: raise HTTPException(404, "Collector unavailable")
    runs = db.scalars(select(CollectorRun).where(CollectorRun.collector_id == collector.id)
        .order_by(CollectorRun.started_at.desc(), CollectorRun.id.desc()).limit(limit)).all()
    return {"id": str(collector.id), "name": collector.name, "source_name": source.name,
        "source_type": source.source_type, "organization_id": str(source.organization_id),
        "status": collector.status, "enabled": collector.enabled, "history": [run_item(run) for run in runs]}

@router.get("/reports")
def reports(organization_id: list[UUID] = Query(default=[]), days: int = Query(7, ge=1, le=90), db: Session = Depends(get_db)):
    end = datetime.now(timezone.utc); start = end-timedelta(days=days)
    # Aggregate every stored observation in the window, independently of UI limits.
    http = scoped(select(DataSource.id, DataSource.name, func.count(CollectorRun.id),
        func.sum(case((CollectorRun.status == "SUCCESS", 1), else_=0)),
        func.sum(case((CollectorRun.status == "FAILED", 1), else_=0)),
        func.avg(CollectorRun.response_time_ms), func.min(CollectorRun.started_at), func.max(CollectorRun.started_at))
        .join(Collector, Collector.data_source_id == DataSource.id)
        .join(CollectorRun, CollectorRun.collector_id == Collector.id)
        .where(DataSource.source_type.in_(HTTP_TYPES), CollectorRun.started_at >= start, CollectorRun.started_at <= end)
        .group_by(DataSource.id, DataSource.name), DataSource, organization_id)
    service_rows = []
    for sid, name, count, passed, failed, latency, first, last in db.execute(http).all():
        evaluated = (passed or 0) + (failed or 0)
        service_rows.append({"id": str(sid), "name": name, "observations": count, "success": passed or 0,
            "failed": failed or 0, "unknown": count-evaluated, "sample_success_percent": round(100*passed/evaluated, 2) if evaluated else None,
            "mean_response_time_ms": round(latency, 2) if latency is not None else None, "first_observed_at": iso(first), "last_observed_at": iso(last)})
    terminal = JobOrderHistory.status.in_(["SUCCESS", "FAILED"])
    timed = terminal & JobOrderHistory.started_at.is_not(None) & JobOrderHistory.ended_at.is_not(None) & (JobOrderHistory.ended_at >= JobOrderHistory.started_at) & (JobOrderHistory.sla_seconds > 0)
    # Runtime SLA excludes in-progress executions, unknown timing and No Run.
    etl = scoped(select(JobOrder.id, JobOrder.name, func.count(JobOrderHistory.id),
        func.sum(case((JobOrderHistory.status == "SUCCESS", 1), else_=0)),
        func.sum(case((JobOrderHistory.status == "FAILED", 1), else_=0)),
        func.sum(case((JobOrderHistory.status == "NO_RUN", 1), else_=0)),
        func.sum(case((timed & (JobOrderHistory.sla_status == "MET"), 1), else_=0)),
        func.sum(case((timed & (JobOrderHistory.sla_status == "BREACHED"), 1), else_=0)))
        .join(JobOrderHistory, JobOrderHistory.job_order_id == JobOrder.id)
        .where(JobOrderHistory.detected_at >= start, JobOrderHistory.detected_at <= end)
        .group_by(JobOrder.id, JobOrder.name), JobOrder, organization_id)
    job_rows = []
    for jid, name, count, success, failed, missing, met, breached in db.execute(etl).all():
        evaluated = (met or 0) + (breached or 0)
        job_rows.append({"id": str(jid), "name": name, "executions": count, "success": success or 0, "failed": failed or 0,
            "no_run": missing or 0, "sla_met": met or 0, "sla_breached": breached or 0, "sla_excluded": count-evaluated,
            "runtime_sla_percent": round(100*met/evaluated, 2) if evaluated else None})
    return {"generated_at": iso(end), "window_start": iso(start), "window_end": iso(end), "days": days,
        "methodology": {"http": "Successful probes / completed success or failed probes. Sample based, not time-weighted uptime. Unknown statuses excluded.",
            "etl": "Terminal executions meeting runtime SLA / terminal executions with a known SLA result. Running, No Run and unknown timing excluded. Job success is separate."},
        "services": service_rows, "etl": job_rows}

@router.get("/history")
def operational_history(organization_id: list[UUID] = Query(default=[]), days: int = Query(7, ge=1, le=90),
    limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db)):
    start = datetime.now(timezone.utc)-timedelta(days=days)
    runs = db.execute(scoped(select(CollectorRun, DataSource).join(Collector, Collector.id == CollectorRun.collector_id)
        .join(DataSource, DataSource.id == Collector.data_source_id).where(CollectorRun.started_at >= start)
        .order_by(CollectorRun.started_at.desc()).limit(limit), DataSource, organization_id)).all()
    jobs = db.execute(scoped(select(JobOrderHistory, JobOrder).join(JobOrder, JobOrder.id == JobOrderHistory.job_order_id)
        .where(JobOrderHistory.detected_at >= start).order_by(JobOrderHistory.detected_at.desc()).limit(limit), JobOrder, organization_id)).all()
    rows = [{"id": str(run.id), "kind": "COLLECTOR", "name": source.name, "status": run.status, "at": iso(run.started_at),
        "data_source_id": str(source.id), "source_type": source.source_type, "collector_id": str(run.collector_id)} for run, source in runs]
    rows += [{"id": str(h.id), "kind": "ETL", "name": job.name, "status": h.status.value, "at": iso(h.detected_at), "history_id": str(h.id)} for h, job in jobs]
    return {"events": sorted(rows, key=lambda item: item["at"], reverse=True)[:limit], "limit": limit}

@router.get("/jobs/{job_id}/history")
def job_history(job_id: UUID, days: int = Query(7, ge=1, le=90), limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db)):
    from app.api.etl import _item
    if not db.get(JobOrder, job_id): raise HTTPException(404, "Job unavailable")
    rows = db.scalars(select(JobOrderHistory).where(JobOrderHistory.job_order_id == job_id,
        JobOrderHistory.detected_at >= datetime.now(timezone.utc)-timedelta(days=days))
        .order_by(JobOrderHistory.detected_at.desc()).limit(limit)).all()
    return [_item(row, db).model_dump(mode="json") for row in rows]

@router.get("/overview")
def overview_counts(organization_id:list[UUID]=Query(default=[]),db:Session=Depends(get_db)):
    # Count-only overview authority does not grant resource/detail APIs.
    customers=select(func.count()).select_from(Organization)
    if organization_id:customers=customers.where(Organization.id.in_(organization_id))
    resources=scoped(select(func.count()).select_from(DataSource),DataSource,organization_id)
    jobs=scoped(select(func.count()).select_from(JobOrder),JobOrder,organization_id)
    alerts=scoped(select(func.count()).select_from(AlertState).where(AlertState.status=="OPEN"),AlertState,organization_id)
    return {"customers":db.scalar(customers),"resources":db.scalar(resources),"etl_jobs":db.scalar(jobs),"active_alerts":db.scalar(alerts)}
