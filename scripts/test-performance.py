#!/usr/bin/env python3
"""Bounded measured load against an explicitly authorized owned local test stack."""

import argparse
import concurrent.futures
import ipaddress
import json
import math
import os
import socket
import ssl
import statistics
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def percentile(values, fraction):
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * fraction) - 1)]


def local_base(value):
    url = urllib.parse.urlsplit(value)
    if (
        url.scheme not in {"http", "https"}
        or not url.hostname
        or url.username
        or url.password
        or url.query
        or url.fragment
        or url.path not in {"", "/"}
    ):
        raise ValueError(
            "A local HTTP(S) origin without credentials or paths is required"
        )
    if url.hostname != "localhost":
        try:
            literal = ipaddress.ip_address(url.hostname)
        except ValueError:
            raise ValueError(
                "Only localhost or literal loopback addresses are permitted"
            ) from None
        if not literal.is_loopback:
            raise ValueError("Only loopback addresses are permitted")
    addresses = socket.getaddrinfo(
        url.hostname, url.port or 443, type=socket.SOCK_STREAM
    )
    if not addresses or not all(
        ipaddress.ip_address(row[4][0]).is_loopback for row in addresses
    ):
        raise ValueError("Performance runner only permits loopback destinations")
    return value.rstrip("/")


def run_batch(base, token, mode, count, concurrency, timeout, tls):
    def request(index):
        data = None
        endpoint = "/api/v1/unified/resources?limit=25"
        if mode == "ingestion":
            endpoint = "/api/v1/agent/otlp/v1/metrics"
            # Every payload has a unique timestamp; transport dedup cannot turn
            # repeated cached envelopes into misleading throughput evidence.
            data = json.dumps(
                {
                    "resourceMetrics": [
                        {
                            "resource": {
                                "attributes": [
                                    {
                                        "key": "evidence.origin",
                                        "value": {
                                            "stringValue": "CONTROLLED_LOAD_TEST"
                                        },
                                    }
                                ]
                            },
                            "scopeMetrics": [
                                {
                                    "scope": {"name": "opscontrol.local.performance"},
                                    "metrics": [
                                        {
                                            "name": "opscontrol.lab.performance",
                                            "unit": "1",
                                            "gauge": {
                                                "dataPoints": [
                                                    {
                                                        "timeUnixNano": str(
                                                            time.time_ns()
                                                        ),
                                                        "asDouble": index,
                                                    }
                                                ]
                                            },
                                        }
                                    ],
                                }
                            ],
                        }
                    ]
                }
            ).encode()
        started = time.perf_counter()
        status = 0
        error = None
        try:
            opener = urllib.request.build_opener(
                NoRedirect(), urllib.request.HTTPSHandler(context=tls)
            )
            req = urllib.request.Request(
                base + endpoint,
                data=data,
                headers={
                    "Authorization": "Bearer " + token,
                    "Content-Type": "application/json",
                },
            )
            with opener.open(req, timeout=timeout) as response:
                status = response.status
                payload = response.read(2 * 1024 * 1024)
                decoded = json.loads(payload)
                if not isinstance(decoded, dict):
                    raise ValueError("Expected JSON object response")
                if mode == "api" and not isinstance(decoded.get("items"), list):
                    error = "INVALID_INVENTORY_RESPONSE"
                partial = decoded.get("partialSuccess", {})
                if partial.get("rejectedDataPoints", "0") not in {"0", 0}:
                    error = "PARTIAL_INGESTION_REJECTION"
        except urllib.error.HTTPError as exc:
            status = exc.code
            error = "HTTP_ERROR"
        except (OSError, ValueError, urllib.error.URLError):
            error = "TRANSPORT_OR_RESPONSE_ERROR"
        return {
            "latency_ms": (time.perf_counter() - started) * 1000,
            "status": status,
            "failed": error is not None or not 200 <= status < 300,
        }

    start = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
        results = list(pool.map(request, range(count)))
    seconds = time.perf_counter() - start
    latency = [row["latency_ms"] for row in results]
    return {
        "mode": mode,
        "requests": count,
        "concurrency": concurrency,
        "duration_seconds": round(seconds, 3),
        "requests_per_second": round(count / seconds, 3),
        "mean_latency_ms": round(statistics.mean(latency), 3),
        "p50_latency_ms": round(percentile(latency, 0.5), 3),
        "p95_latency_ms": round(percentile(latency, 0.95), 3),
        "p99_latency_ms": round(percentile(latency, 0.99), 3),
        "error_rate": sum(row["failed"] for row in results) / count,
        "status_counts": dict(Counter(str(row["status"]) for row in results)),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if os.getenv("OPSCONTROL_PERFORMANCE_ACCEPTANCE") != "1" or os.getenv(
        "ENV"
    ) not in {"test", "development"}:
        parser.error(
            "Requires ENV=test/development and OPSCONTROL_PERFORMANCE_ACCEPTANCE=1"
        )
    if os.name != "nt" and args.inputs.stat().st_mode & 0o077:
        parser.error("Credential input file must be owner-only (chmod 600)")
    cfg = json.loads(args.inputs.read_text())
    base = local_base(cfg["base_url"])
    count, concurrency = int(cfg.get("requests", 200)), int(cfg.get("concurrency", 8))
    if not 1 <= count <= 10000 or not 1 <= concurrency <= 32:
        parser.error("Bounds: 1–10000 requests, 1–32 concurrent workers")
    timeout = float(cfg.get("timeout_seconds", 10))
    if not 0 < timeout <= 60:
        parser.error("Request timeout must be within 0–60 seconds")
    tls = ssl.create_default_context(cafile=cfg.get("ca_file"))
    reports = []
    for mode, key in (("api", "api_token"), ("ingestion", "agent_token")):
        if not cfg.get(key):
            parser.error(f"Missing {key}; both actual API and ingestion must be tested")
        reports.append(
            run_batch(base, cfg[key], mode, count, concurrency, timeout, tls)
        )
    checks = []
    for report in reports:
        passed = (
            report["error_rate"] <= float(cfg.get("max_error_rate", 0))
            and report["p95_latency_ms"] <= float(cfg.get("max_p95_ms", 2000))
            and report["requests_per_second"]
            >= float(cfg.get("min_requests_per_second", 1))
        )
        checks.append(passed)
        report["thresholds_passed"] = passed
    evidence = {
        "status": "PASS" if all(checks) else "FAIL",
        "evidence_origin": "CONTROLLED_LOAD_TEST",
        "limits": "Loopback, bounded load; measures HTTP acceptance, not production capacity or database restoration.",
        "thresholds": {
            key: cfg.get(key, default)
            for key, default in (
                ("max_error_rate", 0),
                ("max_p95_ms", 2000),
                ("min_requests_per_second", 1),
            )
        },
        "results": reports,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps({"status": evidence["status"], "results": reports}))
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
