"""Synthetic-only preservation probe; never point this at customer/UAT data.

Requires this task's uniquely labelled disposable Docker container. Dumps remain
in a temporary directory and are erased after restoration; evidence contains
counts and hashes, never row values or credentials.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


def main():
    url = make_url(os.environ['DATABASE_URL'])
    if os.environ.get('OPSCONTROL_SCOPE_REMOVAL_FIXTURE') != '1' or url.database != 'scope_removal':
        raise SystemExit('Explicit synthetic scope_removal fixture required')
    docker = ['docker', '--host=unix:///var/run/docker.sock']
    env = {k: v for k, v in os.environ.items() if k not in (
        'DOCKER_HOST', 'DOCKER_CONTEXT', 'DOCKER_TLS', 'DOCKER_TLS_VERIFY', 'DOCKER_CERT_PATH')}
    def command(*args, **kwargs):
        return subprocess.run(list(args), env=env, check=True, **kwargs)
    container = 'oc-scope-rem-001-pg'
    info = json.loads(command(*docker, 'inspect', container, capture_output=True, text=True).stdout)[0]
    if info['Config']['Labels'].get('task') != 'OC-SCOPE-REM-001':
        raise SystemExit('Fixture ownership label mismatch')
    ips = [v['IPAddress'] for v in info['NetworkSettings']['Networks'].values()]
    if url.host not in ips or url.port != 5432:
        raise SystemExit('URL must identify the owned container bridge IP')
    # Seed legacy identity/history directly: the product import route is gone.
    from tests.test_kubernetes_cluster_associations import KubernetesClusterAssociationTests
    fixture = KubernetesClusterAssociationTests()
    fixture.setUp()
    fixture.db.commit()
    fixture.doCleanups()
    def snapshot(database):
        engine = create_engine(url.set(database=database))
        result = {}
        with engine.connect() as conn:
            tables = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")).scalars().all()
            for table in tables:
                # Names are from the server catalog, quoted through the dialect.
                quoted = engine.dialect.identifier_preparer.quote(table)
                rows = conn.execute(text(f'SELECT row_to_json(t)::text FROM {quoted} t')).scalars().all()
                canonical = sorted(json.dumps(json.loads(r), sort_keys=True, separators=(',', ':')) for r in rows)
                result[table] = {'rows':len(rows), 'sha256':hashlib.sha256('\n'.join(canonical).encode()).hexdigest()}
        engine.dispose()
        return result
    before = snapshot('scope_removal')
    command(str(Path('.venv/bin/alembic')), 'upgrade', 'head')
    after = snapshot('scope_removal')
    with tempfile.TemporaryDirectory(prefix='oc-scope-rem-001-') as directory:
        dump = Path(directory) / 'synthetic.dump'
        with dump.open('wb') as out:
            command(*docker, 'exec', container, 'pg_dump', '-U', 'postgres', '-Fc', 'scope_removal', stdout=out)
        os.chmod(dump, 0o600)
        dump_hash = hashlib.sha256(dump.read_bytes()).hexdigest()
        command(*docker, 'exec', container, 'createdb', '-U', 'postgres', 'scope_removal_restored')
        with dump.open('rb') as inp:
            command(*docker, 'exec', '-i', container, 'pg_restore', '-U', 'postgres', '-d', 'scope_removal_restored', stdin=inp)
        restored = snapshot('scope_removal_restored')
    result = {'source_sha':command('git', 'rev-parse', 'HEAD', capture_output=True, text=True).stdout.strip(),
              'image_id':info['Image'], 'container_id':info['Id'],
              'before':before, 'after':after, 'restored':restored,
              'dump_sha256':dump_hash, 'dump_retention':'synthetic dump erased after restore',
              'upgrade_preserved':before == after, 'restore_preserved':before == restored,
              'scope':'synthetic-only; no schema change; populated upgrade head is a no-op'}
    print(json.dumps(result, indent=2))
    if before != after or before != restored:
        raise SystemExit('Preservation mismatch')


if __name__ == '__main__':
    main()
