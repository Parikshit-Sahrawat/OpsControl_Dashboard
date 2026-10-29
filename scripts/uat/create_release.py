#!/usr/bin/env python3
import hashlib
import json
import os
from pathlib import Path
import re
from datetime import datetime, timezone

sha = os.environ['GITHUB_SHA']
assert re.fullmatch('[a-f0-9]{40}', sha)
repo = os.environ['GITHUB_REPOSITORY']
assert repo == 'Parikshit-Sahrawat/OpsControl_Dashboard'
prefix = os.environ['IMAGE_PREFIX']
assert prefix == 'ghcr.io/parikshit-sahrawat/opscontrol_dashboard'
backend = os.environ['BACKEND_DIGEST']
frontend = os.environ['FRONTEND_DIGEST']
assert re.fullmatch('sha256:[a-f0-9]{64}', backend)
assert re.fullmatch('sha256:[a-f0-9]{64}', frontend)
files = sorted(p for p in Path('backend/migrations').rglob('*') if p.is_file())
h = hashlib.sha256()
for path in files:
    h.update(hashlib.sha256(path.read_bytes()).hexdigest().encode('ascii'))
    h.update(b'  ')
    h.update(str(path).encode('utf-8'))
    h.update(b'\n')
manifest = {'schema':1,'repository':repo,'ref':'refs/heads/main','sha':sha,
    'workflow':'.github/workflows/local-uat-auto-deploy.yml','policy':'uat-pull-v1',
    'run_id':int(os.environ['GITHUB_RUN_ID']),'run_attempt':int(os.environ['GITHUB_RUN_ATTEMPT']),
    'created_at':datetime.now(timezone.utc).isoformat(),
    'migration_hash':h.hexdigest(),
    'images':{'backend':prefix+'-backend@'+backend,'frontend':prefix+'-frontend@'+frontend}}
Path('release.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
