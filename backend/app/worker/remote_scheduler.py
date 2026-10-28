"""Safe, durable dispatch of due pre-approved remote collectors.

Run this separately from HTTP API on trusted control-plane backend:
    python -m scripts.run_remote_scheduler

Only an admin-authorized worker binding can schedule remote collection.
Leases, assignments, and due timestamps are all persisted to PostgreSQL.
"""
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, update
from app.db.session import SessionLocal
from app.models import Collector,DataSource,Organization
from app.security.models import WorkerIdentity
from app.worker.remote_models import RemoteProbeJob
from app.worker.egress import EgressDenied

log=logging.getLogger(__name__)

def utc(): return datetime.now(timezone.utc)

def queue_due_once(limit=100):
    now=utc()
    queued=0
    with SessionLocal() as db:
        # Expired 3-attempt leases are terminal rather than blocking
        # future scheduling forever or misrepresenting monitoring as healthy.
        db.execute(update(RemoteProbeJob).where(
            RemoteProbeJob.state=="LEASED",
            RemoteProbeJob.attempts>=3,
            RemoteProbeJob.lease_expires_at<now
        ).values(state="EXPIRED",lease_nonce_hash=None))
        # Retire all remote Kubernetes collectors, including those not yet due,
        # and invalidate queued/leased jobs without deleting their history.
        from app.services.excluded_platforms import require_supported_collector
        from fastapi import HTTPException
        retired_ids=[]
        # Include not-yet-due collectors and admitted jobs; source identity and
        # nested persisted configuration cannot bypass retirement by using HTTP.
        candidates=db.execute(select(Collector,DataSource).join(DataSource,Collector.data_source_id==DataSource.id).where(
            Collector.remote_worker_id.is_not(None),
            (Collector.enabled.is_(True) | Collector.id.in_(select(RemoteProbeJob.collector_id).where(
                RemoteProbeJob.state.in_(("QUEUED","LEASED")))))
        ).with_for_update(of=Collector)).all()
        for collector,source in candidates:
            try:
                require_supported_collector(collector,source)
            except HTTPException:
                collector.enabled=False
                collector.status="STOPPED"
                collector.last_error="Kubernetes monitoring retired; historical evidence retained"
                retired_ids.append(collector.id)
        if retired_ids:
            db.execute(update(RemoteProbeJob).where(
                RemoteProbeJob.collector_id.in_(retired_ids),
                RemoteProbeJob.state.in_(("QUEUED", "LEASED"))
            ).values(state="CANCELLED",lease_nonce_hash=None))
        collectors=db.scalars(
            select(Collector).where(
                Collector.enabled.is_(True),Collector.remote_worker_id.is_not(None),
                ((Collector.next_run_at.is_(None)) | (Collector.next_run_at<=now))
            ).order_by(Collector.next_run_at.nullsfirst()).with_for_update(skip_locked=True).limit(limit)
        ).all()
        for collector in collectors:
            if collector.collector_type.upper() in {"KUBERNETES", "K8S", "AWS_EKS", "EKS", "AKS", "AZURE_AKS", "GKE", "GOOGLE_GKE", "OPENSHIFT"}:
                collector.enabled=False
                collector.status="STOPPED"
                collector.last_error="Kubernetes monitoring retired; historical evidence retained"
                continue
            last=collector.last_run_at or collector.created_at
            if last.tzinfo is None: last=last.replace(tzinfo=timezone.utc)
            if (now-last).total_seconds()>max(2*collector.interval_seconds+30,120):
                collector.status="STALE"
                collector.last_error="No fresh remote monitoring evidence"
            worker=db.get(WorkerIdentity,collector.remote_worker_id)
            source=db.get(DataSource,collector.data_source_id)
            org=db.get(Organization,source.organization_id) if source else None
            if not worker or not worker.enabled or worker.expires_at.replace(tzinfo=timezone.utc)<=now or not source or not source.enabled or not org or not org.active or worker.organization_id!=org.id:
                # Keep a visible monitoring blind spot, not a healthy state.
                collector.status="ERROR"
                collector.last_error="Remote worker or data source unavailable"
                collector.next_run_at=now+timedelta(seconds=60)
                continue
            from app.api.remote_protocol import _snapshot
            try:
                snap=_snapshot(collector,source,worker)
            except Exception:
                collector.status="ERROR"
                collector.last_error="Remote configuration or egress policy invalid"
                collector.next_run_at=now+timedelta(seconds=60)
                continue
            planned=collector.next_run_at or now
            if planned.tzinfo is None: planned=planned.replace(tzinfo=timezone.utc)
            # At most one pending/in-flight job for a collector, bounded queue.
            existing=db.scalar(select(RemoteProbeJob.id).where(
                RemoteProbeJob.collector_id==collector.id,
                RemoteProbeJob.state.in_(["QUEUED","LEASED"])
            ).limit(1))
            if existing is None:
                db.add(RemoteProbeJob(id=uuid.uuid4(),organization_id=org.id,
                    collector_id=collector.id,assigned_worker_id=worker.id,
                    planned_for=planned,config_snapshot=snap,state="QUEUED",attempts=0))
                queued+=1
            collector.next_run_at=now+timedelta(seconds=max(collector.interval_seconds,30))
        db.commit()
    return queued
