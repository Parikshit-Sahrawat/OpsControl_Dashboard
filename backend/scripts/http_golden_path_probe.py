"""Real HTTPS golden path, only inside the disposable golden-path stack.

Orchestrated by scripts/http-golden-path.sh. Credentials stay in a protected
runtime file, never in evidence reports or stdout. No fabricated probe results.
"""
import json
import os
import secrets
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from app.db.session import SessionLocal
from app.models import Collector, MetricDefinition, MetricSample, AlertRule, AlertState, LogEvent, LogSource
from app.services.rule_models import MonitoringActivation, MonitoringRuleBinding
from app.worker.remote_models import RemoteProbeEvidence, RemoteProbeJob
from app.security.models import SecurityAuditEvent
from app.worker.remote_scheduler import queue_due_once

PRIVATE = Path('/golden/private/session.json')
REPORT = Path('/golden/evidence/report.json')
BASE = 'http://127.0.0.1:8000'


def api(status, method, path, token=None, body=None):
    req = urllib.request.Request(BASE + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={'Content-Type': 'application/json', **({'Authorization': 'Bearer '+token} if token else {})})
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            actual, data = response.status, json.loads(response.read() or b'null')
    except urllib.error.HTTPError as error:
        actual, data = error.code, json.loads(error.read() or b'null')
    # Do not echo response payloads; worker enrollment can contain a credential.
    assert actual == status, (method, path, status, actual)
    return data


def setup():
    password = Path('/run/secrets/demo_admin_password').read_text().strip()
    admin = api(200, 'POST', '/api/v1/auth/login', body={'username':'demo-admin','password':password})['access_token']
    orgs = [api(201, 'POST', '/api/v1/organizations', admin,
        {'name':name,'code':code}) for name, code in [('Golden HTTP Lab','GOLDEN'),('Other Fictional Tenant','OTHER')]]
    state = {'admin_token':admin, 'org_id':orgs[0]['id'], 'other_org_id':orgs[1]['id']}
    for key, org in [('operator', orgs[0]), ('other', orgs[1])]:
        password = secrets.token_urlsafe(32)
        user = api(201, 'POST', '/api/v1/auth/users', admin,
                   {'username':'golden-'+key,'password':password})
        api(201, 'POST', '/api/v1/auth/memberships', admin,
            {'user_id':user['id'],'organization_id':org['id'],'role':'org_admin'})
        state[key+'_username'], state[key+'_password'] = 'golden-'+key, password
        state[key+'_token'] = api(200,'POST','/api/v1/auth/login',body={'username':'golden-'+key,'password':password})['access_token']
    token = state['operator_token']
    source = api(201,'POST','/api/v1/resource-management/data-sources',token,
        {'organization_id':state['org_id'],'name':'Fictional HTTPS Portal','source_type':'API',
         'endpoint':'https://portal.example.test/ready','description':'Isolated synthetic TLS health fixture'})
    state['source_id'] = source['id']
    worker = api(201,'POST','/api/v1/auth/workers',admin,
        {'organization_id':state['org_id'],'name':'golden-private-agent','expires_in_days':1})
    state['worker_id'], state['worker_token'] = worker['id'], worker['worker_token']
    api(200,'PUT','/api/v1/remote-probes/workers/'+worker['id']+'/network-policy',admin,
        {'allowed_hosts':['portal.example.test'],'allowed_cidrs':['172.28.77.0/24']})
    versions = []
    for kind, name, definition in [
        ('METRIC','golden-readiness',{'name':'probe_up','metric_type':'GAUGE'}),
        ('LOG','golden-http-events',{'name':'http_events','source_type':'HTTP','parser_type':'RAW'}),
        ('ALERT','golden-unavailable',{'name':'unavailable','metric_name':'probe_up','operator':'LT',
            'threshold_value':0.5,'consecutive_breaches':1}),
    ]:
        catalog = api(201,'POST','/api/v1/rule-catalogs',token,
            {'organization_id':state['org_id'],'kind':kind,'name':name,'definition':definition})
        versions.append(catalog['versions'][0]['id'])
        if kind == 'METRIC':
            # Publish v2, but intentionally keep the activation pinned to v1.
            newer=api(201,'POST','/api/v1/rule-catalogs/'+catalog['id']+'/versions',token,{'definition':definition})
            assert newer['version']==2
            state['metric_v1'], state['metric_v2'] = versions[-1], newer['id']
    state['versions']=versions
    payload={'remote_worker_id':worker['id'],'rule_version_ids':versions,'include_templates':False}
    path='/api/v1/data-sources/'+source['id']
    preview=api(200,'POST',path+'/activation-preview',token,payload)
    assert preview['status']=='CHANGES_REQUIRED'
    applied=api(200,'POST',path+'/activations',token,payload)
    assert applied['status']=='ACTIVE' and applied['changed']
    again=api(200,'POST',path+'/activations',token,payload)
    assert not again['changed'] and again['collector_id']==applied['collector_id']
    state['collector_id']=applied['collector_id']
    PRIVATE.write_text(json.dumps(state)); PRIVATE.chmod(0o600)
    owner=PRIVATE.parent.stat()
    os.chown(PRIVATE, owner.st_uid, owner.st_gid)
    REPORT.write_text(json.dumps({'source_id':source['id'],'organization_id':state['org_id'],
        'rule_versions':versions,'activation_idempotent':True,'phases':[]},indent=2)+'\n')
    print('Authenticated scoped onboarding, immutable v1/v2 and idempotent activation PASS')


def schedule():
    state=json.loads(PRIVATE.read_text())
    with SessionLocal() as db:
        collector=db.get(Collector,UUID(state['collector_id']))
        collector.next_run_at=datetime.now(timezone.utc)-timedelta(seconds=1)
        db.commit()
    assert queue_due_once()==1
    print('One real HTTPS job queued')


def verify(phase):
    state=json.loads(PRIVATE.read_text())
    count, value, status, opens, resolved = {
        'healthy':(1,1.0,200,0,0), 'failed':(2,0.0,503,1,0), 'recovered':(3,1.0,200,0,1)
    }[phase]
    source_path='/api/v1/data-sources/'+state['source_id']
    diagnostics=api(200,'GET',source_path+'/diagnostics',state['operator_token'])
    assert diagnostics['activation']['status']=='ACTIVE'
    assert diagnostics['freshness']=='CURRENT'
    assert diagnostics['collector']['last_error']==('ASSERTION_FAILED' if phase=='failed' else None)
    assert diagnostics['open_alert_count']==opens and diagnostics['resolved_alert_count']==resolved
    assert diagnostics['metric_sample_count']==count
    assert diagnostics['latest_evidence']['http_status']==status
    with SessionLocal() as db:
        cid=UUID(state['collector_id']); oid=UUID(state['org_id'])
        metric=db.scalar(select(MetricDefinition).where(MetricDefinition.collector_id==cid,MetricDefinition.name=='probe_up'))
        samples=db.scalars(select(MetricSample).where(MetricSample.metric_definition_id==metric.id).order_by(MetricSample.observed_at)).all()
        assert [s.value_numeric for s in samples]==[1.0,0.0,1.0][:count]
        assert all(s.organization_id==oid for s in samples)
        jobs=db.scalars(select(RemoteProbeJob).where(RemoteProbeJob.collector_id==cid).order_by(RemoteProbeJob.created_at)).all()
        assert len(jobs)==count and all(j.state=='COMPLETED' for j in jobs)
        evidence=db.scalars(select(RemoteProbeEvidence).where(RemoteProbeEvidence.job_id.in_([j.id for j in jobs])).order_by(RemoteProbeEvidence.observed_at)).all()
        assert [e.result['http_status'] for e in evidence]==[200,503,200][:count]
        assert all(e.organization_id==oid and e.worker_id==UUID(state['worker_id']) for e in evidence)
        assert all(e.result['response_time_ms']>=0 for e in evidence)
        rule=db.scalar(select(AlertRule).where(AlertRule.metric_definition_id==metric.id))
        alerts=db.scalars(select(AlertState).where(AlertState.alert_rule_id==rule.id)).all()
        assert len(alerts)==(0 if phase=='healthy' else 1)
        if alerts:
            assert alerts[0].status==('OPEN' if phase=='failed' else 'RESOLVED')
            if phase=='recovered': assert alerts[0].resolved_at>=alerts[0].first_triggered_at
        logs=db.scalars(select(LogEvent).join(LogSource).where(LogSource.collector_id==cid)).all()
        assert len(logs)==count
        activation=db.scalar(select(MonitoringActivation).where(MonitoringActivation.data_source_id==UUID(state['source_id'])))
        bindings=db.scalars(select(MonitoringRuleBinding).where(MonitoringRuleBinding.activation_id==activation.id)).all()
        assert {str(b.rule_version_id) for b in bindings}==set(state['versions'])
        assert state['metric_v2'] not in {str(b.rule_version_id) for b in bindings}
    report=json.loads(REPORT.read_text())
    alert_id=str(alerts[0].id) if alerts else None
    if phase=='recovered':
        assert alert_id==report['phases'][-1]['alert_id']
    report['phases'].append({'alert_id':alert_id,'phase':phase,'http_status':status,'probe_up':value,'sample_count':count,
        'open_alerts':opens,'resolved_alerts':resolved,'jobs_completed':count,'log_events':count,
        'observed_at':diagnostics['latest_evidence']['observed_at']})
    REPORT.write_text(json.dumps(report,indent=2)+'\n')
    print('Real TLS evidence, database and alert lifecycle:',phase,'PASS')


def isolation():
    s=json.loads(PRIVATE.read_text()); token=s['other_token']; path='/api/v1/data-sources/'+s['source_id']
    api(401,'GET',path+'/diagnostics')
    for suffix in ['/diagnostics','/activation']:
        api(404,'GET',path+suffix,token)
    api(404,'POST',path+'/activations',token,{'remote_worker_id':s['worker_id'],'rule_version_ids':s['versions'],'include_templates':False})
    api(404,'POST','/api/v1/resource-management/data-sources',token,
        {'organization_id':s['org_id'],'name':'Forbidden','source_type':'API'})
    sources=api(200,'GET','/api/v1/resource-management/data-sources',token)
    assert s['source_id'] not in {row['id'] for row in sources}
    assert not api(200,'GET','/api/v1/rule-catalogs',token)
    assert not api(200,'GET','/api/v1/monitoring/alerts',token)
    api(403,'GET','/api/v1/auth/audit',token)
    audit=api(200,'GET','/api/v1/auth/audit?limit=500',s['admin_token'])
    assert any(e['event_type']=='LOGIN' and e['outcome']=='SUCCESS' for e in audit)
    assert any(e['event_type']=='HTTP_AUTH_DENIED' and e['outcome']=='DENIED' for e in audit)
    for suffix in ['/activations','/activation-preview']:
        assert any(e['target_id']==path+suffix and e['event_type']=='CONFIG_OR_ACTION' and e['outcome']=='SUCCESS' for e in audit)
    with SessionLocal() as db:
        assert len(db.scalars(select(SecurityAuditEvent)).all())==len(audit)
        for statement in ['UPDATE security_audit_events SET outcome=outcome WHERE id=:id',
                          'DELETE FROM security_audit_events WHERE id=:id']:
            try:
                with db.begin_nested():
                    db.execute(text(statement), {'id':UUID(audit[0]['id'])})
            except DBAPIError as error:
                assert 'append-only' in str(error.orig)
            else:
                raise AssertionError('Audit mutation unexpectedly accepted')
    # Redacted audit metadata only; no bearer credentials or payloads.
    for secret in [s['worker_token'],s['admin_token'],s['operator_token'],s['operator_password']]:
        assert secret not in json.dumps(audit)
    report=json.loads(REPORT.read_text());report['tenant_isolation']='PASS';report['audit_events']=audit;report['audit_append_only']='PASS'
    REPORT.write_text(json.dumps(report,indent=2)+'\n')
    print('Anonymous denial, cross-tenant reads/writes, scoped lists and redacted audit history PASS')

if __name__=='__main__':
    if os.getenv('ENVIRONMENT')!='demo' or os.getenv('OPSCONTROL_GOLDEN_PATH')!='1':
        raise SystemExit('Requires the disposable golden-path demo stack')
    command=sys.argv[1]
    if command=='setup': setup()
    elif command=='schedule': schedule()
    elif command=='isolation': isolation()
    else: verify(command)
