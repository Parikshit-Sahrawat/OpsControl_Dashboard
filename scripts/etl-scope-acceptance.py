#!/usr/bin/env python3
"""OC-ETL-002: disposable PostgreSQL, real migrations and authenticated HTTP."""
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import time
import tempfile
import re
from urllib.request import urlopen

root = Path(__file__).resolve().parents[1]
out = Path(os.environ["ETL_SCOPE_EVIDENCE_DIR"]).resolve()
out.mkdir(parents=True, exist_ok=True)
python = root / "backend/.venv/bin/python"
name = "oc-etl002-" + secrets.token_hex(6)
password = secrets.token_urlsafe(32)
docker = ["docker", "--host=unix:///var/run/docker.sock"]
env = {
    k: v
    for k, v in os.environ.items()
    if k
    not in {
        "DOCKER_HOST",
        "DOCKER_CONTEXT",
        "DOCKER_TLS",
        "DOCKER_TLS_VERIFY",
        "DOCKER_CERT_PATH",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
    }
}
env.update(
    ENVIRONMENT="test",
    OPSCONTROL_ETL_SCOPE_ACCEPTANCE="1",
    OPSCONTROL_V16_ACCEPTANCE="1",
    ETL_SCOPE_EVIDENCE_DIR=str(out),
    POSTGRES_PASSWORD=password,
    AWS_EC2_METADATA_DISABLED="true",
)
commands = []
api = None
ui = None
started = False
success = False
identity = None
authority_private = tempfile.TemporaryDirectory(prefix="etl-authority-contract-")
authority_store = Path(authority_private.name) / "public-trust.json"
authority_store.write_text(json.dumps({"version": 1, "issuers": {}}))
authority_store.chmod(0o600)
env["OPSCONTROL_ETL_AUTHORITY_TRUST_STORE"] = str(authority_store)


def run(args, label, cwd=root):
    result = subprocess.run(
        list(map(str, args)),
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    (out / (label + ".log")).write_text(
        (result.stdout + "\n" + result.stderr).replace(password, "[REDACTED]")
    )
    commands.append(
        {
            "command": list(map(str, args)),
            "cwd": str(cwd),
            "exit_code": result.returncode,
            "log": label + ".log",
        }
    )
    if result.returncode:
        raise RuntimeError(label + " failed; sanitized log retained")
    return result.stdout.strip()


try:
    run(
        [
            *docker,
            "run",
            "-d",
            "--name",
            name,
            "--label",
            "task=OC-ETL-002",
            "--tmpfs",
            "/var/lib/postgresql/data",
            "-p",
            "127.0.0.1::5432",
            "-e",
            "POSTGRES_PASSWORD",
            "-e",
            "POSTGRES_DB=etl_scope",
            "postgres:17-alpine",
        ],
        "postgres-start",
    )
    started = True
    for _ in range(100):
        if (
            subprocess.run(
                [*docker, "exec", name, "pg_isready", "-U", "postgres"],
                capture_output=True,
            ).returncode
            == 0
        ):
            break
        time.sleep(0.2)
    else:
        raise RuntimeError("Owned PostgreSQL readiness timeout")
    port = run([*docker, "port", name, "5432/tcp"], "postgres-port").rsplit(":", 1)[1]
    identity = run(
        [*docker, "inspect", "--format", "{{.Id}} {{.Image}}", name],
        "postgres-identity",
    )
    env["DATABASE_URL"] = (
        f"postgresql+psycopg://postgres:{password}@127.0.0.1:{port}/etl_scope"
    )
    run(
        [python, "-m", "alembic", "upgrade", "head"],
        "migration-upgrade",
        root / "backend",
    )
    run([python, "-m", "alembic", "check"], "migration-model-check", root / "backend")
    env["ETL_SCOPE_CONTAINER"] = name
    run(
        [python, "-m", "scripts.etl_rollback_probe"],
        "rollback-preservation",
        root / "backend",
    )
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        apiport = s.getsockname()[1]
    env["ETL_SCOPE_API_URL"] = f"http://127.0.0.1:{apiport}"
    if os.getenv("ETL_WORKFLOW_UI_ACCEPTANCE") == "1":
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            uiport = sock.getsockname()[1]
        env["ETL_WORKFLOW_UI_URL"] = f"http://127.0.0.1:{uiport}"
        env["VITE_API_BASE_URL"] = env["ETL_SCOPE_API_URL"]
        env["CORS_ORIGINS"] = env["ETL_WORKFLOW_UI_URL"]
    with (out / "api.log").open("w") as log:
        api = subprocess.Popen(
            [
                str(python),
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(apiport),
                "--no-access-log",
            ],
            cwd=root / "backend",
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
    for _ in range(100):
        try:
            with urlopen(env["ETL_SCOPE_API_URL"] + "/health", timeout=1) as response:
                if response.status == 200:
                    break
        except OSError:
            time.sleep(0.2)
    else:
        raise RuntimeError("Owned API readiness timeout")
    if os.getenv("ETL_WORKFLOW_UI_ACCEPTANCE") == "1":
        with (out / "ui.log").open("w") as log:
            ui = subprocess.Popen(
                [
                    "node",
                    "node_modules/vite/bin/vite.js",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(uiport),
                    "--strictPort",
                ],
                cwd=root / "frontend",
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
        for _ in range(100):
            try:
                with urlopen(env["ETL_WORKFLOW_UI_URL"], timeout=1) as response:
                    if response.status == 200:
                        break
            except OSError:
                time.sleep(0.2)
        else:
            raise RuntimeError("Owned UI readiness timeout")
    run(
        [
            python,
            "-m",
            "unittest",
            *(
                os.environ["ETL_SCOPE_TEST_TARGETS"].split(",")
                if os.environ.get("ETL_SCOPE_TEST_TARGETS")
                else [
                    "tests.test_etl_workflow_scope",
                    "tests.test_etl_workflow_foundation",
                    "tests.test_etl_dag_concurrency",
                    "tests.test_etl_native_binding_contract",
                    "tests.test_etl_binding_lifecycle",
                    "tests.test_etl_authority_writer",
                    *(
                        ["tests.test_etl_workflow_ui"]
                        if os.getenv("ETL_WORKFLOW_UI_ACCEPTANCE") == "1"
                        else []
                    ),
                    "tests.test_sprint08_rbac",
                ]
            ),
            "-v",
        ],
        "regressions",
        root / "backend",
    )
    success = True
finally:
    if ui:
        ui.terminate()
        try:
            ui.wait(timeout=10)
        except subprocess.TimeoutExpired:
            ui.kill()
            ui.wait(timeout=5)
    if api:
        api.terminate()
        try:
            api.wait(timeout=15)
        except subprocess.TimeoutExpired:
            api.kill()
            api.wait(timeout=5)
    authority_private.cleanup()
    # Even failed docker run may leave the exact task-created name allocated.
    exists = (
        subprocess.run([*docker, "inspect", name], capture_output=True).returncode == 0
    )
    cleanup = (
        subprocess.run(
            [*docker, "rm", "-f", "-v", name], capture_output=True, text=True
        )
        if exists
        else None
    )
    remaining = (
        subprocess.run([*docker, "inspect", name], capture_output=True).returncode == 0
    )
    # Playwright failure call logs can include transient synthetic bearer headers.
    # Preserve redacted failures, never exported credentials.
    redacted = 0
    for artifact in [*out.rglob("*.log"), *out.rglob("*.json")]:
        content = artifact.read_text()
        content, count = re.subn(
            r"(?i)(Bearer\s+)[A-Za-z0-9._~+/-]+=*", r"\1[REDACTED]", content
        )
        if count:
            artifact.write_text(content)
            redacted += count
    (out / "LOG_REDACTION.json").write_text(
        json.dumps({"synthetic_bearer_occurrences_redacted": redacted})
    )
    (out / "RESULTS.json").write_text(
        json.dumps(
            {
                "status": "PASS" if success and not remaining else "FAIL",
                "source_sha": subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], cwd=root, text=True
                ).strip(),
                "working_tree_diff": subprocess.check_output(
                    ["git", "diff", "--name-only"], cwd=root, text=True
                ).splitlines(),
                "commands": commands,
                "container": name,
                "identity": identity,
                "remaining_container": remaining,
                "cleanup_exit": None if cleanup is None else cleanup.returncode,
                "api_stopped": api is None or api.poll() is not None,
                "ui_stopped": ui is None or ui.poll() is not None,
                "volumes": "tmpfs only; rm -v scoped to owned container",
                "production_or_uat_access": False,
            },
            indent=2,
        )
        + "\n"
    )
