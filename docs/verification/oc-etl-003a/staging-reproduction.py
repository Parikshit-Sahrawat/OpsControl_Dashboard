from pathlib import Path
import os,subprocess,json,secrets,time
r=Path('/workspace/OpsControl_Dashboard');out=Path('/tmp/oc-etl003a-staging');out.mkdir(exist_ok=True)
name='oc-etl003a-stage-'+secrets.token_hex(4);docker=['docker','--host=unix:///var/run/docker.sock'];env=os.environ.copy();env.update(ENVIRONMENT='test',SEED_DEMO_DATA='false',PYTHONPATH='.');commands=[]
def run(args,cwd,label):
 p=subprocess.run(args,cwd=cwd,env=env,capture_output=True,text=True,timeout=180);(out/(label+'.log')).write_text(p.stdout+'\n'+p.stderr);commands.append({'args':args,'exit_code':p.returncode});assert p.returncode==0,label;return p.stdout
try:
 run(docker+['run','-d','--name',name,'--tmpfs','/var/lib/postgresql/data','-p','127.0.0.1::5432','-e','POSTGRES_USER=opscontrol','-e','POSTGRES_PASSWORD=synthetic-local','-e','POSTGRES_DB=opscontrol','postgres:17-alpine'],r,'start')
 for _ in range(100):
  if subprocess.run(docker+['exec',name,'pg_isready','-h','127.0.0.1','-U','opscontrol'],capture_output=True).returncode==0:break
  time.sleep(.2)
 port=subprocess.check_output(docker+['port',name,'5432/tcp'],text=True).strip().rsplit(':',1)[1]
 env['DATABASE_URL']=f'postgresql+psycopg://opscontrol:synthetic-local@127.0.0.1:{port}/opscontrol'
 py=str(r/'backend/.venv/bin/python')
 run(docker+['exec',name,'psql','-U','opscontrol','-Atc','SELECT version()'],r,'postgres-version')
 for i,(action,target) in enumerate([('upgrade','0024_notification_leases'),('downgrade','0023_worker_heartbeat'),('upgrade','0024_notification_leases')]):run([py,'-m','alembic',action,target],r/'backend',str(i)+'-'+action)
 run([py,'scripts/existing_database_upgrade_probe.py'],r/'backend','populated-upgrade')
 run([py,'-m','alembic','check'],r/'backend','model-check')
 (out/'result.json').write_text(json.dumps({'status':'PASS','commands':commands,'scope':'staging migration and populated upgrade steps; HTTP/browser covered by hosted staging job separately'},indent=2))
finally:
 cleanup=subprocess.run(docker+['rm','-f','-v',name],capture_output=True,text=True)
 (out/'cleanup.json').write_text(json.dumps({'name':name,'exit_code':cleanup.returncode,'remaining':subprocess.run(docker+['inspect',name],capture_output=True).returncode==0}))
