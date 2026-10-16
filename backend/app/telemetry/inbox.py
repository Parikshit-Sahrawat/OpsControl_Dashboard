"""Durable, recipient-scoped in-app notifications with current RBAC rechecks."""

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, func, or_
from sqlalchemy.dialects.postgresql import insert
from app.db.session import SessionLocal, get_db
from app.security.scope import current_principal
from app.security.access_control import require_permission, resolve_access
from app.security.access_models import Department, DepartmentMembership
from app.security.models import User
from app.security.audit import log_event
from app.telemetry.models import InAppNotification
from app.telemetry.api import item

router = APIRouter(prefix="/api/v1/notifications", tags=["Personal Notifications"])


def validate_targets(db, configuration, organization_id, provider_id):
    """Generic failures do not disclose employee records to resource operators."""
    for identity in configuration.get("user_ids", []):
        user = db.get(User, uuid.UUID(identity))
        if (
            not user
            or not user.active
            or user.service_provider_id != provider_id
            or not resolve_access(db, user).allows("alerts.view", organization_id)
        ):
            raise HTTPException(
                422, "Notification recipient is not eligible for this organization"
            )
    for identity in configuration.get("department_ids", []):
        department = db.get(Department, uuid.UUID(identity))
        if (
            not department
            or not department.active
            or department.service_provider_id != provider_id
        ):
            raise HTTPException(422, "Notification team is not eligible")


def audience(db, configuration, organization_id):
    direct = {uuid.UUID(value) for value in configuration.get("user_ids", [])}
    teams = [uuid.UUID(value) for value in configuration.get("department_ids", [])]
    if teams:
        direct.update(
            db.scalars(
                select(DepartmentMembership.user_id)
                .join(Department, Department.id == DepartmentMembership.department_id)
                .where(
                    DepartmentMembership.department_id.in_(teams),
                    DepartmentMembership.active.is_(True),
                    Department.active.is_(True),
                )
            )
        )
    query = select(User).where(User.active.is_(True))
    if direct or teams or configuration.get("user_ids"):
        query = query.where(User.id.in_(direct))
    users = db.scalars(query.order_by(User.id).limit(1001)).all()
    if len(users) > 1000:
        raise RuntimeError("In-app recipient fanout exceeds the bounded delivery limit")
    return [
        user
        for user in users
        if (user.notification_preferences or {}).get("in_app", True)
        and resolve_access(db, user).allows("alerts.view", organization_id)
    ]


def persist(delivery, state, configuration=None):
    configuration = configuration or {}
    if delivery.alert_state_id != state.id:
        raise RuntimeError("Notification delivery/evidence association mismatch")
    with SessionLocal() as db:
        for user in audience(db, configuration, state.organization_id):
            db.execute(
                insert(InAppNotification)
                .values(
                    id=uuid.uuid4(),
                    organization_id=state.organization_id,
                    user_id=user.id,
                    delivery_id=delivery.id,
                    created_at=datetime.now(timezone.utc),
                )
                .on_conflict_do_nothing(index_elements=["delivery_id", "user_id"])
            )
        db.commit()
    return "in-app:" + str(delivery.id)


class Preference(BaseModel):
    model_config = ConfigDict(extra="forbid")
    in_app: bool


@router.get("")
def inbox(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db=Depends(get_db),
):
    p = require_permission("alerts.view")
    from app.models import AlertNotificationDelivery, AlertState

    from app.unified.pentaho_models import PentahoHistoricalNotice

    query = (
        select(InAppNotification, AlertState, PentahoHistoricalNotice)
        .outerjoin(
            AlertNotificationDelivery,
            AlertNotificationDelivery.id == InAppNotification.delivery_id,
        )
        .outerjoin(
            AlertState, AlertState.id == AlertNotificationDelivery.alert_state_id
        )
        .outerjoin(
            PentahoHistoricalNotice,
            PentahoHistoricalNotice.id == InAppNotification.historical_notice_id,
        )
        .where(
            InAppNotification.user_id == p.user_id,
            or_(
                AlertState.organization_id == InAppNotification.organization_id,
                PentahoHistoricalNotice.organization_id
                == InAppNotification.organization_id,
            ),
        )
    )
    if not p.platform_admin:
        query = query.where(InAppNotification.organization_id.in_(p.organizations))
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.execute(
        query.order_by(InAppNotification.created_at.desc(), InAppNotification.id)
        .limit(limit)
        .offset(offset)
    ).all()
    return {
        "items": [
            {
                **item(note),
                "message": (
                    state.message
                    if state
                    else "Historical failure: " + historical.payload["pipeline_name"]
                ),
                "severity": state.severity if state else "CRITICAL",
                "alert_state_id": str(state.id) if state else None,
                "status": state.status if state else historical.status,
                **(
                    {
                        "classification": "HISTORICAL_FAILURE",
                        "historical_evidence": historical.payload,
                    }
                    if historical
                    else {}
                ),
            }
            for note, state, historical in rows
        ],
        "total": total,
    }


@router.get("/preferences")
def preferences():
    p = require_permission("alerts.view")
    with SessionLocal() as db:
        user = db.get(User, p.user_id)
        return {"in_app": (user.notification_preferences or {}).get("in_app", True)}


@router.put("/preferences")
def save_preferences(payload: Preference):
    p = require_permission("alerts.view")
    with SessionLocal() as db:
        user = db.get(User, p.user_id)
        user.notification_preferences = payload.model_dump()
        log_event(
            db,
            event_type="NOTIFICATION_PREFERENCE_UPDATE",
            outcome="SUCCESS",
            actor_id=p.user_id,
            target_type="user",
            target_id=p.user_id,
        )
        db.commit()
    return payload.model_dump()
