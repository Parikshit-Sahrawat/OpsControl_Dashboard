from pathlib import Path
import os,subprocess,json,secrets,time,socket,yaml,signal
r=Path('/workspace/OpsControl_Dashboard');out=Path('/tmp/oc-etl003a-staging-full');out.mkdir(exist_ok=True)
workflow=yaml.safe_load((r/'.github/workflows/phase1-staging.yml').read_text());job=workflow['jobs']['staging-smoke'];name='oc-etl003a-stagefull-'+secrets.token_hex(4);docker=['docker','--host=unix:///var/run/docker.sock'];env=os.environ.copy();env.update({k:str(v) for k,v in job['env'].items()});env['PATH']=str(r/'backend/.venv/bin')+':'+env['PATH'];commands=[];sessions=[]
for key in ('AWS_ACCESS_KEY_ID','AWS_SECRET_ACCESS_KEY','AWS_SESSION_TOKEN'):env.pop(key,None)
for port in (8000,5173):
 with socket.socket() as sock:sock.bind(('127.0.0.1',port))
def run(args,cwd,label):
 p=subprocess.run(args,cwd=cwd,env=env,capture_output=True,text=True,timeout=180);(out/(label+'.log')).write_text(p.stdout+'\n'+p.stderr);commands.append({'label':label,'exit_code':p.returncode});assert p.returncode==0,label;return p.stdout
try:
 run(docker+['run','-d','--name',name,'--tmpfs','/var/lib/postgresql/data','-p','127.0.0.1::5432','-e','POSTGRES_USER=opscontrol','-e','POSTGRES_PASSWORD=synthetic-local','-e','POSTGRES_DB=opscontrol','postgres:17-alpine'],r,'start')
 for _ in range(100):
  if subprocess.run(docker+['exec',name,'pg_isready','-h','127.0.0.1','-U','opscontrol'],capture_output=True).returncode==0:break
  time.sleep(.2)
 port=subprocess.check_output(docker+['port',name,'5432/tcp'],text=True).strip().rsplit(':',1)[1];env['DATABASE_URL']=f'postgresql+psycopg://opscontrol:synthetic-local@127.0.0.1:{port}/opscontrol'
 started=False
 for index,step in enumerate(job['steps']):
  if 'run' not in step or step.get('name')=='Install backend dependencies':continue
  label=f'{index:02}-'+step.get('name','step').replace(' ','-').replace('/','-')[:90];body=step['run'];cwd=r/step.get('working-directory','.')
  if step.get('name')=='Start API and check HTTP endpoints':
   log=(out/'api.log').open('w');proc=subprocess.Popen(['uvicorn','app.main:app','--host','127.0.0.1','--port','8000'],cwd=r/'backend',env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);sessions.append(proc)
   body=body[body.index("python - <<'PY'"):]
  if step.get('name')=='Run frontend for browser evidence':
   log=(out/'vite.log').open('w');proc=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','5173','--strictPort'],cwd=r/'frontend',env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);sessions.append(proc);time.sleep(2);continue
  if step.get('name')=='Capture authenticated React UI with Playwright':body='node scripts/capture_phase1_ui.mjs'
  run(['bash','-e','-c',body],cwd,label)
 (out/'result.json').write_text(json.dumps({'status':'PASS','commands':commands,'environment':'existing pinned dependencies; local Node24 versus hosted Node20; all executable staging checks retained, dependency installation skipped'},indent=2))
finally:
 for proc in sessions:
  if proc.poll() is None:
   os.killpg(proc.pid,signal.SIGTERM)
   try:proc.wait(timeout=10)
   except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
 cleanup=subprocess.run(docker+['rm','-f','-v',name],capture_output=True)
 (out/'cleanup.json').write_text(json.dumps({'container':name,'exit_code':cleanup.returncode,'remaining':subprocess.run(docker+['inspect',name],capture_output=True).returncode==0,'processes_stopped':all(p.poll() is not None for p in sessions)}))
