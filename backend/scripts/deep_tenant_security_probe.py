"""Negative IDOR tests for nested metrics, logs, alerts and template attachment.

Run after auth_tenant_probe.py and before security_release_probe.py against disposable DB.
"""
from datetime import datetime, timezone
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models import (
    Organization, DataSource, Collector, MetricDefinition, MetricSample,
    LogSource, LogEvent, AlertRule, AlertState,
)
from scripts.auth_tenant_probe import login, expect, call

def seed():
    with SessionLocal() as db:
        north=db.scalar(select(Organization).where(Organization.code=="LAB-N"))
        south=db.scalar(select(Organization).where(Organization.code=="LAB-S"))
        assert north and south
        source_n=db.scalar(select(DataSource).where(DataSource.organization_id==north.id))
        source_s=db.scalar(select(DataSource).where(DataSource.organization_id==south.id))
        coll_n=db.scalar(select(Collector).where(Collector.data_source_id==source_n.id))
        coll_s=db.scalar(select(Collector).where(Collector.data_source_id==source_s.id))
        m_n=MetricDefinition(organization_id=north.id,data_source_id=source_n.id,collector_id=coll_n.id,
                             name="north-latency",resource_type="APPLICATION",metric_type="GAUGE")
        m_s=MetricDefinition(organization_id=south.id,data_source_id=source_s.id,collector_id=coll_s.id,
                             name="south-latency",resource_type="APPLICATION",metric_type="GAUGE")
        l_n=LogSource(organization_id=north.id,data_source_id=source_n.id,collector_id=coll_n.id,
                      name="north-probe-log",source_type="API",resource_type="APPLICATION")
        l_s=LogSource(organization_id=south.id,data_source_id=source_s.id,collector_id=coll_s.id,
                      name="south-probe-log",source_type="API",resource_type="APPLICATION")
        db.add_all([m_n,m_s,l_n,l_s]);db.flush()
        now=datetime.now(timezone.utc)
        db.add_all([
            MetricSample(organization_id=north.id,metric_definition_id=m_n.id,observed_at=now,value_numeric=1.0),
            MetricSample(organization_id=south.id,metric_definition_id=m_s.id,observed_at=now,value_numeric=99.0),
            LogEvent(organization_id=north.id,log_source_id=l_n.id,observed_at=now,message="north fictional event"),
            LogEvent(organization_id=south.id,log_source_id=l_s.id,observed_at=now,message="south fictional event"),
        ])
        r_n=AlertRule(organization_id=north.id,metric_definition_id=m_n.id,name="north-alert",threshold_value="50")
        r_s=AlertRule(organization_id=south.id,metric_definition_id=m_s.id,name="south-alert",threshold_value="50")
        db.add_all([r_n,r_s]);db.flush()
        st_n=AlertState(organization_id=north.id,alert_rule_id=r_n.id,metric_definition_id=m_n.id,
                        severity="WARNING",first_triggered_at=now,last_evaluated_at=now,last_value=1,
                        message="synthetic north")
        st_s=AlertState(organization_id=south.id,alert_rule_id=r_s.id,metric_definition_id=m_s.id,
                        severity="CRITICAL",first_triggered_at=now,last_evaluated_at=now,last_value=99,
                        message="synthetic south")
        db.add_all([st_n,st_s]);db.flush()
        ids={key:str(value) for key,value in {
            "n":north.id,"s":south.id,"sn":source_n.id,"ss":source_s.id,
            "cn":coll_n.id,"cs":coll_s.id,"mn":m_n.id,"ms":m_s.id,
            "ln":l_n.id,"ls":l_s.id,"rn":r_n.id,"rs":r_s.id,
            "an":st_n.id,"as":st_s.id}.items()}
        db.commit();return ids

def only_one(token, path, field):
    rows=expect(200,"GET",path,token)
    assert len(rows)==1 and rows[0]["id"]==field,(path,rows)

def main():
    i=seed()
    north=login("test-north")
    south=login("test-south")
    viewer=login("test-reader")
    admin=login("test-admin")
    only_one(north,"/api/v1/monitoring/metrics",i["mn"])
    only_one(north,"/api/v1/monitoring/logs",i["ln"])
    only_one(north,"/api/v1/monitoring/alert-rules",i["rn"])
    only_one(north,"/api/v1/monitoring/alerts",i["an"])
    only_one(south,"/api/v1/monitoring/metrics",i["ms"])
    for kind,identifier in [("metrics",i["ms"]),("logs",i["ls"]),("alert-rules",i["rs"]),("alerts",i["as"])]:
        expect(404,"GET","/api/v1/monitoring/"+kind+"/"+identifier,north)
    expect(404,"GET","/api/v1/monitoring/metrics/"+i["ms"]+"/samples",north)
    expect(404,"GET","/api/v1/monitoring/logs/"+i["ls"]+"/events",north)
    expect(404,"GET","/api/v1/monitoring/alerts/"+i["as"]+"/notifications",north)
    expect(404,"PATCH","/api/v1/monitoring/metrics/"+i["ms"],north,{"name":"cross-org"})
    expect(404,"DELETE","/api/v1/monitoring/alert-rules/"+i["rs"],north)
    expect(404,"PATCH","/api/v1/monitoring/logs/"+i["ls"],north,{"name":"cross-org"})
    expect(403,"POST","/api/v1/monitoring/metrics",viewer,{
        "organization_id":i["n"],"data_source_id":i["sn"],
        "name":"viewer-wrong","resource_type":"APPLICATION","metric_type":"GAUGE"})
    status,response=call("POST","/api/v1/monitoring/alert-rules",north,{
        "organization_id":i["n"],"metric_definition_id":i["ms"],
        "name":"cross-bound","threshold_value":"50"})
    assert status in (404,409),(status,response)
    status,response=call("POST","/api/v1/monitoring/metrics",north,{
        "organization_id":i["n"],"data_source_id":i["ss"],
        "name":"cross-fk","resource_type":"APPLICATION","metric_type":"GAUGE"})
    assert status in (404,409),(status,response)
    # Full platform administrator has explicit elevated cross-org visibility.
    rows=expect(200,"GET","/api/v1/monitoring/metrics",admin)
    assert {x["id"] for x in rows} >= {i["mn"],i["ms"]}
    print("DEEP TENANT SECURITY NEGATIVE TESTS PASS")

if __name__=="__main__":
    main()
