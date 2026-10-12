#!/usr/bin/env python3
"""Disposable populated PostgreSQL restore, retention and TLS deployment gate.

No live cloud credentials, existing volumes, database resets or public ports.
Failure artifacts contain private fixture data and remain outside the checkout.
"""
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.error
import ssl
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
PYTHON = str(ROOT/'backend/.venv/bin/python')
OUT = Path(os.getenv('RELEASE_EVIDENCE_DIR', '/tmp/opscontrol-release-evidence'))
private = Path(tempfile.mkdtemp(prefix='opscontrol-release-')); private.chmod(0o700)
prefix = 'opscontrol-release-'+secrets.token_hex(4)
database, ingress = prefix+'-pg', prefix+'-tls'
processes = []; containers = []; checks = []; passed = False
environment = os.environ.copy()
for name in ('AWS_PROFILE','AWS_DEFAULT_PROFILE','AWS_ACCESS_KEY_ID','AWS_SECRET_ACCESS_KEY','AWS_SESSION_TOKEN'):
    environment.pop(name, None)
environment.update(ENVIRONMENT='demo', OPSCONTROL_RELEASE_ACCEPTANCE='1', RELEASE_PRIVATE_DIR=str(private),
    AWS_EC2_METADATA_DISABLED='true', POSTGRES_USER='opscontrol', POSTGRES_DB='opscontrol',
    POSTGRES_PASSWORD=secrets.token_urlsafe(32), RELEASE_APP_PASSWORD=secrets.token_urlsafe(32),
    RELEASE_MAINTENANCE_PASSWORD=secrets.token_urlsafe(32))

def run(args, *, env=None, input=None, expected=0):
    result = subprocess.run(args, cwd=ROOT, env=env or environment, input=input, capture_output=True, text=True, timeout=240)
    if result.returncode != expected:
        (private/'failed-command.log').write_text(result.stdout+'\n'+result.stderr)
        raise RuntimeError('Acceptance command failed; see private diagnostics')
    return result.stdout.strip()

def module(name, *args, env=None):
    result = subprocess.run([PYTHON, '-m', name, *args], cwd=ROOT/'backend', env=env or environment,
        capture_output=True, text=True, timeout=240)
    with (private/'probes.log').open('a') as log:
        log.write(result.stdout+'\n'+result.stderr)
    if result.returncode:
        raise RuntimeError('Acceptance probe failed; see private diagnostics')
    return result.stdout.strip()

def start_api(env, host, port, proxy='127.0.0.1'):
    log = (private/f'api-{len(processes)}.log').open('w')
    process = subprocess.Popen([PYTHON, '-m', 'uvicorn', 'app.main:app', '--host', host, '--port', str(port),
        '--forwarded-allow-ips', proxy, '--no-access-log'], cwd=ROOT/'backend', env=env, stdout=log, stderr=subprocess.STDOUT)
    processes.append(process); return process

def free_port():
    with socket.socket() as sock:
        sock.bind(('0.0.0.0', 0)); return sock.getsockname()[1]

def wait_url(url):
    for _ in range(100):
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200: return
        except Exception: time.sleep(.1)
    raise RuntimeError('Acceptance readiness failed')

def record(message):
    checks.append(message); print('PASS:', message, flush=True)

try:
    run(['docker','run','-d','--name',database,'-p','127.0.0.1::5432',
        '-e','POSTGRES_USER','-e','POSTGRES_PASSWORD','-e','POSTGRES_DB',
        '-v',str(private)+':/fixture:ro','postgres:17-alpine']); containers.append(database)
    for _ in range(100):
        if subprocess.run(['docker','exec',database,'pg_isready','-U','opscontrol'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0: break
        time.sleep(.1)
    else: raise RuntimeError('PostgreSQL readiness failed')
    port = int(run(['docker','inspect','--format','{{(index (index .NetworkSettings.Ports "5432/tcp") 0).HostPort}}',database]))
    owner = f"postgresql+psycopg://opscontrol:{environment['POSTGRES_PASSWORD']}@127.0.0.1:{port}/opscontrol"
    environment.update(DATABASE_URL=owner,
        MAINTENANCE_DATABASE_URL=f"postgresql+psycopg://release_maintenance:{environment['RELEASE_MAINTENANCE_PASSWORD']}@127.0.0.1:{port}/opscontrol")
    module('alembic','upgrade','head')
    api_port = free_port(); base = f'http://127.0.0.1:{api_port}'
    ui_port = free_port()
    environment['CORS_ORIGINS'] = f'http://127.0.0.1:{ui_port}'
    environment['TEST_API_BASE'] = base
    development = start_api(environment, '127.0.0.1', api_port); wait_url(base+'/health')
    module('scripts.auth_tenant_probe')
    for probe, variable in (('security_release_probe','URL'), ('deep_tenant_security_probe','BASE'), ('remote_protocol_probe','BASE')):
        code = f'from scripts import {probe} as p;p.{variable}={base!r};p.main()'
        result = subprocess.run([PYTHON,'-c',code], cwd=ROOT/'backend', env=environment, capture_output=True, text=True, timeout=180)
        (private/(probe+'.log')).write_text(result.stdout+'\n'+result.stderr)
        if result.returncode: raise RuntimeError(probe+' failed')
    record('RBAC, two-tenant isolation, secrets, audit tamper and remote worker/lease/replay negatives')
    module('scripts.remote_telemetry_acceptance_probe')
    record('Actual Basic-auth HTTPS, server worker heartbeat and five native failure/recovery observations')
    module('scripts.servicenow_acceptance_probe')
    record('Native alert/correlation and real controlled ServiceNow TLS open/retry/resolve with leased delivery fencing')
    module('scripts.release_runtime_probe','seed')
    if environment.get('RELEASE_BROWSER_ACCEPTANCE') == '1':
        ui_environment = {**environment, 'VITE_API_BASE_URL':base, 'RELEASE_UI_BASE':f'http://127.0.0.1:{ui_port}', 'RELEASE_EVIDENCE_DIR':str(OUT)}
        ui_log = (private/'ui.log').open('w')
        ui = subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',str(ui_port),'--strictPort'],cwd=ROOT/'frontend',env=ui_environment,stdout=ui_log,stderr=subprocess.STDOUT)
        processes.append(ui); wait_url(ui_environment['RELEASE_UI_BASE'])
        run(['node','frontend/scripts/release_pagination_acceptance.mjs'],env=ui_environment)
        run(['node','frontend/scripts/resource_crud_acceptance.mjs'],env=ui_environment)
        ui.terminate(); ui.wait(timeout=10)
        record('Actual authenticated Playwright pagination across 205-resource inventory in both themes')
        record('Browser resource CRUD, inactive OTEL registration edit persistence and cross-tenant denial')
    # Capability roles are reapplied after migrations. Runtime credentials are
    # composed by psycopg and never interpolated into shell commands.
    role_code = """
from pathlib import Path
import os
from psycopg import sql
from app.db.session import engine
raw = engine.raw_connection()
try:
    connection = raw.driver_connection
    connection.execute(Path('../deploy/examples/restricted-database-roles.sql').read_text())
    for name, capability, key in [('release_app','opscontrol_app','RELEASE_APP_PASSWORD'),('release_maintenance','opscontrol_maintenance','RELEASE_MAINTENANCE_PASSWORD')]:
        connection.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {} IN ROLE {}').format(sql.Identifier(name),sql.Literal(os.environ[key]),sql.Identifier(capability)))
    connection.commit()
finally:
    raw.close()
"""
    result = subprocess.run([PYTHON,'-c',role_code],cwd=ROOT/'backend',env=environment,capture_output=True,text=True,timeout=30)
    if result.returncode:
        (private/'roles.log').write_text(result.stderr); raise RuntimeError('Restricted-role provisioning failed')
    module('scripts.release_runtime_probe','exercise')
    record('Atomic audit rollback/commit; bounded collector concurrency; retention rollback, pinning and audit preservation')
    development.terminate(); development.wait(timeout=10)
    # Concurrent-index migration rollback/upgrade on populated data.
    module('scripts.release_runtime_probe','snapshot')
    module('scripts.release_runtime_probe','indexes-roundtrip')
    module('scripts.release_runtime_probe','verify')
    service = f"[source]\nhost=127.0.0.1\nport=5432\ndbname=opscontrol\nuser=opscontrol\npassword={environment['POSTGRES_PASSWORD']}\n[restored]\nhost=127.0.0.1\nport=5432\ndbname=restored\nuser=opscontrol\npassword={environment['POSTGRES_PASSWORD']}\n"
    (private/'pg_service.conf').write_text(service); (private/'pg_service.conf').chmod(0o600)
    backup_environment = {**environment, 'PGSERVICE':'source', 'PGSERVICEFILE':'/fixture/pg_service.conf'}
    archive = private/'backup'/'populated.dump'
    module('scripts.database_backup','backup',str(archive),'--container',database,env=backup_environment)
    run(['docker','exec',database,'createdb','-U','opscontrol','restored'])
    restored_environment = {**environment,'DATABASE_URL':owner.rsplit('/', 1)[0]+'/restored'}
    restore_environment = {**backup_environment, 'PGSERVICE':'restored'}
    began = time.monotonic()
    module('scripts.database_backup','restore',str(archive),'--container',database,env=restore_environment)
    restore_seconds = round(time.monotonic()-began,3)
    module('scripts.release_runtime_probe','verify',env=restored_environment)
    module('alembic','upgrade','head',env=restored_environment)
    module('scripts.release_runtime_probe','verify',env=restored_environment)
    record('Populated custom-format dump/restore: every row hash, FK/check constraint, migration head and audit trigger preserved')
    # No-overwrite and nonempty restore target must fail without changing data.
    for action in ('backup','restore'):
        result = subprocess.run([PYTHON,'-m','scripts.database_backup',action,str(archive),'--container',database],cwd=ROOT/'backend',env=restore_environment,capture_output=True,text=True,timeout=30)
        assert result.returncode != 0
    original_manifest = archive.with_suffix('.dump.json').read_text()
    manifest = json.loads(original_manifest); manifest['sha256'] = '0'*64
    archive.with_suffix('.dump.json').write_text(json.dumps(manifest))
    result = subprocess.run([PYTHON,'-m','scripts.database_backup','restore',str(archive),'--container',database],cwd=ROOT/'backend',env=restore_environment,capture_output=True,text=True,timeout=30)
    assert result.returncode != 0 and 'checksum' in result.stderr
    archive.with_suffix('.dump.json').write_text(original_manifest)
    record('Backup overwrite, corrupted checksum and nonempty restore target refused')
    # Actual TLS ingress with exact proxy-peer trust and non-owner API identity.
    host = socket.gethostbyname(socket.gethostname()); production_port = free_port(); tls_port = free_port()
    run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(private/'tls.key'),'-out',str(private/'tls.crt'),'-days','1','-subj','/CN=opscontrol.example.test','-addext','subjectAltName=DNS:opscontrol.example.test,IP:127.0.0.1'])
    run(['npm','run','build','--prefix','frontend'],env={**environment,'VITE_API_BASE_URL':f'https://127.0.0.1:{tls_port}'})
    # Public static assets must be readable by the unprivileged Nginx worker;
    # keep backups, fixture credentials and TLS keys under the private umask.
    assets = private/'public-spa'
    shutil.copytree(ROOT/'frontend/dist', assets)
    assets.chmod(0o755)
    for item in assets.rglob('*'):
        item.chmod(0o755 if item.is_dir() else 0o644)
    run(['node','frontend/scripts/render-production-nginx.mjs','frontend/dist/index.html',str(private/'nginx.conf'),f'http://{host}:{production_port}'])
    run(['docker','create','--name',ingress,'-p',f'127.0.0.1:{tls_port}:443',
        '-v',str(private/'tls.crt')+':/run/secrets/tls.crt:ro','-v',str(private/'tls.key')+':/run/secrets/tls.key:ro',
        '-v',str(private/'nginx.conf')+':/etc/nginx/conf.d/default.conf:ro',
        '-v',str(assets)+':/usr/share/nginx/html:ro','nginx:1.28-alpine']); containers.append(ingress)
    run(['docker','start',ingress])
    peer = run(['docker','inspect','--format','{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}',ingress])
    production_environment = {**environment,'ENVIRONMENT':'production','CORS_ORIGINS':f'https://127.0.0.1:{tls_port}',
        'DATABASE_URL':owner.replace('opscontrol:'+environment['POSTGRES_PASSWORD'],'release_app:'+environment['RELEASE_APP_PASSWORD']), 'TRUSTED_PROXY_IPS':peer}
    production = start_api(production_environment, host, production_port, peer)
    context = ssl.create_default_context(cafile=str(private/'tls.crt'))
    for _ in range(100):
        try:
            with urllib.request.urlopen(f'https://127.0.0.1:{tls_port}/health',context=context,timeout=1) as response:
                if response.status == 200: break
        except Exception: time.sleep(.1)
    else: raise RuntimeError('Production TLS ingress readiness failed')
    with urllib.request.urlopen(f'https://127.0.0.1:{tls_port}/',context=context,timeout=5) as response:
        headers = response.headers
        assert 'frame-ancestors' in headers['Content-Security-Policy']
        assert "script-src 'self'" in headers['Content-Security-Policy'] and "script-src 'self' 'unsafe-inline'" not in headers['Content-Security-Policy']
        assert headers['Strict-Transport-Security'].startswith('max-age=31536000')
        assert headers['X-Content-Type-Options']=='nosniff' and headers['X-Frame-Options']=='DENY'
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    forged = urllib.request.Request(f'http://{host}:{production_port}/health',headers={'X-Forwarded-Proto':'https','X-Forwarded-For':'127.0.0.1'})
    try: opener.open(forged,timeout=5)
    except urllib.error.HTTPError as response: assert response.code==403
    else: raise AssertionError('Untrusted peer spoofed proxy TLS scheme')
    record('Certificate-verified TLS ingress, static SPA CSP/HSTS/security headers and rejected untrusted proxy spoof')
    # Reuse the production Settings and runtime identity, not mocked headers.
    role_check = """
from app.db.session import engine
from sqlalchemy import text
with engine.begin() as c:
    for statement in ('UPDATE security_audit_events SET outcome=outcome', 'ALTER TABLE data_sources ADD COLUMN forbidden_runtime_ddl int'):
        try:
            with c.begin_nested(): c.execute(text(statement))
        except Exception: pass
        else: raise AssertionError('Privileged runtime operation unexpectedly allowed')
"""
    result = subprocess.run([PYTHON,'-c',role_check],cwd=ROOT/'backend',env=production_environment,capture_output=True,text=True,timeout=30)
    assert result.returncode == 0
    owner_check = """
from app.security.deployment import validate_runtime_database_role
try: validate_runtime_database_role()
except RuntimeError: pass
else: raise AssertionError('Production owner identity accepted')
"""
    result = subprocess.run([PYTHON,'-c',owner_check],cwd=ROOT/'backend',env={**production_environment,'DATABASE_URL':owner},capture_output=True,text=True,timeout=30)
    assert result.returncode == 0
    payload = json.dumps({'username':'test-admin','password':'testing-only-StrongPassword-123!'}).encode()
    with urllib.request.urlopen(urllib.request.Request(f'https://127.0.0.1:{tls_port}/api/v1/auth/login',data=payload,headers={'Content-Type':'application/json'}),context=context,timeout=10) as response:
        token=json.load(response)['access_token']
    with urllib.request.urlopen(urllib.request.Request(f'https://127.0.0.1:{tls_port}/api/v1/auth/me',headers={'Authorization':'Bearer '+token}),context=context,timeout=10) as response:
        assert json.load(response)['platform_admin'] is True
    transport_code = f"from app.worker.collector_runtime import ApiAdapter;r=ApiAdapter._request('https://127.0.0.1:{tls_port}/','GET','synthetic-reader','synthetic-only',5,{{200}},True,False,0,{{}},None);assert r.success,r.message"
    result = subprocess.run([PYTHON,'-c',transport_code],cwd=ROOT/'backend',env={**environment,'SSL_CERT_FILE':str(private/'tls.crt')},capture_output=True,text=True,timeout=15)
    assert result.returncode == 0
    record('Production non-owner API authentication; runtime DDL/audit mutation and owner startup refused; actual trusted legacy TLS transport')
    fp = json.loads((private/'fingerprint.json').read_text())
    OUT.mkdir(parents=True,exist_ok=True)
    report={'status':'PASS','created_at':datetime.now(timezone.utc).isoformat(),'checks':checks,
        'database':{'tables':len(fp['tables']),'rows':sum(v['rows'] for v in fp['tables'].values()),'constraints':len(fp['constraints']),
                    'restore_seconds':restore_seconds,'dump_sha256':json.loads(original_manifest)['sha256']},
        'limitations':['Controlled small dataset, not a production RTO/RPO or load SLO','Independent human security review and operator UAT pending','Live AWS, Windows and genuine Carte acceptance deferred','Audit/incident/ETL history retained indefinitely; approved deletion/archive policy pending']}
    (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    passed=True; print('RELEASE RESTORE / RETENTION / TLS ACCEPTANCE PASS',flush=True)
finally:
    for process in reversed(processes):
        if process.poll() is None:
            process.terminate()
            try: process.wait(timeout=10)
            except subprocess.TimeoutExpired: process.kill(); process.wait()
    for container in reversed(containers):
        subprocess.run(['docker','rm','-f',container],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    if passed:
        shutil.rmtree(private)
    else:
        print('Private acceptance diagnostics retained at',private,file=sys.stderr)
