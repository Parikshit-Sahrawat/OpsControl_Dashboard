"""Native alert/outbox lifecycle against an authenticated fictional TLS Table API.

No real external message or customer ServiceNow is contacted. Claims, fencing,
retries, correlation, recovery and persisted evidence use actual PostgreSQL.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import base64
import json
import os
from pathlib import Path
import secrets
import ssl
import subprocess
import threading
from unittest.mock import patch
from urllib.parse import urlsplit, parse_qs
from uuid import UUID, uuid4
from sqlalchemy import select, func
from app.db.session import SessionLocal, engine
from app.models import Organization, DataSource, MetricDefinition, MetricSample, AlertRule, AlertState, AlertNotificationDelivery, OperationalIncident
from app.worker.alert_engine import evaluate_metric_sample
from app.worker.notifications import dispatch_pending_notifications, _claim_notification, _finish_notification, MAX_ATTEMPTS

def main():
    if os.getenv('OPSCONTROL_RELEASE_ACCEPTANCE')!='1' or os.getenv('ENVIRONMENT')!='demo':
        raise SystemExit('Explicit disposable release lab required')
    private=Path(os.environ['RELEASE_PRIVATE_DIR']); cert=private/'snow.crt'; key=private/'snow.key'
    subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1',
        '-keyout',str(key),'-out',str(cert),'-subj','/CN=127.0.0.1','-addext','subjectAltName=IP:127.0.0.1'],
        check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    password=secrets.token_urlsafe(24)
    authorization='Basic '+base64.b64encode(('fixture-writer:'+password).encode()).decode()
    fixture={'records':{},'mode':'normal','posts':0,'patches':0,'redirect_targets':0}
    entered=threading.Event(); release=threading.Event()
    class TableAPI(BaseHTTPRequestHandler):
        def reply(self,code,value):
            body=json.dumps(value).encode(); self.send_response(code)
            self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(body)))
            self.end_headers(); self.wfile.write(body)
        def authorized(self):
            if self.headers.get('Authorization')==authorization: return True
            self.reply(401,{'error':'Authentication required'}); return False
        def do_GET(self):
            if not self.authorized(): return
            route=urlsplit(self.path)
            if route.path=='/redirect-target':
                fixture['redirect_targets']+=1; return self.reply(200,{'result':[]})
            if fixture['mode']=='redirect':
                self.send_response(302); self.send_header('Location','/redirect-target'); self.end_headers(); return
            if fixture['mode']=='bad-identity': return self.reply(200,{'result':[{'sys_id':'../../'+password}]})
            assert route.path=='/api/now/table/incident'
            params=parse_qs(route.query); corr=params['sysparm_query'][0].removeprefix('correlation_id=')
            record=fixture['records'].get(corr)
            self.reply(200,{'result':[{'sys_id':record['sys_id']}] if record else []})
        def do_POST(self):
            if not self.authorized(): return
            assert self.path=='/api/now/table/incident'
            payload=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            corr=payload['correlation_id']
            if corr in fixture['records']: return self.reply(409,{'error':'Duplicate correlation'})
            fixture['posts']+=1
            record={'sys_id':uuid4().hex,'state':'1',**payload}; fixture['records'][corr]=record
            if fixture['mode']=='pause':
                entered.set()
                if not release.wait(timeout=15): return self.reply(503,{'error':'Controlled timeout'})
            if fixture['mode']=='fail-after-create': return self.reply(503,{'error':password})
            self.reply(201,{'result':{'sys_id':record['sys_id']}})
        def do_PATCH(self):
            if not self.authorized(): return
            identity=self.path.rsplit('/',1)[-1]
            records=[r for r in fixture['records'].values() if r['sys_id']==identity]
            assert len(records)==1
            payload=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            assert set(payload)<= {'state','close_notes','close_code'} and payload['state']=='6'
            records[0].update(payload); fixture['patches']+=1
            self.reply(200,{'result':{'sys_id':identity}})
        def log_message(self,*_): pass
    server=ThreadingHTTPServer(('127.0.0.1',0),TableAPI)
    tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); tls.load_cert_chain(cert,key)
    server.socket=tls.wrap_socket(server.socket,server_side=True)
    thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    origin=f'https://127.0.0.1:{server.server_port}'
    env={'SSL_CERT_FILE':str(cert),'OPSCONTROL_SERVICENOW_URL':origin,
         'OPSCONTROL_SERVICENOW_USERNAME':'fixture-writer','OPSCONTROL_SERVICENOW_PASSWORD':password,
         'OPSCONTROL_SERVICENOW_CREDENTIAL_REF':'','OPSCONTROL_SERVICENOW_TABLE':'incident',
         'OPSCONTROL_SERVICENOW_CORRELATION_FIELD':'correlation_id','OPSCONTROL_SERVICENOW_RESOLVED_STATE':'6'}
    try:
        with SessionLocal() as db:
            org=db.scalar(select(Organization).where(Organization.code=='LAB-N'))
            source=DataSource(organization_id=org.id,name='ServiceNow lifecycle fixture',source_type='API')
            db.add(source); db.flush()
            metric=MetricDefinition(organization_id=org.id,data_source_id=source.id,name='snow_fixture_up',
                metric_type='GAUGE',resource_type='APPLICATION')
            db.add(metric); db.flush()
            rule=AlertRule(organization_id=org.id,metric_definition_id=metric.id,name='ServiceNow synthetic availability',
                operator='LT',threshold_value='0.5',consecutive_breaches=2,notification_channels=['SERVICENOW','SERVICENOW'])
            db.add(rule); db.flush(); metric_id,rule_id=metric.id,rule.id; db.commit()
        stamp=datetime.now(timezone.utc)-timedelta(minutes=1); sequence=0
        def emit(value):
            nonlocal sequence
            sequence+=1
            with SessionLocal() as db:
                metric=db.get(MetricDefinition,metric_id)
                sample=MetricSample(organization_id=metric.organization_id,metric_definition_id=metric_id,
                    observed_at=stamp+timedelta(seconds=sequence),value_numeric=value)
                db.add(sample); db.flush(); state=evaluate_metric_sample(db,sample)
                result=state.id if state else None; db.commit(); return result
        def delivery(state_id,event):
            with SessionLocal() as db:
                return db.scalar(select(AlertNotificationDelivery).where(
                    AlertNotificationDelivery.alert_state_id==state_id,AlertNotificationDelivery.event_type==event))
        with patch.dict(os.environ,env):
            emit(1); assert emit(0) is None
            state_id=emit(0); assert state_id is not None
            assert emit(0)==state_id
            with SessionLocal() as db:
                assert db.scalar(select(func.count()).select_from(AlertNotificationDelivery).where(AlertNotificationDelivery.alert_state_id==state_id))==1
            fixture['mode']='pause'
            with ThreadPoolExecutor(max_workers=2) as pool:
                first=pool.submit(dispatch_pending_notifications)
                assert entered.wait(timeout=5)
                # Network IO owns no DB connection or row lock.
                assert engine.pool.checkedout()==0
                with SessionLocal() as db:
                    db.scalar(select(AlertNotificationDelivery).where(AlertNotificationDelivery.alert_state_id==state_id).with_for_update(nowait=True))
                second=pool.submit(dispatch_pending_notifications).result(timeout=5)
                assert second['claimed']==0
                release.set(); result=first.result(timeout=15)
                assert result['sent']==1
            fixture['mode']='normal'
            open_row=delivery(state_id,'OPENED'); reference=open_row.external_reference
            assert open_row.status=='SENT' and fixture['posts']==1
            assert emit(1)==state_id
            assert dispatch_pending_notifications()['sent']==1
            closed=delivery(state_id,'RESOLVED')
            assert closed.status=='SENT' and closed.external_reference==reference
            assert fixture['patches']==1 and list(fixture['records'].values())[0]['state']=='6'
            with SessionLocal() as db:
                assert db.get(AlertState,state_id).status=='RESOLVED'
                assert db.scalar(select(OperationalIncident).where(OperationalIncident.alert_state_id==state_id)).condition_status=='RECOVERED'
            # Crash/HTTP ambiguity after provider creation must reuse correlation.
            emit(0); retry_state=emit(0)
            fixture['mode']='fail-after-create'
            assert dispatch_pending_notifications()['failed']==1
            failed=delivery(retry_state,'OPENED')
            assert failed.status=='FAILED' and password not in failed.last_error
            with SessionLocal() as db:
                db.get(AlertNotificationDelivery,failed.id).updated_at=datetime.now(timezone.utc)-timedelta(seconds=31); db.commit()
            fixture['mode']='normal'
            assert dispatch_pending_notifications()['sent']==1
            assert fixture['posts']==2 and len(fixture['records'])==2
            emit(1); assert dispatch_pending_notifications()['sent']==1
            # Expired lease cannot overwrite a recovered delivery.
            emit(0); fence_state=emit(0)
            claimed=_claim_notification(); assert claimed and claimed[0].alert_state_id==fence_state
            owned,_,token=claimed
            with SessionLocal() as db:
                db.get(AlertNotificationDelivery,owned.id).lease_expires_at=datetime.now(timezone.utc)-timedelta(seconds=1); db.commit()
            assert _finish_notification(owned.id,token,reference='f'*32) is False
            assert dispatch_pending_notifications()['sent']==1
            assert _finish_notification(owned.id,token,reference='f'*32) is False
            emit(1); assert dispatch_pending_notifications()['sent']==1
            # Provider identity/path injection and redirect remain failed evidence.
            emit(0); invalid_state=emit(0); fixture['mode']='bad-identity'
            assert dispatch_pending_notifications()['failed']==1
            invalid=delivery(invalid_state,'OPENED')
            assert invalid.status=='FAILED' and invalid.external_reference is None and password not in invalid.last_error
            with SessionLocal() as db:
                db.get(AlertNotificationDelivery,invalid.id).updated_at=datetime.now(timezone.utc)-timedelta(seconds=31); db.commit()
            fixture['mode']='redirect'
            assert dispatch_pending_notifications()['failed']==1 and fixture['redirect_targets']==0
            with SessionLocal() as db:
                db.get(AlertNotificationDelivery,invalid.id).attempts=MAX_ATTEMPTS; db.commit()
        report={'status':'PASS','origin':'Native synthetic metric/alert/incident evidence and real certificate-verified authenticated local ServiceNow-shaped TLS API',
            'checks':['Consecutive breach/dedup and duplicate channel normalization','Concurrent dispatcher claim sends once',
                'No DB connection/row lock held during provider IO','Same incident sys_id resolves after recovery',
                'Creation ambiguity retry reuses correlation without another POST','Expired lease completion fenced',
                'Malformed incident identity and redirect rejected; provider secret absent from error evidence'],
            'provider_incidents':len(fixture['records']),'provider_creates':fixture['posts'],'provider_resolves':fixture['patches'],
            'limitations':['Fictional Table API, not genuine ServiceNow acceptance','Actual field choices, ACLs, mandatory closure fields and correlation uniqueness need instance acceptance']}
        out=Path(os.getenv('RELEASE_EVIDENCE_DIR','/tmp/opscontrol-release-evidence')); out.mkdir(parents=True,exist_ok=True)
        (out/'servicenow.json').write_text(json.dumps(report,indent=2)+'\n')
        print('NATIVE ALERT / SERVICENOW TLS / SHORT LEASE / RETRY / RECOVERY ACCEPTANCE PASS')
    finally:
        release.set(); server.shutdown(); server.server_close(); thread.join(timeout=5)

if __name__=='__main__': main()
