"""Tenant-bound remote HTTP probe dispatch, leasing, and evidence ingestion.

Agent pull only. All operations are database transactions; no remote shell,
generic URL fetching, browser JS, or arbitrary task execution.
"""
import hashlib
import json
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, get_db
from app.models import Collector, CollectorRun, DataSource, MetricDefinition, MetricSample, Organization
from app.security.audit import log_event
from app.security.http import require_admin, token_digest
from app.security.models import WorkerIdentity
from app.worker.egress import EgressDenied, check_target, policy_cidrs, policy_hosts
from app.worker.alert_engine import evaluate_metric_sample
from app.worker.remote_models import RemoteProbeJob, RemoteProbeEvidence

worker_router = APIRouter(prefix="/api/v1/worker", tags=["Remote Probe Workers"])
admin_router = APIRouter(prefix="/api/v1/remote-probes", tags=["Remote Probe Administration"])

def utc(): return datetime.now(timezone.utc)

class NetworkPolicy(BaseModel):
    model_config=ConfigDict(extra="forbid")
    allowed_hosts: list[str] = Field(min_length=1,max_length=64)
    allowed_cidrs: list[str] = Field(min_length=1,max_length=32)

class AssignmentRequest(BaseModel):
    model_config=ConfigDict(extra="forbid")
    worker_id: uuid.UUID

@admin_router.put("/collectors/{collector_id}/assignment")
def assign_collector(collector_id:uuid.UUID,payload:AssignmentRequest):
    principal=require_admin()
    with SessionLocal() as db:
        worker=db.get(WorkerIdentity,payload.worker_id)
        collector=db.get(Collector,collector_id)
        if not worker or not worker.enabled or worker.expires_at.replace(tzinfo=timezone.utc)<=utc():
            raise HTTPException(404,"Worker not available")
        if not collector or not collector.enabled:
            raise HTTPException(404,"Collector not available")
        source=db.get(DataSource,collector.data_source_id)
        if not source or not source.enabled or source.organization_id!=worker.organization_id:
            raise HTTPException(403,"Organization mismatch")
        _snapshot(collector,source,worker)
        collector.remote_worker_id=worker.id
        collector.next_run_at=utc()
        # Legacy worker must stop; new scheduler owns this collector.
        collector.status="STOPPED"
        log_event(db,event_type="REMOTE_ASSIGN",outcome="SUCCESS",actor_id=principal.user_id,
                  organization_id=worker.organization_id,target_type="collector",target_id=collector_id)
        db.commit()
        return {"collector_id":str(collector_id),"worker_id":str(worker.id),"scheduled":True}

@admin_router.delete("/collectors/{collector_id}/assignment",status_code=204)
def unassign_collector(collector_id:uuid.UUID):
    principal=require_admin()
    with SessionLocal() as db:
        collector=db.get(Collector,collector_id)
        if not collector: raise HTTPException(404,"Collector not found")
        source=db.get(DataSource,collector.data_source_id)
        for job in db.scalars(select(RemoteProbeJob).where(
                RemoteProbeJob.collector_id==collector_id,
                RemoteProbeJob.state.in_(["QUEUED","LEASED"]))).all():
            job.state="CANCELLED"
            job.lease_nonce_hash=None
        collector.remote_worker_id=None
        collector.enabled=False   # cannot fall back to legacy local polling
        collector.status="STOPPED"
        log_event(db,event_type="REMOTE_UNASSIGN",outcome="SUCCESS",actor_id=principal.user_id,
                  organization_id=source.organization_id if source else None,
                  target_type="collector",target_id=collector_id)
        db.commit()

class QueueRequest(BaseModel):
    model_config=ConfigDict(extra="forbid")
    collector_id: uuid.UUID
    worker_id: uuid.UUID
    idempotency_key: uuid.UUID

class EvidenceInput(BaseModel):
    model_config=ConfigDict(extra="forbid")
    event_id: uuid.UUID
    job_id: uuid.UUID
    lease_nonce: str = Field(min_length=40,max_length=160)
    outcome: Literal["SUCCESS","ASSERTION_FAILED","NETWORK_ERROR","TLS_ERROR","TIMEOUT"]
    observed_at: datetime
    http_status: int | None = Field(default=None,ge=100,le=599)
    response_time_ms: int | None = Field(default=None,ge=0,le=600000)
    response_size_bytes: int | None = Field(default=None,ge=0,le=65536)

def worker_from_request(request: Request):
    raw=request.headers.get("authorization","").split()
    if len(raw)!=2 or raw[0]!="Bearer" or len(raw[1])>256:
        raise HTTPException(401,"Worker authentication required")
    with SessionLocal() as db:
        worker=db.scalar(select(WorkerIdentity).where(WorkerIdentity.token_hash==token_digest(raw[1])))
        if worker is None or not worker.enabled or worker.expires_at.replace(tzinfo=timezone.utc)<=utc():
            raise HTTPException(401,"Invalid or expired worker identity")
        org=db.get(Organization,worker.organization_id)
        if org is None or not org.active:
            raise HTTPException(403,"Worker organization inactive")
        return {"id":worker.id,"organization_id":worker.organization_id}

@admin_router.put("/workers/{worker_id}/network-policy")
def update_network_policy(worker_id:uuid.UUID,payload:NetworkPolicy):
    actor=require_admin()
    try:
        hosts=policy_hosts(payload.allowed_hosts)
        nets=policy_cidrs(payload.allowed_cidrs)
    except EgressDenied as exc: raise HTTPException(422,str(exc))
    with SessionLocal() as db:
        worker=db.get(WorkerIdentity,worker_id)
        if not worker or not worker.enabled: raise HTTPException(404,"Worker not available")
        worker.allowed_hosts=hosts
        worker.allowed_cidrs=[str(n) for n in nets]
        log_event(db,event_type="WORKER_POLICY",outcome="SUCCESS",actor_id=actor.user_id,
                  organization_id=worker.organization_id,target_type="worker",target_id=worker_id)
        db.commit()
        return {"worker_id":str(worker.id),"approved_hosts":hosts,"approved_cidrs":worker.allowed_cidrs}

def _snapshot(collector:Collector,source:DataSource,worker:WorkerIdentity):
    cfg=collector.configuration or {}
    if collector.collector_type.upper() not in {"HTTP","API"} or not isinstance(cfg,dict):
        raise HTTPException(422,"Only configured HTTP probes supported by this worker protocol")
    url=cfg.get("url") or source.endpoint
    if not isinstance(url,str): raise HTTPException(422,"HTTPS probe URL required")
    snapshot={"url":url,"expected_status":cfg.get("expected_status",200),
              "timeout_seconds":cfg.get("timeout_seconds",8)}
    try:
        check_target(url,worker.allowed_hosts,worker.allowed_cidrs)
        if type(snapshot["expected_status"]) is not int or not 100<=snapshot["expected_status"]<=599:
            raise EgressDenied("Invalid expected status")
        if type(snapshot["timeout_seconds"]) is not int or not 1<=snapshot["timeout_seconds"]<=10:
            raise EgressDenied("Timeout must be between 1 and 10 seconds")
    except EgressDenied as exc: raise HTTPException(422,str(exc))
    return snapshot

@admin_router.post("/jobs",status_code=201)
def enqueue_probe(payload:QueueRequest):
    actor=require_admin()
    with SessionLocal() as db:
        worker=db.get(WorkerIdentity,payload.worker_id)
        collector=db.scalar(select(Collector).where(Collector.id==payload.collector_id).with_for_update())
        if not worker or not worker.enabled or worker.expires_at.replace(tzinfo=timezone.utc)<=utc():
            raise HTTPException(404,"Worker not available")
        if not collector or not collector.enabled: raise HTTPException(404,"Collector not available")
        source=db.get(DataSource,collector.data_source_id)
        if not source or not source.enabled or source.organization_id!=worker.organization_id:
            raise HTTPException(403,"Worker cannot access this collector")
        if collector.remote_worker_id!=worker.id:
            raise HTTPException(403,"Collector is not assigned to this worker")
        snapshot=_snapshot(collector,source,worker)
        existing=db.get(RemoteProbeJob,payload.idempotency_key)
        if existing:
            if existing.collector_id!=collector.id or existing.assigned_worker_id!=worker.id:
                raise HTTPException(409,"Idempotency key already used")
            return {"job_id":str(existing.id),"state":existing.state,"duplicate":True}
        pending=db.scalar(select(RemoteProbeJob.id).where(
            RemoteProbeJob.collector_id==collector.id,
            RemoteProbeJob.state.in_(["QUEUED","LEASED"])).limit(1))
        if pending:
            raise HTTPException(409,"Collector already has an outstanding remote job")
        job=RemoteProbeJob(id=payload.idempotency_key,organization_id=worker.organization_id,
            collector_id=collector.id,assigned_worker_id=worker.id,planned_for=utc(),
            config_snapshot=snapshot,state="QUEUED",attempts=0)
        db.add(job)
        log_event(db,event_type="REMOTE_JOB_QUEUED",outcome="SUCCESS",actor_id=actor.user_id,
                  organization_id=job.organization_id,target_type="remote-job",target_id=job.id)
        db.commit()
        return {"job_id":str(job.id),"state":"QUEUED","duplicate":False}

@worker_router.post("/claim")
def claim_probe(identity=Depends(worker_from_request)):
    with SessionLocal() as db:
        now=utc()
        worker=db.get(WorkerIdentity,identity["id"])
        stmt=(select(RemoteProbeJob)
              .where(RemoteProbeJob.assigned_worker_id==identity["id"],
                     RemoteProbeJob.organization_id==identity["organization_id"],
                     RemoteProbeJob.attempts<3,
                     ((RemoteProbeJob.state=="QUEUED") |
                      ((RemoteProbeJob.state=="LEASED") & (RemoteProbeJob.lease_expires_at<now))))
              .order_by(RemoteProbeJob.planned_for)
              .with_for_update(skip_locked=True).limit(1))
        job=db.scalar(stmt)
        if not job: return {"job":None}
        collector=db.get(Collector,job.collector_id)
        source=db.get(DataSource,collector.data_source_id) if collector else None
        if not collector or not collector.enabled or not source or not source.enabled or source.organization_id!=worker.organization_id or collector.remote_worker_id!=worker.id:
            job.state="CANCELLED"
            db.commit()
            return {"job":None}
        try:
            _snapshot(collector,source,worker)
            check_target(job.config_snapshot["url"],worker.allowed_hosts,worker.allowed_cidrs)
        except (HTTPException,EgressDenied):
            job.state="CANCELLED"
            db.commit()
            return {"job":None}
        nonce=secrets.token_urlsafe(48)
        job.lease_nonce_hash=token_digest(nonce)
        job.lease_expires_at=now+timedelta(seconds=90)
        job.state="LEASED"
        job.attempts+=1
        run_id=uuid.uuid4()
        job.run_id=run_id
        db.commit()
        return {"job":{"job_id":str(job.id),"run_id":str(run_id),"lease_nonce":nonce,
                       "lease_expires_at":job.lease_expires_at.isoformat(),
                       "config":job.config_snapshot,
                       "network_policy":{"allowed_hosts":worker.allowed_hosts,
                                         "allowed_cidrs":worker.allowed_cidrs}}}

def canonical_result(payload:EvidenceInput):
    # Never accept arbitrary messages, response bodies, headers or credentials.
    return payload.model_dump(mode="json",exclude={"lease_nonce"})

@worker_router.post("/results",status_code=202)
def ingest_probe(payload:EvidenceInput,identity=Depends(worker_from_request)):
    now=utc()
    if payload.observed_at.tzinfo is None:
        raise HTTPException(422,"Observed time must contain UTC offset")
    if abs((now-payload.observed_at.astimezone(timezone.utc)).total_seconds())>300:
        raise HTTPException(422,"Observed timestamp outside allowed window")
    result=canonical_result(payload)
    digest=hashlib.sha256(json.dumps(result,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    with SessionLocal() as db:
        # Lock job first, then check event id and lease to prevent double completion.
        job=db.scalar(select(RemoteProbeJob).where(RemoteProbeJob.id==payload.job_id).with_for_update())
        if job is None or job.assigned_worker_id!=identity["id"] or job.organization_id!=identity["organization_id"]:
            raise HTTPException(404,"Job unavailable")
        previous=db.scalar(select(RemoteProbeEvidence).where(RemoteProbeEvidence.job_id==job.id))
        if previous:
            if previous.event_id==payload.event_id and previous.payload_sha256==digest:
                return {"accepted":True,"duplicate":True}
            raise HTTPException(409,"Conflicting or replayed result")
        if (job.state!="LEASED" or job.lease_expires_at is None or job.lease_expires_at<=now
            or job.lease_nonce_hash!=token_digest(payload.lease_nonce)):
            raise HTTPException(409,"Lease expired, revoked or invalid")
        collector=db.get(Collector,job.collector_id)
        source=db.get(DataSource,collector.data_source_id) if collector else None
        if not collector or not collector.enabled or not source or not source.enabled or source.organization_id!=identity["organization_id"] or collector.remote_worker_id!=identity["id"]:
            raise HTTPException(409,"Collector no longer authorized")
        if db.scalar(select(RemoteProbeEvidence).where(RemoteProbeEvidence.event_id==payload.event_id)):
            raise HTTPException(409,"Event id already used")
        evidence=RemoteProbeEvidence(event_id=payload.event_id,job_id=job.id,
             organization_id=identity["organization_id"],worker_id=identity["id"],
             observed_at=payload.observed_at,result=result,payload_sha256=digest)
        db.add(evidence)
        run=CollectorRun(id=job.run_id,collector_id=collector.id,started_at=payload.observed_at,
             ended_at=now,status="SUCCESS" if payload.outcome=="SUCCESS" else "FAILED",
             outcome=payload.outcome,http_status=payload.http_status,
             response_time_ms=payload.response_time_ms,response_size_bytes=payload.response_size_bytes)
        db.add(run)
        collector.last_run_at=now
        if payload.outcome=="SUCCESS":
            collector.last_success_at=now
            collector.status="SUCCESS"
        else:
            collector.last_error_at=now
            collector.status="ERROR"
            collector.last_error=payload.outcome
        # Only existing compatible MetricDefinition registrations are populated.
        for metric in db.scalars(select(MetricDefinition).where(
                MetricDefinition.collector_id==collector.id,
                MetricDefinition.organization_id==identity["organization_id"],
                MetricDefinition.enabled.is_(True))).all():
            name=metric.name.lower()
            if name in {"probe_up","http_up","http_availability"}:
                value=1.0 if payload.outcome=="SUCCESS" else 0.0
            elif name in {"http_response_time_ms","response_time_ms"} and payload.response_time_ms is not None:
                value=float(payload.response_time_ms)
            else: continue
            sample=MetricSample(organization_id=identity["organization_id"],
                metric_definition_id=metric.id,collector_id=collector.id,collector_run_id=run.id,
                observed_at=payload.observed_at,value_numeric=value,unit=metric.unit)
            db.add(sample)
            db.flush()
            evaluate_metric_sample(db,sample)
        job.state="COMPLETED"
        job.completed_at=now
        job.lease_nonce_hash=None
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409,"Evidence event conflicts with another result")
        return {"accepted":True,"duplicate":False}

@admin_router.get("/jobs/{job_id}")
def get_remote_job(job_id:uuid.UUID,db:Session=Depends(get_db)):
    require_admin()  # until explicitly tenant-scoped resource model access is available
    job=db.get(RemoteProbeJob,job_id)
    if not job: raise HTTPException(404,"Job not found")
    return {"job_id":str(job.id),"organization_id":str(job.organization_id),
            "collector_id":str(job.collector_id),"state":job.state,
            "attempts":job.attempts,"created_at":job.created_at.isoformat(),
            "completed_at":job.completed_at.isoformat() if job.completed_at else None}
