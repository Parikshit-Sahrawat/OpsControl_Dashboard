"""Disposable PostgreSQL API integration tests for remote worker trust boundaries."""
import json
import uuid
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models import DataSource, Collector, MetricDefinition
from app.security.models import WorkerIdentity
from app.worker.remote_models import RemoteProbeJob, RemoteProbeEvidence

BASE="http://127.0.0.1:8000"
PASSWORD="testing-only-StrongPassword-123!"

def req(method,path,token=None,body=None):
    data=json.dumps(body).encode() if body is not None else None
    headers={"Content-Type":"application/json"}
    if token: headers["Authorization"]="Bearer "+token
    request=urllib.request.Request(BASE+path,method=method,data=data,headers=headers)
    try:
        with urllib.request.urlopen(request,timeout=20) as response:
            return response.status,json.loads(response.read() or b"null")
    except urllib.error.HTTPError as response:
        return response.code,json.loads(response.read() or b"null")

def check(status,method,path,token=None,body=None):
    got,payload=req(method,path,token,body)
    assert got==status,(method,path,status,got,payload)
    print("PASS",got,method,path)
    return payload

def main():
    admin=check(200,"POST","/api/v1/auth/login",body={"username":"test-admin","password":PASSWORD})["access_token"]
    viewer=check(200,"POST","/api/v1/auth/login",body={"username":"test-reader","password":PASSWORD})["access_token"]
    with SessionLocal() as db:
        north=db.scalar(select(DataSource).where(DataSource.name=="north-synthetic"))
        south=db.scalar(select(DataSource).where(DataSource.name=="south-synthetic"))
        assert north and south
        collector=Collector(data_source_id=north.id,name="remote-readiness",collector_type="HTTP",
                            configuration={"url":"https://portal.example.test/health","expected_status":200,"timeout_seconds":5})
        db.add(collector)
        db.flush()
        metric=MetricDefinition(organization_id=north.organization_id,data_source_id=north.id,collector_id=collector.id,
                                name="probe_up",metric_type="GAUGE",resource_type="APPLICATION")
        db.add(metric)
        db.flush()
        ids={"collector":str(collector.id),"org_n":str(north.organization_id),"org_s":str(south.organization_id),
             "metric":str(metric.id)}
        db.commit()
    worker=check(201,"POST","/api/v1/auth/workers",admin,
                 {"organization_id":ids["org_n"],"name":"remote-agent-lab","expires_in_days":1})
    other=check(201,"POST","/api/v1/auth/workers",admin,
                 {"organization_id":ids["org_s"],"name":"remote-agent-other","expires_in_days":1})
    token=worker["worker_token"]
    other_token=other["worker_token"]
    check(401,"POST","/api/v1/worker/claim",body={})
    check(413,"POST","/api/v1/worker/claim",worker["worker_token"],{"padding":"x"*10000})
    check(401,"POST","/api/v1/worker/claim",admin,{})
    check(403,"POST","/api/v1/remote-probes/jobs",viewer,{"collector_id":ids["collector"],"worker_id":worker["id"],"idempotency_key":str(uuid.uuid4())})
    check(422,"PUT",f"/api/v1/remote-probes/workers/{worker['id']}/network-policy",admin,
          {"allowed_hosts":["portal.example.test"],"allowed_cidrs":["169.254.0.0/16"]})
    check(200,"PUT",f"/api/v1/remote-probes/workers/{worker['id']}/network-policy",admin,
          {"allowed_hosts":["portal.example.test"],"allowed_cidrs":["10.20.0.0/16"]})
    check(200,"PUT",f"/api/v1/remote-probes/workers/{other['id']}/network-policy",admin,
          {"allowed_hosts":["portal.example.test"],"allowed_cidrs":["10.20.0.0/16"]})
    check(200,"PUT","/api/v1/remote-probes/collectors/"+ids["collector"]+"/assignment",admin,{"worker_id":worker["id"]})
    from app.worker.remote_scheduler import queue_due_once
    assert queue_due_once()>=1
    with SessionLocal() as db:
        generated=db.scalars(select(RemoteProbeJob).where(
            RemoteProbeJob.collector_id==uuid.UUID(ids["collector"]),
            RemoteProbeJob.state=="QUEUED")).all()
        assert len(generated)==1
        generated[0].state="CANCELLED"
        db.commit()
    data={"collector_id":ids["collector"],"worker_id":other["id"],"idempotency_key":str(uuid.uuid4())}
    check(403,"POST","/api/v1/remote-probes/jobs",admin,data)
    job_id=str(uuid.uuid4())
    data["worker_id"]=worker["id"];data["idempotency_key"]=job_id
    check(201,"POST","/api/v1/remote-probes/jobs",admin,data)
    duplicate=check(201,"POST","/api/v1/remote-probes/jobs",admin,data)
    assert duplicate["duplicate"]
    empty=check(200,"POST","/api/v1/worker/claim",other_token,{})
    assert empty["job"] is None
    claimed=check(200,"POST","/api/v1/worker/claim",token,{})["job"]
    assert claimed and claimed["job_id"]==job_id
    assert set(claimed["config"])=={"url","expected_status","timeout_seconds"}
    assert "password" not in json.dumps(claimed).lower()
    check(200,"POST","/api/v1/worker/claim",token,{})
    event=str(uuid.uuid4())
    result={"event_id":event,"job_id":job_id,"lease_nonce":claimed["lease_nonce"],
            "observed_at":datetime.now(timezone.utc).isoformat(),"outcome":"SUCCESS",
            "http_status":200,"response_time_ms":51,"response_size_bytes":20}
    check(404,"POST","/api/v1/worker/results",other_token,result)
    invalid=dict(result,lease_nonce="wrong-"*12)
    check(409,"POST","/api/v1/worker/results",token,invalid)
    stale=dict(result,observed_at=(datetime.now(timezone.utc)-timedelta(hours=1)).isoformat())
    check(422,"POST","/api/v1/worker/results",token,stale)
    oversized=dict(result,response_body="private-data")
    check(422,"POST","/api/v1/worker/results",token,oversized)
    accepted=check(202,"POST","/api/v1/worker/results",token,result)
    assert accepted["accepted"] and not accepted["duplicate"]
    again=check(202,"POST","/api/v1/worker/results",token,result)
    assert again["duplicate"]
    conflict=dict(result,event_id=str(uuid.uuid4()))
    check(409,"POST","/api/v1/worker/results",token,conflict)
    state=check(200,"GET","/api/v1/remote-probes/jobs/"+job_id,admin)
    assert state["state"]=="COMPLETED"
    check(403,"GET","/api/v1/remote-probes/jobs/"+job_id,viewer)
    with SessionLocal() as db:
        assert len(db.scalars(select(RemoteProbeEvidence).where(RemoteProbeEvidence.job_id==uuid.UUID(job_id))).all())==1
        assert db.get(RemoteProbeJob,uuid.UUID(job_id)).attempts==1
        from app.models import CollectorRun,MetricSample
        assert len(db.scalars(select(CollectorRun).where(CollectorRun.collector_id==uuid.UUID(ids["collector"]))).all())==1
        samples=db.scalars(select(MetricSample).where(MetricSample.metric_definition_id==uuid.UUID(ids["metric"]))).all()
        assert len(samples)==1 and samples[0].value_numeric==1.0
    # A second authenticated failed probe emits a fresh sample and activates
    # an independently configured metric alert rule.
    from app.models import AlertRule, AlertState
    with SessionLocal() as db:
        rule=AlertRule(organization_id=uuid.UUID(ids["org_n"]),
            metric_definition_id=uuid.UUID(ids["metric"]),
            name="Synthetic http availability",operator="LT",
            threshold_value="0.5",consecutive_breaches=1)
        db.add(rule);db.flush()
        rule_id=rule.id
        db.commit()
    next_id=str(uuid.uuid4())
    check(201,"POST","/api/v1/remote-probes/jobs",admin,
        {"collector_id":ids["collector"],"worker_id":worker["id"],"idempotency_key":next_id})
    next_job=check(200,"POST","/api/v1/worker/claim",token,{})["job"]
    assert next_job and next_job["job_id"]==next_id
    failure={"event_id":str(uuid.uuid4()),"job_id":next_id,
             "lease_nonce":next_job["lease_nonce"],
             "observed_at":datetime.now(timezone.utc).isoformat(),
             "outcome":"ASSERTION_FAILED","http_status":503,
             "response_time_ms":72,"response_size_bytes":0}
    check(202,"POST","/api/v1/worker/results",token,failure)
    with SessionLocal() as db:
        from app.models import MetricSample
        samples=db.scalars(select(MetricSample).where(
            MetricSample.metric_definition_id==uuid.UUID(ids["metric"]))).all()
        assert len(samples)==2 and sorted(s.value_numeric for s in samples)==[0.0,1.0]
        alerts=db.scalars(select(AlertState).where(AlertState.alert_rule_id==rule_id)).all()
        assert len(alerts)==1 and alerts[0].status=="OPEN"
    print("PASS remote metric alert evaluation")
    check(204,"DELETE","/api/v1/remote-probes/collectors/"+ids["collector"]+"/assignment",admin)
    check(204,"DELETE",f"/api/v1/auth/workers/{worker['id']}",admin)
    check(401,"POST","/api/v1/worker/claim",token,{})
    print("REMOTE TRUST/LEASE/EVIDENCE TESTS PASS")

if __name__=="__main__": main()
