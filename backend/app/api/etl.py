from uuid import UUID
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_
from sqlalchemy.orm import Session, joinedload, selectinload
from app.db.session import get_db
from app.models import JobOrderHistory, JobOrder, VM, ExecutionStatus, ExecutionType, JobStepExecution, CorrelationRecord, Organization, DataSource, Collector, AlertIncidentEvent
from app.schemas.etl import ExecutionCreate, ExecutionListItem, ExecutionOut, StepOut, JobOrderCreate, WorkflowCreate, WorkflowUpdate, WorkflowJobCreate, WorkflowJobUpdate, WorkflowDependencyCreate
from sqlalchemy.exc import IntegrityError
from app.schemas.monitoring import CorrelationRecordOut
from app.services.correlation import correlate_execution
from app.unified.schemas import Environment
from app.models.entities import ETLWorkflow, ETLWorkflowDependency
from app.security.access_control import require_permission
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
def list_executions(
    status: ExecutionStatus | None = None,
    environment: str | None = None,
    environments: list[Environment] = Query(default=[]),
    execution_type: ExecutionType | None = None,
    search: str | None = None,
    organization_ids: list[UUID] | None = Query(default=None),
    limit: int = Query(100, ge=1, le=500),
    latest_only: bool = False,
    db: Session = Depends(get_db),
):
    stmt=select(JobOrderHistory).join(JobOrder).outerjoin(JobOrder.vm).options(joinedload(JobOrderHistory.job_order).joinedload(JobOrder.vm),joinedload(JobOrderHistory.job_order).joinedload(JobOrder.organization))
    if organization_ids: stmt=stmt.where(JobOrder.organization_id.in_(organization_ids))
    if status: stmt=stmt.where(JobOrderHistory.status==status)
    if environment and environments:
        raise HTTPException(422, "Use environment or environments, not both")
    if environment:
        stmt = stmt.where(JobOrder.environment == environment)
    elif environments:
        stmt = stmt.where(JobOrder.environment.in_(environments))
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


def _workflow_out(workflow):
    return {
        "id": str(workflow.id), "organization_id": str(workflow.organization_id),
        "name": workflow.name, "environment": workflow.environment,
        "schedule": workflow.schedule,
        "expected_window_start": workflow.expected_window_start,
        "expected_window_end": workflow.expected_window_end,
        "expected_duration_seconds": workflow.expected_duration_seconds,
        "sla_seconds": workflow.sla_seconds, "active": workflow.active,
    }


@router.post("/workflows", status_code=201)
def create_workflow(payload: WorkflowCreate, db: Session = Depends(get_db)):
    require_permission("etl.configure", payload.organization_id)
    org = db.get(Organization, payload.organization_id)
    if not org:
        raise HTTPException(404, "Organization not found")
    if not org.active:
        raise HTTPException(409, "Organization is inactive")
    workflow = ETLWorkflow(
        organization_id=payload.organization_id, name=payload.name,
        environment=payload.environment,
        schedule={"timezone": payload.timezone, "weekdays": payload.weekdays},
        expected_window_start=payload.expected_window_start,
        expected_window_end=payload.expected_window_end,
        expected_duration_seconds=payload.expected_duration_seconds,
        sla_seconds=payload.sla_seconds,
    )
    db.add(workflow)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Workflow already exists")
    return _workflow_out(workflow)


@router.get("/workflows")
def list_workflows(organization_id: UUID, db: Session = Depends(get_db)):
    require_permission("etl.view", organization_id)
    workflows = db.scalars(select(ETLWorkflow).where(
        ETLWorkflow.organization_id == organization_id
    ).order_by(ETLWorkflow.name)).all()
    return [_workflow_out(workflow) for workflow in workflows]



@router.get("/workflows/{workflow_id}")
def get_workflow(workflow_id: UUID, db: Session = Depends(get_db)):
    workflow = db.get(ETLWorkflow, workflow_id)
    if not workflow:
        raise HTTPException(404, "Workflow not found")
    require_permission("etl.view", workflow.organization_id)
    return _workflow_out(workflow)


@router.patch("/workflows/{workflow_id}")
def update_workflow(workflow_id: UUID, payload: WorkflowUpdate, db: Session = Depends(get_db)):
    workflow = db.get(ETLWorkflow, workflow_id)
    if not workflow:
        raise HTTPException(404, "Workflow not found")
    require_permission("etl.configure", workflow.organization_id)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return _workflow_out(workflow)
    if any(value is None for key, value in changes.items() if key not in (
        "expected_window_start", "expected_window_end",
        "expected_duration_seconds", "sla_seconds",
    )):
        raise HTTPException(422, "Required workflow fields cannot be null")
    if "environment" in changes and changes["environment"] != workflow.environment:
        assigned = db.scalar(select(JobOrder.id).where(JobOrder.workflow_id == workflow_id).limit(1))
        if assigned:
            raise HTTPException(409, "Cannot change environment while workflow has jobs")
    schedule = dict(workflow.schedule or {})
    for field in ("timezone", "weekdays"):
        if field in changes:
            schedule[field] = changes.pop(field)
    start = changes.get("expected_window_start", workflow.expected_window_start)
    end = changes.get("expected_window_end", workflow.expected_window_end)
    if bool(start) != bool(end):
        raise HTTPException(422, "Both window endpoints required")
    for field, value in changes.items():
        setattr(workflow, field, value)
    workflow.schedule = schedule
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Workflow configuration conflicts with an existing workflow")
    return _workflow_out(workflow)


@router.post("/workflows/{workflow_id}/jobs", status_code=201)
def create_workflow_job(workflow_id: UUID, payload: WorkflowJobCreate, db: Session = Depends(get_db)):
    workflow = db.get(ETLWorkflow, workflow_id)
    if not workflow:
        raise HTTPException(404, "Workflow not found")
    require_permission("etl.configure", workflow.organization_id)
    if not workflow.active:
        raise HTTPException(409, "Workflow is inactive")
    if payload.host_data_source_id:
        host = db.get(DataSource, payload.host_data_source_id)
        if not host or host.organization_id != workflow.organization_id:
            raise HTTPException(409, "Host source unavailable in this organization")
    vm = db.scalar(select(VM).where(
        VM.organization_id == workflow.organization_id, VM.hostname == payload.hostname
    ))
    if not vm:
        vm = VM(organization_id=workflow.organization_id, hostname=payload.hostname,
                environment=workflow.environment)
        vm._unified_initial_source_id = payload.host_data_source_id
        db.add(vm)
        db.flush()
    elif vm.environment != workflow.environment:
        raise HTTPException(409, "Host environment differs from workflow")
    job = JobOrder(
        workflow_id=workflow.id, organization_id=workflow.organization_id,
        vm_id=vm.id, host_data_source_id=payload.host_data_source_id,
        name=payload.name, environment=workflow.environment,
        expected_runtime_seconds=payload.expected_duration_seconds,
        monitoring_enabled=True,
    )
    db.add(job)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Job already exists")
    return {"id": str(job.id), "workflow_id": str(workflow.id), "name": job.name,
            "expected_duration_seconds": job.expected_runtime_seconds}


@router.get("/workflows/{workflow_id}/jobs")
def list_workflow_jobs(workflow_id: UUID, db: Session = Depends(get_db)):
    workflow = db.get(ETLWorkflow, workflow_id)
    if not workflow:
        raise HTTPException(404, "Workflow not found")
    require_permission("etl.view", workflow.organization_id)
    jobs = db.scalars(select(JobOrder).where(JobOrder.workflow_id == workflow_id).order_by(JobOrder.name)).all()
    return [{"id": str(job.id), "name": job.name,
             "expected_duration_seconds": job.expected_runtime_seconds,
             "active": job.active, "monitoring_enabled": job.monitoring_enabled} for job in jobs]



@router.patch("/workflows/{workflow_id}/jobs/{job_id}")
def update_workflow_job(workflow_id: UUID, job_id: UUID, payload: WorkflowJobUpdate,
                        db: Session = Depends(get_db)):
    workflow = db.get(ETLWorkflow, workflow_id)
    if not workflow:
        raise HTTPException(404, "Workflow not found")
    require_permission("etl.configure", workflow.organization_id)
    job = db.scalar(select(JobOrder).where(
        JobOrder.id == job_id,
        JobOrder.workflow_id == workflow_id,
        JobOrder.organization_id == workflow.organization_id,
    ))
    if not job:
        raise HTTPException(404, "Workflow job not found")
    from app.etl_bindings.writer import mark
    mark(db)
    changes = payload.model_dump(exclude_unset=True)
    if any(value is None for value in changes.values()):
        raise HTTPException(422, "Job configuration fields cannot be null")
    if changes.get("monitoring_enabled") is True and not workflow.active:
        raise HTTPException(409, "Cannot enable monitoring on an inactive workflow")
    if changes.get("active") is True and not workflow.active:
        raise HTTPException(409, "Cannot activate a job in an inactive workflow")
    if "expected_duration_seconds" in changes:
        job.expected_runtime_seconds = changes.pop("expected_duration_seconds")
    for field, value in changes.items():
        setattr(job, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Workflow job configuration conflicts with an existing job")
    return {
        "id": str(job.id), "workflow_id": str(workflow.id), "name": job.name,
        "expected_duration_seconds": job.expected_runtime_seconds,
        "active": job.active, "monitoring_enabled": job.monitoring_enabled,
    }


@router.get("/workflows/{workflow_id}/monitoring")
def get_workflow_monitoring(workflow_id: UUID, db: Session = Depends(get_db)):
    """Read-only projection of persisted native observations; never schedules jobs."""
    from app.etl_bindings.service import readiness as binding_readiness
    workflow = db.get(ETLWorkflow, workflow_id)
    if not workflow:
        raise HTTPException(404, "Workflow not found")
    require_permission("etl.view", workflow.organization_id)
    jobs = db.scalars(select(JobOrder).where(
        JobOrder.workflow_id == workflow_id,
        JobOrder.organization_id == workflow.organization_id,
    ).order_by(JobOrder.name)).all()
    results = []
    for job in jobs:
        history = db.scalar(select(JobOrderHistory).where(
            JobOrderHistory.job_order_id == job.id
        ).order_by(
            JobOrderHistory.detected_at.desc().nullslast(),
            JobOrderHistory.created_at.desc(),
            JobOrderHistory.id.desc(),
        ).limit(1))
        results.append({
            "id": str(job.id), "name": job.name, "active": job.active,
            "monitoring_enabled": job.monitoring_enabled,
            "expected_duration_seconds": job.expected_runtime_seconds,
            "hostname": job.vm.hostname if job.vm else None,
            "telemetry_status": "MISSING" if history is None else _item(history, db).monitoring_status,
            "latest_execution": None if history is None else {
                "id": str(history.id),
                "status": history.status.value,
                "execution_type": history.execution_type.value,
                "provider_execution_id": history.provider_execution_id,
                "started_at": history.started_at.isoformat() if history.started_at else None,
                "ended_at": history.ended_at.isoformat() if history.ended_at else None,
                "detected_at": history.detected_at.isoformat() if history.detected_at else None,
                "sla_status": history.sla_status,
                "monitoring_conditions": history.monitoring_conditions,
            },
        })
    return {
        "workflow": _workflow_out(workflow),
        "jobs": results,
        "observed_job_count": sum(job["latest_execution"] is not None for job in results),
        "total_job_count": len(results),
        "source": "persisted_observations",
        "readiness_dimensions": binding_readiness(db, workflow, jobs),
        "readiness": {
            "configuration_status": "INCOMPLETE" if not jobs or any(
                job.expected_runtime_seconds is None
                or not 1 <= job.expected_runtime_seconds <= 604800 for job in jobs
            ) else "VALID",
            "configuration_scope": "SUPPORTED_CHILD_RUNTIME_FIELDS_ONLY",
            "activation_status": "BLOCKED",
            "provider_status": "UNVERIFIED",
            "reasons": ["Workflow activation and native source certification are not established by configuration persistence", "Frequency/recurrence and separate Job long-running threshold contracts remain unavailable"],
        },
        "scheduler_control": False,
    }


@router.post("/workflows/{workflow_id}/dependencies", status_code=201)
def create_workflow_dependency(workflow_id: UUID, payload: WorkflowDependencyCreate, db: Session = Depends(get_db)):
    workflow = db.get(ETLWorkflow, workflow_id)
    if not workflow:
        raise HTTPException(404, "Workflow not found")
    require_permission("etl.configure", workflow.organization_id)
    # Serialize configuration graph edits only for this already-authorized
    # workflow. READ COMMITTED gives the graph query below a fresh snapshot
    # after a waiting transaction acquires the row lock.
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError
    try:
        db.execute(text("SET LOCAL lock_timeout = '5s'"))
        locked = db.scalar(select(ETLWorkflow).where(ETLWorkflow.id == workflow_id).with_for_update())
    except DBAPIError as exc:
        db.rollback()
        if getattr(exc.orig, "sqlstate", None) == "55P03":
            raise HTTPException(409, "Workflow configuration is busy; retry the configuration update") from exc
        raise
    if locked is None:
        raise HTTPException(404, "Workflow not found")
    if payload.predecessor_job_id == payload.successor_job_id:
        raise HTTPException(422, "A job cannot depend on itself")
    jobs = db.scalars(select(JobOrder).where(
        JobOrder.id.in_([payload.predecessor_job_id, payload.successor_job_id]),
        JobOrder.workflow_id == workflow_id,
    )).all()
    if len(jobs) != 2:
        raise HTTPException(409, "Both jobs must belong to this workflow")
    # Internal complete graph for the authorized, locked workflow; projection
    # filters must not hide paths during cycle detection. Never returned to UI.
    graph = ETLWorkflowDependency.__table__
    edges = db.execute(select(graph.c.predecessor_job_id, graph.c.successor_job_id).where(
        graph.c.workflow_id == workflow_id
    )).all()
    adjacency = {}
    for edge in edges:
        adjacency.setdefault(edge.predecessor_job_id, set()).add(edge.successor_job_id)
    # Adding predecessor -> successor is illegal when successor already reaches predecessor.
    pending = [payload.successor_job_id]
    visited = set()
    while pending:
        current = pending.pop()
        if current == payload.predecessor_job_id:
            raise HTTPException(409, "Workflow dependency cycle")
        if current in visited:
            continue
        visited.add(current)
        pending.extend(adjacency.get(current, ()))
    edge = ETLWorkflowDependency(
        id=uuid.uuid4(), workflow_id=workflow_id,
        predecessor_job_id=payload.predecessor_job_id,
        successor_job_id=payload.successor_job_id,
    )
    db.add(edge)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Dependency already exists")
    return {"id": str(edge.id), "workflow_id": str(workflow_id),
            "predecessor_job_id": str(edge.predecessor_job_id),
            "successor_job_id": str(edge.successor_job_id)}


@router.get("/workflows/{workflow_id}/dependencies")
def list_workflow_dependencies(workflow_id: UUID, db: Session = Depends(get_db)):
    workflow = db.get(ETLWorkflow, workflow_id)
    if not workflow:
        raise HTTPException(404, "Workflow not found")
    require_permission("etl.view", workflow.organization_id)
    edges = db.scalars(select(ETLWorkflowDependency).where(
        ETLWorkflowDependency.workflow_id == workflow_id
    )).all()
    return [{"id": str(edge.id), "predecessor_job_id": str(edge.predecessor_job_id),
             "successor_job_id": str(edge.successor_job_id)} for edge in edges]
