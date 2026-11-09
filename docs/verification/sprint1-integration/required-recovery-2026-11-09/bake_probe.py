import json, os, secrets, subprocess, tempfile, sys
from pathlib import Path
sys.path.insert(0,'/tmp/oc-sprint1-integration')
from scripts.ci.compose_build import build_with_trust
out=Path('/tmp/oc-s1-required-recovery/bake-probe-3');out.mkdir(exist_ok=True)
project='oc-ca-proof-'+secrets.token_hex(4)
private=Path(tempfile.mkdtemp(prefix=project)); context=private/'context';context.mkdir()
os.environ['BUILDX_CONFIG']=str(private/'buildx')
ca=Path('/etc/ssl/certs/ca-certificates.crt').resolve()
(context/'Dockerfile').write_text('FROM python:3.12-alpine\nRUN --network=none --mount=type=secret,id=proxy_ca,required=true python -c "import ssl; c=ssl.create_default_context(cafile=\'/run/secrets/proxy_ca\'); assert c.verify_mode==ssl.CERT_REQUIRED and c.check_hostname"\n')
(private/'compose.json').write_text(json.dumps({'services':{'proof':{'image':project+':proof','build':{'context':str(context),'secrets':['proxy_ca']}}},'secrets':{'proxy_ca':{'file':str(ca)}}}))
compose=['docker','compose','-p',project,'-f',str(private/'compose.json')]
steps=[]
def call(command,expected=0):
 r=subprocess.run(command,cwd=private,capture_output=True,text=True,timeout=180)
 (out/f'{len(steps):02d}.log').write_text(r.stdout+'\n'+r.stderr)
 steps.append({'command':command,'exit':r.returncode,'expected':expected})
 if expected is not None: assert r.returncode==expected,steps[-1]
 return r
try:
 plan=call(compose+['build','--print']).stdout;(private/'initial.json').write_text(plan)
 r=call(['docker','buildx','bake','-f',str(private/'initial.json'),'--load'],None)
 assert r.returncode!=0 and 'additional privileges requested' in r.stderr
 build_with_trust(compose,ca,private,lambda command:call(command).stdout)
 call(['docker','run','--rm',project+':proof','python','-c','from pathlib import Path; assert not Path("/run/secrets/proxy_ca").exists()'])
 call(['docker','image','inspect',project+':proof','--format','{{.Id}}'])
 (out/'result.json').write_text(json.dumps({'status':'PASS','negative_without_entitlement':'REJECTED','positive_exact_file':'PASS','secret_absent_from_runtime':'PASS','steps':steps},indent=2))
finally:
 call(['docker','image','rm',project+':proof'],None)
 import shutil
 shutil.rmtree(private)
 (out/'cleanup.json').write_text(json.dumps({'owned_tag':project+':proof','remaining':subprocess.run(['docker','image','inspect',project+':proof'],capture_output=True).returncode==0,'private_removed':not private.exists()}))
