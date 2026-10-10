"""Idempotent, scoped activation of independent rule versions and template bundles.

Only explicitly approved remote HTTP workers can be made ACTIVE. Resource
discovery and configuration attachment do not implicitly start monitoring.
"""
import hashlib
import json
import uuid
from datetime import datetime,timezone
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import (DataSource,Collector,MetricDefinition,LogSource,AlertRule)
from app.security.models import WorkerIdentity
from app.security.secret_refs import require_safe_config
from app.services.template_resolution import resolve_data_source_configuration
from app.services.rule_models import (MonitoringRuleCatalog,MonitoringRuleVersion,
    MonitoringActivation,MonitoringRuleBinding)
from app.api.rule_catalogs import validate_definition
from app.worker.egress import EgressDenied,check_target

def now(): return datetime.now(timezone.utc)
def stable(namespace,component):
    return uuid.uuid5(namespace,"opscontrol-monitoring:"+component)

def _rules(db,source,version_ids,include_templates):
    selected=[]
    for version_id in version_ids:
        version=db.get(MonitoringRuleVersion,version_id)
        catalog=db.get(MonitoringRuleCatalog,version.catalog_id) if version else None
        if catalog is None or catalog.organization_id!=source.organization_id:
            raise HTTPException(404,"Referenced rule version not available in organization")
        validate_definition(catalog.kind,version.definition)
        selected.append({"version_id":str(version.id),"kind":catalog.kind,"definition":version.definition,
                         "source":"CATALOG","catalog_name":catalog.name})
    if include_templates:
        effective=resolve_data_source_configuration(db,source.id)
        if not effective["valid"]:
            raise HTTPException(422,{"missing_required_attributes":effective["missing_required_attributes"]})
        for kind,key in (("METRIC","metrics"),("LOG","logs"),("ALERT","alerts")):
            for item in effective[key]:
                if not isinstance(item,dict):raise HTTPException(422,"Invalid template rule entry")
                normalized=dict(item)
                if kind=="METRIC":
                    normalized["name"]=item.get("metric",item.get("name"))
                    normalized.setdefault("metric_type","GAUGE")
                elif kind=="LOG":
                    normalized.setdefault("source_type","HTTP")
                elif kind=="ALERT":
                    normalized["metric_name"]=item.get("metric_name",item.get("metric"))
                require_safe_config(normalized)
                validate_definition(kind,normalized)
                selected.append({"version_id":None,"kind":kind,"definition":normalized,
                                 "source":"TEMPLATE","catalog_name":normalized.get("name","")})
    seen=set()
    for item in selected:
        definition=item["definition"]
        key=(item["kind"],definition.get("name"))
        if key in seen: raise HTTPException(409,"Duplicate rule names across selected versions/templates")
        seen.add(key)
    return selected

def build_plan(db:Session,source_id,version_ids,worker_id,include_templates=True):
    source=db.get(DataSource,source_id)
    if source is None: raise HTTPException(404,"Data source not found")
    if not source.enabled: raise HTTPException(409,"Data source disabled")
    worker=db.get(WorkerIdentity,worker_id) if worker_id else None
    if worker is None or not worker.enabled or worker.organization_id!=source.organization_id or worker.expires_at.replace(tzinfo=timezone.utc)<=now():
        raise HTTPException(422,"An active organization-scoped remote worker is required")
    rules=_rules(db,source,version_ids,include_templates)
    if not rules: raise HTTPException(422,"Select at least one metric, log or alert rule")
    types={r["kind"] for r in rules}
    if "METRIC" not in types:
        raise HTTPException(422,"A supported Metric Rule is required to establish evidence")
    metric_names={r["definition"]["name"] for r in rules if r["kind"]=="METRIC"}
    for r in rules:
        if r["kind"]=="ALERT" and r["definition"]["metric_name"] not in metric_names:
            raise HTTPException(422,"Alert rule references a missing metric rule")
    effective=resolve_data_source_configuration(db,source.id) if include_templates else {"collector":{}}
    cc=effective.get("collector") or {}
    if cc.get("type", "HTTP").upper() not in {"HTTP","API"}:
        raise HTTPException(422,"Only remote HTTP/API activation is supported; other providers remain BLOCKED")
    config={"url":cc.get("url") or source.endpoint,
            "expected_status":cc.get("expected_status",200),
            "timeout_seconds":cc.get("timeout_seconds",8)}
    if not isinstance(config["url"],str): raise HTTPException(422,"Target HTTPS URL is missing")
    try:
        check_target(config["url"],worker.allowed_hosts,worker.allowed_cidrs)
    except EgressDenied as exc:raise HTTPException(422,str(exc))
    if type(config["expected_status"]) is not int or not 100<=config["expected_status"]<=599:
        raise HTTPException(422,"Invalid expected_status")
    if type(config["timeout_seconds"]) is not int or not 1<=config["timeout_seconds"]<=10:
        raise HTTPException(422,"Timeout must be 1..10 seconds")
    try:
        interval=int(cc.get("interval_seconds",60))
    except (ValueError,TypeError): raise HTTPException(422,"Invalid polling interval")
    if interval<30 or interval>86400: raise HTTPException(422,"Interval must be 30..86400 seconds")
    plan={"source_id":str(source.id),"organization_id":str(source.organization_id),
          "remote_worker_id":str(worker.id),"collector":{"type":"HTTP","name":"opscontrol-http",
          "interval_seconds":interval,"configuration":config},"rules":rules}
    fingerprint=hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    plan["fingerprint"]=fingerprint
    return plan

def preview(db,source_id,version_ids,worker_id,include_templates=True):
    plan=build_plan(db,source_id,version_ids,worker_id,include_templates)
    current=db.scalar(select(MonitoringActivation).where(MonitoringActivation.data_source_id==source_id))
    return {"status":"UNCHANGED" if current and current.status=="ACTIVE" and current.fingerprint==plan["fingerprint"] else "CHANGES_REQUIRED",
            "current_version":current.version if current else None,
            "plan":plan,"supported":True}

def _disable_previous(db,activation):
    for record in activation.details.get("generated",[]):
        try: rid=uuid.UUID(record["id"])
        except (ValueError,KeyError): continue
        model={"METRIC":MetricDefinition,"LOG":LogSource,"ALERT":AlertRule}.get(record.get("kind"))
        obj=db.get(model,rid) if model else None
        if obj: obj.enabled=False

def apply(db,source_id,version_ids,worker_id,include_templates=True):
    # Lock the Data Source to serialize concurrent activation and assignment.
    source=db.scalar(select(DataSource).where(DataSource.id==source_id).with_for_update())
    if source is None:raise HTTPException(404,"Data source not found")
    plan=build_plan(db,source_id,version_ids,worker_id,include_templates)
    existing=db.scalar(select(MonitoringActivation).where(
        MonitoringActivation.data_source_id==source_id).with_for_update())
    if existing and existing.status=="ACTIVE" and existing.fingerprint==plan["fingerprint"]:
        return {"status":"ACTIVE","changed":False,"version":existing.version,
                "collector_id":str(existing.collector_id)}
    if existing: _disable_previous(db,existing)
    stable_id=stable(source.id,"collector:http")
    collector=db.get(Collector,stable_id)
    if collector is None:
        collector=Collector(id=stable_id,data_source_id=source.id,
            name="opscontrol-http",collector_type="HTTP")
        db.add(collector)
    elif collector.data_source_id!=source.id:
        raise HTTPException(409,"Collector identity collision")
    collector.collector_type="HTTP"
    collector.configuration=plan["collector"]["configuration"]
    collector.interval_seconds=plan["collector"]["interval_seconds"]
    collector.remote_worker_id=worker_id
    collector.enabled=True
    collector.next_run_at=now()
    collector.status="STOPPED"  # never mark healthy until verified evidence
    if existing is None:
        existing=MonitoringActivation(organization_id=source.organization_id,
            data_source_id=source.id,version=0,fingerprint="",status="DRAFT",details={})
        db.add(existing)
        db.flush()
    else:
        db.query(MonitoringRuleBinding).filter(MonitoringRuleBinding.activation_id==existing.id).delete(synchronize_session=False)
    existing.version+=1
    existing.status="ACTIVE"
    existing.fingerprint=plan["fingerprint"]
    existing.applied_at=now()
    existing.collector_id=collector.id
    created=[]
    metrics={}
    # Persist metrics first so alert foreign keys can resolve.
    for kind in ("METRIC","LOG","ALERT"):
        for index,rule in enumerate(x for x in plan["rules"] if x["kind"]==kind):
            data=rule["definition"]
            identity=stable(source.id,kind+":"+data.get("name",str(index)))
            if kind=="METRIC":
                row=db.get(MetricDefinition,identity)
                if row is None:
                    row=MetricDefinition(id=identity,organization_id=source.organization_id,
                        data_source_id=source.id,collector_id=collector.id,name=data["name"],
                        resource_type="APPLICATION",metric_type="GAUGE")
                    db.add(row)
                row.enabled=True
                row.collector_id=collector.id
                row.collection_interval_seconds=collector.interval_seconds
                row.query_config={"adapter":"remote_http","rule_version_id":rule["version_id"]}
                metrics[data["name"]]=row
            elif kind=="LOG":
                row=db.get(LogSource,identity)
                if row is None:
                    row=LogSource(id=identity,organization_id=source.organization_id,
                        data_source_id=source.id,collector_id=collector.id,name=data["name"],
                        source_type="HTTP",resource_type="APPLICATION")
                    db.add(row)
                row.enabled=True
                row.collector_id=collector.id
                row.parser_type="RAW"
                row.parser_config={"adapter":"remote_http","rule_version_id":rule["version_id"]}
            else:
                metric=metrics.get(data["metric_name"])
                if metric is None:raise HTTPException(422,"Unresolved metric reference")
                row=db.get(AlertRule,identity)
                if row is None:
                    row=AlertRule(id=identity,organization_id=source.organization_id,
                        metric_definition_id=metric.id,name=f"{source.id}:{data['name']}",
                        threshold_value=str(data["threshold_value"]))
                    db.add(row)
                row.enabled=True
                row.metric_definition_id=metric.id
                row.operator=data["operator"]
                row.threshold_value=str(data["threshold_value"])
                row.severity=data.get("severity","WARNING")
                row.consecutive_breaches=data.get("consecutive_breaches",1)
            created.append({"kind":kind,"id":str(identity),"name":data["name"]})
            if rule["version_id"]:
                db.add(MonitoringRuleBinding(activation_id=existing.id,
                    rule_version_id=uuid.UUID(rule["version_id"]),materialized_id=identity,kind=kind))
    existing.details={"generated":created,"plan":plan}
    db.commit()
    return {"status":"ACTIVE","changed":True,"version":existing.version,
            "collector_id":str(collector.id),"generated":created}

def disable(db,source_id):
    source=db.scalar(select(DataSource).where(DataSource.id==source_id).with_for_update())
    if not source:raise HTTPException(404,"Data source not found")
    activation=db.scalar(select(MonitoringActivation).where(
        MonitoringActivation.data_source_id==source_id).with_for_update())
    if not activation:raise HTTPException(404,"No activation for source")
    if activation.status=="DISABLED":return {"status":"DISABLED","changed":False}
    _disable_previous(db,activation)
    collector=db.get(Collector,activation.collector_id) if activation.collector_id else None
    if collector:
        collector.enabled=False
        collector.remote_worker_id=None
        collector.status="STOPPED"
    from app.worker.remote_models import RemoteProbeJob
    for job in db.scalars(select(RemoteProbeJob).where(
        RemoteProbeJob.collector_id==activation.collector_id,
        RemoteProbeJob.state.in_(["QUEUED","LEASED"]))).all():
        job.state="CANCELLED"
        job.lease_nonce_hash=None
    activation.status="DISABLED"
    activation.version+=1
    db.commit()
    return {"status":"DISABLED","changed":True}
