from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_
from sqlalchemy.orm import Session, joinedload
from app.db.session import get_db
from app.models import JobOrderHistory, JobOrder, VM, ExecutionStatus, ExecutionType, JobStepExecution
from app.schemas.etl import ExecutionCreate, ExecutionListItem, ExecutionOut, StepOut
router = APIRouter(prefix="/api/v1/etl", tags=["ETL"])
def _item(h):
    return ExecutionListItem(id=h.id,job_order_id=h.job_order_id,execution_type=h.execution_type,status=h.status,started_at=h.started_at,ended_at=h.ended_at,detected_at=h.detected_at,expected_runtime_seconds=h.expected_runtime_seconds,sla_seconds=h.sla_seconds,sla_status=h.sla_status,failed_step=h.failed_step,incident_number=h.incident_number,job_name=h.job_order.name,server=h.job_order.vm.hostname,environment=h.job_order.environment,organization=h.job_order.organization.name)
def _load(eid,db):
    stmt=select(JobOrderHistory).options(joinedload(JobOrderHistory.job_order).joinedload(JobOrder.vm),joinedload(JobOrderHistory.job_order).joinedload(JobOrder.organization),joinedload(JobOrderHistory.steps)).where(JobOrderHistory.id==eid)
    return db.scalars(stmt).unique().first()
def _out(h):
    return ExecutionOut(**_item(h).model_dump(),source_error_code=h.source_error_code,source_error_message=h.source_error_message,source_exception=h.source_exception,source_log_location=h.source_log_location,source_result=h.source_result,steps=[StepOut.model_validate(s) for s in h.steps])
@router.get("/executions",response_model=list[ExecutionListItem])
def list_executions(status:ExecutionStatus|None=None,environment:str|None=None,execution_type:ExecutionType|None=None,search:str|None=None,limit:int=Query(100,ge=1,le=500),db:Session=Depends(get_db)):
    stmt=select(JobOrderHistory).join(JobOrder).join(JobOrder.vm).options(joinedload(JobOrderHistory.job_order).joinedload(JobOrder.vm),joinedload(JobOrderHistory.job_order).joinedload(JobOrder.organization))
    if status: stmt=stmt.where(JobOrderHistory.status==status)
    if environment: stmt=stmt.where(JobOrder.environment==environment)
    if execution_type: stmt=stmt.where(JobOrderHistory.execution_type==execution_type)
    if search:
        p=f"%{search}%"; stmt=stmt.where(or_(JobOrder.name.ilike(p),JobOrder.vm.has(VM.hostname.ilike(p))))
    stmt=stmt.order_by(JobOrderHistory.started_at.desc().nullslast()).limit(limit)
    return [_item(h) for h in db.scalars(stmt).unique().all()]
@router.get("/executions/{execution_id}",response_model=ExecutionOut)
def get_execution(execution_id:UUID,db:Session=Depends(get_db)):
    h=_load(execution_id,db)
    if not h: raise HTTPException(404,"Execution not found")
    return _out(h)
@router.post("/job-orders/{job_order_id}/executions",response_model=ExecutionOut,status_code=201)
def create_execution(job_order_id:UUID,payload:ExecutionCreate,db:Session=Depends(get_db)):
    jo=db.get(JobOrder,job_order_id)
    if not jo: raise HTTPException(404,"Job Order not found")
    h=JobOrderHistory(job_order_id=job_order_id,**payload.model_dump(exclude={"steps"})); db.add(h); db.flush()
    for step in payload.steps: db.add(JobStepExecution(history_id=h.id,**step.model_dump()))
    db.commit(); return _out(_load(h.id,db))
