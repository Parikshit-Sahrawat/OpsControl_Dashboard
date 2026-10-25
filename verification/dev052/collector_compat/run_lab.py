"""Own an isolated internal-network lab; never contact a real provider/production.

Existing immutable Python image supplies dependencies, with experimental sources
mounted read-only. It is not a newly built or approved release image.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import signal
import shutil
import socket
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]
PYTHON = ROOT / "backend/.venv/bin/python"
HERE = Path(__file__).resolve().parent
DOCKER = ["docker", "--host=unix:///var/run/docker.sock"]
PG_IMAGE = "sha256:ab20e934b27ba3ff927c1b4c9ff8cf6c32f315f743efe68dd3441182a87fb085"
FIXTURE_IMAGE = (
    "sha256:f4b7b8044a873fcc0f348549a19b9075cd77bd56ead7177192cfec38d85bce4a"
)


def main():
    def interrupted(signum, frame):
        raise KeyboardInterrupt("Owned lab interrupted; scoped cleanup required")

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--guarded-binary", type=Path, required=True)
    args = parser.parse_args()
    stage, out = args.stage.resolve(), args.output.resolve()
    assert (
        json.loads((stage / "overlay-provenance.json").read_text())[
            "production_guard_modified"
        ]
        is False
    )
    pin = json.loads((HERE / "candidate.json").read_text())
    for binary, digest in [
        (args.binary, pin["binary_sha256"]),
        (
            args.guarded_binary,
            "6bca4ddd928b4b0880f7ec6c16511922f740c497b4efa4b33915b2d54a729213",
        ),
    ]:
        with binary.open("rb") as stream:
            assert hashlib.file_digest(stream, "sha256").hexdigest() == digest
    if shutil.disk_usage(ROOT).free < 900 * 1024**2:
        raise RuntimeError(
            "BLOCKED: lab needs at least 900 MiB free; do not prune unrelated Docker resources"
        )
    out.mkdir(parents=True, exist_ok=False)
    private = Path(tempfile.mkdtemp(prefix="dev052a3-lab-"))
    name = "dev052a3-" + secrets.token_hex(4)
    containers, networks = [], []
    processes = []
    password = secrets.token_urlsafe(32)
    known_secrets = [password]
    env = {
        **os.environ,
        "ENVIRONMENT": "test",
        "OPSCONTROL_ARCH001_ACCEPTANCE": "1",
        "ARCH001_PRIVATE_DIR": str(private),
        "ARCH001_EVIDENCE_DIR": str(out),
        "OPSCONTROL_OTEL_BINARY": str(args.binary.resolve()),
        "AWS_EC2_METADATA_DISABLED": "true",
    }
    report = {
        "status": "FAIL",
        "scope": "owned disposable fixture, not provider certification",
        "api_dependencies": "existing local backend/.venv; not a release image",
        "runner_fixture_image": FIXTURE_IMAGE,
        "postgres_image": PG_IMAGE,
        "source": json.loads((stage / "overlay-provenance.json").read_text()),
    }

    def run(argv, cwd=ROOT, timeout=120):
        result = subprocess.run(
            [str(a) for a in argv],
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        with (private / "commands.log").open("a") as log:
            # Arguments intentionally excluded: synthetic passwords may be present.
            log.write(
                "command=" + str(argv[0]) + " exit=" + str(result.returncode) + "\n"
            )
            log.write(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError("Owned lab command failed: " + str(argv[0]))
        return result.stdout.strip()

    def module(name, *argv):
        return run([PYTHON, "-m", name, *argv], stage / "backend", timeout=180)

    api_args = []

    def start_api():
        log = (private / "api.log").open("a")
        process = subprocess.Popen(
            api_args,
            cwd=stage / "backend",
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        log.close()
        processes.append(process)
        return process

    try:
        for image in [PG_IMAGE, FIXTURE_IMAGE]:
            assert (
                run([*DOCKER, "image", "inspect", "--format", "{{.Id}}", image])
                == image
            )
        for network in [name, name + "-denied"]:
            run([*DOCKER, "network", "create", "--internal", network])
            networks.append(network)
        gateway = json.loads(run([*DOCKER, "network", "inspect", name]))[0]["IPAM"][
            "Config"
        ][0]["Gateway"]
        postgres = name + "-pg"
        containers.append(postgres)
        run(
            [
                *DOCKER,
                "run",
                "-d",
                "--name",
                postgres,
                "--network",
                name,
                "--memory",
                "256m",
                "--pids-limit",
                "128",
                "--env",
                "POSTGRES_USER=opscontrol",
                "--env",
                "POSTGRES_DB=opscontrol",
                "--env",
                "POSTGRES_PASSWORD=" + password,
                PG_IMAGE,
            ]
        )
        for _ in range(100):
            ready = subprocess.run(
                [*DOCKER, "exec", postgres, "pg_isready", "-U", "opscontrol"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if ready.returncode == 0:
                break
            time.sleep(0.2)
        else:
            raise RuntimeError("Postgres readiness failed")
        pg_ip = run(
            [
                *DOCKER,
                "inspect",
                "--format",
                '{{(index .NetworkSettings.Networks "' + name + '").IPAddress}}',
                postgres,
            ]
        )
        env["DATABASE_URL"] = (
            f"postgresql+psycopg://opscontrol:{password}@{pg_ip}:5432/opscontrol"
        )
        module("alembic", "upgrade", "0026_managed_telemetry_uat")
        module("scripts.arch001_acceptance_probe", "seed")
        module("alembic", "upgrade", "head")
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
                "/CN=dev052a3",
                "-addext",
                f"subjectAltName=IP:{gateway},IP:127.0.0.1,DNS:localhost",
            ]
        )
        with socket.socket() as sock:
            sock.bind((gateway, 0))
            apiport = sock.getsockname()[1]
        base = f"https://{gateway}:{apiport}"
        env.update(
            ARCH001_API_URL=base,
            SSL_CERT_FILE=str(private / "ca.pem"),
            OPSCONTROL_PUBLIC_INGESTION_URL=base,
            NO_PROXY=env.get("NO_PROXY", "") + "," + gateway,
        )
        env["no_proxy"] = env["NO_PROXY"]
        api_args[:] = [
            str(PYTHON),
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            gateway,
            "--port",
            str(apiport),
            "--no-access-log",
            "--ssl-keyfile",
            str(private / "key.pem"),
            "--ssl-certfile",
            str(private / "ca.pem"),
        ]
        api = start_api()
        # Configure trust explicitly for the host owner; no verification disable.
        import ssl
        from urllib.request import build_opener, ProxyHandler, HTTPSHandler

        opener = build_opener(
            ProxyHandler({}),
            HTTPSHandler(
                context=ssl.create_default_context(cafile=str(private / "ca.pem"))
            ),
        )
        for _ in range(150):
            try:
                with opener.open(base + "/health", timeout=1) as response:
                    assert response.status == 200
                break
            except OSError:
                assert api.poll() is None, "API exited"
                time.sleep(0.2)
        else:
            raise RuntimeError("API startup timed out")
        denied = name + "-denied-target"
        containers.append(denied)
        run(
            [
                *DOCKER,
                "run",
                "-d",
                "--name",
                denied,
                "--network",
                name + "-denied",
                "--read-only",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges:true",
                FIXTURE_IMAGE,
                "python",
                "-m",
                "http.server",
                "8080",
            ]
        )
        denied_ip = run(
            [
                *DOCKER,
                "inspect",
                "--format",
                '{{(index .NetworkSettings.Networks "' + name + '-denied").IPAddress}}',
                denied,
            ]
        )
        run(
            [
                *DOCKER,
                "exec",
                denied,
                "python",
                "-c",
                "import urllib.request;assert urllib.request.urlopen('http://127.0.0.1:8080').status==200",
            ]
        )
        runner = name + "-agent"
        containers.append(runner)
        run(
            [
                *DOCKER,
                "run",
                "-d",
                "--name",
                runner,
                "--network",
                name,
                "--user",
                f"{os.getuid()}:{os.getgid()}",
                "--read-only",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges:true",
                "--memory",
                "512m",
                "--cpus",
                "1",
                "--pids-limit",
                "128",
                "--tmpfs",
                "/tmp:rw,nosuid,nodev,size=64m",
                "--env",
                "ENVIRONMENT=test",
                "--env",
                "DEV052A3_LAB=1",
                "--env",
                "OPSCONTROL_ARCH001_ACCEPTANCE=1",
                "--env",
                "ARCH001_API_URL=" + base,
                "--env",
                "ARCH001_PRIVATE_DIR=/fixture",
                "--env",
                "ARCH001_EVIDENCE_DIR=/fixture",
                "--env",
                "SSL_CERT_FILE=/fixture/ca.pem",
                "--env",
                "NO_PROXY=*",
                "--env",
                "no_proxy=*",
                "--env",
                "HTTP_PROXY=",
                "--env",
                "HTTPS_PROXY=",
                "--env",
                "ALL_PROXY=",
                "--env",
                "DENIED_FIXTURE_IP=" + denied_ip,
                "--env",
                "PYTHONPATH=/work/backend",
                "--volume",
                f"{stage}:/work:ro",
                "--volume",
                f"{HERE}:/verification:ro",
                "--volume",
                f"{private}:/fixture:rw",
                "--volume",
                f"{args.binary.resolve()}:/runtime/otelcol-contrib:ro",
                "--volume",
                f"{args.guarded_binary.resolve()}:/runtime/otelcol-contrib-0.123.0:ro",
                FIXTURE_IMAGE,
                "python",
                "/verification/e2e.py",
            ]
        )
        fields = json.loads(
            run([*DOCKER, "inspect", "--format", "{{json .HostConfig}}", runner])
        )
        report["constraints"] = {
            k: fields[k]
            for k in [
                "ReadonlyRootfs",
                "Memory",
                "NanoCpus",
                "PidsLimit",
                "CapDrop",
                "SecurityOpt",
            ]
        }
        deadline = time.monotonic() + 360
        outage = False
        while time.monotonic() < deadline:
            state = json.loads(
                run([*DOCKER, "inspect", "--format", "{{json .State}}", runner])
            )
            if not state["Running"]:
                assert (
                    state["ExitCode"] == 0
                ), "Agent E2E failed; retained redacted logs"
                break
            if not outage and (private / "request-api-outage").exists():
                outage = True
                api.terminate()
                api.wait(timeout=15)
                (private / "api-down").touch()
                time.sleep(5)
                api = start_api()
                for _ in range(100):
                    try:
                        opener.open(base + "/health", timeout=1).close()
                        break
                    except OSError:
                        time.sleep(0.2)
                else:
                    raise RuntimeError("API did not recover")
                (private / "api-restored").touch()
            time.sleep(0.5)
        else:
            raise RuntimeError("E2E timed out")
        report["e2e"] = json.loads((private / "e2e.json").read_text())
        # Independently query persisted evidence and exercise unchanged authenticated
        # enrollment/rotation/revocation/tenant/method/negative API assertions.
        shutil.copy2(
            HERE / "postcheck.py", stage / "backend/scripts/dev052a3_postcheck.py"
        )
        module("scripts.dev052a3_postcheck")
        report["status"] = "PASS"
    except (Exception, KeyboardInterrupt) as error:
        report["error"] = type(error).__name__ + ": " + str(error)
    finally:
        for name_owned in containers:
            logs = subprocess.run(
                [*DOCKER, "logs", name_owned], capture_output=True, text=True
            )
            (private / (name_owned + ".log")).write_text(logs.stdout + logs.stderr)
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=20)

        # Gather only this lab's synthetic credentials for redaction.
        def secrets_in(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    if any(s in key for s in ["token", "password"]) and isinstance(
                        item, str
                    ):
                        known_secrets.append(item)
                    else:
                        secrets_in(item)
            elif isinstance(value, list):
                for item in value:
                    secrets_in(item)

        for file in private.rglob("*.json"):
            try:
                secrets_in(json.loads(file.read_text()))
            except (ValueError, OSError):
                pass
        for file in private.rglob("*"):
            if file.is_file() and (
                file.suffix == ".log" or file.name in ["e2e.json", "generated.yaml"]
            ):
                text = file.read_text(errors="replace")
                for secret in sorted(set(known_secrets), key=len, reverse=True):
                    if secret:
                        text = text.replace(secret, "[REDACTED]")
                (
                    out / file.relative_to(private).as_posix().replace("/", "_")
                ).write_text(text)
        cleanup_errors = []
        for name_owned in reversed(containers):
            result = subprocess.run(
                [*DOCKER, "rm", "-f", "-v", name_owned], capture_output=True, text=True
            )
            if result.returncode and "No such container" not in result.stderr:
                cleanup_errors.append(name_owned)
        for network in reversed(networks):
            result = subprocess.run(
                [*DOCKER, "network", "rm", network], capture_output=True, text=True
            )
            if result.returncode:
                cleanup_errors.append(network)
        shutil.rmtree(private)
        report["cleanup"] = {
            "status": "PASS" if not cleanup_errors else "FAIL",
            "errors": cleanup_errors,
            "owned_containers": containers,
            "owned_networks": networks,
            "private_credentials_tls_and_database_volume_removed": not cleanup_errors,
            "broad_cleanup": False,
        }
        rendered = json.dumps(report, indent=2)
        for secret in sorted(set(known_secrets), key=len, reverse=True):
            if secret:
                rendered = rendered.replace(secret, "[REDACTED]")
        (out / "lab-result.json").write_text(rendered + "\n")
        print(rendered)
    raise SystemExit(0 if report["status"] == "PASS" and not cleanup_errors else 1)


if __name__ == "__main__":
    main()
