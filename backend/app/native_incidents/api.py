"""Customer-scoped native incidents; transitions require real recovery evidence."""

from uuid import UUID
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, func, or_, cast, String
from app.db.session import get_db
from app.models import OperationalIncident, IncidentActivity
from app.native_incidents.models import NativeIncidentDetails, NativeIncidentAlert
from app.native_incidents import service
from app.security.access_control import require_permission, resolve_access
from app.security.models import User
from app.unified.schemas import Environment
from app.unified.models import (
    MonitoringResource,
    ResourceCondition,
    EventCorrelationGroup,
)

router = APIRouter(prefix="/api/v1/native-incidents", tags=["Native Incidents"])
State = Literal[
    "OPEN",
    "ACKNOWLEDGED",
    "INVESTIGATING",
    "RECOVERY_IN_PROGRESS",
    "MONITORING",
    "RESOLVED",
    "CLOSED",
]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Revision(Input):
    revision: int = Field(ge=1)


class Transition(Revision):
    status: State
    note: str | None = Field(default=None, max_length=4000)


class Note(Input):
    text: str = Field(min_length=1, max_length=4000)
    evidence_reference: str | None = Field(default=None, max_length=1000)


class Assignment(Revision):
    assigned_user_id: UUID | None


class Escalation(Revision):
    note: str = Field(min_length=1, max_length=4000)


def serialized(row):
    return {c.name: getattr(row, c.name) for c in row.__table__.columns}


def item(db, row):
    result = serialized(row)
    d = db.get(NativeIncidentDetails, row.id)
    result["details"] = (
        serialized(d)
        if d
        else {
            "assigned_user_id": None,
            "revision": 1,
            "recovery_started_at": None,
            "monitoring_started_at": None,
            "monitoring_seconds": 60,
            "escalation_level": 0,
            "verified_at": None,
            "evidence": {},
        }
    )
    return result


def checked(db, incident_id, permission, lock=False):
    require_permission(permission)
    query = select(OperationalIncident).where(OperationalIncident.id == incident_id)
    row = db.scalar(query.with_for_update() if lock else query)
    if not row:
        raise HTTPException(404, "Incident not found")
    require_permission(permission, row.organization_id)
    return row


def check_revision(db, row, revision):
    d = service.details(db, row)
    if d.revision != revision:
        raise HTTPException(409, "Incident changed; refresh before saving")
    return d


@router.get("")
def inventory(
    organization_id: list[UUID] | None = Query(None),
    status: State | None = None,
    environment: Environment | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db=Depends(get_db),
):
    require_permission("incidents.view")
    query = select(OperationalIncident)
    if organization_id:
        for organization in organization_id:
            require_permission("incidents.view", organization)
        query = query.where(OperationalIncident.organization_id.in_(organization_id))
    if environment:
        # An environment filter requires an actual resource/correlation binding.
        # Unmapped legacy evidence remains unknown, never guessed from names.
        bound = (
            select(NativeIncidentAlert.incident_id)
            .join(
                ResourceCondition,
                ResourceCondition.alert_state_id == NativeIncidentAlert.alert_state_id,
            )
            .join(
                MonitoringResource,
                MonitoringResource.id == ResourceCondition.resource_id,
            )
            .where(
                MonitoringResource.environment == environment,
                MonitoringResource.organization_id
                == NativeIncidentAlert.organization_id,
            )
        )
        sources = select(MonitoringResource.data_source_id).where(
            MonitoringResource.environment == environment
        )
        groups = select(cast(EventCorrelationGroup.id, String)).where(
            EventCorrelationGroup.environment == environment
        )
        query = query.where(
            or_(
                OperationalIncident.id.in_(bound),
                OperationalIncident.data_source_id.in_(sources),
                (OperationalIncident.source_kind == "CORRELATION")
                & OperationalIncident.source_reference.in_(groups),
            )
        )
    if status:
        query = query.where(OperationalIncident.status == status)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.scalars(
        query.order_by(OperationalIncident.opened_at.desc(), OperationalIncident.id)
        .limit(limit)
        .offset(offset)
    ).all()
    return {
        "items": [item(db, r) for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{incident_id}")
def detail(incident_id: UUID, db=Depends(get_db)):
    row = checked(db, incident_id, "incidents.view")
    result = item(db, row)
    snapshots = {
        link.alert_state_id: link.evidence
        for link in db.scalars(
            select(NativeIncidentAlert).where(
                NativeIncidentAlert.incident_id == row.id,
                NativeIncidentAlert.organization_id == row.organization_id,
            )
        )
    }
    result["alerts"] = [
        {**serialized(a), "incident_evidence": snapshots.get(a.id, {})}
        for a in service.linked_alerts(db, row)
    ]
    result["activities"] = [
        serialized(a)
        for a in db.scalars(
            select(IncidentActivity)
            .where(
                IncidentActivity.incident_id == row.id,
                IncidentActivity.organization_id == row.organization_id,
            )
            .order_by(IncidentActivity.occurred_at.desc(), IncidentActivity.id)
            .limit(200)
        )
    ]
    result["recovery"] = (
        service.recovery(db, row)
        if db.get(NativeIncidentDetails, row.id)
        else {
            "ready": False,
            "reasons": ["Enter the recovery workflow to verify this historic incident"],
            "evidence": {},
        }
    )
    return result


@router.get("/{incident_id}/recovery-preview")
def recovery_preview(incident_id: UUID, db=Depends(get_db)):
    return detail(incident_id, db)["recovery"]


@router.post("/{incident_id}/transition")
def transition(incident_id: UUID, body: Transition, db=Depends(get_db)):
    key = (
        "incidents.acknowledge" if body.status == "ACKNOWLEDGED" else "incidents.manage"
    )
    row = checked(db, incident_id, key, True)
    p = require_permission(key, row.organization_id)
    service.transition(
        db, row, body.status, body.revision, p.username, p.user_id, body.note
    )
    db.commit()
    return item(db, row)


@router.post("/{incident_id}/notes")
def note(incident_id: UUID, body: Note, db=Depends(get_db)):
    row = checked(db, incident_id, "incidents.manage", True)
    p = require_permission("incidents.manage", row.organization_id)
    text = body.text + (
        "\nEvidence: " + body.evidence_reference if body.evidence_reference else ""
    )
    service.record(db, row, "NOTE", p.username, text, actor_id=p.user_id)
    service.details(db, row).revision += 1
    db.commit()
    return item(db, row)


@router.post("/{incident_id}/assignment")
def assignment(incident_id: UUID, body: Assignment, db=Depends(get_db)):
    row = checked(db, incident_id, "incidents.manage", True)
    p = require_permission("incidents.manage", row.organization_id)
    d = check_revision(db, row, body.revision)
    if body.assigned_user_id:
        user = db.get(User, body.assigned_user_id)
        if (
            not user
            or not user.active
            or user.service_provider_id != p.service_provider_id
        ):
            raise HTTPException(422, "Select an active authorized employee")
        if not resolve_access(db, user).allows("incidents.manage", row.organization_id):
            raise HTTPException(
                422, "Employee lacks incident authority for this organization"
            )
    d.assigned_user_id = body.assigned_user_id
    d.revision += 1
    service.record(db, row, "ASSIGNED", p.username, actor_id=p.user_id)
    db.commit()
    return item(db, row)


@router.post("/{incident_id}/escalate")
def escalate(incident_id: UUID, body: Escalation, db=Depends(get_db)):
    row = checked(db, incident_id, "incidents.manage", True)
    p = require_permission("incidents.manage", row.organization_id)
    d = check_revision(db, row, body.revision)
    if row.status == "CLOSED":
        raise HTTPException(409, "Reopen before escalating")
    d.escalation_level += 1
    d.revision += 1
    service.record(db, row, "ESCALATED", p.username, body.note, actor_id=p.user_id)
    db.commit()
    return item(db, row)


@router.post("/{incident_id}/recovery-validation")
def verify(incident_id: UUID, body: Revision, db=Depends(get_db)):
    row = checked(db, incident_id, "incidents.manage", True)
    p = require_permission("incidents.manage", row.organization_id)
    d = check_revision(db, row, body.revision)
    proof = service.recovery(db, row)
    if row.status != "MONITORING" or not proof["ready"]:
        raise HTTPException(409, {"message": "Recovery is not verified", **proof})
    d.verified_at = service.utc()
    d.evidence = {**(d.evidence or {}), **proof["evidence"]}
    d.revision += 1
    service.record(db, row, "RECOVERY_VERIFIED", p.username, actor_id=p.user_id)
    db.commit()
    return {**proof, "incident": item(db, row)}
