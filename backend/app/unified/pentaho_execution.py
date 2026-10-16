"""Pentaho identity/attempt extension called by the existing execution reducer.

No job runner, schedule engine or incident state machine lives here. The source
acceptance transaction stamps authority; observations cannot self-certify it.
"""

import hashlib
import json
import re
import uuid
from sqlalchemy import select
from app.models import JobOrderHistory, ExecutionStatus, ExecutionType
from app.unified.pentaho_models import PentahoAlias, PentahoAttempt, PentahoRevision

CLAIMS = {"INVOCATION", "EXECUTION_OUTCOME", "SCHEDULER_RETRY", "SCHEDULE"}
TERMINAL = {"SUCCESS", "FAILED", "CANCELLED"}


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()
    ).hexdigest()


def verified_projection(db, source, payload, links, evidence_id):
    """Stamp current native authority after fence/eligibility validation only."""
    from app.data_pipelines import service as s
    from app.data_pipelines.models import (
        PipelineConnection,
        PipelineCapability,
        PipelineIntegration,
        PipelineEvidence,
    )

    result = dict(payload)
    identity = result.pop("pentaho_identity", None)
    result.pop("pentaho_verification", None)
    methods = {method.id: method for _, method in links}.values()
    permitted = set(CLAIMS)
    has_context = False
    attestations = []
    for method in methods:
        integration = db.get(PipelineIntegration, method.integration_id)
        connection = db.get(PipelineConnection, method.connection_id)
        cfg = {
            **connection.configuration,
            **method.configuration.get("adapter_overrides", {}),
        }
        if integration.platform != "PENTAHO" or not cfg.get("monitoring_context"):
            permitted.clear()
            continue
        has_context = True
        profile = db.get(PipelineCapability, method.capability_id)
        declared = (
            profile.definition.get("verified_pentaho_claims", []) if profile else []
        )
        permitted &= set(declared) & CLAIMS if isinstance(declared, list) else set()
        eligible = source.lease_mode == "LIVE" and s.eligible(db, method)
        if not eligible:
            permitted.clear()
        if eligible and profile:
            attestations.append(
                {
                    "method_id": str(method.id),
                    "connection_id": str(connection.id),
                    "capability_id": str(profile.id),
                    "platform_version": profile.platform_version,
                    "verification_evidence_id": str(profile.verification_evidence_id),
                    "reader_definition_hash": s.reader_definition(db, method),
                    "claims": sorted(set(declared) & CLAIMS),
                }
            )
    if has_context and isinstance(identity, dict):
        result["pentaho_identity"] = identity
        result["pentaho_verification"] = {
            "claims": sorted(permitted),
            "evidence_id": str(evidence_id),
            "source_id": str(source.id),
            "generation": str(source.generation),
            "fence": source.fence,
            "evidence_sha256": digest(db.get(PipelineEvidence, evidence_id).payload),
            "accepted_at": db.get(PipelineEvidence, evidence_id).created_at.isoformat(),
            "attestations": attestations,
        }
    return result


def identity_claim(payload, resource):
    """Verified native IDs, not names/time/PID, establish grouping."""
    meta = payload.get("pentaho_identity") or {}
    authority = payload.get("pentaho_verification") or {}
    claims = set(authority.get("claims", []))
    if meta.get("version") != 1 or "INVOCATION" not in claims:
        raise ValueError("PENTAHO_NATIVE_IDENTITY_UNVERIFIED")
    alias = meta.get("invocation_alias")
    if (
        not isinstance(alias, str)
        or not alias.startswith("pentaho-r1:")
        or len(alias) != 75
        or meta.get("native_job_id") != resource.configuration.get("native_job_id")
        or meta.get("environment") != resource.environment
        or not meta.get("native_execution_id")
        or not meta.get("authority_id")
        or meta.get("workload_kind") not in {"JOB", "TRANSFORMATION"}
    ):
        raise ValueError("PENTAHO_IDENTITY_AMBIGUOUS")
    scope = [
        str(resource.organization_id),
        str(resource.id),
        meta["environment"],
        meta["native_job_id"],
        meta["workload_kind"],
    ]
    scheduler = meta.get("scheduler")
    verified_retry = False
    if isinstance(scheduler, dict) and "SCHEDULER_RETRY" in claims:
        required = {
            "authority_id",
            "native_run_id",
            "native_attempt_id",
            "attempt_order",
            "authority_revision",
            "retry_state",
            "authority_evidence_sha256",
        }
        verified_retry = bool(
            required <= scheduler.keys()
            and all(
                isinstance(scheduler.get(k), str) and scheduler[k]
                for k in ("authority_id", "native_run_id", "native_attempt_id")
            )
            and type(scheduler.get("attempt_order")) is int
            and 1 <= scheduler["attempt_order"] <= 10000
            and type(scheduler.get("authority_revision")) is int
            and 1 <= scheduler["authority_revision"] <= 10000
            and scheduler.get("retry_state") in {"PENDING", "EXHAUSTED", "UNKNOWN"}
            and bool(
                re.fullmatch(
                    r"[a-f0-9]{64}", str(scheduler.get("authority_evidence_sha256", ""))
                )
            )
            and (
                scheduler["attempt_order"] == 1
                or bool(scheduler.get("previous_attempt_id"))
            )
        )
    group = (
        "pentaho-logical:"
        + digest(scope + [scheduler["authority_id"], scheduler["native_run_id"]])
        if verified_retry
        else alias
    )
    scheduler_alias = (
        "scheduler-attempt:"
        + digest(
            scope
            + [
                scheduler["authority_id"],
                scheduler["native_run_id"],
                scheduler["native_attempt_id"],
            ]
        )
        if verified_retry
        else None
    )
    return {
        "invocation": alias,
        "logical": group,
        "scheduler_alias": scheduler_alias,
        "previous_alias": (
            "scheduler-attempt:"
            + digest(
                scope
                + [
                    scheduler["authority_id"],
                    scheduler["native_run_id"],
                    scheduler["previous_attempt_id"],
                ]
            )
            if verified_retry and scheduler["attempt_order"] > 1
            else None
        ),
        "order": scheduler["attempt_order"] if verified_retry else 1,
        "scheduler": scheduler if verified_retry else {},
        "unverified_retry": bool(scheduler and not verified_retry),
        "native": meta,
        "claims": claims,
    }


def execution_state(attempts):
    """Separate lifecycle/outcome from attempt completeness and health."""
    ordered = sorted(attempts, key=lambda a: a.attempt_order)
    if not ordered:
        return "IDENTIFIED", None, "UNKNOWN"
    latest = ordered[-1]
    completeness = (
        "COMPLETE"
        if all(a.completeness == "COMPLETE" for a in ordered)
        and len(ordered) == latest.attempt_order
        else "PARTIAL"
    )
    if latest.outcome == "SUCCESS":
        return (
            "TERMINAL",
            "SUCCESS_AFTER_RETRY" if latest.attempt_order > 1 else "SUCCESS",
            completeness,
        )
    if (
        latest.outcome == "CANCELLED"
        and latest.retry_authority.get("retry_state") != "PENDING"
    ):
        return "TERMINAL", "CANCELLED", completeness
    if latest.outcome == "FAILED":
        retry = latest.retry_authority.get("retry_state")
        if retry == "PENDING":
            return "WAITING_FOR_RETRY", None, completeness
        if retry == "EXHAUSTED":
            return "TERMINAL", "FAILED", completeness
    return (
        ("RUNNING" if latest.outcome == "RUNNING" else "IDENTIFIED"),
        None,
        completeness,
    )


def reduce_events(db, resource, events, job=None):
    """Shared JobOrder row lock is held by reduce_execution() before entering."""
    from app.unified.pentaho_review import open_review

    def unresolved(event, error, history=None):
        event.processing_status = "UNRESOLVED"
        event.processing_error = error
        if history:
            event.history_id = history.id
        open_review(db, resource, event, error, history)

    histories = {}
    for event in events:
        if db.scalar(
            select(PentahoRevision.id).where(PentahoRevision.event_id == event.id)
        ):
            continue
        try:
            claim = identity_claim(event.payload, resource)
        except (ValueError, TypeError, KeyError) as error:
            unresolved(
                event,
                (
                    str(error)
                    if isinstance(error, ValueError)
                    else "PENTAHO_IDENTITY_AMBIGUOUS"
                ),
            )
            continue
        keys = [claim["invocation"], claim["logical"]]
        if claim["scheduler_alias"]:
            keys.append(claim["scheduler_alias"])
        aliases = list(
            db.scalars(
                select(PentahoAlias).where(
                    PentahoAlias.organization_id == resource.organization_id,
                    PentahoAlias.resource_id == resource.id,
                    PentahoAlias.alias_key.in_(keys),
                )
            )
        )
        history_ids = {a.history_id for a in aliases}
        if len(history_ids) > 1:
            for history_id in sorted(history_ids, key=str):
                unresolved(
                    event,
                    "PENTAHO_IDENTITY_CONFLICT",
                    db.get(JobOrderHistory, history_id),
                )
            continue
        history = (
            db.get(JobOrderHistory, next(iter(history_ids))) if history_ids else None
        )
        if history is None:
            # Safely adopt an unchanged existing invocation projection; never
            # combine/relabel pre-existing terminal histories without review.
            existing_rows = list(
                db.scalars(
                    select(JobOrderHistory).where(
                        JobOrderHistory.job_order_id == resource.job_order_id,
                        JobOrderHistory.provider_execution_id.in_(
                            [claim["logical"], claim["invocation"]]
                        ),
                    )
                )
            )
            if len(existing_rows) > 1:
                unresolved(event, "PENTAHO_LEGACY_IDENTITY_AMBIGUOUS")
                continue
            existing = existing_rows[0] if existing_rows else None
            if (
                existing
                and not existing.pentaho_resource_id
                and existing.status in {ExecutionStatus.SUCCESS, ExecutionStatus.FAILED}
            ):
                from app.unified.pentaho_models import PentahoEvidenceReview

                approval = db.scalar(
                    select(PentahoEvidenceReview.id).where(
                        PentahoEvidenceReview.event_id == event.id,
                        PentahoEvidenceReview.category == "LEGACY_ADOPTION",
                        PentahoEvidenceReview.status == "ACCEPTED",
                    )
                )
                if not approval:
                    unresolved(
                        event, "PENTAHO_LEGACY_IDENTITY_REVIEW_REQUIRED", existing
                    )
                    continue
            history = existing or JobOrderHistory(
                job_order_id=resource.job_order_id,
                provider_execution_id=claim["logical"],
                status=ExecutionStatus.UNKNOWN,
                execution_type=ExecutionType(
                    event.payload.get("execution_type", "SCHEDULED")
                ),
                detected_at=event.received_at,
                expected_runtime_seconds=job.expected_runtime_seconds if job else None,
                sla_seconds=job.sla_seconds if job else None,
            )
            history.pentaho_customer_id = resource.organization_id
            history.pentaho_resource_id = resource.id
            history.pentaho_lifecycle = "IDENTIFIED"
            history.pentaho_identity_state = "CONFIRMED"
            history.pentaho_completeness = "UNKNOWN"
            history.pentaho_review_state = "CLEAR"
            if claim["scheduler"].get("native_occurrence_id"):
                history.pentaho_schedule_occurrence = {
                    "authority_id": claim["scheduler"]["authority_id"],
                    "native_occurrence_id": claim["scheduler"]["native_occurrence_id"],
                }
            db.add(history)
            db.flush()
        if claim["scheduler"] and claim["order"] > 1:
            scheduler = claim["scheduler"]
            if scheduler.get("previous_attempt_id") == scheduler.get(
                "native_attempt_id"
            ):
                unresolved(event, "PENTAHO_RETRY_PREDECESSOR_CONFLICT", history)
                continue
        if claim["previous_alias"]:
            predecessor = db.scalar(
                select(PentahoAlias).where(
                    PentahoAlias.organization_id == resource.organization_id,
                    PentahoAlias.resource_id == resource.id,
                    PentahoAlias.alias_key == claim["previous_alias"],
                )
            )
            if predecessor:
                prior_attempt = (
                    db.get(PentahoAttempt, predecessor.attempt_id)
                    if predecessor.attempt_id
                    else None
                )
                if (
                    not prior_attempt
                    or prior_attempt.history_id != history.id
                    or prior_attempt.attempt_order >= claim["order"]
                ):
                    unresolved(event, "PENTAHO_RETRY_PREDECESSOR_CONFLICT", history)
                    continue
        mapped_attempts = {a.attempt_id for a in aliases if a.attempt_id}
        if len(mapped_attempts) > 1:
            unresolved(event, "PENTAHO_ATTEMPT_ALIAS_CONFLICT", history)
            continue
        attempt = (
            db.get(PentahoAttempt, next(iter(mapped_attempts)))
            if mapped_attempts
            else None
        )
        previous_scheduler = (
            (attempt.native_identity.get("scheduler") or {}) if attempt else {}
        )
        if (
            attempt
            and claim["scheduler"]
            and previous_scheduler
            and any(
                previous_scheduler.get(key) != claim["scheduler"].get(key)
                for key in ("authority_id", "native_run_id", "native_attempt_id")
            )
        ):
            unresolved(event, "PENTAHO_IDENTITY_CONFLICT", history)
            continue
        if attempt and (
            attempt.history_id != history.id or attempt.attempt_order != claim["order"]
        ):
            unresolved(event, "PENTAHO_RETRY_ASSOCIATION_AMBIGUOUS", history)
            continue
        if attempt is None:
            occupied = db.scalar(
                select(PentahoAttempt).where(
                    PentahoAttempt.history_id == history.id,
                    PentahoAttempt.attempt_order == claim["order"],
                )
            )
            if occupied:
                unresolved(event, "PENTAHO_ATTEMPT_ORDER_CONFLICT", history)
                continue
            attempt = PentahoAttempt(
                organization_id=resource.organization_id,
                resource_id=resource.id,
                history_id=history.id,
                attempt_key=claim["invocation"],
                attempt_order=claim["order"],
                native_identity=claim["native"],
                outcome="UNKNOWN",
                completeness="PARTIAL",
                retry_authority={},
                revision=0,
            )
            db.add(attempt)
            db.flush()
        # A later proposed alias cannot retarget any confirmed registration.
        by_key = {a.alias_key: a for a in aliases}
        alias_pairs = [
            ("INVOCATION", claim["invocation"]),
            ("SCHEDULER_ATTEMPT", claim["scheduler_alias"]),
        ]
        if claim["logical"] != claim["invocation"]:
            alias_pairs.insert(0, ("LOGICAL", claim["logical"]))
        for kind, key in alias_pairs:
            if key and key not in by_key:
                row = PentahoAlias(
                    organization_id=resource.organization_id,
                    resource_id=resource.id,
                    history_id=history.id,
                    attempt_id=(
                        None
                        if kind == "LOGICAL" and key != claim["invocation"]
                        else attempt.id
                    ),
                    alias_key=key,
                    kind=kind,
                    native_identity=claim["native"],
                )
                db.add(row)
                by_key[key] = row
        signature = digest(
            {
                "identity": claim["native"],
                "claims": sorted(claim["claims"]),
                "timestamp": event.payload.get("timestamp"),
                "execution_type": event.payload.get("execution_type"),
            }
        )
        observation_key = digest(
            [
                claim["invocation"],
                claim["native"].get("observation_id") or event.external_key,
            ]
        )
        old = db.scalar(
            select(PentahoRevision).where(
                PentahoRevision.attempt_id == attempt.id,
                PentahoRevision.observation_key == observation_key,
            )
        )
        if old:
            if old.payload.get("signature") != signature:
                unresolved(event, "PENTAHO_OBSERVATION_ID_CONFLICT", history)
            else:
                event.history_id = history.id
                event.processing_status = "PROCESSED"
            continue
        native = claim["native"]
        previous_projection = (
            attempt.outcome,
            attempt.completeness,
            attempt.started_at,
            attempt.ended_at,
            attempt.retry_authority,
        )
        outcome = native.get("native_outcome", "UNKNOWN")
        outcome_verified = (
            "EXECUTION_OUTCOME" in claim["claims"]
            and native.get("completion_evidence") is True
        )
        disposition = "RETRY_UNVERIFIED" if claim["unverified_retry"] else "ACCEPTED"
        conflict_claim = "EXECUTION_OUTCOME"
        if outcome in TERMINAL and outcome_verified:
            if attempt.outcome in TERMINAL and attempt.outcome != outcome:
                disposition = "CONFLICT_PENDING"
            else:
                attempt.outcome = outcome
                attempt.completeness = (
                    "COMPLETE"
                    if native.get("native_started_at") and native.get("native_ended_at")
                    else "PARTIAL"
                )
        elif attempt.outcome not in TERMINAL and outcome == "RUNNING":
            attempt.outcome = "RUNNING"
        if disposition != "CONFLICT_PENDING" and (
            attempt.outcome not in TERMINAL or outcome_verified
        ):
            from app.pipeline_adapters.core import instant
            from datetime import datetime

            start, end = instant(native.get("native_started_at")), instant(
                native.get("native_ended_at")
            )
            if start:
                stamp = datetime.fromisoformat(start)
                attempt.started_at = (
                    min(attempt.started_at, stamp) if attempt.started_at else stamp
                )
            if end and outcome_verified:
                stamp = datetime.fromisoformat(end)
                attempt.ended_at = (
                    max(attempt.ended_at, stamp) if attempt.ended_at else stamp
                )
            retry = claim["scheduler"]
            if retry:
                prior = attempt.retry_authority
                number, previous = retry["authority_revision"], prior.get(
                    "authority_revision", 0
                )
                if number == previous and retry != prior:
                    disposition = "CONFLICT_PENDING"
                    conflict_claim = "SCHEDULER_RETRY"
                elif number > previous:
                    attempt.retry_authority = retry
        if (
            disposition != "CONFLICT_PENDING"
            and history.pentaho_lifecycle == "TERMINAL"
        ):
            candidates = list(
                db.scalars(
                    select(PentahoAttempt).where(
                        PentahoAttempt.history_id == history.id
                    )
                )
            )
            lifecycle, terminal_outcome, _ = execution_state(candidates)
            if lifecycle != "TERMINAL" or terminal_outcome != history.pentaho_outcome:
                disposition = "CONFLICT_PENDING"
                conflict_claim = "SCHEDULER_RETRY"
        if disposition == "CONFLICT_PENDING":
            (
                attempt.outcome,
                attempt.completeness,
                attempt.started_at,
                attempt.ended_at,
                attempt.retry_authority,
            ) = previous_projection
        attempt.revision += 1
        verification = event.payload.get("pentaho_verification", {})
        db.add(
            PentahoRevision(
                organization_id=resource.organization_id,
                resource_id=resource.id,
                history_id=history.id,
                attempt_id=attempt.id,
                event_id=event.id,
                source_evidence_id=(
                    uuid.UUID(verification["evidence_id"])
                    if verification.get("evidence_id")
                    else None
                ),
                revision=attempt.revision,
                observation_key=observation_key,
                disposition=disposition,
                payload={
                    "signature": signature,
                    "identity": native,
                    "verification": verification,
                    "occurred_at": event.payload.get("timestamp"),
                    "observed_at": event.observed_at.isoformat(),
                    "received_at": event.received_at.isoformat(),
                    "attempt_outcome": attempt.outcome,
                    "claim_kind": conflict_claim,
                    "projection_before": {
                        "outcome": previous_projection[0],
                        "completeness": previous_projection[1],
                        "retry_authority": previous_projection[4],
                    },
                    "prior_revision_ids": [
                        str(v)
                        for v in db.scalars(
                            select(PentahoRevision.id)
                            .where(PentahoRevision.attempt_id == attempt.id)
                            .order_by(PentahoRevision.revision.desc())
                            .limit(100)
                        )
                    ],
                },
            )
        )
        event.history_id = history.id
        event.processing_status = "PROCESSED"
        if disposition != "ACCEPTED":
            error = (
                "PENTAHO_RETRY_AUTHORITY_CONFLICT"
                if disposition == "CONFLICT_PENDING"
                and conflict_claim == "SCHEDULER_RETRY"
                else "PENTAHO_" + disposition
            )
            unresolved(event, error, history)
        # Materialize each accepted projection before a later claim in this
        # batch can conflict; freezing must preserve that defensible state.
        project_history(db, history, observed_at=event.observed_at)
        if (
            history.pentaho_outcome == "FAILED"
            and history.ended_at
            and outcome_verified
            and native.get("native_outcome") == "FAILED"
        ):
            threshold = (
                resource.configuration.get("historical_notifications") or {}
            ).get("historical_after_seconds", 3600)
            if (event.received_at - history.ended_at).total_seconds() >= threshold:
                history.source_evidence = {
                    **(history.source_evidence or {}),
                    "pentaho_historical": {
                        "occurred_at": history.ended_at.isoformat(),
                        "discovered_at": event.received_at.isoformat(),
                        "event_id": str(event.id),
                        "operational_reassessment_required": True,
                        "notification_eligibility": "PENDING_POLICY_AND_EVIDENCE_REVIEW",
                    },
                }
        histories[history.id] = history
        db.flush()
    for history in histories.values():
        project_history(db, history, observed_at=max(e.observed_at for e in events))
    db.flush()
    return next(iter(histories.values()), None)


def apply_native_outcome(attempt, native):
    """Caller has already checked native completion authority and identity."""
    from app.pipeline_adapters.core import instant
    from datetime import datetime

    attempt.outcome = native["native_outcome"]
    start, end = instant(native.get("native_started_at")), instant(
        native.get("native_ended_at")
    )
    if start:
        attempt.started_at = datetime.fromisoformat(start)
    if end:
        attempt.ended_at = datetime.fromisoformat(end)
    attempt.completeness = "COMPLETE" if start and end else "PARTIAL"


def project_history(db, history, allow_correction=False, observed_at=None):
    if not allow_correction and history.pentaho_review_state == "CONFLICTED_EVIDENCE":
        return
    attempts = list(
        db.scalars(
            select(PentahoAttempt)
            .where(PentahoAttempt.history_id == history.id)
            .order_by(PentahoAttempt.attempt_order)
        )
    )
    lifecycle, outcome, completeness = execution_state(attempts)
    # Only an explicit audited outcome decision can revise a terminal projection.
    if (
        not allow_correction
        and history.pentaho_lifecycle == "TERMINAL"
        and (lifecycle != "TERMINAL" or outcome != history.pentaho_outcome)
    ):
        history.pentaho_identity_state = "REVIEW_REQUIRED"
        return
    history.pentaho_lifecycle, history.pentaho_outcome = lifecycle, outcome
    history.pentaho_completeness = completeness
    history.status = (
        ExecutionStatus.SUCCESS
        if outcome in {"SUCCESS", "SUCCESS_AFTER_RETRY"}
        else (
            ExecutionStatus.FAILED
            if outcome == "FAILED"
            else (
                ExecutionStatus.RUNNING
                if lifecycle in {"RUNNING", "WAITING_FOR_RETRY"}
                else ExecutionStatus.UNKNOWN
            )
        )
    )
    starts = [a.started_at for a in attempts if a.started_at]
    history.started_at = min(starts) if starts else None
    history.ended_at = attempts[-1].ended_at if lifecycle == "TERMINAL" else None
    history.source_result = "PENTAHO_NATIVE_ATTEMPT_RECONSTRUCTION"
    history.source_evidence = {
        **(history.source_evidence or {}),
        "resource_id": str(history.pentaho_resource_id),
        "attempt_ids": [str(a.id) for a in attempts],
        **({"observed_at": observed_at.isoformat()} if observed_at else {}),
    }


def proof_covers_claims(definition, payload):
    """Required native proof shape for independent review, never certification."""
    declared = definition.get("verified_pentaho_claims", [])
    if (
        not isinstance(declared, list)
        or not all(isinstance(v, str) for v in declared)
        or set(declared) - CLAIMS
    ):
        return False
    if not declared:
        return True  # Legacy profile: no new execution/retry authority granted.
    meta = (payload.get("event") or {}).get("pentaho_identity") or {}
    if (
        "INVOCATION" not in declared
        or not meta.get("invocation_alias")
        or not meta.get("native_execution_id")
    ):
        return False
    if "EXECUTION_OUTCOME" in declared and not (
        meta.get("completion_evidence") is True
        and meta.get("native_outcome") in TERMINAL
    ):
        return False
    if "SCHEDULE" in declared:
        from app.unified.pentaho_schedule import native_schedule

        try:
            native_schedule(meta.get("schedule"))
        except (ValueError, TypeError, KeyError):
            return False
    if "SCHEDULER_RETRY" in declared:
        from types import SimpleNamespace

        try:
            candidate = identity_claim(
                {
                    "pentaho_identity": meta,
                    "pentaho_verification": {"claims": declared},
                },
                SimpleNamespace(
                    organization_id="review",
                    id="review",
                    environment=meta.get("environment"),
                    configuration={"native_job_id": meta.get("native_job_id")},
                ),
            )
        except (ValueError, TypeError, KeyError):
            return False
        if not candidate["scheduler"]:
            return False
    return True
