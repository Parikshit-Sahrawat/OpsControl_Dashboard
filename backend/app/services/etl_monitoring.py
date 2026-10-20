"""Read-only Carte ingestion and evidence-based daily schedule evaluation.

One local scheduler owns polling. Source failure, missing execution and poll
failure are different facts. Alert events are appended only on transitions.
"""

from datetime import datetime, timedelta, timezone, time
from uuid import UUID, uuid5, NAMESPACE_URL
from zoneinfo import ZoneInfo
import hashlib
import json
from sqlalchemy import select
from app.models import (
    JobOrder,
    JobOrderHistory,
    JobStepExecution,
    DataSource,
    ExecutionStatus,
    ExecutionType,
    AlertIncidentEvent,
)
from app.unified.models import MonitoringResource, NormalizedEvent


def retain_observation(db, job, collector, record, observed, conflict=False):
    """Append source facts independently of the mutable legacy projection.

    Reuse the canonical resource/evidence store. A contradictory poll must not
    erase either the last defensible projection or the disputed observation.
    The JobOrder lock held by the caller serializes digest deduplication.
    """
    resource = db.scalar(
        select(MonitoringResource).where(
            MonitoringResource.organization_id == job.organization_id,
            MonitoringResource.job_order_id == job.id,
        )
    )
    if resource is None:
        return None  # Legacy unbound orders cannot assert canonical identity.
    digest = hashlib.sha256(
        json.dumps(
            [str(collector.id), record],
            sort_keys=True,
            default=str,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    key = "carte-observation:" + digest
    event = db.scalar(
        select(NormalizedEvent).where(
            NormalizedEvent.resource_id == resource.id,
            NormalizedEvent.external_key == key,
        )
    )
    if event is None:
        event = NormalizedEvent(
            organization_id=job.organization_id,
            resource_id=resource.id,
            external_key=key,
            source_kind="CARTE_READ_ONLY",
            observed_at=observed,
            payload={
                "execution_id": record["execution_id"],
                "native_observation": record,
            },
            # The legacy projection was applied here. Never feed this raw
            # journal back into the independent canonical execution reducer.
            processing_status="QUARANTINED" if conflict else "IGNORED",
            processing_error="CONFLICTING_NATIVE_EVIDENCE" if conflict else None,
        )
        db.add(event)
        db.flush()
    return event


def step_key(item, ordinal):
    # Native copies are stable step identities, not child invocation UUIDs.
    # Identical name/copy rows remain separate by occurrence within this poll;
    # ambiguous repeated invocations are never claimed as native identities.
    return json.dumps([item["name"], item.get("copy"), ordinal], separators=(",", ":"))


def source_time(value):
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else None


def runtime_status(status, started, ended, expected, sla, observed):
    elapsed = (
        max(0, ((ended or observed) - started).total_seconds()) if started else None
    )
    sla_status = (
        "UNKNOWN"
        if elapsed is None or not sla
        else ("BREACHED" if elapsed >= sla else "MET")
    )
    if status == "RUNNING":
        sla_status = (
            "UNKNOWN"
            if elapsed is None or not sla
            else ("BREACHED" if elapsed >= sla else "ON_TRACK")
        )
        if elapsed is not None and expected and elapsed >= expected:
            status = "LONG_RUNNING"
    return status, sla_status


def expected_window(job, observed):
    if not job.expected_window_start or not job.expected_window_end:
        return None
    schedule = job.schedule or {}
    zone = ZoneInfo(schedule.get("timezone", "UTC"))
    local = observed.astimezone(zone)
    start_time = time.fromisoformat(job.expected_window_start)
    end_time = time.fromisoformat(job.expected_window_end)
    day = local.date()
    if end_time <= start_time and local.time().replace(tzinfo=None) < start_time:
        day -= timedelta(days=1)
    if day.weekday() not in schedule.get("weekdays", list(range(7))):
        return None
    start = datetime.combine(day, start_time, zone)
    end = datetime.combine(
        day + timedelta(days=int(end_time <= start_time)), end_time, zone
    )
    return start.astimezone(timezone.utc), end.astimezone(timezone.utc) + timedelta(
        seconds=job.no_run_grace_seconds or 0
    )


def _alert(db, job, history, condition, active, observed):
    reference = str(uuid5(NAMESPACE_URL, f"opscontrol:etl:{job.id}:{condition}"))
    last = db.scalar(
        select(AlertIncidentEvent)
        .join(JobOrderHistory)
        .where(
            JobOrderHistory.job_order_id == job.id,
            AlertIncidentEvent.reference == reference,
        )
        .order_by(AlertIncidentEvent.timestamp.desc(), AlertIncidentEvent.id.desc())
        .limit(1)
    )
    was_open = last is not None and last.event_type.endswith("_OPEN")
    if active == was_open:
        return
    event = AlertIncidentEvent(
        history_id=history.id,
        event_type=condition + ("_OPEN" if active else "_RESOLVED"),
        source="ETL_MONITOR",
        reference=reference,
        severity="WARNING" if condition == "LONG_RUNNING" else "CRITICAL",
        timestamp=observed,
    )
    db.add(event)
    db.flush()


def ingest_snapshot(collector, result, observed, db):
    payload = result.payload or {}
    if (
        collector.collector_type.upper() != "PENTAHO"
        or payload.get("provider") != "PENTAHO"
    ):
        return
    try:
        job_id = UUID((collector.configuration or {})["job_order_id"])
    except (KeyError, TypeError, ValueError):
        return
    job, source = db.get(JobOrder, job_id), db.get(DataSource, collector.data_source_id)
    if (
        not job
        or not source
        or job.organization_id != source.organization_id
        or not job.active
        or not job.monitoring_enabled
    ):
        return
    # Serialize all execution/schedule transitions for a Job Order.
    db.execute(select(JobOrder.id).where(JobOrder.id == job_id).with_for_update())
    # Partial inventory may still contain valid observations. Completeness only
    # authorizes absence/NO_RUN claims, not ingestion of observed executions.
    if "executions" in payload:
        records = payload["executions"]
        if not isinstance(records, list) or len(records) > 200:
            return
    else:
        records = [payload]
    for record in records:
        if not isinstance(record, dict):
            continue
        identity = record.get("execution_id")
        if not isinstance(identity, str) or not 1 <= len(identity) <= 200:
            continue
        if record.get("execution_status") not in {
            "SUCCESS",
            "FAILED",
            "RUNNING",
            "UNKNOWN",
        }:
            continue
        history = db.scalar(
            select(JobOrderHistory).where(
                JobOrderHistory.job_order_id == job_id,
                JobOrderHistory.provider_execution_id == identity,
            )
        )
        fresh = history is None
        previous = history.status.value if history else None
        if fresh:
            history = JobOrderHistory(
                job_order_id=job_id,
                provider_execution_id=identity,
                execution_type=ExecutionType.SCHEDULED,
                status=ExecutionStatus.UNKNOWN,
                detected_at=observed,
                expected_runtime_seconds=job.expected_runtime_seconds,
                sla_seconds=job.sla_seconds,
            )
            db.add(history)
        warnings = record.get("evidence_warnings") or []
        conflict = any(w.startswith("CONFLICTED") for w in warnings)
        new_start = source_time(record.get("started_at"))
        if (
            not fresh
            and history.started_at
            and new_start
            and history.started_at != new_start
        ):
            conflict = True
        if (
            previous in {"SUCCESS", "FAILED"}
            and record["execution_status"] in {"SUCCESS", "FAILED"}
            and record["execution_status"] != previous
        ):
            conflict = True
        retain_observation(db, job, collector, record, observed, conflict)
        if conflict:
            history.monitoring_conditions = {
                **(history.monitoring_conditions or {}),
                "CONFLICTING_TERMINAL_EVIDENCE": True,
            }
        # No disputed or older observation may rewrite defensible source facts.
        prior_observed = source_time((history.source_evidence or {}).get("observed_at"))
        if not fresh and (
            conflict
            or (prior_observed and observed < prior_observed)
            or (
                previous in {"SUCCESS", "FAILED"}
                and record["execution_status"] != previous
            )
        ):
            continue
        history.started_at = source_time(record.get("started_at")) or history.started_at
        history.ended_at = source_time(record.get("ended_at")) or history.ended_at
        status, sla_status = runtime_status(
            "UNKNOWN" if conflict else record["execution_status"],
            history.started_at,
            history.ended_at,
            history.expected_runtime_seconds,
            history.sla_seconds,
            observed,
        )
        history.status, history.sla_status = ExecutionStatus(status), sla_status
        history.source_result = "CARTE_READ_ONLY"
        history.source_evidence = {
            "collector_id": str(collector.id),
            "observed_at": observed.isoformat(),
            "source_status": record["execution_status"],
            "nr_errors": record.get("nr_errors"),
            "native_status_desc": record.get("native_status_desc"),
            "native_result": record.get("native_result"),
            "native_exit_status": record.get("native_exit_status"),
            "native_log_channel_id": record.get("native_log_channel_id"),
            "native_log_date_raw": record.get("native_log_date_raw"),
            "evidence_warnings": record.get("evidence_warnings", []),
            "log_evidence_status": record.get("log_evidence_status"),
            "logs": record.get("logs"),
            "policy": {
                "expected_window_start": job.expected_window_start,
                "expected_window_end": job.expected_window_end,
                "grace_seconds": job.no_run_grace_seconds,
                "timezone": (job.schedule or {}).get("timezone", "UTC"),
            },
        }
        history.source_error_code = (
            "CARTE_REPORTED_ERRORS" if record.get("nr_errors") else None
        )
        db.flush()
        existing = {
            (step.source_evidence or {}).get("observed_step_key"): step
            for step in db.scalars(
                select(JobStepExecution).where(
                    JobStepExecution.history_id == history.id
                )
            )
            if (step.source_evidence or {}).get("observed_step_key") is not None
        }
        occurrences = {}
        for index, item in enumerate(record.get("steps", [])):
            pair = (item["name"], item.get("copy"))
            ordinal = occurrences.get(pair, 0)
            occurrences[pair] = ordinal + 1
            key = step_key(item, ordinal)
            step = existing.get(key)
            if step is None:
                step = JobStepExecution(history_id=history.id, name=item["name"])
                db.add(step)
                existing[key] = step
            step.source_evidence = {
                "observed_step_key": key,
                "observed_entry_position": index,
                "identity_provenance": (
                    "NATIVE_STEP_COPY"
                    if item.get("copy") is not None
                    else "OBSERVED_ORDER_ONLY"
                ),
                "nr_errors": item.get("nr_errors"),
                "native_copy": item.get("copy"),
                "native_status_description": item.get("statusDescription"),
                "native_metrics": item.get("metrics"),
            }
            metrics = item.get("metrics") or {}
            step.records_read = metrics.get("linesRead")
            step.records_written = metrics.get("linesWritten")
            for key in ("status", "step_type", "error_code", "error_message"):
                setattr(step, key, item.get(key))
            if item["status"] == "FAILED":
                history.failed_step = item["name"]
                history.source_error_message = item.get("error_message")
        db.flush()
        if status == "FAILED" and previous != "FAILED":
            from app.services.correlation import correlate_execution

            correlate_execution(db, history.id)
    db.flush()
    histories = db.scalars(
        select(JobOrderHistory).where(
            JobOrderHistory.job_order_id == job_id,
            JobOrderHistory.source_result == "CARTE_READ_ONLY",
        )
    ).all()
    # A complete inventory identifies currently retained source executions. An
    # absent old execution remains historical evidence, not a current signal.
    identities = {record.get("execution_id") for record in records}
    candidates = [h for h in histories if h.provider_execution_id in identities]
    latest = (
        max(candidates, key=lambda h: (h.started_at or h.detected_at, h.detected_at))
        if candidates
        else None
    )
    window = expected_window(job, observed)
    if (
        payload.get("inventory_complete")
        and window
        and observed >= window[1]
        and all(h.started_at for h in histories)
    ):
        start, deadline = window
        matching = [h for h in histories if start <= h.started_at <= observed]
        identity = "opscontrol:no-run:" + start.isoformat()
        missing = db.scalar(
            select(JobOrderHistory).where(
                JobOrderHistory.job_order_id == job_id,
                JobOrderHistory.provider_execution_id == identity,
            )
        )
        if not matching and missing is None:
            missing = JobOrderHistory(
                job_order_id=job_id,
                provider_execution_id=identity,
                execution_type=ExecutionType.SCHEDULED,
                status=ExecutionStatus.NO_RUN,
                detected_at=observed,
                expected_runtime_seconds=job.expected_runtime_seconds,
                sla_seconds=job.sla_seconds,
                sla_status="UNKNOWN",
                source_result="OPSCONTROL_SCHEDULE",
                source_evidence={
                    "observed_at": observed.isoformat(),
                    "window_start": start.isoformat(),
                    "deadline": deadline.isoformat(),
                    "collector_id": str(collector.id),
                    "policy": {
                        "timezone": (job.schedule or {}).get("timezone", "UTC"),
                        "grace_seconds": job.no_run_grace_seconds,
                        "expected_window_start": job.expected_window_start,
                        "expected_window_end": job.expected_window_end,
                    },
                },
            )
            db.add(missing)
            db.flush()
        if missing:
            _alert(db, job, missing, "NO_RUN", not matching, observed)
    if latest:
        terminal_times = [
            h.started_at
            for h in histories
            if h.started_at and h.status.value in {"SUCCESS", "FAILED"}
        ]
        if (
            latest.started_at
            and terminal_times
            and latest.started_at < max(terminal_times)
        ):
            return  # an old retained execution cannot reopen a recovered condition
        # Failed runs remain historical failures; the next successful run resolves
        # the Job Order condition without altering investigations or source facts.
        latest_status = latest.status.value
        if latest_status == "UNKNOWN":
            return  # Missing/conflicted evidence cannot prove recovery.
        for condition, active in [
            ("JOB_FAILED", latest_status == "FAILED"),
            ("LONG_RUNNING", latest_status == "LONG_RUNNING"),
            ("SLA_BREACH", latest.sla_status == "BREACHED"),
        ]:
            if (
                latest_status in {"RUNNING", "LONG_RUNNING", "NO_RESPONSE"}
                and condition == "JOB_FAILED"
            ):
                continue
            _alert(db, job, latest, condition, active, observed)
    db.flush()
