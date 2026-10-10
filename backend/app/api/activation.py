"""Explicit preview/apply/disable lifecycle for monitoring configurations."""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.session import get_db
from app.models import DataSource
from app.security.scope import current_principal
from app.services.activation_engine import preview,apply,disable
from app.services.rule_models import MonitoringActivation

router=APIRouter(prefix="/api/v1/data-sources",tags=["Monitoring Activation"])

class ActivationRequest(BaseModel):
    model_config=ConfigDict(extra="forbid")
    remote_worker_id:uuid.UUID
    rule_version_ids:list[uuid.UUID]=Field(default_factory=list,max_length=100)
    include_templates:bool=True

def can_manage(db,source_id):
    source=db.get(DataSource,source_id)
    if not source:raise HTTPException(404,"Data source not found")
    principal=current_principal.get()
    if not principal or not principal.can_edit(source.organization_id):
        raise HTTPException(403,"Organization administrator required")
    return source

@router.post("/{source_id}/activation-preview")
def activation_preview(source_id:uuid.UUID,payload:ActivationRequest,db:Session=Depends(get_db)):
    can_manage(db,source_id)
    return preview(db,source_id,payload.rule_version_ids,payload.remote_worker_id,payload.include_templates)

@router.post("/{source_id}/activations")
def activation_apply(source_id:uuid.UUID,payload:ActivationRequest,db:Session=Depends(get_db)):
    can_manage(db,source_id)
    return apply(db,source_id,payload.rule_version_ids,payload.remote_worker_id,payload.include_templates)

@router.get("/{source_id}/activation")
def activation_state(source_id:uuid.UUID,db:Session=Depends(get_db)):
    can_manage(db,source_id)
    record=db.scalar(select(MonitoringActivation).where(MonitoringActivation.data_source_id==source_id))
    if not record:return {"status":"NOT_CONFIGURED","version":0,"collector_id":None}
    return {"status":record.status,"version":record.version,
            "collector_id":str(record.collector_id) if record.collector_id else None,
            "applied_at":record.applied_at.isoformat(),"generated":record.details.get("generated",[])}

@router.post("/{source_id}/deactivation")
def activation_disable(source_id:uuid.UUID,db:Session=Depends(get_db)):
    can_manage(db,source_id)
    return disable(db,source_id)
