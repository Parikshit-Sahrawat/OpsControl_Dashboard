#!/usr/bin/env python3
"""Owned disposable PostgreSQL/API/UI fixture. Never touches an existing database."""
import json, os, secrets, socket, subprocess, tempfile, time, uuid, hashlib, sys, shutil
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / "backend/.venv/bin/python"
private = Path(tempfile.mkdtemp(prefix="opscontrol-access-"))
private.chmod(0o700)
OUT = Path(os.getenv("ACCESS_EVIDENCE_DIR", "/tmp/opscontrol-access-evidence"))
name = "opscontrol-access-" + secrets.token_hex(5)
processes = []
started = False
success = False
password = secrets.token_urlsafe(32)
admin_password = secrets.token_urlsafe(30)
env = os.environ.copy()
env.update(
    ENVIRONMENT="test",
    OPSCONTROL_ACCESS_ACCEPTANCE="1",
    ACCESS_PRIVATE_DIR=str(private),
    ACCESS_EVIDENCE_DIR=str(OUT),
    AWS_EC2_METADATA_DISABLED="true",
)


if Path("/usr/bin/chromium").is_file():
    env.setdefault("PLAYWRIGHT_CHROMIUM_EXECUTABLE", "/usr/bin/chromium")


def run(args, cwd=ROOT, expected=0):
    p = subprocess.run(
        [str(x) for x in args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=240,
    )
    if p.returncode != expected:
        (private / "failed.log").write_text(p.stdout + "\n" + p.stderr)
        raise RuntimeError(
            "Owned access fixture command failed; private diagnostics retained"
        )
    return (p.stdout + ("\n" + p.stderr if expected else "")).strip()


def port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait(url):
    for _ in range(100):
        try:
            with urlopen(url, timeout=1) as r:
                if r.status == 200:
                    return
        except OSError:
            time.sleep(0.2)
    raise RuntimeError("Owned service readiness failed")


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
        "postgresql+psycopg://opscontrol:"
        + password
        + "@127.0.0.1:"
        + dbport
        + "/opscontrol"
    )
    run(
        [PYTHON, "-m", "alembic", "upgrade", "0024_notification_leases"],
        ROOT / "backend",
    )
    fixture = {
        "admin_id": str(uuid.uuid4()),
        "viewer_id": str(uuid.uuid4()),
        "customer_a": str(uuid.uuid4()),
        "customer_b": str(uuid.uuid4()),
        "vm_id": str(uuid.uuid4()),
        "admin_password": admin_password,
        "old_viewer_token": secrets.token_urlsafe(48),
    }
    (private / "fixture.json").write_text(json.dumps(fixture))
    # Seed the old schema through explicit SQL: new ORM columns do not exist yet.
    code = """
import json,hashlib
from pathlib import Path
from datetime import datetime,timezone,timedelta
from sqlalchemy import create_engine,text
from app.core.config import settings
from app.security.passwords import hash_password
f=json.loads((Path(__import__('os').environ['ACCESS_PRIVATE_DIR'])/'fixture.json').read_text());engine=create_engine(settings.database_url)
with engine.begin() as c:
 for key,name,admin in [('admin_id','access-fixture-admin',True),('viewer_id','access-fixture-legacy',False)]:
  c.execute(text('INSERT INTO users(id,username,password_hash,active,platform_admin,created_at) VALUES (:id,:u,:h,true,:a,now())'),{'id':f[key],'u':name,'h':hash_password(f['admin_password']),'a':admin})
 for key,name,code in [('customer_a','Customer A (synthetic)','ACCESS-A'),('customer_b','Customer B (synthetic)','ACCESS-B')]:
  c.execute(text('INSERT INTO organizations(id,name,code,active,created_at,updated_at) VALUES (:id,:n,:c,true,now(),now())'),{'id':f[key],'n':name,'c':code})
 c.execute(text("INSERT INTO vms(id,organization_id,hostname,environment,created_at) VALUES (:id,:o,'access-preserved.example.test','PROD',now())"),{'id':f['vm_id'],'o':f['customer_a']})
 import uuid
 c.execute(text("INSERT INTO organization_memberships(id,user_id,organization_id,role) VALUES (:id,:u,:o,'viewer')"),{'id':str(uuid.uuid4()),'u':f['viewer_id'],'o':f['customer_a']})
 c.execute(text('INSERT INTO access_sessions(id,user_id,token_hash,expires_at,created_at) VALUES (:id,:u,:h,:e,now())'),{'id':str(uuid.uuid4()),'u':f['viewer_id'],'h':hashlib.sha256(f['old_viewer_token'].encode()).hexdigest(),'e':datetime.now(timezone.utc)+timedelta(hours=12)})
 before={table:[list(map(str,r)) for r in c.execute(text('SELECT '+columns+' FROM '+table+' ORDER BY id'))] for table,columns in [('users','id,username,password_hash,active,platform_admin,created_at'),('organizations','id,name,code,active,created_at'),('vms','id,organization_id,hostname'),('access_sessions','id,user_id,token_hash,expires_at,created_at'),('organization_memberships','id,user_id,organization_id,role')]}
 (Path(__import__('os').environ['ACCESS_PRIVATE_DIR'])/'before.json').write_text(json.dumps(before))
"""
    run([PYTHON, "-c", code], ROOT / "backend")
    run([PYTHON, "-m", "alembic", "upgrade", "head"], ROOT / "backend")
    verify = code[code.index(" before=") : code.index("\n (Path")].replace(
        " before=", " actual="
    )
    check = (
        "import json,os\nfrom pathlib import Path\nfrom sqlalchemy import create_engine,text\nfrom app.core.config import settings\nwith create_engine(settings.database_url).begin() as c:\n"
        + verify
        + "\n expected=json.loads((Path(os.environ['ACCESS_PRIVATE_DIR'])/'before.json').read_text());assert actual==expected\nprint('Populated migration preserves old UUIDs, customer FKs, password hashes and sessions PASS')"
    )
    print(run([PYTHON, "-c", check], ROOT / "backend"), flush=True)
    print(
        run([PYTHON, "-m", "scripts.access_schema_probe"], ROOT / "backend"), flush=True
    )
    print(run([PYTHON, "-m", "alembic", "check"], ROOT / "backend"), flush=True)
    run(
        [PYTHON, "-m", "alembic", "downgrade", "0024_notification_leases"],
        ROOT / "backend",
        expected=1,
    )
    print("Schema/ORM migration check and unsafe downgrade refusal PASS", flush=True)
    # Unknown legacy privilege labels must fail transactionally, not be guessed.
    valid_url = env["DATABASE_URL"]
    run(
        [
            PYTHON,
            "-c",
            "from sqlalchemy import create_engine,text;from app.core.config import settings; e=create_engine(settings.database_url,isolation_level='AUTOCOMMIT'); c=e.connect();c.execute(text('CREATE DATABASE access_invalid_legacy'));c.close();e.dispose()",
        ],
        ROOT / "backend",
    )
    env["DATABASE_URL"] = valid_url.rsplit("/", 1)[0] + "/access_invalid_legacy"
    run(
        [PYTHON, "-m", "alembic", "upgrade", "0024_notification_leases"],
        ROOT / "backend",
    )
    seed_invalid = """
from sqlalchemy import create_engine,text
from app.core.config import settings
from uuid import uuid4
with create_engine(settings.database_url).begin() as c:
 u,o,m=uuid4(),uuid4(),uuid4()
 c.execute(text("INSERT INTO users(id,username,password_hash,active,platform_admin,created_at) VALUES (:id,'unknown-legacy','unusable-test-hash',true,false,now())"),{'id':u})
 c.execute(text("INSERT INTO organizations(id,name,code,active,created_at,updated_at) VALUES (:id,'Legacy fixture','LEGACY-INVALID',true,now(),now())"),{'id':o})
 c.execute(text("INSERT INTO organization_memberships(id,user_id,organization_id,role) VALUES (:m,:u,:o,'unknown-privilege')"),{'m':m,'u':u,'o':o})
"""
    run([PYTHON, "-c", seed_invalid], ROOT / "backend")
    failure = run(
        [PYTHON, "-m", "alembic", "upgrade", "head"], ROOT / "backend", expected=1
    )
    assert "Unknown legacy membership role" in failure
    run(
        [
            PYTHON,
            "-c",
            "from sqlalchemy import create_engine,text;from app.core.config import settings; c=create_engine(settings.database_url).connect();assert c.scalar(text('SELECT version_num FROM alembic_version'))=='0024_notification_leases';assert c.scalar(text(\"SELECT to_regclass('public.service_providers')\")) is None;assert c.scalar(text('SELECT count(*) FROM users'))==1;c.close()",
        ],
        ROOT / "backend",
    )
    env["DATABASE_URL"] = valid_url
    print(
        "Unknown legacy roles fail and roll back without altering old users/schema PASS",
        flush=True,
    )

    apiport = port()
    uiport = port()
    env.update(
        TEST_API_BASE=f"http://127.0.0.1:{apiport}",
        ACCESS_UI_BASE=f"http://127.0.0.1:{uiport}",
        VITE_API_BASE_URL=f"http://127.0.0.1:{apiport}",
        CORS_ORIGINS=f"http://127.0.0.1:{uiport}",
    )
    log = (private / "api.log").open("w")
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
    processes.append(p)
    wait(env["TEST_API_BASE"] + "/openapi.json")
    print(
        run([PYTHON, "-m", "scripts.access_acceptance_probe"], ROOT / "backend"),
        flush=True,
    )
    if os.getenv("ACCESS_BROWSER_ACCEPTANCE") == "1":
        ui_log = (private / "ui.log").open("w")
        p = subprocess.Popen(
            [
                "node",
                "node_modules/vite/bin/vite.js",
                "--host",
                "127.0.0.1",
                "--port",
                str(uiport),
                "--strictPort",
            ],
            cwd=ROOT / "frontend",
            env=env,
            stdout=ui_log,
            stderr=subprocess.STDOUT,
        )
        processes.append(p)
        wait(env["ACCESS_UI_BASE"])
        print(run(["node", "frontend/scripts/access_acceptance.mjs"]), flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "migration.json").write_text(
        json.dumps(
            {
                "status": "PASS",
                "from": "0024_notification_leases",
                "to": "0026_managed_telemetry_uat",
                "preserved": [
                    "User UUIDs/password hashes/admin flags",
                    "Existing human sessions",
                    "Customer UUIDs and resource foreign keys",
                    "Legacy customer memberships",
                ],
                "disposable": True,
            },
            indent=2,
        )
    )
    success = True
    print("CUSTOMER / DEPARTMENT / RBAC ACCEPTANCE PASS", flush=True)
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
            ["docker", "rm", "-f", name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    if success:
        shutil.rmtree(private)
    else:
        print("Private diagnostics:", private, file=sys.stderr)
