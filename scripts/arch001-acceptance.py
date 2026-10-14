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
    "OPSCONTROL_NOTIFICATION_THROTTLE_SECONDS": "0",
}
password = secrets.token_urlsafe(32)
processes = []
started = False
target_started = False
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
    original_url = env["DATABASE_URL"]
    run(
        [
            PYTHON,
            "-c",
            "from sqlalchemy import create_engine,text;from app.core.config import settings;e=create_engine(settings.database_url,isolation_level='AUTOCOMMIT');c=e.connect();c.execute(text('CREATE DATABASE arch001_empty'));c.close();e.dispose()",
        ],
        ROOT / "backend",
    )
    env["DATABASE_URL"] = original_url.rsplit("/", 1)[0] + "/arch001_empty"
    module("alembic", "upgrade", "head")
    module("alembic", "downgrade", "0026_managed_telemetry_uat")
    module("alembic", "upgrade", "head")
    module("alembic", "check")
    env["DATABASE_URL"] = original_url
    print(
        "Empty ARCH-001 upgrade/downgrade/upgrade and schema comparison PASS",
        flush=True,
    )
    if os.getenv("ARCH001_API_ACCEPTANCE") == "1":
        uiport = port()
        env["ARCH001_UI_URL"] = f"http://127.0.0.1:{uiport}"
        env["CORS_ORIGINS"] = env["ARCH001_UI_URL"]
        apiport = port()
        env["ARCH001_API_URL"] = f"http://127.0.0.1:{apiport}"
        tls_args = []
        if os.getenv("ARCH001_RUNTIME_ACCEPTANCE") == "1":
            target = name + "-target"
            run(
                [
                    "docker",
                    "create",
                    "--name",
                    target,
                    "--mount",
                    f"type=bind,source={private},target=/fixture,readonly",
                    "--mount",
                    f"type=bind,source={ROOT / 'scripts/uat/native-target.py'},target=/target.py,readonly",
                    "python:3.12-alpine",
                    "python",
                    "/target.py",
                ]
            )
            target_started = True
            run(["docker", "start", target])
            # Docker assigns an address even though the fixture awaits its cert.
            target_ip = run(
                [
                    "docker",
                    "inspect",
                    "-f",
                    "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}",
                    target,
                ]
            )
            run(
                [
                    "openssl",
                    "req",
                    "-x509",
                    "-newkey",
                    "rsa:2048",
                    "-nodes",
                    "-keyout",
                    private / "key.pem",
                    "-out",
                    private / "ca.pem",
                    "-days",
                    "1",
                    "-subj",
                    "/CN=localhost",
                    "-addext",
                    f"subjectAltName=DNS:localhost,IP:127.0.0.1,IP:{target_ip}",
                ]
            )
            (private / "target.json").write_text(
                json.dumps({"http_status": 200, "records": []})
            )
            provider_token = secrets.token_urlsafe(32)
            (private / "provider-token").write_text(provider_token)
            env["ARCH001_PROVIDER_TOKEN"] = provider_token
            env["ARCH001_TARGET_URL"] = f"https://{target_ip}:8443"
            env["OPSCONTROL_NATIVE_ALLOWED_HOSTS"] = target_ip
            env["OPSCONTROL_NATIVE_ALLOWED_CIDRS"] = target_ip + "/32"
            env["OPSCONTROL_NATIVE_ALLOWED_PORTS"] = "8443"
            run(["docker", "start", target])
            env["ARCH001_API_URL"] = f"https://localhost:{apiport}"
            env["SSL_CERT_FILE"] = str(private / "ca.pem")
            env["OPSCONTROL_PUBLIC_INGESTION_URL"] = env["ARCH001_API_URL"]
            env["OPSCONTROL_OTEL_BINARY"] = env.get(
                "OPSCONTROL_OTEL_BINARY", "/tmp/opscontrol-otel-bin/otelcol-contrib"
            )
            tls_args = [
                "--ssl-keyfile",
                str(private / "key.pem"),
                "--ssl-certfile",
                str(private / "ca.pem"),
            ]
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
                *tls_args,
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
                with urlopen(
                    env["ARCH001_API_URL"] + "/health",
                    timeout=1,
                    context=__import__("ssl").create_default_context(
                        cafile=env.get("SSL_CERT_FILE")
                    ),
                ) as response:
                    if response.status == 200:
                        break
            except OSError:
                time.sleep(0.2)
        else:
            raise RuntimeError("Owned API startup failed")
        print(module("scripts.arch001_acceptance_probe", "api"), flush=True)
        if os.getenv("ARCH001_ENGINE_ACCEPTANCE") == "1":
            print(module("scripts.arch001_acceptance_probe", "engines"), flush=True)
            print(module("scripts.arch001_acceptance_probe", "incidents"), flush=True)
        if os.getenv("ARCH001_RUNTIME_ACCEPTANCE") == "1":
            print(module("scripts.arch001_runtime_probe"), flush=True)
        if os.getenv("ARCH001_BROWSER_ACCEPTANCE") == "1":
            env["VITE_API_BASE_URL"] = env["ARCH001_API_URL"]
            env["PLAYWRIGHT_MODULE"] = env.get(
                "PLAYWRIGHT_MODULE",
                "/workspace/.golden-tools/node_modules/playwright/index.mjs",
            )
            run(["npm", "run", "build"], ROOT / "frontend")
            frontend_log = open(private / "frontend.log", "w")
            ui = subprocess.Popen(
                [
                    "npm",
                    "run",
                    "preview",
                    "--",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(uiport),
                    "--strictPort",
                ],
                cwd=ROOT / "frontend",
                env=env,
                stdout=frontend_log,
                stderr=subprocess.STDOUT,
            )
            frontend_log.close()
            processes.append(ui)
            for _ in range(100):
                try:
                    with urlopen(env["ARCH001_UI_URL"], timeout=1) as response:
                        if response.status == 200:
                            break
                except OSError:
                    time.sleep(0.2)
            else:
                raise RuntimeError("Owned frontend startup failed")
            print(
                run(["node", "scripts/arch001_acceptance.mjs"], ROOT / "frontend"),
                flush=True,
            )
            print(
                run(["node", "scripts/access_v15.mjs"], ROOT / "frontend"), flush=True
            )
    (OUT / "report.json").write_text(
        json.dumps(
            {
                "status": "PASS",
                "origin": "OWNED_POSTGRES_AND_ACTUAL_API",
                "migration": "0031_in_app_notifications",
                "production_modified": False,
            },
            indent=2,
        )
        + "\n"
    )
    passed = True
    print("ARCH-001 OWNED ACCEPTANCE PASS", flush=True)
finally:
    # Subprocess timeouts can kill the probe before its agent cleanup executes.
    # Reap only children carrying this owned lab's exact private-directory tag.
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        try:
            child_env = (entry / "environ").read_bytes().split(b"\0")
            child_args = (entry / "cmdline").read_bytes()
        except (FileNotFoundError, PermissionError):
            continue
        if ("ARCH001_PRIVATE_DIR=" + str(private)).encode() in child_env and any(
            name in child_args
            for name in (
                b"opscontrol_agent.py",
                b"scripts.run_collector_worker",
                b"otelcol-contrib",
            )
        ):
            try:
                os.kill(int(entry.name), __import__("signal").SIGTERM)
            except ProcessLookupError:
                pass
    for p in reversed(processes):
        p.terminate()
        try:
            p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait(timeout=10)
    if target_started:
        subprocess.run(
            ["docker", "rm", "-f", name + "-target"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    if started:
        subprocess.run(
            ["docker", "rm", "-f", "-v", name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    if passed:
        shutil.rmtree(private)
    else:
        print("Private diagnostics:", private, flush=True)
