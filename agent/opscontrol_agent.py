#!/usr/bin/env python3
"""OpsControl Agent supervises upstream OTel; never executes backend shell commands."""

import argparse, glob, hashlib, json, os, platform, signal, ssl, subprocess, tempfile, threading, time
from pathlib import Path
from urllib.request import Request, build_opener, HTTPSHandler, HTTPRedirectHandler
from urllib.error import HTTPError
from urllib.parse import urlsplit

VERSION = "1.5.0"
RUNTIME_VERSION = "0.123.0"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise RuntimeError("Management redirects forbidden")


class Agent:
    def __init__(self, home, backend, runtime, stop=None, poll_seconds=30):
        if not 5 <= poll_seconds <= 300:
            raise ValueError("Agent poll interval must be 5–300 seconds")
        self.poll_seconds = poll_seconds
        self.home = Path(home)
        self.home.mkdir(parents=True, exist_ok=True)
        self.backend = backend.rstrip("/")
        self.runtime = str(Path(runtime).resolve())
        self.stop = stop or threading.Event()
        self.process = None
        self.applied = None
        self.checksum = None
        self.renew_at = 0
        self.next_service_observation = 0
        self.agent_configuration = {"services": []}
        self.methods = []
        self.service_failures = []
        parsed = urlsplit(self.backend)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.path not in ("", "/")
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Backend must be a credential-free HTTPS origin")
        self.client = build_opener(
            NoRedirect(), HTTPSHandler(context=ssl.create_default_context())
        )
        self.credentials = self.home / "identity.json"
        self.state = self.home / "state.json"
        self.config = self.home / "otel.yaml"
        self.token = (
            json.loads(self.credentials.read_text())["access_token"]
            if self.credentials.exists()
            else None
        )
        if self.state.exists():
            state = json.loads(self.state.read_text())
            self.applied = state.get("applied_revision")
            self.checksum = state.get("sha256")
            self.methods = state.get("method_snapshot", [])
            from service_health import configuration

            self.agent_configuration = configuration(
                state.get("agent_configuration", {})
            )
        result = subprocess.run(
            [self.runtime, "--version"], capture_output=True, text=True, timeout=10
        )
        if result.returncode or RUNTIME_VERSION not in result.stdout:
            raise RuntimeError("OTel runtime version mismatch")

    def request(self, path, body=None):
        req = Request(
            self.backend + "/api/v1/agent" + path,
            data=None if body is None else json.dumps(body).encode(),
            headers={
                "Content-Type": "application/json",
                **({"Authorization": "Bearer " + self.token} if self.token else {}),
            },
        )
        with self.client.open(req, timeout=15) as r:
            data = r.read(2 * 1024 * 1024 + 1)
            if len(data) > 2 * 1024 * 1024:
                raise RuntimeError("Management response too large")
            return json.loads(data)

    def write_private(self, path, content):
        fd, temp = tempfile.mkstemp(dir=self.home)
        try:
            if os.name != "nt":
                os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, path)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)

    def enroll(self, enrollment_file, force=False):
        if self.token and not force:
            return
        file = Path(enrollment_file)
        if not file.exists():
            raise RuntimeError("Enrollment file missing")
        result = self.request(
            "/register",
            {
                "enrollment_token": file.read_text().strip(),
                "hostname": platform.node(),
                "os_type": platform.system(),
                "version": VERSION,
                "runtime_version": RUNTIME_VERSION,
            },
        )
        if self.credentials.exists():
            original = self.credentials.read_text()
            old = json.loads(original)
            if old.get("agent_id") != result.get("agent_id"):
                raise RuntimeError("REENROLLMENT_RESOURCE_MISMATCH_USE_SEPARATE_HOME")
            self.write_private(
                self.home
                / ("identity.before-reenrollment." + str(time.time_ns()) + ".json"),
                original,
            )
        self.write_private(self.credentials, json.dumps(result))
        self.token = result["access_token"]
        file.unlink()

    def preflight(self, version):
        for method in version["method_snapshot"]:
            if not method["enabled"] or method.get("deleted_at"):
                continue
            c = method["configuration"]
            if method["method_type"] == "FILE_LOG" and c["source"] == "FILE":
                for pattern in c["paths"]:
                    paths = glob.glob(pattern)
                    if not paths:
                        raise RuntimeError("LOG_PATH_NOT_FOUND")
                    for path in paths:
                        if Path(path).resolve().is_relative_to(self.home.resolve()):
                            raise RuntimeError("AGENT_PRIVATE_PATH_DENIED")
                        # Actual open under the service identity, not UI metadata.
                        with open(path, "rb") as stream:
                            stream.read(1)
            if method["method_type"] == "FILE_LOG" and c["source"] == "JOURNALD":
                result = subprocess.run(
                    ["journalctl", "--no-pager", "-n", "1"],
                    capture_output=True,
                    timeout=10,
                )
                if result.returncode:
                    raise RuntimeError("JOURNAL_PERMISSION_DENIED")
            if method["method_type"] == "FILE_LOG" and c["source"] == "WINDOWS_EVENT":
                result = subprocess.run(
                    [
                        "powershell.exe",
                        "-NoProfile",
                        "-NonInteractive",
                        "-Command",
                        "Get-WinEvent -LogName '"
                        + c["channel"].replace("'", "''")
                        + "' -MaxEvents 1 -ErrorAction Stop | Out-Null",
                    ],
                    capture_output=True,
                    timeout=10,
                )
                if result.returncode:
                    raise RuntimeError("EVENT_LOG_PERMISSION_DENIED")

    def apply(self, version):
        if version["runtime_version"] != RUNTIME_VERSION:
            raise RuntimeError("RUNTIME_VERSION_MISMATCH")
        text = version["yaml_text"]
        if hashlib.sha256(text.encode()).hexdigest() != version["sha256"]:
            raise RuntimeError("CONFIG_CHECKSUM_MISMATCH")
        from service_health import configuration

        runtime_configuration = configuration(version.get("agent_configuration", {}))
        self.preflight(version)
        candidate = self.home / "candidate.yaml"
        self.write_private(candidate, text)
        env = {
            **os.environ,
            "OPSCONTROL_AGENT_TOKEN": self.token,
            "OPSCONTROL_AGENT_STATE_DIR": str(self.home.resolve()),
        }
        result = subprocess.run(
            [self.runtime, "validate", "--config", str(candidate)],
            env=env,
            capture_output=True,
            timeout=30,
        )
        if result.returncode:
            raise RuntimeError("COLLECTOR_CONFIG_INVALID")
        previous = self.config.read_text() if self.config.exists() else None
        self.stop_runtime()
        self.write_private(self.config, text)
        try:
            self.start_runtime()
            if self.process.poll() is not None:
                raise RuntimeError("COLLECTOR_START_FAILED")
        except Exception as start_error:
            if previous:
                self.write_private(self.config, previous)
                self.start_runtime()
            else:
                self.config.unlink(missing_ok=True)
            raise RuntimeError("COLLECTOR_START_FAILED") from start_error
        self.applied = version["revision"]
        self.checksum = version["sha256"]
        self.agent_configuration = runtime_configuration
        self.methods = version["method_snapshot"]
        self.write_private(
            self.state,
            json.dumps(
                {
                    "applied_revision": self.applied,
                    "sha256": version["sha256"],
                    "agent_configuration": self.agent_configuration,
                    "method_snapshot": self.methods,
                }
            ),
        )

    def start_runtime(self):
        # Runtime log is private. Do not forward full subprocess errors/secrets.
        log = open(self.home / "runtime.log", "ab")
        if os.name != "nt":
            os.chmod(self.home / "runtime.log", 0o600)
        try:
            self.process = subprocess.Popen(
                [self.runtime, "--config", str(self.config)],
                env={
                    **os.environ,
                    "OPSCONTROL_AGENT_TOKEN": self.token,
                    "OPSCONTROL_AGENT_STATE_DIR": str(self.home.resolve()),
                },
                stdout=log,
                stderr=subprocess.STDOUT,
            )
        finally:
            log.close()
        time.sleep(0.5)

    def stop_runtime(self):
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()

    def run(self, enrollment_file):
        self.enroll(enrollment_file)
        if self.config.exists():
            # An offline restart may reuse only the locally authenticated,
            # previously applied checksum; corruption never becomes a rollout.
            if (
                not self.checksum
                or hashlib.sha256(self.config.read_bytes()).hexdigest() != self.checksum
            ):
                raise RuntimeError("CONFIG_CHECKSUM_MISMATCH")
            result = subprocess.run(
                [self.runtime, "validate", "--config", str(self.config)],
                env={
                    **os.environ,
                    "OPSCONTROL_AGENT_TOKEN": self.token,
                    "OPSCONTROL_AGENT_STATE_DIR": str(self.home.resolve()),
                },
                capture_output=True,
                timeout=30,
            )
            if result.returncode:
                raise RuntimeError("COLLECTOR_CONFIG_INVALID")
            self.start_runtime()
        try:
            while not self.stop.is_set():
                error = None
                try:
                    if time.monotonic() >= self.renew_at:
                        renewed = self.request("/credentials/renew", {})
                        identity = json.loads(self.credentials.read_text())
                        identity["expires_at"] = renewed["expires_at"]
                        self.write_private(self.credentials, json.dumps(identity))
                        self.renew_at = time.monotonic() + 86400
                except Exception:
                    error = "CREDENTIAL_RENEWAL_FAILED"
                try:
                    version = self.request("/configuration")
                    if version["revision"] != self.applied:
                        self.apply(version)
                except HTTPError as e:
                    if e.code in (401, 403):
                        self.stop_runtime()
                        error = "AUTHORIZATION_REVOKED_OR_TARGET_DISABLED"
                    elif e.code != 404:
                        error = "MANAGEMENT_REQUEST_FAILED"
                except PermissionError:
                    error = "FILE_PERMISSION_DENIED"
                except Exception as e:
                    error = (
                        str(e)
                        if str(e)
                        in (
                            "LOG_PATH_NOT_FOUND",
                            "AGENT_PRIVATE_PATH_DENIED",
                            "JOURNAL_PERMISSION_DENIED",
                            "EVENT_LOG_PERMISSION_DENIED",
                            "CONFIG_CHECKSUM_MISMATCH",
                            "COLLECTOR_CONFIG_INVALID",
                            "COLLECTOR_START_FAILED",
                        )
                        else "CONFIG_APPLY_FAILED"
                    )
                running = self.process is not None and self.process.poll() is None
                if self.applied and not running and not error:
                    try:
                        self.start_runtime()
                        running = self.process.poll() is None
                    except Exception:
                        error = "COLLECTOR_RESTART_FAILED"
                if (
                    running
                    and time.monotonic() >= self.next_service_observation
                    and any(
                        self.agent_configuration.get(k)
                        for k in ("services", "processes", "native_os_metrics")
                    )
                ):
                    try:
                        from service_health import envelope

                        telemetry, failures = envelope(
                            self.agent_configuration["services"],
                            platform.system(),
                            platform.node(),
                            self.agent_configuration.get("processes", []),
                            self.agent_configuration.get("native_os_metrics", False),
                            self.methods,
                        )
                        self.service_failures = failures
                        self.request("/otlp/v1/metrics", telemetry)
                        self.next_service_observation = (
                            time.monotonic()
                            + self.agent_configuration.get(
                                "service_interval_seconds", 30
                            )
                        )
                        if failures and not error:
                            error = "SERVICE_QUERY_UNAVAILABLE"
                    except Exception:
                        if not error:
                            error = "SERVICE_TELEMETRY_UNAVAILABLE"
                try:
                    from service_health import method_observations

                    observations = method_observations(
                        self.methods, running, self.home, self.service_failures
                    )
                    self.request(
                        "/heartbeat",
                        {
                            "version": VERSION,
                            "runtime_version": RUNTIME_VERSION,
                            "applied_revision": self.applied,
                            "configuration_sha256": self.checksum,
                            "health": (
                                "ERROR"
                                if error
                                else "RUNNING" if running else "STOPPED"
                            ),
                            "error_code": error,
                            "method_observations": observations,
                        },
                    )
                except Exception:
                    pass  # next heartbeat retries; server liveness expires
                self.stop.wait(
                    min(
                        self.poll_seconds,
                        self.agent_configuration.get("service_interval_seconds", 30),
                    )
                )
        finally:
            self.stop_runtime()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", required=True)
    parser.add_argument("--backend", required=True)
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--enrollment-file")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--reenroll-only", action="store_true")
    mode.add_argument("--rotate-credentials-only", action="store_true")
    parser.add_argument("--poll-seconds", type=int, default=30)
    args = parser.parse_args()
    stop = threading.Event()
    for s in (signal.SIGTERM, signal.SIGINT):
        signal.signal(s, lambda *_: stop.set())
    agent = Agent(args.home, args.backend, args.runtime, stop, args.poll_seconds)
    if args.rotate_credentials_only:
        result = agent.request("/credentials/rotate", {})
        identity = json.loads(agent.credentials.read_text())
        agent.write_private(
            agent.home / ("identity.before-rotation." + str(time.time_ns()) + ".json"),
            json.dumps(identity),
        )
        identity.update({key: result[key] for key in ("access_token", "expires_at")})
        agent.write_private(agent.credentials, json.dumps(identity))
        return  # Restart the managed service to load the rotated process environment.
    if not args.enrollment_file:
        parser.error("--enrollment-file is required for enrollment/run")
    if args.reenroll_only:
        agent.enroll(args.enrollment_file, force=True)
        return
    agent.run(args.enrollment_file)


if __name__ == "__main__":
    main()
