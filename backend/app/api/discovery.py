"""Manual approval workflow for AWS/Kubernetes read-only discovery.

No auto-provisioned collector is enabled by import. Source ownership and
external identities are checked before creating typed resource inventory.
"""
import uuid
from datetime import datetime,timezone
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,ConfigDict,Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import DataSource,Collector
from app.security.scope import current_principal
from app.worker.provider_discovery import aws_ec2_candidates,k8s_pod_candidates
from app.worker.provider_checks import ProviderCheckError

router=APIRouter(prefix="/api/v1/resource-discovery",tags=["Resource Discovery"])

class ImportRequest(BaseModel):
    model_config=ConfigDict(extra="forbid")
    approved_external_ids:list[str]=Field(min_length=1,max_length=50)
    dry_run:bool=True

def source_access(db,source_id):
    source=db.get(DataSource,source_id)
    if source is None:raise HTTPException(404,"Data source not found")
    principal=current_principal.get()
    if not principal or not principal.can_edit(source.organization_id):
        raise HTTPException(403,"Organization administrator required")
    if source.source_type not in {"AWS_EC2","EC2","KUBERNETES","K8S"}:
        raise HTTPException(422,"Source is not a supported resource-discovery connection")
    if not source.enabled:raise HTTPException(409,"Discovery source disabled")
    return source

def scan(source):
    try:
        if source.source_type in {"AWS_EC2","EC2"}:
            rows=aws_ec2_candidates(source.connection_config or {})
        else:
            rows=k8s_pod_candidates(source.connection_config or {})
    except ProviderCheckError as exc:raise HTTPException(422,str(exc))
    except Exception:
        raise HTTPException(503,"Read-only provider discovery failed or is unauthorized")
    # Never mark discovery candidates healthy by inference.
    return [{"organization_id":str(source.organization_id),
             "discovery_source_id":str(source.id),
             "monitoring_status":"NOT_CONFIGURED",
             **record} for record in rows]

@router.get("/capabilities")
def capabilities():
    return [
        {"provider":"AWS_EC2","discovery":True,"monitoring":True,
         "authentication":"AWS workload IAM role; expected account ID"},
        {"provider":"KUBERNETES","discovery":True,"monitoring":True,
         "authentication":"In-cluster service account; namespace-scoped RBAC"},
        {"provider":"HTTP","discovery":False,"monitoring":True,
         "authentication":"Private-network worker plus approved egress policy"},
        {"provider":"PENTAHO","discovery":False,"monitoring":True,
         "authentication":"Read-only Carte status with managed credential reference"},
    ]

@router.post("/sources/{source_id}/scan")
def scan_source(source_id:uuid.UUID,db:Session=Depends(get_db)):
    source=source_access(db,source_id)
    return {"source_id":str(source.id),"discovered_at":datetime.now(timezone.utc).isoformat(),
            "candidates":scan(source),"imported":False}

@router.post("/sources/{source_id}/import")
def import_candidates(source_id:uuid.UUID,payload:ImportRequest,db:Session=Depends(get_db)):
    source=db.scalar(select(DataSource).where(DataSource.id==source_id).with_for_update())
    if source is None:raise HTTPException(404,"Data source not found")
    source=source_access(db,source_id)
    candidates={x["external_id"]:x for x in scan(source)}
    selected=[]
    for identity in payload.approved_external_ids:
        if identity not in candidates:
            raise HTTPException(422,"Import identifier was not discovered in the authorized provider scope")
        if identity in [x["external_id"] for x in selected]:
            raise HTTPException(422,"Duplicate resource import ID")
        selected.append(candidates[identity])
    results=[]
    for candidate in selected:
        external_id=candidate["external_id"]
        display_name=external_id[:200]
        existing=db.scalar(select(DataSource).where(
            DataSource.organization_id==source.organization_id,
            DataSource.name==display_name))
        new=existing is None
        if new and not payload.dry_run:
            if candidate["resource_type"]=="EC2_INSTANCE":
                config={"region":candidate["region"],"account_id":candidate["account_id"],
                        "instance_id":candidate["instance_id"]}
                ctype="AWS_EC2"
            else:
                config={"namespace":candidate["namespace"],"pod_name":candidate["pod_name"]}
                ctype="KUBERNETES"
            new_source=DataSource(organization_id=source.organization_id,name=display_name,
                source_type=ctype,connection_config=config,status="UNKNOWN",
                description="Approved read-only resource inventory; monitoring not yet activated")
            db.add(new_source);db.flush()
            db.add(Collector(data_source_id=new_source.id,name="provider-readonly",
                collector_type=ctype,configuration=config,enabled=False,status="STOPPED"))
            existing=new_source
        results.append({"external_id":external_id,"action":"WOULD_IMPORT" if payload.dry_run and new else
                        "IMPORTED" if new else "ALREADY_IMPORTED",
                        "data_source_id":str(existing.id) if existing else None,
                        "monitoring_status":"NOT_CONFIGURED"})
    if not payload.dry_run:db.commit()
    return {"dry_run":payload.dry_run,"resources":results}
