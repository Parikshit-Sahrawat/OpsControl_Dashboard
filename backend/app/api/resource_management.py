from uuid import UUID
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, false, func, or_, select, true
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict, Field

from app.db.session import get_db
from app.api.pagination import CollectionPage, page
from app.models import (
    Collector, DataSource, Organization, KubernetesCluster,
    KubernetesClusterAssociation, KubernetesClusterAssociationDecision,
)
from app.security.scope import current_principal
from app.security.boundaries import permits, relevant
from app.schemas.monitoring import (
    CollectorCreate,
    CollectorOut,
    CollectorUpdate,
    DataSourceCreate,
    DataSourceOut,
    DataSourceUpdate,
)

router = APIRouter(prefix="/api/v1/resource-management", tags=["Resource Management"])


class ClusterAssociationChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1)
    active: Literal[False]
    reason: str = Field(min_length=3, max_length=2000)


def _cluster_view(cluster, association):
    return {
        "cluster_id": str(cluster.id),
        "organization_id": str(association.organization_id),
        "provider_identity": cluster.provider_identity,
        "provider_cluster_id": cluster.provider_cluster_id,
        "association_revision": association.revision,
        "monitoring_status": "UNKNOWN",
        "namespace_scope": [],
        "workload_scope": [],
    }


def _cluster_access(principal, organization_id, cluster_id, permission):
    return (
        organization_id in principal.organizations
        and principal.allows(permission, organization_id)
        and permits(principal, permission, organization_id, resource=cluster_id)
    )


def _cluster_read_filter(principal, customers):
    """Apply effective resource boundaries in SQL before counting or paging."""
    terms = []
    for customer in customers:
        if not principal.allows("resources.view", customer):
            continue
        limits = []
        denies = []
        for boundary in relevant(principal, customer, "resources.view"):
            scope = boundary["specification"]
            match = false() if scope["environments"] else (
                KubernetesCluster.id.in_(scope["resources"])
                if scope["resources"] else true()
            )
            (limits if boundary["kind"] == "LIMIT" else denies).append(match)
        terms.append(and_(
            KubernetesClusterAssociation.organization_id == customer,
            and_(*limits) if limits else true(),
            ~or_(*denies) if denies else true(),
        ))
    return or_(*terms) if terms else false()


@router.get("/kubernetes-clusters")
def list_kubernetes_clusters(
    organization_id: list[UUID] = Query(default=[]),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Cluster-only projection. No namespace, workload or telemetry is inferred."""
    principal = current_principal.get()
    allowed = set(principal.organizations)
    if organization_id:
        allowed.intersection_update(organization_id)
    if not allowed:
        return {"items": [], "total": 0, "limit": limit, "offset": offset}
    query = (
        select(KubernetesCluster, KubernetesClusterAssociation)
        .join(KubernetesClusterAssociation,
              KubernetesClusterAssociation.cluster_id == KubernetesCluster.id)
        .where(KubernetesClusterAssociation.active.is_(True),
               _cluster_read_filter(principal, allowed))
    )
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.execute(
        query
        .order_by(KubernetesCluster.provider_identity,
                  KubernetesClusterAssociation.organization_id)
        .limit(limit).offset(offset)
    ).all()
    return {"items": [_cluster_view(cluster, association) for cluster, association in rows],
            "total": total,
            "limit": limit, "offset": offset}


@router.get("/kubernetes-clusters/{cluster_id}")
def get_kubernetes_cluster(cluster_id: UUID, db: Session = Depends(get_db)):
    principal = current_principal.get()
    rows = db.execute(
        select(KubernetesCluster, KubernetesClusterAssociation)
        .join(KubernetesClusterAssociation,
              KubernetesClusterAssociation.cluster_id == KubernetesCluster.id)
        .where(KubernetesCluster.id == cluster_id,
               KubernetesClusterAssociation.active.is_(True),
               _cluster_read_filter(principal, principal.organizations))
    ).all()
    visible = [_cluster_view(cluster, association) for cluster, association in rows]
    if not visible:
        raise HTTPException(404, "Cluster not found")
    return {"associations": visible}


@router.patch("/kubernetes-clusters/{cluster_id}/associations/{organization_id}")
def change_kubernetes_cluster_association(
    cluster_id: UUID, organization_id: UUID, payload: ClusterAssociationChange,
    db: Session = Depends(get_db),
):
    principal = current_principal.get()
    if not principal.platform_admin or not _cluster_access(
        principal, organization_id, cluster_id, "resources.update"
    ):
        raise HTTPException(403, "Cluster association administration denied")
    association = db.scalar(select(KubernetesClusterAssociation).where(
        KubernetesClusterAssociation.cluster_id == cluster_id,
        KubernetesClusterAssociation.organization_id == organization_id,
    ).with_for_update())
    if association is None:
        raise HTTPException(404, "Cluster association not found")
    if association.revision != payload.expected_revision:
        raise HTTPException(409, "Cluster association revision changed")
    if association.active == payload.active:
        raise HTTPException(409, "Cluster association state is unchanged")
    association.revision += 1
    association.active = payload.active
    db.add(KubernetesClusterAssociationDecision(
        association_id=association.id, actor_id=principal.user_id,
        revision=association.revision, active=association.active,
        reason=payload.reason,
    ))
    db.commit()
    return {"cluster_id": str(cluster_id), "organization_id": str(organization_id),
            "association_revision": association.revision, "active": association.active}


def _org(
    db: Session, organization_id: UUID, require_active: bool = False
) -> Organization:
    item = db.get(Organization, organization_id)
    if not item:
        raise HTTPException(status_code=404, detail="Organization not found")
    if require_active and not item.active:
        raise HTTPException(status_code=409, detail="Organization is inactive")
    return item


def _source(db: Session, data_source_id: UUID) -> DataSource:
    item = db.get(DataSource, data_source_id)
    if not item:
        raise HTTPException(status_code=404, detail="Data source not found")
    return item


@router.get(
    "/data-sources", response_model=list[DataSourceOut] | CollectionPage[DataSourceOut]
)
def list_scoped_data_sources(
    organization_id: list[UUID] = Query(default=[]),
    enabled: bool | None = None,
    limit: int = Query(500, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    paginated: bool = False,
    search: str = Query("", max_length=200),
    db: Session = Depends(get_db),
):
    stmt = select(DataSource)
    if organization_id:
        stmt = stmt.where(DataSource.organization_id.in_(organization_id))
    if enabled is not None:
        stmt = stmt.where(DataSource.enabled == enabled)
    if search:
        stmt = stmt.where(DataSource.name.ilike("%" + search + "%"))
    ordering = (DataSource.name, DataSource.id)
    if paginated:
        return page(
            db, stmt, ordering, limit, offset, lambda r: DataSourceOut.model_validate(r)
        )
    return db.scalars(stmt.order_by(*ordering).offset(offset).limit(limit)).all()


@router.post("/data-sources", response_model=DataSourceOut, status_code=201)
def create_scoped_data_source(payload: DataSourceCreate, db: Session = Depends(get_db)):
    _org(db, payload.organization_id, require_active=True)
    item = DataSource(**payload.model_dump())
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Data source name already exists in this organization",
        )
    db.refresh(item)
    return item


@router.patch("/data-sources/{data_source_id}", response_model=DataSourceOut)
def update_scoped_data_source(
    data_source_id: UUID,
    payload: DataSourceUpdate,
    db: Session = Depends(get_db),
):
    item = _source(db, data_source_id)
    values = payload.model_dump(exclude_unset=True)
    for key, value in values.items():
        setattr(item, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Data source name already exists in this organization",
        )
    db.refresh(item)
    return item


@router.delete("/data-sources/{data_source_id}", status_code=204)
def disable_scoped_data_source(data_source_id: UUID, db: Session = Depends(get_db)):
    item = _source(db, data_source_id)
    item.enabled = False
    db.commit()


@router.get(
    "/collectors", response_model=list[CollectorOut] | CollectionPage[CollectorOut]
)
def list_scoped_collectors(
    data_source_id: list[UUID] = Query(default=[]),
    limit: int = Query(500, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    paginated: bool = False,
    search: str = Query("", max_length=200),
    db: Session = Depends(get_db),
):
    stmt = select(Collector)
    if data_source_id:
        stmt = stmt.where(Collector.data_source_id.in_(data_source_id))
    else:
        return (
            {
                "items": [],
                "total": 0,
                "limit": limit,
                "offset": offset,
                "has_more": False,
            }
            if paginated
            else []
        )
    if search:
        stmt = stmt.where(Collector.name.ilike("%" + search + "%"))
    ordering = (Collector.name, Collector.id)
    if paginated:
        return page(
            db, stmt, ordering, limit, offset, lambda r: CollectorOut.model_validate(r)
        )
    return db.scalars(stmt.order_by(*ordering).offset(offset).limit(limit)).all()


@router.post("/collectors", response_model=CollectorOut, status_code=201)
def create_scoped_collector(payload: CollectorCreate, db: Session = Depends(get_db)):
    source = _source(db, payload.data_source_id)
    if not source.enabled:
        raise HTTPException(
            status_code=409, detail="Cannot add a collector to a disabled data source"
        )
    item = Collector(**payload.model_dump())
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Collector name already exists for this data source"
        )
    db.refresh(item)
    return item


@router.patch("/collectors/{collector_id}", response_model=CollectorOut)
def update_scoped_collector(
    collector_id: UUID,
    payload: CollectorUpdate,
    db: Session = Depends(get_db),
):
    item = db.get(Collector, collector_id)
    if not item:
        raise HTTPException(status_code=404, detail="Collector not found")
    values = payload.model_dump(exclude_unset=True)
    for key, value in values.items():
        setattr(item, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Collector name already exists for this data source"
        )
    db.refresh(item)
    return item


@router.delete("/collectors/{collector_id}", status_code=204)
def disable_scoped_collector(collector_id: UUID, db: Session = Depends(get_db)):
    item = db.get(Collector, collector_id)
    if not item:
        raise HTTPException(status_code=404, detail="Collector not found")
    item.enabled = False
    item.status = "STOPPED"
    db.commit()
