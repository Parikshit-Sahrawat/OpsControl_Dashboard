#!/usr/bin/env python3
"""Restore-verify the explicitly local Docker demo before an additive upgrade."""
import json, os, secrets, subprocess, time, hashlib
from pathlib import Path

root = Path(__file__).resolve().parents[1]
private = root / ".demo-private/backups"
private.mkdir(parents=True, exist_ok=True)
private.chmod(0o700)


def run(args, data=None):
    r = subprocess.run(args, input=data, capture_output=True)
    if r.returncode:
        (private / "restore-error.log").write_bytes(r.stderr)
        print("Failed operation:", args[3] if len(args) > 3 else args[0])
        for line in r.stderr.decode(errors="replace").splitlines():
            if "ERROR:" in line:
                print(line[:240])
        raise RuntimeError(
            "Backup/restore command failed; no original database changes made"
        )
    return r.stdout


environment = (
    run(
        [
            "docker",
            "exec",
            "opscontrol_dashboard-api-1",
            "python",
            "-c",
            "from app.core.config import settings;print(settings.environment)",
        ]
    )
    .decode()
    .strip()
)
assert (
    environment == "demo"
), "Only explicitly identified local demo may be backed up here"
backup = run(
    [
        "docker",
        "exec",
        "opscontrol_dashboard-postgres-1",
        "pg_dump",
        "-U",
        "opscontrol",
        "-d",
        "opscontrol",
        "-Fc",
    ]
)
path = private / ("arch001-v15-" + str(int(time.time())) + ".dump")
path.write_bytes(backup)
path.chmod(0o600)
name = "opscontrol-backup-verify-" + secrets.token_hex(5)
try:
    run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            name,
            "--network",
            "none",
            "-e",
            "POSTGRES_USER=opscontrol",
            "-e",
            "POSTGRES_DB=opscontrol",
            "-e",
            "POSTGRES_PASSWORD=" + secrets.token_urlsafe(32),
            "postgres:17-alpine",
        ]
    )
    for _ in range(100):
        if (
            subprocess.run(
                [
                    "docker",
                    "exec",
                    name,
                    "pg_isready",
                    "-h",
                    "127.0.0.1",
                    "-U",
                    "opscontrol",
                ],
                capture_output=True,
            ).returncode
            == 0
        ):
            break
        time.sleep(0.2)
    else:
        raise RuntimeError("Restore verifier startup failed")
    run(
        [
            "docker",
            "exec",
            "-i",
            name,
            "pg_restore",
            "-U",
            "opscontrol",
            "-d",
            "opscontrol",
            "--exit-on-error",
        ],
        backup,
    )
    sql = "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
    tables = (
        run(
            [
                "docker",
                "exec",
                name,
                "psql",
                "-U",
                "opscontrol",
                "-d",
                "opscontrol",
                "-Atc",
                sql,
            ]
        )
        .decode()
        .splitlines()
    )
    counts = {}
    for table in tables:
        assert table.replace("_", "").isalnum()
        query = 'SELECT count(*) FROM "' + table + '"'
        original = (
            run(
                [
                    "docker",
                    "exec",
                    "opscontrol_dashboard-postgres-1",
                    "psql",
                    "-U",
                    "opscontrol",
                    "-d",
                    "opscontrol",
                    "-Atc",
                    query,
                ]
            )
            .decode()
            .strip()
        )
        restored = (
            run(
                [
                    "docker",
                    "exec",
                    name,
                    "psql",
                    "-U",
                    "opscontrol",
                    "-d",
                    "opscontrol",
                    "-Atc",
                    query,
                ]
            )
            .decode()
            .strip()
        )
        assert (
            original == restored
        ), "Concurrent source data change; take a consistent fresh snapshot"
        counts[table] = int(restored)
    evidence = {
        "status": "PASS",
        "environment": "local-demo",
        "restore_verified": True,
        "tables": len(tables),
        "record_counts": counts,
        "backup_sha256": hashlib.sha256(backup).hexdigest(),
        "production_modified": False,
    }
    (private / "latest-verification.json").write_text(json.dumps(evidence, indent=2))
    (private / "latest-verification.json").chmod(0o600)
    print(
        json.dumps(
            {
                "status": "PASS",
                "environment": environment,
                "restored_tables": len(tables),
                "preserved_records": sum(counts.values()),
                "backup_file": str(path),
            }
        )
    )
finally:
    subprocess.run(["docker", "rm", "-f", "-v", name], capture_output=True)
