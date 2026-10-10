"""Organization-scoped operational diagnostics; no credentials or response bodies."""
import uuid
from datetime import datetime,timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import Collector,DataSource,MetricDefinition,MetricSample,AlertRule,AlertState
from app.security.scope import current_principal
from app.services.rule_models import MonitoringActivation
from app.worker.remote_models import RemoteProbeJob,RemoteProbeEvidence

router=APIRouter(prefix="/api/v1/data-sources",tags=["Monitoring Diagnostics"])

@router.get("/{source_id}/diagnostics")
def diagnostics(source_id:uuid.UUID,db:Session=Depends(get_db)):
    principal=current_principal.get()
    source=db.get(DataSource,source_id)
    if source is None: raise HTTPException(404,"Data source unavailable")
    if not principal or not (principal.platform_admin or source.organization_id in principal.roles):
        raise HTTPException(404,"Data source unavailable")
    activation=db.scalar(select(MonitoringActivation).where(
        MonitoringActivation.data_source_id==source.id))
    collector=db.get(Collector,activation.collector_id) if activation and activation.collector_id else None
    if collector and collector.data_source_id!=source.id:
        raise HTTPException(409,"Collector/source consistency failure")
    jobs=db.scalars(select(RemoteProbeJob).where(
        RemoteProbeJob.organization_id==source.organization_id,
        RemoteProbeJob.collector_id==collector.id).order_by(
        RemoteProbeJob.created_at.desc()).limit(10)).all() if collector else []
    evidence=db.scalar(select(RemoteProbeEvidence).where(
        RemoteProbeEvidence.organization_id==source.organization_id,
        RemoteProbeEvidence.job_id.in_([job.id for job in jobs])).order_by(
        RemoteProbeEvidence.received_at.desc()).limit(1)) if jobs else None
    metrics=db.scalars(select(MetricDefinition.id).where(
        MetricDefinition.organization_id==source.organization_id,
        MetricDefinition.collector_id==collector.id)).all() if collector else []
    ids=list(metrics)
    samples=db.scalar(select(func.count()).select_from(MetricSample).where(
        MetricSample.organization_id==source.organization_id,
        MetricSample.metric_definition_id.in_(ids))) if ids else 0
    open_alerts=db.scalar(select(func.count()).select_from(AlertState).join(
        AlertRule,AlertRule.id==AlertState.alert_rule_id).where(
        AlertState.organization_id==source.organization_id,
        AlertRule.metric_definition_id.in_(ids),
        AlertState.status=="OPEN")) if ids else 0
    now=datetime.now(timezone.utc)
    last=collector.last_run_at if collector else None
    if last and last.tzinfo is None: last=last.replace(tzinfo=timezone.utc)
    stale=bool(collector and (not last or (now-last).total_seconds()>max(2*collector.interval_seconds+30,120)))
    if not activation or activation.status!="ACTIVE":
        health="NOT_CONFIGURED" if not activation else "DISABLED"
    elif not collector or not collector.enabled:
        health="COLLECTOR_DISABLED"
    elif stale:
        health="UNKNOWN"
    elif collector.status in ("ERROR","FAILED"):
        health="MONITORING_ERROR"
    else:
        health="OBSERVING"
    return {
        "source_id":str(source.id),"organization_id":str(source.organization_id),
        "activation":{"status":activation.status if activation else "NOT_CONFIGURED",
                      "version":activation.version if activation else 0,
                      "applied_at":activation.applied_at.isoformat() if activation else None},
        "collector":{"id":str(collector.id),"status":collector.status,"enabled":collector.enabled,
                     "interval_seconds":collector.interval_seconds,
                     "remote_worker_id":str(collector.remote_worker_id) if collector.remote_worker_id else None,
                     "last_run_at":last.isoformat() if last else None,
                     "last_success_at":collector.last_success_at.isoformat() if collector.last_success_at else None,
                     "last_error":collector.last_error,
                     "next_run_at":collector.next_run_at.isoformat() if collector.next_run_at else None} if collector else None,
        "health":health,"freshness":"STALE" if stale else "CURRENT" if last else "NO_EVIDENCE",
        "metric_sample_count":samples or 0,"open_alert_count":open_alerts or 0,
        "latest_evidence":{"observed_at":evidence.observed_at.isoformat(),
                           "outcome":evidence.result.get("outcome"),
                           "http_status":evidence.result.get("http_status"),
                           "response_time_ms":evidence.result.get("response_time_ms")} if evidence else None,
        "jobs":[{"id":str(j.id),"state":j.state,"attempts":j.attempts,
                 "planned_for":j.planned_for.isoformat(),
                 "lease_expires_at":j.lease_expires_at.isoformat() if j.lease_expires_at else None}
                for j in jobs]
    }
