"""Scoped control plane and authenticated agent pull; no remote shell."""

import hashlib, json, os, secrets, uuid
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import Field
from typing import Literal
from sqlalchemy import select, func, or_, and_
from app.db.session import get_db, SessionLocal
from app.models import (
    Collector,
    DataSource,
    Organization,
    LogEvent,
    LogSource,
    MetricSample,
    MetricDefinition,
)
from app.security.models import WorkerIdentity
from app.security.http import token_digest
from app.security.access_control import require_permission
from app.security.audit import log_event
from app.telemetry.models import *
from app.telemetry.configuration import (
    Strict,
    MethodInput,
    host_os,
    validate_method,
    generate,
    validate_binary,
    RUNTIME_VERSION,
)

router = APIRouter(prefix="/api/v1/agent-control", tags=["Collector and Agent Control"])
agent_router = APIRouter(prefix="/api/v1/agent", tags=["OpsControl Agent"])


def utc():
    return datetime.now(timezone.utc)


def item(row):
    from app.security.secret_refs import redact_config

    return {
        c.name: redact_config(getattr(row, c.name))
        for c in row.__table__.columns
        if c.name not in {"token_hash", "previous_token_hash"}
    }


def parent(db, id, write=False):
    statement = select(Collector).where(Collector.id == id)
    c = db.scalar(statement.with_for_update() if write else statement)
    if c is None:
        raise HTTPException(404, "Collector unavailable")
    source = db.get(DataSource, c.data_source_id)
    if source is None:
        raise HTTPException(404, "Data Source unavailable")
    require_permission(
        "collectors.manage" if write else "collectors.view", source.organization_id
    )
    return c, source


def commit(db, source, action, target):
    p = require_permission("collectors.manage", source.organization_id)
    log_event(
        db,
        event_type=action,
        outcome="SUCCESS",
        actor_id=p.user_id,
        organization_id=source.organization_id,
        target_type="collector",
        target_id=target,
    )
    db.commit()


def rows(db, id):
    return db.scalars(
        select(CollectorMethod)
        .where(CollectorMethod.collector_id == id, CollectorMethod.deleted_at.is_(None))
        .order_by(CollectorMethod.created_at, CollectorMethod.id)
    ).all()


def method_evidence(db, collector_id, method_id, applied_at):
    """Receiver-specific evidence is scoped to the authenticated Collector."""
    key = str(method_id)
    log_count, log_last = db.execute(
        select(func.count(LogEvent.id), func.max(LogEvent.created_at))
        .join(LogSource, LogSource.id == LogEvent.log_source_id)
        .where(
            LogSource.collector_id == collector_id,
            LogEvent.attributes["opscontrol.method.id"].as_string() == key,
            LogEvent.created_at >= applied_at,
        )
    ).one()
    metric_count, metric_last = db.execute(
        select(func.count(MetricSample.id), func.max(MetricSample.created_at)).where(
            MetricSample.collector_id == collector_id,
            MetricSample.dimensions["opscontrol.method.id"].as_string() == key,
            MetricSample.created_at >= applied_at,
        )
    ).one()
    # Prometheus emits up=0 on actual target failure; receiving that sample is not healthy.
    up = db.execute(
        select(MetricSample.value_numeric, MetricSample.created_at)
        .join(
            MetricDefinition, MetricDefinition.id == MetricSample.metric_definition_id
        )
        .where(
            MetricSample.collector_id == collector_id,
            MetricSample.dimensions["opscontrol.method.id"].as_string() == key,
            MetricDefinition.query_config["otel_metric_name"].as_string() == "up",
            MetricSample.created_at >= applied_at,
        )
        .order_by(MetricSample.created_at.desc())
        .limit(1)
    ).first()
    last = max(
        (value for value in (log_last, metric_last) if value is not None), default=None
    )
    return {
        "record_count": log_count + metric_count,
        "last_received_at": last,
        "scrape_up": up[0] if up else None,
    }


def agent_delivery_state(agent, collector_enabled=True):
    if not collector_enabled:
        return "DISABLED"
    if (
        not agent
        or not agent.enabled
        or not agent.last_seen_at
        or agent.last_seen_at < utc() - timedelta(seconds=90)
    ):
        return "DISCONNECTED"
    if agent.health in {"STOPPED", "ERROR"}:
        return agent.health
    if agent.health != "RUNNING":
        return "NO_DATA"
    return None


def signal_delivery_state(agent, last_received_at, collector_enabled=True):
    if last_received_at is None:
        return "NO_DATA"
    unavailable = agent_delivery_state(agent, collector_enabled)
    if unavailable:
        return unavailable
    return "RECEIVING" if last_received_at > utc() - timedelta(minutes=5) else "NO_DATA"


def method_collection_state(
    method, agent, applied, current, evidence, collector_enabled=True
):
    if not method.enabled:
        return "DISABLED"
    if not collector_enabled:
        return "DISABLED"
    if not current or not applied:
        return "NOT_APPLIED"
    unavailable = agent_delivery_state(agent)
    if unavailable:
        return unavailable
    observation = (agent.method_health or {}).get(str(method.id), {})
    if observation.get("applied_revision") != applied.revision:
        observation = {}
    if observation:
        try:
            observed_at = datetime.fromisoformat(observation.get("observed_at", ""))
            if observed_at.tzinfo is None or observed_at < utc() - timedelta(
                seconds=90
            ):
                observation = {}
        except (ValueError, TypeError):
            observation = {}
    if observation.get("state") == "STOPPED":
        return "STOPPED"
    if observation.get("state") == "ERROR":
        return "ERROR"
    if evidence.get("scrape_up") == 0:
        return "ERROR"
    last = evidence.get("last_received_at")
    if last and last > utc() - timedelta(minutes=5):
        return "RECEIVING"
    if (
        method.method_type == "FILE_LOG"
        and observation.get("state") == "IDLE"
        and observation.get("sources_readable", 0) > 0
    ):
        return "IDLE"
    return "NO_DATA"


@router.get("/collectors/{id}")
def details(id: uuid.UUID, db=Depends(get_db)):
    c, s = parent(db, id)
    a = db.scalar(select(ManagedAgent).where(ManagedAgent.collector_id == id))
    receipt = []
    if a:
        for signal in ("logs", "metrics", "traces"):
            count, last = db.execute(
                select(
                    func.sum(TelemetryReceipt.record_count),
                    func.max(TelemetryReceipt.received_at),
                ).where(
                    TelemetryReceipt.agent_id == a.id, TelemetryReceipt.signal == signal
                )
            ).one()
            receipt.append(
                {
                    "signal": signal,
                    "count": count or 0,
                    "last_received_at": last,
                    "status": signal_delivery_state(a, last, c.enabled),
                }
            )
    versions = db.scalars(
        select(CollectorConfigVersion)
        .where(CollectorConfigVersion.collector_id == id)
        .order_by(CollectorConfigVersion.revision.desc())
        .limit(50)
    ).all()
    deployments = (
        db.scalars(
            select(AgentDeployment)
            .where(AgentDeployment.agent_id == a.id)
            .order_by(AgentDeployment.created_at.desc())
            .limit(50)
        ).all()
        if a
        else []
    )
    applied = None
    if a and a.applied_revision:
        applied = db.scalar(
            select(CollectorConfigVersion).where(
                CollectorConfigVersion.collector_id == id,
                CollectorConfigVersion.revision == a.applied_revision,
            )
        )
    applied_methods = {m["id"]: m for m in applied.method_snapshot} if applied else {}
    method_documents = []
    for method in rows(db, id):
        old = applied_methods.get(str(method.id))
        current = old is not None and old["revision"] == method.revision
        deployed = (
            ("APPLIED" if method.enabled else "DISABLED_IN_APPLIED_CONFIG")
            if current
            else ("CHANGES_NOT_APPLIED" if old else "NOT_APPLIED")
        )
        valid = any(
            v.validation_status == "VALIDATED"
            and any(
                m["id"] == str(method.id) and m["revision"] == method.revision
                for m in v.method_snapshot
            )
            for v in ([applied] if applied else []) + versions
        )
        evidence = (
            method_evidence(db, id, method.id, a.applied_at)
            if a and applied and current and a.applied_at
            else {"record_count": 0, "last_received_at": None}
        )
        method_documents.append(
            {
                **item(method),
                "deployment_status": deployed,
                "binary_validation": "VALIDATED" if valid else "NOT_VALIDATED",
                "collection_status": method_collection_state(
                    method, a, applied, current, evidence, c.enabled
                ),
                "method_observation": (
                    (a.method_health or {}).get(str(method.id)) if a else None
                ),
                **evidence,
            }
        )
    return {
        "collector": item(c),
        "os_type": host_os(s),
        "methods": method_documents,
        "agent": (
            {
                **item(a),
                "configuration_state": (
                    "ERROR"
                    if a.last_error
                    else (
                        "DRIFT"
                        if a.desired_revision != a.applied_revision
                        else (
                            "VERIFIED"
                            if a.verified_revision == a.applied_revision
                            and a.applied_revision
                            else (
                                "APPLIED_AWAITING_EVIDENCE"
                                if a.applied_revision
                                else (
                                    "DOWNLOADED"
                                    if a.downloaded_revision
                                    else "NOT_CONFIGURED"
                                )
                            )
                        )
                    )
                ),
                "connection": (
                    "REVOKED"
                    if not a.enabled
                    else (
                        "CONNECTED"
                        if a.last_seen_at
                        and a.last_seen_at > utc() - timedelta(seconds=90)
                        else "DISCONNECTED"
                    )
                ),
            }
            if a
            else None
        ),
        "signals": receipt,
        "versions": [item(v) for v in versions],
        "deployments": [item(d) for d in deployments],
        "runtime_version": RUNTIME_VERSION,
        "remote_installation_available": False,
    }


@router.post("/collectors/{id}/methods", status_code=201)
def add_method(id: uuid.UUID, payload: MethodInput, db=Depends(get_db)):
    c, s = parent(db, id, True)
    try:
        validate_method(payload, host_os(s))
    except ValueError as e:
        raise HTTPException(422, str(e)) from None
    m = CollectorMethod(
        collector_id=id,
        organization_id=s.organization_id,
        **payload.model_dump(exclude={"expected_revision"}),
        validation_status="SCHEMA_VALID"
    )
    db.add(m)
    db.flush()
    commit(db, s, "METHOD_CREATE", m.id)
    return item(m)


@router.put("/collectors/{id}/methods/{method_id}")
def edit_method(
    id: uuid.UUID, method_id: uuid.UUID, payload: MethodInput, db=Depends(get_db)
):
    c, s = parent(db, id, True)
    m = db.scalar(
        select(CollectorMethod)
        .where(
            CollectorMethod.id == method_id,
            CollectorMethod.collector_id == id,
            CollectorMethod.deleted_at.is_(None),
        )
        .with_for_update()
    )
    if not m:
        raise HTTPException(404, "Method unavailable")
    if payload.expected_revision != m.revision:
        raise HTTPException(409, "Method changed; reload before saving")
    try:
        validate_method(payload, host_os(s))
    except ValueError as e:
        raise HTTPException(422, str(e)) from None
    for k, v in payload.model_dump(exclude={"expected_revision"}).items():
        setattr(m, k, v)
    m.revision += 1
    m.updated_at = utc()
    m.validation_status = "SCHEMA_VALID"
    commit(db, s, "METHOD_UPDATE", m.id)
    return item(m)


@router.delete("/collectors/{id}/methods/{method_id}", status_code=204)
def delete_method(id: uuid.UUID, method_id: uuid.UUID, db=Depends(get_db)):
    c, s = parent(db, id, True)
    m = db.scalar(
        select(CollectorMethod).where(
            CollectorMethod.id == method_id,
            CollectorMethod.collector_id == id,
            CollectorMethod.deleted_at.is_(None),
        )
    )
    if not m:
        raise HTTPException(404, "Method unavailable")
    m.deleted_at = utc()
    m.enabled = False
    m.revision += 1
    commit(db, s, "METHOD_DELETE", m.id)


@router.get("/collectors/{id}/preview")
def preview(id: uuid.UUID, db=Depends(get_db)):
    c, s = parent(db, id)
    try:
        text = generate(
            c,
            s,
            rows(db, id),
            os.getenv("OPSCONTROL_PUBLIC_INGESTION_URL", ""),
        )
    except ValueError as e:
        raise HTTPException(422, str(e)) from None
    return {
        "yaml": text,
        "runtime_version": RUNTIME_VERSION,
        "status": "PREVIEW",
        "deployment": False,
    }


@router.post("/collectors/{id}/versions", status_code=201)
def save_version(id: uuid.UUID, db=Depends(get_db)):
    c, s = parent(db, id, True)
    methods = rows(db, id)
    try:
        text = generate(
            c,
            s,
            methods,
            os.getenv("OPSCONTROL_PUBLIC_INGESTION_URL", ""),
        )
        services = list((c.configuration or {}).get("services", []))
        for method in methods:
            if method.enabled and method.method_type == "SERVICES":
                services.extend(method.configuration.get("services", []))
        services = list(dict.fromkeys(services))
        import re

        if (
            not isinstance(services, list)
            or len(services) > 50
            or any(
                not isinstance(v, str)
                or not re.fullmatch(r"[A-Za-z0-9_.@ -]{1,200}", v)
                for v in services
            )
            or len(set(services)) != len(services)
        ):
            raise ValueError("Invalid service identities")
        processes = list((c.configuration or {}).get("processes", []))
        for method in methods:
            if method.enabled and method.method_type == "SERVICES":
                processes.extend(method.configuration.get("processes", []))
        processes = list(dict.fromkeys(processes))
        if (
            not isinstance(processes, list)
            or len(processes) > 50
            or any(
                not isinstance(v, str)
                or not re.fullmatch(r"[A-Za-z0-9_.@ -]{1,200}", v)
                for v in processes
            )
            or len(set(processes)) != len(processes)
        ):
            raise ValueError("Invalid process identities")
        valid = bool(os.getenv("OPSCONTROL_OTEL_BINARY"))
        if valid:
            validate_binary(text)
    except ValueError as e:
        raise HTTPException(422, str(e)) from None
    revision = (
        db.scalar(
            select(func.max(CollectorConfigVersion.revision)).where(
                CollectorConfigVersion.collector_id == id
            )
        )
        or 0
    ) + 1
    version = CollectorConfigVersion(
        organization_id=s.organization_id,
        collector_id=id,
        revision=revision,
        yaml_text=text,
        sha256=hashlib.sha256(text.encode()).hexdigest(),
        runtime_version=RUNTIME_VERSION,
        validation_status="VALIDATED" if valid else "UNVALIDATED",
        agent_configuration={
            "services": services,
            "processes": processes,
            "native_os_metrics": bool((c.configuration or {}).get("os_metrics"))
            or any(m.enabled and m.method_type == "HOST_METRICS" for m in methods),
            "service_interval_seconds": min(
                [
                    m.configuration.get("interval_seconds", 30)
                    for m in methods
                    if m.enabled and m.method_type == "SERVICES"
                ]
                or [30]
            ),
        },
        method_snapshot=[json.loads(json.dumps(item(m), default=str)) for m in methods],
    )
    db.add(version)
    db.flush()
    commit(db, s, "CONFIG_SAVE", version.id)
    return item(version)


@router.post("/collectors/{id}/registration", status_code=201)
def enrollment(id: uuid.UUID, db=Depends(get_db)):
    c, s = parent(db, id, True)
    if c.collector_type != "OTEL" or host_os(s) == "Unsupported":
        raise HTTPException(422, "A supported OTEL host Collector is required")
    if not c.enabled or not s.enabled:
        raise HTTPException(409, "Collector and Data Source must be enabled")
    if db.scalar(
        select(ManagedAgent.id).where(
            ManagedAgent.collector_id == id, ManagedAgent.enabled.is_(True)
        )
    ):
        raise HTTPException(
            409, "Agent already registered; revoke before re-enrollment"
        )
    for old in db.scalars(
        select(AgentRegistration).where(
            AgentRegistration.collector_id == id,
            AgentRegistration.consumed_at.is_(None),
        )
    ):
        old.consumed_at = utc()
    token = secrets.token_urlsafe(48)
    row = AgentRegistration(
        organization_id=s.organization_id,
        collector_id=id,
        token_hash=token_digest(token),
        expires_at=utc() + timedelta(minutes=15),
    )
    db.add(row)
    commit(db, s, "AGENT_ENROLLMENT", id)
    return {"enrollment_token": token, "expires_at": row.expires_at, "one_time": True}


class Register(Strict):
    os_type: str = Field(pattern="^(Linux|Windows)$")
    enrollment_token: str = Field(min_length=40, max_length=160)
    hostname: str = Field(min_length=1, max_length=255)
    version: str = Field(min_length=1, max_length=80)
    runtime_version: str = Field(min_length=1, max_length=80)


@agent_router.post("/register", status_code=201)
def register(payload: Register):
    with SessionLocal() as db:
        digest = token_digest(payload.enrollment_token)
        target = db.execute(
            select(AgentRegistration.id, AgentRegistration.collector_id).where(
                AgentRegistration.token_hash == digest
            )
        ).first()
        if not target:
            raise HTTPException(401, "Enrollment expired or consumed")
        # Enrollment issuance also locks the collector first. Serialize token
        # consumption in the same order to avoid a renew/register deadlock.
        c = db.scalar(
            select(Collector)
            .where(Collector.id == target.collector_id)
            .with_for_update()
        )
        reg = db.scalar(
            select(AgentRegistration)
            .where(AgentRegistration.id == target.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if (
            not c
            or not reg
            or reg.token_hash != digest
            or reg.consumed_at
            or reg.expires_at <= utc()
        ):
            raise HTTPException(401, "Enrollment expired or consumed")
        s = db.get(DataSource, c.data_source_id)
        o = db.get(Organization, reg.organization_id)
        if (
            not o.active
            or not c.enabled
            or not s.enabled
            or s.organization_id != reg.organization_id
            or host_os(s) == "Unsupported"
        ):
            raise HTTPException(403, "Enrollment target unavailable")
        if payload.os_type != host_os(s):
            raise HTTPException(422, "Agent OS does not match the selected Data Source")
        if payload.runtime_version != RUNTIME_VERSION:
            raise HTTPException(422, "Unsupported OTel runtime version")
        existing = db.scalar(
            select(ManagedAgent)
            .where(ManagedAgent.collector_id == c.id)
            .with_for_update()
        )
        if existing is not None and existing.enabled:
            raise HTTPException(409, "Collector already has an agent")
        token = secrets.token_urlsafe(48)
        if existing:
            w = db.get(WorkerIdentity, existing.worker_id)
            w.token_hash = token_digest(token)
            w.enabled = True
            w.expires_at = utc() + timedelta(days=90)
            w.last_seen_at = None
            a = existing
            a.hostname = payload.hostname
            a.version = payload.version
            a.runtime_version = payload.runtime_version
            a.last_seen_at = None
            a.desired_revision = None
            a.applied_revision = None
            a.downloaded_revision = None
            a.verified_revision = None
            a.last_working_revision = None
            a.configuration_sha256 = None
            a.applied_at = None
            a.verified_at = None
            a.previous_token_hash = None
            a.previous_token_expires_at = None
            a.enabled = True
            a.health = "REGISTERED"
            a.last_error = None
        else:
            w = WorkerIdentity(
                organization_id=reg.organization_id,
                name="managed-agent-" + str(c.id),
                token_hash=token_digest(token),
                allowed_hosts=[],
                allowed_cidrs=[],
                expires_at=utc() + timedelta(days=90),
            )
            db.add(w)
            db.flush()
            a = ManagedAgent(
                organization_id=reg.organization_id,
                collector_id=c.id,
                worker_id=w.id,
                hostname=payload.hostname,
                version=payload.version,
                runtime_version=payload.runtime_version,
            )
            db.add(a)
        reg.consumed_at = utc()
        db.flush()
        log_event(
            db,
            event_type="AGENT_REGISTER",
            outcome="SUCCESS",
            organization_id=a.organization_id,
            target_type="agent",
            target_id=a.id,
        )
        db.commit()
        return {"agent_id": a.id, "access_token": token, "expires_at": w.expires_at}


def credential_matches(agent, worker, digest):
    return worker.token_hash == digest or bool(
        agent.previous_token_hash == digest
        and agent.previous_token_expires_at
        and agent.previous_token_expires_at > utc()
    )


def authenticate(db, request):
    auth = request.headers.get("authorization", "").split()
    if len(auth) != 2 or auth[0] != "Bearer" or len(auth[1]) > 256:
        raise HTTPException(401, "Agent authentication required")
    digest = token_digest(auth[1])
    identity = db.execute(
        select(ManagedAgent.id, ManagedAgent.collector_id, WorkerIdentity.id)
        .join(WorkerIdentity, ManagedAgent.worker_id == WorkerIdentity.id)
        .where(
            or_(
                WorkerIdentity.token_hash == digest,
                and_(
                    ManagedAgent.previous_token_hash == digest,
                    ManagedAgent.previous_token_expires_at > utc(),
                ),
            )
        )
    ).first()
    if not identity:
        raise HTTPException(401, "Agent credentials unavailable")
    # Keep the control plane and ingestion lock order identical: collector,
    # agent, worker. Recheck the credential after locking to cover revocation.
    c = db.scalar(
        select(Collector).where(Collector.id == identity.collector_id).with_for_update()
    )
    a = db.scalar(
        select(ManagedAgent)
        .where(ManagedAgent.id == identity[0])
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    w = db.scalar(
        select(WorkerIdentity)
        .where(WorkerIdentity.id == identity[2])
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if (
        not c
        or not a
        or not w
        or not credential_matches(a, w, digest)
        or not w.enabled
        or w.expires_at <= utc()
        or not a.enabled
        or a.worker_id != w.id
        or a.organization_id != w.organization_id
    ):
        raise HTTPException(401, "Agent credentials unavailable")
    s = db.get(DataSource, c.data_source_id)
    o = db.get(Organization, a.organization_id)
    if (
        not o
        or not o.active
        or not s
        or not c.enabled
        or not s.enabled
        or s.organization_id != a.organization_id
    ):
        raise HTTPException(403, "Agent target disabled")
    return a, c, s, w


class MethodObservation(Strict):
    method_id: uuid.UUID
    state: Literal["RUNNING", "IDLE", "STOPPED", "ERROR"]
    error_code: str | None = Field(default=None, pattern="^[A-Z0-9_]{1,80}$")
    sources_found: int = Field(default=0, ge=0, le=1000)
    sources_readable: int = Field(default=0, ge=0, le=1000)


class Heartbeat(Strict):
    version: str = Field(max_length=80)
    runtime_version: str = Field(max_length=80)
    applied_revision: int | None = None
    configuration_sha256: str | None = Field(default=None, pattern="^[a-f0-9]{64}$")
    health: str = Field(pattern="^(RUNNING|STOPPED|ERROR)$")
    method_observations: list[MethodObservation] = Field(
        default_factory=list, max_length=100
    )
    error_code: str | None = Field(default=None, pattern="^[A-Z0-9_]{1,80}$")


@agent_router.post("/heartbeat")
def heartbeat(payload: Heartbeat, request: Request):
    with SessionLocal() as db:
        a, c, s, w = authenticate(db, request)
        if payload.runtime_version != RUNTIME_VERSION:
            raise HTTPException(422, "Unsupported runtime")
        if payload.applied_revision is not None and payload.applied_revision not in (
            a.desired_revision,
            a.applied_revision,
        ):
            raise HTTPException(409, "Unapproved configuration revision")
        a.last_seen_at = utc()
        w.last_seen_at = a.last_seen_at
        a.version = payload.version
        a.runtime_version = payload.runtime_version
        a.health = payload.health
        a.last_error = payload.error_code
        if payload.health == "ERROR" and a.desired_revision:
            for deployment in db.scalars(
                select(AgentDeployment).where(
                    AgentDeployment.agent_id == a.id,
                    AgentDeployment.revision == a.desired_revision,
                    AgentDeployment.status == "APPROVED",
                )
            ):
                deployment.status = "FAILED"
                deployment.completed_at = utc()
                log_event(
                    db,
                    event_type="AGENT_CONFIG_FAILED",
                    outcome="FAILURE",
                    organization_id=a.organization_id,
                    target_type="agent",
                    target_id=a.id,
                )
        if payload.health == "RUNNING" and payload.applied_revision:
            version = db.scalar(
                select(CollectorConfigVersion).where(
                    CollectorConfigVersion.collector_id == c.id,
                    CollectorConfigVersion.revision == payload.applied_revision,
                )
            )
            if not version or version.validation_status != "VALIDATED":
                raise HTTPException(409, "Configuration not validated")
            if (
                payload.configuration_sha256
                and payload.configuration_sha256 != version.sha256
            ):
                raise HTTPException(409, "Configuration checksum mismatch")
            if a.applied_revision != payload.applied_revision or not a.applied_at:
                a.applied_at = utc()
                a.verified_revision = None
                a.verified_at = None
            a.applied_revision = payload.applied_revision
            a.configuration_sha256 = payload.configuration_sha256
            for d in db.scalars(
                select(AgentDeployment).where(
                    AgentDeployment.agent_id == a.id,
                    AgentDeployment.revision == a.applied_revision,
                    AgentDeployment.status.in_(["APPROVED", "FAILED"]),
                )
            ):
                d.status = "APPLIED"
                d.completed_at = utc()
                log_event(
                    db,
                    event_type="AGENT_CONFIG_APPLIED",
                    outcome="SUCCESS",
                    organization_id=a.organization_id,
                    target_type="agent",
                    target_id=a.id,
                )
            db.flush()
            verify_reception(db, a, version)
        if payload.method_observations:
            if payload.applied_revision != a.applied_revision:
                raise HTTPException(
                    409, "Method observations require the applied revision"
                )
            observed_version = db.scalar(
                select(CollectorConfigVersion).where(
                    CollectorConfigVersion.collector_id == c.id,
                    CollectorConfigVersion.revision == a.applied_revision,
                )
            )
            valid_ids = (
                {
                    str(m["id"])
                    for m in observed_version.method_snapshot
                    if m.get("enabled")
                }
                if observed_version
                else set()
            )
            observations = {}
            for observation in payload.method_observations:
                key = str(observation.method_id)
                if key not in valid_ids or key in observations:
                    raise HTTPException(
                        422,
                        "Method is not in the applied configuration or is duplicated",
                    )
                if observation.sources_readable > observation.sources_found:
                    raise HTTPException(422, "Invalid source observation counts")
                observations[key] = {
                    **observation.model_dump(mode="json"),
                    "applied_revision": a.applied_revision,
                    "observed_at": a.last_seen_at.isoformat(),
                }
            a.method_health = observations
        db.commit()
        return {
            "accepted": True,
            "desired_revision": a.desired_revision,
            "verified_revision": a.verified_revision,
            "last_working_revision": a.last_working_revision,
        }


@agent_router.get("/configuration")
def configuration(request: Request):
    with SessionLocal() as db:
        a, c, s, w = authenticate(db, request)
        if not a.desired_revision:
            raise HTTPException(404, "No configuration approved")
        v = db.scalar(
            select(CollectorConfigVersion).where(
                CollectorConfigVersion.collector_id == c.id,
                CollectorConfigVersion.revision == a.desired_revision,
            )
        )
        if not v or v.validation_status != "VALIDATED":
            raise HTTPException(409, "Configuration is not validated")
        a.downloaded_revision = v.revision
        db.commit()
        return item(v)


def verify_reception(db, agent, version):
    """Only the server can verify a revision, using post-application receipts."""
    import yaml

    if not agent.applied_at or agent.configuration_sha256 != version.sha256:
        return False
    signals = {
        key.split("/")[0]
        for key in yaml.safe_load(version.yaml_text)
        .get("service", {})
        .get("pipelines", {})
    }
    if version.agent_configuration.get("services") or version.agent_configuration.get(
        "processes"
    ):
        signals.add("metrics")
    if not signals:
        return False
    observed = set(
        db.scalars(
            select(TelemetryReceipt.signal).where(
                TelemetryReceipt.agent_id == agent.id,
                TelemetryReceipt.received_at >= agent.applied_at,
                TelemetryReceipt.record_count > 0,
            )
        ).all()
    )
    if not signals <= observed:
        return False
    if agent.verified_revision == version.revision:
        return True
    agent.verified_revision = version.revision
    agent.last_working_revision = version.revision
    agent.verified_at = utc()
    for deployment in db.scalars(
        select(AgentDeployment).where(
            AgentDeployment.agent_id == agent.id,
            AgentDeployment.revision == version.revision,
            AgentDeployment.status == "APPLIED",
        )
    ):
        deployment.status = "VERIFIED"
        deployment.completed_at = utc()
    log_event(
        db,
        event_type="AGENT_CONFIG_VERIFIED",
        outcome="SUCCESS",
        organization_id=agent.organization_id,
        target_type="agent",
        target_id=agent.id,
    )
    return True


@agent_router.post("/credentials/renew")
def renew_credentials(request: Request):
    # Extending the authenticated credential avoids token handover races with
    # the running upstream Collector. Revocation immediately disables it.
    with SessionLocal() as db:
        agent, collector, source, worker = authenticate(db, request)
        worker.expires_at = utc() + timedelta(days=90)
        agent.credential_renewed_at = utc()
        log_event(
            db,
            event_type="AGENT_CREDENTIAL_RENEW",
            outcome="SUCCESS",
            organization_id=agent.organization_id,
            target_type="agent",
            target_id=agent.id,
        )
        db.commit()
        return {"expires_at": worker.expires_at, "agent_id": agent.id}


@agent_router.post("/credentials/rotate")
def rotate_credentials(request: Request):
    with SessionLocal() as db:
        agent, collector, source, worker = authenticate(db, request)
        token = secrets.token_urlsafe(48)
        agent.previous_token_hash = worker.token_hash
        agent.previous_token_expires_at = utc() + timedelta(minutes=5)
        worker.token_hash = token_digest(token)
        worker.expires_at = utc() + timedelta(days=90)
        agent.credential_renewed_at = utc()
        log_event(
            db,
            event_type="AGENT_CREDENTIAL_ROTATE",
            outcome="SUCCESS",
            organization_id=agent.organization_id,
            target_type="agent",
            target_id=agent.id,
        )
        db.commit()
        return {
            "access_token": token,
            "expires_at": worker.expires_at,
            "previous_valid_until": agent.previous_token_expires_at,
        }


class Apply(Strict):
    revision: int = Field(ge=1)
    approve: bool


@router.post("/collectors/{id}/apply")
def apply(id: uuid.UUID, payload: Apply, db=Depends(get_db)):
    c, s = parent(db, id, True)
    a = db.scalar(
        select(ManagedAgent).where(
            ManagedAgent.collector_id == id, ManagedAgent.enabled.is_(True)
        )
    )
    v = db.scalar(
        select(CollectorConfigVersion).where(
            CollectorConfigVersion.collector_id == id,
            CollectorConfigVersion.revision == payload.revision,
        )
    )
    if not payload.approve:
        raise HTTPException(422, "Explicit application approval required")
    if not a:
        raise HTTPException(
            409,
            "Install and register an agent first; remote installation is not available",
        )
    if not v or v.validation_status != "VALIDATED":
        raise HTTPException(
            409, "Actual Collector validation required before application"
        )
    p = require_permission("collectors.manage", s.organization_id)
    d = AgentDeployment(
        organization_id=s.organization_id,
        agent_id=a.id,
        revision=v.revision,
        previous_revision=a.applied_revision,
        actor_id=p.user_id,
    )
    db.add(d)
    a.desired_revision = v.revision
    commit(db, s, "CONFIG_APPLY_APPROVED", id)
    return item(d)


@router.delete("/collectors/{id}/agent", status_code=204)
def revoke(id: uuid.UUID, db=Depends(get_db)):
    c, s = parent(db, id, True)
    a = db.scalar(select(ManagedAgent).where(ManagedAgent.collector_id == id))
    if not a:
        raise HTTPException(404, "Agent unavailable")
    a.enabled = False
    a.previous_token_hash = None
    a.previous_token_expires_at = None
    # The request write policy allows only revocation of this exact bound
    # credential; WorkerIdentity remains closed to general human mutations.
    db.info["agent_revocation_worker"] = a.worker_id
    db.get(WorkerIdentity, a.worker_id).enabled = False
    commit(db, s, "AGENT_REVOKE", a.id)


@router.get("/packages/{platform}")
def package(platform: str):
    from pathlib import Path
    from fastapi.responses import FileResponse

    if platform not in ("linux", "windows"):
        raise HTTPException(404, "Unsupported agent platform")
    require_permission("collectors.view")
    root = os.getenv("OPSCONTROL_AGENT_PACKAGE_DIR")
    file = Path(root) / ("opscontrol-agent-" + platform + ".zip") if root else None
    if file is None or not file.is_file():
        raise HTTPException(503, "Approved agent package has not been provisioned")
    return FileResponse(file, media_type="application/zip", filename=file.name)


@router.get("/collectors/{id}/template-defaults")
def template_defaults(id: uuid.UUID, db=Depends(get_db)):
    """Reuse attached immutable packages; offer explicit drafts, never deploy."""
    import re
    from app.services.template_resolution import resolve_data_source_configuration

    c, source = parent(db, id)
    require_permission("templates.view", source.organization_id)
    effective = resolve_data_source_configuration(db, source.id)
    meta = (source.connection_config or {}).get("opscontrol", {})
    values = {
        row.get("key"): row.get("defaultValue") for row in effective["attributes"]
    }
    values.update(meta.get("attributes", {}))
    values.update(
        {
            key: meta.get(key)
            for key in ("hostname", "environment", "application")
            if meta.get(key)
        }
    )

    def resolve(text):
        def substitute(match):
            value = values.get(match.group(1))
            if value in (None, ""):
                raise ValueError("Supply Data Source attribute " + match.group(1))
            return str(value)

        return re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", substitute, text)

    methods = []
    errors = []
    for row in effective["logs"]:
        if not row.get("enabled", True):
            continue
        source_type = row.get("source", row.get("source_type", "FILE"))
        if source_type not in ("FILE", "JOURNALD", "WINDOWS_EVENT"):
            errors.append(
                "Legacy log source is not a host-agent method: " + str(source_type)
            )
            continue
        try:
            configuration = {
                "source": source_type,
                "format": "JSON" if row.get("parser") == "JSON" else "TEXT",
            }
            if source_type == "FILE":
                configuration["paths"] = [
                    resolve(row.get("path", row.get("location", "")))
                ]
            if source_type == "WINDOWS_EVENT":
                configuration["channel"] = row.get("channel", "Application")
            method = MethodInput(
                name=row.get("name") or "Template log source",
                method_type="FILE_LOG",
                configuration=configuration,
            )
            validate_method(method, host_os(source))
            methods.append(method.model_dump(exclude={"expected_revision"}))
        except ValueError as error:
            errors.append(str(error))
    return {
        "methods": methods,
        "templates": effective["templates"],
        "missing_required_attributes": effective["missing_required_attributes"],
        "warnings": errors,
        "saved": False,
        "deployed": False,
    }
