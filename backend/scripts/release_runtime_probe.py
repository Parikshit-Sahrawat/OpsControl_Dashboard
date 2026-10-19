"""Controlled populated-DB, atomic-audit, retention and collector regressions."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
import subprocess
from uuid import UUID
from sqlalchemy import create_engine, select, func, text
from sqlalchemy.orm import Session
from app.db.session import SessionLocal, engine
from app.models import (DataSource, Collector, MetricDefinition, MetricSample, LogSource, LogEvent,
    JobOrder, JobOrderHistory, CollectorRun, CorrelationRecord, CorrelationEvidence)
from app.security.models import SecurityAuditEvent, User, AccessSession
from app.security.scope import Principal, configure_request_session, current_principal
from app.security.permission_catalog import PROVIDER_ID
from app.services.retention import prune_batch
from app.worker.collector_runtime import execute_collector, ADAPTERS, CollectionResult
from scripts.database_integrity import fingerprint

PRIVATE = Path(os.environ['RELEASE_PRIVATE_DIR'])
NOW = datetime.now(timezone.utc)

def seed():
    with SessionLocal() as db:
        source = db.scalar(select(DataSource).where(DataSource.name == 'north-synthetic'))
        collector = db.scalar(select(Collector).where(Collector.data_source_id == source.id))
        metric = MetricDefinition(organization_id=source.organization_id, data_source_id=source.id,
            collector_id=collector.id, name='retention-fixture', resource_type='APPLICATION', metric_type='GAUGE', retention_days=2)
        logs = LogSource(organization_id=source.organization_id, data_source_id=source.id,
            collector_id=collector.id, name='retention-fixture', source_type='API', resource_type='APPLICATION', retention_days=1)
        db.add_all([metric, logs]); db.flush()
        pinned = MetricSample(organization_id=source.organization_id, metric_definition_id=metric.id,
            observed_at=NOW-timedelta(days=10), value_numeric=1)
        db.add(pinned); db.flush()
        history = db.scalar(select(JobOrderHistory).join(JobOrder).where(JobOrder.organization_id == source.organization_id))
        correlation = CorrelationRecord(organization_id=source.organization_id, history_id=history.id,
            anchor_at=NOW, window_start=NOW-timedelta(minutes=5), window_end=NOW,
            summary='Synthetic retention pin', evidence_count=1)
        db.add(correlation); db.flush()
        db.add(CorrelationEvidence(correlation_id=correlation.id, evidence_type='METRIC', source_id=pinned.id,
            observed_at=pinned.observed_at, relationship='SYNTHETIC_RETENTION_PIN', details={'summary': 'Synthetic pinned sample'}))
        for days in (10, 10, 10, 0):
            db.add(MetricSample(organization_id=source.organization_id, metric_definition_id=metric.id,
                observed_at=NOW-timedelta(days=days), value_numeric=12))
            db.add(LogEvent(organization_id=source.organization_id, log_source_id=logs.id,
                observed_at=NOW-timedelta(days=days), message='Synthetic retention log'))
        db.add(SecurityAuditEvent(event_type='RETENTION_FIXTURE', outcome='SUCCESS', occurred_at=NOW-timedelta(days=1000)))
        from app.services.rule_models import MonitoringRuleCatalog
        db.add(MonitoringRuleCatalog(organization_id=source.organization_id, name='release-check-fixture', kind='METRIC'))
        # Historical fixture only: prove retired ITSM records/checks survive restore.
        # No monitoring event creates these records in the running application.
        from app.models import OperationalIncident
        db.add(OperationalIncident(organization_id=source.organization_id,
            episode_key='archived-release-fixture', source_kind='METRIC',
            source_reference='historical-synthetic-fixture', title='Archived synthetic record',
            severity='WARNING', status='RESOLVED', condition_status='RECOVERED',
            opened_at=NOW-timedelta(days=30), recovered_at=NOW-timedelta(days=29),
            resolved_at=NOW-timedelta(days=29)))
        # Enough resources to prove counts cannot be inferred from a capped page.
        for index in range(205):
            db.add(DataSource(organization_id=source.organization_id, name=f'Scale fixture {index:03}', source_type='LINUX_HOST'))
            db.add(DataSource(organization_id=source.organization_id, name=f'Service scale fixture {index:03}', source_type='API'))
        for index in range(8):
            db.add(Collector(data_source_id=source.id, name=f'Concurrency fixture {index}', collector_type='CONTROLLED_RELEASE', enabled=True))
        db.commit()
    print('Populated synthetic evidence and retention fixtures created')

def atomic_audit():
    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.username == 'test-admin'))
        source = db.scalar(select(DataSource).where(DataSource.name == 'north-synthetic'))
        sid, uid = source.id, admin.id
        before = db.scalar(select(func.count()).select_from(SecurityAuditEvent).where(SecurityAuditEvent.event_type == 'CONFIG_MUTATION'))
    principal = Principal(uid, 'test-admin', True, {})
    context = current_principal.set(principal)
    try:
        with SessionLocal() as db:
            configure_request_session(db)
            db.get(DataSource, sid).description = 'rolled back synthetic mutation'
            db.flush()
            db.rollback()
        with SessionLocal() as db:
            assert db.scalar(select(func.count()).select_from(SecurityAuditEvent).where(SecurityAuditEvent.event_type == 'CONFIG_MUTATION')) == before
            configure_request_session(db)
            db.get(DataSource, sid).description = 'committed synthetic mutation'
            db.commit()
        with SessionLocal() as db:
            assert db.scalar(select(func.count()).select_from(SecurityAuditEvent).where(SecurityAuditEvent.event_type == 'CONFIG_MUTATION')) == before+1
    finally:
        current_principal.reset(context)
    print('Atomic configuration mutation/audit commit and rollback PASS')

def last_admin_concurrency():
    from threading import Barrier
    from app.security.http import change_user_status, UserStatus
    from app.security.passwords import hash_password
    from fastapi import HTTPException
    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.username == 'test-admin'))
        second = User(username='concurrent-admin-fixture', password_hash=hash_password('synthetic-StrongPassword-123!'), platform_admin=True)
        db.add(second); db.flush(); first_id, second_id = admin.id, second.id; db.commit()
    barrier = Barrier(2)
    def disable(uid):
        context = current_principal.set(Principal(first_id, 'test-admin', True, {}, service_provider_id=PROVIDER_ID))
        try:
            barrier.wait(timeout=5)
            try:
                change_user_status(uid, UserStatus(active=False)); return 200
            except HTTPException as error:
                return error.status_code
        finally:
            current_principal.reset(context)
    with ThreadPoolExecutor(max_workers=2) as workers:
        outcomes = list(workers.map(disable, (first_id, second_id)))
    assert sorted(outcomes) == [200,409], outcomes
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(User).where(User.active.is_(True), User.platform_admin.is_(True))) == 1
        db.get(User, first_id).active = True; db.get(User, second_id).active = True; db.commit()
    print('Coordinated PostgreSQL last-administrator race PASS')

def multi_process_lock_recovery():
    with SessionLocal() as db:
        cid = db.scalar(select(Collector.id).where(Collector.collector_type == 'CONTROLLED_RELEASE'))
        before = db.scalar(select(func.count()).select_from(CollectorRun).where(CollectorRun.collector_id == cid))
    command = [sys.executable, '-m', 'scripts.release_runtime_probe', 'collect-once', str(cid)]
    first = subprocess.Popen(command, env={**os.environ, 'CONTROLLED_RELEASE_DELAY':'30'}, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        import time
        for _ in range(100):
            with SessionLocal() as db:
                if db.get(Collector, cid).status == 'RUNNING': break
            if first.poll() is not None: raise AssertionError('First replica exited before claim')
            time.sleep(.03)
        else: raise AssertionError('First replica did not start')
        subprocess.run(command, env={**os.environ, 'CONTROLLED_RELEASE_DELAY':'30'}, check=True, timeout=5, capture_output=True)
    finally:
        first.terminate(); first.wait(timeout=5)
    subprocess.run(command, env={**os.environ, 'CONTROLLED_RELEASE_DELAY':'.02'}, check=True, timeout=10, capture_output=True)
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(CollectorRun).where(CollectorRun.collector_id == cid)) == before+1
    print('Separate collector processes exclude duplicates and recover after process death PASS')

def collect_once():
    class Controlled:
        async def collect(self, collector):
            await asyncio.sleep(float(os.environ.get('CONTROLLED_RELEASE_DELAY','.1')))
            return CollectionResult(True, 'Controlled process observation', {'outcome':'SUCCESS'})
    ADAPTERS['CONTROLLED_RELEASE'] = Controlled()
    asyncio.run(execute_collector(UUID(sys.argv[2])))

def scale():
    from scripts.acceptance_scope import probe_headers
    import urllib.request
    base = os.environ['TEST_API_BASE']
    request = urllib.request.Request(base+'/api/v1/auth/login', data=json.dumps({'username':'test-north','password':'testing-only-StrongPassword-123!'}).encode(), headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request, timeout=10) as response:
        token = json.load(response)['access_token']
    def get(path):
        with urllib.request.urlopen(urllib.request.Request(base+path, headers={'Authorization':'Bearer '+token, **probe_headers(base, token, path)}), timeout=10) as response:
            return json.load(response)
    first = get('/api/v1/infrastructure/resources?limit=2&offset=0')
    second = get('/api/v1/infrastructure/resources?limit=2&offset=2')
    assert first['total'] == second['total'] == 205
    assert first['has_more'] and len(first['resources']) == 2
    assert not set(r['id'] for r in first['resources']) & set(r['id'] for r in second['resources'])
    with SessionLocal() as db:
        other = db.scalar(select(DataSource.organization_id).where(DataSource.name=='south-synthetic'))
    denied = get('/api/v1/infrastructure/resources?organization_id='+str(other))
    assert denied['total'] == 0 and not denied['resources']
    services = get('/api/v1/operations/services?limit=1&offset=0')
    assert services['total'] > 1 and len(services['services']) == 1 and services['has_more']
    from app.api.operations import prefetch_services, service_snapshot
    from sqlalchemy import event
    counter = [0]
    def query(*args): counter[0] += 1
    with SessionLocal() as db:
        sources = list(db.scalars(select(DataSource).where(DataSource.source_type == 'API')))
        event.listen(engine, 'before_cursor_execute', query)
        try:
            cached = prefetch_services(sources, db)
            assert counter[0] == 4, counter
        finally:
            event.remove(engine, 'before_cursor_execute', query)
        for source in sources:
            assert service_snapshot(source, db, cached[source.id]) == service_snapshot(source, db)
    print('Tenant-scoped complete counts, stable pagination and constant-query snapshots identical to legacy results PASS')

async def concurrent_collectors():
    class Controlled:
        active = 0
        peak = 0
        async def collect(self, collector):
            self.active += 1; self.peak = max(self.peak, self.active)
            await asyncio.sleep(.12)
            self.active -= 1
            return CollectionResult(True, 'Synthetic concurrency observation', {'outcome': 'SUCCESS'})
    controlled = Controlled(); ADAPTERS['CONTROLLED_RELEASE'] = controlled
    with SessionLocal() as db:
        ids = list(db.scalars(select(Collector.id).where(Collector.collector_type == 'CONTROLLED_RELEASE')))
        before = db.scalar(select(func.count()).select_from(CollectorRun))
    # Competing executions of the same ID must produce exactly one run.
    await asyncio.gather(*(execute_collector(ids[0]) for _ in range(6)))
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(CollectorRun)) == before+1
    # Production scheduler cap is tested with a fleet larger than its capacity.
    from app.worker.collector_runtime import scheduler_loop
    from unittest.mock import patch
    from app.core.config import settings
    with patch.object(settings, 'collector_max_concurrency', 2):
        task = asyncio.create_task(scheduler_loop(.03))
        try:
            for _ in range(100):
                with SessionLocal() as db:
                    completed = db.scalar(select(func.count()).select_from(CollectorRun).join(Collector).where(Collector.collector_type == 'CONTROLLED_RELEASE'))
                if completed >= len(ids): break
                await asyncio.sleep(.03)
            else: raise AssertionError('Bounded scheduler did not process the controlled fleet')
        finally:
            task.cancel(); await asyncio.gather(task, return_exceptions=True)
    assert controlled.peak <= 2, controlled.peak
    print('Same-collector exclusion and bounded concurrent fleet PASS')

def retention():
    maintenance = create_engine(os.environ['MAINTENANCE_DATABASE_URL'])
    with engine.connect() as connection:
        before = fingerprint(connection)
    with Session(maintenance) as db:
        dry = prune_batch(db, batch_size=2)
        assert dry['metric_samples'] == dry['log_events'] == 2, dry
        db.rollback()
    with engine.connect() as connection:
        assert fingerprint(connection) == before
    with Session(maintenance) as db:
        first = prune_batch(db, batch_size=2); db.commit()
        second = prune_batch(db, batch_size=2); db.commit()
        third = prune_batch(db, batch_size=2); db.commit()
    assert first['metric_samples'] + second['metric_samples'] == 3
    assert first['log_events'] + second['log_events'] == 3
    assert third['metric_samples'] == third['log_events'] == 0
    with engine.connect() as connection:
        after = fingerprint(connection)
    assert after['tables']['security_audit_events'] == before['tables']['security_audit_events']
    assert after['tables']['collector_runs'] == before['tables']['collector_runs']
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(MetricSample).join(MetricDefinition).where(MetricDefinition.name == 'retention-fixture')) == 2
    maintenance.dispose()
    print('Restricted maintenance role, bounded/idempotent retention, rollback, current/pinned evidence and indefinite audit preservation PASS')

def snapshot():
    with engine.connect() as connection:
        data = fingerprint(connection)
    path = PRIVATE/'fingerprint.json'
    if sys.argv[1] == 'snapshot':
        path.write_text(json.dumps(data, sort_keys=True)); path.chmod(0o600)
        print('Populated fingerprint saved:', len(data['tables']), 'tables;', sum(v['rows'] for v in data['tables'].values()), 'rows')
    else:
        expected = json.loads(path.read_text())
        if expected != data:
            (PRIVATE/'fingerprint-actual.json').write_text(json.dumps(data,sort_keys=True))
            changed = [name for name in expected['tables'] if expected['tables'][name] != data['tables'].get(name)]
            raise AssertionError(f'Restored integrity differs: tables={changed}; constraints_equal={expected["constraints"] == data["constraints"]}')
        with engine.begin() as connection:
            try:
                with connection.begin_nested():
                    connection.execute(text("UPDATE security_audit_events SET outcome='FAILURE'"))
            except Exception as exc:
                assert 'append-only' in str(exc)
            else:
                raise AssertionError('Restored audit trigger missing')
        for table, field, constraint in (
            ('monitoring_rule_catalogs', 'kind', 'ck_monitoring_catalog_kind'),
            ('operational_incidents', 'status', 'ck_incident_status'),
            ('operational_incidents', 'condition_status', 'ck_incident_condition'),
        ):
            with engine.begin() as connection:
                assert connection.scalar(text(f'SELECT count(*) FROM {table}')) > 0
                try:
                    with connection.begin_nested():
                        connection.execute(text(f"UPDATE {table} SET {field}='INVALID'"))
                except Exception as exc:
                    assert constraint in str(exc)
                else:
                    raise AssertionError('Restored CHECK not enforced: '+constraint)
        print('Full populated restore fingerprints, FKs/checks and audit trigger PASS')

def indexes_roundtrip():
    # Exercise the concurrent index migration's actual downgrade/upgrade DDL
    # without downgrading later data-bearing migrations (e.g. worker liveness).
    import importlib
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    migration = importlib.import_module('migrations.versions.0022_runtime_query_indexes')
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        with context.begin_transaction(), Operations.context(context):
            migration.downgrade()
            migration.upgrade()
        names = connection.scalars(text("SELECT indexname FROM pg_indexes WHERE schemaname='public'")).all()
        assert {'ix_collectors_due_local', 'ix_collector_runs_latest',
                'ix_infra_evidence_latest', 'ix_security_audit_occurred'} <= set(names)
    print('Concurrent-index migration DDL rollback/upgrade PASS; later populated columns preserved')

def main():
    if os.environ.get('OPSCONTROL_RELEASE_ACCEPTANCE') != '1' or os.environ.get('ENVIRONMENT') != 'demo':
        raise SystemExit('Explicit disposable release acceptance only')
    action = sys.argv[1]
    if action == 'seed': seed()
    elif action == 'exercise': atomic_audit(); last_admin_concurrency(); asyncio.run(concurrent_collectors()); multi_process_lock_recovery(); retention(); scale()
    elif action == 'collect-once': collect_once()
    elif action in ('snapshot', 'verify'): snapshot()
    elif action == 'indexes-roundtrip': indexes_roundtrip()
    else: raise SystemExit('Unknown acceptance phase')

if __name__ == '__main__':
    main()
