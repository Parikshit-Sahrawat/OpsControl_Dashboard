#!/usr/bin/env python3
"""OpsControl Agent supervises upstream OTel; never executes backend shell commands."""
import argparse, glob, hashlib, json, os, platform, signal, ssl, subprocess, tempfile, threading, time
from pathlib import Path
from urllib.request import Request, build_opener, HTTPSHandler, HTTPRedirectHandler
from urllib.error import HTTPError
from urllib.parse import urlsplit

VERSION = "1.0.0"
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
            self.applied = json.loads(self.state.read_text()).get("applied_revision")
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

    def enroll(self, enrollment_file):
        if self.token:
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
                        + c["channel"]
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
        self.start_runtime()
        if self.process.poll() is not None:
            if previous:
                self.write_private(self.config, previous)
                self.start_runtime()
            raise RuntimeError("COLLECTOR_START_FAILED")
        self.applied = version["revision"]
        self.write_private(
            self.state,
            json.dumps({"applied_revision": self.applied, "sha256": version["sha256"]}),
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
            self.start_runtime()
        try:
            while not self.stop.is_set():
                error = None
                try:
                    version = self.request("/configuration")
                    if version["revision"] != self.applied:
                        self.apply(version)
                except HTTPError as e:
                    if e.code != 404:
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
                try:
                    self.request(
                        "/heartbeat",
                        {
                            "version": VERSION,
                            "runtime_version": RUNTIME_VERSION,
                            "applied_revision": self.applied,
                            "health": (
                                "ERROR"
                                if error
                                else "RUNNING" if running else "STOPPED"
                            ),
                            "error_code": error,
                        },
                    )
                except Exception:
                    pass  # next heartbeat retries; server liveness expires
                self.stop.wait(self.poll_seconds)
        finally:
            self.stop_runtime()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", required=True)
    parser.add_argument("--backend", required=True)
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--enrollment-file", required=True)
    parser.add_argument("--poll-seconds", type=int, default=30)
    args = parser.parse_args()
    stop = threading.Event()
    for s in (signal.SIGTERM, signal.SIGINT):
        signal.signal(s, lambda *_: stop.set())
    Agent(args.home, args.backend, args.runtime, stop, args.poll_seconds).run(
        args.enrollment_file
    )


if __name__ == "__main__":
    main()
