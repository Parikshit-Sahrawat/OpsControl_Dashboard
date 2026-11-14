import os, subprocess, tempfile, time, socket, json, secrets, sys
from pathlib import Path
import psycopg, pgserver
root=Path.cwd(); python=str(root/'backend/.venv/bin/python'); pg=Path(pgserver.__file__).parent/'pginstall/bin'
private=Path(tempfile.mkdtemp(prefix='aptron-foundation-lab-')); private.chmod(0o700)
out=root/'docs/verification/aptron-foundation';out.mkdir(exist_ok=True,parents=True)
def run(name,args,cwd=None,extra=None):
 t=time.monotonic();p=subprocess.run(args,cwd=cwd or root,env={**env,**(extra or {})},text=True,capture_output=True,timeout=180)
 (out/(name+'.log')).write_text(p.stdout+'\n'+p.stderr)
 print(name,p.returncode,round(time.monotonic()-t,2),flush=True)
 if p.returncode:failures.append(name)
 return p.returncode
subprocess.run([str(pg/'initdb'),'-D',str(private/'pgdata'),'-U','postgres','--auth=trust'],capture_output=True,check=True)
s=socket.socket();s.bind(('127.0.0.1',0));port=s.getsockname()[1];s.close()
log=(private/'pg.log').open('w');server=subprocess.Popen([str(pg/'postgres'),'-D',str(private/'pgdata'),'-h','127.0.0.1','-p',str(port),'-k',''],stdout=log,stderr=log)
env={**os.environ,'ENVIRONMENT':'test','ENV':'test','AWS_EC2_METADATA_DISABLED':'true','DATABASE_URL':f'postgresql+psycopg://postgres@127.0.0.1:{port}/postgres'}
api=None
failures=[]
try:
 for _ in range(100):
  try:
   with psycopg.connect(f'postgresql://postgres@127.0.0.1:{port}/postgres') as conn: break
  except psycopg.OperationalError:time.sleep(.1)
 else:raise RuntimeError('PG not ready')
 if run('pg-migration',[python,'-m','alembic','upgrade','head'],root/'backend'):raise RuntimeError('Migration failed')
 run('pg-schema-check',[python,'-m','alembic','check'],root/'backend')
 run('pg-tenant-rbac-history',[python,'-m','unittest','tests.test_pipeline_ownership_v16','tests.test_sprint08_rbac','tests.test_pentaho_incident_r1','-v'],root/'backend',{'OPSCONTROL_V16_ACCEPTANCE':'1'})
 (private/'api-fixture.json').write_text(json.dumps({'password':secrets.token_urlsafe(30),'viewer_password':secrets.token_urlsafe(30)}));(private/'api-fixture.json').chmod(0o600)
 env.update({'OPSCONTROL_V16_ACCEPTANCE':'1','V16_PRIVATE_DIR':str(private),'V16_EVIDENCE_DIR':str(out),'V16_API_URL':'http://127.0.0.1:58137'})
 apilog=(private/'api.log').open('w');api=subprocess.Popen([python,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port','58137','--no-access-log'],cwd=root/'backend',env=env,stdout=apilog,stderr=apilog)
 from urllib.request import urlopen
 for _ in range(100):
  try:
   if urlopen(env['V16_API_URL']+'/health',timeout=1).status==200:break
  except OSError:time.sleep(.1)
 else:raise RuntimeError('API not ready')
 run('pg-http-workflow',[python,'-m','scripts.v16_api_probe'],root/'backend')
 run('pg-http-rbac',[python,'-m','scripts.sprint08_http_probe'],root/'backend')
except Exception as e:
 failures.append(type(e).__name__);print(type(e).__name__,str(e),flush=True)
finally:
 if api:api.terminate();api.wait(timeout=15)
 server.terminate();server.wait(timeout=15)
 print('Owned API and PostgreSQL stopped; no external target',flush=True)

sys.exit(bool(failures))
