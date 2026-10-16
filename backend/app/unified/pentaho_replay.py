"""Bounded re-reduction of already accepted, verifiable native evidence.

This is not a Pentaho Server replay API or a file rewind. Provider/file replay
remains unsupported without an independently verified continuity capability.
"""

import uuid
from datetime import datetime, timedelta
from sqlalchemy import select, tuple_, cast, DateTime, func
from app.data_pipelines import service as s
from app.data_pipelines.models import (
    PipelineIntegration,
    PipelineOperation,
    PipelineSource,
)
from app.unified.models import MonitoringResource, NormalizedEvent
from app.unified.pentaho_review import verified_candidate
from app.unified.reconstruction import reduce_execution

MODE = "ACCEPTED_PENTAHO_EVIDENCE"


def is_pentaho(db, source):
    return any(
        db.get(PipelineIntegration, m.integration_id).platform == "PENTAHO"
        for m in s.methods(db, source)
    )


def run_batch(db, source, operation, ticket, limit=50):
    s.check_ticket(db, source, ticket)
    if (
        operation.kind != "RECOVERY"
        or operation.source_id != source.id
        or operation.organization_id != source.organization_id
    ):
        raise s.PipelineError("RECOVERY_SOURCE_SCOPE_INVALID")
    if s.suspended(db, source):
        raise s.PipelineError("SOURCE_SUSPENDED")
    if not source.continuity_validated:
        raise s.PipelineError("CONTINUITY_NOT_VERIFIED")
    if not source.next_run_at or source.next_run_at <= s.clock(db):
        raise s.PipelineError("LIVE_COLLECTION_HAS_PRIORITY")
    if operation.configuration.get("generation") != str(source.generation):
        raise s.PipelineError("RECOVERY_GENERATION_CHANGED")
    if operation.configuration.get("mode") != MODE:
        raise s.PipelineError("PENTAHO_PROVIDER_REPLAY_UNSUPPORTED")
    if operation.state not in {"PENDING", "APPROVED", "RUNNING"}:
        raise s.PipelineError("RECOVERY_NOT_ELIGIBLE")
    # Recheck risk policy at execution, not only at the original plan endpoint.
    start = datetime.fromisoformat(operation.configuration["start"])
    end = datetime.fromisoformat(operation.configuration["end"])
    risky = (end - start).total_seconds() > s.RECOVERY_BOUNDS[source.method_type] or (
        s.clock(db) - start
    ).total_seconds() > s.RECOVERY_BOUNDS[source.method_type]
    if risky and (
        not operation.reviewer_id or operation.reviewer_id == operation.actor_id
    ):
        raise s.PipelineError("INDEPENDENT_REPLAY_APPROVAL_REQUIRED")
    from app.security.access_control import resolve_access
    from app.security.models import User

    user = db.get(User, operation.actor_id)
    if (
        not user
        or not user.active
        or not resolve_access(db, user).allows("etl.replay", source.organization_id)
    ):
        raise s.PipelineError("REPLAY_AUTHORIZATION_REVOKED")
    if risky:
        reviewer = db.get(User, operation.reviewer_id)
        if (
            not reviewer
            or not reviewer.active
            or not resolve_access(db, reviewer).allows(
                "etl.approve_replay", source.organization_id
            )
        ):
            raise s.PipelineError("REPLAY_APPROVAL_REVOKED")
    cursor = operation.result.get("reconciliation_cursor")
    query = select(NormalizedEvent).where(
        NormalizedEvent.organization_id == source.organization_id,
        NormalizedEvent.payload["pentaho_verification"]["source_id"].astext
        == str(source.id),
        NormalizedEvent.payload["pentaho_verification"]["generation"].astext
        == str(source.generation),
        func.coalesce(
            cast(NormalizedEvent.payload["timestamp"].astext, DateTime(timezone=True)),
            NormalizedEvent.observed_at,
        )
        >= start,
        func.coalesce(
            cast(NormalizedEvent.payload["timestamp"].astext, DateTime(timezone=True)),
            NormalizedEvent.observed_at,
        )
        <= end,
    )
    if cursor:
        query = query.where(
            tuple_(NormalizedEvent.received_at, NormalizedEvent.id)
            > (
                datetime.fromisoformat(cursor["received_at"]),
                uuid.UUID(cursor["event_id"]),
            )
        )
    rows = list(
        db.scalars(
            query.order_by(NormalizedEvent.received_at, NormalizedEvent.id).limit(
                min(limit, 50) + 1
            )
        )
    )
    handled = 0
    for event in rows[: min(limit, 50)]:
        resource = db.get(MonitoringResource, event.resource_id)
        if not resource or resource.organization_id != source.organization_id:
            raise s.PipelineError("REPLAY_RESOURCE_SCOPE_CHANGED")
        if event.processing_status in {"PENDING", "PROCESSED"}:
            verified_candidate(db, resource, event)
            reduce_execution(db, resource, event.payload["execution_id"])
        # UNRESOLVED/REVIEWED evidence remains under its existing adjudication;
        # advancing this operation cursor is not accepting or releasing a claim.
        from app.unified.pentaho_history import reconcile

        reconcile(db, resource)
        cursor = {
            "received_at": event.received_at.isoformat(),
            "event_id": str(event.id),
        }
        handled += 1
    s.check_ticket(db, source, ticket)
    operation.result = {
        **operation.result,
        "reconciliation_cursor": cursor,
        "processed": operation.result.get("processed", 0) + handled,
        "coverage_status": "ACCEPTED_RECORDS_ONLY_NO_GAP_CLOSURE",
        "provider_collection_performed": False,
        "live_checkpoint_unchanged": True,
    }
    operation.state = "PENDING" if len(rows) > min(limit, 50) else "COMPLETE"
    source.lease_until = s.clock(db)
    # Physical method replay cursors remain untouched: they cannot be replaced
    # by an event UUID. The separate cursor is durable per recovery range.
    return handled


def run(id):
    from app.db.session import SessionLocal

    ticket = operation_ticket = None
    try:
        with SessionLocal() as db:
            operation = db.get(PipelineOperation, id)
            if not operation:
                return
            source = db.get(PipelineSource, operation.source_id)
            current = s.clock(db)
            if operation.state not in {"PENDING", "APPROVED"} and not (
                operation.state == "RUNNING"
                and operation.lease_until
                and operation.lease_until <= current
            ):
                return
            if not source.next_run_at or source.next_run_at <= current:
                return
            ticket = s.acquire(db, source.id, uuid.uuid4(), 120)
            operation = db.scalar(
                select(PipelineOperation)
                .where(PipelineOperation.id == id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            operation.fence += 1
            operation.owner_id = uuid.UUID(ticket["owner_id"])
            operation.lease_until = source.lease_until
            operation.state = "RUNNING"
            operation.attempts += 1
            operation_ticket = {"id": operation.id, "fence": operation.fence}
            db.commit()
            source = s.locked_source(db, source.id)
            operation = db.scalar(
                select(PipelineOperation)
                .where(PipelineOperation.id == id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if (
                operation.fence != operation_ticket["fence"]
                or str(operation.owner_id) != ticket["owner_id"]
                or operation.state != "RUNNING"
            ):
                raise s.PipelineError("OPERATION_CLAIM_EXPIRED")
            run_batch(db, source, operation, ticket)
            operation.lease_until = s.clock(db)
            s.event(db, operation, "PENTAHO_RECONCILIATION", operation.actor_id)
            db.commit()
    except Exception as error:
        if ticket and operation_ticket:
            failure(ticket, operation_ticket, error)


def failure(ticket, operation_ticket, error):
    """Fence cleanup independently; replay errors never change live health."""
    from app.db.session import SessionLocal

    with SessionLocal() as db:
        source = s.locked_source(db, uuid.UUID(ticket["source_id"]))
        now = s.clock(db)
        try:
            s.check_ticket(db, source, ticket)
            source.owner_id = None
            source.lease_until = now
        except s.PipelineError:
            pass  # Expired/replaced/revoked owners cannot release current leases.
        row = db.scalar(
            select(PipelineOperation)
            .where(PipelineOperation.id == operation_ticket["id"])
            .with_for_update()
        )
        if (
            row
            and row.fence == operation_ticket["fence"]
            and str(row.owner_id) == ticket["owner_id"]
            and row.state == "RUNNING"
            and row.lease_until
            and row.lease_until > now
        ):
            row.state = "UNRECOVERABLE"
            row.result = {
                **row.result,
                "error_code": getattr(
                    error, "code", "CONTINUITY_OR_AUTHORITY_UNPROVEN"
                ),
                "new_evidence_required": True,
                "live_checkpoint_unchanged": True,
            }
            row.lease_until = now
            s.event(db, row, "PENTAHO_RECONCILIATION_FAILED", row.actor_id)
        db.commit()
