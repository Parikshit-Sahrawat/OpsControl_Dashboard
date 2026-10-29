#!/usr/bin/env python3
"""Application-only UAT deployer with preflight, rollback, and durable audit.

Never runs migrations or changes postgres/gateway services. Requires independent
release authorization by pull_release.py before invocation.
"""
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
from urllib.request import urlopen

DIGEST = re.compile(r'ghcr\.io/[a-z0-9_.-]+/[a-z0-9_.-]+@sha256:[a-f0-9]{64}\Z')
SHA = re.compile(r'[a-f0-9]{40}\Z')

def required(key):
    value = os.environ.get(key)
    if not value:
        raise RuntimeError(f'Missing {key}')
    return value

def run(*args, env=None):
    p = subprocess.run(args, check=True, text=True, env=env, capture_output=True, timeout=600)
    return p.stdout

def check_url(url):
    with urlopen(url, timeout=15) as r:
        if r.status != 200:
            raise RuntimeError('Health check failed')

def atomic(path, obj):
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False, prefix='.uat-') as f:
        temp = Path(f.name)
        os.chmod(temp, 0o600)
        json.dump(obj, f, sort_keys=True)
        f.write('\n'); f.flush(); os.fsync(f.fileno())
    os.replace(temp, path)
    fd = os.open(path.parent, os.O_DIRECTORY | os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)

def record(state, event):
    with (state / 'deploy-audit.jsonl').open('a') as f:
        os.chmod(f.name, 0o600)
        f.write(json.dumps(dict(event, at=int(time.time())), sort_keys=True)+'\n')
        f.flush(); os.fsync(f.fileno())

def config(compose, env, backend, frontend):
    c = json.loads(run(*compose, 'config', '--format', 'json', env=env))
    s = c.get('services', {})
    if not {'api','worker','frontend','postgres','ingestion-gateway'} <= set(s):
        raise RuntimeError('Missing expected services')
    for name, image in [('api',backend),('worker',backend),('frontend',frontend)]:
        if s[name].get('build') or s[name].get('image','').lower() != image:
            raise RuntimeError(f'Unexpected image/build for {name}')
    return c

def check_worker(compose, env, started):
    # Execute inside the worker: an API endpoint cannot satisfy this check.
    probe = ("import pathlib,time; "
             "t=float(pathlib.Path('/tmp/opscontrol-worker-heartbeat').read_text()); "
             f"assert {started!r} <= t <= time.time() and time.time()-t < 60")
    run(*compose, 'exec', '-T', 'worker', 'python', '-c', probe, env=env)


def deploy_images(compose, base_env, backend, frontend, health):
    env = dict(base_env, STAGE_B_BACKEND_IMAGE=backend, STAGE_B_FRONTEND_IMAGE=frontend)
    config(compose, env, backend, frontend)
    run(*compose, 'pull', 'api', 'worker', 'frontend', env=env)
    started = time.time()
    run(*compose, 'up', '-d', '--no-deps', 'api', 'worker', 'frontend', env=env)
    # Worker readiness must be a separate signal, not inferred from API health.
    deadline = time.monotonic() + 120
    while True:
        try:
            for url in health:
                check_url(url)
            check_worker(compose, env, started)
            break
        except Exception:
            if time.monotonic() >= deadline:
                raise
            time.sleep(2)

def main():
    raw_state = Path(required('LOCAL_UAT_STATE_DIR'))
    if raw_state.is_symlink():
        raise RuntimeError('Symlink state directory rejected')
    state = raw_state.resolve(strict=True)
    if state.stat().st_mode & 0o077 or state.is_symlink():
        raise RuntimeError('State directory must be private')
    if os.environ.get('LOCAL_UAT_PULL_ENABLED') != 'true':
        raise RuntimeError('Controller is disabled')
    base = Path(required('LOCAL_UAT_BASE_COMPOSE')).resolve(strict=True)
    override = Path(required('LOCAL_UAT_OVERRIDE_COMPOSE')).resolve(strict=True)
    project = required('LOCAL_UAT_PROJECT')
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,62}', project):
        raise RuntimeError('Invalid Compose project')
    if project == 'opscontrol-uat' and os.environ.get('LOCAL_UAT_LIVE_APPROVED') != 'true':
        raise RuntimeError('Live UAT deployment not authorized')
    overlay = Path(__file__).resolve().parents[2] / 'deploy/uat/compose.local-images.yml'
    compose = ('docker','compose','-p',project,'-f',str(base),'-f',str(override),'-f',str(overlay))
    health = (required('LOCAL_UAT_API_URL').rstrip('/')+'/health/db',
              required('LOCAL_UAT_FRONTEND_URL'))
    with (state / 'deployment.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # Verify only after acquiring the deployment lock; atomic nonce reservation
        # rejects replay/concurrency before Docker or image pulls are invoked.
        from release_handoff import read_fd
        body = read_fd(state)
        sha = body['sha']
        backend, frontend = body['images']['backend'], body['images']['frontend']
        last_file = state / 'last-deployment.json'
        if last_file.exists() and json.loads(last_file.read_text()).get('sha') == sha:
            raise RuntimeError('Release SHA already deployed')
        last_path = state / 'last-deployment.json'
        previous = json.loads(last_path.read_text()) if last_path.exists() else None
        try:
            deploy_images(compose, os.environ, backend, frontend, health)
        except Exception:
            rollback = 'NOT_AVAILABLE'
            if previous:
                try:
                    deploy_images(compose, os.environ, previous['backend_image'],
                                  previous['frontend_image'], health)
                    rollback = 'PASS'
                except Exception:
                    rollback = 'FAIL'
            record(state, {'sha':sha,'outcome':'DEPLOY_FAILED','rollback':rollback})
            raise RuntimeError(f'Deployment failed; rollback={rollback}') from None
        result = {'sha':sha,'backend_image':backend,'frontend_image':frontend,
                  'verified_at':int(time.time()),'result':'PASS'}
        atomic(last_path, result)
        record(state, {'sha':sha,'outcome':'DEPLOYED','rollback':'NOT_REQUIRED'})
        print(json.dumps(result))

if __name__ == '__main__':
    main()
