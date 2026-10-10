"""Versioned independent metric, log and alert rule catalogs.

Rule versions are immutable. A new revision is created with POST; existing
version records may only be read. Organization authorization happens before
lookups, not through a user-supplied selector.
"""
import uuid
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.security.scope import current_principal
from app.security.secret_refs import require_safe_config
from app.models import Organization
from app.services.rule_models import MonitoringRuleCatalog, MonitoringRuleVersion

router=APIRouter(prefix="/api/v1/rule-catalogs",tags=["Independent Monitoring Rules"])

class RuleCreate(BaseModel):
    model_config=ConfigDict(extra="forbid")
    organization_id:uuid.UUID
    kind:Literal["METRIC","LOG","ALERT"]
    name:str=Field(min_length=1,max_length=160)
    definition:dict

    @field_validator("definition")
    @classmethod
    def safe_definition(cls,value):
        require_safe_config(value)
        if len(str(value))>16000: raise ValueError("Rule config exceeds 16 KiB")
        return value

class NewVersion(BaseModel):
    model_config=ConfigDict(extra="forbid")
    definition:dict
    @field_validator("definition")
    @classmethod
    def safe_definition(cls,value):
        require_safe_config(value)
        if len(str(value))>16000: raise ValueError("Rule config exceeds 16 KiB")
        return value

def require_org_write(org_id):
    principal=current_principal.get()
    if not principal or not principal.can_edit(org_id):
        raise HTTPException(403,"Organization administrator required")

def to_out(catalog,versions):
    return {"id":str(catalog.id),"organization_id":str(catalog.organization_id),
            "name":catalog.name,"kind":catalog.kind,
            "versions":[{"id":str(v.id),"version":v.version,"definition":v.definition} for v in versions]}

def validate_definition(kind,definition):
    if not isinstance(definition,dict): raise HTTPException(422,"Rule definition must be JSON")
    if kind=="METRIC":
        if definition.get("name") not in {"probe_up","http_response_time_ms","http_up","http_availability","response_time_ms"}:
            raise HTTPException(422,"Only supported HTTP metric names can be activated in this slice")
        if definition.get("metric_type","GAUGE")!="GAUGE":
            raise HTTPException(422,"HTTP metrics require GAUGE type")
    elif kind=="LOG":
        if definition.get("source_type") not in {"HTTP","API"}:
            raise HTTPException(422,"Only HTTP/API structured event sources are supported")
        if definition.get("parser_type","RAW")!="RAW":
            raise HTTPException(422,"Only safe RAW structured event parsing is supported")
    elif kind=="ALERT":
        if definition.get("metric_name") not in {"probe_up","http_response_time_ms","http_up","http_availability","response_time_ms"}:
            raise HTTPException(422,"Alert metric_name must reference a supported active metric")
        if definition.get("operator") not in {"GT","GTE","LT","LTE","EQ","NE"}:
            raise HTTPException(422,"Unsupported alert operator")
        try: float(definition["threshold_value"])
        except (TypeError,KeyError,ValueError):
            raise HTTPException(422,"Numeric threshold required")
        if type(definition.get("consecutive_breaches",1)) is not int or not 1<=definition.get("consecutive_breaches",1)<=100:
            raise HTTPException(422,"consecutive_breaches must be 1..100")

@router.post("",status_code=201)
def create_catalog(payload:RuleCreate,db:Session=Depends(get_db)):
    require_org_write(payload.organization_id)
    if not db.get(Organization,payload.organization_id):
        raise HTTPException(404,"Organization not found")
    validate_definition(payload.kind,payload.definition)
    record=MonitoringRuleCatalog(organization_id=payload.organization_id,kind=payload.kind,name=payload.name)
    db.add(record)
    try:
        db.flush()
        version=MonitoringRuleVersion(catalog_id=record.id,version=1,definition=payload.definition)
        db.add(version)
        db.commit()
        db.refresh(version)
    except IntegrityError:
        db.rollback()
        raise HTTPException(409,"Rule already exists")
    return to_out(record,[version])

@router.get("")
def list_catalogs(organization_id:uuid.UUID|None=None,kind:Literal["METRIC","LOG","ALERT"]|None=None,
                  limit:int=Query(100,ge=1,le=500),db:Session=Depends(get_db)):
    stmt=select(MonitoringRuleCatalog).order_by(MonitoringRuleCatalog.name).limit(limit)
    if organization_id: stmt=stmt.where(MonitoringRuleCatalog.organization_id==organization_id)
    if kind: stmt=stmt.where(MonitoringRuleCatalog.kind==kind)
    records=db.scalars(stmt).all()
    return [to_out(item,db.scalars(select(MonitoringRuleVersion).where(
        MonitoringRuleVersion.catalog_id==item.id).order_by(MonitoringRuleVersion.version)).all()) for item in records]

@router.get("/{catalog_id}")
def get_catalog(catalog_id:uuid.UUID,db:Session=Depends(get_db)):
    item=db.get(MonitoringRuleCatalog,catalog_id)
    if item is None: raise HTTPException(404,"Rule catalog not found")
    return to_out(item,db.scalars(select(MonitoringRuleVersion).where(
        MonitoringRuleVersion.catalog_id==catalog_id).order_by(MonitoringRuleVersion.version)).all())

@router.post("/{catalog_id}/versions",status_code=201)
def add_version(catalog_id:uuid.UUID,payload:NewVersion,db:Session=Depends(get_db)):
    item=db.scalar(select(MonitoringRuleCatalog).where(MonitoringRuleCatalog.id==catalog_id).with_for_update())
    if item is None: raise HTTPException(404,"Rule catalog not found")
    require_org_write(item.organization_id)
    validate_definition(item.kind,payload.definition)
    current=db.scalar(select(func.max(MonitoringRuleVersion.version)).where(MonitoringRuleVersion.catalog_id==catalog_id)) or 0
    version=MonitoringRuleVersion(catalog_id=catalog_id,version=current+1,definition=payload.definition)
    db.add(version)
    db.commit()
    db.refresh(version)
    return {"id":str(version.id),"catalog_id":str(catalog_id),"version":version.version,"definition":version.definition}
