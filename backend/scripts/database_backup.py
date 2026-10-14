"""Verified custom-format backup/empty-target restore using libpq service files.

Credentials stay in a private PGSERVICEFILE, never command-line DSNs. An optional
Docker container supplies PostgreSQL tools; PGSERVICEFILE is its internal path.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess

def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()

def tools(container: str | None) -> list[str]:
    if not os.environ.get('PGSERVICE') or not os.environ.get('PGSERVICEFILE'):
        raise ValueError('PGSERVICE and private PGSERVICEFILE are required')
    return ['docker', 'exec', '-e', 'PGSERVICE', '-e', 'PGSERVICEFILE', container] if container else []

def backup(path: Path, prefix: list[str]) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if stat.S_IMODE(path.parent.stat().st_mode) & 0o077:
        raise ValueError('Backup directory must be private (0700)')
    manifest_path = path.with_suffix(path.suffix + '.json')
    if path.exists() or manifest_path.exists():
        raise ValueError('Refusing to overwrite an existing backup or manifest')
    archive_created = manifest_created = False
    try:
        with path.open('xb') as stream:
            archive_created = True
            path.chmod(0o600)
            subprocess.run(prefix + ['pg_dump', '--format=custom'], stdout=stream, check=True, timeout=1800)
        manifest = {'format': 'postgresql-custom', 'sha256': digest(path),
                    'created_at': datetime.now(timezone.utc).isoformat(), 'bytes': path.stat().st_size}
        with manifest_path.open('x', encoding='utf-8') as stream:
            manifest_created = True
            manifest_path.chmod(0o600)
            stream.write(json.dumps(manifest, indent=2) + '\n')
        return manifest
    except BaseException:
        if archive_created:
            path.unlink(missing_ok=True)
        if manifest_created:
            manifest_path.unlink(missing_ok=True)
        raise

def restore(path: Path, prefix: list[str]) -> None:
    manifest = json.loads(path.with_suffix(path.suffix + '.json').read_text())
    if manifest.get('format') != 'postgresql-custom' or digest(path) != manifest.get('sha256'):
        raise ValueError('Backup checksum or format mismatch')
    empty = subprocess.run(prefix + ['psql', '-XAt', '-v', 'ON_ERROR_STOP=1', '-c',
        "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname NOT LIKE 'pg_toast%' AND c.relkind IN ('r','p','v','m','S','f')"],
        capture_output=True, text=True, check=True, timeout=30).stdout.strip()
    if empty != '0':
        raise ValueError('Restore target must be a new, empty database')
    with path.open('rb') as stream:
        # docker exec needs -i to pass the archive through standard input.
        restore_prefix = prefix.copy()
        if restore_prefix:
            restore_prefix.insert(2, '-i')
        subprocess.run(restore_prefix + ['pg_restore', '--exit-on-error', '--single-transaction', '--no-owner', '--no-acl', '--dbname=service=' + os.environ['PGSERVICE']],
                       stdin=stream, check=True, timeout=1800)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('backup', 'restore'))
    parser.add_argument('path', type=Path)
    parser.add_argument('--container')
    args = parser.parse_args()
    prefix = tools(args.container)
    result = backup(args.path, prefix) if args.action == 'backup' else restore(args.path, prefix)
    print(json.dumps({'action': args.action, 'status': 'PASS', 'manifest': result}))

if __name__ == '__main__':
    main()
