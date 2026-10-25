#!/usr/bin/env python3
"""Baseline-pinned, project-scoped disposable product verification (no production)."""
import argparse
import hashlib
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import time

BASELINE = "f617cc653a965c2ad1bb7edf9e20237e40044b97"
ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--inject-failure",
        action="store_true",
        help="Exercise failure cleanup before lifecycle checks",
    )
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    runtime = Path(tempfile.mkdtemp(prefix="opscontrol-dev05-"))
    project = "dev05-" + secrets.token_hex(5)
    rows = []
    report = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "baseline": BASELINE,
        "project": project,
        "checks": rows,
        "scope": "Synthetic disposable Docker only; no production/provider certification",
    }
    env = os.environ.copy()
    env.update(
        DEV05_RUNTIME=str(runtime),
        DEV05_IMAGE=project + "-backend",
        BUILDX_CONFIG=str(runtime / "buildx"),
    )
    secret_values = []
    compose = []
    failed = False

    def cmd(argv, *, timeout=900, check=True):
        result = subprocess.run(
            argv,
            env=env,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        text = result.stdout.decode(errors="replace")
        with (runtime / "commands.log").open("a") as log:
            log.write("\n$ " + " ".join(map(str, argv)) + "\n" + text)
        if check and result.returncode:
            raise RuntimeError(
                f"Command failed ({result.returncode}): " + " ".join(map(str, argv))
            )
        return result

    def cc(*argv, **kwargs):
        return cmd(compose + list(argv), **kwargs)

    def check(name, fn):
        started = time.monotonic()
        try:
            fn()
        except Exception as error:
            rows.append(
                {
                    "name": name,
                    "status": "FAIL",
                    "detail": str(error),
                    "seconds": round(time.monotonic() - started, 2),
                }
            )
            print(name + ": FAIL", flush=True)
            return False
        rows.append(
            {
                "name": name,
                "status": "PASS",
                "seconds": round(time.monotonic() - started, 2),
            }
        )
        print(name + ": PASS", flush=True)
        return True

    def api(command):
        cc("exec", "-T", "api", "python", "/verification/probe.py", command)

    def browser(phase):
        cc("exec", "-T", "browser", "node", "/verification/browser.mjs", phase)

    def interruption(signum, frame):
        raise KeyboardInterrupt(f"Interrupted by signal {signum}")

    signal.signal(signal.SIGTERM, interruption)
    signal.signal(signal.SIGINT, interruption)
    try:
        head = cmd(["git", "rev-parse", "HEAD"]).stdout.decode().strip()
        report["harness_parent_or_head"] = head
        # Application files ALWAYS come from the exact baseline, even on later harness commits.
        archive = runtime / "baseline.tar"
        with archive.open("wb") as target:
            subprocess.run(
                ["git", "archive", BASELINE], cwd=ROOT, stdout=target, check=True
            )
        context = runtime / "context"
        context.mkdir()
        with tarfile.open(archive) as tar:
            tar.extractall(context, filter="data")
        shutil.copytree(
            ROOT / "verification/dev05",
            context / "verification/dev05",
            dirs_exist_ok=True,
        )
        compose = [
            "docker",
            "compose",
            "-p",
            project,
            "-f",
            str(context / "verification/dev05/compose.yml"),
        ]
        env.update(DOCKER_HOST="unix:///var/run/docker.sock")
        for name in (
            "DOCKER_CONTEXT",
            "DOCKER_TLS",
            "DOCKER_TLS_VERIFY",
            "DOCKER_CERT_PATH",
        ):
            env.pop(name, None)
        cmd(["docker", "info"])
        networks = cmd(["docker", "network", "ls", "-q"]).stdout.decode().split()
        occupied = []
        for network in networks:
            info = json.loads(cmd(["docker", "network", "inspect", network]).stdout)[0]
            occupied.extend(
                item.get("Subnet", "") for item in (info["IPAM"].get("Config") or [])
            )
        import ipaddress

        for prefix in range(20, 32):
            candidate = f"172.{prefix}.77.0/24"
            if not any(
                ipaddress.ip_network(candidate).overlaps(ipaddress.ip_network(n))
                for n in occupied
                if n and ":" not in n
            ):
                env["DEV05_PREFIX"] = f"172.{prefix}"
                break
        else:
            raise RuntimeError("No non-overlapping private fixture subnet")
        for name in ("private", "tls", "evidence"):
            (runtime / name).mkdir(mode=0o700)
        password = secrets.token_urlsafe(36)
        secret_values.append(password)
        (runtime / "private/admin-password").write_text(password)
        (runtime / "private/admin-password").chmod(0o600)
        for name in ("worker-session.json", "browser-session.json"):
            (runtime / "private" / name).write_text("{}")
            (runtime / "private" / name).chmod(0o600)
        (runtime / "tls/state").write_text("healthy")
        cmd(
            [
                "openssl",
                "req",
                "-x509",
                "-newkey",
                "rsa:2048",
                "-nodes",
                "-days",
                "1",
                "-keyout",
                str(runtime / "tls/tls.key"),
                "-out",
                str(runtime / "tls/tls.crt"),
                "-subj",
                "/CN=portal.example.test",
                "-addext",
                "subjectAltName=DNS:portal.example.test",
            ]
        )
        cc("config", "--quiet")
        report["unrelated_before"] = {
            kind: cmd(["docker", *argv]).stdout.decode().split()
            for kind, argv in [
                ("containers", ["ps", "-aq"]),
                ("networks", ["network", "ls", "-q"]),
                ("volumes", ["volume", "ls", "-q"]),
            ]
        }
        print("Building isolated verification images", flush=True)
        cc("build", "api", "frontend", "browser", timeout=1800)
        cc(
            "up",
            "-d",
            "--wait",
            "--wait-timeout",
            "180",
            "postgres",
            "api",
            "frontend",
            "fixture",
            "worker",
            "browser",
            timeout=240,
        )
        manifest = {}
        for service in ("postgres", "api", "frontend", "fixture", "worker", "browser"):
            ident = cc("ps", "-q", service).stdout.decode().strip()
            manifest[service] = json.loads(
                cmd(["docker", "inspect", "--format", "{{json .Image}}", ident]).stdout
            )
        (runtime / "evidence/images.json").write_text(
            json.dumps(manifest, indent=2) + "\n"
        )
        cc("exec", "-T", "browser", "chromium", "--version")
        if args.inject_failure:
            raise RuntimeError("Intentional failure to verify cleanup")
        if not check("synthetic_seed_activation", lambda: api("setup")):
            raise RuntimeError("Seed prerequisite failed")
        check("organizations_sources_templates_collectors", lambda: api("regression"))
        check("live_linux_infrastructure_lifecycle", lambda: api("infrastructure"))
        check("browser_activation_reload_saved_config", lambda: browser("configured"))
        for phase in ("healthy", "failed", "recovered"):
            (runtime / "tls/state").write_text(
                "failed" if phase == "failed" else "healthy"
            )

            def lifecycle(phase=phase):
                api("schedule")
                cc("exec", "-T", "worker", "python", "/fixtures/golden_agent_cycle.py")
                api(phase)

            check("https_get_persisted_" + phase, lifecycle)
            check("browser_diagnostics_" + phase, lambda phase=phase: browser(phase))
        check("tenant_isolation_audit_redaction", lambda: api("isolation"))
        check("https_head_latency_persistence", lambda: api("configure-head"))
        check(
            "https_head_worker_execution",
            lambda: cc(
                "exec", "-T", "worker", "python", "/fixtures/golden_agent_cycle.py"
            ),
        )
        check("https_head_evidence", lambda: api("verify-head"))
        check(
            "browser_saved_api_settings",
            lambda: cc("exec", "-T", "browser", "node", "/verification/settings.mjs"),
        )
        check("worker_authorization_negatives", lambda: api("authorization"))
        check(
            "tls_egress_methods_headers_latency_negatives",
            lambda: cc(
                "exec", "-T", "worker", "python", "/verification/worker_checks.py"
            ),
        )
        check(
            "scoped_existing_regressions",
            lambda: cc("exec", "-T", "api", "python", "/verification/regressions.py"),
        )
        check(
            "frontend_existing_tests_build",
            lambda: cc(
                "exec",
                "-T",
                "frontend",
                "sh",
                "-ec",
                "npm test && npm run lint && npm run build",
            ),
        )
        rows.extend(
            [
                {
                    "name": "genuine_provider_runtime_certification",
                    "status": "BLOCKED",
                    "detail": "No genuine Pentaho, cloud, Kubernetes or customer targets/credentials authorized. Synthetic contracts only.",
                },
                {
                    "name": "production_deployment",
                    "status": "NOT TESTED",
                    "detail": "Strictly prohibited.",
                },
            ]
        )
    except (Exception, KeyboardInterrupt) as error:
        failed = True
        rows.append(
            {"name": "harness_execution", "status": "FAIL", "detail": str(error)}
        )
        print(str(error), file=sys.stderr, flush=True)
    finally:
        # Preserve only redacted artifacts BEFORE destroying this project's resources.
        try:
            session = runtime / "private/session.json"
            if session.exists():
                values = json.loads(session.read_text())
                secret_values.extend(
                    v
                    for k, v in values.items()
                    if any(s in k for s in ("token", "password")) and isinstance(v, str)
                )
            if compose:
                logs = cc("logs", "--no-color", timeout=30, check=False).stdout
                (runtime / "service.log").write_bytes(logs)
            leaked_files = []
            for source in (
                [
                    runtime / "commands.log",
                    runtime / "service.log",
                    *(runtime / "evidence").glob("*"),
                ]
                if (runtime / "evidence").exists()
                else [runtime / "commands.log"]
            ):
                if source.is_file():
                    data = source.read_bytes()
                    if source.suffix != ".png":
                        if any(value.encode() in data for value in secret_values):
                            leaked_files.append(source.name)
                        for value in secret_values:
                            data = data.replace(value.encode(), b"[REDACTED]")
                        import re

                        data = re.sub(
                            rb"(?i)(Bearer|Basic)\s+[A-Za-z0-9+/=_-]+",
                            rb"\1 [REDACTED]",
                            data,
                        )
                    (output / source.name).write_bytes(data)
            rows.append(
                {
                    "name": "raw_artifact_secret_scan",
                    "status": "FAIL" if leaked_files else "PASS",
                    "files": leaked_files,
                }
            )
        except Exception as error:
            failed = True
            rows.append(
                {
                    "name": "artifact_preservation",
                    "status": "FAIL",
                    "detail": str(error),
                }
            )
        cleanup = {"project": project}
        try:
            if compose:
                result = cc(
                    "down",
                    "--volumes",
                    "--remove-orphans",
                    "--timeout",
                    "10",
                    timeout=90,
                    check=False,
                )
                cleanup["compose_down_exit"] = result.returncode
                for kind, args_ in [
                    ("containers", ["ps", "-aq"]),
                    ("networks", ["network", "ls", "-q"]),
                    ("volumes", ["volume", "ls", "-q"]),
                ]:
                    result = cmd(
                        [
                            "docker",
                            *args_,
                            "--filter",
                            f"label=com.docker.compose.project={project}",
                        ],
                        check=False,
                    )
                    cleanup[kind] = result.stdout.decode().split()
                    if result.returncode:
                        raise RuntimeError("Cleanup inventory failed: " + kind)
                cleanup["status"] = (
                    "PASS"
                    if cleanup["compose_down_exit"] == 0
                    and not any(
                        cleanup[k] for k in ("containers", "networks", "volumes")
                    )
                    else "FAIL"
                )
            else:
                cleanup["status"] = "PASS"
        except Exception as error:
            cleanup.update(status="FAIL", detail=str(error))
        finally:
            shutil.rmtree(runtime)
            cleanup["synthetic_secret_directory_removed"] = not runtime.exists()
        (output / "cleanup.json").write_text(json.dumps(cleanup, indent=2) + "\n")
        rows.append({"name": "project_scoped_cleanup", "status": cleanup["status"]})
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        report["result"] = (
            "FAIL"
            if failed
            or any(row["status"] == "FAIL" for row in rows)
            or cleanup["status"] != "PASS"
            else "PASS_WITH_LIMITATIONS"
        )
        report["artifacts"] = {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in output.iterdir()
            if p.is_file()
        }
        (output / "acceptance.json").write_text(json.dumps(report, indent=2) + "\n")
        print("Evidence:", output, "Result:", report["result"], flush=True)
    return 1 if report["result"] == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
