"""Disposable authenticated E2E: independent rules -> activation -> evidence.

Run after auth_tenant_probe and remote_protocol_probe in staging, with a
dedicated local PostgreSQL database only.
"""
import uuid
from datetime import datetime,timezone
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models import DataSource,Collector,MetricDefinition,AlertRule,LogSource,MetricSample,LogEvent,AlertState
from app.services.rule_models import MonitoringActivation,MonitoringRuleVersion
from scripts.auth_tenant_probe import call,login,expect

def request(status,method,path,token,body=None):
    result, data=call(method,path,token,body)
    assert result==status,(method,path,status,result,data)
    print("PASS",method,path,status)
    return data

def main():
    admin=login("test-admin")
    north=login("test-north")
    viewer=login("test-reader")
    south=login("test-south")
    with SessionLocal() as db:
        source=db.scalar(select(DataSource).where(DataSource.name=="north-synthetic"))
        other=db.scalar(select(DataSource).where(DataSource.name=="south-synthetic"))
        source.endpoint="https://portal.example.test/ready"
        source_id=str(source.id)
        org_id=str(source.organization_id)
        other_id=str(other.id)
        db.commit()

    worker=request(201,"POST","/api/v1/auth/workers",admin,
        {"organization_id":org_id,"name":"activation-demo-agent","expires_in_days":1})
    wid=worker["id"]
    request(200,"PUT",f"/api/v1/remote-probes/workers/{wid}/network-policy",admin,
        {"allowed_hosts":["portal.example.test"],"allowed_cidrs":["10.20.0.0/16"]})
    defs=[
        ("METRIC","readiness",{"name":"probe_up","metric_type":"GAUGE"}),
        ("LOG","probe-events",{"name":"http_events","source_type":"HTTP","parser_type":"RAW"}),
        ("ALERT","readiness-unavailable",{"name":"unavailable","metric_name":"probe_up",
                    "operator":"LT","threshold_value":0.5,"consecutive_breaches":1}),
    ]
    rule_ids=[]
    for kind,name,definition in defs:
        c=request(201,"POST","/api/v1/rule-catalogs",north,
            {"organization_id":org_id,"kind":kind,"name":name,"definition":definition})
        assert c["kind"]==kind and c["versions"][0]["version"]==1
        rule_ids.append(c["versions"][0]["id"])
    request(403,"POST","/api/v1/rule-catalogs",viewer,
        {"organization_id":org_id,"kind":"METRIC","name":"illegal","definition":defs[0][2]})
    request(403,"POST","/api/v1/rule-catalogs",north,
        {"organization_id":str(other.organization_id),"kind":"METRIC","name":"illegal","definition":defs[0][2]})
    cats=request(200,"GET","/api/v1/rule-catalogs",north)
    assert len(cats)==3,cats
    cats_other=request(200,"GET","/api/v1/rule-catalogs",south)
    assert not cats_other,cats_other
    version=request(201,"POST",f"/api/v1/rule-catalogs/{cats[0]['id']}/versions",north,
        {"definition":cats[0]["versions"][0]["definition"]})
    assert version["version"]==2
    # Invalid alert has no matching metric; preview must reject without mutation.
    bad=request(201,"POST","/api/v1/rule-catalogs",north,
        {"organization_id":org_id,"kind":"ALERT","name":"bad-reference",
         "definition":{"name":"bad","metric_name":"http_response_time_ms","operator":"GT","threshold_value":10}})
    payload={"remote_worker_id":wid,"rule_version_ids":rule_ids,"include_templates":False}
    request(403,"POST",f"/api/v1/data-sources/{source_id}/activations",viewer,payload)
    request(403,"POST",f"/api/v1/data-sources/{other_id}/activations",north,payload)
    request(422,"POST",f"/api/v1/data-sources/{source_id}/activation-preview",north,
            {**payload,"rule_version_ids":rule_ids+[bad["versions"][0]["id"]]})
    plan=request(200,"POST",f"/api/v1/data-sources/{source_id}/activation-preview",north,payload)
    assert plan["status"]=="CHANGES_REQUIRED" and len(plan["plan"]["rules"])==3
    response=request(200,"POST",f"/api/v1/data-sources/{source_id}/activations",north,payload)
    assert response["status"]=="ACTIVE" and response["changed"]
    collector_id=response["collector_id"]
    unchanged=request(200,"POST",f"/api/v1/data-sources/{source_id}/activations",north,payload)
    assert not unchanged["changed"] and unchanged["collector_id"]==collector_id
    version_num=response["version"]
    health=request(200,"GET",f"/api/v1/data-sources/{source_id}/activation",north)
    assert health["status"]=="ACTIVE" and health["version"]==version_num
    with SessionLocal() as db:
        cc=db.get(Collector,uuid.UUID(collector_id))
        assert cc.enabled and str(cc.remote_worker_id)==wid and cc.status in {"STOPPED","STALE"}
        assert len(db.scalars(select(MetricDefinition).where(
            MetricDefinition.collector_id==cc.id,MetricDefinition.name=="probe_up")).all())==1
        assert len(db.scalars(select(LogSource).where(LogSource.collector_id==cc.id)).all())==1
        assert len(db.scalars(select(AlertRule).where(AlertRule.organization_id==cc.data_source.organization_id,
            AlertRule.name.like("%unavailable"))).all())==1
    from app.worker.remote_scheduler import queue_due_once
    assert queue_due_once()>=1
    job=request(200,"POST","/api/v1/worker/claim",worker["worker_token"],{})["job"]
    assert job is not None
    result={"event_id":str(uuid.uuid4()),"job_id":job["job_id"],"lease_nonce":job["lease_nonce"],
            "observed_at":datetime.now(timezone.utc).isoformat(),
            "outcome":"ASSERTION_FAILED","http_status":503,
            "response_time_ms":25,"response_size_bytes":0}
    request(202,"POST","/api/v1/worker/results",worker["worker_token"],result)
    with SessionLocal() as db:
        assert db.scalar(select(MetricSample).join(MetricDefinition).where(
            MetricDefinition.collector_id==uuid.UUID(collector_id),MetricSample.value_numeric==0.0)) is not None
        state=db.scalar(select(AlertState).join(AlertRule).where(
            AlertRule.name.like("%unavailable"),AlertState.status=="OPEN"))
        assert state is not None
    disabled=request(200,"POST",f"/api/v1/data-sources/{source_id}/deactivation",north)
    assert disabled["status"]=="DISABLED"
    again=request(200,"POST",f"/api/v1/data-sources/{source_id}/deactivation",north)
    assert not again["changed"]
    with SessionLocal() as db:
        cc=db.get(Collector,uuid.UUID(collector_id))
        assert not cc.enabled and cc.remote_worker_id is None
        assert not db.scalar(select(MetricDefinition).where(
            MetricDefinition.collector_id==cc.id)).enabled
    print("PHASE 2 RULE CATALOG / ACTIVATION / REAL EVIDENCE TESTS PASS")

if __name__=="__main__":main()
