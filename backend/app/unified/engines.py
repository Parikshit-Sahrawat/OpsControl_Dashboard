"""Native persistent evaluation. Only observed facts can establish health/recovery."""

import hashlib, json, statistics, uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func, or_, text
from app.db.session import SessionLocal
from app.models import (
    DataSource,
    Organization,
    Collector,
    CollectorRun,
    JobOrder,
    JobOrderHistory,
    ExecutionStatus,
    MetricDefinition,
    MetricSample,
    AlertRule,
    AlertState,
)
from app.telemetry.models import (
    ManagedAgent,
    TelemetryReceipt,
    CollectorConfigVersion,
    CollectorMethod,
)
from app.worker.alert_engine import evaluate_metric_sample, _breaches
from app.unified.models import *
from app.unified.calendar import occurrences, next_occurrence
from app.unified.reconstruction import ingest_logs, ingest_connector


def utc():
    return datetime.now(timezone.utc)


def active_parameters(db, r):
    return db.scalar(
        select(ParameterVersion).where(
            ParameterVersion.resource_id == r.id, ParameterVersion.status == "ACTIVE"
        )
    )


def readable_idle_file(method, agent, configuration, observed):
    """A quiet readable tailer is available; it is not evidence of log reception."""
    if (
        method.get("method_type") != "FILE_LOG"
        or method.get("configuration", {}).get("source", "FILE") != "FILE"
    ):
        return False
    observation = (
        (agent.method_health or {}).get(str(method["id"]), {}) if agent else {}
    )
    try:
        timestamp = datetime.fromisoformat(observation.get("observed_at", ""))
        age = (observed - timestamp).total_seconds()
    except (ValueError, TypeError):
        return False
    return bool(
        configuration
        and agent.configuration_sha256 == configuration.sha256
        and observation.get("applied_revision") == configuration.revision
        and 0 <= age <= 90
        and observation.get("state") == "IDLE"
        and observation.get("sources_found", 0) > 0
        and observation.get("sources_readable") == observation.get("sources_found")
        and not observation.get("error_code")
    )


def source_readiness(db, r, observed=None):
    observed = observed or utc()
    from app.models import Organization

    customer = db.get(Organization, r.organization_id)
    if not customer or not customer.active:
        return {
            "ready": False,
            "checks": [{"name": "Customer active", "passed": False}],
            "reason": "CUSTOMER_INACTIVE",
        }
    checks = []
    if r.domain == "ETL" and r.linked_vm_id and not r.primary_collector_id:
        parent = db.scalar(
            select(MonitoringResource).where(MonitoringResource.vm_id == r.linked_vm_id)
        )
        if not parent:
            return {
                "ready": False,
                "checks": [{"name": "VM relationship", "passed": False}],
                "reason": "UNMAPPED_VM",
            }
        result = source_readiness(db, parent, observed)
        paths = r.configuration.get("log_paths", [])
        cfg = (
            db.scalar(
                select(CollectorConfigVersion)
                .join(
                    ManagedAgent,
                    ManagedAgent.collector_id == CollectorConfigVersion.collector_id,
                )
                .where(
                    ManagedAgent.collector_id == parent.primary_collector_id,
                    CollectorConfigVersion.revision == ManagedAgent.applied_revision,
                )
            )
            if parent.primary_collector_id
            else None
        )
        configured = {
            p
            for m in (cfg.method_snapshot if cfg else [])
            if m.get("enabled") and m.get("method_type") == "FILE_LOG"
            for p in m["configuration"].get("paths", [])
        }
        result["checks"] = list(result["checks"]) + [
            {
                "name": "ETL log paths applied",
                "passed": all(p in configured for p in paths),
            }
        ]
        result["ready"] = all(c["passed"] for c in result["checks"])
        return result
    if r.domain in {"API", "ETL"}:
        c = (
            db.get(Collector, r.primary_collector_id)
            if r.primary_collector_id
            else None
        )
        source = db.get(DataSource, r.data_source_id) if r.data_source_id else None
        run = (
            db.scalar(
                select(CollectorRun)
                .where(CollectorRun.collector_id == c.id)
                .order_by(CollectorRun.started_at.desc(), CollectorRun.id)
                .limit(1)
            )
            if c
            else None
        )
        accepted = bool(
            run
            and run.outcome
            in {"SUCCESS", "ASSERTION_FAILED", "TIMEOUT", "NETWORK_ERROR"}
        )
        if r.domain == "ETL":
            accepted = bool(
                run
                and run.status == "SUCCESS"
                and (run.source_metadata or {}).get("inventory_complete")
            )
        recent = bool(
            run
            and run.ended_at
            and observed - run.ended_at
            <= timedelta(seconds=max(120, c.interval_seconds * 3))
        )
        checks = [
            {
                "name": "Approved collector enabled",
                "passed": bool(c and c.enabled and source and source.enabled),
            },
            {
                "name": "Real recent provider/probe observation",
                "passed": accepted and recent,
            },
        ]
        return {
            "ready": all(c["passed"] for c in checks),
            "checks": checks,
            "last_received_at": run.ended_at if run else None,
            "reason": (
                "VERIFIED"
                if all(c["passed"] for c in checks)
                else "NO_VERIFIED_SOURCE_EVIDENCE"
            ),
        }
    c = db.get(Collector, r.primary_collector_id) if r.primary_collector_id else None
    a = (
        db.scalar(select(ManagedAgent).where(ManagedAgent.collector_id == c.id))
        if c
        else None
    )
    cfg = (
        db.scalar(
            select(CollectorConfigVersion).where(
                CollectorConfigVersion.collector_id == c.id,
                CollectorConfigVersion.revision == a.applied_revision,
            )
        )
        if a and a.applied_revision
        else None
    )
    connected = bool(
        c
        and c.enabled
        and a
        and a.enabled
        and a.last_seen_at
        and observed - a.last_seen_at <= timedelta(seconds=90)
        and a.health == "RUNNING"
    )
    desired_methods = (
        db.scalars(
            select(CollectorMethod).where(CollectorMethod.collector_id == c.id)
        ).all()
        if c
        else []
    )
    applied_methods = {str(m["id"]): m for m in cfg.method_snapshot} if cfg else {}
    configuration_current = (
        bool(cfg)
        and len(desired_methods) == len(applied_methods)
        and all(
            str(m.id) in applied_methods
            and m.revision == applied_methods[str(m.id)].get("revision")
            and m.enabled == applied_methods[str(m.id)].get("enabled")
            for m in desired_methods
        )
    )
    desired_agent = (c.configuration or {}) if c else {}
    applied_methods_enabled = [
        m for m in (cfg.method_snapshot if cfg else []) if m.get("enabled")
    ]
    expected_services = sorted(
        set(desired_agent.get("services", []))
        | {
            name
            for m in applied_methods_enabled
            if m["method_type"] == "SERVICES"
            for name in m["configuration"].get("services", [])
        }
    )
    expected_processes = sorted(
        set(desired_agent.get("processes", []))
        | {
            name
            for m in applied_methods_enabled
            if m["method_type"] == "SERVICES"
            for name in m["configuration"].get("processes", [])
        }
    )
    expected_metrics = bool(
        desired_agent.get("os_metrics")
        or any(m["method_type"] == "HOST_METRICS" for m in applied_methods_enabled)
    )
    configuration_current = (
        configuration_current
        and bool(cfg)
        and sorted((cfg.agent_configuration or {}).get("services", []))
        == expected_services
        and sorted((cfg.agent_configuration or {}).get("processes", []))
        == expected_processes
        and bool((cfg.agent_configuration or {}).get("native_os_metrics"))
        == expected_metrics
    )
    checks = [
        {
            "name": "Desired configuration matches applied revision",
            "passed": configuration_current,
        },
        {"name": "Authenticated agent heartbeat/runtime", "passed": connected},
        {
            "name": "Validated configuration actually applied",
            "passed": bool(cfg and cfg.validation_status == "VALIDATED"),
        },
    ]
    enabled_methods = [
        m for m in (cfg.method_snapshot if cfg else []) if m.get("enabled")
    ]
    signals = (
        {"metrics"}
        if ((c.configuration if c else {}) or {}).get("os_metrics")
        else set()
    )
    for m in cfg.method_snapshot if cfg else []:
        if m.get("enabled"):
            if m["method_type"] in {"FILE_LOG", "SYSLOG_RECEIVER"}:
                signals.add("logs")
            elif m["method_type"] in {"METRIC_SCRAPE", "HOST_METRICS", "SERVICES"}:
                signals.add("metrics")
            elif m["method_type"] == "OTLP_RECEIVER":
                signals.update(s.lower() for s in m["configuration"]["signals"])
    last = None
    for signal in sorted(signals):
        receipt = (
            db.scalar(
                select(func.max(TelemetryReceipt.received_at)).where(
                    TelemetryReceipt.agent_id == a.id, TelemetryReceipt.signal == signal
                )
            )
            if a
            else None
        )
        received = bool(
            receipt
            and a.applied_at
            and a.applied_at <= receipt <= observed
            and observed - receipt <= timedelta(seconds=120)
        )
        log_methods = [
            m
            for m in enabled_methods
            if m["method_type"] in {"FILE_LOG", "SYSLOG_RECEIVER"}
            or (
                m["method_type"] == "OTLP_RECEIVER"
                and "Logs" in m["configuration"]["signals"]
            )
        ]
        idle = bool(
            signal == "logs"
            and connected
            and configuration_current
            and log_methods
            and all(readable_idle_file(m, a, cfg, observed) for m in log_methods)
        )
        checks.append(
            {
                "name": (
                    "Actual " + signal + " reception"
                    if not idle or received
                    else "Readable quiet File Logs (IDLE; no receipt)"
                ),
                "passed": received or idle,
                "state": "RECEIVING" if received else "IDLE" if idle else "NO_DATA",
                "last_received_at": receipt,
            }
        )
        if receipt:
            last = max(last, receipt) if last else receipt
    if not signals:
        checks.append(
            {"name": "At least one explicit telemetry signal", "passed": False}
        )
    observations = [
        ("services", "opscontrol.service.up", "service.name"),
        ("processes", "opscontrol.process.count", "process.name"),
    ]
    for kind, metric_name, dimension in observations:
        for service in (cfg.agent_configuration if cfg else {}).get(kind, []):
            point = db.scalar(
                select(MetricSample)
                .join(MetricDefinition)
                .where(
                    MetricDefinition.collector_id == c.id,
                    MetricDefinition.query_config["otel_metric_name"].as_string()
                    == metric_name,
                    MetricSample.dimensions[dimension].as_string() == service,
                )
                .order_by(MetricSample.observed_at.desc())
                .limit(1)
            )
            # A service being down is valid evidence, not absent instrumentation.
            checks.append(
                {
                    "name": "Observed " + kind + " " + service,
                    "passed": bool(
                        point and observed - point.observed_at <= timedelta(seconds=120)
                    ),
                }
            )
    return {
        "ready": all(c["passed"] for c in checks),
        "checks": checks,
        "last_received_at": last,
        "reason": (
            "VERIFIED"
            if all(c["passed"] for c in checks)
            else "MISSING_AGENT_OR_TELEMETRY"
        ),
    }


def condition(db, r, key, type, active, severity, message, evidence, observed):
    row = db.scalar(
        select(ResourceCondition).where(
            ResourceCondition.resource_id == r.id,
            ResourceCondition.condition_key == key,
        )
    )
    if row and row.last_observed_at > observed:
        return row
    changed = (
        row is None or row.active != active or (active and row.severity != severity)
    )
    if row is None:
        row = ResourceCondition(
            organization_id=r.organization_id,
            resource_id=r.id,
            condition_key=key,
            condition_type=type,
            active=active,
            severity=severity,
            message=message,
            first_observed_at=observed,
            last_observed_at=observed,
            evidence=evidence,
        )
        db.add(row)
    else:
        if active and not row.active:
            row.first_observed_at = observed
            row.resolved_at = None
        row.active = active
        row.severity = severity
        row.message = message
        row.last_observed_at = observed
        row.evidence = evidence
    if not active:
        row.resolved_at = observed
    setup = (r.configuration or {}).get("alert_setup") or {}
    current_version = active_parameters(db, r)
    alert_enabled = bool(
        setup.get("enabled")
        and current_version
        and setup.get("parameter_version") == current_version.version
        and severity in setup.get("severities", [])
    )
    pending_recovery = bool(
        not active
        and row.alert_state_id
        and (state := db.get(AlertState, row.alert_state_id))
        and state.status == "OPEN"
    )
    if alert_enabled and (changed or active or pending_recovery):
        name = (
            "native-condition:"
            + str(r.id)
            + ":"
            + hashlib.sha256(key.encode()).hexdigest()[:20]
        )
        metric = db.scalar(
            select(MetricDefinition).where(
                MetricDefinition.organization_id == r.organization_id,
                MetricDefinition.name == name,
            )
        )
        if metric is None:
            metric = MetricDefinition(
                organization_id=r.organization_id,
                name=name,
                resource_type=r.domain,
                resource_id=r.id,
                metric_type="DERIVED_CONDITION",
                unit="1",
                query_config={"condition_type": type, "native_resource_id": str(r.id)},
            )
            db.add(metric)
            db.flush()
        rule_name = (
            r.name[:60]
            + ": "
            + message[:100]
            + " ["
            + hashlib.sha256((str(r.id) + ":" + key).encode()).hexdigest()[:16]
            + "]"
        )
        rule = db.scalar(
            select(AlertRule).where(AlertRule.metric_definition_id == metric.id)
        )
        if rule is None:
            rule = AlertRule(
                organization_id=r.organization_id,
                metric_definition_id=metric.id,
                name=rule_name,
                severity=severity,
                operator="GT",
                threshold_value="0.5",
                consecutive_breaches=1,
                notification_channels=(["IN_APP"] if setup.get("in_app") else [])
                + ["DEST:" + str(v) for v in setup.get("destinations", [])],
            )
            db.add(rule)
            db.flush()
        rule.enabled = True
        rule.notification_channels = (["IN_APP"] if setup.get("in_app") else []) + [
            "DEST:" + str(value) for value in setup.get("destinations", [])
        ]
        rule.severity = severity
        rule.name = rule_name
        sample = MetricSample(
            organization_id=r.organization_id,
            metric_definition_id=metric.id,
            observed_at=observed,
            value_numeric=1 if active else 0,
            unit="1",
            dimensions={"derived_from": evidence, "resource_id": str(r.id)},
        )
        db.add(sample)
        db.flush()
        state = evaluate_metric_sample(db, sample)
        if state:
            row.alert_state_id = state.id
    db.flush()
    return row


def evaluate_schedule(db, r, p, observed):
    if r.configuration.get("platform") == "PENTAHO":
        from app.unified.pentaho_schedule import evaluate

        return evaluate(db, r, p, observed)
    config = p.configuration
    schedule = config.get("schedule")
    if not schedule:
        return
    start = r.schedule_watermark or max(r.created_at, p.created_at)
    values = list(occurrences(schedule, start, observed, limit=200))
    for scheduled in values:
        exists = db.scalar(
            select(ExpectedExecutionWindow).where(
                ExpectedExecutionWindow.resource_id == r.id,
                ExpectedExecutionWindow.scheduled_at == scheduled,
            )
        )
        if not exists:
            db.add(
                ExpectedExecutionWindow(
                    organization_id=r.organization_id,
                    resource_id=r.id,
                    scheduled_at=scheduled,
                    deadline=scheduled
                    + timedelta(seconds=config["no_run_grace_seconds"]),
                    parameter_version=p.version,
                )
            )
    # Do not jump the watermark over a capped backlog. Restart catches up in
    # durable batches instead of losing expected executions.
    r.schedule_watermark = values[-1] if len(values) == 200 else observed
    db.flush()
    readiness = source_readiness(db, r, observed)
    windows = db.scalars(
        select(ExpectedExecutionWindow)
        .where(
            ExpectedExecutionWindow.resource_id == r.id,
            ExpectedExecutionWindow.scheduled_at <= observed,
            ExpectedExecutionWindow.status.in_(
                ["EXPECTED", "NO_RUN", "UNKNOWN", "BLOCKED"]
            ),
        )
        .order_by(
            ExpectedExecutionWindow.evaluated_at.nullsfirst(),
            ExpectedExecutionWindow.scheduled_at,
        )
        .limit(200)
    ).all()
    for window in windows:
        # Preserve the schedule version that created an expectation.
        version = (
            db.scalar(
                select(ParameterVersion).where(
                    ParameterVersion.resource_id == r.id,
                    ParameterVersion.version == window.parameter_version,
                )
            )
            or p
        )
        next_start = next_occurrence(
            version.configuration["schedule"], window.scheduled_at
        )
        query = select(JobOrderHistory).where(
            JobOrderHistory.job_order_id == r.job_order_id,
            JobOrderHistory.execution_type == "SCHEDULED",
            JobOrderHistory.started_at >= window.scheduled_at,
        )
        if next_start:
            query = query.where(JobOrderHistory.started_at < next_start)
        run = db.scalar(query.order_by(JobOrderHistory.started_at).limit(1))
        window.evaluated_at = observed
        if run:
            late = (
                run.started_at - window.scheduled_at
            ).total_seconds() > version.configuration["delayed_start_seconds"]
            window.history_id = run.id
            window.status = "DELAYED" if late else "STARTED"
            window.evidence = {
                "actual_start": run.started_at.isoformat(),
                "execution_id": str(run.id),
                "source_evidence": True,
            }
            condition(
                db,
                r,
                "NO_RUN",
                "NO_RUN",
                False,
                "CRITICAL",
                "Expected execution started",
                {"window_id": str(window.id), "execution_id": str(run.id)},
                run.started_at,
            )
            condition(
                db,
                r,
                "DELAYED",
                "DELAYED",
                late and run.ended_at is None,
                "WARNING",
                "Scheduled execution started late",
                window.evidence,
                run.started_at,
            )
            condition(
                db,
                r,
                "DEPENDENCY_BLOCKED",
                "DEPENDENCY_BLOCKED",
                False,
                "WARNING",
                "Execution dependency condition recovered",
                window.evidence,
                run.started_at,
            )
        elif observed >= window.deadline:
            dependencies = db.scalars(
                select(ResourceDependency).where(
                    ResourceDependency.resource_id == r.id,
                    ResourceDependency.valid_to.is_(None),
                    ResourceDependency.relationship_type.in_(
                        ["DEPENDS_ON", "REQUIRES_SERVICE"]
                    ),
                )
            ).all()
            blocked = []
            if version.configuration["require_dependencies"]:
                for dependency in dependencies:
                    query = select(ResourceCondition).where(
                        ResourceCondition.resource_id == dependency.depends_on_id,
                        ResourceCondition.active.is_(True),
                    )
                    if dependency.service_identity:
                        query = query.where(
                            ResourceCondition.evidence["service_identity"].astext
                            == dependency.service_identity
                        )
                    blocked.extend(str(c.id) for c in db.scalars(query).all())
            if not readiness["ready"]:
                window.status = "UNKNOWN"
                window.evidence = {
                    "reason": "SOURCE_TELEMETRY_UNAVAILABLE",
                    "readiness": json_safe(readiness),
                }
            elif blocked:
                window.status = "BLOCKED"
                window.evidence = {"dependency_condition_ids": blocked}
                condition(
                    db,
                    r,
                    "DEPENDENCY_BLOCKED",
                    "DEPENDENCY_BLOCKED",
                    True,
                    "WARNING",
                    "Execution is blocked by an observed dependency condition",
                    {"window_id": str(window.id), "condition_ids": blocked},
                    observed,
                )
            else:
                condition(
                    db,
                    r,
                    "DEPENDENCY_BLOCKED",
                    "DEPENDENCY_BLOCKED",
                    False,
                    "WARNING",
                    "Observed dependency condition recovered",
                    {"window_id": str(window.id)},
                    observed,
                )
                window.status = "NO_RUN"
                window.evidence = {
                    "source_verified": True,
                    "deadline": window.deadline.isoformat(),
                }
                condition(
                    db,
                    r,
                    "NO_RUN",
                    "NO_RUN",
                    True,
                    "CRITICAL",
                    "No execution observed in the expected schedule window",
                    {
                        "window_id": str(window.id),
                        "deadline": window.deadline.isoformat(),
                    },
                    window.deadline,
                )


def json_safe(value):
    return json.loads(json.dumps(value, default=str))


def evaluate_executions(db, r, p, observed):
    if getattr(r, "configuration", {}).get("platform") == "PENTAHO":
        from app.unified.pentaho_history import reconcile

        reconcile(db, r, observed)
    cfg = p.configuration
    histories = db.scalars(
        select(JobOrderHistory)
        .where(JobOrderHistory.job_order_id == r.job_order_id)
        .order_by(JobOrderHistory.created_at.desc())
        .limit(200)
    ).all()
    readiness = source_readiness(db, r, observed)
    condition(
        db,
        r,
        "ETL_TELEMETRY",
        "TELEMETRY_UNKNOWN",
        not readiness["ready"],
        "WARNING",
        "Execution telemetry is unavailable; job failure is not inferred",
        json_safe(readiness),
        observed,
    )
    for h in histories:
        if getattr(h, "pentaho_resource_id", None) and (
            getattr(h, "pentaho_review_state", None)
            in {"CONFLICTED_EVIDENCE", "REVIEW_REQUIRED"}
            or (h.source_evidence or {})
            .get("pentaho_historical", {})
            .get("operational_reassessment_required")
            or (h.source_evidence or {})
            .get("pentaho_adjudication", {})
            .get("operational_reassessment_required")
        ):
            # Keep the last defensible operational conditions. Review is neither
            # failure nor recovery; historical incident/notification policy is a
            # separate, explicit eligibility gate (Sprint 05).
            continue
        if not h.started_at:
            if h.status in {ExecutionStatus.SUCCESS, ExecutionStatus.FAILED}:
                condition(
                    db,
                    r,
                    "ETL_FAILURE",
                    "ETL_FAILURE",
                    h.status == ExecutionStatus.FAILED,
                    "CRITICAL",
                    "Terminal provider status observed; duration unknown",
                    {
                        "execution_id": str(h.id),
                        "source_evidence": h.source_evidence,
                        "observed_duration_seconds": None,
                    },
                    observed,
                )
                h.sla_status = "UNKNOWN"
            continue
        terminal = (
            h.pentaho_lifecycle == "TERMINAL"
            if h.pentaho_lifecycle is not None
            else h.status in {ExecutionStatus.SUCCESS, ExecutionStatus.FAILED}
        )
        duration = ((h.ended_at or observed) - h.started_at).total_seconds()
        long = (
            not terminal
            and h.status in {ExecutionStatus.RUNNING, ExecutionStatus.LONG_RUNNING}
            and duration >= cfg["long_running_seconds"]
        )
        sla = (not terminal or h.ended_at is not None) and duration >= cfg[
            "completion_sla_seconds"
        ]
        if h.pentaho_outcome in {"CANCELLED", "UNKNOWN"}:
            sla = False  # No success/SLA assertion from a cancelled/unknown native run.
        h.sla_status = (
            "UNKNOWN"
            if h.pentaho_outcome in {"CANCELLED", "UNKNOWN"}
            else "BREACHED" if sla else "MET" if terminal else "ON_TRACK"
        )
        last = __import__("datetime").datetime.fromisoformat(
            (h.source_evidence or {}).get("observed_at", h.started_at.isoformat())
        )
        stale = (
            not terminal
            and (observed - last).total_seconds() > cfg["no_response_seconds"]
        )
        h.monitoring_conditions = {
            **(h.monitoring_conditions or {}),
            "LONG_RUNNING": long,
            "SLA_BREACHED": sla,
            "NO_RESPONSE": stale and readiness["ready"],
            "TELEMETRY_UNKNOWN": stale and not readiness["ready"],
        }
        evidence = {
            "execution_id": str(h.id),
            "observed_duration_seconds": duration,
            "source_evidence": h.source_evidence,
        }
        condition(
            db,
            r,
            "LONG_RUNNING:" + str(h.id),
            "LONG_RUNNING",
            long,
            "WARNING",
            "Execution exceeded its expected duration",
            evidence,
            h.ended_at or observed,
        )
        condition(
            db,
            r,
            "NO_RESPONSE:" + str(h.id),
            "NO_RESPONSE",
            stale and readiness["ready"],
            "WARNING",
            "Execution has no recent status event despite a verified telemetry path",
            evidence,
            h.ended_at or observed,
        )
        if terminal:
            if h.status not in {ExecutionStatus.SUCCESS, ExecutionStatus.FAILED}:
                continue
            condition(
                db,
                r,
                "ETL_FAILURE",
                "ETL_FAILURE",
                h.status == ExecutionStatus.FAILED,
                "CRITICAL",
                (
                    "Execution failed"
                    if h.status == ExecutionStatus.FAILED
                    else "Execution failure condition recovered"
                ),
                evidence,
                h.ended_at or last,
            )
            condition(
                db,
                r,
                "SLA_BREACH",
                "SLA_BREACH",
                sla,
                "WARNING",
                "Completion SLA exceeded",
                evidence,
                h.ended_at or last,
            )
        else:
            condition(
                db,
                r,
                "SLA_BREACH:" + str(h.id),
                "SLA_BREACH",
                sla,
                "CRITICAL",
                "Running execution exceeded completion SLA",
                evidence,
                observed,
            )


def evaluate_vm(db, r, p, observed):
    config = p.configuration
    ready = source_readiness(db, r, observed)
    condition(
        db,
        r,
        "COLLECTOR_HEALTH",
        "COLLECTOR_HEALTH",
        not ready["ready"],
        "WARNING",
        "Collector or required telemetry is unavailable",
        json_safe(ready),
        observed,
    )
    metrics = (
        db.scalars(
            select(MetricDefinition).where(
                MetricDefinition.organization_id == r.organization_id,
                MetricDefinition.data_source_id == r.data_source_id,
                MetricDefinition.metric_type != "DERIVED_CONDITION",
            )
        ).all()
        if r.data_source_id
        else []
    )
    activation = db.scalar(
        select(ParameterActivation).where(
            ParameterActivation.resource_id == r.id,
            ParameterActivation.effective_to.is_(None),
        )
    )
    mapping_grace_expired = bool(
        activation
        and observed - activation.effective_from
        >= timedelta(seconds=config["missing_telemetry_seconds"])
    )
    for spec in config["thresholds"]:
        matched = [
            m
            for m in metrics
            if (
                str(m.id) == spec["metric_definition_id"]
                if spec.get("metric_definition_id")
                else (
                    m.name == spec["metric_name"]
                    or (m.query_config or {}).get("otel_metric_name")
                    == spec["metric_name"]
                )
            )
        ]
        mapping_key = (
            "METRIC_MAPPING:"
            + hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()[:20]
        )
        condition(
            db,
            r,
            mapping_key,
            "MISSING_METRIC",
            not matched and mapping_grace_expired,
            "WARNING",
            "Configured metric has no observed matching series",
            {"metric_name": spec["metric_name"], "expected_unit": spec["unit"]},
            observed,
        )
        for metric in matched:
            if metric.unit != spec["unit"]:
                condition(
                    db,
                    r,
                    "METRIC_UNIT:" + str(metric.id),
                    "METRIC_UNIT_MISMATCH",
                    True,
                    "WARNING",
                    "Observed metric unit does not match the activated rule",
                    {
                        "metric_id": str(metric.id),
                        "expected_unit": spec["unit"],
                        "observed_unit": metric.unit,
                    },
                    observed,
                )
                continue
            points = db.scalars(
                select(MetricSample)
                .where(
                    MetricSample.metric_definition_id == metric.id,
                    MetricSample.observed_at <= observed,
                    MetricSample.observed_at
                    >= observed
                    - timedelta(
                        seconds=max(
                            spec["duration_seconds"] + spec["maximum_gap_seconds"],
                            spec["baseline_minutes"] * 60,
                        )
                    ),
                )
                .order_by(MetricSample.observed_at.desc())
                .limit(10001)
            ).all()
            missing = (
                not points
                or len(points) > 10000
                or observed - points[0].observed_at
                > timedelta(seconds=config["missing_telemetry_seconds"])
            )
            condition(
                db,
                r,
                "METRIC_MISSING:" + str(metric.id),
                "MISSING_METRIC",
                missing and mapping_grace_expired,
                "WARNING",
                "Configured metric has no recent usable observation",
                {
                    "metric_definition_id": str(metric.id),
                    "last_sample_id": str(points[0].id) if points else None,
                },
                observed,
            )
            if missing:
                continue
            unit_mismatch = points[0].unit != spec["unit"]
            condition(
                db,
                r,
                "METRIC_UNIT:" + str(metric.id),
                "METRIC_UNIT_MISMATCH",
                unit_mismatch,
                "WARNING",
                "Observed metric unit does not match the activated rule",
                {
                    "metric_id": str(metric.id),
                    "expected_unit": spec["unit"],
                    "observed_unit": points[0].unit,
                },
                observed,
            )
            if unit_mismatch:
                continue
            baseline = [
                s.value_numeric
                for s in points
                if s.observed_at
                < points[0].observed_at - timedelta(seconds=spec["duration_seconds"])
            ]
            dynamic = None
            if (
                spec["threshold_mode"] != "STATIC"
                and len(baseline) >= spec["baseline_minimum_samples"]
            ):
                dynamic = statistics.mean(baseline) + (
                    1 if spec["operator"] in {"GT", "GTE"} else -1
                ) * spec["standard_deviations"] * statistics.pstdev(baseline)
            if spec["threshold_mode"] != "STATIC" and dynamic is None:
                continue
            for severity, static in [
                ("WARNING", spec["warning"]),
                ("CRITICAL", spec["critical"]),
            ]:
                if static is None:
                    continue
                threshold = (
                    static
                    if dynamic is None
                    else (
                        dynamic
                        if spec["threshold_mode"] == "DYNAMIC"
                        else (
                            max(static, dynamic)
                            if spec["operator"] in {"GT", "GTE"}
                            else min(static, dynamic)
                        )
                    )
                )
                breached = []
                for point in points:
                    if not _breaches(point.value_numeric, spec["operator"], threshold):
                        break
                    breached.append(point)
                duration_ok = bool(
                    breached
                    and (
                        breached[0].observed_at - breached[-1].observed_at
                    ).total_seconds()
                    >= spec["duration_seconds"]
                )
                gap_ok = all(
                    (a.observed_at - b.observed_at).total_seconds()
                    <= spec["maximum_gap_seconds"]
                    for a, b in zip(breached, breached[1:])
                )
                active = (
                    len(breached) >= spec["consecutive_breaches"]
                    and duration_ok
                    and gap_ok
                )
                key = "METRIC:" + str(metric.id) + ":" + severity
                previous = db.scalar(
                    select(ResourceCondition).where(
                        ResourceCondition.resource_id == r.id,
                        ResourceCondition.condition_key == key,
                    )
                )
                if previous and previous.active and not active:
                    recovery = (
                        spec["recovery"] if spec["recovery"] is not None else threshold
                    )
                    # Hysteresis requires actual non-breaching recovery evidence.
                    active = _breaches(
                        points[0].value_numeric, spec["operator"], recovery
                    )
                condition(
                    db,
                    r,
                    key,
                    "METRIC_THRESHOLD",
                    active,
                    severity,
                    spec["metric_name"] + " " + severity.lower() + " threshold",
                    {
                        "metric_definition_id": str(metric.id),
                        "metric_sample_id": str(points[0].id),
                        "threshold": threshold,
                        "unit": spec["unit"],
                    },
                    points[0].observed_at,
                )
    monitored = [
        (name, "opscontrol.service.up", "service.name", "SERVICE", "SERVICE_DOWN")
        for name in config["services"]
    ]
    monitored += [
        (name, "opscontrol.process.count", "process.name", "PROCESS", "PROCESS_DOWN")
        for name in config.get("processes", [])
    ]
    for service, metric_name, dimension, prefix, condition_type in monitored:
        series = [
            m
            for m in metrics
            if (m.query_config or {}).get("otel_metric_name") == metric_name
        ]
        ids = [m.id for m in series]
        points = (
            db.scalars(
                select(MetricSample)
                .where(
                    MetricSample.metric_definition_id.in_(ids),
                    MetricSample.dimensions[dimension].as_string() == service,
                    MetricSample.observed_at <= observed,
                )
                .order_by(MetricSample.observed_at.desc())
                .limit(config["service_failures"])
            ).all()
            if ids
            else []
        )
        if not points or observed - points[0].observed_at > timedelta(
            seconds=config["missing_telemetry_seconds"]
        ):
            continue
        active = len(points) >= config["service_failures"] and all(
            s.value_numeric == 0 for s in points
        )
        condition(
            db,
            r,
            prefix + ":" + service,
            condition_type,
            active,
            "CRITICAL",
            prefix.title() + " " + service + " is not running",
            {"service_identity": service, "sample_ids": [str(s.id) for s in points]},
            points[0].observed_at,
        )


def evaluate_api(db, r, p, observed):
    cfg = p.configuration
    runs = (
        db.scalars(
            select(CollectorRun)
            .where(
                CollectorRun.collector_id == r.primary_collector_id,
                CollectorRun.ended_at <= observed,
            )
            .order_by(CollectorRun.ended_at.desc(), CollectorRun.id)
            .limit(max(cfg["consecutive_failures"], cfg["recovery_successes"], 100))
        ).all()
        if r.primary_collector_id
        else []
    )
    if not runs:
        return
    # Native probes snapshot the active policy at measurement time. Never
    # reinterpret historical results under a newly activated assertion.
    native = db.get(Collector, r.primary_collector_id)
    native_policy = native and native.collector_type == "NATIVE_API"
    activation = db.scalar(
        select(ParameterActivation).where(
            ParameterActivation.resource_id == r.id,
            ParameterActivation.parameter_version == p.version,
            ParameterActivation.effective_to.is_(None),
        )
    )
    valid = [
        run
        for run in runs
        if run.outcome in {"SUCCESS", "ASSERTION_FAILED", "TIMEOUT", "NETWORK_ERROR"}
        and (
            not native_policy
            or (
                (run.source_metadata or {}).get("policy_version") == p.version
                and activation
                and run.ended_at >= activation.effective_from
            )
        )
    ]
    # Consecutive observations must not bridge an outage or configuration error.
    consecutive = []
    for run in valid:
        if (
            consecutive
            and (consecutive[-1].ended_at - run.ended_at).total_seconds()
            > cfg["missing_results_seconds"]
        ):
            break
        if any(
            run.ended_at < invalid.ended_at < valid[0].ended_at
            for invalid in runs
            if invalid not in valid
        ):
            break
        consecutive.append(run)
    valid = consecutive
    if not valid:
        return
    latest = valid[0]
    missing = observed - latest.ended_at > timedelta(
        seconds=cfg["missing_results_seconds"]
    )
    condition(
        db,
        r,
        "MISSING_PROBE",
        "MISSING_PROBE",
        missing,
        "WARNING",
        "Recent API probe evidence is missing",
        {"last_run_id": str(latest.id)},
        observed,
    )
    good = lambda run: (
        run.outcome == "SUCCESS"
        if native_policy
        else run.http_status in cfg["expected_statuses"]
        and run.outcome not in {"TIMEOUT", "NETWORK_ERROR"}
    )
    head = []
    for run in valid:
        if good(run):
            break
        head.append(run)
    active = len(head) >= cfg["consecutive_failures"]
    previous = db.scalar(
        select(ResourceCondition).where(
            ResourceCondition.resource_id == r.id,
            ResourceCondition.condition_key == "API_AVAILABILITY",
        )
    )
    successes = []
    for run in valid:
        if not good(run):
            break
        successes.append(run)
    if previous and previous.active and len(successes) < cfg["recovery_successes"]:
        active = True
    condition(
        db,
        r,
        "API_AVAILABILITY",
        "API_UNAVAILABLE",
        active,
        "CRITICAL",
        "Endpoint availability assertion failed",
        {
            "run_ids": [str(x.id) for x in head] or [str(latest.id)],
            "http_status": latest.http_status,
        },
        latest.ended_at,
    )
    latency = latest.response_time_ms
    if latency is not None:
        for severity, threshold in [
            ("WARNING", cfg["warning_latency_ms"]),
            ("CRITICAL", cfg["critical_latency_ms"]),
        ]:
            consecutive = [
                run
                for run in valid[: cfg["consecutive_failures"]]
                if (run.response_time_ms or 0) > threshold
            ]
            condition(
                db,
                r,
                "API_LATENCY:" + severity,
                "API_LATENCY",
                len(consecutive) >= cfg["consecutive_failures"],
                severity,
                "Endpoint latency exceeds " + str(threshold) + " ms",
                {"run_id": str(latest.id), "response_time_ms": latency},
                latest.ended_at,
            )
    window = db.scalars(
        select(CollectorRun).where(
            CollectorRun.collector_id == r.primary_collector_id,
            CollectorRun.ended_at
            >= observed - timedelta(minutes=cfg["sla_window_minutes"]),
            CollectorRun.ended_at <= observed,
        )
    ).all()
    observed_window = [
        run
        for run in window
        if run.outcome in {"SUCCESS", "ASSERTION_FAILED", "TIMEOUT", "NETWORK_ERROR"}
        and (
            not native_policy
            or (run.source_metadata or {}).get("policy_version") == p.version
        )
    ]
    if observed_window:
        availability = (
            100 * sum(good(run) for run in observed_window) / len(observed_window)
        )
        condition(
            db,
            r,
            "API_SLA",
            "API_SLA",
            availability < cfg["availability_percent"],
            "WARNING",
            "Observed API availability is below configured SLA",
            {
                "sample_count": len(observed_window),
                "availability_percent": availability,
                "observation_weighting": "PER_COMPLETED_PROBE",
            },
            latest.ended_at,
        )


def correlate(db, organization_id, environment, observed):
    # A resource lease alone does not serialize a group shared by many resources.
    # Skip a busy group rather than deadlocking workers holding different roots.
    key = "arch001-correlation:" + str(organization_id) + ":" + environment
    if not db.scalar(
        text("SELECT pg_try_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": key},
    ):
        return
    roots = db.scalars(
        select(MonitoringResource).where(
            MonitoringResource.organization_id == organization_id,
            MonitoringResource.environment == environment,
        )
    ).all()
    ids = [r.id for r in roots]
    active = db.scalars(
        select(ResourceCondition).where(
            ResourceCondition.resource_id.in_(ids), ResourceCondition.active.is_(True)
        )
    ).all()
    by_resource = {}
    for c in active:
        by_resource.setdefault(c.resource_id, []).append(c)
    links = db.scalars(
        select(ResourceDependency).where(
            ResourceDependency.organization_id == organization_id,
            ResourceDependency.valid_to.is_(None),
            ResourceDependency.resource_id.in_(ids),
            ResourceDependency.depends_on_id.in_(ids),
        )
    ).all()
    current = set()
    for link in links:
        parents = [
            c
            for c in by_resource.get(link.depends_on_id, [])
            if not link.service_identity
            or c.evidence.get("service_identity") == link.service_identity
        ]
        for parent in parents:
            children = [
                c
                for c in by_resource.get(link.resource_id, [])
                if abs((c.first_observed_at - parent.first_observed_at).total_seconds())
                <= 3600
            ]
            if not children:
                continue
            key = (
                "dependency:"
                + str(link.id)
                + ":"
                + str(parent.alert_state_id or parent.id)
            )
            group = db.scalar(
                select(EventCorrelationGroup).where(
                    EventCorrelationGroup.group_key == key
                )
            )
            evidence = {
                "relationship_id": str(link.id),
                "relationship_type": link.relationship_type,
                "upstream_condition_id": str(parent.id),
                "downstream_condition_ids": [str(c.id) for c in children],
                "statement": "Observed dependency and overlapping conditions support a potential common cause; root cause is not proven.",
            }
            if group is None:
                group = EventCorrelationGroup(
                    organization_id=organization_id,
                    environment=environment,
                    group_key=key,
                    title="Related "
                    + parent.condition_type
                    + " and dependent resource conditions",
                    confidence="RELATIONSHIP_SUPPORTED",
                    evidence=evidence,
                    opened_at=observed,
                    last_observed_at=observed,
                )
                db.add(group)
                db.flush()
            group.status = "OPEN"
            group.last_observed_at = observed
            group.evidence = evidence
            group.resolved_at = None
            current.add(group.id)
            for item in [parent, *children]:
                if not db.scalar(
                    select(EventCorrelationMember.id).where(
                        EventCorrelationMember.group_id == group.id,
                        EventCorrelationMember.condition_id == item.id,
                    )
                ):
                    db.add(
                        EventCorrelationMember(
                            organization_id=organization_id,
                            group_id=group.id,
                            condition_id=item.id,
                            relationship_id=link.id,
                            evidence={
                                "condition_evidence": item.evidence,
                                "alert_state_id": (
                                    str(item.alert_state_id)
                                    if item.alert_state_id
                                    else None
                                ),
                            },
                        )
                    )
    db.flush()
    # A relation becoming inactive does not prove health recovery. Resolve only
    # after every member's independently evaluated condition has recovered.
    for group in db.scalars(
        select(EventCorrelationGroup).where(
            EventCorrelationGroup.organization_id == organization_id,
            EventCorrelationGroup.environment == environment,
            EventCorrelationGroup.status == "OPEN",
        )
    ):
        members = db.scalars(
            select(ResourceCondition)
            .join(
                EventCorrelationMember,
                EventCorrelationMember.condition_id == ResourceCondition.id,
            )
            .where(EventCorrelationMember.group_id == group.id)
        ).all()
        if members and all(not c.active for c in members):
            group.status = "RESOLVED"
            group.resolved_at = observed
            group.last_observed_at = observed


def cycle(limit=20, observed=None):
    observed = observed or utc()
    count = 0
    with SessionLocal() as db:
        ids = db.scalars(
            select(MonitoringResource.id)
            .join(Organization, Organization.id == MonitoringResource.organization_id)
            .where(
                Organization.active.is_(True),
                MonitoringResource.active.is_(True),
                MonitoringResource.activation_status == "ACTIVE",
                or_(
                    MonitoringResource.last_engine_attempt_at.is_(None),
                    MonitoringResource.last_engine_attempt_at
                    < observed - timedelta(seconds=4),
                ),
            )
            .order_by(
                MonitoringResource.last_engine_attempt_at.nullsfirst(),
                MonitoringResource.id,
            )
            .limit(limit)
        ).all()
    for id in ids:
        try:
            with SessionLocal() as db:
                r = db.scalar(
                    select(MonitoringResource)
                    .where(
                        MonitoringResource.id == id,
                        or_(
                            MonitoringResource.last_engine_attempt_at.is_(None),
                            MonitoringResource.last_engine_attempt_at
                            < observed - timedelta(seconds=4),
                        ),
                    )
                    .with_for_update(skip_locked=True)
                )
                if not r:
                    continue
                p = active_parameters(db, r)
                if not p and r.domain == "ETL":
                    from types import SimpleNamespace
                    from app.unified.schemas import ETLParameters

                    resource_parser = SimpleNamespace(
                        version=None,
                        configuration=ETLParameters(
                            parser=r.configuration.get("parser", {})
                        ).model_dump(mode="json"),
                    )
                    if r.primary_collector_id:
                        ingest_connector(db, r, resource_parser)
                    else:
                        ingest_logs(db, r, resource_parser)
                if p:
                    if r.domain == "ETL":
                        if r.primary_collector_id:
                            ingest_connector(db, r, p)
                        else:
                            ingest_logs(db, r, p)
                        evaluate_schedule(db, r, p, observed)
                        evaluate_executions(db, r, p, observed)
                    elif r.domain == "VM":
                        evaluate_vm(db, r, p, observed)
                    else:
                        evaluate_api(db, r, p, observed)
                    correlate(db, r.organization_id, r.environment, observed)
                if (
                    not p
                    and r.domain == "ETL"
                    and r.configuration.get("platform") == "PENTAHO"
                ):
                    from app.unified.pentaho_history import reconcile

                    reconcile(db, r, observed)
                r.last_engine_attempt_at = observed
                r.last_engine_success_at = observed
                r.last_engine_error = None
                db.commit()
                count += 1
        except Exception:
            # Isolate a poison resource and leave its transaction rolled back.
            # Other resources still progress; no sensitive exception is logged.
            with SessionLocal() as db:
                failed = db.get(MonitoringResource, id)
                if failed:
                    failed.last_engine_attempt_at = observed
                    failed.last_engine_error = "EVALUATION_FAILED"
                    db.commit()
    return count
