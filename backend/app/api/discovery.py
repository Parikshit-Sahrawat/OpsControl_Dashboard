"""Manual approval workflow for AWS/Kubernetes read-only discovery.

No auto-provisioned collector is enabled by import. Source ownership and
external identities are checked before creating typed resource inventory.
"""
import uuid
from datetime import datetime,timezone
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,ConfigDict,Field
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import (
    DataSource, Collector, KubernetesCluster, KubernetesClusterAssociation,
    KubernetesClusterAssociationDecision,
)
from app.security.scope import current_principal
from app.worker.provider_discovery import aws_ec2_candidates,k8s_pod_candidates,aws_eks_candidates
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
    if not principal or not principal.platform_admin:
        raise HTTPException(403,"Platform administrator must authorize discovery using deployment identity")
    if source.source_type not in {"AWS_EC2","EC2","AWS_EKS","KUBERNETES","K8S"}:
        raise HTTPException(422,"Source is not a supported resource-discovery connection")
    if not source.enabled:raise HTTPException(409,"Discovery source disabled")
    return source

def scan(source):
    try:
        if source.source_type in {"AWS_EC2","EC2"}:
            rows=aws_ec2_candidates(source.connection_config or {})
        elif source.source_type == "AWS_EKS":
            rows=aws_eks_candidates(source.connection_config or {})
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


def register_approved_eks(db, source, candidate, actor_id):
    """Serialize the verified ARN into one cluster and an explicit customer grant.

    Re-import never reactivates a revoked association. Namespace/workload scope
    remains empty: this discovery interface has no verified namespace UIDs.
    """
    identity = candidate["arn"]  # Verified against account/region/name by the reader.
    physical_id = candidate["provider_cluster_id"]
    # Serialize competing customer imports for the same provider identity.
    db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:identity, 0))"),
               {"identity": identity})
    if db.scalar(select(KubernetesCluster.id).where(
        KubernetesCluster.provider_identity == identity,
        KubernetesCluster.provider_cluster_id != physical_id,
    ).limit(1)):
        raise HTTPException(409, "Provider cluster identity changed; review prior association evidence")
    cluster_id = uuid.uuid4()
    db.execute(
        insert(KubernetesCluster).values(
            id=cluster_id, provider_identity=identity,
            provider_cluster_id=physical_id,
            created_at=datetime.now(timezone.utc),
        ).on_conflict_do_nothing(constraint="uq_k8s_verified_cluster_identity")
    )
    cluster = db.scalar(select(KubernetesCluster).where(
        KubernetesCluster.provider_identity == identity,
        KubernetesCluster.provider_cluster_id == physical_id,
    ).with_for_update())
    association = db.scalar(select(KubernetesClusterAssociation).where(
        KubernetesClusterAssociation.cluster_id == cluster.id,
        KubernetesClusterAssociation.organization_id == source.organization_id,
    ).with_for_update())
    if association is None:
        association = KubernetesClusterAssociation(
            cluster_id=cluster.id, organization_id=source.organization_id,
            revision=1, active=True,
        )
        db.add(association)
        db.flush()
        db.add(KubernetesClusterAssociationDecision(
            association_id=association.id, actor_id=actor_id, revision=1,
            active=True, reason="Approved read-only EKS discovery import",
        ))
    return cluster, association

@router.get("/capabilities")
def capabilities():
    return [
        {"provider":"AWS_EC2","discovery":True,"monitoring":True,
         "authentication":"AWS workload IAM role; expected account ID"},
        {"provider":"AWS_EKS","discovery":True,"monitoring":False,
         "authentication":"AWS workload IAM role; expected account/region; list/describe only"},
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
    actor=current_principal.get()
    for candidate in selected:
        external_id=candidate["external_id"]
        display_name=external_id[:200]
        existing=db.scalar(select(DataSource).where(
            DataSource.organization_id==source.organization_id,
            DataSource.discovery_external_id==external_id))
        new=existing is None
        if new and not payload.dry_run:
            if candidate["resource_type"]=="EC2_INSTANCE":
                config={"region":candidate["region"],"account_id":candidate["account_id"],
                        "instance_id":candidate["instance_id"]}
                ctype="AWS_EC2"
            elif candidate['resource_type']=='EKS_CLUSTER':
                config={'region':candidate['region'],'account_id':candidate['account_id'],
                        'cluster_names':[candidate['cluster_name']]}
                ctype='AWS_EKS'
            else:
                key={'K8S_POD':'pod_name','K8S_DEPLOYMENT':'deployment_name','K8S_NODE':'node_name'}[candidate['resource_type']]
                config={"namespace":candidate["namespace"],key:candidate[key]}
                ctype="KUBERNETES"
            new_source=DataSource(organization_id=source.organization_id,name=display_name,
                source_type=ctype,connection_config=config,status="UNKNOWN",discovery_external_id=external_id,
                description="Approved read-only resource inventory; monitoring not yet activated")
            db.add(new_source);db.flush()
            # EKS discovery does not imply a runnable host/Pod adapter. Avoid
            # manufacturing an unsupported enabled or dormant collector.
            if ctype != 'AWS_EKS':
                db.add(Collector(data_source_id=new_source.id,name="provider-readonly",
                    collector_type=ctype,configuration=config,enabled=False,status="STOPPED"))
            existing=new_source
        cluster=None
        association=None
        if (candidate["resource_type"] == "EKS_CLUSTER" and not payload.dry_run
                and candidate.get("provider_cluster_id")):
            cluster, association = register_approved_eks(db, source, candidate, actor.user_id)
        results.append({"external_id":external_id,"action":"WOULD_IMPORT" if payload.dry_run and new else
                        "IMPORTED" if new else "ALREADY_IMPORTED",
                        "data_source_id":str(existing.id) if existing else None,
                        **({"cluster_id":str(cluster.id),
                            "association_revision":association.revision,
                            "association_active":association.active} if cluster else
                           {"cluster_identity_status":"UNVERIFIED"}
                           if candidate["resource_type"] == "EKS_CLUSTER" else {}),
                        "monitoring_status":"NOT_CONFIGURED"})
    if not payload.dry_run:db.commit()
    return {"dry_run":payload.dry_run,"resources":results}
