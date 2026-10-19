"""Verify populated Sprint 3 alert backfill before starting the disposable NOC lab."""
import json, os, sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, text
from app.db.session import SessionLocal
from app.models import (Organization, VM, JobOrder, JobOrderHistory, ExecutionType, ExecutionStatus,
    DataSource, MetricDefinition, AlertRule, AlertState, AlertIncidentEvent, OperationalIncident, IncidentActivity)
private=Path(os.environ['ETL_PRIVATE_DIR'])
def seed():
    now=datetime.now(timezone.utc)
    with SessionLocal() as db:
        org=Organization(name='Controlled migration archive',code='NOC-MIGRATION');db.add(org);db.flush()
        vm=VM(organization_id=org.id,hostname='archive.example.test',environment='TEST');db.add(vm);db.flush()
        job=JobOrder(organization_id=org.id,vm_id=vm.id,name='Historical ETL failure');db.add(job);db.flush()
        # Seed the historical 0020 schema with its own column contract, not the
        # current JobOrderHistory ORM mapping (which includes 0033+ Pentaho fields).
        import uuid
        history_id = uuid.uuid4()
        db.execute(text("""INSERT INTO job_order_histories
            (id,job_order_id,execution_type,status,detected_at,created_at)
            VALUES (:id,:job,:execution_type,:status,:detected_at,:created_at)"""),
            {'id':history_id,'job':job.id,'execution_type':ExecutionType.SCHEDULED.value,
             'status':ExecutionStatus.FAILED.value,'detected_at':now-timedelta(days=2),'created_at':now})
        source=DataSource(organization_id=org.id,name='Historical HTTP source',source_type='API');db.add(source);db.flush()
        metric=MetricDefinition(organization_id=org.id,data_source_id=source.id,name='archive-up',resource_type='APPLICATION',metric_type='GAUGE');db.add(metric);db.flush()
        # Target is intentionally the old 0020 schema: do not INSERT current
        # ORM-only acknowledgment/evaluation columns into that historical DB.
        import uuid
        rule_id=uuid.uuid4()
        db.execute(text("INSERT INTO alert_rules(id,organization_id,metric_definition_id,name,severity,operator,threshold_value,evaluation_window_seconds,consecutive_breaches,enabled,created_at,updated_at) VALUES (:id,:org,:metric,'archive-outage','WARNING','LT','.5',60,1,true,:now,:now)"),{'id':rule_id,'org':org.id,'metric':metric.id,'now':now})
        for status in ('OPEN','RESOLVED'):
            db.execute(text("INSERT INTO alert_states(id,organization_id,alert_rule_id,metric_definition_id,status,severity,first_triggered_at,last_evaluated_at,resolved_at,last_value,breach_count,message,created_at,updated_at) VALUES (:id,:org,:rule,:metric,:status,'CRITICAL',:first,:last,:resolved,0,0,'Controlled archived alert',:now,:now)"),{'id':uuid.uuid4(),'org':org.id,'rule':rule_id,'metric':metric.id,'status':status,'first':now-timedelta(days=2),'last':now-timedelta(days=1),'resolved':now-timedelta(days=1) if status=='RESOLVED' else None,'now':now})
        for index,event_type in enumerate(('JOB_FAILED_OPEN','JOB_FAILED_RESOLVED','JOB_FAILED_OPEN')):
            db.add(AlertIncidentEvent(history_id=history_id,event_type=event_type,source='ETL_MONITOR',reference='archive-condition',severity='CRITICAL',timestamp=now-timedelta(days=2)+timedelta(seconds=index)))
        db.commit()
    print('Populated pre-Sprint-4 metric and ETL alert migration fixtures seeded')
def verify():
    with SessionLocal() as db:
        org=db.scalar(select(Organization).where(Organization.code=='NOC-MIGRATION'))
        rows=db.scalars(select(OperationalIncident).where(OperationalIncident.organization_id==org.id)).all()
        assert len(rows)==4 and sum(r.condition_status=='RECOVERED' for r in rows)==2
        assert all(row.status=='OPEN' for row in rows) # no invented operator resolution
        events=db.scalars(select(IncidentActivity).where(IncidentActivity.organization_id==org.id)).all()
        assert len(events)==6 and all(e.actor=='migration' for e in events)
        snapshot=sorted(str(row.id) for row in rows)
    path=private/'migration-snapshot.json'
    if path.exists():assert json.loads(path.read_text())==snapshot
    path.write_text(json.dumps(snapshot))
    print('Populated alert backfill / deterministic episodes / recovery history / upgrade repeatability PASS')
if __name__=='__main__':seed() if sys.argv[1]=='seed' else verify()
