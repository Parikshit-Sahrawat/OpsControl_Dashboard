"""SEC-03: authenticated, single-use controller -> deployer handoff.

Security boundary requires SEC-04: key and deployer execution identity must be
isolated from untrusted local users. A same-UID attacker can otherwise read key.
"""
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import stat
import time

class HandoffError(RuntimeError):
    pass

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()

def key_for(state):
    path = state / 'handoff.key'
    if path.is_symlink():
        raise HandoffError('Symlink key rejected')
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.geteuid():
            raise HandoffError('Insecure handoff key permissions/ownership')
        key = os.read(fd, 65)
        if len(key) != 32:
            raise HandoffError('Invalid handoff key length')
        return key
    finally:
        os.close(fd)

def create(state, manifest):
    key = key_for(state)
    body = {'schema': 1, 'sha': manifest['sha'], 'images': dict(manifest['images']),
            'run_id': manifest['run_id'], 'run_attempt': manifest['run_attempt'],
            'nonce': secrets.token_hex(32), 'issued_at': int(time.time())}
    mac = hmac.new(key, canonical(body), hashlib.sha256).hexdigest()
    return canonical({'body': body, 'mac': mac})

def verify_and_consume(state, raw, *, now=None):
    if len(raw) > 8192:
        raise HandoffError('Oversized handoff')
    try:
        envelope = json.loads(raw)
        if set(envelope) != {'body', 'mac'}:
            raise ValueError('Invalid envelope')
        body, mac = envelope['body'], envelope['mac']
        if not isinstance(body, dict) or set(body) != {'schema','sha','images','run_id','run_attempt','nonce','issued_at'}:
            raise ValueError('Invalid body')
        if not isinstance(mac, str) or len(mac) != 64:
            raise ValueError('Invalid MAC')
        if not hmac.compare_digest(hmac.new(key_for(state), canonical(body), hashlib.sha256).hexdigest(), mac):
            raise HandoffError('Handoff authentication failed')
        # Explicit validation here avoids depending on controller imports in deployer.
        import re
        sha = body['sha']; images = body['images']; nonce = body['nonce']
        if body['schema'] != 1 or not isinstance(sha, str) or not re.fullmatch('[a-f0-9]{40}', sha):
            raise ValueError('Invalid source SHA')
        if not isinstance(images, dict) or set(images) != {'backend', 'frontend'}:
            raise ValueError('Invalid images')
        for name, image in images.items():
            if not isinstance(image, str) or not re.fullmatch(
                r'ghcr\.io/parikshit-sahrawat/opscontrol_dashboard-'+name+'@sha256:[a-f0-9]{64}', image):
                raise ValueError('Invalid image')
        if type(body['run_id']) is not int or body['run_id'] <= 0 or type(body['run_attempt']) is not int or body['run_attempt'] <= 0:
            raise ValueError('Invalid run')
        if not isinstance(nonce, str) or not re.fullmatch('[a-f0-9]{64}', nonce):
            raise ValueError('Invalid nonce')
        issued = body['issued_at']; now = int(time.time()) if now is None else now
        if type(issued) is not int or not (now - 120 <= issued <= now + 10):
            raise HandoffError('Expired/future handoff')
    except (TypeError, ValueError, KeyError, AttributeError) as exc:
        raise HandoffError('Malformed handoff') from exc
    # Atomic O_EXCL reservation; consumed before any Docker operation. Keep markers
    # for replay prevention, including failed deployments; retention requires review.
    used = state / 'consumed-handoffs'
    if used.is_symlink():
        raise HandoffError('Unsafe nonce directory')
    used.mkdir(mode=0o700, exist_ok=True)
    if used.stat().st_mode & 0o077:
        raise HandoffError('Insecure nonce directory')
    marker = used / nonce
    try:
        fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    except FileExistsError as exc:
        raise HandoffError('Replayed handoff') from exc
    with os.fdopen(fd, 'w') as file:
        file.write(sha+'\n'); file.flush(); os.fsync(file.fileno())
    return body

def read_fd(state):
    raw_fd = os.environ.get('LOCAL_UAT_HANDOFF_FD')
    if not raw_fd or not raw_fd.isdecimal():
        raise HandoffError('Authenticated handoff FD required')
    fd = int(raw_fd)
    if fd < 3:
        raise HandoffError('Invalid handoff FD')
    data = os.read(fd, 8193)
    os.close(fd)
    return verify_and_consume(state, data)
