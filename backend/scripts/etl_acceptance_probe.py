"""Authenticated controlled Carte polling -> ETL evidence, alerts and investigation."""
import asyncio, json, os, secrets, sys, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID
from sqlalchemy import select, func
from app.db.session import SessionLocal
from app.models import JobOrderHistory, Collector, AlertIncidentEvent, CollectorRun, Investigation
from app.worker.collector_runtime import execute_collector
PRIVATE=Path(os.environ['ETL_PRIVATE_DIR']);BASE='http://127.0.0.1:18800'

def api(status,method,path,token=None,body=None):
    request=urllib.request.Request(BASE+path,method=method,data=json.dumps(body).encode() if body is not None else None,
        headers={'Content-Type':'application/json',**({'Authorization':'Bearer '+token} if token else {})})
    try:
        with urllib.request.urlopen(request,timeout=20) as response:actual,data=response.status,json.loads(response.read() or b'null')
    except urllib.error.HTTPError as error:actual,data=error.code,json.loads(error.read() or b'null')
    assert actual==status,(method,path,status,actual)
    return data

def login(user,password):return api(200,'POST','/api/v1/auth/login',body={'username':user,'password':password})['access_token']
def load():return json.loads((PRIVATE/'session.json').read_text())

def setup():
    state={'admin_token':login('demo-admin',(PRIVATE/'admin-password').read_text().strip())};admin=state['admin_token']
    org=api(201,'POST','/api/v1/organizations',admin,{'name':'Controlled ETL Lab','code':'ETL-LAB'})
    other=api(201,'POST','/api/v1/organizations',admin,{'name':'Other ETL Tenant','code':'ETL-OTHER'})
    state.update(org_id=org['id'],other_org_id=other['id'])
    for who,scope,role in [('reader',org,'viewer'),('operator',org,'operator'),('owner',org,'org_admin'),('other',other,'org_admin')]:
        password=secrets.token_urlsafe(32);user=api(201,'POST','/api/v1/auth/users',admin,{'username':'etl-'+who,'password':password})
        api(201,'POST','/api/v1/auth/memberships',admin,{'user_id':user['id'],'organization_id':scope['id'],'role':role})
        state[who+'_username']='etl-'+who;state[who+'_password']=password;state[who+'_token']=login('etl-'+who,password)
    host=api(201,'POST','/api/v1/resource-management/data-sources',admin,{'organization_id':org['id'],'name':'ETL live Linux worker','source_type':'LINUX_HOST','connection_config':{'disk_path':'/','process_pid':int(os.environ['LINUX_TARGET_PID'])}})
    metric=api(201,'POST','/api/v1/rule-catalogs',admin,{'organization_id':org['id'],'name':'etl-host-up','kind':'METRIC','definition':{'name':'infrastructure_up','metric_type':'GAUGE'}})
    alert=api(201,'POST','/api/v1/rule-catalogs',admin,{'organization_id':org['id'],'name':'etl-host-health','kind':'ALERT','definition':{'name':'etl-host-health','metric_name':'infrastructure_up','operator':'LT','threshold_value':.5,'severity':'CRITICAL','consecutive_breaches':1}})
    activation=api(200,'POST','/api/v1/data-sources/'+host['id']+'/activations',admin,{'include_templates':False,'rule_version_ids':[metric['versions'][0]['id'],alert['versions'][0]['id']],'remote_worker_id':None})
    now=datetime.now(timezone.utc)
    job=api(201,'POST','/api/v1/etl/job-orders',admin,{'organization_id':org['id'],'hostname':'etl-controlled-worker','name':'Fictional Daily Warehouse','expected_runtime_seconds':60,'sla_seconds':120,'host_data_source_id':host['id'],
        'expected_window_start':(now-timedelta(minutes=20)).strftime('%H:%M'),'expected_window_end':(now-timedelta(minutes=10)).strftime('%H:%M'),'no_run_grace_seconds':60,'timezone':'UTC'})
    source=api(201,'POST','/api/v1/resource-management/data-sources',admin,{'organization_id':org['id'],'name':'Controlled HTTPS Carte','source_type':'PENTAHO'})
    cfg={'url':'https://'+os.environ['ETL_FIXTURE_IP'],'job_name':job['name'],'job_order_id':job['id'],'credential_ref':'etl-fixture','allowed_hosts':[os.environ['ETL_FIXTURE_IP']],'allowed_cidrs':[os.environ['ETL_FIXTURE_IP']+'/32'],'collect_logs':True}
    collector=api(201,'POST','/api/v1/resource-management/collectors',admin,{'data_source_id':source['id'],'name':'read-only-carte-history','collector_type':'PENTAHO','interval_seconds':3600,'configuration':cfg})
    state.update(job_id=job['id'],collector_id=collector['id'],source_id=source['id'],host_id=host['id'],host_collector_id=activation['collector_id'],collector_config=cfg)
    (PRIVATE/'session.json').write_text(json.dumps(state));(PRIVATE/'session.json').chmod(0o600)
    (PRIVATE/'report.json').write_text(json.dumps({'origin':'CONTROLLED_AUTHENTICATED_PINNED_HTTPS_CARTE_SHAPED_API','genuine_carte_acceptance':'PENDING_SEPARATE_READ_ONLY_GATE','host_origin':'LIVE_LOCAL_LINUX','phases':[]}))
    print('Scoped ETL Job Order, monitoring policy, credential reference and live host activation PASS')

def collect(phase):
    state=load();(PRIVATE/'phase').write_text(phase)
    if phase=='recovered':
        api(200,'PATCH','/api/v1/resource-management/collectors/'+state['host_collector_id'],state['admin_token'],{'configuration':{'disk_path':'/','process_pid':int(os.environ['LINUX_TARGET_PID'])}})
    asyncio.run(execute_collector(UUID(state['host_collector_id'])))
    asyncio.run(execute_collector(UUID(state['collector_id'])))
    # Repeated authenticated status polling must not duplicate executions/events.
    with SessionLocal() as db:
        count=db.scalar(select(func.count()).select_from(JobOrderHistory).where(JobOrderHistory.job_order_id==UUID(state['job_id'])))
        event_count=db.scalar(select(func.count()).select_from(AlertIncidentEvent))
    asyncio.run(execute_collector(UUID(state['collector_id'])))
    with SessionLocal() as db:
        assert count==db.scalar(select(func.count()).select_from(JobOrderHistory).where(JobOrderHistory.job_order_id==UUID(state['job_id'])))
        assert event_count==db.scalar(select(func.count()).select_from(AlertIncidentEvent))
    print('Actual authenticated HTTPS Carte reads and idempotent lifecycle collection PASS:',phase)

def verify(phase):
    state=load();reader=state['reader_token'];history=api(200,'GET','/api/v1/etl/executions',reader)
    current=api(200,'GET','/api/v1/etl/executions?latest_only=true',reader)
    assert len(current)==1
    expected={'no-run':'NO_RUN','running':'RUNNING','long-running':'LONG_RUNNING','sla-breach':'LONG_RUNNING','failed':'FAILED','poll-failed':'FAILED','recovered':'SUCCESS'}[phase]
    assert current[0]['status']==expected,(phase,current[0]['status'])
    assert current[0]['monitoring_status']==('ERROR' if phase=='poll-failed' else 'CURRENT')
    detail=api(200,'GET','/api/v1/etl/executions/'+current[0]['id'],reader)
    evidence=api(200,'GET','/api/v1/etl/executions/'+current[0]['id']+'/evidence',reader)
    if phase=='no-run':assert detail['started_at'] is None and detail['source_result']=='OPSCONTROL_SCHEDULE'
    else:
        assert detail['started_at'] and len(detail['steps'])==2
        assert 'fixture-sensitive-marker' not in json.dumps(detail)
        assert (PRIVATE/'carte-password').read_text().strip() not in json.dumps(detail)
    if phase=='sla-breach':assert detail['sla_status']=='BREACHED'
    if phase=='failed':
        assert detail['failed_step']=='Load warehouse'
        correlation=api(200,'GET','/api/v1/etl/executions/'+detail['id']+'/correlation',reader)
        assert any(e['evidence_type']=='ALERT_STATE' and e['details']['status']=='OPEN' for e in correlation['evidence'])
        assert correlation['primary_category']=='RESOURCE_ALERT'
        state['failed_execution_id']=detail['id'];(PRIVATE/'session.json').write_text(json.dumps(state))
        # GET for missing investigation is read-only and safe for viewers.
        api(404,'GET','/api/v1/etl/executions/'+detail['id']+'/investigation',reader)
        transition=api(201,'POST','/api/v1/etl/executions/'+detail['id']+'/investigation/transitions',state['operator_token'],{'new_status':'ACKNOWLEDGED','operator':'spoofed-identity'})
        assert transition['operator']=='etl-operator'
        note=api(201,'POST','/api/v1/etl/executions/'+detail['id']+'/investigation/notes',state['operator_token'],{'text':'Controlled warehouse failure coincided with host process loss. Correlation requires investigation.','operator':'spoofed-identity'})
        assert note['operator']=='etl-operator'
        api(409,'POST','/api/v1/etl/executions/'+detail['id']+'/investigation/transitions',state['operator_token'],{'new_status':'RESOLVED','operator':'ignored'})
        api(200,'POST','/api/v1/etl/executions/'+detail['id']+'/correlation',state['operator_token'])
    if phase=='poll-failed':
        assert len(history)==5 and detail['id']==state['failed_execution_id']
    if phase=='recovered':
        assert len(history)==6 and any(h['status']=='FAILED' for h in history) and any(h['status']=='NO_RUN' for h in history)
        inv=api(200,'GET','/api/v1/etl/executions/'+state['failed_execution_id']+'/investigation',reader)
        assert inv['status']=='INVESTIGATING' and len(inv['notes'])==2
        by_reference={}
        for event in reversed(evidence['alert_events']):by_reference.setdefault(event['reference'],[]).append(event['event_type'])
        assert len(by_reference)==4 and all(events[-1].endswith('_RESOLVED') for events in by_reference.values()),by_reference
    report=json.loads((PRIVATE/'report.json').read_text());report['phases'].append({'phase':phase,'execution':detail,'evidence':evidence})
    (PRIVATE/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('ETL PostgreSQL, source facts, monitoring condition and alert evidence PASS:',phase)

def isolation():
    semantics()
    from scripts import remote_protocol_probe
    remote_protocol_probe.BASE=BASE
    remote_protocol_probe.main()
    state=load();eid=state['failed_execution_id'];path='/api/v1/etl/executions/'+eid
    api(401,'GET','/api/v1/etl/executions')
    assert api(200,'GET','/api/v1/etl/executions',state['other_token'])==[]
    for suffix in ('','/evidence','/correlation','/investigation'):api(404,'GET',path+suffix,state['other_token'])
    api(404,'POST',path+'/correlation',state['other_token'])
    api(404,'POST',path+'/investigation/notes',state['other_token'],{'operator':'forged','text':'forbidden'})
    api(403,'POST',path+'/investigation/notes',state['reader_token'],{'operator':'forged','text':'forbidden'})
    api(403,'POST',path+'/correlation',state['reader_token'])
    api(403,'PATCH','/api/v1/resource-management/collectors/'+state['collector_id'],state['owner_token'],{'configuration':state['collector_config'] | {'job_name':'Unapproved alternate job'}})
    api(403,'POST','/api/v1/resource-management/collectors',state['owner_token'],{'data_source_id':state['source_id'],'name':'privileged-bypass','collector_type':'PENTAHO','configuration':state['collector_config']})
    api(409,'POST','/api/v1/etl/job-orders',state['other_token'],{'organization_id':state['other_org_id'],'hostname':'unrelated','name':'cross-host','expected_runtime_seconds':60,'sla_seconds':120,'host_data_source_id':state['host_id']})
    # Authentication rejection is an actual TLS fixture response.
    import ssl
    context=ssl.create_default_context()
    for method,path,expected in [('GET','/kettle/status/?xml=Y',401),('POST','/kettle/startJob/',403)]:
        request=urllib.request.Request('https://'+os.environ['ETL_FIXTURE_IP']+path,method=method)
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=context))
        try:opener.open(request,timeout=5)
        except urllib.error.HTTPError as e:assert e.code==expected
        else:raise AssertionError('Controlled Carte boundary failed')
    requests=[json.loads(line) for line in (PRIVATE/'carte-requests.jsonl').read_text().splitlines()]
    successful=[r for r in requests if r['status']==200]
    assert successful and all(r['method']=='GET' and r['path'] in {'/kettle/status/','/kettle/jobStatus/'} for r in successful)
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(JobOrderHistory).where(JobOrderHistory.job_order_id==UUID(state['job_id'])))==6
        assert db.scalar(select(func.count()).select_from(CollectorRun).where(CollectorRun.collector_id==UUID(state['collector_id']),CollectorRun.status=='FAILED'))==2
        assert db.scalar(select(func.count()).select_from(Investigation))==1
    report=json.loads((PRIVATE/'report.json').read_text());audit=api(200,'GET','/api/v1/auth/audit?limit=500',state['admin_token'])
    assert any(item['outcome']=='DENIED' for item in audit)
    report.update(security='PASS',audit_event_count=len(audit),read_only_https_requests=len(successful),fixture_requests=requests)
    (PRIVATE/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('ETL tenancy, viewer/worker authorization, actor attribution, read-only TLS and audit checks PASS')

def semantics():
    """Transactional negatives that do not alter the runtime acceptance evidence."""
    from types import SimpleNamespace
    from app.models import JobOrder
    from app.services.etl_monitoring import ingest_snapshot
    from app.worker.collector_runtime import CollectionResult, PentahoAdapter
    state=load();instant=datetime(2026,10,11,15,14,tzinfo=timezone.utc)
    empty=CollectionResult(True,'Controlled complete inventory',{'provider':'PENTAHO','inventory_complete':True,'executions':[]})
    failure=CollectionResult(False,'Controlled unavailable poll',{'outcome':'PROVIDER_ERROR'})
    with SessionLocal() as db:
        original=db.get(JobOrder,UUID(state['job_id']))
        job=JobOrder(organization_id=original.organization_id,vm_id=original.vm_id,name='transactional-semantics',expected_runtime_seconds=60,sla_seconds=120,
            expected_window_start='14:00',expected_window_end='15:00',no_run_grace_seconds=900,schedule={'timezone':'UTC'})
        db.add(job);db.flush()
        collector=SimpleNamespace(id=UUID(state['collector_id']),data_source_id=UUID(state['source_id']),collector_type='PENTAHO',configuration={'job_order_id':str(job.id)})
        count=lambda:db.scalar(select(func.count()).select_from(JobOrderHistory).where(JobOrderHistory.job_order_id==job.id))
        ingest_snapshot(collector,empty,instant,db);assert count()==0  # within grace
        ingest_snapshot(collector,failure,instant+timedelta(minutes=2),db);assert count()==0  # no trusted inventory
        ingest_snapshot(collector,empty,instant+timedelta(minutes=1),db);assert count()==1
        ingest_snapshot(collector,empty,instant+timedelta(minutes=2),db);assert count()==1
        missing=db.scalar(select(JobOrderHistory).where(JobOrderHistory.job_order_id==job.id))
        assert missing.status.value=='NO_RUN' and missing.started_at is None and missing.ended_at is None
        unknown=JobOrder(organization_id=original.organization_id,vm_id=original.vm_id,name='unknown-source-time',expected_runtime_seconds=60,sla_seconds=120,
            expected_window_start='14:00',expected_window_end='15:00',no_run_grace_seconds=900,schedule={'timezone':'UTC'})
        db.add(unknown);db.flush();collector.configuration={'job_order_id':str(unknown.id)}
        unknown_result=CollectionResult(True,'Unknown source timing',{'provider':'PENTAHO','inventory_complete':True,'executions':[{'execution_id':'unknown-time','execution_status':'RUNNING','nr_errors':0}]})
        ingest_snapshot(collector,unknown_result,instant+timedelta(minutes=2),db)
        ingest_snapshot(collector,empty,instant+timedelta(minutes=3),db)
        rows=db.scalars(select(JobOrderHistory).where(JobOrderHistory.job_order_id==unknown.id)).all()
        assert len(rows)==1 and rows[0].status.value=='RUNNING' and rows[0].sla_status=='UNKNOWN' and rows[0].started_at is None
        failed=db.get(JobOrderHistory,UUID(state['failed_execution_id']));detected=failed.detected_at;ended=failed.ended_at
        collector.configuration={'job_order_id':str(original.id)}
        stale=CollectionResult(True,'Stale status',{'provider':'PENTAHO','execution_id':failed.provider_execution_id,'execution_status':'SUCCESS','nr_errors':0})
        ingest_snapshot(collector,stale,instant,db)
        assert failed.status.value=='FAILED' and failed.detected_at==detected and failed.ended_at==ended
        other_job=db.scalar(select(JobOrder).where(JobOrder.organization_id!=original.organization_id))
        collector.configuration={'job_order_id':str(other_job.id)}
        before=(PRIVATE/'carte-requests.jsonl').read_text()
        result=asyncio.run(PentahoAdapter().collect(collector))
        assert result.payload['outcome']=='CONFIGURATION_ERROR' and (PRIVATE/'carte-requests.jsonl').read_text()==before
        db.rollback()
    print('No Run grace, poll blindness, unknown source timing, terminal immutability and pre-network tenancy PASS')

if __name__=='__main__':
    if os.getenv('ENVIRONMENT')!='demo' or os.getenv('OPSCONTROL_ETL_ACCEPTANCE')!='1':raise SystemExit('Disposable ETL acceptance only')
    command=sys.argv[1]
    if command=='setup':setup()
    elif command=='isolation':isolation()
    elif command.startswith('collect-'):collect(command.removeprefix('collect-'))
    else:verify(command)
