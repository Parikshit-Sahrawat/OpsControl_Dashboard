"""Idempotent fictional local demo bootstrap. Never runs outside ENVIRONMENT=demo."""
import os
from datetime import datetime,timedelta,timezone
from pathlib import Path
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models import Organization,VM,JobOrder,JobOrderHistory,ExecutionStatus,ExecutionType,DataSource,Collector
from app.security.models import User
from app.security.passwords import hash_password

def main():
    if os.environ.get("ENVIRONMENT")!="demo":
        raise SystemExit("Public demo bootstrap requires ENVIRONMENT=demo")
    path=Path(os.getenv("OPSCONTROL_DEMO_PASSWORD_FILE","/run/secrets/demo_admin_password"))
    if not path.is_file():
        raise SystemExit("Demo admin password file missing; refusing known default credential")
    password=path.read_text(encoding="utf-8").strip()
    if len(password)<20:
        raise SystemExit("Demo admin password must be a locally generated random value")
    with SessionLocal() as db:
        username="demo-admin"
        if db.scalar(select(User).where(User.username==username)) is None:
            db.add(User(username=username,password_hash=hash_password(password),platform_admin=True))
        org=db.scalar(select(Organization).where(Organization.code=="DEMO-LAB"))
        if org is None:
            org=Organization(name="Fictional Observatory Demo",code="DEMO-LAB")
            db.add(org);db.flush()
        vm=db.scalar(select(VM).where(VM.organization_id==org.id,VM.hostname=="demo-node.example.test"))
        if vm is None:
            vm=VM(organization_id=org.id,hostname="demo-node.example.test",environment="PROD",os="Linux")
            db.add(vm);db.flush()
        now=datetime.now(timezone.utc)
        for name,status,mins in [
            ("Daily Import (synthetic)",ExecutionStatus.SUCCESS,65),
            ("Hourly Inventory Sync (synthetic)",ExecutionStatus.FAILED,32),
            ("Weekly Analytics (synthetic)",ExecutionStatus.RUNNING,11),
        ]:
            job=db.scalar(select(JobOrder).where(JobOrder.organization_id==org.id,
                JobOrder.vm_id==vm.id,JobOrder.name==name))
            if job is None:
                job=JobOrder(organization_id=org.id,vm_id=vm.id,name=name,
                             environment="PROD",expected_runtime_seconds=1800,sla_seconds=3600)
                db.add(job);db.flush()
                db.add(JobOrderHistory(job_order_id=job.id,execution_type=ExecutionType.SCHEDULED,
                    status=status,started_at=now-timedelta(minutes=mins),
                    ended_at=None if status==ExecutionStatus.RUNNING else now-timedelta(minutes=mins-5),
                    detected_at=now-timedelta(minutes=mins),source_result="FICTIONAL_DEMO_ONLY"))
        source=db.scalar(select(DataSource).where(DataSource.organization_id==org.id,
            DataSource.name=="Example internal portal (not connected)"))
        if source is None:
            source=DataSource(organization_id=org.id,name="Example internal portal (not connected)",
                source_type="API",endpoint="https://portal.example.test/ready",
                status="UNKNOWN",enabled=True,description="Illustrative resource; no real private application connected")
            db.add(source);db.flush()
        collector=db.scalar(select(Collector).where(Collector.data_source_id==source.id,
            Collector.name=="example-http-inactive"))
        if collector is None:
            db.add(Collector(data_source_id=source.id,name="example-http-inactive",
                collector_type="HTTP",enabled=False,status="STOPPED",interval_seconds=60,
                configuration={"url":"https://portal.example.test/ready","expected_status":200}))
        db.commit()
    print("Public-safe, fictional demo seeded (no live infrastructure connections).")

if __name__=="__main__":
    main()
