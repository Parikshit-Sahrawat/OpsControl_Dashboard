#!/usr/bin/env python3
"""Disposable Sprint 3 controlled HTTPS Carte lifecycle and real browser gate."""
import json, os, secrets, shutil, socket, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PYTHON=str(ROOT/'backend/.venv/bin/python')
OUT=Path(os.getenv('ETL_EVIDENCE_DIR',str(ROOT/'docs/screenshots/etl')))
private=Path(tempfile.mkdtemp(prefix='opscontrol-etl-'));private.chmod(0o700)
container='opscontrol-etl-'+secrets.token_hex(4);fixture=container+'-carte';processes=[];passed=False
host=socket.gethostbyname(socket.gethostname())
env=os.environ.copy()
for key in ('AWS_PROFILE','AWS_DEFAULT_PROFILE','AWS_ACCESS_KEY_ID','AWS_SECRET_ACCESS_KEY','AWS_SESSION_TOKEN'):env.pop(key,None)
env.update(DATABASE_URL='postgresql+psycopg://opscontrol:etl-local-only@127.0.0.1:11432/opscontrol',ENVIRONMENT='demo',SEED_DEMO='false',OPSCONTROL_ETL_ACCEPTANCE='1',ETL_PRIVATE_DIR=str(private),ETL_FIXTURE_IP=host,
    OPSCONTROL_LOCAL_ALLOWED_HOSTS=host,OPSCONTROL_LOCAL_ALLOWED_CIDRS=host+'/32',SSL_CERT_FILE=str(private/'tls.crt'),
    OPSCONTROL_CREDENTIAL_ETL_FIXTURE_USERNAME='fixture-reader',OPSCONTROL_DEMO_PASSWORD_FILE=str(private/'admin-password'),CORS_ORIGINS='http://127.0.0.1:15174',AWS_EC2_METADATA_DISABLED='true',VITE_API_BASE_URL='http://127.0.0.1:18800')

def run(args,cwd=ROOT):subprocess.run(args,cwd=cwd,env=env,check=True,timeout=180)
def start(args,cwd=ROOT,label='service'):
    log=open(private/(label+'.log'),'w');process=subprocess.Popen(args,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT);processes.append(process);return process
def wait_url(url):
    for _ in range(100):
        try:
            with urllib.request.urlopen(url,timeout=1) as response:
                if response.status==200:return
        except Exception:time.sleep(.3)
    raise RuntimeError('Acceptance service readiness timed out')
def probe(command):run([PYTHON,'-m','scripts.etl_acceptance_probe',command],ROOT/'backend')
def browser(phase):
    env.update(ETL_SESSION_FILE=str(private/'session.json'),ETL_EVIDENCE_DIR=str(OUT));run(['node','frontend/scripts/etl_acceptance.mjs',phase])
def target():return start([PYTHON,'-c','import time;time.sleep(3600)'],label='linux-target')

try:
    import ipaddress
    if ipaddress.ip_address(host).is_loopback:raise RuntimeError('Controlled fixture needs an actual private interface address')
    for name in ('admin-password','carte-password'):
        (private/name).write_text(secrets.token_urlsafe(36));(private/name).chmod(0o600)
    env['OPSCONTROL_CREDENTIAL_ETL_FIXTURE_PASSWORD']=(private/'carte-password').read_text().strip()
    (private/'phase').write_text('no-run')
    run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(private/'tls.key'),'-out',str(private/'tls.crt'),'-days','1','-subj','/CN='+host,'-addext','subjectAltName=IP:'+host])
    run(['docker','run','-d','--name',container,'-p','127.0.0.1:11432:5432','-e','POSTGRES_USER=opscontrol','-e','POSTGRES_PASSWORD=etl-local-only','-e','POSTGRES_DB=opscontrol','postgres:17-alpine'])
    for _ in range(100):
        if subprocess.run(['docker','exec',container,'pg_isready','-U','opscontrol'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:break
        time.sleep(.3)
    else:raise RuntimeError('Disposable PostgreSQL not ready')
    run([PYTHON,'-m','alembic','upgrade','head'],ROOT/'backend')
    run([PYTHON,'-m','alembic','downgrade','0019_infrastructure_evidence'],ROOT/'backend')
    run([PYTHON,'-m','alembic','upgrade','head'],ROOT/'backend')
    linux=target();env['LINUX_TARGET_PID']=str(linux.pid)
    run(['docker','run','-d','--name',fixture,'-p',host+':443:443','-e','ETL_FIXTURE_BIND=0.0.0.0',
        '-v',str(private)+':/fixture','-v',str(ROOT/'deploy/fixtures/pentaho_carte_api.py')+':/app.py:ro',
        'python:3.12-alpine','python','/app.py','/fixture',host])
    start([PYTHON,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port','18800','--no-access-log'],ROOT/'backend','api')
    start(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','15174','--strictPort'],ROOT/'frontend','ui')
    wait_url('http://127.0.0.1:18800/health');wait_url('http://127.0.0.1:15174')
    env['TEST_API_BASE']='http://127.0.0.1:18800'
    run([PYTHON,'-m','scripts.auth_tenant_probe'],ROOT/'backend')
    run([PYTHON,'-c',"from scripts import security_release_probe as p;p.URL='http://127.0.0.1:18800';p.main()"],ROOT/'backend')
    run([PYTHON,'-m','scripts.bootstrap_public_demo'],ROOT/'backend')
    probe('setup');browser('configured')
    for phase in ('no-run','running','long-running','sla-breach','failed','poll-failed','recovered'):
        if phase=='failed':linux.terminate();linux.wait(timeout=5)
        if phase=='recovered':linux=target();env['LINUX_TARGET_PID']=str(linux.pid)
        probe('collect-'+phase);probe(phase);browser(phase)
    probe('isolation')
    OUT.mkdir(parents=True,exist_ok=True);shutil.copyfile(private/'report.json',OUT/'report.json')
    passed=True;print('SPRINT 3 CONTROLLED CARTE / LIVE HOST / BROWSER ACCEPTANCE PASS; genuine Carte acceptance remains pending')
except Exception:
    print('Acceptance failed; private service logs retained at',private,file=sys.stderr);raise
finally:
    for process in reversed(processes):
        if process.poll() is None:
            process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait()
    subprocess.run(['docker','rm','-f','-v',fixture,container],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    if passed:shutil.rmtree(private)
