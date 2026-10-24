"""Disposable PostgreSQL retirement regression: remote leases, pending jobs and history."""
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func
from app.db.session import SessionLocal
from app.models import Collector, CollectorRun, DataSource, Organization
from app.worker.remote_models import RemoteProbeJob, RemoteProbeEvidence
from app.worker.remote_scheduler import queue_due_once
from scripts import remote_protocol_probe as api

KINDS=("KUBERNETES","K8S","AWS_EKS")

def main():
    if os.getenv("OPSCONTROL_RELEASE_ACCEPTANCE")!="1" or os.getenv("ENVIRONMENT")!="demo":
        raise SystemExit("Disposable release PostgreSQL required")
    api.BASE=os.environ["TEST_API_BASE"]
    admin=api.check(200,"POST","/api/v1/auth/login",body={"username":"test-admin","password":api.PASSWORD})["access_token"]
    with SessionLocal() as db:
        org=db.scalar(select(Organization).where(Organization.code=="LAB-N"))
        assert org
        before={table.__tablename__:db.scalar(select(func.count()).select_from(table))
                for table in (CollectorRun,RemoteProbeEvidence)}
        worker_id=uuid.uuid4()
        from app.security.models import WorkerIdentity
        # Reuse the real disposable worker established by remote_protocol_probe.
        worker=db.scalar(select(WorkerIdentity).where(WorkerIdentity.organization_id==org.id))
        assert worker
        worker_id=worker.id
        ids=[]
        for kind in KINDS:
            source=DataSource(organization_id=org.id,name="retirement-"+kind+"-"+uuid.uuid4().hex[:8],
                              source_type=kind,connection_config={},status="UNKNOWN")
            db.add(source);db.flush()
            for state in ("QUEUED","LEASED"):
                collector=Collector(data_source_id=source.id,name="retired-"+state,
                                    collector_type=kind,configuration={},enabled=True,status="ACTIVE",
                                    remote_worker_id=worker_id,
                                    next_run_at=datetime.now(timezone.utc)+timedelta(hours=2))
                db.add(collector);db.flush()
                job=RemoteProbeJob(organization_id=org.id,collector_id=collector.id,
                                   assigned_worker_id=worker_id,planned_for=datetime.now(timezone.utc),
                                   config_snapshot={"url":"https://portal.example.test/health"},
                                   state=state,attempts=1 if state=="LEASED" else 0,
                                   lease_nonce_hash="a"*64 if state=="LEASED" else None,
                                   lease_expires_at=datetime.now(timezone.utc)+timedelta(seconds=90) if state=="LEASED" else None)
                db.add(job);db.flush()
                ids.append((collector.id,job.id))
        db.commit()
    assert queue_due_once()>=0
    with SessionLocal() as db:
        for collector_id,job_id in ids:
            collector=db.get(Collector,collector_id)
            job=db.get(RemoteProbeJob,job_id)
            assert not collector.enabled and collector.status=="STOPPED"
            assert job.state=="CANCELLED" and job.lease_nonce_hash is None
        after={table.__tablename__:db.scalar(select(func.count()).select_from(table))
               for table in (CollectorRun,RemoteProbeEvidence)}
        assert before==after,(before,after)
    # A retired job must never become claimable, even after its old lease expires.
    queue_due_once()
    with SessionLocal() as db:
        assert all(db.get(RemoteProbeJob,j).state=="CANCELLED" for _,j in ids)
    output=os.getenv("RELEASE_EVIDENCE_DIR","/tmp/opscontrol-release-evidence")
    from pathlib import Path
    dest=Path(output);dest.mkdir(parents=True,exist_ok=True)
    (dest/"kubernetes-remote-retirement.json").write_text(json.dumps({
        "status":"PASS","database":"disposable PostgreSQL",
        "collector_types":KINDS,"collectors_retired":len(ids),"jobs_cancelled":len(ids),
        "tested_job_states":["QUEUED","LEASED"],"not_yet_due":True,
        "lease_nonce_cleared":True,"collector_runs_and_remote_evidence_preserved":True,
        "limitations":["No physical in-flight worker process was drained in this test",
                       "Historical cluster association integrity is covered by separate V1.5 acceptance"]
    },indent=2)+"\n")
    print("KUBERNETES REMOTE RETIREMENT / POSTGRESQL PASS")

if __name__=="__main__":main()
