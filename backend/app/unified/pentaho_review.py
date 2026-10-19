"""Claim-scoped evidence review; no alias reassignment or workload controls.

The canonical JobOrder lock serializes reduction and review. Decisions append
before/after projections; accepted claims must still have native authority.
"""

import uuid
from sqlalchemy import select, or_
from fastapi import HTTPException
from app.models import JobOrder, JobOrderHistory, OperationalIncident
from app.unified.models import NormalizedEvent
from app.unified.pentaho_models import (
    PentahoEvidenceReview as Review,
    PentahoEvidenceDecision as Decision,
    PentahoAttempt,
    PentahoRevision,
    PentahoAlias,
)
from app.unified.pentaho_execution import digest, identity_claim, TERMINAL
from app.security.access_control import require_permission
from app.security.audit import log_event
from app.security.scope import current_principal
from app.worker.pentaho_status import safe_text


def category(error):
    if "LEGACY" in error:
        return "LEGACY_ADOPTION"
    if "RECOVERY" in error:
        return "RECOVERY_IDENTITY"
    if any(s in error for s in ("RETRY", "PREDECESSOR", "ATTEMPT_ORDER")):
        return "RETRY_RELATIONSHIP"
    if "CONFLICT_PENDING" in error:
        return "EXECUTION_OUTCOME"
    if any(
        s in error for s in ("ALIAS", "IDENTITY_CONFLICT", "OBSERVATION_ID_CONFLICT")
    ):
        return "NATIVE_ALIAS_CONFLICT"
    return "AMBIGUOUS_IDENTITY"


def snapshot(history):
    if not history:
        return {}
    return {
        "legacy_status": history.status.value,
        **{
            key: (
                getattr(history, key).isoformat()
                if hasattr(getattr(history, key), "isoformat")
                else getattr(history, key)
            )
            for key in (
                "pentaho_lifecycle",
                "pentaho_outcome",
                "pentaho_completeness",
                "pentaho_identity_state",
                "pentaho_review_state",
                "started_at",
                "ended_at",
            )
        },
    }


def open_review(db, resource, event, error, history=None):
    """Idempotent under the existing canonical JobOrder lock."""
    db.flush()  # Source/session uses autoflush=False; include the disputed revision.
    kind = category(error)
    row = db.scalar(
        select(Review).where(Review.event_id == event.id, Review.category == kind)
    )
    if row:
        return row
    verification = event.payload.get("pentaho_verification") or {}
    affected = {history.id} if history else set()
    try:
        claim = identity_claim(event.payload, resource)
        keys = [claim["invocation"], claim["logical"], claim["scheduler_alias"]]
        affected.update(
            db.scalars(
                select(PentahoAlias.history_id).where(
                    PentahoAlias.organization_id == resource.organization_id,
                    PentahoAlias.resource_id == resource.id,
                    PentahoAlias.alias_key.in_([k for k in keys if k]),
                )
            )
        )
    except (ValueError, TypeError, KeyError):
        pass  # No identity is guessed for an unverified observation.
    anchor = None
    if history:
        authority = (
            "SCHEDULER_RETRY"
            if kind == "RETRY_RELATIONSHIP"
            else "EXECUTION_OUTCOME" if kind == "EXECUTION_OUTCOME" else "INVOCATION"
        )
        prior = select(PentahoRevision.id).where(
            PentahoRevision.history_id == history.id,
            PentahoRevision.event_id != event.id,
            PentahoRevision.disposition == "ACCEPTED",
            PentahoRevision.payload["verification"]["claims"].contains([authority]),
        )
        if kind == "EXECUTION_OUTCOME":
            prior = prior.where(
                PentahoRevision.payload["identity"]["completion_evidence"]
                .as_boolean()
                .is_(True)
            )
        anchor = db.scalar(
            prior.order_by(
                PentahoRevision.created_at.desc(), PentahoRevision.revision.desc()
            ).limit(1)
        )
    row = Review(
        organization_id=resource.organization_id,
        resource_id=resource.id,
        job_order_id=resource.job_order_id,
        history_id=history.id if history else None,
        event_id=event.id,
        source_evidence_id=(
            uuid.UUID(verification["evidence_id"])
            if verification.get("evidence_id")
            else None
        ),
        category=kind,
        claim="EXECUTION_OUTCOME" if kind == "EXECUTION_OUTCOME" else "IDENTITY",
        status="OPEN",
        revision=1,
        context={
            "error": error,
            "affected_history_ids": sorted(str(v) for v in affected),
            "candidate_event_id": str(event.id),
            "identity": event.payload.get("pentaho_identity"),
            "verification": verification,
            "projection_at_conflict": snapshot(history),
            "occurred_at": event.payload.get("timestamp"),
            "observed_at": event.observed_at.isoformat(),
            "received_at": event.received_at.isoformat(),
            "incident_associations": (
                [
                    str(v)
                    for v in db.scalars(
                        select(OperationalIncident.id).where(
                            OperationalIncident.organization_id
                            == resource.organization_id,
                            OperationalIncident.history_id == history.id,
                        )
                    )
                ]
                if history
                else []
            ),
            "applicable_prior_revision_id": str(anchor) if anchor else None,
            "prior_revision_ids": (
                [
                    str(v)
                    for v in db.scalars(
                        select(PentahoRevision.id)
                        .where(PentahoRevision.history_id == history.id)
                        .order_by(PentahoRevision.created_at.desc())
                        .limit(100)
                    )
                ]
                if history
                else []
            ),
            "incident_action": "NONE",
            "notification_eligibility": "NOT_EVALUATED_SPRINT05",
        },
    )
    db.add(row)
    for affected_id in affected:
        target = db.get(JobOrderHistory, affected_id)
        if kind != "EXECUTION_OUTCOME":
            target.pentaho_identity_state = "REVIEW_REQUIRED"
        target.pentaho_review_state = (
            "CONFLICTED_EVIDENCE" if kind == "EXECUTION_OUTCOME" else "REVIEW_REQUIRED"
        )
    db.flush()
    log_event(
        db,
        event_type="PENTAHO_EVIDENCE_REVIEW_OPENED",
        outcome="SUCCESS",
        actor_id=current_principal.get().user_id if current_principal.get() else None,
        organization_id=resource.organization_id,
        target_type="pentaho_evidence_review",
        target_id=row.id,
    )
    return row


def synchronize_reviews(db, resource, limit=100):
    """Bounded queue backfill for pre-S04 quarantine, never replays evidence."""
    db.scalar(
        select(JobOrder).where(JobOrder.id == resource.job_order_id).with_for_update()
    )
    events = list(
        db.scalars(
            select(NormalizedEvent)
            .where(
                NormalizedEvent.organization_id == resource.organization_id,
                NormalizedEvent.resource_id == resource.id,
                NormalizedEvent.processing_status == "UNRESOLVED",
                NormalizedEvent.payload.has_key("pentaho_identity"),
                ~select(Review.id)
                .where(Review.event_id == NormalizedEvent.id)
                .exists(),
            )
            .order_by(NormalizedEvent.received_at, NormalizedEvent.id)
            .limit(limit)
        )
    )
    for event in events:
        history = (
            db.get(JobOrderHistory, event.history_id) if event.history_id else None
        )
        open_review(
            db,
            resource,
            event,
            event.processing_error or "PENTAHO_IDENTITY_AMBIGUOUS",
            history,
        )
    return len(events)


def unqueued_identity_evidence(db, history):
    # A bounded migration/backfill must not temporarily clear old quarantine.
    return (
        db.scalar(
            select(NormalizedEvent.id)
            .where(
                NormalizedEvent.history_id == history.id,
                NormalizedEvent.processing_status == "UNRESOLVED",
                ~select(Review.id)
                .where(Review.event_id == NormalizedEvent.id)
                .exists(),
            )
            .limit(1)
        )
        is not None
    )


def refresh_review_state(db, history):
    rows = list(
        db.scalars(
            select(Review).where(
                or_(
                    Review.history_id == history.id,
                    Review.context["affected_history_ids"].contains([str(history.id)]),
                ),
                Review.status == "OPEN",
            )
        )
    )
    identity = any(
        r.category != "EXECUTION_OUTCOME" for r in rows
    ) or unqueued_identity_evidence(db, history)
    history.pentaho_identity_state = "REVIEW_REQUIRED" if identity else "CONFIRMED"
    history.pentaho_review_state = (
        "CONFLICTED_EVIDENCE"
        if any(r.category == "EXECUTION_OUTCOME" for r in rows)
        else ("REVIEW_REQUIRED" if identity else "CLEAR")
    )


def verified_candidate(db, resource, event):
    from app.data_pipelines.models import PipelineEvidence

    try:
        claim = identity_claim(event.payload, resource)
        stamp = event.payload.get("pentaho_verification") or {}
        raw = db.get(PipelineEvidence, uuid.UUID(stamp["evidence_id"]))
        valid = (
            raw is not None
            and raw.organization_id == resource.organization_id
            and str(raw.source_id) == stamp.get("source_id")
            and str(raw.generation) == stamp.get("generation")
            and digest(raw.payload) == stamp.get("evidence_sha256")
            and type(stamp.get("fence")) is int
            and stamp["fence"] > 0
            and bool(stamp.get("attestations"))
            and all(
                a.get("platform_version")
                and a.get("verification_evidence_id")
                and a.get("reader_definition_hash")
                and a.get("connection_id")
                and set(claim["claims"]) <= set(a.get("claims", []))
                for a in stamp["attestations"]
            )
        )
    except (ValueError, TypeError, KeyError):
        valid = False
    if not valid:
        raise HTTPException(
            409,
            "Durable native authority/build/source/fence/integrity snapshot is required; new verified evidence is needed",
        )
    return claim


def decide(
    db, resource, review_id, actor_id, action, expected_revision, request_key, reason
):
    principal = require_permission("etl.resolve_identity", resource.organization_id)
    if principal.user_id != actor_id:
        raise HTTPException(403, "Review actor must be the authenticated operator")
    # Same lock as worker reduction. Acquire before reading mutable review state.
    db.scalar(
        select(JobOrder).where(JobOrder.id == resource.job_order_id).with_for_update()
    )
    row = db.scalar(
        select(Review)
        .where(
            Review.id == review_id,
            Review.resource_id == resource.id,
            Review.organization_id == resource.organization_id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if not row:
        raise HTTPException(404, "Evidence review unavailable")
    clean_reason = safe_text(reason)[:2000]
    if len(clean_reason.strip()) < 10:
        raise HTTPException(422, "A substantive non-secret review reason is required")
    signature = digest(
        [str(review_id), str(actor_id), action, expected_revision, clean_reason]
    )
    prior = db.scalar(
        select(Decision).where(
            Decision.organization_id == resource.organization_id,
            Decision.request_key == request_key,
        )
    )
    if prior:
        if prior.request_hash != signature or prior.review_id != row.id:
            raise HTTPException(409, "Evidence decision idempotency key conflicts")
        return row
    if row.revision != expected_revision or row.status != "OPEN":
        raise HTTPException(409, "Review changed; refresh before deciding")
    event = db.get(NormalizedEvent, row.event_id)
    history = (
        db.get(JobOrderHistory, row.history_id, populate_existing=True)
        if row.history_id
        else None
    )
    before = snapshot(history)
    if action == "DEFER":
        pass
    elif action == "REJECT_CLAIM":
        row.status = "REJECTED"
        event.processing_status = "REVIEWED"
        event.processing_error = "PENTAHO_CLAIM_REJECTED_BY_REVIEW"
    elif action == "ACCEPT_VERIFIED_CLAIM":
        if row.category != "EXECUTION_OUTCOME" or not history:
            raise HTTPException(
                409,
                "Only verified outcome conflicts allow projection correction; immutable aliases cannot be reassigned",
            )
        other = db.scalar(
            select(Review.id)
            .where(
                or_(
                    Review.history_id == history.id,
                    Review.context["affected_history_ids"].contains([str(history.id)]),
                ),
                Review.status == "OPEN",
                Review.category != "EXECUTION_OUTCOME",
            )
            .limit(1)
        )
        if (
            other
            or history.pentaho_identity_state != "CONFIRMED"
            or unqueued_identity_evidence(db, history)
        ):
            raise HTTPException(
                409, "Unresolved native identity blocks outcome correction"
            )
        claim = verified_candidate(db, resource, event)
        native = claim["native"]
        if (
            "EXECUTION_OUTCOME" not in claim["claims"]
            or native.get("completion_evidence") is not True
            or native.get("native_outcome") not in TERMINAL
        ):
            raise HTTPException(409, "Verified native completion evidence required")
        revision = db.scalar(
            select(PentahoRevision).where(
                PentahoRevision.event_id == event.id,
                PentahoRevision.history_id == history.id,
            )
        )
        if not revision:
            raise HTTPException(409, "A durable scoped attempt revision is required")
        attempt = db.get(PentahoAttempt, revision.attempt_id, populate_existing=True)
        if attempt.attempt_key != claim["invocation"]:
            raise HTTPException(409, "Native invocation mismatch")
        # Equal-authority native outcomes may be corrected explicitly. This does
        # not resolve retry authority contradictions or change immutable IDs.
        from app.unified.pentaho_execution import apply_native_outcome, project_history

        apply_native_outcome(attempt, native)
        project_history(db, history, allow_correction=True)
        row.status = "ACCEPTED"
        event.processing_status = "REVIEWED"
        event.processing_error = "PENTAHO_VERIFIED_OUTCOME_REVIEWED"
    elif action == "ADOPT_LEGACY":
        if (
            row.category != "LEGACY_ADOPTION"
            or not history
            or history.pentaho_resource_id
        ):
            raise HTTPException(409, "A unique unbound legacy invocation is required")
        claim = verified_candidate(db, resource, event)
        if history.provider_execution_id not in {claim["logical"], claim["invocation"]}:
            raise HTTPException(
                409, "Verified native alias must match legacy identity exactly"
            )
        native = claim["native"]
        if (
            "EXECUTION_OUTCOME" not in claim["claims"]
            or native.get("completion_evidence") is not True
        ):
            raise HTTPException(
                409, "Legacy terminal adoption requires verified native completion"
            )
        if history.status.value != native.get("native_outcome"):
            raise HTTPException(
                409, "Contradictory legacy terminal evidence cannot be silently adopted"
            )
        if (
            native.get("native_outcome") == "FAILED"
            and claim["scheduler"].get("retry_state") != "EXHAUSTED"
        ):
            raise HTTPException(
                409,
                "Legacy failure requires verified finality, not assumed retry exhaustion",
            )
        # Reducer still checks every alias, retry predecessor and immutable key.
        row.status = "ACCEPTED"
        db.flush()
        event.processing_status = "PENDING"
        from app.unified.pentaho_execution import reduce_events

        job = db.get(JobOrder, resource.job_order_id)
        reduce_events(db, resource, [event], job=job)
        if event.processing_status != "PROCESSED":
            raise HTTPException(
                409, "Legacy adoption remains unsafe; no identity was changed"
            )
    else:
        raise HTTPException(422, "Unsupported evidence review decision")
    if history and action in {"ACCEPT_VERIFIED_CLAIM", "ADOPT_LEGACY"}:
        # Sprint 05 will evaluate historical notification/reassessment eligibility.
        # An adjudicated correction must never silently resurrect a closed case.
        history.source_evidence = {
            **(history.source_evidence or {}),
            "pentaho_adjudication": {
                "review_id": str(row.id),
                "decision_revision": row.revision + 1,
                "operational_reassessment_required": True,
                "occurred_at": event.payload.get("timestamp"),
                "discovered_at": event.received_at.isoformat(),
                "notification_eligibility": "NOT_EVALUATED_SPRINT05",
            },
        }
    row.revision += 1
    db.flush()
    for affected_id in row.context.get("affected_history_ids", []):
        target = db.get(JobOrderHistory, uuid.UUID(affected_id))
        if target and target.pentaho_resource_id == resource.id:
            refresh_review_state(db, target)
    db.add(
        Decision(
            organization_id=resource.organization_id,
            resource_id=resource.id,
            review_id=row.id,
            revision=row.revision,
            actor_id=actor_id,
            action=action,
            reason=clean_reason,
            request_key=request_key,
            request_hash=signature,
            evidence={
                "event_id": str(event.id),
                "source_evidence_id": (
                    str(row.source_evidence_id) if row.source_evidence_id else None
                ),
                "payload_sha256": digest(event.payload),
                "review_context": row.context,
            },
            projection_before=before,
            projection_after=snapshot(history),
        )
    )
    log_event(
        db,
        event_type="PENTAHO_EVIDENCE_" + action,
        outcome="SUCCESS",
        actor_id=actor_id,
        organization_id=resource.organization_id,
        target_type="pentaho_evidence_review",
        target_id=row.id,
    )
    db.flush()
    return row


def flag_recovery_identity(db, resource, event_id, actor_id, request_key, reason):
    """Operator reports an observed relationship identity issue, never a link."""
    principal = require_permission("etl.resolve_identity", resource.organization_id)
    if principal.user_id != actor_id:
        raise HTTPException(403, "Authenticated review actor required")
    db.scalar(
        select(JobOrder).where(JobOrder.id == resource.job_order_id).with_for_update()
    )
    event = db.scalar(
        select(NormalizedEvent).where(
            NormalizedEvent.id == event_id,
            NormalizedEvent.resource_id == resource.id,
            NormalizedEvent.organization_id == resource.organization_id,
        )
    )
    if not event or not event.payload.get("pentaho_identity") or not event.history_id:
        raise HTTPException(404, "Scoped Pentaho relationship evidence unavailable")
    existing = db.scalar(
        select(Review).where(
            Review.event_id == event.id, Review.category == "RECOVERY_IDENTITY"
        )
    )
    if existing:
        prior = db.scalar(
            select(Decision.id).where(
                Decision.review_id == existing.id, Decision.request_key == request_key
            )
        )
        if not prior:
            raise HTTPException(409, "Relationship identity review already exists")
        return decide(
            db, resource, existing.id, actor_id, "DEFER", 1, request_key, reason
        )
    history = db.get(JobOrderHistory, event.history_id)
    if not history or history.pentaho_resource_id != resource.id:
        raise HTTPException(409, "Verified execution binding is required")
    event.processing_status = "UNRESOLVED"
    event.processing_error = "PENTAHO_RECOVERY_IDENTITY"
    row = open_review(db, resource, event, "PENTAHO_RECOVERY_IDENTITY", history)
    return decide(db, resource, row.id, actor_id, "DEFER", 1, request_key, reason)
