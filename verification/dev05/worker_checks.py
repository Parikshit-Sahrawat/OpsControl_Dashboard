"""Real TLS negative checks against only the disposable synthetic fixture."""

import json
import os
from pathlib import Path
import ssl
from app.worker.egress import EgressDenied, probe_https
from app.worker.pentaho_status import get_job_status

hosts = ["portal.example.test"]
cidrs = [os.environ["GOLDEN_NETWORK_PREFIX"] + ".77.0/24"]
cfg = {"url": "https://portal.example.test/ready", "expected_status": 200}
results = []


def denied(name, config, allowed_hosts=hosts, allowed_cidrs=cidrs):
    try:
        probe_https(config, allowed_hosts, allowed_cidrs)
    except EgressDenied:
        results.append({"name": name, "status": "PASS"})
    else:
        raise AssertionError("Expected policy denial: " + name)


for method in ("POST", "PUT", "DELETE", "PATCH", "OPTIONS", "TRACE", "CONNECT"):
    denied("forbidden_method_" + method, {**cfg, "method": method})
for header in ("Authorization", "Host", "Cookie", "X-Forwarded-For"):
    denied("forbidden_header_" + header, {**cfg, "headers": {header: "synthetic"}})
denied(
    "header_crlf",
    {**cfg, "headers": {"x-opscontrol-check": "synthetic\r\nInjected: yes"}},
)
denied("unapproved_host", {**cfg, "url": "https://not-approved.invalid/ready"})
denied("outside_approved_cidr", cfg, allowed_cidrs=["10.254.254.0/24"])
denied("plain_http", {**cfg, "url": "http://portal.example.test/ready"})
denied(
    "url_credentials",
    {**cfg, "url": "https://synthetic:secret@portal.example.test/ready"},
)
denied("query_secret", {**cfg, "url": cfg["url"] + "?token=synthetic"})
denied("unapproved_credential_reference", {**cfg, "credential_ref": "not-installed"})
# Default system roots must reject our ephemeral self-signed fixture certificate.
original = os.environ.get("SSL_CERT_FILE")
os.environ["SSL_CERT_FILE"] = "/etc/ssl/certs/ca-certificates.crt"
try:
    try:
        probe_https(cfg, hosts, cidrs)
    except ssl.SSLCertVerificationError:
        results.append({"name": "untrusted_tls", "status": "PASS"})
    else:
        raise AssertionError("Untrusted TLS unexpectedly accepted")
finally:
    os.environ["SSL_CERT_FILE"] = original
# A second alias points at the same peer, but is absent from certificate SAN.
try:
    probe_https(
        {**cfg, "url": "https://wrong.example.test/ready"},
        ["wrong.example.test"],
        cidrs,
    )
except ssl.SSLCertVerificationError:
    results.append({"name": "tls_hostname_mismatch", "status": "PASS"})
else:
    raise AssertionError("Wrong TLS hostname accepted")
slow = probe_https(
    {**cfg, "url": "https://portal.example.test/slow", "max_response_time_ms": 1},
    hosts,
    cidrs,
)
assert (
    slow["outcome"] == "ASSERTION_FAILED"
    and slow["http_status"] == 200
    and slow["response_time_ms"] > 1
)
results.append(
    {
        "name": "real_latency_assertion_failure",
        "status": "PASS",
        "latency_ms": slow["response_time_ms"],
    }
)
# Real TLS transport into the existing read-only Carte parser; synthetic, not certification.
os.environ["OPSCONTROL_LOCAL_ALLOWED_HOSTS"] = hosts[0]
os.environ["OPSCONTROL_LOCAL_ALLOWED_CIDRS"] = cidrs[0]
carte = get_job_status(
    {
        "url": "https://portal.example.test",
        "job_name": "DEV05 synthetic job",
        "execution_id": "dev05-1",
        "allowed_hosts": hosts,
        "allowed_cidrs": cidrs,
    }
)
assert carte["execution_id"] == "dev05-1" and carte["execution_status"] == "SUCCESS"
results.append({"name": "synthetic_carte_tls_parser", "status": "PASS"})
Path("/golden/evidence/worker-negatives.json").write_text(
    json.dumps(results, indent=2) + "\n"
)
print("Real TLS, policy, method/header and synthetic Carte checks PASS:", len(results))
