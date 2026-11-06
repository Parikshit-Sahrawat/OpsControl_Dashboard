"""Owned PostgreSQL migration preservation and actual dump/restore proof."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

assert (
    os.environ.get("OPSCONTROL_ETL_SCOPE_ACCEPTANCE") == "1"
    and os.environ.get("ENVIRONMENT") == "test"
)
out = Path(os.environ["ETL_SCOPE_EVIDENCE_DIR"])
container = os.environ["ETL_SCOPE_CONTAINER"]
assert container.startswith("oc-etl002-")
url = make_url(os.environ["DATABASE_URL"])
engine = create_engine(url)
checks = []
commands = []


def migration(action, target, label, database=None, blocked=False, extra=()):
    env = os.environ.copy()
    if database:
        env["DATABASE_URL"] = url.set(database=database).render_as_string(
            hide_password=False
        )
    args = [sys.executable, "-m", "alembic", action, target, *extra]
    r = subprocess.run(args, env=env, capture_output=True, text=True, timeout=90)
    (out / (label + ".log")).write_text(
        (r.stdout + "\n" + r.stderr).replace(url.password, "[REDACTED]")
    )
    commands.append(
        {
            "command": args,
            "database": database or url.database,
            "exit_code": r.returncode,
            "expected": "nonzero" if blocked else 0,
            "log": label + ".log",
        }
    )
    assert (r.returncode != 0) == blocked, (label, r.returncode)
    if blocked:
        assert (
            "Unsafe populated ETL downgrade blocked before DDL" in r.stderr
            or "unsupported" in r.stderr
            or "explicit Alembic revision" in r.stderr
        ), label


def snapshot(e):
    with e.connect() as c:
        i = inspect(c)
        result = {}
        for table in sorted(i.get_table_names()):
            rows = c.scalars(
                text(
                    f'SELECT to_jsonb(t)::text FROM "{table}" t ORDER BY to_jsonb(t)::text'
                )
            ).all()
            result[table] = {
                "count": len(rows),
                "sha256": hashlib.sha256(json.dumps(rows).encode()).hexdigest(),
                "columns": [
                    (x["name"], str(x["type"]), x["nullable"])
                    for x in i.get_columns(table)
                ],
                "foreign_keys": i.get_foreign_keys(table),
            }
        return result


def seed_legacy(e):
    org, vm, job, history = [uuid4() for _ in range(4)]
    with e.begin() as c:
        c.execute(
            text(
                "INSERT INTO organizations(id,name,code,created_at,updated_at) VALUES (:o,:n,:n,now(),now())"
            ),
            {"o": org, "n": "rollback-" + uuid4().hex},
        )
        c.execute(
            text(
                "INSERT INTO vms(id,organization_id,hostname,created_at) VALUES (:v,:o,'synthetic.invalid',now())"
            ),
            {"v": vm, "o": org},
        )
        c.execute(
            text(
                "INSERT INTO job_orders(id,organization_id,vm_id,name,created_at) VALUES (:j,:o,:v,'legacy-preserved',now())"
            ),
            {"j": job, "o": org, "v": vm},
        )
        c.execute(
            text(
                "INSERT INTO job_order_histories(id,job_order_id,execution_type,status,created_at) VALUES (:h,:j,'SCHEDULED','SUCCESS',now())"
            ),
            {"h": history, "j": job},
        )
    return org, vm, job, history


def docker(*args, input=None):
    r = subprocess.run(
        [
            "docker",
            "--host=unix:///var/run/docker.sock",
            "exec",
            "-i",
            container,
            *args,
        ],
        input=input,
        capture_output=True,
        timeout=90,
    )
    assert r.returncode == 0, (args, r.stderr.decode())
    return r.stdout


try:
    empty = snapshot(engine)
    migration("downgrade", "0038_k8s_cluster_associations", "empty-downgrade")
    migration("upgrade", "head", "empty-upgrade")
    assert snapshot(engine) == empty
    checks.append("empty 0039→0038→0039 round trip preserves initial schema/data")
    migration("downgrade", "0038_k8s_cluster_associations", "legacy-prepare")
    org, vm, legacy, history = seed_legacy(engine)
    legacy_before = snapshot(engine)
    migration("upgrade", "head", "populated-forward-upgrade")
    migration("downgrade", "0038_k8s_cluster_associations", "legacy-safe-downgrade")
    assert snapshot(engine) == legacy_before
    checks.append(
        "unassigned legacy Job/History populated upgrade and safe rollback preserve every row/schema/FK"
    )
    migration("upgrade", "head", "legacy-final-upgrade")
    workflow, a, b, edge = [uuid4() for _ in range(4)]
    with engine.begin() as c:
        c.execute(
            text(
                "INSERT INTO etl_workflows(id,organization_id,name,environment,schedule,active,created_at) VALUES (:w,:o,'populated','PROD','{}',true,now())"
            ),
            {"w": workflow, "o": org},
        )
        for j in [a, b]:
            c.execute(
                text(
                    "INSERT INTO job_orders(id,organization_id,vm_id,workflow_id,name,environment,created_at) VALUES (:j,:o,:v,:w,:n,'PROD',now())"
                ),
                {"j": j, "o": org, "v": vm, "w": workflow, "n": str(j)},
            )
        c.execute(
            text(
                "INSERT INTO etl_workflow_dependencies(id,workflow_id,predecessor_job_id,successor_job_id) VALUES (:id,:w,:a,:b)"
            ),
            {"id": edge, "w": workflow, "a": a, "b": b},
        )
    before = snapshot(engine)
    migration(
        "downgrade",
        "0038_k8s_cluster_associations",
        "populated-downgrade-refused",
        blocked=True,
    )
    assert snapshot(engine) == before
    checks.append(
        "populated Workflow/Job/dependency downgrade refused before DDL; all rows, FK metadata and revision preserved"
    )
    migration("downgrade", "-1", "relative-downgrade-refused", blocked=True)
    migration(
        "downgrade",
        "0039_etl_workflow_foundation:0038_k8s_cluster_associations",
        "offline-downgrade-refused",
        blocked=True,
        extra=("--sql",),
    )
    assert snapshot(engine) == before
    checks.append(
        "relative and offline downgrade bypasses refused without changing database"
    )
    archive = docker("pg_dump", "-U", "postgres", "-Fc", url.database)
    (out / "synthetic-populated-backup.dump").write_bytes(archive)
    restore = "etl_restore_" + uuid4().hex[:10]
    docker("createdb", "-U", "postgres", restore)
    docker(
        "pg_restore", "-U", "postgres", "--exit-on-error", "-d", restore, input=archive
    )
    restored = create_engine(url.set(database=restore))
    restored_snapshot = snapshot(restored)
    assert restored_snapshot == before
    restored.dispose()
    checks.append(
        "actual custom-format pg_dump/pg_restore to separate empty owned database matches every table hash, column and FK"
    )
    # Older identity/evidence fields are independently protected, not only the
    # newest workflow tables. No customer records are cleared to permit downgrade.
    old = "etl_legacy_" + uuid4().hex[:10]
    docker("createdb", "-U", "postgres", old)
    migration(
        "upgrade", "0017_rule_catalogs_activation", "old-identity-base", database=old
    )
    older = create_engine(url.set(database=old))
    _, _, old_job, old_history = seed_legacy(older)
    original = snapshot(older)
    migration(
        "upgrade",
        "0018_pentaho_execution_identity",
        "identity-additive-upgrade",
        database=old,
    )
    migration(
        "downgrade",
        "0017_rule_catalogs_activation",
        "null-identity-safe-downgrade",
        database=old,
    )
    assert snapshot(older) == original
    migration(
        "upgrade",
        "0018_pentaho_execution_identity",
        "identity-upgrade-again",
        database=old,
    )
    with older.begin() as c:
        c.execute(
            text(
                "UPDATE job_order_histories SET provider_execution_id='synthetic-native-id' WHERE id=:id"
            ),
            {"id": old_history},
        )
    identity_before = snapshot(older)
    migration(
        "downgrade",
        "0017_rule_catalogs_activation",
        "populated-identity-refused",
        database=old,
        blocked=True,
    )
    assert snapshot(older) == identity_before
    migration(
        "upgrade", "0020_etl_monitoring_evidence", "evidence-upgrade", database=old
    )
    with older.begin() as c:
        c.execute(
            text("UPDATE job_order_histories SET source_evidence='{}' WHERE id=:id"),
            {"id": old_history},
        )
    evidence_before = snapshot(older)
    migration(
        "downgrade",
        "0019_infrastructure_evidence",
        "populated-evidence-refused",
        database=old,
        blocked=True,
    )
    assert snapshot(older) == evidence_before
    older.dispose()
    checks.append(
        "0018 NULL-only safe rollback proven; populated native identity and 0020 source evidence protected with unchanged hashes"
    )
    with engine.connect() as c:
        version = c.scalar(text("SELECT version()"))
    (out / "rollback-results.json").write_text(
        json.dumps(
            {
                "status": "PASS",
                "checks": checks,
                "postgresql": version,
                "before_refused_rollback": before,
                "after_restore": restored_snapshot,
                "backup_sha256": hashlib.sha256(archive).hexdigest(),
                "backup_bytes": len(archive),
                "commands": commands,
                "scope": "all databases are in this harness-owned disposable container; no live UAT/production",
            },
            indent=2,
            default=str,
        )
        + "\n"
    )
    print(
        "PostgreSQL rollback/upgrade/preservation/recovery PASS:", len(checks), "groups"
    )
finally:
    (out / "rollback-commands.json").write_text(json.dumps(commands, indent=2) + "\n")
    engine.dispose()
