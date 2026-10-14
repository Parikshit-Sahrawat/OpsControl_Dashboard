"""Read-only target service observation. No shell, restart or arbitrary commands."""

import json, re, subprocess, time


def configuration(value):
    if not isinstance(value, dict) or set(value) - {
        "services",
        "processes",
        "native_os_metrics",
        "service_interval_seconds",
    }:
        raise ValueError("Invalid agent configuration")
    interval = value.get("service_interval_seconds", 30)
    if (
        not isinstance(interval, int)
        or isinstance(interval, bool)
        or not 5 <= interval <= 3600
    ):
        raise ValueError("Invalid service interval")
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
    processes = value.get("processes", [])
    if (
        not isinstance(processes, list)
        or len(processes) > 50
        or len(set(processes)) != len(processes)
        or any(
            not isinstance(name, str)
            or not re.fullmatch(r"[A-Za-z0-9_.@ -]{1,200}", name)
            for name in processes
        )
    ):
        raise ValueError("Invalid process identity")
    return {
        "services": services,
        "processes": processes,
        "native_os_metrics": bool(value.get("native_os_metrics", False)),
        "service_interval_seconds": interval,
    }


def observe(name, os_type):
    if os_type == "Linux":
        result = subprocess.run(
            ["systemctl", "show", "--property=ActiveState", "--value", name],
            capture_output=True,
            text=True,
            timeout=3,
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
            ["sc.exe", "query", name], capture_output=True, text=True, timeout=3
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


def envelope(
    services, os_type, hostname, processes=None, native_os_metrics=False, methods=None
):
    records = []
    errors = []
    timestamp = str(time.time_ns())
    deadline = time.monotonic() + 15
    for name in services:
        if time.monotonic() >= deadline:
            errors.append(name)
            continue
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
    metrics = [
        {"name": "opscontrol.service.up", "unit": "1", "gauge": {"dataPoints": records}}
    ]
    if native_os_metrics:
        try:
            if os_type == "Linux":
                uptime = time.clock_gettime(time.CLOCK_BOOTTIME)
            elif os_type == "Windows":
                import ctypes

                ctypes.windll.kernel32.GetTickCount64.restype = ctypes.c_ulonglong
                uptime = ctypes.windll.kernel32.GetTickCount64() / 1000
            else:
                raise RuntimeError()
            metrics.append(
                {
                    "name": "opscontrol.host.uptime",
                    "unit": "s",
                    "gauge": {
                        "dataPoints": [{"timeUnixNano": timestamp, "asDouble": uptime}]
                    },
                }
            )
        except (AttributeError, OSError, RuntimeError):
            errors.append("HOST_UPTIME")
    if processes:
        try:
            counts = {name: 0 for name in processes}
            if os_type == "Linux":
                from pathlib import Path

                for entry in Path("/proc").iterdir():
                    if not entry.name.isdigit():
                        continue
                    try:
                        name = (entry / "comm").read_text().strip()
                    except FileNotFoundError:
                        continue
                    if name in counts:
                        counts[name] += 1
            elif os_type == "Windows":
                import csv, io

                query = subprocess.run(
                    ["tasklist.exe", "/NH", "/FO", "CSV"],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                if query.returncode:
                    raise RuntimeError()
                rows = list(csv.reader(io.StringIO(query.stdout)))
                if not rows or any(
                    len(row) < 2 or not row[1].isdigit() for row in rows
                ):
                    raise RuntimeError()
                for row in rows:
                    for name in counts:
                        if row[0].lower() == name.lower():
                            counts[name] += 1
            else:
                raise RuntimeError()
            metrics.append(
                {
                    "name": "opscontrol.process.count",
                    "unit": "count",
                    "gauge": {
                        "dataPoints": [
                            {
                                "timeUnixNano": timestamp,
                                "asInt": str(count),
                                "attributes": [
                                    {
                                        "key": "process.name",
                                        "value": {"stringValue": name},
                                    }
                                ],
                            }
                            for name, count in counts.items()
                        ]
                    },
                }
            )
        except (OSError, subprocess.TimeoutExpired, RuntimeError):
            errors.append("PROCESS_QUERY")
    if methods:
        for metric in metrics:
            tagged = []
            for point in metric.get("gauge", {}).get("dataPoints", []):
                attrs = {
                    a["key"]: a["value"].get("stringValue")
                    for a in point.get("attributes", [])
                }
                matching = [
                    m
                    for m in methods
                    if m.get("enabled")
                    and (
                        m["method_type"] == "SERVICES"
                        and (
                            attrs.get("service.name")
                            in m["configuration"].get("services", [])
                            or attrs.get("process.name")
                            in m["configuration"].get("processes", [])
                        )
                        or m["method_type"] == "HOST_METRICS"
                        and metric["name"] == "opscontrol.host.uptime"
                    )
                ]
                for method in matching:
                    tagged.append(
                        {
                            **point,
                            "attributes": [
                                *point.get("attributes", []),
                                {
                                    "key": "opscontrol.method.id",
                                    "value": {"stringValue": str(method["id"])},
                                },
                            ],
                        }
                    )
                if not matching:
                    tagged.append(point)
            metric["gauge"]["dataPoints"] = tagged
    return {
        "resourceMetrics": [
            {
                "resource": {
                    "attributes": [
                        {"key": "host.name", "value": {"stringValue": hostname}}
                    ]
                },
                "scopeMetrics": [
                    {"scope": {"name": "opscontrol.native-health"}, "metrics": metrics}
                ],
            }
        ]
    }, errors


def method_observations(methods, running, private_home, failures=None):
    """Actual access checks describe idle capability; never infer receiving data."""
    import glob
    import itertools
    from pathlib import Path

    private = Path(private_home).resolve()
    results = []
    failures = set(failures or [])
    for method in methods[:100]:
        if not method.get("enabled"):
            continue
        state = "RUNNING" if running else "STOPPED"
        code = None
        total = readable = 0
        config = method["configuration"]
        if (
            running
            and method["method_type"] == "FILE_LOG"
            and config.get("source", "FILE") == "FILE"
        ):
            try:
                for pattern in config.get("paths", []):
                    matches = list(itertools.islice(glob.iglob(pattern), 501))
                    if not matches:
                        raise RuntimeError("LOG_PATH_NOT_FOUND")
                    if len(matches) > 500 or total + len(matches) > 1000:
                        raise RuntimeError("LOG_SOURCE_LIMIT_EXCEEDED")
                    total += len(matches)
                    for path in matches:
                        if Path(path).resolve().is_relative_to(private):
                            raise RuntimeError("AGENT_PRIVATE_PATH_DENIED")
                        with open(path, "rb") as stream:
                            stream.read(1)
                        readable += 1
                state = "IDLE" if total else "ERROR"
                code = None if total else "LOG_PATH_NOT_FOUND"
            except PermissionError:
                state, code = "ERROR", "LOG_PERMISSION_DENIED"
            except OSError:
                state, code = "ERROR", "LOG_SOURCE_UNAVAILABLE"
            except RuntimeError as error:
                state, code = "ERROR", str(error)
        elif running and method["method_type"] == "SERVICES":
            if failures & (
                set(config.get("services", []))
                | ({"PROCESS_QUERY"} if config.get("processes") else set())
            ):
                state, code = "ERROR", "SERVICE_QUERY_UNAVAILABLE"
        results.append(
            {
                "method_id": str(method["id"]),
                "state": state,
                "error_code": code,
                "sources_found": total,
                "sources_readable": readable,
            }
        )
    return results
