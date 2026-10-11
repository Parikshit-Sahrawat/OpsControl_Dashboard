"""Read-only Carte ingestion and evidence-based daily schedule evaluation.

One local scheduler owns polling. Source failure, missing execution and poll
failure are different facts. Alert events are appended only on transitions.
"""
from datetime import datetime, timedelta, timezone, time
from uuid import UUID, uuid5, NAMESPACE_URL
from zoneinfo import ZoneInfo
from sqlalchemy import select
from app.models import (JobOrder, JobOrderHistory, JobStepExecution, DataSource,
                        ExecutionStatus, ExecutionType, AlertIncidentEvent)

def source_time(value):
    if not value: return None
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else None

def runtime_status(status, started, ended, expected, sla, observed):
    elapsed = max(0, ((ended or observed)-started).total_seconds()) if started else None
    sla_status = 'UNKNOWN' if elapsed is None or not sla else ('BREACHED' if elapsed >= sla else 'MET')
    if status == 'RUNNING':
        sla_status = 'UNKNOWN' if elapsed is None or not sla else ('BREACHED' if elapsed >= sla else 'ON_TRACK')
        if elapsed is not None and expected and elapsed >= expected: status = 'LONG_RUNNING'
    return status, sla_status

def expected_window(job, observed):
    if not job.expected_window_start or not job.expected_window_end: return None
    schedule = job.schedule or {}
    zone = ZoneInfo(schedule.get('timezone', 'UTC'))
    local = observed.astimezone(zone)
    start_time = time.fromisoformat(job.expected_window_start)
    end_time = time.fromisoformat(job.expected_window_end)
    day = local.date()
    if end_time <= start_time and local.time().replace(tzinfo=None) < start_time:
        day -= timedelta(days=1)
    if day.weekday() not in schedule.get('weekdays', list(range(7))): return None
    start = datetime.combine(day, start_time, zone)
    end = datetime.combine(day + timedelta(days=int(end_time <= start_time)), end_time, zone)
    return start.astimezone(timezone.utc), end.astimezone(timezone.utc) + timedelta(seconds=job.no_run_grace_seconds or 0)

def _alert(db, job, history, condition, active, observed):
    reference = str(uuid5(NAMESPACE_URL, f'opscontrol:etl:{job.id}:{condition}'))
    last = db.scalar(select(AlertIncidentEvent).join(JobOrderHistory).where(
        JobOrderHistory.job_order_id == job.id, AlertIncidentEvent.reference == reference
    ).order_by(AlertIncidentEvent.timestamp.desc(), AlertIncidentEvent.id.desc()).limit(1))
    was_open = last is not None and last.event_type.endswith('_OPEN')
    if active == was_open: return
    db.add(AlertIncidentEvent(history_id=history.id,
        event_type=condition + ('_OPEN' if active else '_RESOLVED'), source='ETL_MONITOR',
        reference=reference, severity='WARNING' if condition == 'LONG_RUNNING' else 'CRITICAL', timestamp=observed))

def ingest_snapshot(collector, result, observed, db):
    payload = result.payload or {}
    if collector.collector_type.upper() != 'PENTAHO' or payload.get('provider') != 'PENTAHO': return
    try: job_id = UUID((collector.configuration or {})['job_order_id'])
    except (KeyError, TypeError, ValueError): return
    job, source = db.get(JobOrder, job_id), db.get(DataSource, collector.data_source_id)
    if not job or not source or job.organization_id != source.organization_id or not job.active or not job.monitoring_enabled: return
    # Serialize all execution/schedule transitions for a Job Order.
    db.execute(select(JobOrder.id).where(JobOrder.id == job_id).with_for_update())
    records = payload.get('executions') if payload.get('inventory_complete') else [payload]
    for record in records:
        identity = record.get('execution_id')
        if not identity: continue
        history = db.scalar(select(JobOrderHistory).where(JobOrderHistory.job_order_id == job_id,
            JobOrderHistory.provider_execution_id == identity))
        fresh = history is None
        previous = history.status.value if history else None
        if fresh:
            history = JobOrderHistory(job_order_id=job_id, provider_execution_id=identity,
                execution_type=ExecutionType.SCHEDULED, detected_at=observed,
                expected_runtime_seconds=job.expected_runtime_seconds, sla_seconds=job.sla_seconds)
            db.add(history)
        # Never downgrade a terminal source result from a stale status response.
        if previous in {'SUCCESS', 'FAILED'} and record['execution_status'] != previous: continue
        history.started_at = source_time(record.get('started_at')) or history.started_at
        history.ended_at = source_time(record.get('ended_at')) or history.ended_at
        status, sla_status = runtime_status(record['execution_status'], history.started_at,
            history.ended_at, history.expected_runtime_seconds, history.sla_seconds, observed)
        history.status, history.sla_status = ExecutionStatus(status), sla_status
        history.source_result = 'CARTE_READ_ONLY'
        history.source_evidence = {'collector_id': str(collector.id), 'observed_at': observed.isoformat(),
            'source_status': record['execution_status'], 'nr_errors': record.get('nr_errors', 0),
            'logs': record.get('logs'), 'policy': {'expected_window_start': job.expected_window_start,
                'expected_window_end': job.expected_window_end, 'grace_seconds': job.no_run_grace_seconds,
                'timezone': (job.schedule or {}).get('timezone', 'UTC')}}
        history.source_error_code = 'CARTE_REPORTED_ERRORS' if record.get('nr_errors') else None
        db.flush()
        existing = {step.name: step for step in db.scalars(select(JobStepExecution).where(JobStepExecution.history_id == history.id))}
        for item in record.get('steps', []):
            step = existing.get(item['name'])
            if step is None:
                step = JobStepExecution(history_id=history.id, name=item['name']); db.add(step)
                existing[item['name']] = step
            for key in ('status', 'step_type', 'error_code', 'error_message'): setattr(step, key, item.get(key))
            if item['status'] == 'FAILED':
                history.failed_step = item['name']; history.source_error_message = item.get('error_message')
        db.flush()
        if status == 'FAILED' and previous != 'FAILED':
            from app.services.correlation import correlate_execution
            correlate_execution(db, history.id)
    db.flush()
    histories = db.scalars(select(JobOrderHistory).where(JobOrderHistory.job_order_id == job_id,
        JobOrderHistory.source_result == 'CARTE_READ_ONLY')).all()
    # A complete inventory identifies currently retained source executions. An
    # absent old execution remains historical evidence, not a current signal.
    identities = {record.get('execution_id') for record in records}
    candidates = [h for h in histories if h.provider_execution_id in identities]
    latest = max(candidates, key=lambda h: (h.started_at or h.detected_at, h.detected_at)) if candidates else None
    window = expected_window(job, observed)
    if payload.get('inventory_complete') and window and observed >= window[1] and all(h.started_at for h in histories):
        start, deadline = window
        matching = [h for h in histories if start <= h.started_at <= observed]
        identity = 'opscontrol:no-run:' + start.isoformat()
        missing = db.scalar(select(JobOrderHistory).where(JobOrderHistory.job_order_id == job_id,
            JobOrderHistory.provider_execution_id == identity))
        if not matching and missing is None:
            missing = JobOrderHistory(job_order_id=job_id, provider_execution_id=identity,
                execution_type=ExecutionType.SCHEDULED, status=ExecutionStatus.NO_RUN,
                detected_at=observed, expected_runtime_seconds=job.expected_runtime_seconds,
                sla_seconds=job.sla_seconds, sla_status='UNKNOWN', source_result='OPSCONTROL_SCHEDULE',
                source_evidence={'observed_at': observed.isoformat(), 'window_start': start.isoformat(),
                    'deadline': deadline.isoformat(), 'collector_id': str(collector.id),
                    'policy': {'timezone': (job.schedule or {}).get('timezone', 'UTC'), 'grace_seconds': job.no_run_grace_seconds,
                               'expected_window_start': job.expected_window_start, 'expected_window_end': job.expected_window_end}})
            db.add(missing); db.flush()
        if missing: _alert(db, job, missing, 'NO_RUN', not matching, observed)
    if latest:
        terminal_times = [h.started_at for h in histories if h.started_at and h.status.value in {'SUCCESS','FAILED'}]
        if latest.started_at and terminal_times and latest.started_at < max(terminal_times):
            return  # an old retained execution cannot reopen a recovered condition
        # Failed runs remain historical failures; the next successful run resolves
        # the Job Order condition without altering investigations or source facts.
        latest_status = latest.status.value
        for condition, active in [('JOB_FAILED', latest_status == 'FAILED'),
                                  ('LONG_RUNNING', latest_status == 'LONG_RUNNING'),
                                  ('SLA_BREACH', latest.sla_status == 'BREACHED')]:
            if latest_status in {'RUNNING', 'LONG_RUNNING', 'NO_RESPONSE'} and condition == 'JOB_FAILED': continue
            _alert(db, job, latest, condition, active, observed)
    db.flush()
