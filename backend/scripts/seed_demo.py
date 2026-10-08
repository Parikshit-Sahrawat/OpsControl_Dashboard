from datetime import datetime, timezone, timedelta
from app.db.session import SessionLocal
from app.models import Organization, VM, PentahoInstance, JobOrder, JobOrderHistory, JobStepExecution, ExecutionType, ExecutionStatus

def add_job(db, org, vm, pentaho, name, status, start, duration, expected, sla, incident=None, failed_step=None):
    jo=JobOrder(organization_id=org.id,vm_id=vm.id,pentaho_instance_id=pentaho.id,name=name,environment="PROD",expected_runtime_seconds=expected,sla_seconds=sla,schedule={"type":"daily","time":"08:00"},expected_window_start="08:00",expected_window_end="08:15",no_run_grace_seconds=900)
    db.add(jo);db.flush()
    ended=start+timedelta(seconds=duration) if duration is not None else None
    h=JobOrderHistory(job_order_id=jo.id,execution_type=ExecutionType.SCHEDULED,status=status,started_at=start,ended_at=ended,detected_at=start+timedelta(seconds=5),expected_runtime_seconds=expected,sla_seconds=sla,sla_status="BREACHED" if duration and duration>=sla else "AT RISK" if duration and duration>=expected else "ON TRACK",failed_step=failed_step,source_error_message="Connection timeout" if status==ExecutionStatus.FAILED else None,incident_number=incident)
    db.add(h);db.flush()
    if status==ExecutionStatus.FAILED:
        db.add_all([JobStepExecution(history_id=h.id,name="Extract Customer Data",step_type="Table Input",status="SUCCESS",duration_seconds=71),JobStepExecution(history_id=h.id,name="Transform Pricing",step_type="Transformation",status="SUCCESS",duration_seconds=189),JobStepExecution(history_id=h.id,name=failed_step or "Failed step",step_type="Table Output",status="FAILED",duration_seconds=1,error_message="Connection timeout")])
def main():
    db=SessionLocal()
    try:
        if db.query(Organization).first(): print("Demo data already exists; no changes made."); return
        org=Organization(name="ABC Corporation",code="ABC");db.add(org);db.flush()
        vm=VM(organization_id=org.id,hostname="HERO-PRDAPP001",environment="PROD",os="Windows Server");db.add(vm);db.flush()
        pentaho=PentahoInstance(vm_id=vm.id,name="PENTAHO-PROD-01");db.add(pentaho);db.flush()
        now=datetime.now(timezone.utc).replace(second=0,microsecond=0)
        add_job(db,org,vm,pentaho,"JC_Pricing_Daily",ExecutionStatus.FAILED,now-timedelta(minutes=10),348,1200,1800,"INC0012345","Update Customer Database")
        add_job(db,org,vm,pentaho,"Job_SPP_PAI",ExecutionStatus.RUNNING,now-timedelta(minutes=18),None,900,1800)
        add_job(db,org,vm,pentaho,"Customer_Extract",ExecutionStatus.LONG_RUNNING,now-timedelta(minutes=24),1441,1200,1500,"INC0012339")
        add_job(db,org,vm,pentaho,"Inventory_Daily",ExecutionStatus.SUCCESS,now-timedelta(hours=1),1053,1200,1800)
        db.commit();print("Demo data seeded.")
    finally: db.close()
if __name__=="__main__": main()
