"""Read-only target service observation. No shell, restart or arbitrary commands."""

import json, re, subprocess, time


def configuration(value):
    if not isinstance(value, dict) or set(value) - {"services"}:
        raise ValueError("Invalid agent configuration")
    services = value.get("services", [])
    if (
        not isinstance(services, list)
        or len(services) > 50
        or len(set(services)) != len(services)
        or any(
            not isinstance(name, str)
            or not re.fullmatch(r"[A-Za-z0-9_.@ -]{1,200}", name)
            for name in services
        )
    ):
        raise ValueError("Invalid service identity")
    return {"services": services}


def observe(name, os_type):
    if os_type == "Linux":
        result = subprocess.run(
            ["systemctl", "show", "--property=ActiveState", "--value", name],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode:
            raise RuntimeError("SERVICE_QUERY_UNAVAILABLE")
        state = result.stdout.strip()
        if state not in {
            "active",
            "inactive",
            "failed",
            "activating",
            "deactivating",
            "reloading",
        }:
            raise RuntimeError("SERVICE_QUERY_UNKNOWN")
        return 1 if state in {"active", "reloading"} else 0
    if os_type == "Windows":
        # Numeric Service Control Manager state survives localized output.
        result = subprocess.run(
            ["sc.exe", "query", name], capture_output=True, text=True, timeout=10
        )
        if result.returncode:
            raise RuntimeError("SERVICE_QUERY_UNAVAILABLE")
        match = re.search(
            r":\s*([1-7])\s+(?:STOPPED|START_PENDING|STOP_PENDING|RUNNING|CONTINUE_PENDING|PAUSE_PENDING|PAUSED)",
            result.stdout,
        )
        if not match:
            raise RuntimeError("SERVICE_QUERY_UNKNOWN")
        return 1 if match[1] == "4" else 0
    raise RuntimeError("SERVICE_OS_UNSUPPORTED")


def envelope(services, os_type, hostname):
    records = []
    errors = []
    timestamp = str(time.time_ns())
    for name in services:
        try:
            value = observe(name, os_type)
            records.append(
                {
                    "timeUnixNano": timestamp,
                    "asInt": str(value),
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": name}}
                    ],
                }
            )
        except (OSError, subprocess.TimeoutExpired, RuntimeError):
            errors.append(name)
    return {
        "resourceMetrics": [
            {
                "resource": {
                    "attributes": [
                        {"key": "host.name", "value": {"stringValue": hostname}}
                    ]
                },
                "scopeMetrics": [
                    {
                        "scope": {"name": "opscontrol.native-service-health"},
                        "metrics": [
                            {
                                "name": "opscontrol.service.up",
                                "unit": "1",
                                "gauge": {"dataPoints": records},
                            }
                        ],
                    }
                ],
            }
        ]
    }, errors
