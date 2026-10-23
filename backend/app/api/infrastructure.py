"""Evidence-backed infrastructure inventory with request-scoped ORM isolation."""
from datetime import datetime,timezone
from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException,Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import DataSource,Collector,MetricDefinition,MetricSample,AlertRule,AlertState,InfrastructureEvidence
from app.worker.infrastructure import INFRA_TYPES
from app.unified.models import MonitoringResource
from app.unified.schemas import Environment

router=APIRouter(prefix='/api/v1/infrastructure',tags=['Infrastructure Health'])
MONITORED_SOURCE_TYPES = INFRA_TYPES | {'LINUX', 'WINDOWS'}

def utc(value): return value.replace(tzinfo=timezone.utc) if value and value.tzinfo is None else value


def snapshot(source,db):
    collectors=db.scalars(select(Collector).where(Collector.data_source_id==source.id).order_by(Collector.name)).all()
    ids=[c.id for c in collectors]
    now=datetime.now(timezone.utc)
    rows=[]
    all_samples=[]
    for collector in collectors:
        evidence=db.scalar(select(InfrastructureEvidence).where(InfrastructureEvidence.collector_id==collector.id).order_by(InfrastructureEvidence.observed_at.desc()).limit(1))
        freshness='NO_EVIDENCE' if evidence is None else 'STALE' if (now-utc(evidence.observed_at)).total_seconds()>max(collector.interval_seconds*2+30,120) else 'CURRENT'
        metrics=db.scalars(select(MetricDefinition).where(MetricDefinition.collector_id==collector.id,MetricDefinition.enabled.is_(True))).all()
        samples=[]
        for metric in metrics:
            sample=db.scalar(select(MetricSample).where(MetricSample.metric_definition_id==metric.id).order_by(MetricSample.observed_at.desc()).limit(1))
            if sample:
                samples.append({'name':metric.name,'value':sample.value_numeric,'unit':sample.unit,'observed_at':sample.observed_at.isoformat()})
        all_samples.extend(samples)
        rows.append({'id':str(collector.id),'name':collector.name,'type':collector.collector_type,
            'enabled':collector.enabled,'status':collector.status,'freshness':freshness,
            'last_error':collector.last_error,'last_run_at':collector.last_run_at.isoformat() if collector.last_run_at else None,
            'evidence':{'id':str(evidence.id),'observed_at':evidence.observed_at.isoformat(),**evidence.payload} if evidence else None,
            'metrics':samples})
    metrics=db.scalars(select(MetricDefinition.id).where(MetricDefinition.collector_id.in_(ids))).all() if ids else []
    alerts=db.scalars(select(AlertState).join(AlertRule).where(AlertRule.metric_definition_id.in_(metrics)).order_by(AlertState.last_evaluated_at.desc())).all() if metrics else []
    open_alerts=[a for a in alerts if a.status=='OPEN']
    enabled=[c for c in rows if c['enabled']]
    if not source.enabled or not enabled: health='DISABLED'
    elif any(c['freshness']!='CURRENT' for c in enabled): health='UNKNOWN'
    elif open_alerts: health='CRITICAL' if any(a.severity=='CRITICAL' for a in open_alerts) else 'WARNING'
    elif any(c['status']=='ERROR' for c in enabled): health='WARNING'
    elif any(c['status']!='HEALTHY' for c in enabled): health='UNKNOWN'
    elif any((c['evidence'] or {}).get('outcome') not in ('SUCCESS',) for c in enabled): health='WARNING'
    else: health='HEALTHY'
    return {'id':str(source.id),'organization_id':str(source.organization_id),'name':source.name,
        'provider':source.source_type,'health':health,'collectors':rows,'metrics':all_samples,
        'open_alert_count':len(open_alerts),'alerts':[{'id':str(a.id),'status':a.status,'severity':a.severity,
            'message':a.message,'first_triggered_at':a.first_triggered_at.isoformat(),
            'resolved_at':a.resolved_at.isoformat() if a.resolved_at else None} for a in alerts]}

@router.get('/resources')
def resources(organization_id:list[UUID]=Query(default=[]),environments:list[Environment]=Query(default=[]),limit:int=Query(200,ge=1,le=500),offset:int=Query(0,ge=0,le=1000000),db:Session=Depends(get_db)):
    stmt=select(DataSource).where(DataSource.source_type.in_(MONITORED_SOURCE_TYPES))
    if organization_id: stmt=stmt.where(DataSource.organization_id.in_(organization_id))
    if environments:
        scoped_sources = select(MonitoringResource.data_source_id).where(
            MonitoringResource.domain == "VM",
            MonitoringResource.environment.in_(set(environments)),
        )
        stmt = stmt.where(DataSource.id.in_(scoped_sources))
    total=db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows=[snapshot(source,db) for source in db.scalars(stmt.order_by(DataSource.name,DataSource.id).offset(offset).limit(limit)).all()]
    return {'resources':rows,'summary':{state:sum(r['health']==state for r in rows)
        for state in ('HEALTHY','WARNING','CRITICAL','UNKNOWN','DISABLED')},'total':total,
        'offset':offset,'limit':limit,'has_more':offset+len(rows)<total,'truncated':total>len(rows),'summary_scope':'page'}

@router.get('/resources/{source_id}')
def resource(source_id:UUID,db:Session=Depends(get_db)):
    source=db.get(DataSource,source_id)
    if source is None or source.source_type not in MONITORED_SOURCE_TYPES: raise HTTPException(404,'Infrastructure source unavailable')
    return snapshot(source,db)

@router.get('/resources/{source_id}/history')
def history(source_id:UUID,limit:int=Query(100,ge=1,le=500),db:Session=Depends(get_db)):
    resource(source_id,db)
    rows=db.scalars(select(InfrastructureEvidence).where(InfrastructureEvidence.data_source_id==source_id).order_by(InfrastructureEvidence.observed_at.desc()).limit(limit)).all()
    return [{'id':str(row.id),'collector_run_id':str(row.collector_run_id),'provider':row.provider,
             'observed_at':row.observed_at.isoformat(),'payload':row.payload} for row in rows]
