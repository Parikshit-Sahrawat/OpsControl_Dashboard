"""DEV-04.3: bounded, safe API-check configuration shared by activation and dispatch.

This first slice deliberately preserves the existing HTTPS GET-only worker protocol.
More methods or request bodies require a separately versioned worker capability.
"""
from fastapi import HTTPException

from app.worker.egress import EgressDenied, check_target

ALLOWED_METHODS = frozenset({"GET", "HEAD"})
ALLOWED_HEADERS = frozenset({"x-opscontrol-check"})
MAX_HEADER_VALUE = 256


def build_api_config(collector_config, source, worker):
    """Validate API monitoring settings without admitting unsafe outbound requests."""
    cfg = collector_config or {}
    if not isinstance(cfg, dict):
        raise HTTPException(422, "API collector configuration must be an object")
    config = {
        "url": cfg.get("url") or source.endpoint,
        "expected_status": cfg.get("expected_status", 200),
        "timeout_seconds": cfg.get("timeout_seconds", 8),
    }
    method = cfg.get("method", "GET")
    if not isinstance(method, str) or method not in ALLOWED_METHODS:
        raise HTTPException(422, "API method must be GET or HEAD")
    config["method"] = method
    headers = cfg.get("headers", {})
    if not isinstance(headers, dict) or len(headers) > 8:
        raise HTTPException(422, "API headers must be an object with at most eight entries")
    normalized = {}
    for name, value in headers.items():
        if not isinstance(name, str) or name.lower() not in ALLOWED_HEADERS:
            raise HTTPException(422, "API header is not approved")
        if (not isinstance(value, str) or not value or len(value) > MAX_HEADER_VALUE
                or any(ord(ch) < 32 or ord(ch) > 126 for ch in value)):
            raise HTTPException(422, "Invalid API header value")
        key = name.lower()
        if key in normalized:
            raise HTTPException(422, "Duplicate API header")
        normalized[key] = value
    if normalized:
        config["headers"] = normalized
    if any(key in cfg for key in ("body", "payload", "query", "params", "follow_redirects")):
        raise HTTPException(422, "API request bodies, queries and redirects are not supported")
    if not isinstance(config["url"], str):
        raise HTTPException(422, "Target HTTPS URL is missing")
    try:
        check_target(config["url"], worker.allowed_hosts, worker.allowed_cidrs)
    except EgressDenied as exc:
        raise HTTPException(422, str(exc)) from None
    if type(config["expected_status"]) is not int or not 100 <= config["expected_status"] <= 599:
        raise HTTPException(422, "Invalid expected_status")
    if type(config["timeout_seconds"]) is not int or not 1 <= config["timeout_seconds"] <= 10:
        raise HTTPException(422, "Timeout must be 1..10 seconds")
    latency=cfg.get("max_response_time_ms")
    if latency is not None:
        if type(latency) is not int or not 1 <= latency <= 10000:
            raise HTTPException(422, "Maximum response time must be 1..10000 ms")
        config["max_response_time_ms"]=latency
    return config
