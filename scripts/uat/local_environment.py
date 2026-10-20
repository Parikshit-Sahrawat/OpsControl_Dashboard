#!/usr/bin/env python3
"""Operate only the locally owned Sprint 14 UAT Compose project."""

import argparse
import json
import hashlib
import re
import os
from pathlib import Path
import secrets
import signal
import socket
import subprocess
import sys
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
STATE = Path(
    os.environ.get("OPSCONTROL_UAT_STATE_DIR", f"/tmp/opscontrol-s14-uat-{os.getuid()}")
)
BASE = ROOT / "docker-compose.demo.yml"
FROZEN_HEAD = os.environ.get("OPSCONTROL_UAT_EXPECTED_HEAD", "")
if not re.fullmatch(r"[0-9a-f]{40}", FROZEN_HEAD):
    raise SystemExit(
        "Set OPSCONTROL_UAT_EXPECTED_HEAD to the exact reviewed source commit"
    )


def source_fingerprint():
    files = {}
    for folder in (
        "backend/app",
        "backend/tests",
        "backend/migrations",
        "frontend/src",
        "frontend/scripts",
        "agent",
        "scripts",
    ):
        for path in sorted((ROOT / folder).rglob("*")):
            if path.is_file() and path.suffix in {".py", ".js", ".jsx", ".mjs", ".sh"}:
                files[str(path.relative_to(ROOT))] = hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
    return hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()


def port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def config():
    if STATE.is_symlink():
        raise SystemExit("UAT state path must not be a symlink")
    path = STATE / "settings.json"
    if path.is_symlink() or not path.is_file():
        raise SystemExit(f"No owned UAT state at {path}; run start first")
    settings = json.loads(path.read_text())
    if (
        not settings.get("project", "").startswith("opscontrol-s14-uat-")
        or settings.get("commit") != FROZEN_HEAD
        or settings.get("repository_root") != str(ROOT.resolve())
    ):
        raise SystemExit("Refusing unrelated Compose project or source state")
    return settings


def stop_hosts():
    for name, signature in (
        ("api", "uvicorn app.main:app"),
        ("frontend", "frontend/node_modules/.bin/vite"),
    ):
        pidfile = STATE / f"{name}.pid"
        if not pidfile.exists():
            continue
        pid = int(pidfile.read_text())
        try:
            command = (
                Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode()
            )
        except FileNotFoundError:
            pidfile.unlink()
            continue
        expected_cwd = ROOT / ("backend" if name == "api" else "frontend")
        if (
            signature not in command
            or os.getpgid(pid) != pid
            or Path(f"/proc/{pid}/cwd").resolve() != expected_cwd.resolve()
        ):
            raise SystemExit(f"Refusing to stop unrelated PID {pid}; inspect {pidfile}")
        os.killpg(pid, signal.SIGTERM)
        pidfile.unlink()


def compose(settings, *args, check=True, input=None):
    command = [
        "docker",
        "compose",
        "-p",
        settings["project"],
        "-f",
        str(BASE),
        "-f",
        str(STATE / "override.yml"),
        *args,
    ]
    return subprocess.run(command, cwd=ROOT, check=check, text=True, input=input)


def start():
    current = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    if current != FROZEN_HEAD:
        raise SystemExit(
            f"Refusing UAT startup: expected frozen main {FROZEN_HEAD}, found {current}"
        )
    if STATE.exists() and any(STATE.iterdir()):
        settings = config()
        if settings.get("source_sha256") != source_fingerprint():
            raise SystemExit(
                "Source changed; stop the owned project and use a fresh UAT state directory"
            )
        if settings["commit"] != current:
            raise SystemExit(
                "UAT state belongs to another commit; stop/reset it before switching baselines"
            )
        if all((STATE / f"{name}.pid").exists() for name in ("api", "frontend")):
            try:
                for name in ("api", "frontend"):
                    os.kill(int((STATE / f"{name}.pid").read_text()), 0)
                print(
                    f'Already running: API http://127.0.0.1:{settings["api_port"]}  UI http://127.0.0.1:{settings["ui_port"]}'
                )
                return
            except ProcessLookupError:
                raise SystemExit(
                    "Stale UAT process state; inspect/reset only this owned project"
                )
    else:
        if STATE.is_symlink():
            raise SystemExit("UAT state path must not be a symlink")
        STATE.mkdir(mode=0o700, parents=True, exist_ok=True)
        STATE.chmod(0o700)
        settings = {
            "project": "opscontrol-s14-uat-" + secrets.token_hex(4),
            "commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "repository_root": str(ROOT.resolve()),
            "source_sha256": source_fingerprint(),
            "api_port": port(),
            "ui_port": port(),
            "db_port": port(),
        }
        while settings["ui_port"] == settings["api_port"]:
            settings["ui_port"] = port()
        db_password = secrets.token_urlsafe(36)
        (STATE / "admin-password").write_text(secrets.token_urlsafe(36))
        (STATE / "db-password").write_text(db_password)
        (STATE / "uat-users.json").write_text(
            json.dumps(
                {
                    "uat-viewer-a": secrets.token_urlsafe(30),
                    "uat-admin-b": secrets.token_urlsafe(30),
                    "uat-operator-ab": secrets.token_urlsafe(30),
                }
            )
        )
        for name in ("admin-password", "db-password", "uat-users.json"):
            (STATE / name).chmod(0o600)
        (STATE / "override.yml").write_text(
            f"""services:
  postgres:
    image: postgres:17-alpine
    volumes: !override []
    environment:
      POSTGRES_PASSWORD: {db_password}
    ports: !override
      - "127.0.0.1:{settings["db_port"]}:5432"
  api:
    environment:
      DATABASE_URL: postgresql+psycopg://opscontrol:{db_password}@postgres:5432/opscontrol
      CORS_ORIGINS: http://127.0.0.1:{settings["ui_port"]}
    volumes: !override
      - "{STATE}/admin-password:/run/secrets/demo_admin_password:ro"
    ports: !override
      - "127.0.0.1:{settings["api_port"]}:8000"
  frontend:
    build:
      args:
        VITE_API_BASE_URL: http://127.0.0.1:{settings["api_port"]}
    ports: !override
      - "127.0.0.1:{settings["ui_port"]}:80"
"""
        )
        (STATE / "override.yml").chmod(0o600)
        (STATE / "settings.json").write_text(json.dumps(settings, indent=2))
        (STATE / "settings.json").chmod(0o600)
    if "db_port" not in settings:
        raise SystemExit(
            "Incomplete UAT state from an earlier attempt; run reset, then start"
        )
    compose(settings, "up", "-d", "postgres")
    db_url = f'postgresql+psycopg://opscontrol:{(STATE / "db-password").read_text()}@127.0.0.1:{settings["db_port"]}/opscontrol'
    environment = os.environ.copy()
    environment.update(
        {
            "DATABASE_URL": db_url,
            "ENVIRONMENT": "demo",
            "AWS_EC2_METADATA_DISABLED": "true",
            "OPSCONTROL_DEMO_PASSWORD_FILE": str(STATE / "admin-password"),
            "CORS_ORIGINS": f'http://127.0.0.1:{settings["ui_port"]}',
        }
    )
    python = Path(
        os.environ.get(
            "OPSCONTROL_UAT_PYTHON",
            str(ROOT / "backend/.venv/bin/python"),
        )
    )
    node_modules = Path(
        os.environ.get(
            "OPSCONTROL_UAT_NODE_MODULES",
            str(ROOT / "frontend/node_modules"),
        )
    )
    frontend_modules = ROOT / "frontend/node_modules"
    if not python.is_file() or (
        not frontend_modules.exists() and not node_modules.is_dir()
    ):
        raise SystemExit(
            "Installed backend Python/frontend Node dependencies unavailable; set OPSCONTROL_UAT_PYTHON and OPSCONTROL_UAT_NODE_MODULES"
        )
    for _ in range(30):
        probe = subprocess.run(
            [
                "docker",
                "compose",
                "-p",
                settings["project"],
                "-f",
                str(BASE),
                "-f",
                str(STATE / "override.yml"),
                "exec",
                "-T",
                "postgres",
                "pg_isready",
                "-U",
                "opscontrol",
                "-d",
                "opscontrol",
            ],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if probe.returncode == 0:
            break
        time.sleep(1)
    else:
        raise SystemExit("Owned PostgreSQL did not become ready")
    subprocess.run(
        [str(python), "-m", "alembic", "upgrade", "head"],
        cwd=ROOT / "backend",
        env=environment,
        check=True,
    )
    subprocess.run(
        [str(python), "-m", "scripts.bootstrap_public_demo"],
        cwd=ROOT / "backend",
        env=environment,
        check=True,
    )
    if not frontend_modules.exists():
        frontend_modules.symlink_to(node_modules, target_is_directory=True)
    services = (
        (
            "api",
            [
                str(python),
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(settings["api_port"]),
            ],
            ROOT / "backend",
        ),
        (
            "frontend",
            [
                str(frontend_modules / ".bin/vite"),
                "--host",
                "127.0.0.1",
                "--port",
                str(settings["ui_port"]),
                "--strictPort",
            ],
            ROOT / "frontend",
        ),
    )
    environment["VITE_API_BASE_URL"] = f'http://127.0.0.1:{settings["api_port"]}'
    for name, command, cwd in services:
        log = (STATE / f"{name}.log").open("a")
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=environment,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        (STATE / f"{name}.pid").write_text(str(process.pid))
        log.close()
    for _ in range(60):
        try:
            with urlopen(
                f'http://127.0.0.1:{settings["api_port"]}/health', timeout=1
            ) as api, urlopen(
                f'http://127.0.0.1:{settings["ui_port"]}/', timeout=1
            ) as ui:
                if api.status == ui.status == 200:
                    break
        except OSError:
            time.sleep(1)
    else:
        raise SystemExit(f"API/UI startup failed; inspect {STATE}/*.log")
    print(
        f'API http://127.0.0.1:{settings["api_port"]}  UI http://127.0.0.1:{settings["ui_port"]}'
    )
    print(f'Owned project {settings["project"]}; credentials in {STATE} (mode 0600)')


def seed():
    settings = config()
    users = (STATE / "uat-users.json").read_text()
    env = os.environ.copy()
    env.update(
        {
            "DATABASE_URL": f'postgresql+psycopg://opscontrol:{(STATE / "db-password").read_text()}@127.0.0.1:{settings["db_port"]}/opscontrol',
            "ENVIRONMENT": "demo",
            "OPSCONTROL_UAT_FIXTURES": "1",
            "OPSCONTROL_UAT_USERS_JSON": users,
            "PYTHONPATH": str(ROOT / "backend"),
        }
    )
    result = subprocess.run(
        [
            os.environ.get(
                "OPSCONTROL_UAT_PYTHON",
                str(ROOT / "backend/.venv/bin/python"),
            ),
            str(ROOT / "scripts/uat/seed_readiness.py"),
        ],
        cwd=ROOT / "backend",
        env=env,
        check=False,
    )
    if result.returncode:
        raise SystemExit(result.returncode)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=("start", "seed", "status", "logs", "stop", "reset")
    )
    args = parser.parse_args()
    if args.action == "start":
        start()
    elif args.action == "seed":
        seed()
    else:
        settings = config()
        if args.action == "status":
            compose(settings, "ps")
            print(
                f'API http://127.0.0.1:{settings["api_port"]}  UI http://127.0.0.1:{settings["ui_port"]}'
            )
            for name in ("api", "frontend"):
                pidfile = STATE / f"{name}.pid"
                if pidfile.exists():
                    try:
                        os.kill(int(pidfile.read_text()), 0)
                        print(f"{name}: running")
                    except ProcessLookupError:
                        print(f"{name}: stopped")
        elif args.action == "logs":
            compose(settings, "logs", "--no-color", "--tail", "60", "postgres")
            for name in ("api", "frontend"):
                print(f"{name} log: {STATE / (name + '.log')}")
        elif args.action == "stop":
            stop_hosts()
            compose(settings, "stop", "postgres")
        elif args.action == "reset":
            stop_hosts()
            compose(settings, "down", "--volumes", "--remove-orphans")
            modules = ROOT / "frontend/node_modules"
            if (
                modules.is_symlink()
                and modules.resolve()
                == Path(
                    os.environ.get(
                        "OPSCONTROL_UAT_NODE_MODULES",
                        str(ROOT / "frontend/node_modules"),
                    )
                ).resolve()
            ):
                modules.unlink()
            for name in (
                "settings.json",
                "override.yml",
                "admin-password",
                "db-password",
                "uat-users.json",
                "api.log",
                "frontend.log",
                "http-smoke.txt",
                "browser-smoke.txt",
                "schema-check.txt",
                "demo-admin-navigation.png",
                "uat-viewer-a-navigation.png",
            ):
                (STATE / name).unlink(missing_ok=True)
            STATE.rmdir()
            print(
                "Removed only the owned UAT project, anonymous volume and private state"
            )


if __name__ == "__main__":
    main()
