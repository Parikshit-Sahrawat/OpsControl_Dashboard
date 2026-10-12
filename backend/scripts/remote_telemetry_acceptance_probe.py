"""Actual controlled Basic-auth HTTPS + worker heartbeat + native evidence.

Only disposable release labs. DNS is a controlled hostname-to-private-IP mapping;
TLS verification, HTTP auth, control-plane requests and PostgreSQL are genuine.
"""
import base64
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import secrets
import socket
import time
import subprocess
from unittest.mock import patch
from uuid import uuid4
from sqlalchemy import select, func
from app.db.session import SessionLocal
from app.models import Organization, DataSource, Collector, MetricDefinition, MetricSample, AlertRule, AlertState, OperationalIncident
from app.security.models import WorkerIdentity
from app.worker.egress import EgressDenied, policy_hosts, policy_cidrs, probe_https, resolve_target
from scripts.run_remote_agent import run_once
from scripts import remote_protocol_probe as protocol

HOSTNAME = 'basic-fixture.example.test'

def main():
    if os.getenv('OPSCONTROL_RELEASE_ACCEPTANCE') != '1' or os.getenv('ENVIRONMENT') != 'demo':
        raise SystemExit('Explicit disposable release lab required')
    base = os.environ['TEST_API_BASE']; protocol.BASE = base
    private = Path(os.environ['RELEASE_PRIVATE_DIR'])
    fixture_dir = private/'basic-fixture'; fixture_dir.mkdir(mode=0o700)
    cert, key = fixture_dir/'tls.crt', fixture_dir/'tls.key'
    subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
        '-keyout', str(key), '-out', str(cert), '-subj', '/CN='+HOSTNAME,
        '-addext', 'subjectAltName=DNS:'+HOSTNAME], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    password = secrets.token_urlsafe(24)
    (fixture_dir/'credentials.json').write_text(json.dumps({'username':'fixture-reader','password':password}))
    (fixture_dir/'credentials.json').chmod(0o600)
    (fixture_dir/'state').write_text('healthy')
    name = 'opscontrol-basic-'+secrets.token_hex(4); network = name+'-net'
    def docker(*args):
        result = subprocess.run(['docker', *args],capture_output=True,text=True,timeout=60)
        if result.returncode: raise RuntimeError('Controlled Basic TLS fixture setup failed')
        return result.stdout.strip()
    def reads():
        path = fixture_dir/'reads.jsonl'
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
    docker('network','create','--internal',network)
    try:
        docker('run','-d','--name',name,'--network',network,
            '-v',str(fixture_dir)+':/fixture',
            '-v',str(Path(__file__).resolve().parents[2]/'deploy/fixtures/basic_https_api.py')+':/app.py:ro',
            'python:3.12-alpine','python','/app.py')
        host = docker('inspect','--format','{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}',name)
        for _ in range(100):
            try:
                with socket.create_connection((host,443),timeout=.5): pass
                break
            except OSError: time.sleep(.1)
        else: raise RuntimeError('Controlled Basic TLS fixture not ready')
    except BaseException:
        subprocess.run(['docker','rm','-f',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        subprocess.run(['docker','network','rm',network],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        raise
    original_dns = socket.getaddrinfo
    def dns(name, port, *args, **kwargs):
        if name == HOSTNAME:
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (host, port))]
        return original_dns(name, port, *args, **kwargs)
    environment = {'SSL_CERT_FILE': str(cert), 'OPSCONTROL_ALLOWED_CREDENTIAL_REFS': 'basic-fixture',
        'OPSCONTROL_CREDENTIAL_BASIC_FIXTURE_USERNAME': 'fixture-reader',
        'OPSCONTROL_CREDENTIAL_BASIC_FIXTURE_PASSWORD': password}
    try:
        admin = protocol.check(200, 'POST', '/api/v1/auth/login', body={
            'username': 'test-admin', 'password': protocol.PASSWORD})['access_token']
        with SessionLocal() as db:
            org = db.scalar(select(Organization).where(Organization.code == 'LAB-N'))
            source = DataSource(organization_id=org.id, name='Basic TLS sequence fixture', source_type='HTTPS',
                endpoint='https://'+HOSTNAME+'/ready', auth_type='BASIC', connection_config={'credential_ref':'basic-fixture'})
            db.add(source); db.flush()
            collector = Collector(data_source_id=source.id, name='Basic TLS remote collector', collector_type='HTTP',
                configuration={'url':source.endpoint, 'expected_status':200, 'timeout_seconds':5, 'credential_ref':'basic-fixture'})
            db.add(collector); db.flush()
            metric = MetricDefinition(organization_id=org.id, data_source_id=source.id, collector_id=collector.id,
                name='http_availability', metric_type='GAUGE', resource_type='APPLICATION', query_config={'extract':'AVAILABILITY'})
            db.add(metric); db.flush()
            rule = AlertRule(organization_id=org.id, metric_definition_id=metric.id, name='Basic TLS availability',
                operator='LT', threshold_value='0.5', consecutive_breaches=2, notification_channels=[])
            db.add(rule); db.flush()
            ids = {'org':str(org.id), 'collector':str(collector.id), 'metric':metric.id, 'rule':rule.id}
            db.commit()
        worker = protocol.check(201,'POST','/api/v1/auth/workers',admin,
            {'organization_id':ids['org'],'name':'basic-heartbeat-fixture','expires_in_days':1})
        token = worker['worker_token']
        protocol.check(401,'POST','/api/v1/worker/heartbeat',admin,{})
        protocol.check(422,'POST','/api/v1/worker/heartbeat',token,{'observed_at':'2099-01-01T00:00:00Z'})
        beat = protocol.check(200,'POST','/api/v1/worker/heartbeat',token,{})
        assert beat['worker_id']==worker['id'] and beat['organization_id']==ids['org']
        with SessionLocal() as db:
            from uuid import UUID
            assert db.get(WorkerIdentity,UUID(worker['id'])).last_seen_at is not None
            assert db.scalar(select(func.count()).select_from(MetricSample).where(MetricSample.metric_definition_id==ids['metric']))==0
        protocol.check(200,'PUT',f"/api/v1/remote-probes/workers/{worker['id']}/network-policy",admin,
            {'allowed_hosts':[HOSTNAME],'allowed_cidrs':[host+'/32']})
        protocol.check(200,'PUT','/api/v1/remote-probes/collectors/'+ids['collector']+'/assignment',admin,{'worker_id':worker['id']})
        with patch.dict(os.environ, environment), patch('app.worker.egress.resolve_target',
                side_effect=lambda name, networks: resolve_target(name, networks, resolver=dns)):
            cfg = {'url':'https://'+HOSTNAME+'/ready','credential_ref':'basic-fixture'}
            before = len(reads())
            with patch.dict(os.environ, {'OPSCONTROL_ALLOWED_CREDENTIAL_REFS':''}):
                try: probe_https(cfg,[HOSTNAME],[host+'/32'])
                except EgressDenied: pass
                else: raise AssertionError('Unapproved credential reference used')
            assert len(reads())==before
            # A redirect remains observed evidence; no second origin receives auth.
            redirect = probe_https({**cfg,'url':'https://'+HOSTNAME+'/redirect'},[HOSTNAME],[host+'/32'])
            assert redirect['http_status']==302 and redirect['outcome']=='ASSERTION_FAILED'
            for healthy in (True, False, False, False, True):
                (fixture_dir/'state').write_text('healthy' if healthy else 'failed')
                job_id = str(uuid4())
                protocol.check(201,'POST','/api/v1/remote-probes/jobs',admin,
                    {'collector_id':ids['collector'],'worker_id':worker['id'],'idempotency_key':job_id})
                assert run_once(base,token,policy_hosts([HOSTNAME]),policy_cidrs([host+'/32']))
        with SessionLocal() as db:
            samples = db.scalars(select(MetricSample).where(MetricSample.metric_definition_id==ids['metric']).order_by(MetricSample.observed_at)).all()
            assert [sample.value_numeric for sample in samples]==[1,0,0,0,1], 'Unexpected native availability observations'
            states = db.scalars(select(AlertState).where(AlertState.alert_rule_id==ids['rule'])).all()
            assert len(states)==1 and states[0].status=='RESOLVED'
            assert states[0].resolved_at is not None
            incident = db.scalar(select(OperationalIncident).where(OperationalIncident.source_reference==str(states[0].id)))
            assert incident is not None and incident.condition_status=='RECOVERED'
            serial = json.dumps([sample.dimensions for sample in samples])
            assert password not in serial
        protocol.check(204,'DELETE',f"/api/v1/auth/workers/{worker['id']}",admin)
        protocol.check(401,'POST','/api/v1/worker/heartbeat',token,{})
        facts = reads()
        assert len(facts)==6 and all(fact['authenticated'] for fact in facts)
        report = {'status':'PASS','origin':'Controlled DNS mapping; actual certificate-verified Basic HTTPS, authenticated control plane and PostgreSQL',
            'checks':['Unapproved credential denies before target request','Redirect never followed','Human/forged/revoked heartbeat denied',
                      'Server liveness creates no health sample','Five real authenticated probes persist [1,0,0,0,1]',
                      'Consecutive breach opens once, deduplicates, resolves and correlates'], 'authenticated_https_reads':6}
        output = Path(os.environ.get('RELEASE_EVIDENCE_DIR','/tmp/opscontrol-release-evidence')); output.mkdir(parents=True,exist_ok=True)
        (output/'remote-telemetry.json').write_text(json.dumps(report,indent=2)+'\n')
        print('ACTUAL BASIC TLS / HEARTBEAT / NATIVE TELEMETRY / ALERT CORRELATION PASS')
    finally:
        subprocess.run(['docker','rm','-f',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        subprocess.run(['docker','network','rm',network],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

if __name__=='__main__': main()
