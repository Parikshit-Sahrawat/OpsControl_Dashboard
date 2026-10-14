#!/usr/bin/env python3
"""Owned PostgreSQL/TLS/OTel/browser lab; never touches existing volumes or production."""
import hashlib, json, os, secrets, shutil, socket, ssl, subprocess, sys, tempfile, time, uuid
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[2]
PYTHON = ROOT / "backend/.venv/bin/python"
private = Path(tempfile.mkdtemp(prefix="opscontrol-uat-"))
private.chmod(0o700)
OUT = Path(os.getenv("UAT_EVIDENCE_DIR", "/tmp/opscontrol-consolidated-uat-evidence"))
OUT.mkdir(parents=True, exist_ok=True)
name = "opscontrol-uat-" + secrets.token_hex(5)
password = secrets.token_urlsafe(32)
admin_password = secrets.token_urlsafe(32)
started = False
processes = []
success = False
binary = os.getenv("OPSCONTROL_OTEL_BINARY", "/tmp/opscontrol-otel-bin/otelcol-contrib")
checks = []


def port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


apiport, uiport, otlpport = port(), port(), port()
env = {
    **os.environ,
    "ENVIRONMENT": "test",
    "AWS_EC2_METADATA_DISABLED": "true",
    "OPSCONTROL_OTEL_BINARY": binary,
    "OPSCONTROL_PUBLIC_INGESTION_URL": f"https://localhost:{apiport}",
    "UAT_PRIVATE_DIR": str(private),
    "UAT_EVIDENCE_DIR": str(OUT),
    "UAT_BASE_URL": f"https://localhost:{apiport}",
    "UAT_UI_URL": f"http://127.0.0.1:{uiport}",
    "UAT_OTLP_PORT": str(otlpport),
    "CORS_ORIGINS": f"http://127.0.0.1:{uiport}",
    "OPSCONTROL_NOTIFICATION_THROTTLE_SECONDS": "0",
}


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
        (private / "failed.log").write_text(p.stdout + "\n" + p.stderr)
        raise RuntimeError("Owned UAT command failed; private diagnostics retained")
    return p.stdout.strip()


def start(args, log, cwd=ROOT):
    stream = open(private / log, "w")
    p = subprocess.Popen(
        [str(a) for a in args],
        cwd=cwd,
        env=env,
        stdout=stream,
        stderr=subprocess.STDOUT,
    )
    stream.close()
    processes.append(p)
    return p


def wait(url, context=None):
    for _ in range(100):
        try:
            with urlopen(url, context=context, timeout=1) as r:
                if r.status == 200:
                    return
        except OSError:
            time.sleep(0.2)
    raise RuntimeError("UAT service readiness failed")


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
    dbport = run(["docker", "port", name, "5432/tcp"]).rsplit(":", 1)[1]
    env["DATABASE_URL"] = (
        f"postgresql+psycopg://opscontrol:{password}@127.0.0.1:{dbport}/opscontrol"
    )
    run(
        [PYTHON, "-m", "alembic", "upgrade", "0025_provider_department_rbac"],
        ROOT / "backend",
    )
    # Preserve a populated old customer/user before the additive update.
    ids = {
        "admin": str(uuid.uuid4()),
        "organization": str(uuid.uuid4()),
        "other": str(uuid.uuid4()),
        "password": admin_password,
    }
    (private / "fixture.json").write_text(json.dumps(ids))
    code = """
import json,os
from pathlib import Path
from sqlalchemy import create_engine,text
from app.core.config import settings
from app.security.passwords import hash_password
f=json.loads((Path(os.environ['UAT_PRIVATE_DIR'])/'fixture.json').read_text())
with create_engine(settings.database_url).begin() as c:
 c.execute(text("INSERT INTO users(id,service_provider_id,username,full_name,password_hash,active,platform_admin,created_at) VALUES (:id,(SELECT id FROM service_providers LIMIT 1),'uat-admin','UAT Administrator',:h,true,true,now())"),{'id':f['admin'],'h':hash_password(f['password'])})
 for id,name in [(f['organization'],'Fictional North Operations'),(f['other'],'Fictional South Operations')]:
  c.execute(text('INSERT INTO organizations(id,name,code,active,created_at,updated_at) VALUES (:id,:name,:code,true,now(),now())'),{'id':id,'name':name,'code':id[:8]})
"""
    run([PYTHON, "-c", code], ROOT / "backend")
    run([PYTHON, "-m", "alembic", "upgrade", "head"], ROOT / "backend")
    run([PYTHON, "-m", "alembic", "check"], ROOT / "backend")
    # Empty new tables can safely roll back one revision; archived records remain.
    run(
        [PYTHON, "-m", "alembic", "downgrade", "0025_provider_department_rbac"],
        ROOT / "backend",
    )
    run([PYTHON, "-m", "alembic", "upgrade", "head"], ROOT / "backend")
    run([PYTHON, "-m", "alembic", "check"], ROOT / "backend")
    checks.append(
        "Populated 0025→0026 and empty additive downgrade/upgrade; full schema zero drift"
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
            "subjectAltName=DNS:localhost,IP:127.0.0.1",
        ]
    )
    pub = subprocess.run(
        ["openssl", "x509", "-in", str(private / "ca.pem"), "-pubkey", "-noout"],
        capture_output=True,
        check=True,
    ).stdout
    der = subprocess.run(
        ["openssl", "pkey", "-pubin", "-outform", "DER"],
        input=pub,
        capture_output=True,
        check=True,
    ).stdout
    env["UAT_TLS_SPKI"] = (
        __import__("base64").b64encode(hashlib.sha256(der).digest()).decode()
    )
    env["NODE_EXTRA_CA_CERTS"] = str(private / "ca.pem")
    env["SSL_CERT_FILE"] = str(private / "ca.pem")
    env["REQUESTS_CA_BUNDLE"] = str(private / "ca.pem")
    env["UAT_ADMIN_PASSWORD_FILE"] = str(private / "admin-password")
    (private / "admin-password").write_text(admin_password)
    start(
        [
            PYTHON,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            apiport,
            "--ssl-keyfile",
            private / "key.pem",
            "--ssl-certfile",
            private / "ca.pem",
        ],
        "api.log",
        ROOT / "backend",
    )
    wait(
        f"https://localhost:{apiport}/health",
        ssl.create_default_context(cafile=str(private / "ca.pem")),
    )
    print("Owned PostgreSQL migration and real TLS API ready", flush=True)
    run([PYTHON, "-m", "scripts.consolidated_uat_probe"], ROOT / "backend")
    checks.append(
        "Scoped methods, one-time enrollment, identity, OTLP reception, sustained alerts and notification queue"
    )
    if os.getenv("UAT_BROWSER_ACCEPTANCE") == "1":
        env["VITE_API_BASE_URL"] = f"https://localhost:{apiport}"
        env.setdefault(
            "PLAYWRIGHT_MODULE",
            "/workspace/.golden-tools/node_modules/playwright/index.mjs",
        )
        env.setdefault("PLAYWRIGHT_CHROMIUM_EXECUTABLE", "/usr/bin/chromium")
        start(
            [
                "node",
                "node_modules/vite/bin/vite.js",
                "--host",
                "127.0.0.1",
                "--port",
                uiport,
                "--strictPort",
            ],
            "frontend.log",
            ROOT / "frontend",
        )
        wait(f"http://127.0.0.1:{uiport}")
        run(["node", "frontend/scripts/consolidated_uat.mjs"])
        checks.append(
            "Actual authenticated Chromium organization/access/collector/method/alerts/responsive journeys"
        )
    run(
        [PYTHON, "-m", "alembic", "downgrade", "0025_provider_department_rbac"],
        ROOT / "backend",
        expected=1,
    )
    checks.append("Populated telemetry downgrade refuses destructive rollback")
    report = {
        "status": "PASS",
        "checks": checks,
        "origin": "OWNED_POSTGRES_TLS_AND_UPSTREAM_OTEL",
        "production_modified": False,
        "limitations": [
            "Native Windows service execution requires target-host UAT",
            "No remote installation channel",
            "Third requested resource tab remains undefined",
        ],
    }
    (OUT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    success = True
    print("CONSOLIDATED UAT ACCEPTANCE PASS", flush=True)
finally:
    for p in reversed(processes):
        p.terminate()
        try:
            p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait()
    if started:
        subprocess.run(
            ["docker", "rm", "-f", "-v", name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    if success:
        shutil.rmtree(private)
    else:
        print("Private UAT diagnostics:", private, file=sys.stderr)
