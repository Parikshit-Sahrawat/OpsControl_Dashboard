from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from app.db.session import get_db
from app.models import Investigation, InvestigationTransition, OperatorNote, InvestigationStatus, JobOrderHistory
from app.schemas.investigation import InvestigationOut, TransitionCreate, NoteCreate, TransitionOut, NoteOut
router=APIRouter(prefix="/api/v1",tags=["Investigations"])
ALLOWED={InvestigationStatus.NEW:InvestigationStatus.ACKNOWLEDGED,InvestigationStatus.ACKNOWLEDGED:InvestigationStatus.INVESTIGATING,InvestigationStatus.INVESTIGATING:InvestigationStatus.ROOT_CAUSE_IDENTIFIED,InvestigationStatus.ROOT_CAUSE_IDENTIFIED:InvestigationStatus.RECOVERY_IN_PROGRESS,InvestigationStatus.RECOVERY_IN_PROGRESS:InvestigationStatus.MONITORING,InvestigationStatus.MONITORING:InvestigationStatus.RESOLVED}
def _get(inv_id,db):
    stmt=select(Investigation).options(joinedload(Investigation.transitions),joinedload(Investigation.notes)).where(Investigation.id==inv_id)
    return db.scalars(stmt).unique().first()
def _ensure(history_id,db):
    inv=db.scalar(select(Investigation).where(Investigation.history_id==history_id))
    if inv:return inv
    if not db.get(JobOrderHistory,history_id):raise HTTPException(404,"Execution not found")
    inv=Investigation(history_id=history_id,status=InvestigationStatus.NEW);db.add(inv);db.commit();db.refresh(inv);return inv
@router.get("/etl/executions/{history_id}/investigation",response_model=InvestigationOut)
def get_investigation(history_id:UUID,db:Session=Depends(get_db)):
    return _get(_ensure(history_id,db).id,db)
@router.post("/etl/executions/{history_id}/investigation/transitions",response_model=TransitionOut,status_code=201)
def transition(history_id:UUID,payload:TransitionCreate,db:Session=Depends(get_db)):
    inv=_ensure(history_id,db); current=inv.status
    if payload.new_status!=ALLOWED.get(current):raise HTTPException(409,f"Invalid investigation transition: {current} -> {payload.new_status}")
    t=InvestigationTransition(investigation_id=inv.id,previous_status=current,new_status=payload.new_status,operator=payload.operator,comment=payload.comment);inv.status=payload.new_status;inv.operator=payload.operator
    now=datetime.now(timezone.utc)
    if inv.started_at is None:inv.started_at=now
    if payload.new_status==InvestigationStatus.RESOLVED:inv.resolved_at=now
    db.add(t);db.commit();db.refresh(t);return t
@router.post("/etl/executions/{history_id}/investigation/notes",response_model=NoteOut,status_code=201)
def add_note(history_id:UUID,payload:NoteCreate,db:Session=Depends(get_db)):
    inv=_ensure(history_id,db);note=OperatorNote(investigation_id=inv.id,**payload.model_dump());db.add(note);db.commit();db.refresh(note);return note
