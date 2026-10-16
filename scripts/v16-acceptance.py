#!/usr/bin/env python3
"""Owned disposable V1.6 PostgreSQL checks. Never touches configured demo volumes."""
import json, os, secrets, socket, subprocess, tempfile, time
from pathlib import Path

root = Path(__file__).resolve().parents[1]
private = Path(tempfile.mkdtemp(prefix="opscontrol-v16-"))
private.chmod(0o700)
name = "opscontrol-v16-" + secrets.token_hex(6)
password = secrets.token_urlsafe(32)
env = {
    **os.environ,
    "ENV": "test",
    "ENVIRONMENT": "test",
    "OPSCONTROL_V16_ACCEPTANCE": "1",
    "AWS_EC2_METADATA_DISABLED": "true",
}
started = False
out = Path(os.getenv("V16_EVIDENCE_DIR", "/tmp/opscontrol-v16-evidence"))
out.mkdir(parents=True, exist_ok=True)
python = root / "backend/.venv/bin/python"


def run(args, cwd=root):
    result = subprocess.run(
        [str(x) for x in args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    if result.returncode:
        (private / "failure.log").write_text(result.stdout + "\n" + result.stderr)
        for line in (result.stdout + "\n" + result.stderr).splitlines():
            if line.startswith(
                (
                    "ERROR:",
                    "FAIL:",
                    "AssertionError:",
                    "FAILED",
                    "RuntimeError:",
                    "ImportError:",
                    "ModuleNotFoundError:",
                )
            ):
                print(line[:300])
        raise RuntimeError(
            "Owned V1.6 check failed; private diagnostics: " + str(private)
        )
    return (result.stdout + "\n" + result.stderr).strip()


try:
    run(
        [
            "docker",
            "run",
            "--detach",
            "--name",
            name,
            "--publish",
            "127.0.0.1::5432",
            "--env",
            "POSTGRES_USER=opscontrol",
            "--env",
            "POSTGRES_DB=opscontrol",
            "--env",
            "POSTGRES_PASSWORD=" + password,
            "postgres:17-alpine",
        ]
    )
    started = True
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
        raise RuntimeError("Owned PostgreSQL readiness failed")
    port = json.loads(run(["docker", "inspect", name]))[0]["NetworkSettings"]["Ports"][
        "5432/tcp"
    ][0]["HostPort"]
    env["DATABASE_URL"] = (
        "postgresql+psycopg://opscontrol:"
        + password
        + "@127.0.0.1:"
        + port
        + "/opscontrol"
    )
    if os.getenv("V16_STAGING_PRESERVATION") == "1":
        run(
            [python, "-m", "alembic", "upgrade", "0024_notification_leases"],
            root / "backend",
        )
        preservation = run(
            [python, "-m", "scripts.existing_database_upgrade_probe"], root / "backend"
        )
        (out / "staging-preservation.txt").write_text(preservation + "\n")
        run([python, "-m", "alembic", "check"], root / "backend")
        # Only this freshly owned database exists here; V1.6 tables are empty.
        run(
            [python, "-m", "alembic", "downgrade", "0031_in_app_notifications"],
            root / "backend",
        )
    run(
        [python, "-m", "alembic", "upgrade", "0031_in_app_notifications"],
        root / "backend",
    )
    # Upgrade a populated V1.5 identity/cursor rather than certify only an empty DB.
    run(
        [
            python,
            "-c",
            "from sqlalchemy import text;from app.db.session import engine;from app.security.passwords import hash_password;import uuid;\nwith engine.begin() as db:\n db.execute(text(\"INSERT INTO organizations(id,name,code,active,created_at,updated_at) VALUES(:id,'Controlled preserved customer','V16-PRESERVED',true,now(),now())\"),{'id':uuid.uuid4()})",
        ],
        root / "backend",
    )
    run([python, "-m", "alembic", "upgrade", "head"], root / "backend")
    run([python, "-m", "alembic", "check"], root / "backend")
    run(
        [python, "-m", "alembic", "downgrade", "0031_in_app_notifications"],
        root / "backend",
    )
    if os.getenv("V16_PENTAHO_R1_ACCEPTANCE") == "1":
        run(
            [python, "-m", "alembic", "upgrade", "0032_pipeline_ownership"],
            root / "backend",
        )
        env["V16_EVIDENCE_DIR"] = str(out)
        run([python, "-m", "scripts.pentaho_migration_probe", "seed"], root / "backend")
    if os.getenv("V16_PENTAHO_REVIEW_ACCEPTANCE") == "1":
        run(
            [python, "-m", "alembic", "upgrade", "0033_pentaho_attempts"],
            root / "backend",
        )
        run(
            [python, "-m", "scripts.pentaho_review_migration_probe", "seed"],
            root / "backend",
        )
    run([python, "-m", "alembic", "upgrade", "head"], root / "backend")
    if os.getenv("V16_PENTAHO_REVIEW_ACCEPTANCE") == "1":
        run(
            [python, "-m", "scripts.pentaho_review_migration_probe", "verify"],
            root / "backend",
        )
    if os.getenv("V16_PENTAHO_R1_ACCEPTANCE") == "1":
        run(
            [python, "-m", "scripts.pentaho_migration_probe", "verify"],
            root / "backend",
        )
    run([python, "-m", "alembic", "check"], root / "backend")
    targets = (
        os.getenv("V16_TEST_TARGETS", "").split(",")
        if os.getenv("V16_TEST_TARGETS")
        else [
            "tests.test_pipeline_ownership_v16",
            *(
                [
                    "tests.test_pentaho_execution_r1",
                    *(
                        ["tests.test_pentaho_review_r1"]
                        if os.getenv("V16_PENTAHO_REVIEW_ACCEPTANCE") == "1"
                        else []
                    ),
                ]
                if os.getenv("V16_PENTAHO_R1_ACCEPTANCE") == "1"
                else []
            ),
        ]
    )
    assert all(
        t.startswith("tests.test_") and all(c.isalnum() or c in "_." for c in t)
        for t in targets
    )
    output = run(
        [
            python,
            "-m",
            "unittest",
            *targets,
            "-v",
        ],
        root / "backend",
    )
    (out / "ownership.txt").write_text(output + "\n")
    if os.getenv("V16_API_ACCEPTANCE") == "1":
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            apiport = sock.getsockname()[1]
        env["V16_API_URL"] = "http://127.0.0.1:" + str(apiport)
        ui = None
        if os.getenv("V16_BROWSER_ACCEPTANCE") == "1":
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                uiport = sock.getsockname()[1]
            env["V16_UI_URL"] = "http://127.0.0.1:" + str(uiport)
            env["CORS_ORIGINS"] = env["V16_UI_URL"]
            env["VITE_API_BASE_URL"] = env["V16_API_URL"]
        env["V16_PRIVATE_DIR"] = str(private)
        env["V16_EVIDENCE_DIR"] = str(out)
        (private / "api-fixture.json").write_text(
            json.dumps(
                {
                    "password": secrets.token_urlsafe(30),
                    "viewer_password": secrets.token_urlsafe(30),
                }
            )
        )
        (private / "api-fixture.json").chmod(0o600)
        with (private / "api.log").open("w") as log:
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
        try:
            from urllib.request import urlopen

            for _ in range(120):
                try:
                    if urlopen(env["V16_API_URL"] + "/health", timeout=1).status == 200:
                        break
                except OSError:
                    time.sleep(0.2)
            else:
                raise RuntimeError("Owned V1.6 API readiness failed")
            print(run([python, "-m", "scripts.v16_api_probe"], root / "backend"))
            if os.getenv("V16_PENTAHO_R1_ACCEPTANCE") == "1":
                print(
                    run(
                        [python, "-m", "scripts.pentaho_sprint03_http_probe"],
                        root / "backend",
                    )
                )
            if os.getenv("V16_PENTAHO_REVIEW_ACCEPTANCE") == "1":
                print(
                    run(
                        [python, "-m", "scripts.pentaho_sprint04_http_probe"],
                        root / "backend",
                    )
                )
            if os.getenv("V16_BROWSER_ACCEPTANCE") == "1":
                run(["npm", "run", "build"], root / "frontend")
                env.setdefault(
                    "PLAYWRIGHT_CHROMIUM_EXECUTABLE",
                    "/usr/bin/chromium" if Path("/usr/bin/chromium").is_file() else "",
                )
                with (private / "ui.log").open("w") as log:
                    ui = subprocess.Popen(
                        [
                            "node",
                            "node_modules/vite/bin/vite.js",
                            "preview",
                            "--host",
                            "127.0.0.1",
                            "--port",
                            str(uiport),
                        ],
                        cwd=root / "frontend",
                        env=env,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                    )
                for _ in range(100):
                    try:
                        if urlopen(env["V16_UI_URL"], timeout=1).status == 200:
                            break
                    except OSError:
                        time.sleep(0.2)
                else:
                    raise RuntimeError("Owned V1.6 UI readiness failed")
                print(run(["node", "frontend/scripts/pipeline_v16_acceptance.mjs"]))
        finally:
            if ui:
                ui.terminate()
                ui.wait(timeout=15)
            api.terminate()
            api.wait(timeout=15)
    # Populated V1.6 downgrade must fail before dropping even one new table.
    result = subprocess.run(
        [str(python), "-m", "alembic", "downgrade", "0031_in_app_notifications"],
        cwd=root / "backend",
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0 and any(
        message in result.stderr
        for message in (
            "V1.6 identities/evidence/checkpoints exist",
            "Pentaho attempts/identity/evidence/recovery exist",
            "Pentaho evidence review/decisions exist",
        )
    )
    run([python, "-m", "alembic", "check"], root / "backend")
    (out / "report.json").write_text(
        json.dumps(
            {
                "status": "PASS",
                "owned_postgresql": True,
                "head": run(
                    [python, "-m", "alembic", "heads"], root / "backend"
                ).split()[0],
                "populated_v15_upgrade": True,
                "schema_drift": False,
                "populated_downgrade_refused": True,
                "empty_downgrade_upgrade": True,
                "critical_race_41_42": "PASS",
                "vendor_environments_accessed": False,
                "production_modified": False,
            },
            indent=2,
        )
    )
    print(
        "V1.6 actual PostgreSQL ownership/durability/discovery/holds/recovery/scopes and additive migration PASS"
    )
finally:
    if started:
        subprocess.run(
            ["docker", "rm", "--force", "--volumes", name], capture_output=True
        )
