from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_
from sqlalchemy.orm import Session, joinedload, selectinload
from app.db.session import get_db
from app.models import JobOrderHistory, JobOrder, VM, ExecutionStatus, ExecutionType, JobStepExecution, CorrelationRecord, Organization, DataSource, Collector, AlertIncidentEvent
from app.schemas.etl import ExecutionCreate, ExecutionListItem, ExecutionOut, StepOut, JobOrderCreate
from sqlalchemy.exc import IntegrityError
from app.schemas.monitoring import CorrelationRecordOut
from app.services.correlation import correlate_execution
router = APIRouter(prefix="/api/v1/etl", tags=["ETL"])
def _item(h, db=None):
    monitor='UNKNOWN'
    evidence=h.source_evidence or {}
    if db and evidence.get('collector_id'):
        try: collector=db.get(Collector,UUID(evidence['collector_id']))
        except ValueError: collector=None
        if collector:
            instant=datetime.now(timezone.utc)
            if not collector.enabled: monitor='DISABLED'
            elif collector.last_error: monitor='ERROR'
            elif collector.last_success_at and (instant-collector.last_success_at).total_seconds()<=max(120,collector.interval_seconds*2+30): monitor='CURRENT'
            else: monitor='STALE'
    duration=int(max(0,((h.ended_at or datetime.now(timezone.utc))-h.started_at).total_seconds())) if h.started_at and (h.ended_at or h.status in {ExecutionStatus.RUNNING,ExecutionStatus.LONG_RUNNING}) else None
    return ExecutionListItem(id=h.id,job_order_id=h.job_order_id,execution_type=h.execution_type,status=h.status,started_at=h.started_at,ended_at=h.ended_at,detected_at=h.detected_at,expected_runtime_seconds=h.expected_runtime_seconds,sla_seconds=h.sla_seconds,sla_status=h.sla_status,failed_step=h.failed_step,incident_number=h.incident_number,job_name=h.job_order.name,server=h.job_order.vm.hostname if h.job_order.vm else "SaaS",environment=h.job_order.environment,organization=h.job_order.organization.name,organization_id=h.job_order.organization_id,duration_seconds=duration,provider_execution_id=h.provider_execution_id,monitoring_status=monitor,monitoring_conditions=h.monitoring_conditions)
def _load(eid,db):
    stmt=select(JobOrderHistory).options(joinedload(JobOrderHistory.job_order).joinedload(JobOrder.vm),joinedload(JobOrderHistory.job_order).joinedload(JobOrder.organization),joinedload(JobOrderHistory.steps)).where(JobOrderHistory.id==eid)
    return db.scalars(stmt).unique().first()
def _out(h,db=None):
    return ExecutionOut(**_item(h,db).model_dump(),source_error_code=h.source_error_code,source_error_message=h.source_error_message,source_exception=h.source_exception,source_log_location=h.source_log_location,source_result=h.source_result,steps=[StepOut.model_validate(s) for s in h.steps],source_evidence=h.source_evidence)
@router.get("/executions",response_model=list[ExecutionListItem])
def list_executions(status:ExecutionStatus|None=None,environment:str|None=None,execution_type:ExecutionType|None=None,search:str|None=None,organization_ids:list[UUID]|None=Query(default=None),limit:int=Query(100,ge=1,le=500),latest_only:bool=False,db:Session=Depends(get_db)):
    stmt=select(JobOrderHistory).join(JobOrder).outerjoin(JobOrder.vm).options(joinedload(JobOrderHistory.job_order).joinedload(JobOrder.vm),joinedload(JobOrderHistory.job_order).joinedload(JobOrder.organization))
    if organization_ids: stmt=stmt.where(JobOrder.organization_id.in_(organization_ids))
    if status: stmt=stmt.where(JobOrderHistory.status==status)
    if environment: stmt=stmt.where(JobOrder.environment==environment)
    if execution_type: stmt=stmt.where(JobOrderHistory.execution_type==execution_type)
    if search:
        p=f"%{search}%"; stmt=stmt.where(or_(JobOrder.name.ilike(p),JobOrder.vm.has(VM.hostname.ilike(p))))
    if latest_only:
        from sqlalchemy import func
        ranked=select(JobOrderHistory.id.label('id'),func.row_number().over(partition_by=JobOrderHistory.job_order_id,order_by=(JobOrderHistory.detected_at.desc().nullslast(),JobOrderHistory.created_at.desc(),JobOrderHistory.id.desc())).label('rank')).subquery()
        stmt=stmt.join(ranked,ranked.c.id==JobOrderHistory.id).where(ranked.c.rank==1)
    stmt=stmt.order_by(JobOrderHistory.detected_at.desc().nullslast(),JobOrderHistory.created_at.desc()).limit(limit)
    return [_item(h,db) for h in db.scalars(stmt).unique().all()]
@router.get("/executions/{execution_id}",response_model=ExecutionOut)
def get_execution(execution_id:UUID,db:Session=Depends(get_db)):
    h=_load(execution_id,db)
    if not h: raise HTTPException(404,"Execution not found")
    return _out(h,db)

@router.post('/job-orders',status_code=201)
def create_job_order(payload:JobOrderCreate,db:Session=Depends(get_db)):
    org=db.get(Organization,payload.organization_id)
    if not org:raise HTTPException(404,'Organization not found')
    if not org.active:raise HTTPException(409,'Organization is inactive')
    if payload.host_data_source_id:
        host=db.get(DataSource,payload.host_data_source_id)
        if not host or host.organization_id!=org.id:raise HTTPException(409,'Host source unavailable in this organization')
    vm=db.scalar(select(VM).where(VM.organization_id==org.id,VM.hostname==payload.hostname))
    if not vm:
        vm=VM(organization_id=org.id,hostname=payload.hostname,environment=payload.environment)
        # Include the authorized host in the first projection, rather than
        # attempting a later change to its immutable ownership relationship.
        vm._unified_initial_source_id=payload.host_data_source_id
        db.add(vm);db.flush()
    values=payload.model_dump(exclude={'hostname','timezone','weekdays'})
    job=JobOrder(vm_id=vm.id,**values,schedule={'timezone':payload.timezone,'weekdays':payload.weekdays})
    db.add(job)
    try:db.commit()
    except IntegrityError:
        db.rollback();raise HTTPException(409,'Job Order already exists')
    return {'id':str(job.id),'name':job.name,'vm_id':str(job.vm_id),'organization_id':str(job.organization_id)}

@router.get('/executions/{execution_id}/evidence')
def execution_evidence(execution_id:UUID,db:Session=Depends(get_db)):
    h=_load(execution_id,db)
    if not h:raise HTTPException(404,'Execution not found')
    histories=db.scalars(select(JobOrderHistory).where(JobOrderHistory.job_order_id==h.job_order_id).order_by(JobOrderHistory.detected_at.desc().nullslast(),JobOrderHistory.created_at.desc()).limit(30)).all()
    events=db.scalars(select(AlertIncidentEvent).join(JobOrderHistory).where(JobOrderHistory.job_order_id==h.job_order_id).order_by(AlertIncidentEvent.timestamp.desc()).limit(100)).all()
    timeline=[]
    for value,event,source in [(h.started_at,'Job started','Carte'),(h.detected_at,'Execution detected','OpsControl'),(h.ended_at,'Job '+h.status.value.lower(),'Carte')]:
        if value:timeline.append({'time':value.isoformat(),'event':event,'source':source})
    for step in h.steps:
        observed=(h.source_evidence or {}).get('observed_at') or (h.detected_at.isoformat() if h.detected_at else None)
        if observed:timeline.append({'time':observed,'event':step.name+' · '+step.status,'source':'Carte entry result (observed)'})
    for event in events:
        if event.history_id==h.id:timeline.append({'time':event.timestamp.isoformat(),'event':event.event_type,'source':event.source})
    return {'timeline':sorted(timeline,key=lambda item:item['time']),
        'logs':(h.source_evidence or {}).get('logs'),
        'history':[_item(item,db).model_dump(mode='json') for item in histories],
        'alert_events':[{'id':str(e.id),'event_type':e.event_type,'reference':e.reference,'severity':e.severity,'timestamp':e.timestamp.isoformat()} for e in events]}
@router.post("/job-orders/{job_order_id}/executions",response_model=ExecutionOut,status_code=201)
def create_execution(job_order_id:UUID,payload:ExecutionCreate,db:Session=Depends(get_db)):
    jo=db.get(JobOrder,job_order_id)
    if not jo: raise HTTPException(404,"Job Order not found")
    h=JobOrderHistory(job_order_id=job_order_id,**payload.model_dump(exclude={"steps"})); db.add(h); db.flush()
    for step in payload.steps: db.add(JobStepExecution(history_id=h.id,**step.model_dump()))
    db.commit(); return _out(_load(h.id,db))

@router.get("/executions/{history_id}/correlation", response_model=CorrelationRecordOut)
def get_execution_correlation(history_id: UUID, db: Session = Depends(get_db)):
    record = db.scalar(
        select(CorrelationRecord)
        .options(selectinload(CorrelationRecord.evidence))
        .where(CorrelationRecord.history_id == history_id)
    )
    if not record:
        raise HTTPException(404, "Correlation record not found")
    return record


@router.post("/executions/{history_id}/correlation", response_model=CorrelationRecordOut)
def analyze_execution_correlation(
    history_id: UUID,
    window_before_seconds: int = Query(900, ge=0, le=86400),
    window_after_seconds: int = Query(900, ge=0, le=86400),
    db: Session = Depends(get_db),
):
    try:
        record = correlate_execution(
            db,
            history_id,
            window_before_seconds=window_before_seconds,
            window_after_seconds=window_after_seconds,
        )
    except ValueError as exc:
        raise HTTPException(409, str(exc))
    if not record:
        raise HTTPException(404, "Execution not found")
    db.commit()
    db.refresh(record)
    return record
