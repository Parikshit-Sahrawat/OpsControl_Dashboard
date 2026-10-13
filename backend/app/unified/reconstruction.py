"""Durable replay reducer: terminal facts, parallel steps and retry attempts."""

import hashlib, json, uuid, fnmatch
from datetime import datetime, timezone
from sqlalchemy import select, exists, func
from app.models import (
    JobOrder,
    JobOrderHistory,
    JobStepExecution,
    ExecutionStatus,
    ExecutionType,
    LogEvent,
    LogSource,
)
from app.unified.models import MonitoringResource, NormalizedEvent, ParameterVersion
from app.unified.normalization import normalize, NormalizationError


def enqueue(db, resource, payload, source_kind, key, observed_at, log_id=None):
    old = db.scalar(
        select(NormalizedEvent).where(
            NormalizedEvent.resource_id == resource.id,
            NormalizedEvent.external_key == key,
        )
    )
    if old:
        return old, False
    event = NormalizedEvent(
        organization_id=resource.organization_id,
        resource_id=resource.id,
        external_key=key,
        source_kind=source_kind,
        log_event_id=log_id,
        observed_at=observed_at,
        payload=payload,
    )
    db.add(event)
    db.flush()
    return event, True


def reduce_execution(db, resource, identity):
    events = db.scalars(
        select(NormalizedEvent)
        .where(
            NormalizedEvent.resource_id == resource.id,
            NormalizedEvent.payload["execution_id"].astext == identity,
            NormalizedEvent.processing_status.in_(["PENDING", "PROCESSED"]),
        )
        .order_by(NormalizedEvent.observed_at, NormalizedEvent.external_key)
    ).all()
    if not events:
        return None
    job = db.scalar(
        select(JobOrder).where(JobOrder.id == resource.job_order_id).with_for_update()
    )
    history = db.scalar(
        select(JobOrderHistory)
        .where(
            JobOrderHistory.job_order_id == job.id,
            JobOrderHistory.provider_execution_id == identity,
        )
        .with_for_update()
    )
    if history is None:
        history = JobOrderHistory(
            job_order_id=job.id,
            provider_execution_id=identity,
            execution_type=ExecutionType(
                events[0].payload.get("execution_type", "SCHEDULED")
            ),
            status=ExecutionStatus.UNKNOWN,
            detected_at=events[0].received_at,
            expected_runtime_seconds=job.expected_runtime_seconds,
            sla_seconds=job.sla_seconds,
        )
        db.add(history)
        db.flush()
    starts = [e.observed_at for e in events if e.payload["event_type"] == "START"]
    ends = [
        e
        for e in events
        if e.payload["event_type"] == "END"
        and e.payload["status"] in {"SUCCESS", "FAILED", "UNKNOWN"}
    ]
    if starts:
        history.started_at = min(starts)
    if ends:
        # Conflicting terminal facts are retained and made explicit. A late
        # START/heartbeat cannot downgrade an already terminal execution.
        terminal = ends[-1]
        history.status = ExecutionStatus(terminal.payload["status"])
        history.ended_at = terminal.observed_at
        if len({e.payload["status"] for e in ends}) > 1:
            history.monitoring_conditions = {
                **(history.monitoring_conditions or {}),
                "CONFLICTING_TERMINAL_EVIDENCE": True,
            }
        history.source_error_message = (
            terminal.payload.get("error")
            if history.status == ExecutionStatus.FAILED
            else None
        )
    elif history.status not in {ExecutionStatus.SUCCESS, ExecutionStatus.FAILED}:
        history.status = ExecutionStatus.RUNNING if starts else ExecutionStatus.UNKNOWN
    if (
        history.started_at
        and history.ended_at
        and history.ended_at < history.started_at
    ):
        history.monitoring_conditions = {
            **(history.monitoring_conditions or {}),
            "INCONSISTENT_EXECUTION_TIMES": True,
        }
    step_events = {}
    for event in events:
        p = event.payload
        if p["event_type"].startswith("STEP"):
            step_events.setdefault((p["step_id"], p["attempt"]), []).append(event)
        event.history_id = history.id
        event.processing_status = "PROCESSED"
    for (identity, attempt), facts in step_events.items():
        step = db.scalar(
            select(JobStepExecution).where(
                JobStepExecution.history_id == history.id,
                JobStepExecution.external_step_id == identity,
                JobStepExecution.attempt == attempt,
            )
        )
        if step is None:
            step = JobStepExecution(
                history_id=history.id,
                external_step_id=identity,
                attempt=attempt,
                name=facts[-1].payload["step_name"],
                status="UNKNOWN",
            )
            db.add(step)
        begins = [
            f.observed_at for f in facts if f.payload["event_type"] == "STEP_START"
        ]
        terminal = [
            f for f in facts if f.payload["event_type"] in {"STEP_END", "STEP_FAILED"}
        ]
        if begins:
            step.started_at = min(begins)
        if terminal:
            last = terminal[-1]
            step.ended_at = last.observed_at
            step.status = (
                "FAILED"
                if last.payload["event_type"] == "STEP_FAILED"
                else last.payload["status"]
            )
            step.error_message = last.payload.get("error")
        elif begins:
            step.status = "RUNNING"
        step.duration_seconds = (
            int((step.ended_at - step.started_at).total_seconds())
            if step.started_at and step.ended_at and step.ended_at >= step.started_at
            else None
        )
        step.source_evidence = {"event_ids": [str(f.id) for f in facts]}
        if step.status == "FAILED":
            history.failed_step = step.name
    history.source_result = "NATIVE_EXECUTION_RECONSTRUCTION"
    history.source_evidence = {
        **(history.source_evidence or {}),
        "resource_id": str(resource.id),
        "platform": resource.configuration.get("platform"),
        "event_ids": [str(e.id) for e in events][-1000:],
        "native_order_id": events[-1].payload.get("native_order_id"),
        "observed_at": max(e.observed_at for e in events).isoformat(),
        "incomplete_start": history.started_at is None,
        "incomplete_terminal": history.ended_at is None,
    }
    db.flush()
    return history


def ingest_logs(db, resource, version, limit=200):
    if not resource.linked_vm_id:
        return 0
    vm = db.scalar(
        select(MonitoringResource).where(
            MonitoringResource.vm_id == resource.linked_vm_id
        )
    )
    if not vm or not vm.data_source_id:
        return 0
    rootlogs = (
        select(LogEvent)
        .join(LogSource)
        .where(
            LogSource.data_source_id == vm.data_source_id,
            LogEvent.organization_id == resource.organization_id,
            LogEvent.observed_at >= resource.created_at,
            ~exists(
                select(NormalizedEvent.id).where(
                    NormalizedEvent.resource_id == resource.id,
                    NormalizedEvent.log_event_id == LogEvent.id,
                )
            ),
        )
        .order_by(LogEvent.observed_at, LogEvent.id)
        .limit(limit)
    )
    logs = db.scalars(rootlogs).all()
    ids = set()
    parsed = 0
    for log in logs:
        path = (log.attributes or {}).get("log.file.path")
        allowed = resource.configuration.get("log_paths", [])
        if allowed and (
            not path
            or not any(
                fnmatch.fnmatchcase(path.replace("\\", "/"), p.replace("\\", "/"))
                for p in allowed
            )
        ):
            event, _ = enqueue(
                db,
                resource,
                {},
                "FILE_LOG",
                "log:" + str(log.id),
                log.observed_at,
                log.id,
            )
            event.processing_status = "IGNORED"
            event.processing_error = "OTHER_LOG_SOURCE"
            continue
        key = (
            "log:"
            + hashlib.sha256(
                (
                    str(log.log_source_id)
                    + "|"
                    + log.observed_at.isoformat()
                    + "|"
                    + log.message
                ).encode()
            ).hexdigest()
        )
        try:
            payload, instant = normalize(
                log.message,
                version.configuration["parser"],
                log.observed_at,
                resource.configuration["jobchain"],
            )
            event, new = enqueue(
                db, resource, payload, "FILE_LOG", key, instant, log.id
            )
            event.parameter_version = version.version
            if not new and event.log_event_id != log.id:
                duplicate, _ = enqueue(
                    db,
                    resource,
                    {"duplicate_of": str(event.id)},
                    "FILE_LOG",
                    "duplicate:" + str(log.id),
                    instant,
                    log.id,
                )
                duplicate.processing_status = "IGNORED"
                duplicate.processing_error = "DUPLICATE_EVIDENCE"
            ids.add(payload["execution_id"])
            parsed += int(new)
        except NormalizationError as error:
            event, _ = enqueue(
                db,
                resource,
                {},
                "FILE_LOG",
                "log:" + str(log.id),
                log.observed_at,
                log.id,
            )
            event.processing_error = str(error)
            event.processing_status = (
                "IGNORED"
                if str(error) in {"OTHER_JOBCHAIN", "PARSER_NOT_MATCHED"}
                else "UNRESOLVED"
            )
    for id in ids:
        reduce_execution(db, resource, id)
    return parsed


def ingest_connector(db, resource, version, limit=100):
    from app.models import CollectorRun

    if not resource.primary_collector_id:
        return 0
    runs = db.scalars(
        select(CollectorRun)
        .where(
            CollectorRun.collector_id == resource.primary_collector_id,
            CollectorRun.ended_at >= resource.created_at,
            CollectorRun.status == "SUCCESS",
        )
        .order_by(CollectorRun.ended_at.desc())
        .limit(limit)
    ).all()
    identities = set()
    count = 0
    for run in runs:
        for fact in (run.source_metadata or {}).get("execution_records", []):
            event, new = enqueue(
                db,
                resource,
                fact["event"],
                "IICS",
                fact["key"],
                datetime.fromisoformat(fact["observed_at"]),
            )
            event.parameter_version = version.version
            identities.add(fact["event"]["execution_id"])
            count += int(new)
    for identity in identities:
        reduce_execution(db, resource, identity)
    return count
