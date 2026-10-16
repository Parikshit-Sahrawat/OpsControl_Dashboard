"""Explicit schedule authority and conservative persisted telemetry coverage.

Native occurrence IDs come from verified exports, never from a timestamp guess.
Configured calendar expectations never assert native scheduler authority.
"""

from datetime import datetime, timedelta, timezone
from sqlalchemy import select, cast, DateTime
from fastapi import HTTPException
from app.models import JobOrderHistory
from app.unified.schemas import Schedule
from app.unified.calendar import occurrences, next_occurrence
from app.unified.models import ExpectedExecutionWindow
from app.unified.pentaho_execution import digest
from app.data_pipelines import service as s
from app.data_pipelines.models import (
    PipelineAssociation,
    PipelineJob,
    PipelineMethod,
    PipelineSource,
    PipelineCapability,
    PipelineEvidence,
    PipelineHold,
    PipelineOperation,
)


def native_schedule(value):
    if not isinstance(value, dict) or set(value) != {
        "authority_id",
        "revision",
        "schedule",
        "observed_at",
        "valid_until",
        "evidence_sha256",
        "occurrences",
    }:
        raise ValueError(
            "Native schedule identity, revision, provenance and occurrence inventory required"
        )
    if not all(
        isinstance(value[k], str) and 1 <= len(value[k]) <= 200
        for k in ("authority_id", "revision")
    ):
        raise ValueError("Bounded native schedule identity required")
    import re

    if not re.fullmatch("[a-f0-9]{64}", value["evidence_sha256"]):
        raise ValueError("Native schedule hash required")
    start, end = datetime.fromisoformat(value["observed_at"]), datetime.fromisoformat(
        value["valid_until"]
    )
    if (
        not start.tzinfo
        or not end.tzinfo
        or end <= start
        or end - start > timedelta(days=31)
    ):
        raise ValueError("Bounded fresh native schedule export required")
    schedule = Schedule.model_validate(value["schedule"]).model_dump(mode="json")
    rows = value["occurrences"]
    if not isinstance(rows, list) or not 1 <= len(rows) <= 1000:
        raise ValueError("Bounded native occurrence inventory required")
    seen, instants = set(), set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {
            "native_occurrence_id",
            "scheduled_at",
        }:
            raise ValueError("Native occurrence identity required")
        id = row["native_occurrence_id"]
        stamp = datetime.fromisoformat(row["scheduled_at"])
        if (
            not isinstance(id, str)
            or not 1 <= len(id) <= 200
            or id in seen
            or not stamp.tzinfo
            or not start <= stamp <= end
            or stamp in instants
        ):
            raise ValueError("Ambiguous native occurrence inventory")
        seen.add(id)
        instants.add(stamp)
    return {**value, "schedule": schedule}


def bindings(db, resource):
    return list(
        db.scalars(
            select(PipelineMethod)
            .join(
                PipelineAssociation, PipelineAssociation.method_id == PipelineMethod.id
            )
            .join(PipelineJob, PipelineJob.id == PipelineAssociation.job_id)
            .join(PipelineSource, PipelineSource.id == PipelineMethod.source_id)
            .where(
                PipelineJob.resource_id == resource.id,
                PipelineJob.selected.is_(True),
                PipelineJob.quarantined.is_(False),
                PipelineMethod.organization_id == resource.organization_id,
                PipelineMethod.enabled.is_(True),
                PipelineAssociation.generation == PipelineSource.generation,
            )
            .distinct()
        )
    )


def authority(db, resource, config, now, strict=False):
    selected = config.get("pentaho_schedule_authority")
    result = {"mode": "UNKNOWN", "reason": "EXPLICIT_SCHEDULE_AUTHORITY_REQUIRED"}
    if selected:
        result = dict(selected)
        mode = result["mode"]
        if mode in {"MONITORING_EXPECTATION", "MANUAL"}:
            if mode == "MONITORING_EXPECTATION" and not config.get("schedule"):
                result = {
                    "mode": "UNKNOWN",
                    "reason": "MONITORING_EXPECTATION_REQUIRES_CALENDAR",
                }
        else:
            try:
                proof = db.get(
                    PipelineEvidence,
                    __import__("uuid").UUID(str(result["evidence_id"])),
                )
                profile = db.get(
                    PipelineCapability,
                    __import__("uuid").UUID(str(result["capability_id"])),
                )
                methods = bindings(db, resource)
                method = next(
                    (
                        m
                        for m in methods
                        if m.capability_id == profile.id
                        and m.source_id == proof.source_id
                        and s.eligible(db, m)
                    ),
                    None,
                )
                export = native_schedule(
                    proof.payload["event"]["pentaho_identity"]["schedule"]
                )
                source = db.get(PipelineSource, proof.source_id)
                valid = (
                    method
                    and proof.organization_id == resource.organization_id
                    and proof.generation == source.generation
                    and profile.verification_evidence_id == proof.id
                    and "SCHEDULE"
                    in profile.definition.get("verified_pentaho_claims", [])
                    and proof.payload.get("runtime_origin") == "AUTHENTICATED_RUNTIME"
                )
                valid = (
                    valid
                    and proof.native_job_id
                    == resource.configuration.get("native_job_id")
                    and result["authority_id"] == export["authority_id"]
                    and result["revision"] == export["revision"]
                    and config.get("schedule") == export["schedule"]
                )
                valid = valid and datetime.fromisoformat(
                    export["observed_at"]
                ) <= now <= datetime.fromisoformat(export["valid_until"])
                if not valid:
                    raise ValueError("Unverified schedule")
                result.update(
                    export=export,
                    source_id=str(source.id),
                    generation=str(source.generation),
                    proof_sha256=digest(proof.payload),
                )
            except (ValueError, TypeError, KeyError, AttributeError, StopIteration):
                result = {
                    "mode": "UNKNOWN",
                    "reason": "NATIVE_SCHEDULE_AUTHORITY_UNVERIFIED_OR_STALE",
                }
    if strict and selected and result["mode"] == "UNKNOWN":
        raise HTTPException(409, result["reason"])
    return result


def coverage(db, resource, observed):
    refs = bindings(db, resource)
    sources = {m.source_id: db.get(PipelineSource, m.source_id) for m in refs}
    ready = bool(refs) and all(s.eligible(db, m) for m in refs)
    for source in sources.values():
        receipt = db.scalar(
            select(PipelineOperation)
            .where(
                PipelineOperation.source_id == source.id,
                PipelineOperation.kind == "ACCEPTANCE",
                PipelineOperation.configuration["generation"].astext
                == str(source.generation),
            )
            .order_by(
                cast(
                    PipelineOperation.result["accepted_at"].astext,
                    DateTime(timezone=True),
                )
                .desc()
                .nullslast(),
                PipelineOperation.created_at.desc(),
            )
            .limit(1)
        )
        complete = bool(
            receipt
            and receipt.result.get("complete") is True
            and receipt.result.get("accepted_at")
            and 0
            <= (
                observed - datetime.fromisoformat(receipt.result["accepted_at"])
            ).total_seconds()
            <= 120
        )
        ready = (
            complete
            and ready
            and not s.suspended(db, source)
            and source.continuity_validated
            and source.health in {"RECEIVING", "IDLE"}
            and source.last_observed_at is not None
            and 0 <= (observed - source.last_observed_at).total_seconds() <= 120
        )
    signature = digest(sorted((str(k), str(v.generation)) for k, v in sources.items()))
    op, _ = s.operation(
        db,
        resource.organization_id,
        "PENTAHO_SCHEDULE_COVERAGE",
        str(resource.id),
        {},
        None,
        source_id=None,
    )
    state = op.result or {}
    last = (
        datetime.fromisoformat(state["checked_at"]) if state.get("checked_at") else None
    )
    since = (
        state.get("since")
        if ready
        and state.get("signature") == signature
        and last
        and 0 <= (observed - last).total_seconds() <= 120
        else None
    )
    op.result = {
        "ready": bool(ready),
        "since": since or (observed.isoformat() if ready else None),
        "checked_at": observed.isoformat(),
        "signature": signature,
    }
    op.state = "COMPLETE"
    return op.result, list(sources)


def evaluate(db, resource, parameters, observed):
    from app.unified.engines import condition

    # The parent resource lock is already held by cycle; tests use the same path.
    config = parameters.configuration
    chosen = authority(db, resource, config, observed)
    health, sources = coverage(db, resource, observed)
    if chosen["mode"] == "MANUAL" or not config.get("schedule"):
        return
    start = resource.schedule_watermark or max(
        resource.created_at, parameters.created_at
    )
    if chosen["mode"] == "VERIFIED_SCHEDULER":
        candidates = [
            (datetime.fromisoformat(v["scheduled_at"]), v["native_occurrence_id"])
            for v in chosen["export"]["occurrences"]
            if start < datetime.fromisoformat(v["scheduled_at"]) <= observed
        ]
        candidates = sorted(candidates)[:200]
    else:
        candidates = [
            (v, None)
            for v in occurrences(config["schedule"], start, observed, limit=200)
        ]
    for stamp, native_id in candidates:
        if not db.scalar(
            select(ExpectedExecutionWindow.id).where(
                ExpectedExecutionWindow.resource_id == resource.id,
                ExpectedExecutionWindow.scheduled_at == stamp,
            )
        ):
            db.add(
                ExpectedExecutionWindow(
                    organization_id=resource.organization_id,
                    resource_id=resource.id,
                    scheduled_at=stamp,
                    deadline=stamp + timedelta(seconds=config["no_run_grace_seconds"]),
                    parameter_version=parameters.version,
                    status="PENDING_GRACE",
                    pentaho_authority={
                        "selection": chosen,
                        "calendar": config["schedule"],
                        "grace_seconds": config["no_run_grace_seconds"],
                        "native_occurrence_id": native_id,
                        "delayed_seconds": config["delayed_start_seconds"],
                    },
                    evidence={},
                )
            )
    resource.schedule_watermark = (
        candidates[-1][0] if len(candidates) == 200 else observed
    )
    db.flush()
    windows = list(
        db.scalars(
            select(ExpectedExecutionWindow)
            .where(
                ExpectedExecutionWindow.resource_id == resource.id,
                ExpectedExecutionWindow.status.in_(
                    ["EXPECTED", "PENDING_GRACE", "UNKNOWN", "INCOMPLETE", "NO_RUN"]
                ),
            )
            .order_by(
                ExpectedExecutionWindow.evaluated_at.nullsfirst(),
                ExpectedExecutionWindow.scheduled_at,
            )
            .limit(200)
        )
    )
    for window in windows:
        snapshot = window.pentaho_authority or {
            "selection": {"mode": "UNKNOWN"},
            "calendar": config["schedule"],
        }
        selection = snapshot["selection"]
        mode = selection["mode"]
        query = select(JobOrderHistory).where(
            JobOrderHistory.job_order_id == resource.job_order_id,
            JobOrderHistory.pentaho_identity_state == "CONFIRMED",
            JobOrderHistory.execution_type == "SCHEDULED",
        )
        if mode == "VERIFIED_SCHEDULER":
            query = query.where(
                JobOrderHistory.pentaho_schedule_occurrence["authority_id"].astext
                == selection["authority_id"],
                JobOrderHistory.pentaho_schedule_occurrence[
                    "native_occurrence_id"
                ].astext
                == snapshot["native_occurrence_id"],
            )
        else:
            end = next_occurrence(snapshot["calendar"], window.scheduled_at)
            query = query.where(JobOrderHistory.started_at >= window.scheduled_at)
            if end:
                query = query.where(JobOrderHistory.started_at < end)
        run = (
            db.scalar(query.order_by(JobOrderHistory.started_at).limit(1))
            if mode != "UNKNOWN"
            else None
        )
        window.evaluated_at = observed
        window.evidence = {
            **window.evidence,
            "authority_mode": mode,
            "checked_at": observed.isoformat(),
            "coverage": health,
        }
        if run:
            condition(
                db,
                resource,
                "NO_RUN:" + str(window.id),
                "NO_RUN",
                False,
                "CRITICAL",
                "Expected invocation observed; outcome is independent",
                {"window_id": str(window.id), "execution_id": str(run.id)},
                observed,
            )
            window.history_id = run.id
            window.status = (
                "DELAYED"
                if run.started_at
                and (run.started_at - window.scheduled_at).total_seconds()
                > snapshot.get("delayed_seconds", 120)
                else "OBSERVED"
            )
            window.evidence = {
                **window.evidence,
                "execution_id": str(run.id),
                "outcome_is_independent": True,
            }
            continue
        if window.status == "NO_RUN":
            continue  # A proven historical miss does not disappear on a later outage.
        if mode == "UNKNOWN" or (
            mode == "VERIFIED_SCHEDULER"
            and (
                chosen["mode"] != "VERIFIED_SCHEDULER"
                or observed > datetime.fromisoformat(selection["export"]["valid_until"])
            )
        ):
            window.status = "UNKNOWN"
            continue
        holds = bool(sources) and db.scalar(
            select(PipelineHold.id)
            .where(
                PipelineHold.source_id.in_(sources),
                PipelineHold.kind != "LEGAL",
                PipelineHold.created_at <= observed,
                (
                    (PipelineHold.released_at.is_(None))
                    | (PipelineHold.released_at >= window.scheduled_at)
                ),
            )
            .limit(1)
        )
        failures = bool(sources) and db.scalar(
            select(PipelineOperation.id)
            .where(
                PipelineOperation.source_id.in_(sources),
                PipelineOperation.state == "FAILED",
                PipelineOperation.created_at >= window.scheduled_at,
                PipelineOperation.created_at <= observed,
            )
            .limit(1)
        )
        sufficient = (
            health["ready"]
            and health["since"]
            and datetime.fromisoformat(health["since"]) <= window.scheduled_at
            and not holds
            and not failures
        )
        if not sufficient:
            window.status = "INCOMPLETE"
            continue
        window.status = "PENDING_GRACE" if observed < window.deadline else "NO_RUN"
        if window.status == "NO_RUN":
            window.evidence = {
                **window.evidence,
                "no_run_proof_at": observed.isoformat(),
                "coverage_at_decision": health,
            }
            condition(
                db,
                resource,
                "NO_RUN:" + str(window.id),
                "NO_RUN",
                True,
                "CRITICAL",
                "No execution observed under " + mode,
                {
                    "window_id": str(window.id),
                    "authority_mode": mode,
                    "schedule_revision": selection.get("revision"),
                },
                window.deadline,
            )
