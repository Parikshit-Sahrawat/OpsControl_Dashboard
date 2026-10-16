"""Observed recovery relationships; never invokes or repairs an ETL workload."""

from sqlalchemy import select
from fastapi import HTTPException
from app.models import JobOrderHistory
from app.unified.models import MonitoringResource, NormalizedEvent
from app.unified.pentaho_models import (
    PentahoRecoveryLink,
    PentahoRecoveryDecision,
    PentahoRevision,
)
from app.security.access_control import require_permission
from app.security.audit import log_event
from app.unified.pentaho_execution import digest
from app.worker.pentaho_status import safe_text


def history(db, resource, history_id, permission="etl.view"):
    require_permission(permission, resource.organization_id)
    row = db.scalar(
        select(JobOrderHistory).where(
            JobOrderHistory.id == history_id,
            JobOrderHistory.job_order_id == resource.job_order_id,
            JobOrderHistory.pentaho_customer_id == resource.organization_id,
            JobOrderHistory.pentaho_resource_id == resource.id,
        )
    )
    if not row:
        raise HTTPException(404, "Pentaho execution unavailable")
    return row


def pair(db, failed, recovery_id, allow_unresolved=False):
    # Parent resources then histories are locked in UUID order, as in reduction.
    candidate = db.get(JobOrderHistory, recovery_id)
    if not candidate or candidate.pentaho_customer_id != failed.pentaho_customer_id:
        raise HTTPException(404, "Recovery execution unavailable")
    ids = {failed.pentaho_resource_id, candidate.pentaho_resource_id}
    for resource in db.scalars(
        select(MonitoringResource)
        .where(MonitoringResource.id.in_(ids))
        .order_by(MonitoringResource.id)
        .with_for_update()
    ):
        require_permission("etl.investigate", resource.organization_id)
    locked = {
        r.id: r
        for r in db.scalars(
            select(JobOrderHistory)
            .where(JobOrderHistory.id.in_([failed.id, recovery_id]))
            .order_by(JobOrderHistory.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    }
    failed, recovery = locked[failed.id], locked[recovery_id]
    if (
        failed.id == recovery.id
        or failed.pentaho_outcome != "FAILED"
        or failed.pentaho_lifecycle != "TERMINAL"
    ):
        raise HTTPException(409, "A separate confirmed failed execution is required")
    for run in () if allow_unresolved else (failed, recovery):
        pending = db.scalar(
            select(NormalizedEvent.id)
            .where(
                NormalizedEvent.history_id == run.id,
                NormalizedEvent.processing_status == "UNRESOLVED",
            )
            .limit(1)
        )
        if run.pentaho_identity_state != "CONFIRMED" or pending:
            raise HTTPException(
                409,
                "Unresolved native identity cannot be overridden by recovery linking",
            )
    return failed, recovery


def supporting_evidence(db, failed, recovery, ids):
    rows = list(
        db.scalars(
            select(NormalizedEvent)
            .join(PentahoRevision, PentahoRevision.event_id == NormalizedEvent.id)
            .where(
                NormalizedEvent.id.in_(ids),
                NormalizedEvent.organization_id == failed.pentaho_customer_id,
                NormalizedEvent.history_id.in_([failed.id, recovery.id]),
                NormalizedEvent.processing_status == "PROCESSED",
                PentahoRevision.disposition == "ACCEPTED",
            )
        )
    )
    if len({r.id for r in rows}) != len(set(ids)) or {r.history_id for r in rows} != {
        failed.id,
        recovery.id,
    }:
        raise HTTPException(
            409, "Verified identity evidence for both executions is required"
        )
    return [
        {
            "event_id": str(r.id),
            "history_id": str(r.history_id),
            "payload_sha256": digest(r.payload),
        }
        for r in sorted(rows, key=lambda r: str(r.id))
    ]


def decision(
    db, link, action, actor_id, request_key, reason, evidence, expected_revision=None
):
    clean_reason = safe_text(reason)[:2000]
    signature = digest(
        [
            str(link.failed_history_id),
            str(link.recovery_history_id),
            action,
            str(actor_id),
            clean_reason,
            evidence,
            expected_revision,
        ]
    )
    prior = db.scalar(
        select(PentahoRecoveryDecision).where(
            PentahoRecoveryDecision.organization_id == link.organization_id,
            PentahoRecoveryDecision.request_key == request_key,
        )
    )
    if prior:
        if prior.link_id != link.id or prior.request_hash != signature:
            raise HTTPException(409, "Recovery request idempotency key conflicts")
        return link
    if expected_revision is not None and link.revision != expected_revision:
        raise HTTPException(409, "Recovery relationship changed; refresh before saving")
    if action == "CONFIRM":
        if link.status != "PROPOSED" or link.proposed_by == actor_id:
            raise HTTPException(
                409,
                "An independent authorized operator must confirm the proposed association",
            )
        link.status = "CONFIRMED"
    elif action == "REVERSE":
        if link.status != "CONFIRMED":
            raise HTTPException(409, "Only a confirmed association can be reversed")
        link.status = "REVERSED"
    elif action == "PROPOSE":
        if link.status != "PROPOSED":
            raise HTTPException(409, "Relationship already decided")
    else:
        raise HTTPException(422, "Unsupported monitoring relationship decision")
    if action != "PROPOSE":
        link.revision += 1
    db.add(
        PentahoRecoveryDecision(
            organization_id=link.organization_id,
            link_id=link.id,
            revision=link.revision,
            action=action,
            actor_id=actor_id,
            request_key=request_key,
            request_hash=signature,
            reason=clean_reason,
            evidence=evidence,
        )
    )
    log_event(
        db,
        event_type="PENTAHO_RECOVERY_" + action,
        outcome="SUCCESS",
        actor_id=actor_id,
        organization_id=link.organization_id,
        target_type="pentaho_recovery_link",
        target_id=link.id,
    )
    db.flush()
    return link


def propose(db, failed, recovery_id, actor_id, request_key, reason, ids):
    failed, recovery = pair(db, failed, recovery_id)
    support = supporting_evidence(db, failed, recovery, ids)
    link = db.scalar(
        select(PentahoRecoveryLink)
        .where(
            PentahoRecoveryLink.failed_history_id == failed.id,
            PentahoRecoveryLink.recovery_history_id == recovery.id,
        )
        .with_for_update()
    )
    if not link:
        # A monitored recovery relation must not introduce a relationship cycle.
        paths = (
            select(PentahoRecoveryLink.recovery_history_id.label("id"))
            .where(
                PentahoRecoveryLink.failed_history_id == recovery.id,
                PentahoRecoveryLink.status != "REVERSED",
            )
            .cte("recoveries", recursive=True)
        )
        paths = paths.union(
            select(PentahoRecoveryLink.recovery_history_id)
            .join(paths, PentahoRecoveryLink.failed_history_id == paths.c.id)
            .where(PentahoRecoveryLink.status != "REVERSED")
        )
        if db.scalar(select(paths.c.id).where(paths.c.id == failed.id).limit(1)):
            raise HTTPException(409, "Cyclic recovery associations are not supported")
        link = PentahoRecoveryLink(
            organization_id=failed.pentaho_customer_id,
            failed_history_id=failed.id,
            recovery_history_id=recovery.id,
            proposed_by=actor_id,
            status="PROPOSED",
            revision=1,
        )
        db.add(link)
        db.flush()
    return decision(db, link, "PROPOSE", actor_id, request_key, reason, support)


def review(
    db, failed, link_id, actor_id, request_key, reason, action, expected_revision
):
    row = db.get(PentahoRecoveryLink, link_id)
    if (
        not row
        or row.organization_id != failed.pentaho_customer_id
        or row.failed_history_id != failed.id
    ):
        raise HTTPException(404, "Recovery relationship unavailable")
    failed, recovery = pair(
        db, failed, row.recovery_history_id, allow_unresolved=action == "REVERSE"
    )
    row = db.scalar(
        select(PentahoRecoveryLink)
        .where(PentahoRecoveryLink.id == row.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    proposal = db.scalar(
        select(PentahoRecoveryDecision).where(
            PentahoRecoveryDecision.link_id == row.id,
            PentahoRecoveryDecision.action == "PROPOSE",
        )
    )
    # Confirmation rechecks identities and supporting evidence; reversal never
    # erases evidence and must remain possible if subsequent identity issues arise.
    if action == "CONFIRM":
        supporting_evidence(
            db,
            failed,
            recovery,
            [__import__("uuid").UUID(e["event_id"]) for e in proposal.evidence],
        )
    return decision(
        db,
        row,
        action,
        actor_id,
        request_key,
        reason,
        proposal.evidence,
        expected_revision,
    )
