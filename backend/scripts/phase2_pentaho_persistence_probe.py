"""Transactional Carte-to-ETL history ingestion, idempotency, tenant protections.

CI invokes on disposable seeded PostgreSQL. Network transport is unit-tested
separately; no live Carte instance or credentials are required for this proof.
"""
from datetime import datetime,timezone,timedelta
from sqlalchemy import select,func
from app.db.session import SessionLocal
import app.security.models  # register referenced service-identity tables
from app.models import Organization,JobOrder,JobOrderHistory,Collector,DataSource
from app.worker.collector_runtime import CollectionResult,_persist_pentaho_history

def main():
    with SessionLocal() as db:
        north=db.scalar(select(Organization).where(Organization.code=="LAB-N"))
        south=db.scalar(select(Organization).where(Organization.code=="LAB-S"))
        job=db.scalar(select(JobOrder).where(JobOrder.organization_id==north.id))
        other_job=db.scalar(select(JobOrder).where(JobOrder.organization_id==south.id))
        source=db.scalar(select(DataSource).where(DataSource.organization_id==north.id))
        from uuid import uuid4
        probe=Collector(data_source_id=source.id,name="pentaho-history-test",collector_type="PENTAHO",
                        enabled=False,configuration={"job_order_id":str(job.id)})
        db.add(probe);db.flush()
        instant=datetime.now(timezone.utc)
        status=lambda run,state,errors=0:CollectionResult(state in {"RUNNING","SUCCESS"},
            "Fixture execution collected",{"provider":"PENTAHO","execution_id":run,
            "execution_status":state,"nr_errors":errors,"outcome":"SUCCESS"})
        _persist_pentaho_history(probe,status("fake-run-01","RUNNING"),instant,db)
        db.flush()
        _persist_pentaho_history(probe,status("fake-run-01","SUCCESS"),instant+timedelta(minutes=1),db)
        db.flush()
        records=db.scalars(select(JobOrderHistory).where(
            JobOrderHistory.job_order_id==job.id,
            JobOrderHistory.provider_execution_id=="fake-run-01")).all()
        assert len(records)==1 and records[0].status.value=="SUCCESS"
        _persist_pentaho_history(probe,status("fake-run-02","FAILED",errors=1),
                                  instant+timedelta(minutes=2),db)
        db.flush()
        assert db.scalar(select(func.count()).select_from(JobOrderHistory).where(
            JobOrderHistory.job_order_id==job.id,
            JobOrderHistory.provider_execution_id.is_not(None)))==2
        # Foreign-organization JobOrder assignment is never accepted.
        probe.configuration={"job_order_id":str(other_job.id)}
        _persist_pentaho_history(probe,status("fake-run-03","SUCCESS"),
                                  instant+timedelta(minutes=3),db)
        db.flush()
        assert db.scalar(select(func.count()).select_from(JobOrderHistory).where(
            JobOrderHistory.provider_execution_id=="fake-run-03"))==0
        db.rollback()
    print("PENTAHO READ-ONLY STATUS PERSISTENCE / DEDUPLICATION / TENANCY PASS")

if __name__=="__main__":main()
