"""Disposable full-chain HTTPS activation → evidence → alert → recovery.

Only execute in ENVIRONMENT=demo with the synthetic demo DB. Never contacts
real cloud or customer infrastructure. Setup returns a one-time synthetic
worker token to a trusted CI shell variable; never logs it.
"""
import json
import os
import sys
import urllib.request
from pathlib import Path
from datetime import datetime,timedelta,timezone
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models import Organization,DataSource,Collector,MetricDefinition,MetricSample,AlertRule,AlertState
from app.services.rule_models import MonitoringActivation
from app.worker.remote_scheduler import queue_due_once

BASE="http://127.0.0.1:8000"
def check_env():
    if os.getenv("ENVIRONMENT")!="demo":
        raise SystemExit("This verification requires disposable demo database")

def api(method,path,token=None,body=None):
    data=json.dumps(body).encode() if body is not None else None
    req=urllib.request.Request(BASE+path,data=data,method=method,headers={
        "Content-Type":"application/json",**({"Authorization":"Bearer "+token} if token else {})})
    with urllib.request.urlopen(req,timeout=10) as response:
        return json.loads(response.read() or b"null")

def resources(db):
    org=db.scalar(select(Organization).where(Organization.code=="DEMO-LAB"))
    if not org: raise AssertionError("Fictional lab missing")
    source=db.scalar(select(DataSource).where(DataSource.organization_id==org.id,
        DataSource.name=="Example internal portal (not connected)"))
    if not source: raise AssertionError("Fictional HTTPS source missing")
    activation=db.scalar(select(MonitoringActivation).where(MonitoringActivation.data_source_id==source.id))
    return org,source,activation

def setup():
    password=Path("/run/secrets/demo_admin_password").read_text().strip()
    admin=api("POST","/api/v1/auth/login",body={"username":"demo-admin","password":password})["access_token"]
    with SessionLocal() as db:
        org,source,_=resources(db)
        organization_id=str(org.id);source_id=str(source.id)
    worker=api("POST","/api/v1/auth/workers",admin,{
        "organization_id":organization_id,"name":"isolated-fixture-agent","expires_in_days":1})
    api("PUT","/api/v1/remote-probes/workers/"+worker["id"]+"/network-policy",admin,{
        "allowed_hosts":["portal.example.test"],"allowed_cidrs":["172.28.77.0/24"]})
    versions=[]
    for kind,name,definition in [
        ("METRIC","synthetic-readiness",{"name":"probe_up","metric_type":"GAUGE"}),
        ("ALERT","synthetic-unavailable",{"name":"unavailable","metric_name":"probe_up",
            "operator":"LT","threshold_value":0.5,"consecutive_breaches":1}),
    ]:
        record=api("POST","/api/v1/rule-catalogs",admin,{
            "organization_id":organization_id,"kind":kind,"name":name,"definition":definition})
        versions.append(record["versions"][0]["id"])
    preview=api("POST","/api/v1/data-sources/"+source_id+"/activation-preview",admin,{
        "remote_worker_id":worker["id"],"rule_version_ids":versions,"include_templates":False})
    assert preview["status"]=="CHANGES_REQUIRED",preview
    applied=api("POST","/api/v1/data-sources/"+source_id+"/activations",admin,{
        "remote_worker_id":worker["id"],"rule_version_ids":versions,"include_templates":False})
    assert applied["status"]=="ACTIVE",applied
    assert queue_due_once()==1
    # Token printed ONLY to trusted CI command substitution; never persisted.
    sys.stdout.write(worker["worker_token"])

def schedule():
    with SessionLocal() as db:
        _,source,activation=resources(db)
        if not activation:raise AssertionError("Activation missing")
        collector=db.get(Collector,activation.collector_id)
        collector.next_run_at=datetime.now(timezone.utc)-timedelta(seconds=1)
        db.commit()
    assert queue_due_once()==1

def verify(expected):
    with SessionLocal() as db:
        _,source,activation=resources(db)
        collector=db.get(Collector,activation.collector_id)
        metric=db.scalar(select(MetricDefinition).where(
            MetricDefinition.collector_id==collector.id,MetricDefinition.name=="probe_up"))
        assert metric is not None
        samples=db.scalars(select(MetricSample).where(
            MetricSample.metric_definition_id==metric.id).order_by(MetricSample.observed_at)).all()
        required={"healthy":(1,1.0),"failed":(2,0.0),"recovered":(3,1.0)}
        count,value=required[expected]
        assert len(samples)==count and samples[-1].value_numeric==value,(expected,len(samples))
        rule=db.scalar(select(AlertRule).where(AlertRule.metric_definition_id==metric.id))
        assert rule is not None
        states=db.scalars(select(AlertState).where(AlertState.alert_rule_id==rule.id)).all()
        if expected=="healthy":assert len(states)==0,states
        else:
            assert len(states)==1 and states[0].status==("OPEN" if expected=="failed" else "RESOLVED"),[
                x.status for x in states]
        assert collector.last_run_at and collector.enabled
    print("LIVE HTTPS ACTIVATION/EVIDENCE/ALERT:",expected,"PASS")

def main():
    check_env()
    command=sys.argv[1]
    if command=="setup":setup()
    elif command=="schedule":schedule()
    elif command in {"healthy","failed","recovered"}:verify(command)
    else:raise SystemExit("Usage: setup | schedule | healthy | failed | recovered")
if __name__=="__main__":main()
