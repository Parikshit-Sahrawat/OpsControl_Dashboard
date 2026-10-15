#!/usr/bin/env python3
"""Build and verify an owned Docker demo project; leave existing demos untouched."""
import hashlib, json, os, secrets, socket, subprocess, tempfile, time, shutil
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
source_commit = subprocess.check_output(
    ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
).strip()
expected_commit = os.getenv("OPSCONTROL_DOCKER_EXPECTED_COMMIT")


def verify_source_head():
    if expected_commit:
        current = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
        dirty = subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=ROOT, text=True
        ).strip()
        if current != expected_commit or dirty:
            raise RuntimeError("Exact-head Docker verification requires the expected clean commit")


verify_source_head()
private = Path(tempfile.mkdtemp(prefix="opscontrol-access-docker-"))
private.chmod(0o700)
project = "opscontrol-access-demo-" + secrets.token_hex(5)
env = os.environ.copy()
env["BUILDX_CONFIG"] = str(private / "buildx")
out = Path(
    os.getenv("ACCESS_DOCKER_EVIDENCE_DIR", "/tmp/opscontrol-access-docker-evidence")
)
passed = False


def port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


api_port, ui_port, gateway_port = port(), port(), port()
subprocess.run(
    [
        str(ROOT / "backend/.venv/bin/python"),
        str(ROOT / "scripts/init-demo-gateway.py"),
        "--directory",
        str(private / "gateway"),
    ],
    check=True,
    capture_output=True,
)
password = secrets.token_urlsafe(36)
db_password = secrets.token_urlsafe(36)
(private / "admin-password").write_text(password)
(private / "admin-password").chmod(0o600)
(private / "override.yml").write_text(
    f"""services:
  postgres:
    image: postgres:17-alpine
    volumes: !override []
    environment:
      POSTGRES_PASSWORD: {db_password}
  api:
    environment:
      DATABASE_URL: postgresql+psycopg://opscontrol:{db_password}@postgres:5432/opscontrol
      CORS_ORIGINS: http://127.0.0.1:{ui_port}
      OPSCONTROL_PUBLIC_INGESTION_URL: https://localhost:{gateway_port}
    ports: !override
      - "127.0.0.1:{api_port}:8000"
    volumes: !override
      - "{private}/admin-password:/run/secrets/demo_admin_password:ro"
  worker:
    environment:
      DATABASE_URL: postgresql+psycopg://opscontrol:{db_password}@postgres:5432/opscontrol
  ingestion-gateway:
    ports: !override
      - "127.0.0.1:{gateway_port}:8443"
    volumes: !override
      - "{ROOT}/deploy/gateway/nginx.conf:/etc/nginx/nginx.conf:ro"
      - "{private}/gateway/tls.crt:/etc/opscontrol/tls/tls.crt:ro"
      - "{private}/gateway/tls.key:/etc/opscontrol/tls/tls.key:ro"
  frontend:
    build:
      args:
        VITE_API_BASE_URL: http://127.0.0.1:{api_port}
    ports: !override
      - "127.0.0.1:{ui_port}:80"
"""
)
compose = [
    "docker",
    "compose",
    "--project-name",
    project,
    "-f",
    str(ROOT / "docker-compose.demo.yml"),
    "-f",
    str(private / "override.yml"),
]
if env.get("OPSCONTROL_BUILD_OVERRIDE"):
    compose += ["-f", env["OPSCONTROL_BUILD_OVERRIDE"]]


def run(args):
    result = subprocess.run(
        args, cwd=ROOT, env=env, capture_output=True, text=True, timeout=600
    )
    if result.returncode:
        (private / "failed.log").write_text(result.stdout + "\n" + result.stderr)
        raise RuntimeError(
            "Owned Docker demo command failed; private diagnostics retained"
        )
    return result.stdout.strip()


def call(path, method="GET", body=None, token=None):
    req = Request(
        f"http://127.0.0.1:{api_port}" + path,
        method=method,
        data=json.dumps(body).encode() if body else None,
        headers={
            "Content-Type": "application/json",
            **({"Authorization": "Bearer " + token} if token else {}),
        },
    )
    with urlopen(req, timeout=10) as r:
        return json.load(r)


try:
    run(compose + ["build"])
    if env.get("OPSCONTROL_DOCKER_RECOVER_BUILD_CACHE") == "1":
        # VFS hosts retain full build snapshots. Release unused, rebuildable
        # cache before allocating the five runtime filesystems; never prune data.
        run(["docker", "builder", "prune", "--all", "--force"])
    run(compose + ["up", "--no-build", "--detach"])
    print("Owned five-service Docker demo built", flush=True)
    image_paths = [
        "app/data_pipelines/api.py", "app/data_pipelines/service.py",
        "app/data_pipelines/runtime.py",
    ]
    source_hashes = {
        path: hashlib.sha256((ROOT / "backend" / path).read_bytes()).hexdigest()
        for path in image_paths
    }
    for service in ("api", "worker"):
        actual = run(compose + ["exec", "-T", service, "python", "-c",
            "import hashlib,json;from pathlib import Path;print(json.dumps({p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in "
            + repr(image_paths) + "}))"])
        if json.loads(actual) != source_hashes:
            raise RuntimeError("Docker image does not match the checked-out pipeline source")
    for _ in range(120):
        try:
            call("/health")
            with urlopen(f"http://127.0.0.1:{ui_port}", timeout=1) as r:
                assert r.status == 200 and r.headers["X-Frame-Options"] == "DENY"
            break
        except OSError:
            time.sleep(0.5)
    else:
        raise RuntimeError("Docker demo readiness failed")
    import ssl
    from urllib.error import HTTPError

    trust = ssl.create_default_context(cafile=str(private / "gateway/ca.crt"))
    with urlopen(
        f"https://localhost:{gateway_port}/health", context=trust, timeout=10
    ) as response:
        assert response.status == 200
    try:
        urlopen(
            Request(
                f"https://localhost:{gateway_port}/api/v1/agent/heartbeat",
                data=b'{"health":"RUNNING","version":"1.5.0","runtime_version":"0.123.0"}',
                headers={"Content-Type": "application/json"},
            ),
            context=trust,
        )
    except HTTPError as error:
        assert error.code == 401
    else:
        raise AssertionError("Unauthenticated gateway request was accepted")
    token = call(
        "/api/v1/auth/login", "POST", {"username": "demo-admin", "password": password}
    )["access_token"]
    resources = call("/api/v1/unified/resources", token=token)
    assert resources["total"] > 0
    assert "domains" in call("/api/v1/unified/overview", token=token)
    for _ in range(60):
        if "OpsControl collector runtime started" in run(
            compose + ["logs", "--no-color", "worker"]
        ):
            break
        time.sleep(0.5)
    else:
        raise RuntimeError("Native Docker worker did not start")
    departments = call("/api/v1/access/departments", token=token)["items"]
    employees = call("/api/v1/access/employees", token=token)["items"]
    customers = call("/api/v1/organizations", token=token)
    assert len(departments) == 3 and len(employees) == 1 and len(customers) == 1
    assert not {r["id"] for r in departments} & {r["id"] for r in customers}
    before = {r["id"] for r in departments}
    run(
        compose + ["exec", "-T", "api", "python", "-m", "scripts.bootstrap_public_demo"]
    )
    after = {r["id"] for r in call("/api/v1/access/departments", token=token)["items"]}
    assert (
        before == after
        and len(call("/api/v1/access/employees", token=token)["items"]) == 1
    )
    runtime = run(
        compose + ["exec", "-T", "api", "/usr/local/bin/otelcol-contrib", "--version"]
    )
    assert "0.123.0" in runtime
    current = run(compose + ["exec", "-T", "api", "python", "-m", "alembic", "current"])
    expected = run(
        compose
        + [
            "exec",
            "-T",
            "api",
            "python",
            "-c",
            'from alembic.config import Config;from alembic.script import ScriptDirectory;print(ScriptDirectory.from_config(Config("alembic.ini")).get_current_head())',
        ]
    )
    assert expected.strip() in current
    comparison = run(
        compose + ["exec", "-T", "api", "python", "-m", "alembic", "check"]
    )
    assert "No new upgrade operations detected." in comparison
    run(compose + ["restart", "api"])
    for _ in range(120):
        try:
            assert call("/api/v1/auth/me", token=token)["platform_admin"]
            break
        except OSError:
            time.sleep(0.5)
    else:
        raise RuntimeError("Docker demo restart/session persistence failed")
    out.mkdir(parents=True, exist_ok=True)
    verify_source_head()
    (out / "docker.json").write_text(
        json.dumps(
            {
                "status": "PASS",
                "source_commit": source_commit,
                "exact_head_checked": bool(expected_commit),
                "api_worker_source_hashes": source_hashes,
                "checks": [
                    "API/frontend/PostgreSQL/native worker/TLS ingestion gateway built and ready",
                    "Frontend nginx response has security headers",
                    "Expected additive migration head installed",
                    "Full image/schema Alembic check has zero pending operations",
                    "Provider departments/customer UUIDs separated",
                    "Bootstrap repeat retains UUIDs and user count",
                    "API restart retains valid pre-restart session",
                ],
                "isolated_project": project,
                "existing_volumes_untouched": True,
            },
            indent=2,
        )
    )
    passed = True
    print(
        "ISOLATED DOCKER BUILD / BOOTSTRAP / RESTART / AUTHENTICATION PASS", flush=True
    )
finally:
    # Only this invocation's generated project and volumes are removable.
    subprocess.run(
        compose + ["down", "--volumes", "--remove-orphans"],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=90,
    )
    if passed:
        shutil.rmtree(private)
    else:
        print("Private Docker diagnostics retained:", private)
