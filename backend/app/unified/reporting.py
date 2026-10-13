"""SQL aggregates and bounded drill-downs over persisted domain evidence."""

from datetime import datetime, timedelta, timezone
from uuid import UUID
from fastapi import Depends, HTTPException, Query
from sqlalchemy import select, func, or_, and_, case
from app.db.session import get_db
from app.models import (
    JobOrderHistory,
    JobStepExecution,
    ExecutionStatus,
    MetricDefinition,
    MetricSample,
    CollectorRun,
    AlertState,
)
from app.unified.models import (
    MonitoringResource,
    ResourceCondition,
    ExpectedExecutionWindow,
    EventCorrelationGroup,
    EventCorrelationMember,
)
from app.unified.api import router, document, output
from app.unified.schemas import Environment
from app.security.scope import current_principal


def root_query(organization_id, environment, resource_id=None, domain=None):
    q = select(MonitoringResource)
    if organization_id:
        q = q.where(MonitoringResource.organization_id.in_(organization_id))
    if environment:
        q = q.where(MonitoringResource.environment == environment)
    if resource_id:
        q = q.where(MonitoringResource.id.in_(resource_id))
    if domain:
        q = q.where(MonitoringResource.domain == domain)
    return q


def roots(db, organization_id, environment, resource_id=None, domain=None):
    return db.scalars(
        root_query(organization_id, environment, resource_id, domain).order_by(
            MonitoringResource.name, MonitoringResource.id
        )
    ).all()


def range_bounds(start, end):
    end = end or datetime.now(timezone.utc)
    start = start or end - timedelta(days=7)
    if (
        start.tzinfo is None
        or end.tzinfo is None
        or start >= end
        or end - start > timedelta(days=366)
    ):
        raise HTTPException(422, "Use an aware UTC date range of at most 366 days")
    return start, end


def alert_join(records):
    ids = [r.id for r in records]
    sources = [r.data_source_id for r in records if r.data_source_id]
    return (
        select(AlertState, MetricDefinition)
        .join(MetricDefinition, MetricDefinition.id == AlertState.metric_definition_id)
        .where(
            or_(
                MetricDefinition.resource_id.in_(ids),
                MetricDefinition.data_source_id.in_(sources),
            )
        )
    )


def alerts_for(db, records, limit=100):
    mapping = {r.id: r for r in records}
    source_mapping = {r.data_source_id: r for r in records if r.data_source_id}
    query = alert_join(records)
    result = []
    for alert, metric in db.execute(
        query.order_by(AlertState.last_evaluated_at.desc(), AlertState.id).limit(limit)
    ):
        root = mapping.get(metric.resource_id) or source_mapping.get(
            metric.data_source_id
        )
        if root:
            result.append(
                {
                    **document(alert),
                    "resource_id": root.id,
                    "resource_name": root.name,
                    "domain": root.domain,
                    "environment": root.environment,
                    "metric_name": (metric.query_config or {}).get(
                        "condition_type", metric.name
                    ),
                    "condition_type": (metric.query_config or {}).get("condition_type"),
                }
            )
    return result


@router.get("/overview")
def overview(
    organization_id: list[UUID] = Query(default=[]),
    environment: Environment | None = None,
    db=Depends(get_db),
):
    records = roots(db, organization_id, environment)
    principal = current_principal.get()
    domain = {
        kind: {
            "resources": sum(r.domain == kind for r in records),
            "monitoring_active": sum(
                r.domain == kind and r.activation_status == "ACTIVE" for r in records
            ),
            "open_alerts": 0,
        }
        for kind in ("ETL", "VM", "API")
    }
    alert_records = alerts_for(db, records, limit=200)
    # Counts use the complete query, not the bounded visible history page.
    mapping = {r.id: r for r in records}
    sources = {r.data_source_id: r for r in records if r.data_source_id}
    for metric, count in db.execute(
        select(MetricDefinition, func.count(AlertState.id))
        .join(AlertState, AlertState.metric_definition_id == MetricDefinition.id)
        .where(
            AlertState.status == "OPEN",
            or_(
                MetricDefinition.resource_id.in_(list(mapping)),
                MetricDefinition.data_source_id.in_(list(sources)),
            ),
        )
        .group_by(MetricDefinition.id)
    ):
        root = mapping.get(metric.resource_id) or sources.get(metric.data_source_id)
        if root and principal.allows("alerts.view", root.organization_id):
            domain[root.domain]["open_alerts"] += count
    orgs = {
        r.organization_id
        for r in records
        if principal.allows("alerts.view", r.organization_id)
    }
    q = select(EventCorrelationGroup).where(
        EventCorrelationGroup.organization_id.in_(orgs)
    )
    if environment:
        q = q.where(EventCorrelationGroup.environment == environment)
    groups = db.scalars(
        q.order_by(EventCorrelationGroup.opened_at.desc()).limit(50)
    ).all()
    group_count = db.scalar(
        select(func.count()).select_from(
            q.where(EventCorrelationGroup.status == "OPEN").subquery()
        )
    )
    alert_records = [
        a
        for a in alert_records
        if principal.allows("alerts.view", a["organization_id"])
    ]
    groups = [g for g in groups if principal.allows("alerts.view", g.organization_id)]
    return {
        "domains": domain,
        "alerts": alert_records,
        "correlation_groups": [document(g) for g in groups],
        "open_correlation_groups": group_count,
        "measurement_note": "Configured/active monitoring and actual evidence are separate states; no health is inferred from saving a resource.",
    }


@router.get("/correlations")
def correlations(
    organization_id: list[UUID] = Query(default=[]),
    environment: Environment | None = None,
    status: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db=Depends(get_db),
):
    q = select(EventCorrelationGroup)
    if organization_id:
        q = q.where(EventCorrelationGroup.organization_id.in_(organization_id))
    if environment:
        q = q.where(EventCorrelationGroup.environment == environment)
    if status:
        q = q.where(EventCorrelationGroup.status == status)
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    groups = db.scalars(
        q.order_by(EventCorrelationGroup.opened_at.desc(), EventCorrelationGroup.id)
        .offset(offset)
        .limit(limit)
    ).all()
    return {
        "total": total,
        "items": [
            {
                **document(g),
                "members": [
                    document(m)
                    for m in db.scalars(
                        select(EventCorrelationMember).where(
                            EventCorrelationMember.group_id == g.id
                        )
                    ).all()
                ],
            }
            for g in groups
        ],
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(groups) < total,
    }


@router.get("/domain-state/{domain}")
def domain_state(
    domain: str,
    organization_id: list[UUID] = Query(default=[]),
    environment: Environment | None = None,
    resource_id: UUID | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db=Depends(get_db),
):
    if domain not in {"VM", "ETL", "API"}:
        raise HTTPException(422, "Invalid monitoring domain")
    query = root_query(
        organization_id, environment, [resource_id] if resource_id else None, domain
    )
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    page = db.scalars(
        query.order_by(MonitoringResource.name, MonitoringResource.id)
        .offset(offset)
        .limit(limit)
    ).all()
    ids = [r.id for r in page]
    conditions = db.scalars(
        select(ResourceCondition).where(ResourceCondition.resource_id.in_(ids))
    ).all()
    by_resource = {}
    for c in conditions:
        by_resource.setdefault(c.resource_id, []).append(document(c))
    result = []
    from app.unified.engines import source_readiness

    for r in page:
        readiness = source_readiness(db, r)
        items = by_resource.get(r.id, [])
        rows = {
            **output(db, r),
            "source_verification": readiness,
            "conditions": items,
            "operational_state": (
                "CRITICAL"
                if any(c["active"] and c["severity"] == "CRITICAL" for c in items)
                else (
                    "WARNING"
                    if any(c["active"] for c in items)
                    else (
                        "VERIFIED"
                        if readiness["ready"] and r.activation_status == "ACTIVE"
                        else "UNVERIFIED"
                    )
                )
            ),
        }
        if domain == "ETL":
            latest = db.scalar(
                select(JobOrderHistory)
                .where(JobOrderHistory.job_order_id == r.job_order_id)
                .order_by(JobOrderHistory.created_at.desc(), JobOrderHistory.id)
                .limit(1)
            )
            rows["latest_execution"] = document(latest) if latest else None
            rows["schedule_windows"] = [
                document(w)
                for w in db.scalars(
                    select(ExpectedExecutionWindow)
                    .where(ExpectedExecutionWindow.resource_id == r.id)
                    .order_by(ExpectedExecutionWindow.scheduled_at.desc())
                    .limit(20)
                )
            ]
        elif domain == "API":
            latest = (
                db.scalar(
                    select(CollectorRun)
                    .where(CollectorRun.collector_id == r.primary_collector_id)
                    .order_by(CollectorRun.started_at.desc())
                    .limit(1)
                )
                if r.primary_collector_id
                else None
            )
            rows["latest_probe"] = document(latest) if latest else None
        else:
            points = (
                db.execute(
                    select(MetricDefinition, MetricSample)
                    .join(
                        MetricSample,
                        MetricSample.metric_definition_id == MetricDefinition.id,
                    )
                    .where(
                        MetricDefinition.data_source_id == r.data_source_id,
                        MetricDefinition.metric_type != "DERIVED_CONDITION",
                    )
                    .order_by(MetricSample.observed_at.desc())
                    .limit(200)
                ).all()
                if r.data_source_id
                else []
            )
            seen = set()
            rows["latest_metrics"] = []
            for m, sample in points:
                if m.id not in seen:
                    rows["latest_metrics"].append(
                        {
                            "metric_definition_id": m.id,
                            "name": (m.query_config or {}).get(
                                "otel_metric_name", m.name
                            ),
                            "value": sample.value_numeric,
                            "unit": sample.unit,
                            "observed_at": sample.observed_at,
                            "dimensions": sample.dimensions,
                        }
                    )
                    seen.add(m.id)
        result.append(rows)
    return {
        "items": result,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(result) < total,
    }


@router.get("/reports/{domain}")
def reports(
    domain: str,
    organization_id: list[UUID] = Query(default=[]),
    environment: Environment | None = None,
    resource_id: list[UUID] = Query(default=[]),
    status: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db=Depends(get_db),
):
    if domain not in {"VM", "ETL", "API"}:
        raise HTTPException(422, "Invalid report domain")
    start, end = range_bounds(start, end)
    resources = roots(db, organization_id, environment, resource_id, domain)
    result = {
        "domain": domain,
        "start": start,
        "end": end,
        "resources": [
            {
                "id": r.id,
                "name": r.name,
                "environment": r.environment,
                "customer_id": r.organization_id,
            }
            for r in resources
        ],
        "summary": {},
        "histogram": [],
        "history": [],
        "limit": limit,
        "offset": offset,
        "total": 0,
    }
    if domain == "ETL":
        jobs = [r.job_order_id for r in resources]
        query = select(JobOrderHistory).where(
            JobOrderHistory.job_order_id.in_(jobs),
            func.coalesce(
                JobOrderHistory.ended_at,
                JobOrderHistory.started_at,
                JobOrderHistory.detected_at,
                JobOrderHistory.created_at,
            )
            >= start,
            func.coalesce(
                JobOrderHistory.ended_at,
                JobOrderHistory.started_at,
                JobOrderHistory.detected_at,
                JobOrderHistory.created_at,
            )
            < end,
        )
        if status:
            query = query.where(JobOrderHistory.status == status)
        sub = query.subquery()
        summary = (
            db.execute(
                select(
                    func.count(sub.c.id).label("observed_executions"),
                    func.count().filter(sub.c.ended_at.is_not(None)).label("completed"),
                    func.count().filter(sub.c.status == "SUCCESS").label("success"),
                    func.count().filter(sub.c.status == "FAILED").label("failed"),
                    func.count()
                    .filter(sub.c.status.in_(["RUNNING", "LONG_RUNNING"]))
                    .label("running"),
                    func.avg(func.extract("epoch", sub.c.ended_at - sub.c.started_at))
                    .filter(sub.c.ended_at >= sub.c.started_at)
                    .label("average_duration_seconds"),
                    func.count().filter(sub.c.sla_status == "MET").label("sla_met"),
                    func.count()
                    .filter(sub.c.sla_status == "BREACHED")
                    .label("sla_breached"),
                )
            )
            .mappings()
            .one()
        )
        result["summary"] = dict(summary)
        eligible = summary["sla_met"] + summary["sla_breached"]
        result["summary"]["sla_compliance_percent"] = (
            100 * summary["sla_met"] / eligible if eligible else None
        )
        histogram = (
            db.execute(
                select(
                    func.date_trunc("day", sub.c.ended_at).label("day"),
                    func.count().label("completed"),
                    func.count().filter(sub.c.status == "SUCCESS").label("success"),
                    func.count().filter(sub.c.status == "FAILED").label("failed"),
                    func.avg(
                        func.extract("epoch", sub.c.ended_at - sub.c.started_at)
                    ).label("average_duration_seconds"),
                )
                .where(sub.c.ended_at.is_not(None))
                .group_by("day")
                .order_by("day")
            )
            .mappings()
            .all()
        )
        result["histogram"] = [dict(row) for row in histogram]
        window = select(ExpectedExecutionWindow).where(
            ExpectedExecutionWindow.resource_id.in_([r.id for r in resources]),
            ExpectedExecutionWindow.scheduled_at >= start,
            ExpectedExecutionWindow.scheduled_at < end,
        )
        windows = window.subquery()
        result["summary"]["no_run"] = db.scalar(
            select(func.count())
            .select_from(windows)
            .where(windows.c.status == "NO_RUN")
        )
        result["summary"]["delayed"] = db.scalar(
            select(func.count())
            .select_from(windows)
            .where(windows.c.status == "DELAYED")
        )
        result["summary"]["long_running_episodes"] = db.scalar(
            select(func.count())
            .select_from(ResourceCondition)
            .where(
                ResourceCondition.resource_id.in_([r.id for r in resources]),
                ResourceCondition.condition_type == "LONG_RUNNING",
                ResourceCondition.alert_state_id.is_not(None),
                ResourceCondition.first_observed_at >= start,
                ResourceCondition.first_observed_at < end,
            )
        )
        result["step_failures"] = [
            dict(row)
            for row in db.execute(
                select(JobStepExecution.name, func.count().label("failed_attempts"))
                .where(
                    JobStepExecution.history_id.in_(select(sub.c.id)),
                    JobStepExecution.status == "FAILED",
                )
                .group_by(JobStepExecution.name)
            ).mappings()
        ]
        result["jobchain_reliability"] = [
            dict(row)
            for row in db.execute(
                select(
                    sub.c.job_order_id,
                    func.count().label("observed"),
                    func.count().filter(sub.c.status == "SUCCESS").label("success"),
                    func.count().filter(sub.c.status == "FAILED").label("failed"),
                ).group_by(sub.c.job_order_id)
            ).mappings()
        ]
        result["total"] = summary["observed_executions"]
        result["history"] = [
            document(h)
            for h in db.scalars(
                query.order_by(JobOrderHistory.created_at.desc(), JobOrderHistory.id)
                .offset(offset)
                .limit(limit)
            )
        ]
    elif domain == "API":
        collectors = [
            r.primary_collector_id for r in resources if r.primary_collector_id
        ]
        query = select(CollectorRun).where(
            CollectorRun.collector_id.in_(collectors),
            CollectorRun.ended_at >= start,
            CollectorRun.ended_at < end,
            CollectorRun.outcome.in_(
                ["SUCCESS", "ASSERTION_FAILED", "TIMEOUT", "NETWORK_ERROR"]
            ),
        )
        if status:
            query = query.where(CollectorRun.status == status)
        sub = query.subquery()
        summary = (
            db.execute(
                select(
                    func.count().label("completed_probes"),
                    func.count()
                    .filter(sub.c.outcome == "SUCCESS")
                    .label("successful_probes"),
                    func.count().filter(sub.c.outcome == "TIMEOUT").label("timeouts"),
                    func.count().filter(sub.c.http_status >= 400).label("http_errors"),
                    func.avg(sub.c.response_time_ms).label("average_latency_ms"),
                    func.percentile_cont(0.95)
                    .within_group(sub.c.response_time_ms)
                    .label("p95_latency_ms"),
                )
            )
            .mappings()
            .one()
        )
        result["summary"] = dict(summary)
        result["summary"]["availability_percent"] = (
            100 * summary["successful_probes"] / summary["completed_probes"]
            if summary["completed_probes"]
            else None
        )
        result["summary"][
            "availability_denominator"
        ] = "COMPLETED_OBSERVED_PROBES; no results are not assumed healthy"
        result["histogram"] = [
            dict(row)
            for row in db.execute(
                select(
                    func.date_trunc("hour", sub.c.ended_at).label("hour"),
                    func.count().label("probes"),
                    func.count().filter(sub.c.outcome == "SUCCESS").label("success"),
                    func.avg(sub.c.response_time_ms).label("average_latency_ms"),
                )
                .group_by("hour")
                .order_by("hour")
            ).mappings()
        ]
        result["total"] = summary["completed_probes"]
        result["history"] = [
            document(h)
            for h in db.scalars(
                query.order_by(CollectorRun.ended_at.desc(), CollectorRun.id)
                .offset(offset)
                .limit(limit)
            )
        ]
    else:
        sources = [r.data_source_id for r in resources if r.data_source_id]
        query = (
            select(MetricSample, MetricDefinition)
            .join(
                MetricDefinition,
                MetricDefinition.id == MetricSample.metric_definition_id,
            )
            .where(
                MetricDefinition.data_source_id.in_(sources),
                MetricDefinition.metric_type != "DERIVED_CONDITION",
                MetricSample.observed_at >= start,
                MetricSample.observed_at < end,
            )
        )
        summary = (
            db.execute(
                select(
                    func.count(MetricSample.id).label("samples"),
                    func.count(func.distinct(MetricSample.metric_definition_id)).label(
                        "metric_series"
                    ),
                    func.max(MetricSample.observed_at).label("last_observed"),
                )
                .join(
                    MetricDefinition,
                    MetricDefinition.id == MetricSample.metric_definition_id,
                )
                .where(
                    MetricDefinition.data_source_id.in_(sources),
                    MetricSample.observed_at >= start,
                    MetricSample.observed_at < end,
                )
            )
            .mappings()
            .one()
        )
        result["summary"] = dict(summary)
        result["histogram"] = [
            dict(row)
            for row in db.execute(
                select(
                    func.date_trunc("hour", MetricSample.observed_at).label("hour"),
                    MetricDefinition.name,
                    MetricSample.unit,
                    func.avg(MetricSample.value_numeric).label("average"),
                    func.min(MetricSample.value_numeric).label("minimum"),
                    func.max(MetricSample.value_numeric).label("maximum"),
                )
                .join(
                    MetricDefinition,
                    MetricDefinition.id == MetricSample.metric_definition_id,
                )
                .where(
                    MetricDefinition.data_source_id.in_(sources),
                    MetricDefinition.metric_type != "DERIVED_CONDITION",
                    MetricSample.observed_at >= start,
                    MetricSample.observed_at < end,
                )
                .group_by("hour", MetricDefinition.id, MetricSample.unit)
                .order_by("hour", MetricDefinition.name)
                .limit(10000)
            ).mappings()
        ]
        result["total"] = db.scalar(select(func.count()).select_from(query.subquery()))
        result["history"] = [
            {
                **document(sample),
                "metric_name": (metric.query_config or {}).get(
                    "otel_metric_name", metric.name
                ),
            }
            for sample, metric in db.execute(
                query.order_by(MetricSample.observed_at.desc(), MetricSample.id)
                .offset(offset)
                .limit(limit)
            )
        ]
        result["summary"][
            "uptime_note"
        ] = "Host uptime is reported only by actual opscontrol.host.uptime samples; unknown is not zero."
    result["has_more"] = offset + len(result["history"]) < result["total"]
    return result


@router.get("/alerts")
def unified_alerts(
    organization_id: list[UUID] = Query(default=[]),
    environment: Environment | None = None,
    domain: str | None = None,
    resource_id: UUID | None = None,
    status: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db=Depends(get_db),
):
    q = (
        select(AlertState, MetricDefinition, MonitoringResource)
        .join(MetricDefinition, MetricDefinition.id == AlertState.metric_definition_id)
        .outerjoin(
            MonitoringResource,
            and_(
                MonitoringResource.organization_id == AlertState.organization_id,
                or_(
                    MetricDefinition.resource_id == MonitoringResource.id,
                    MetricDefinition.data_source_id
                    == MonitoringResource.data_source_id,
                ),
            ),
        )
    )
    if organization_id:
        q = q.where(AlertState.organization_id.in_(organization_id))
    if environment:
        q = q.where(MonitoringResource.environment == environment)
    if domain:
        q = q.where(MonitoringResource.domain == domain)
    if resource_id:
        q = q.where(MonitoringResource.id == resource_id)
    if status:
        q = q.where(AlertState.status == status)
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    items = [
        {
            **document(a),
            "resource_id": r.id if r else None,
            "resource_name": r.name if r else m.name,
            "domain": r.domain if r else "UNMAPPED",
            "environment": r.environment if r else None,
            "metric_name": (m.query_config or {}).get("condition_type", m.name),
            "condition_type": (m.query_config or {}).get("condition_type"),
        }
        for a, m, r in db.execute(
            q.order_by(AlertState.last_evaluated_at.desc(), AlertState.id)
            .offset(offset)
            .limit(limit)
        )
    ]
    return {
        "alerts": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(items) < total,
    }
