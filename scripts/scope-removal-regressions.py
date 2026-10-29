#!/usr/bin/env python3
"""Owned PostgreSQL regression + non-destructive preservation; scoped cleanup."""
import json,os,subprocess,sys,time
from pathlib import Path
root=Path(__file__).resolve().parents[1]
out=Path(os.environ['SCOPE_EVIDENCE_DIR']);out.mkdir(parents=True,exist_ok=True)
docker=['docker','--host=unix:///var/run/docker.sock']
env={k:v for k,v in os.environ.items() if k not in ('DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH')}
name='oc-scope-rem-001-pg';network='oc-scope-rem-001-close';started=False;net=False;results=[]
python=str(root/'backend/.venv/bin/python')
def run(args,label,cwd=root):
 r=subprocess.run(args,cwd=cwd,env=env,capture_output=True,text=True)
 (out/(label+'.log')).write_text((r.stdout+'\n'+r.stderr).replace('scope-removal-synthetic','[REDACTED]'))
 results.append({'command':args,'exit_code':r.returncode,'log':label+'.log'})
 if r.returncode:raise RuntimeError(label+' failed')
 return r.stdout
try:
 if subprocess.run([*docker,'inspect',name],capture_output=True).returncode==0:raise RuntimeError('Owned fixture name already exists; refusing overwrite')
 run([*docker,'network','create','--internal','--label','task=OC-SCOPE-REM-001',network],'network');net=True
 env['POSTGRES_PASSWORD']='scope-removal-synthetic'
 run([*docker,'run','-d','--name',name,'--label','task=OC-SCOPE-REM-001','--network',network,'--tmpfs','/var/lib/postgresql/data','-e','POSTGRES_PASSWORD','-e','POSTGRES_DB=scope_removal','postgres:17-alpine'],'container');started=True
 for _ in range(100):
  if subprocess.run([*docker,'exec',name,'pg_isready','-U','postgres'],capture_output=True).returncode==0:break
  time.sleep(.1)
 else:raise RuntimeError('PostgreSQL readiness failed')
 info=json.loads(run([*docker,'inspect',name],'container-identity'))[0]
 # Do not publish inspect output: it contains the disposable environment secret.
 (out/'container-identity.log').unlink()
 ip=info['NetworkSettings']['Networks'][network]['IPAddress']
 env.update(DATABASE_URL=f'postgresql+psycopg://postgres:scope-removal-synthetic@{ip}:5432/scope_removal',OPSCONTROL_V16_ACCEPTANCE='1',OPSCONTROL_SCOPE_REMOVAL_FIXTURE='1')
 run([python,'-m','alembic','upgrade','head'],'fresh-migration',root/'backend')
 run([python,'-m','unittest','discover','-s','tests','-v'],'backend-full',root/'backend')
 report=run([python,'-m','scripts.scope_removal_preservation_probe'],'preservation',root/'backend')
 (out/'preservation.json').write_text(report)
 run([python,'-m','scripts.provider_unit_probe'],'provider-unit',root/'backend')
 run([python,'-m','scripts.infrastructure_unit_probe'],'infrastructure-unit',root/'backend')
 run([python,'-m','compileall','-q','app','scripts','tests'],'python-compile',root/'backend')
finally:
 if started:subprocess.run([*docker,'rm','-f',name],capture_output=True,check=True)
 if net:subprocess.run([*docker,'network','rm',network],capture_output=True,check=True)
 results=[r for r in results if r['log']!='container-identity.log']
 (out/'results.json').write_text(json.dumps({'source_sha':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
  'commands':results,'container':name,'network':network,'remaining_container':subprocess.run([*docker,'inspect',name],capture_output=True).returncode==0,
  'image':locals().get('info',{}).get('Image'),'cleanup':'owned container and network only; tmpfs; no named volume'},indent=2)+'\n')
