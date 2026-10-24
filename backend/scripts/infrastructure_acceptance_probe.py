"""Scoped API activation -> infrastructure worker -> persisted health/alerts."""
from scripts.acceptance_scope import probe_headers
import asyncio
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime,timedelta,timezone
from pathlib import Path
from uuid import UUID
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models import InfrastructureEvidence,MetricSample,MetricDefinition,AlertState,AlertRule,Collector
from app.worker.collector_runtime import ADAPTERS,execute_collector
from scripts.infrastructure_controlled_providers import EC2Controlled,WindowsControlled
PRIVATE=Path(os.environ['INFRA_PRIVATE_DIR']);BASE='http://127.0.0.1:18000'

def api(status,method,path,token=None,body=None):
    if status==201 and method=='POST' and path=='/api/v1/auth/users' and body and not body.get('platform_admin') and not body.get('department_id'):
        from scripts.fixture_employee import with_department
        body=with_department(body,lambda value:api(201,'POST','/api/v1/access/departments',token,value))
    req=urllib.request.Request(BASE+path,method=method,data=json.dumps(body).encode() if body is not None else None,
        headers={'Content-Type':'application/json',**({'Authorization':'Bearer '+token} if token else {}), **probe_headers(BASE, token, path)})
    try:
        with urllib.request.urlopen(req,timeout=20) as response:actual,data=response.status,json.loads(response.read() or b'null')
    except urllib.error.HTTPError as error:actual,data=error.code,json.loads(error.read() or b'null')
    assert actual==status,(method,path,status,actual)
    return data

def login(username,password):return api(200,'POST','/api/v1/auth/login',body={'username':username,'password':password})['access_token']

def setup():
    import secrets
    state={'admin_token':login('demo-admin',(PRIVATE/'admin-password').read_text().strip())}
    admin=state['admin_token']
    org=api(201,'POST','/api/v1/organizations',admin,{'name':'Infrastructure Controlled Lab','code':'INFRA'})
    other=api(201,'POST','/api/v1/organizations',admin,{'name':'Other Infrastructure Tenant','code':'INFRA-OTHER'})
    state['org_id']=org['id'];state['other_org_id']=other['id']
    for name,scope,role in [('reader',org,'viewer'),('operator',org,'org_admin'),('other',other,'org_admin')]:
        password=secrets.token_urlsafe(32)
        user=api(201,'POST','/api/v1/auth/users',admin,{'username':'infra-'+name,'password':password})
        api(201,'POST','/api/v1/auth/memberships',admin,{'user_id':user['id'],'organization_id':scope['id'],'role':role})
        state[name+'_username']='infra-'+name;state[name+'_password']=password;state[name+'_token']=login('infra-'+name,password)
    resources=[]
    for label,kind,cfg in [('EC2 connection (controlled SDK)','AWS_EC2',{'region':'ap-south-1','account_id':'123456789012'})]:
        connection=api(201,'POST','/api/v1/resource-management/data-sources',admin,{'organization_id':org['id'],'name':label,'source_type':kind,'connection_config':cfg})
        scan=api(200,'POST','/api/v1/resource-discovery/sources/'+connection['id']+'/scan',admin)
        ids=[c['external_id'] for c in scan['candidates']]
        assert len(ids)==1
        imported=api(200,'POST','/api/v1/resource-discovery/sources/'+connection['id']+'/import',admin,{'approved_external_ids':ids,'dry_run':False})
        again=api(200,'POST','/api/v1/resource-discovery/sources/'+connection['id']+'/import',admin,{'approved_external_ids':ids,'dry_run':False})
        assert all(r['action']=='ALREADY_IMPORTED' for r in again['resources'])
        for candidate,row in zip(scan['candidates'],imported['resources']):
            label='EC2 controlled SDK fixture'
            source=api(200,'PATCH','/api/v1/resource-management/data-sources/'+row['data_source_id'],admin,{'name':label})
            resources.append(source)
        after_rename=api(200,'POST','/api/v1/resource-discovery/sources/'+connection['id']+'/import',admin,{'approved_external_ids':ids,'dry_run':False})
        assert all(r['action']=='ALREADY_IMPORTED' for r in after_rename['resources'])
    for label,kind,cfg in [('Linux live worker','LINUX_HOST',{'disk_path':'/','process_pid':int(os.environ['LINUX_TARGET_PID'])}),
        ('Windows controlled SDK fixture','WINDOWS_HOST',{'disk_path':'C:\\','process_pid':101})]:
        resources.append(api(201,'POST','/api/v1/resource-management/data-sources',admin,{'organization_id':org['id'],'name':label,'source_type':kind,'connection_config':cfg}))
    state['resources']=[]
    from app.worker.infrastructure import PROVIDER_METRICS
    for source in resources:
        versions=[]
        for metric in sorted(PROVIDER_METRICS[source['source_type']]):
            catalog=api(201,'POST','/api/v1/rule-catalogs',admin,{'organization_id':org['id'],'name':source['id']+':'+metric,'kind':'METRIC','definition':{'name':metric,'metric_type':'GAUGE'}})
            versions.append(catalog['versions'][0]['id'])
        alert=api(201,'POST','/api/v1/rule-catalogs',admin,{'organization_id':org['id'],'kind':'ALERT','name':source['id']+':health',
            'definition':{'name':'infra-health','metric_name':'ec2_cpu_percent' if source['source_type']=='AWS_EC2' else 'infrastructure_up',
                'operator':'GT' if source['source_type']=='AWS_EC2' else 'LT','threshold_value':80 if source['source_type']=='AWS_EC2' else 0.5,'severity':'CRITICAL','consecutive_breaches':1}})
        versions.append(alert['versions'][0]['id'])
        payload={'include_templates':False,'rule_version_ids':versions,'remote_worker_id':None}
        api(200,'POST','/api/v1/data-sources/'+source['id']+'/activation-preview',admin,payload)
        activation=api(200,'POST','/api/v1/data-sources/'+source['id']+'/activations',admin,payload)
        again=api(200,'POST','/api/v1/data-sources/'+source['id']+'/activations',admin,payload)
        assert not again['changed'] and again['collector_id']==activation['collector_id']
        state['resources'].append({'id':source['id'],'name':source['name'],'provider':source['source_type'],'collector_id':activation['collector_id'],'activation':payload})
    (PRIVATE/'session.json').write_text(json.dumps(state));(PRIVATE/'session.json').chmod(0o600)
    report={'origins':{'AWS_EC2':'CONTROLLED_BOTOCORE_STUBBER','LINUX_HOST':'LIVE_LOCAL_LINUX','WINDOWS_HOST':'CONTROLLED_WINDOWS_API_INPUTS'},'genuine_aws':'PENDING_SANDBOX_IDENTITY','genuine_windows':'PENDING_NATIVE_WORKER','phases':[]}
    (PRIVATE/'report.json').write_text(json.dumps(report,indent=2))
    print('Scoped discovery/import and versioned infrastructure activation PASS')

def collect(phase):
    state=json.loads((PRIVATE/'session.json').read_text());(PRIVATE/'phase').write_text('failed' if phase=='failed' else 'healthy')
    ADAPTERS.update({'AWS_EC2':EC2Controlled(),'WINDOWS_HOST':WindowsControlled()})
    for resource in state['resources']:
        if phase=='recovered' and resource['provider']=='LINUX_HOST':
            api(200,'PATCH','/api/v1/resource-management/data-sources/'+resource['id'],state['admin_token'],{'connection_config':{'disk_path':'/','process_pid':int(os.environ['LINUX_TARGET_PID'])}})
            api(200,'POST','/api/v1/data-sources/'+resource['id']+'/activations',state['admin_token'],resource['activation'])
        asyncio.run(execute_collector(UUID(resource['collector_id'])))
    print('Infrastructure workers collected:',phase)

def verify(phase):
    state=json.loads((PRIVATE/'session.json').read_text());report=json.loads((PRIVATE/'report.json').read_text())
    evidence=[]
    for resource in state['resources']:
        item=api(200,'GET','/api/v1/infrastructure/resources/'+resource['id'],state['reader_token'])
        assert item['health']==('CRITICAL' if phase=='failed' else 'HEALTHY'),(resource['name'],item['health'])
        assert item['open_alert_count']==(1 if phase=='failed' else 0)
        active=[c for c in item['collectors'] if c['enabled']]
        assert len(active)==1 and active[0]['freshness']=='CURRENT'
        assert active[0]['evidence'] and item['metrics']
        assert all(c['last_error'] is None for c in active) if phase!='failed' else True
        history=api(200,'GET','/api/v1/infrastructure/resources/'+resource['id']+'/history',state['reader_token'])
        assert len(history)=={'healthy':1,'failed':2,'recovered':3}[phase]
        if phase=='recovered':assert len(item['alerts'])==1 and item['alerts'][0]['status']=='RESOLVED'
        evidence.append({'name':resource['name'],'provider':resource['provider'],'health':item['health'],
            'metrics':item['metrics'],'latest_evidence':active[0]['evidence'],'alerts':item['alerts']})
    with SessionLocal() as db:
        rows=db.scalars(select(InfrastructureEvidence)).all()
        assert len(rows)==3*{'healthy':1,'failed':2,'recovered':3}[phase]
        assert all(str(row.organization_id)==state['org_id'] for row in rows)
        assert not any('password' in json.dumps(row.payload).lower() or 'token' in json.dumps(row.payload).lower() for row in rows)
    report['phases'].append({'phase':phase,'resources':evidence})
    (PRIVATE/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Infrastructure database, telemetry and alert evidence:',phase,'PASS')

def isolation():
    state=json.loads((PRIVATE/'session.json').read_text());resource=state['resources'][0];path='/api/v1/infrastructure/resources/'+resource['id']
    api(401,'GET','/api/v1/infrastructure/resources')
    api(404,'GET',path,state['other_token']);api(404,'GET',path+'/history',state['other_token'])
    other=api(200,'GET','/api/v1/infrastructure/resources',state['other_token']);assert other['resources']==[]
    api(404,'POST','/api/v1/data-sources/'+resource['id']+'/activations',state['other_token'],resource['activation'])
    api(403,'POST','/api/v1/data-sources/'+resource['id']+'/activations',state['operator_token'],resource['activation'])
    api(403,'POST','/api/v1/resource-management/collectors',state['operator_token'],{'data_source_id':resource['id'],'name':'bypass-local-worker','collector_type':'AWS_EC2','configuration':{'region':'ap-south-1','account_id':'123456789012','instance_id':'i-0123456789abcdef0'}})
    api(403,'PATCH','/api/v1/resource-management/collectors/'+resource['collector_id'],state['operator_token'],{'collector_type':'HTTP','configuration':{'url':'https://unapproved.example.test'}})
    api(403,'POST','/api/v1/resource-discovery/sources/'+resource['id']+'/scan',state['reader_token'])
    api(403,'POST','/api/v1/resource-discovery/sources/'+resource['id']+'/scan',state['operator_token'])
    # An evidence gap stays UNKNOWN even when a past sample was healthy.
    with SessionLocal() as db:
        rows=db.scalars(select(InfrastructureEvidence).where(InfrastructureEvidence.data_source_id==UUID(resource['id']))).all()
        originals={row.id:row.observed_at for row in rows}
        for row in rows:row.observed_at-=timedelta(hours=1)
        db.commit()
    assert api(200,'GET',path,state['reader_token'])['health']=='UNKNOWN'
    with SessionLocal() as db:
        for identity,observed in originals.items():db.get(InfrastructureEvidence,identity).observed_at=observed
        db.commit()
    report=json.loads((PRIVATE/'report.json').read_text());report['security']='PASS';report['stale_evidence']='UNKNOWN'
    audit=api(200,'GET','/api/v1/auth/audit?limit=500',state['admin_token'])
    assert any(e['outcome']=='SUCCESS' and e['target_id']=='/api/v1/data-sources/'+resource['id']+'/activations' for e in audit)
    report['audit_event_count']=len(audit);(PRIVATE/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Tenant isolation, local-worker authorization, stale evidence PASS')

if __name__=='__main__':
    if os.getenv('ENVIRONMENT')!='demo' or os.getenv('OPSCONTROL_INFRA_ACCEPTANCE')!='1':raise SystemExit('Disposable controlled acceptance only')
    command=sys.argv[1]
    if command=='setup':setup()
    elif command=='isolation':isolation()
    elif command.startswith('collect-'):collect(command.removeprefix('collect-'))
    else:verify(command)
