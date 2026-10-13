#!/usr/bin/env python3
"""Owned ARCH-001 PostgreSQL/API lab: no existing volumes or production data."""
import json, os, secrets, shutil, socket, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / "backend/.venv/bin/python"
private = Path(tempfile.mkdtemp(prefix="opscontrol-arch001-"))
private.chmod(0o700)
OUT = Path(os.getenv("ARCH001_EVIDENCE_DIR", "/tmp/opscontrol-arch001-evidence"))
OUT.mkdir(parents=True, exist_ok=True)
name = "opscontrol-arch001-" + secrets.token_hex(5)
env = {
    **os.environ,
    "ENVIRONMENT": "test",
    "OPSCONTROL_ARCH001_ACCEPTANCE": "1",
    "ARCH001_PRIVATE_DIR": str(private),
    "ARCH001_EVIDENCE_DIR": str(OUT),
    "AWS_EC2_METADATA_DISABLED": "true",
}
password = secrets.token_urlsafe(32)
processes = []
started = False
passed = False


def run(args, cwd=ROOT, expected=0):
    p = subprocess.run(
        [str(a) for a in args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=240,
    )
    if p.returncode != expected:
        (private / "failure.log").write_text(p.stdout + "\n" + p.stderr)
        raise RuntimeError(
            "Owned ARCH-001 command failed; private diagnostics retained"
        )
    return p.stdout.strip()


def module(name, *args):
    return run([PYTHON, "-m", name, *args], ROOT / "backend")


def port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


try:
    run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            name,
            "-p",
            "127.0.0.1::5432",
            "-e",
            "POSTGRES_USER=opscontrol",
            "-e",
            "POSTGRES_DB=opscontrol",
            "-e",
            "POSTGRES_PASSWORD=" + password,
            "postgres:17-alpine",
        ]
    )
    started = True
    for _ in range(100):
        if (
            subprocess.run(
                ["docker", "exec", name, "pg_isready", "-U", "opscontrol"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            ).returncode
            == 0
        ):
            break
        time.sleep(0.2)
    else:
        raise RuntimeError("Owned database readiness failed")
    dbport = run(["docker", "port", name, "5432/tcp"]).rsplit(":", 1)[1]
    env["DATABASE_URL"] = (
        f"postgresql+psycopg://opscontrol:{password}@127.0.0.1:{dbport}/opscontrol"
    )
    module("alembic", "upgrade", "0026_managed_telemetry_uat")
    print(module("scripts.arch001_acceptance_probe", "seed"), flush=True)
    module("alembic", "upgrade", "head")
    print(module("alembic", "check"), flush=True)
    print(module("scripts.arch001_acceptance_probe", "migration"), flush=True)
    (
        module("alembic", "downgrade", "0026_managed_telemetry_uat")
        if os.getenv("ARCH001_EMPTY_ONLY") == "1"
        else run(
            [PYTHON, "-m", "alembic", "downgrade", "0026_managed_telemetry_uat"],
            ROOT / "backend",
            expected=1,
        )
    )
    if os.getenv("ARCH001_API_ACCEPTANCE") == "1":
        apiport = port()
        env["ARCH001_API_URL"] = f"http://127.0.0.1:{apiport}"
        log = open(private / "api.log", "w")
        p = subprocess.Popen(
            [
                str(PYTHON),
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(apiport),
                "--no-access-log",
            ],
            cwd=ROOT / "backend",
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        log.close()
        processes.append(p)
        from urllib.request import urlopen

        for _ in range(100):
            try:
                with urlopen(env["ARCH001_API_URL"] + "/health", timeout=1) as response:
                    if response.status == 200:
                        break
            except OSError:
                time.sleep(0.2)
        else:
            raise RuntimeError("Owned API startup failed")
        print(module("scripts.arch001_acceptance_probe", "api"), flush=True)
        if os.getenv("ARCH001_ENGINE_ACCEPTANCE") == "1":
            print(module("scripts.arch001_acceptance_probe", "engines"), flush=True)
    (OUT / "report.json").write_text(
        json.dumps(
            {
                "status": "PASS",
                "origin": "OWNED_POSTGRES_AND_ACTUAL_API",
                "migration": "0027_unified_monitoring",
                "production_modified": False,
            },
            indent=2,
        )
        + "\n"
    )
    passed = True
    print("ARCH-001 OWNED ACCEPTANCE PASS", flush=True)
finally:
    for p in reversed(processes):
        p.terminate()
        try:
            p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait(timeout=10)
    if started:
        subprocess.run(
            ["docker", "rm", "-f", name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    if passed:
        shutil.rmtree(private)
    else:
        print("Private diagnostics:", private, flush=True)
