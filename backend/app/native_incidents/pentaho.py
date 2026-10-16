"""Evidence-based Pentaho extensions to the native incident engine, without IO."""

import re
import uuid
from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy import select, text, or_
from app.models import JobOrderHistory, OperationalIncident
from app.native_incidents.models import (
    NativeIncidentFailure as Failure,
    NativeRecoveryAssessment as Assessment,
)
from app.unified.models import (
    MonitoringResource,
    NormalizedEvent,
    ResourceDependency,
    ResourceCondition,
    ExpectedExecutionWindow,
)
from app.unified.pentaho_models import (
    PentahoRevision,
    PentahoRecoveryLink,
    PentahoEvidenceReview,
)
from app.unified.pentaho_execution import digest
from app.unified.pentaho_review import verified_candidate, unqueued_identity_evidence
from app.unified.pentaho_history import eligible
from app.security.access_control import require_permission


def cause_reference(value):
    """An exact native cause occurrence, never a name/host/time similarity key."""
    if not isinstance(value, dict) or set(value) != {
        "authority_id",
        "occurrence_id",
        "evidence_sha256",
    }:
        raise ValueError("Bound native cause authority, occurrence and proof required")
    if any(
        not isinstance(value[k], str)
        or not re.fullmatch(r"[A-Za-z0-9_.:/-]{1,200}", value[k])
        for k in ("authority_id", "occurrence_id")
    ):
        raise ValueError("Invalid native cause identity")
    if not isinstance(value["evidence_sha256"], str) or not re.fullmatch(
        r"[a-f0-9]{64}", value["evidence_sha256"]
    ):
        raise ValueError("Invalid native cause proof")
    return dict(value)


def root_key(resource, claim):
    if "FAILURE_CAUSE" not in claim["claims"] or not claim["native"].get(
        "failure_cause"
    ):
        return None
    cause = cause_reference(claim["native"]["failure_cause"])
    return digest([str(resource.organization_id), resource.environment, cause])


def correlate(db, resource, history, event, now):
    """Called under reducer resource/job locks; common-root lock serializes replicas.

    Existing history associations win over new evidence. Historical associations to
    resolved incidents are retained and audited without any operational transition.
    """
    from app.native_incidents import service

    if not eligible(db, resource, history, event):
        return None
    root = root_key(resource, verified_candidate(db, resource, event))
    key = "pentaho-incident:" + (root or str(history.id))
    # Nonblocking: workers holding different jobs must never deadlock on a root.
    if not db.scalar(
        text("SELECT pg_try_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": key},
    ):
        return None
    prior = db.scalar(select(Failure).where(Failure.event_id == event.id))
    if prior:
        return prior
    old = db.scalar(
        select(Failure)
        .where(Failure.history_id == history.id)
        .order_by(Failure.discovered_at, Failure.id)
        .limit(1)
    )
    historic = (history.source_evidence or {}).get("pentaho_historical") or {}
    incident = db.scalar(
        select(OperationalIncident)
        .where(
            OperationalIncident.organization_id == resource.organization_id,
            (
                OperationalIncident.id == old.incident_id
                if old
                else OperationalIncident.history_id == history.id
            ),
        )
        .order_by(OperationalIncident.opened_at, OperationalIncident.id)
        .limit(1)
        .with_for_update()
    )
    if not incident and root:
        query = (
            select(OperationalIncident)
            .join(Failure, Failure.incident_id == OperationalIncident.id)
            .where(
                Failure.organization_id == resource.organization_id,
                Failure.root_key == root,
            )
        )
        if not historic.get("operational_reassessment_required"):
            query = query.where(
                OperationalIncident.status.notin_(["RESOLVED", "CLOSED"])
            )
        incident = db.scalar(
            query.order_by(
                OperationalIncident.status.notin_(["RESOLVED", "CLOSED"]).desc(),
                OperationalIncident.opened_at.desc(),
                OperationalIncident.id,
            )
            .limit(1)
            .with_for_update(of=OperationalIncident)
        )
    if not incident:
        incident = OperationalIncident(
            id=uuid.uuid4(),
            organization_id=resource.organization_id,
            episode_key="pentaho-failure:" + str(history.id),
            source_kind="PENTAHO",
            source_reference=str(history.id),
            history_id=history.id,
            title="Verified Pentaho execution failure",
            severity="ERROR",
            status="OPEN",
            condition_status="ACTIVE",
            opened_at=history.ended_at,
        )
        db.add(incident)
        db.flush()
        service.record(db, incident, "CREATED", now=now)
    row = Failure(
        organization_id=resource.organization_id,
        incident_id=incident.id,
        resource_id=resource.id,
        history_id=history.id,
        event_id=event.id,
        root_key=root,
        occurred_at=history.ended_at,
        discovered_at=event.received_at,
        evidence={
            "event_id": str(event.id),
            "payload_sha256": digest(event.payload),
            "verification": event.payload["pentaho_verification"],
            "failure_cause": claim_cause(event),
            "correlation_rule": (
                "VERIFIED_NATIVE_CAUSE" if root else "DISTINCT_EXECUTION"
            ),
        },
        reassessment=(
            {
                **historic,
                "action": "PRESERVE_ASSOCIATION_NO_REOPEN",
                "incident_status": incident.status,
            }
            if historic
            else {}
        ),
    )
    db.add(row)
    service.details(db, incident).revision += 1
    service.details(db, incident).verified_at = None
    service.record(
        db, incident, "HISTORICAL_REASSESSED" if historic else "FAILURE_LINKED", now=now
    )
    db.flush()
    return row


def claim_cause(event):
    return event.payload["pentaho_identity"].get("failure_cause")


def unresolved(db, history):
    return (
        history.pentaho_identity_state != "CONFIRMED"
        or history.pentaho_review_state not in {None, "CLEAR"}
        or unqueued_identity_evidence(db, history)
        or bool(
            db.scalar(
                select(PentahoEvidenceReview.id)
                .where(
                    PentahoEvidenceReview.history_id == history.id,
                    PentahoEvidenceReview.status == "OPEN",
                )
                .limit(1)
            )
        )
    )


def successful_evidence(db, history, now, max_age=120):
    if (
        unresolved(db, history)
        or history.pentaho_lifecycle != "TERMINAL"
        or history.pentaho_outcome not in {"SUCCESS", "SUCCESS_AFTER_RETRY"}
        or history.pentaho_completeness != "COMPLETE"
        or not history.ended_at
        or not 0 <= (now - history.ended_at).total_seconds() <= max_age
    ):
        return None
    resource = db.get(MonitoringResource, history.pentaho_resource_id)
    for revision in db.scalars(
        select(PentahoRevision)
        .where(
            PentahoRevision.history_id == history.id,
            PentahoRevision.disposition == "ACCEPTED",
        )
        .order_by(PentahoRevision.created_at.desc())
        .limit(200)
    ):
        event = db.get(NormalizedEvent, revision.event_id)
        if event.processing_status != "PROCESSED":
            continue
        try:
            claim = verified_candidate(db, resource, event)
        except HTTPException:
            continue
        if (
            "EXECUTION_OUTCOME" in claim["claims"]
            and claim["native"].get("completion_evidence") is True
            and claim["native"].get("native_outcome") == "SUCCESS"
        ):
            return {
                "history_id": str(history.id),
                "event_id": str(event.id),
                "payload_sha256": digest(event.payload),
            }
    return None


def health(db, resource, now):
    from app.unified.engines import source_readiness
    from app.unified.pentaho_schedule import bindings
    from app.data_pipelines import service as pipelines
    from app.data_pipelines.models import PipelineSource, PipelineOperation

    if not resource or not resource.active:
        return False
    if resource.configuration.get("platform") != "PENTAHO":
        return bool(source_readiness(db, resource, now)["ready"])
    methods = bindings(db, resource)
    if not methods:
        return False
    for method in methods:
        source = db.get(PipelineSource, method.source_id)
        receipt = db.scalar(
            select(PipelineOperation)
            .where(
                PipelineOperation.source_id == source.id,
                PipelineOperation.kind == "ACCEPTANCE",
                PipelineOperation.configuration["generation"].astext
                == str(source.generation),
            )
            .order_by(PipelineOperation.created_at.desc())
            .limit(1)
        )
        if (
            not pipelines.eligible(db, method)
            or pipelines.suspended(db, source)
            or not source.continuity_validated
            or source.health not in {"RECEIVING", "IDLE"}
            or not source.last_observed_at
            or not 0 <= (now - source.last_observed_at).total_seconds() <= 120
            or not receipt
            or receipt.result.get("complete") is not True
        ):
            return False
        try:
            if (
                not 0
                <= (
                    now - datetime.fromisoformat(receipt.result["accepted_at"])
                ).total_seconds()
                <= 120
            ):
                return False
        except (ValueError, KeyError, TypeError):
            return False
    return True


def recovery(db, incident, now, seconds=None):
    """Read-only evaluation. Stable windows require persisted periodic assessments."""
    from app.native_incidents import service
    from app.unified.engines import active_parameters

    rows = list(
        db.scalars(
            select(Failure)
            .where(Failure.incident_id == incident.id)
            .order_by(Failure.id)
        )
    )
    if not rows:
        return None
    d = service.details(db, incident)
    seconds = seconds or d.monitoring_seconds
    missing, failed, pending = [], [], []
    candidates, dependencies, schedules, policies = [], [], [], []
    histories = {r.history_id: r for r in rows}
    monitored = set(r.resource_id for r in rows)
    for history_id, failure in histories.items():
        history = db.get(JobOrderHistory, history_id)
        if unresolved(db, history) or history.pentaho_outcome != "FAILED":
            failed.append("Original failure has unresolved or revised evidence")
        links = list(
            db.scalars(
                select(PentahoRecoveryLink).where(
                    PentahoRecoveryLink.failed_history_id == history_id,
                    PentahoRecoveryLink.status == "CONFIRMED",
                )
            )
        )
        candidate = None
        for link in links:
            run = db.get(JobOrderHistory, link.recovery_history_id)
            if unresolved(db, run):
                failed.append("Recovery execution has unresolved conflicting evidence")
            candidate = successful_evidence(db, run, now, seconds + 120)
            if candidate:
                candidate.update(
                    link_id=str(link.id),
                    link_revision=link.revision,
                    failed_history_id=str(history_id),
                )
                monitored.add(run.pentaho_resource_id)
                break
        if candidate:
            candidates.append(candidate)
        else:
            missing.append(
                "Fresh verified successful execution and confirmed recovery relationship required"
            )
    for resource_id in sorted(monitored, key=str):
        resource = db.get(MonitoringResource, resource_id)
        if not health(db, resource, now):
            failed.append("Source/monitoring health unavailable: " + str(resource_id))
        for dep in db.scalars(
            select(ResourceDependency).where(
                ResourceDependency.organization_id == incident.organization_id,
                or_(
                    ResourceDependency.resource_id == resource_id,
                    ResourceDependency.depends_on_id == resource_id,
                ),
                ResourceDependency.valid_to.is_(None),
            )
        ):
            target_id = (
                dep.depends_on_id if dep.resource_id == resource_id else dep.resource_id
            )
            target = db.get(MonitoringResource, target_id)
            conditions = list(
                db.scalars(
                    select(ResourceCondition).where(
                        ResourceCondition.resource_id == target_id
                    )
                )
            )
            # An available telemetry path alone does not prove dependency health.
            dependency_proof = bool(conditions) and all(
                c.evidence
                and c.resolved_at
                and 0 <= (now - c.last_observed_at).total_seconds() <= 120
                for c in conditions
            )
            dependency_execution = None
            if target and target.domain == "ETL":
                last_run = db.scalar(
                    select(JobOrderHistory)
                    .where(JobOrderHistory.pentaho_resource_id == target_id)
                    .order_by(JobOrderHistory.ended_at.desc().nullslast())
                    .limit(1)
                )
                dependency_execution = (
                    successful_evidence(db, last_run, now, seconds + 120)
                    if last_run
                    else None
                )
                dependency_proof = bool(dependency_execution)
            ready = (
                health(db, target, now)
                and dependency_proof
                and not any(
                    c.active
                    or (
                        d.monitoring_started_at
                        and c.resolved_at
                        and c.resolved_at > d.monitoring_started_at
                    )
                    for c in conditions
                )
            )
            dependencies.append(
                {
                    "dependency_id": str(dep.id),
                    "resource_id": str(target_id),
                    "ready": bool(ready),
                    "condition_ids": [str(c.id) for c in conditions],
                    "execution_evidence": dependency_execution,
                }
            )
            if not ready:
                failed.append(
                    "Required dependency unhealthy or unobservable: " + str(target_id)
                )
        from app.unified.pentaho_schedule import bindings
        from app.data_pipelines.models import PipelineSource

        policies.append(
            {
                "resource_id": str(resource_id),
                "revision": resource.revision,
                "sources": sorted(
                    (
                        str(m.source_id),
                        str(db.get(PipelineSource, m.source_id).generation),
                    )
                    for m in bindings(db, resource)
                ),
            }
        )
        parameters = active_parameters(db, resource)
        config = parameters.configuration if parameters else {}
        schedule = config.get("schedule") or {}
        if schedule.get("frequency") and schedule.get("frequency") != "MANUAL":
            window = db.scalar(
                select(ExpectedExecutionWindow)
                .where(
                    ExpectedExecutionWindow.resource_id == resource.id,
                    ExpectedExecutionWindow.deadline <= now,
                )
                .order_by(ExpectedExecutionWindow.scheduled_at.desc())
                .limit(1)
            )
            ready = bool(
                window
                and window.status == "OBSERVED"
                and window.pentaho_authority
                and window.parameter_version == parameters.version
                and window.evaluated_at
                and 0 <= (now - window.evaluated_at).total_seconds() <= 120
            )
            schedules.append(
                {
                    "resource_id": str(resource_id),
                    "window_id": str(window.id) if window else None,
                    "ready": ready,
                }
            )
            if not ready:
                failed.append(
                    "Schedule/freshness compliance not proven: " + str(resource_id)
                )
    latest = db.scalar(
        select(Assessment)
        .where(Assessment.incident_id == incident.id)
        .order_by(Assessment.assessed_at.desc(), Assessment.id)
        .limit(1)
    )
    signature = digest(
        [
            sorted(str(x) for x in histories),
            sorted((c["link_id"], c["link_revision"]) for c in candidates),
            sorted(
                (x["dependency_id"], x["resource_id"], x["ready"]) for x in dependencies
            ),
            schedules,
            policies,
            seconds,
            d.monitoring_started_at,
        ]
    )
    since = None
    if not failed and not missing and d.monitoring_started_at:
        if (
            latest
            and latest.evidence.get("signature") == signature
            and 0 <= (now - latest.assessed_at).total_seconds() <= 120
        ):
            since = latest.evidence.get("healthy_since")
        since = since or now.isoformat()
    if not d.monitoring_started_at:
        pending.append("Enter MONITORING to begin the observation period")
    elif not since or now < datetime.fromisoformat(since) + timedelta(seconds=seconds):
        pending.append(
            "Stable observation period incomplete; persist assessments at most 120 seconds apart"
        )
    result = assessment_result(failed, missing, pending, bool(candidates), bool(latest))
    return {
        "ready": result == "VALIDATED_RECOVERY",
        "result": result,
        "reasons": failed + missing + pending,
        "evidence": {
            "checked_at": now.isoformat(),
            "failure_ids": [str(r.id) for r in rows],
            "candidates": candidates,
            "dependencies": dependencies,
            "policies": policies,
            "schedules": schedules,
            "observation_seconds": seconds,
            "healthy_since": since,
            "signature": signature,
        },
    }


def assessment_result(failed, missing, pending, candidates, previous):
    if failed:
        return "VALIDATION_FAILED"
    if missing:
        return "VALIDATION_PENDING" if candidates else "INSUFFICIENT_EVIDENCE"
    if pending:
        return "VALIDATION_PENDING" if previous else "RECOVERY_CANDIDATE"
    return "VALIDATED_RECOVERY"


def assess(db, incident, revision, request_key, seconds=None, now=None):
    from app.native_incidents import service

    principal = require_permission("incidents.manage", incident.organization_id)
    if not db.scalar(
        text("SELECT pg_try_advisory_xact_lock(hashtextextended(:key, 0))"),
        {
            "key": "native-assessment:"
            + str(incident.organization_id)
            + ":"
            + request_key
        },
    ):
        raise HTTPException(409, "Assessment request is in progress; retry")
    signature = digest([str(incident.id), str(principal.user_id), revision, seconds])
    prior = db.scalar(
        select(Assessment).where(
            Assessment.organization_id == incident.organization_id,
            Assessment.request_key == request_key,
        )
    )
    if prior:
        if prior.request_hash != signature:
            raise HTTPException(409, "Assessment idempotency key conflicts")
        return prior
    d = service.details(db, incident)
    if revision != d.revision:
        raise HTTPException(409, "Incident changed; refresh before assessment")
    if seconds is not None and not 60 <= seconds <= 86400:
        raise HTTPException(422, "Observation period must be 60..86400 seconds")
    now = now or service.utc()
    proof = recovery(db, incident, now, seconds)
    if proof is None:
        raise HTTPException(409, "No verified Pentaho failures associated")
    if seconds is not None:
        d.monitoring_seconds = seconds
    d.revision += 1
    row = Assessment(
        organization_id=incident.organization_id,
        incident_id=incident.id,
        actor_id=principal.user_id,
        request_key=request_key,
        request_hash=signature,
        revision=d.revision,
        result=proof["result"],
        assessed_at=now,
        evidence={**proof["evidence"], "reasons": proof["reasons"]},
    )
    db.add(row)
    service.record(
        db,
        incident,
        "RECOVERY_ASSESSED",
        principal.username,
        proof["result"],
        now=now,
        actor_id=principal.user_id,
    )
    db.flush()
    return row


def correlate_history(db, resource, history, now):
    # Drain distinct evidence in bounded batches; existing rows never starve new ones.
    revisions = db.scalars(
        select(PentahoRevision)
        .where(
            PentahoRevision.history_id == history.id,
            PentahoRevision.payload["identity"]["native_outcome"].astext == "FAILED",
            ~select(Failure.id)
            .where(Failure.event_id == PentahoRevision.event_id)
            .exists(),
        )
        .order_by(PentahoRevision.created_at, PentahoRevision.id)
        .limit(200)
    )
    for revision in revisions:
        correlate(
            db, resource, history, db.get(NormalizedEvent, revision.event_id), now
        )


def lock_resources(db, incident_id):
    """Match reducer/recovery-link lock order before locking the incident itself."""
    from app.models import JobOrder

    ids = set(
        db.scalars(
            select(Failure.resource_id).where(Failure.incident_id == incident_id)
        )
    )
    recovery_ids = (
        select(PentahoRecoveryLink.recovery_history_id)
        .join(Failure, Failure.history_id == PentahoRecoveryLink.failed_history_id)
        .where(Failure.incident_id == incident_id)
    )
    ids.update(
        db.scalars(
            select(JobOrderHistory.pentaho_resource_id).where(
                JobOrderHistory.id.in_(recovery_ids)
            )
        )
    )
    ids.update(
        db.scalars(
            select(ResourceDependency.depends_on_id).where(
                ResourceDependency.resource_id.in_(ids),
                ResourceDependency.valid_to.is_(None),
            )
        )
    )
    ids.update(
        db.scalars(
            select(ResourceDependency.resource_id).where(
                ResourceDependency.depends_on_id.in_(ids),
                ResourceDependency.valid_to.is_(None),
            )
        )
    )
    resources = list(
        db.scalars(
            select(MonitoringResource)
            .where(MonitoringResource.id.in_(ids))
            .order_by(MonitoringResource.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    )
    list(
        db.scalars(
            select(JobOrder)
            .where(
                JobOrder.id.in_([r.job_order_id for r in resources if r.job_order_id])
            )
            .order_by(JobOrder.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    )
