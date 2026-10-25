#!/usr/bin/env python3
"""Isolated TLS/auth-forwarding gateway smoke; owns no database or demo volumes."""
import importlib.util
import json
import os
import secrets
import shutil
import ssl
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def main():
    private = Path(tempfile.mkdtemp(prefix="opscontrol-gateway-smoke-"))
    private.chmod(0o700)
    name = "opscontrol-gateway-" + secrets.token_hex(5)
    api_name, gateway_name = name + "-api", name + "-tls"
    token = secrets.token_urlsafe(32)
    completed = False

    def run(args):
        result = subprocess.run(
            ["docker", *args], capture_output=True, text=True, timeout=120
        )
        if result.returncode:
            (private / "docker-diagnostics.log").write_text(result.stderr)
            raise RuntimeError(
                "Owned gateway smoke failed; private diagnostics: " + str(private)
            )
        return result.stdout.strip()

    try:
        spec = importlib.util.spec_from_file_location(
            "demo_gateway_tls", ROOT / "scripts/init-demo-gateway.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.initialize(private / "gateway")
        # Idempotent reuse validates existing credentials rather than replacing them.
        original = (private / "gateway/tls.crt").read_bytes()
        module.initialize(private / "gateway")
        assert original == (private / "gateway/tls.crt").read_bytes()
        (private / "fixture.py").write_text(
            """import os,json
from http.server import HTTPServer,BaseHTTPRequestHandler
class H(BaseHTTPRequestHandler):
 def log_message(self,*args): pass
 def do_GET(self):
  self.send_response(200 if self.path=="/health" else 401); self.end_headers(); self.wfile.write(b'{}')
 def do_POST(self):
  self.rfile.read(int(self.headers.get("Content-Length",0)))
  self.send_response(200 if self.headers.get("Authorization")=="Bearer "+os.environ["SMOKE_AUTH_TOKEN"] else 401)
  self.end_headers(); self.wfile.write(b'{}')
HTTPServer(("0.0.0.0",8000),H).serve_forever()
"""
        )
        run(["network", "create", name])
        run(
            [
                "run",
                "--detach",
                "--name",
                api_name,
                "--network",
                name,
                "--network-alias",
                "api",
                "--env",
                "SMOKE_AUTH_TOKEN=" + token,
                "--volume",
                str(private / "fixture.py") + ":/fixture.py:ro",
                "python:3.12-alpine",
                "python",
                "/fixture.py",
            ]
        )
        run(
            [
                "run",
                "--detach",
                "--name",
                gateway_name,
                "--network",
                name,
                "--read-only",
                "--security-opt",
                "no-new-privileges:true",
                "--cap-drop",
                "ALL",
                "--cap-add",
                "CHOWN",
                "--cap-add",
                "SETUID",
                "--cap-add",
                "SETGID",
                "--cap-add",
                "DAC_OVERRIDE",
                "--tmpfs",
                "/tmp",
                "--tmpfs",
                "/var/run",
                "--tmpfs",
                "/var/cache/nginx",
                "--publish",
                "127.0.0.1::8443",
                "--volume",
                str(ROOT / "deploy/gateway/nginx.conf") + ":/etc/nginx/nginx.conf:ro",
                "--volume",
                str(private / "gateway/tls.crt") + ":/etc/opscontrol/tls/tls.crt:ro",
                "--volume",
                str(private / "gateway/tls.key") + ":/etc/opscontrol/tls/tls.key:ro",
                os.environ.get("OPSCONTROL_GATEWAY_TEST_IMAGE", "nginx:1.28-alpine"),
                "nginx",
                "-g",
                "daemon off;",
            ]
        )
        port = int(run(["port", gateway_name, "8443/tcp"]).rsplit(":", 1)[1])
        base = "https://localhost:" + str(port)
        trusted = ssl.create_default_context(cafile=str(private / "gateway/ca.crt"))
        for _ in range(60):
            try:
                with urlopen(base + "/health", context=trusted, timeout=2) as response:
                    assert response.status == 200
                break
            except (URLError, OSError):
                time.sleep(0.2)
        else:
            raise RuntimeError("Gateway TLS/health startup failed")
        try:
            urlopen(base + "/health", timeout=2)
        except URLError:
            pass
        else:
            raise AssertionError("Untrusted development CA unexpectedly accepted")
        for path, auth, expected in [
            ("/api/v1/agent/heartbeat", None, 401),
            ("/api/v1/agent/heartbeat", "Bearer invalid", 401),
            ("/api/v1/agent/heartbeat", "Bearer " + token, 200),
            ("/api/v1/access/employees", "Bearer " + token, 404),
        ]:
            request = Request(
                base + path,
                data=b"{}",
                headers={
                    "Content-Type": "application/json",
                    **({"Authorization": auth} if auth else {}),
                },
            )
            try:
                with urlopen(request, context=trusted, timeout=5) as response:
                    actual = response.status
            except HTTPError as error:
                actual = error.code
            assert actual == expected, (path, actual, expected)
        run(["exec", gateway_name, "nginx", "-t"])
        print(
            json.dumps(
                {
                    "passed": True,
                    "tls_chain_and_hostname_verified": True,
                    "untrusted_ca_rejected": True,
                    "unauthorized_requests_rejected": True,
                    "bearer_forwarding_verified_with_controlled_backend": True,
                    "administration_routes_not_exposed": True,
                    "existing_database_volumes_touched": False,
                }
            )
        )
        completed = True
    finally:
        for container in (gateway_name, api_name):
            if not completed:
                logs = subprocess.run(
                    ["docker", "logs", container], capture_output=True, text=True
                )
                (private / (container + ".log")).write_text(logs.stdout + logs.stderr)
            subprocess.run(["docker", "rm", "--force", container], capture_output=True)
        subprocess.run(["docker", "network", "rm", name], capture_output=True)
        if completed:
            shutil.rmtree(private)


if __name__ == "__main__":
    main()
