"""Historical failure obligations and bounded delivery on existing transports."""

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from sqlalchemy import select, tuple_
from sqlalchemy.dialects.postgresql import insert
from app.db.session import SessionLocal
from app.models import JobOrder, JobOrderHistory
from app.unified.models import MonitoringResource, NormalizedEvent
from app.unified.pentaho_models import (
    PentahoHistoricalNotice as Notice,
    PentahoRevision,
    PentahoEvidenceReview,
)
from app.unified.pentaho_review import verified_candidate, unqueued_identity_evidence
from app.security.audit import log_event
from app.security.scope import current_principal
from app.telemetry.models import NotificationDestination, InAppNotification
from app.data_pipelines import service as s


def policy(resource):
    return resource.configuration.get("historical_notifications") or {}


def eligible(db, resource, history, event):
    if (
        event.processing_status == "UNRESOLVED"
        or event.processing_error == "PENTAHO_CLAIM_REJECTED_BY_REVIEW"
    ):
        return False
    if (
        history.pentaho_outcome != "FAILED"
        or history.pentaho_lifecycle != "TERMINAL"
        or history.pentaho_identity_state != "CONFIRMED"
        or history.pentaho_review_state not in {None, "CLEAR"}
    ):
        return False
    if unqueued_identity_evidence(db, history) or db.scalar(
        select(PentahoEvidenceReview.id)
        .where(
            PentahoEvidenceReview.history_id == history.id,
            PentahoEvidenceReview.status == "OPEN",
        )
        .limit(1)
    ):
        return False
    try:
        claim = verified_candidate(db, resource, event)
    except Exception as error:
        from fastapi import HTTPException

        if isinstance(error, HTTPException):
            return False
        raise
    native = claim["native"]
    return (
        "EXECUTION_OUTCOME" in claim["claims"]
        and native.get("completion_evidence") is True
        and native.get("native_outcome") == "FAILED"
        and history.ended_at is not None
    )


def reconcile(db, resource, observed=None):
    """Caller holds resource/JobOrder lock; no notification IO in this transaction."""
    config = policy(resource)
    observed = observed or s.clock(db)
    db.scalar(
        select(JobOrder).where(JobOrder.id == resource.job_order_id).with_for_update()
    )
    scan, _ = s.operation(
        db,
        resource.organization_id,
        "PENTAHO_HISTORICAL_SCAN",
        str(resource.id),
        {},
        None,
    )
    query = select(JobOrderHistory).where(
        JobOrderHistory.pentaho_resource_id == resource.id,
        JobOrderHistory.pentaho_outcome == "FAILED",
    )
    cursor = scan.result.get("cursor")
    if cursor:
        query = query.where(
            tuple_(JobOrderHistory.created_at, JobOrderHistory.id)
            > (
                datetime.fromisoformat(cursor["created_at"]),
                uuid.UUID(cursor["history_id"]),
            )
        )
    histories = list(
        db.scalars(
            query.order_by(JobOrderHistory.created_at, JobOrderHistory.id).limit(200)
        )
    )
    scan.result = {
        "cursor": (
            {
                "created_at": histories[-1].created_at.isoformat(),
                "history_id": str(histories[-1].id),
            }
            if histories
            else None
        )
    }
    scan.state = "COMPLETE"
    created = 0
    for history in histories:
        # Pick a failure claim, not the newest arrival of any type or a successful
        # manual recovery execution. Native attempt/history UUID stays canonical.
        revisions = db.scalars(
            select(PentahoRevision)
            .where(
                PentahoRevision.history_id == history.id,
                PentahoRevision.payload["identity"]["native_outcome"].astext
                == "FAILED",
            )
            .order_by(PentahoRevision.created_at, PentahoRevision.id)
            .limit(200)
        )
        event = next(
            (
                db.get(NormalizedEvent, v.event_id)
                for v in revisions
                if eligible(db, resource, history, db.get(NormalizedEvent, v.event_id))
            ),
            None,
        )
        if not event:
            continue
        from app.native_incidents.pentaho import correlate_history

        if (event.received_at - history.ended_at).total_seconds() < config.get(
            "historical_after_seconds", 3600
        ):
            correlate_history(db, resource, history, observed)
            continue
        history.source_evidence = {
            **(history.source_evidence or {}),
            "pentaho_historical": {
                "occurred_at": history.ended_at.isoformat(),
                "discovered_at": event.received_at.isoformat(),
                "event_id": str(event.id),
                "operational_reassessment_required": True,
                "notification_eligibility": (
                    "ELIGIBLE" if config.get("enabled") else "POLICY_NOT_CONFIGURED"
                ),
            },
        }
        if (history.source_evidence or {}).get("pentaho_adjudication"):
            history.source_evidence = {
                **history.source_evidence,
                "pentaho_adjudication": {
                    **history.source_evidence["pentaho_adjudication"],
                    "notification_eligibility": (
                        "ELIGIBLE_HISTORICAL_ONLY"
                        if config.get("enabled")
                        else "POLICY_NOT_CONFIGURED"
                    ),
                },
            }
        correlate_history(db, resource, history, observed)
        if not config.get("enabled"):
            continue
        for target in config.get("destination_ids", []):
            destination = db.get(NotificationDestination, uuid.UUID(target))
            if (
                not destination
                or destination.organization_id != resource.organization_id
                or not destination.enabled
            ):
                continue
            payload = {
                "classification": "HISTORICAL_FAILURE",
                "resource_id": str(resource.id),
                "pipeline_name": resource.name,
                "execution_id": str(history.id),
                "occurred_at": history.ended_at.isoformat(),
                "discovered_at": event.received_at.isoformat(),
                "evidence_id": str(event.id),
                "source_evidence_id": event.payload["pentaho_verification"][
                    "evidence_id"
                ],
                "operational_incident_reassessment": "REQUIRED_NO_AUTOMATIC_REOPEN",
                "notification_policy": "EXPLICIT_CUSTOMER_DESTINATIONS",
            }
            id = uuid.uuid4()
            saved = db.execute(
                insert(Notice)
                .values(
                    id=id,
                    organization_id=resource.organization_id,
                    resource_id=resource.id,
                    history_id=history.id,
                    event_id=event.id,
                    destination_id=destination.id,
                    payload=payload,
                    status="PENDING",
                    attempts=0,
                    created_at=observed,
                    next_attempt_at=observed,
                )
                .on_conflict_do_nothing(index_elements=["history_id", "destination_id"])
                .returning(Notice.id)
            ).scalar()
            if saved:
                created += 1
                log_event(
                    db,
                    event_type="PENTAHO_HISTORICAL_NOTICE_QUEUED",
                    outcome="SUCCESS",
                    actor_id=(
                        current_principal.get().user_id
                        if current_principal.get()
                        else None
                    ),
                    organization_id=resource.organization_id,
                    target_type="pentaho_historical_notice",
                    target_id=id,
                )
    db.flush()
    return created


def persist_in_app(notice, context, configuration):
    from app.telemetry.inbox import audience

    if not configuration.get("user_ids") and not configuration.get("department_ids"):
        raise RuntimeError("Explicit historical notification recipients required")
    with SessionLocal() as db:
        resource = db.get(MonitoringResource, notice.resource_id)
        db.scalar(
            select(JobOrder)
            .where(JobOrder.id == resource.job_order_id)
            .with_for_update()
        )
        current = db.scalar(
            select(Notice).where(Notice.id == notice.id).with_for_update()
        )
        if (
            current.status != "PROCESSING"
            or current.lease_token != notice.lease_token
            or current.lease_until <= s.clock(db)
            or not policy(resource).get("enabled")
            or str(notice.destination_id)
            not in policy(resource).get("destination_ids", [])
            or not eligible(
                db,
                resource,
                db.get(JobOrderHistory, notice.history_id),
                db.get(NormalizedEvent, notice.event_id),
            )
        ):
            raise RuntimeError("Historical delivery no longer eligible")
        recipients = audience(db, configuration, notice.organization_id)
        if not recipients:
            raise RuntimeError("No eligible recipients; historical delivery not sent")
        for user in recipients:
            db.execute(
                insert(InAppNotification)
                .values(
                    id=uuid.uuid4(),
                    organization_id=notice.organization_id,
                    user_id=user.id,
                    historical_notice_id=notice.id,
                    created_at=datetime.now(timezone.utc),
                )
                .on_conflict_do_nothing(
                    index_elements=["historical_notice_id", "user_id"]
                )
            )
        db.commit()
    return "historical-in-app:" + str(notice.id)


def claim_notice(organization_id=None):
    with SessionLocal() as db:
        now = s.clock(db)
        exhausted = list(
            db.scalars(
                select(Notice)
                .where(
                    Notice.status == "PROCESSING",
                    Notice.lease_until <= now,
                    Notice.attempts >= 5,
                )
                .with_for_update(skip_locked=True)
                .limit(20)
            )
        )
        for expired in exhausted:
            expired.status = "FAILED"
            expired.last_error = "Historical notification retry limit reached"
            expired.lease_token = None
            expired.lease_until = None
            log_event(
                db,
                event_type="PENTAHO_HISTORICAL_NOTICE_FAILED",
                outcome="FAILURE",
                organization_id=expired.organization_id,
                target_type="pentaho_historical_notice",
                target_id=expired.id,
            )
        db.flush()
        row = db.scalar(
            select(Notice)
            .where(
                Notice.organization_id == organization_id if organization_id else True,
                Notice.attempts < 5,
                Notice.next_attempt_at <= now,
                (
                    (Notice.status.in_(["PENDING", "FAILED", "BLOCKED"]))
                    | ((Notice.status == "PROCESSING") & (Notice.lease_until <= now))
                ),
            )
            .order_by(Notice.next_attempt_at, Notice.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if not row:
            db.commit()
            return None
        resource = db.get(MonitoringResource, row.resource_id)
        history = db.get(JobOrderHistory, row.history_id)
        event = db.get(NormalizedEvent, row.event_id)
        from app.models import Organization

        customer = db.get(Organization, row.organization_id)
        if (
            not customer
            or not customer.active
            or not policy(resource).get("enabled")
            or str(row.destination_id)
            not in policy(resource).get("destination_ids", [])
            or not eligible(db, resource, history, event)
        ):
            row.status = "BLOCKED"
            row.next_attempt_at = now + timedelta(seconds=60)
            db.commit()
            return None
        row.status = "PROCESSING"
        row.attempts += 1
        row.lease_token = uuid.uuid4()
        row.lease_until = now + timedelta(seconds=120)
        db.flush()
        db.expunge(row)
        db.commit()
        return row


def finish_notice(id, token, reference=None, error=None):
    with SessionLocal() as db:
        now = s.clock(db)
        row = db.scalar(
            select(Notice)
            .where(
                Notice.id == id,
                Notice.status == "PROCESSING",
                Notice.lease_token == token,
                Notice.lease_until > now,
            )
            .with_for_update()
        )
        if not row:
            return False
        row.status = "FAILED" if error else "SENT"
        row.last_error = error
        row.external_reference = reference
        row.sent_at = now if reference else None
        row.next_attempt_at = now + timedelta(seconds=min(3600, 15 * 2**row.attempts))
        row.lease_token = None
        row.lease_until = None
        log_event(
            db,
            event_type="PENTAHO_HISTORICAL_NOTICE_" + row.status,
            outcome="FAILURE" if error else "SUCCESS",
            organization_id=row.organization_id,
            target_type="pentaho_historical_notice",
            target_id=row.id,
        )
        db.commit()
        return True


def dispatch_notices(limit=5, organization_id=None):
    from app.telemetry.delivery import send_destination
    from app.worker.notifications import _safe_delivery_error

    counts = {"sent": 0, "failed": 0, "fenced": 0}
    for _ in range(min(limit, 20)):
        row = claim_notice(organization_id)
        if not row:
            break
        context = SimpleNamespace(
            organization_id=row.organization_id,
            severity="CRITICAL",
            message="Historical Pentaho failure: "
            + row.payload["pipeline_name"]
            + "; execution "
            + str(row.history_id)
            + "; occurred "
            + row.payload["occurred_at"]
            + "; discovered "
            + row.payload["discovered_at"],
        )
        # Existing destination validation/secret references/TLS/egress restrictions.
        row.channel = "DEST:" + str(row.destination_id)
        row.event_type = "HISTORICAL_FAILURE"
        try:
            reference = send_destination(row, context, historical=True)
            if not isinstance(reference, str) or not 1 <= len(reference) <= 500:
                raise ValueError("Invalid delivery reference")
            complete = finish_notice(row.id, row.lease_token, reference=reference)
            counts["sent" if complete else "fenced"] += 1
        except Exception as error:
            complete = finish_notice(
                row.id, row.lease_token, error=_safe_delivery_error(error)
            )
            counts["failed" if complete else "fenced"] += 1
    return counts
