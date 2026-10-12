#!/usr/bin/env python3
"""Disposable controlled Sprint 2 gate. Never uses cloud credentials or production DB."""
import json,os,secrets,shutil,subprocess,sys,tempfile,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PYTHON=str(ROOT/'backend/.venv/bin/python')
OUT=Path(os.getenv('INFRA_EVIDENCE_DIR',str(ROOT/'docs/screenshots/infrastructure')))
processes=[]
passed=False
container='opscontrol-infra-'+secrets.token_hex(4)
private=Path(tempfile.mkdtemp(prefix='opscontrol-infra-'));private.chmod(0o700)
env=os.environ.copy()
for key in ('AWS_PROFILE','AWS_DEFAULT_PROFILE','AWS_ACCESS_KEY_ID','AWS_SECRET_ACCESS_KEY','AWS_SESSION_TOKEN'):env.pop(key,None)
env.update(DATABASE_URL='postgresql+psycopg://opscontrol:infra-local-only@127.0.0.1:15432/opscontrol',ENVIRONMENT='demo',SEED_DEMO='false',OPSCONTROL_INFRA_ACCEPTANCE='1',INFRA_PRIVATE_DIR=str(private),OPSCONTROL_K8S_ALLOWED_NODES='fixture-node',OPSCONTROL_DEMO_PASSWORD_FILE=str(private/'admin-password'),CORS_ORIGINS='http://127.0.0.1:15173',AWS_EC2_METADATA_DISABLED='true',VITE_API_BASE_URL='http://127.0.0.1:18000')
def run(args,cwd=ROOT):subprocess.run(args,cwd=cwd,env=env,check=True,timeout=180)
def start(args,cwd=ROOT,label='service'):
    log=open(private/(label+'.log'),'w');p=subprocess.Popen(args,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT);processes.append(p);return p

def wait_url(url):
    for _ in range(100):
        try:
            with urllib.request.urlopen(url,timeout=1) as response:
                if response.status==200:return
        except Exception:time.sleep(.3)
    raise RuntimeError('Acceptance service readiness timed out')
def probe(command):run([PYTHON,'-m','scripts.infrastructure_acceptance_probe',command],ROOT/'backend')
def browser(phase):
    env.update(INFRA_SESSION_FILE=str(private/'session.json'),INFRA_EVIDENCE_DIR=str(OUT))
    run(['node','frontend/scripts/infrastructure_acceptance.mjs',phase])
def target():return start([PYTHON,'-c','import time; time.sleep(3600)'],label='linux-target')
try:
    for name in ('admin-password','kube-token'):
        (private/name).write_text(secrets.token_urlsafe(36));(private/name).chmod(0o600)
    (private/'phase').write_text('healthy')
    run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(private/'tls.key'),'-out',str(private/'tls.crt'),'-days','1','-subj','/CN=127.0.0.1','-addext','subjectAltName=IP:127.0.0.1'])
    run(['docker','run','-d','--name',container,'-p','127.0.0.1:15432:5432','-e','POSTGRES_USER=opscontrol','-e','POSTGRES_PASSWORD=infra-local-only','-e','POSTGRES_DB=opscontrol','postgres:17-alpine'])
    for _ in range(100):
        ready=subprocess.run(['docker','exec',container,'pg_isready','-U','opscontrol'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        if ready.returncode==0:break
        time.sleep(.3)
    else:raise RuntimeError('Disposable database readiness timed out')
    run([PYTHON,'-m','alembic','upgrade','0024_notification_leases'],ROOT/'backend')
    run([PYTHON,'-m','alembic','downgrade','-1'],ROOT/'backend')
    run([PYTHON,'-m','alembic','upgrade','head'],ROOT/'backend')
    linux=target();env['LINUX_TARGET_PID']=str(linux.pid)
    start([PYTHON,'deploy/fixtures/infrastructure_kubernetes_api.py',str(private)],label='kubernetes-tls')
    start([PYTHON,'-m','scripts.run_infrastructure_acceptance_api'],ROOT/'backend','api')
    start(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','15173','--strictPort'],ROOT/'frontend','ui')
    wait_url('http://127.0.0.1:18000/health');wait_url('http://127.0.0.1:15173')
    env['TEST_API_BASE']='http://127.0.0.1:18000'
    run([PYTHON,'-m','scripts.auth_tenant_probe'],ROOT/'backend')
    run([PYTHON,'-c',"from scripts import security_release_probe as p; p.URL='http://127.0.0.1:18000'; p.main()"],ROOT/'backend')
    run([PYTHON,'-m','scripts.bootstrap_public_demo'],ROOT/'backend')
    probe('setup');browser('configured')
    for phase in ('healthy','failed','recovered'):
        if phase=='failed':linux.terminate();linux.wait(timeout=5)
        if phase=='recovered':linux=target();env['LINUX_TARGET_PID']=str(linux.pid)
        probe('collect-'+phase);probe(phase);browser(phase)
    probe('isolation')
    OUT.mkdir(parents=True,exist_ok=True);shutil.copyfile(private/'report.json',OUT/'report.json')
    passed=True
    print('SPRINT 2 CONTROLLED ACCEPTANCE PASS; genuine AWS/Kubernetes/Windows remain separately pending')
except Exception:
    print('Acceptance failed; private service logs retained at',private,file=sys.stderr)
    raise
finally:
    for p in reversed(processes):
        if p.poll() is None:
            p.terminate()
            try:p.wait(timeout=5)
            except subprocess.TimeoutExpired:p.kill();p.wait()
    subprocess.run(['docker','rm','-f','-v',container],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    if passed:shutil.rmtree(private)
