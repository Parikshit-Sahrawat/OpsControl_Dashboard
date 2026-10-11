"""Verify populated Sprint 3 alert backfill before starting the disposable NOC lab."""
import json, os, sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
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
        history=JobOrderHistory(job_order_id=job.id,execution_type=ExecutionType.SCHEDULED,status=ExecutionStatus.FAILED,detected_at=now-timedelta(days=2));db.add(history);db.flush()
        source=DataSource(organization_id=org.id,name='Historical HTTP source',source_type='API');db.add(source);db.flush()
        metric=MetricDefinition(organization_id=org.id,data_source_id=source.id,name='archive-up',resource_type='APPLICATION',metric_type='GAUGE');db.add(metric);db.flush()
        rule=AlertRule(organization_id=org.id,metric_definition_id=metric.id,name='archive-outage',operator='LT',threshold_value='.5');db.add(rule);db.flush()
        for status in ('OPEN','RESOLVED'):
            db.add(AlertState(organization_id=org.id,alert_rule_id=rule.id,metric_definition_id=metric.id,status=status,severity='CRITICAL',
                first_triggered_at=now-timedelta(days=2),last_evaluated_at=now-timedelta(days=1),resolved_at=now-timedelta(days=1) if status=='RESOLVED' else None,last_value=0,message='Controlled archived alert'))
        for index,event_type in enumerate(('JOB_FAILED_OPEN','JOB_FAILED_RESOLVED','JOB_FAILED_OPEN')):
            db.add(AlertIncidentEvent(history_id=history.id,event_type=event_type,source='ETL_MONITOR',reference='archive-condition',severity='CRITICAL',timestamp=now-timedelta(days=2)+timedelta(seconds=index)))
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
