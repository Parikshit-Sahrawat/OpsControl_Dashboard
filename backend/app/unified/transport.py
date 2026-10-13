"""Read-only native probes: deployment allowlists, pinned DNS, no redirects."""

import http.client, json, os, ssl, time, base64, ipaddress
from urllib.parse import urlsplit, urlunsplit, parse_qsl
from app.worker.egress import policy_cidrs, resolve_target, EgressDenied, check_target
from app.telemetry.configuration import env_reference
from app.telemetry.delivery import secret


class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host, ip, port, timeout):
        super().__init__(
            host, port=port, timeout=timeout, context=ssl.create_default_context()
        )
        self.pinned_ip = ip

    def connect(self):
        socket = self._create_connection(
            (self.pinned_ip, self.port), self.timeout, self.source_address
        )
        self.sock = self._context.wrap_socket(socket, server_hostname=self.host)


class PinnedHTTP(http.client.HTTPConnection):
    def __init__(self, host, ip, port, timeout):
        super().__init__(host, port=port, timeout=timeout)
        self.pinned_ip = ip

    def connect(self):
        self.sock = self._create_connection(
            (self.pinned_ip, self.port), self.timeout, self.source_address
        )


def request(url, configuration, metadata=False):
    parsed = urlsplit(url)
    host = parsed.hostname
    allowed = {
        x.strip().lower()
        for x in os.getenv("OPSCONTROL_NATIVE_ALLOWED_HOSTS", "").split(",")
        if x.strip()
    }
    ports = {
        int(x)
        for x in os.getenv("OPSCONTROL_NATIVE_ALLOWED_PORTS", "443").split(",")
        if x.strip().isdigit()
    }
    cidrs = [
        x.strip()
        for x in os.getenv("OPSCONTROL_NATIVE_ALLOWED_CIDRS", "").split(",")
        if x.strip()
    ]
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if host not in allowed or port not in ports:
        raise EgressDenied("Native target host/port is not deployment-approved")
    if (
        parsed.username
        or parsed.password
        or parsed.fragment
        or parsed.scheme not in {"http", "https"}
    ):
        raise EgressDenied("Invalid native endpoint")
    if any(
        key.lower()
        in {"token", "password", "api_key", "apikey", "secret", "authorization"}
        for key, value in parse_qsl(parsed.query)
    ):
        raise EgressDenied("Query credentials are forbidden")
    if any(ord(c) < 33 or ord(c) > 126 for c in url):
        raise EgressDenied("Invalid native URL encoding")
    if parsed.scheme == "http" and os.getenv("OPSCONTROL_NATIVE_ALLOW_HTTP") != "1":
        raise EgressDenied("Unencrypted HTTP requires explicit deployment approval")
    # Reuse the established forbidden-address/network policy. Port/protocol
    # approval is separate and never controlled by a resource request payload.
    networks = policy_cidrs(cidrs)
    try:
        ipaddress.ip_address(host)
    except ValueError:
        check_target("https://" + host + (parsed.path or "/"), [host], cidrs)
    addresses = resolve_target(host, networks)
    connection = (PinnedHTTPS if parsed.scheme == "https" else PinnedHTTP)(
        host, str(addresses), port, int(configuration.get("timeout_seconds", 10))
    )
    headers = {
        "User-Agent": "OpsControl-Native-Probe/1.0",
        "Accept": "application/json, text/plain",
        **configuration.get("headers", {}),
    }
    auth = configuration.get(
        "auth_type",
        "BEARER" if metadata and configuration.get("credential_ref") else "NONE",
    )
    if auth != "NONE":
        if parsed.scheme != "https":
            raise EgressDenied("Authenticated probes require TLS")
        ref = configuration.get("credential_ref")
        env_reference(ref)
        value = secret(ref)
        if auth == "BASIC":
            credentials = json.loads(value)
            value = base64.b64encode(
                (credentials["username"] + ":" + credentials["password"]).encode()
            ).decode()
            headers["Authorization"] = "Basic " + value
        else:
            header = configuration.get("credential_header", "Authorization")
            if header not in {"Authorization", "icSessionId", "INFA-SESSION-ID"}:
                raise ValueError("Unsupported managed authentication header")
            headers[header] = "Bearer " + value if header == "Authorization" else value
    start = time.perf_counter()
    try:
        connection.request(
            configuration.get("method", "GET"),
            urlunsplit(("", "", parsed.path or "/", parsed.query, "")),
            headers=headers,
        )
        response = connection.getresponse()
        data = response.read(1024 * 1024 + 1 if metadata else 4097)
        if metadata and len(data) > 1024 * 1024:
            raise ValueError("Provider response exceeds bound")
        elapsed = (time.perf_counter() - start) * 1000
        evidence = {
            "outcome": (
                "SUCCESS" if 200 <= response.status < 300 else "ASSERTION_FAILED"
            ),
            "http_status": response.status,
            "response_time_ms": elapsed,
            "response_size_bytes": len(data),
            "probe_location": "NATIVE_BACKEND",
        }
        if metadata:
            if response.status != 200:
                raise ValueError("Provider read failed")
            return evidence, json.loads(data)
        return evidence, None
    finally:
        connection.close()
