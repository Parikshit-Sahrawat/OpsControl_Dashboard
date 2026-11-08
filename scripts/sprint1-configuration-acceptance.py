#!/usr/bin/env python3
"""Owned PostgreSQL17 + actual HTTP: source revision and integration contract."""

import os
import json
import secrets
import socket
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get("S01_EVIDENCE_DIR", "/tmp/pr89-configuration"))
OUT.mkdir(parents=True, exist_ok=True)
private = Path(tempfile.mkdtemp(prefix="pr89-configuration-"))
private.chmod(0o700)
name = "opscontrol-v16-" + secrets.token_hex(6)
password = secrets.token_urlsafe(32)
api = None
with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
env = dict(
    os.environ,
    ENV="test",
    ENVIRONMENT="test",
    AWS_EC2_METADATA_DISABLED="true",
    OPSCONTROL_ETL_SCOPE_ACCEPTANCE="1",
    S01_CONFIGURATION_ACCEPTANCE="1",
    ETL_SCOPE_API_URL=f"http://127.0.0.1:{port}",
    S01_EVIDENCE_DIR=str(OUT),
    ETL_SCOPE_EVIDENCE_DIR=str(OUT),
    V16_OWNED_CONTAINER=name,
)
python = str(ROOT / "backend/.venv/bin/python")


def run(args, label, cwd=ROOT):
    result = subprocess.run(
        [str(a) for a in args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=240,
    )
    (OUT / (label + ".log")).write_text(
        (result.stdout + "\n" + result.stderr).replace(password, "[REDACTED]")
    )
    print(label, "exit", result.returncode, flush=True)
    if result.returncode:
        raise RuntimeError(label + " failed; see redacted log")
    return result.stdout.strip()


try:
    run(
        [
            "docker",
            "run",
            "--detach",
            "--name",
            name,
            "--tmpfs",
            "/var/lib/postgresql/data",
            "-p",
            "127.0.0.1::5432",
            "-e",
            "POSTGRES_USER=opscontrol",
            "-e",
            "POSTGRES_DB=opscontrol",
            "-e",
            "POSTGRES_PASSWORD=" + password,
            "postgres:17-alpine",
        ],
        "postgres-start",
    )
    for _ in range(120):
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
        raise RuntimeError("PostgreSQL readiness failed")
    mapped = run(["docker", "port", name, "5432/tcp"], "postgres-port").split(":")[-1]
    env["DATABASE_URL"] = (
        f"postgresql+psycopg://opscontrol:{password}@127.0.0.1:{mapped}/opscontrol"
    )
    run(
        [
            "docker",
            "exec",
            name,
            "psql",
            "-U",
            "opscontrol",
            "-Atc",
            "select version()",
        ],
        "postgres-version",
    )
    run([python, "-m", "alembic", "upgrade", "head"], "fresh-upgrade", ROOT / "backend")
    run(
        [python, "-m", "alembic", "downgrade", "0041_etl_authority_writer"],
        "empty-safe-downgrade",
        ROOT / "backend",
    )
    run(
        [python, "-m", "alembic", "upgrade", "head"],
        "forward-reupgrade",
        ROOT / "backend",
    )
    run([python, "-m", "alembic", "check"], "schema-drift", ROOT / "backend")

    def start_api():
        global api
        with (private / "api.log").open("a") as log:
            api = subprocess.Popen(
                [
                    python,
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                    "--no-access-log",
                ],
                cwd=ROOT / "backend",
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
        for _ in range(100):
            try:
                with urlopen(
                    env["ETL_SCOPE_API_URL"] + "/health", timeout=1
                ) as response:
                    if response.status == 200:
                        break
            except Exception:
                time.sleep(0.2)
        else:
            raise RuntimeError("API readiness failed")

    start_api()
    targets = os.environ.get(
        "S01_TEST_TARGETS",
        "tests.test_source_configuration_contract,tests.test_etl_workflow_scope,tests.test_etl_dag_concurrency",
    ).split(",")
    run(
        [python, "-m", "unittest", *targets, "-v"],
        "authenticated-contracts",
        ROOT / "backend",
    )
    # Deterministic process death at a DB-instrumented pre-ledger boundary;
    # then retry, kill after independently visible commit, restart and replay.
    state = private / "restart-state.json"
    run(
        [
            python,
            "-m",
            "scripts.source_configuration_restart_probe",
            "interrupt",
            state,
            api.pid,
        ],
        "api-sigkill-before-ledger",
        ROOT / "backend",
    )
    api.wait(timeout=10)
    start_api()
    run(
        [python, "-m", "scripts.source_configuration_restart_probe", "recover", state],
        "api-restart-recover",
        ROOT / "backend",
    )
    api.kill()
    api.wait(timeout=10)
    start_api()
    run(
        [python, "-m", "scripts.source_configuration_restart_probe", "replay", state],
        "api-restart-postcommit-replay",
        ROOT / "backend",
    )
    # Refusing the new metadata fence downgrade must preserve the entire schema,
    # rows, revision and function definitions, not merely return an error.
    import hashlib

    def dump_state():
        dumped = subprocess.check_output(
            [
                "docker",
                "exec",
                name,
                "pg_dump",
                "-U",
                "opscontrol",
                "--no-owner",
                "--no-privileges",
                "opscontrol",
            ],
            text=True,
        )
        return "\n".join(
            line
            for line in dumped.splitlines()
            if not line.startswith(("\\restrict ", "\\unrestrict "))
        )

    before = dump_state()
    refusal = subprocess.run(
        [python, "-m", "alembic", "downgrade", "0042_source_configuration"],
        cwd=ROOT / "backend",
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    (OUT / "context-fence-populated-refusal.log").write_text(
        refusal.stderr.replace(password, "[REDACTED]")
    )
    assert (
        refusal.returncode != 0
        and "Unsafe populated ETL downgrade blocked before DDL" in refusal.stderr
    )
    after = dump_state()
    assert before == after, (
        "Refused0043 downgrade changed data/schema/function definitions"
    )
    (OUT / "context-fence-preservation.json").write_text(
        json.dumps(
            {
                "status": "PASS",
                "refused_exit": refusal.returncode,
                "target": "0042_source_configuration",
                "before_sha256": hashlib.sha256(before.encode()).hexdigest(),
                "after_sha256": hashlib.sha256(after.encode()).hexdigest(),
                "whole_dump_unchanged": True,
            },
            indent=2,
        )
    )
    run(
        [python, "scripts/ci/postgres_restore.py", name, OUT / "backup-restore.json"],
        "backup-restore",
    )
finally:
    if api:
        api.terminate()
        try:
            api.wait(timeout=10)
        except subprocess.TimeoutExpired:
            api.kill()
            api.wait()
    if (private / "api.log").exists():
        (OUT / "api.log").write_text(
            (private / "api.log").read_text().replace(password, "[REDACTED]")
        )
    removed = (
        subprocess.run(
            ["docker", "rm", "-f", "-v", name], capture_output=True
        ).returncode
        == 0
    )
    import shutil

    shutil.rmtree(private)
    (OUT / "cleanup.json").write_text(
        json.dumps(
            dict(
                container=name,
                removed=removed,
                api_stopped=api is None or api.poll() is not None,
                private_removed=not private.exists(),
                storage="tmpfs; not disk-crash durability certification",
            ),
            indent=2,
        )
    )
