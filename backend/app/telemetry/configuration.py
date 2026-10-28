"""Strict source schemas and version-pinned OTel configuration generation."""

import hashlib, ipaddress, os, re, subprocess, tempfile
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit
import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.security.secret_refs import require_safe_config

RUNTIME_VERSION = "0.123.0"
FILELOG_HANDOFF_MARKER = (
    "# opscontrol-filelog-durable-handoff-v1: stanza.synchronousLogEmitter\n"
)


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FileLog(Strict):
    source: Literal["FILE", "JOURNALD", "WINDOWS_EVENT"] = "FILE"
    paths: list[str] = Field(default_factory=list, max_length=50)
    exclusions: list[str] = Field(default_factory=list, max_length=50)
    format: Literal["TEXT", "JSON"] = "TEXT"
    multiline_pattern: str | None = Field(default=None, max_length=500)
    channel: str = "Application"
    start_at: Literal["beginning", "end"] = "end"


class HostMetrics(Strict):
    interval_seconds: int = Field(default=30, ge=5, le=3600)
    scrapers: list[
        Literal[
            "cpu",
            "memory",
            "disk",
            "filesystem",
            "network",
            "load",
            "paging",
            "process",
            "processes",
        ]
    ] = Field(
        default_factory=lambda: ["cpu", "memory", "disk", "filesystem", "network"],
        min_length=1,
        max_length=9,
    )


class Services(Strict):
    services: list[str] = Field(default_factory=list, max_length=50)
    processes: list[str] = Field(default_factory=list, max_length=50)
    interval_seconds: int = Field(default=30, ge=5, le=3600)


class MetricScrape(Strict):
    targets: list[str] = Field(min_length=1, max_length=50)
    interval_seconds: int = Field(default=30, ge=5, le=3600)
    timeout_seconds: int = Field(default=10, ge=1, le=300)
    path: str = "/metrics"
    tls: bool = False
    ca_file: str | None = None
    server_name: str | None = None
    metric_include: list[str] = Field(default_factory=list, max_length=100)
    metric_exclude: list[str] = Field(default_factory=list, max_length=100)
    labels: dict[str, str] = Field(default_factory=dict, max_length=30)
    credential_ref: str | None = None

    @model_validator(mode="before")
    @classmethod
    def compatible_timeout(cls, value):
        # Older saved methods did not contain timeout; preserve short intervals.
        if isinstance(value, dict) and "timeout_seconds" not in value:
            try:
                interval = int(value.get("interval_seconds", 30))
            except (TypeError, ValueError):
                return value
            value = {**value, "timeout_seconds": min(10, interval)}
        return value


class OTLPReceiver(Strict):
    bind: str = "127.0.0.1"
    protocol: Literal["HTTP", "GRPC"] = "HTTP"
    port: int = Field(default=4318, ge=1024, le=65535)
    signals: list[Literal["Logs", "Metrics", "Traces"]] = Field(
        min_length=1, max_length=3
    )
    allow_remote: bool = False
    tls_certificate: str | None = None
    tls_key_ref: str | None = None
    credential_ref: str | None = None


class SyslogReceiver(Strict):
    bind: str = "127.0.0.1"
    port: int = Field(default=1514, ge=1024, le=65535)
    protocol: Literal["TCP", "UDP"] = "TCP"
    format: Literal["RFC5424", "RFC3164"] = "RFC5424"
    allow_remote: bool = False
    tls_certificate: str | None = None
    tls_key_ref: str | None = None
    client_ca: str | None = None


METHOD_SCHEMAS = {
    "HOST_METRICS": HostMetrics,
    "SERVICES": Services,
    "FILE_LOG": FileLog,
    "METRIC_SCRAPE": MetricScrape,
    "OTLP_RECEIVER": OTLPReceiver,
    "SYSLOG_RECEIVER": SyslogReceiver,
}


class MethodInput(Strict):
    name: str = Field(min_length=1, max_length=160)
    method_type: Literal[
        "HOST_METRICS",
        "SERVICES",
        "FILE_LOG",
        "METRIC_SCRAPE",
        "OTLP_RECEIVER",
        "SYSLOG_RECEIVER",
    ]
    configuration: dict
    enabled: bool = True
    expected_revision: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def safe(self):
        require_safe_config(self.configuration)
        schema = METHOD_SCHEMAS[self.method_type]
        self.configuration = schema.model_validate(self.configuration).model_dump()
        return self


def host_os(source):
    configuration = source.connection_config or {}
    value = configuration.get("opscontrol", {}).get("os_type") or configuration.get(
        "os_type"
    )
    if value:
        return value if value in ("Linux", "Windows") else "Unsupported"
    return {
        "LINUX": "Linux",
        "LINUX_HOST": "Linux",
        "WINDOWS": "Windows",
        "WINDOWS_HOST": "Windows",
    }.get(getattr(source, "source_type", ""), "Unsupported")


def env_reference(value):
    if not re.fullmatch(r"env:[A-Z][A-Z0-9_]{2,100}", value or ""):
        raise ValueError(
            "Use an env:NAME secret reference provisioned on the target agent"
        )
    if value.startswith("env:OPSCONTROL_AGENT_"):
        raise ValueError(
            "Management credential references cannot be used by collection methods"
        )
    return "${env:" + value[4:] + "}"


def safe_path(value, os_type):
    if (
        not isinstance(value, str)
        or len(value) > 1000
        or any(ord(c) < 32 for c in value)
        or ".." in value.replace("\\", "/").split("/")
    ):
        raise ValueError("Invalid host file path")
    if os_type == "Linux" and not value.startswith("/"):
        raise ValueError("Linux paths must be absolute")
    if os_type == "Windows" and not re.match(r"^[A-Za-z]:[\\/]", value):
        raise ValueError("Windows paths must include an absolute drive path")
    return value


def validate_method(method, os_type):
    if os_type not in ("Linux", "Windows"):
        raise ValueError("Data Source OS is unsupported for host agents")
    require_safe_config(method.configuration)
    c = (
        METHOD_SCHEMAS[method.method_type]
        .model_validate(method.configuration)
        .model_dump()
    )
    method.configuration = c
    if method.method_type == "HOST_METRICS":
        if len(set(c["scrapers"])) != len(c["scrapers"]):
            raise ValueError("Duplicate host metric scrapers")
        if os_type == "Windows" and "load" in c["scrapers"]:
            raise ValueError("Load averages are not supported on Windows")
    elif method.method_type == "SERVICES":
        if not c["services"] and not c["processes"]:
            raise ValueError("Configure at least one service or process")
        for value in c["services"] + c["processes"]:
            if not re.fullmatch(r"[A-Za-z0-9_.@ -]{1,160}", value):
                raise ValueError(
                    "Service/process names must be literal identities, not commands"
                )
        if len(set(c["services"])) != len(c["services"]) or len(
            set(c["processes"])
        ) != len(c["processes"]):
            raise ValueError("Duplicate service/process identities")
    elif method.method_type == "FILE_LOG":
        if c["source"] == "FILE":
            if not c["paths"]:
                raise ValueError("At least one log path is required")
            if len(set(c["paths"])) != len(c["paths"]):
                raise ValueError("Duplicate log paths")
            for path in c["paths"] + c["exclusions"]:
                safe_path(path, os_type)
            if c["multiline_pattern"]:
                re.compile(c["multiline_pattern"])
        if c["source"] == "JOURNALD" and os_type != "Linux":
            raise ValueError("Journald requires Linux")
        if c["source"] == "WINDOWS_EVENT" and os_type != "Windows":
            raise ValueError("Windows Event Log requires Windows")
        if not re.fullmatch(r"[\w /.-]{1,160}", c["channel"]):
            raise ValueError("Invalid event log channel")
    elif method.method_type == "METRIC_SCRAPE":
        if c["timeout_seconds"] > c["interval_seconds"]:
            raise ValueError("Scrape timeout cannot exceed interval")
        if not c["path"].startswith("/") or any(
            ch in c["path"] for ch in ("?", "#", "\n", "\r")
        ):
            raise ValueError("Invalid scrape path")
        for target in c["targets"]:
            if not re.fullmatch(
                r"(?:[a-zA-Z0-9.-]+|\[[0-9a-fA-F:]+\]):[0-9]{1,5}", target
            ):
                raise ValueError("Scrape targets require host:port")
            if not 1 <= int(target.rsplit(":", 1)[1]) <= 65535:
                raise ValueError("Invalid scrape port")
        if c["ca_file"]:
            safe_path(c["ca_file"], os_type)
        if c["server_name"] and not re.fullmatch(
            r"[A-Za-z0-9.-]{1,253}", c["server_name"]
        ):
            raise ValueError("Invalid TLS server name")
        for key, value in c["labels"].items():
            if (
                not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key)
                or key.startswith("__")
                or len(value) > 500
            ):
                raise ValueError("Invalid scrape label")
        for pattern in c["metric_include"] + c["metric_exclude"]:
            if len(pattern) > 300 or "(?" in pattern or re.search(r"\\[1-9]", pattern):
                raise ValueError("Use bounded RE2-compatible metric patterns")
            re.compile(pattern)
        if c["credential_ref"]:
            env_reference(c["credential_ref"])
        if c["credential_ref"] and not c["tls"]:
            raise ValueError("Authenticated scraping requires TLS")
    elif method.method_type == "SYSLOG_RECEIVER":
        try:
            local = ipaddress.ip_address(c["bind"]).is_loopback
        except ValueError:
            local = c["bind"] == "localhost"
        if not re.fullmatch(r"[A-Za-z0-9.:-]{1,255}", c["bind"]):
            raise ValueError("Invalid syslog binding")
        if not local and not (
            c["allow_remote"]
            and c["protocol"] == "TCP"
            and c["tls_certificate"]
            and c["tls_key_ref"]
            and c["client_ca"]
        ):
            raise ValueError(
                "Remote syslog requires TCP and mutual TLS; public UDP is forbidden"
            )
        if c["protocol"] == "UDP" and any(
            c.get(k) for k in ("tls_certificate", "tls_key_ref", "client_ca")
        ):
            raise ValueError("UDP cannot provide TLS authentication")
        if bool(c["tls_certificate"]) != bool(c["tls_key_ref"]):
            raise ValueError("Syslog TLS certificate/key must be configured together")
        for key in ("tls_certificate", "tls_key_ref", "client_ca"):
            if c[key]:
                safe_path(c[key], os_type)
    else:
        try:
            local = ipaddress.ip_address(c["bind"]).is_loopback
        except ValueError:
            local = c["bind"] == "localhost"
        if not local and not (
            c["allow_remote"]
            and c["tls_certificate"]
            and c["tls_key_ref"]
            and c["credential_ref"]
        ):
            raise ValueError(
                "Non-loopback OTLP binding requires explicit remote access, TLS and authentication"
            )
        if not re.fullmatch(r"[a-zA-Z0-9.:-]{1,255}", c["bind"]):
            raise ValueError("Invalid bind address")
        if bool(c["tls_certificate"]) != bool(c["tls_key_ref"]):
            raise ValueError("Both TLS certificate and key are required")
        if c["tls_certificate"]:
            safe_path(c["tls_certificate"], os_type)
            safe_path(c["tls_key_ref"], os_type)
        if c["credential_ref"]:
            env_reference(c["credential_ref"])
        if len(set(c["signals"])) != len(c["signals"]):
            raise ValueError("Duplicate signal selection")
    return method


def generate(collector, source, methods, ingestion_url):
    parsed = urlsplit(ingestion_url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Ingestion exporter requires a credential-free HTTPS origin")
    os_type = host_os(source)
    receivers = {}
    pipeline_receivers = {"logs": [], "metrics": [], "traces": []}
    extensions = {
        "health_check": {"endpoint": "127.0.0.1:13133"},
        "file_storage/opscontrol": {
            "directory": "${env:OPSCONTROL_AGENT_STATE_DIR}/otel-checkpoints",
            "create_directory": True,
        },
    }
    ports = set()
    method_metric_pipelines = {}
    method_processors = {}
    durable_file_logs = False
    methods = list(methods)
    for method in methods:
        if not method.enabled or getattr(method, "deleted_at", None):
            continue
        validate_method(method, os_type)
        c = method.configuration
        suffix = str(method.id).replace("-", "")
        if method.method_type == "HOST_METRICS":
            receiver = "hostmetrics/" + suffix
            scrapers = {name: {} for name in c["scrapers"]}
            if "cpu" in scrapers:
                scrapers["cpu"] = {
                    "metrics": {"system.cpu.utilization": {"enabled": True}}
                }
            cfg = {
                "collection_interval": str(c["interval_seconds"]) + "s",
                "scrapers": scrapers,
            }
            signals = ["metrics"]
        elif method.method_type == "SERVICES":
            # The Supervisor emits authenticated service/process OTLP metrics.
            # This bounded loopback receiver also keeps Services-only runtimes valid.
            receiver = "otlp/services_" + suffix
            cfg = {"protocols": {"http": {"endpoint": "127.0.0.1:0"}}}
            signals = ["metrics"]
        elif method.method_type == "FILE_LOG":
            if c["source"] == "FILE":
                durable_file_logs = True
                receiver = "filelog/" + suffix
                cfg = {
                    "include": c["paths"],
                    "include_file_path": True,
                    "include_file_name": True,
                    "exclude": c["exclusions"]
                    + ["${env:OPSCONTROL_AGENT_STATE_DIR}/**"],
                    "start_at": c["start_at"],
                    "storage": "file_storage/opscontrol",
                    # Pause reading on failed handoff (including a full queue).
                    "retry_on_failure": {"enabled": True, "max_elapsed_time": "0s"},
                }
                if c["format"] == "JSON":
                    cfg["operators"] = [{"type": "json_parser"}]
                if c["multiline_pattern"]:
                    cfg["multiline"] = {"line_start_pattern": c["multiline_pattern"]}
                extensions["file_storage/opscontrol"] = {
                    "directory": "${env:OPSCONTROL_AGENT_STATE_DIR}/otel-checkpoints",
                    "create_directory": True,
                }
                # Stable path identities preserve offsets if paths are reordered/added.
                for path in c["paths"]:
                    path_id = hashlib.sha256(path.encode()).hexdigest()[:16]
                    path_receiver = receiver + "_" + path_id
                    receivers[path_receiver] = {
                        **cfg,
                        "include": [path],
                        "operators": [
                            *cfg.get("operators", []),
                            {
                                "type": "add",
                                "field": 'attributes["opscontrol.method.id"]',
                                "value": str(method.id),
                            },
                            {
                                "type": "add",
                                "field": 'attributes["opscontrol.log.source.id"]',
                                "value": str(method.id) + ":" + path_id,
                            },
                        ],
                    }
                    pipeline_receivers["logs"].append(path_receiver)
                continue
            elif c["source"] == "JOURNALD":
                receiver = "journald/" + suffix
                cfg = {}
            else:
                receiver = "windowseventlog/" + suffix
                cfg = {"channel": c["channel"]}
            signals = ["logs"]
        elif method.method_type == "METRIC_SCRAPE":
            receiver = "prometheus/" + suffix
            scrape = {
                "job_name": "opscontrol_" + suffix,
                "scrape_timeout": str(c["timeout_seconds"]) + "s",
                "scrape_interval": str(c["interval_seconds"]) + "s",
                "metrics_path": c["path"],
                "scheme": "https" if c["tls"] else "http",
                "static_configs": [
                    {
                        "targets": c["targets"],
                        "labels": {
                            **c["labels"],
                            "opscontrol_method_id": str(method.id),
                        },
                    }
                ],
            }
            if c["tls"]:
                scrape["tls_config"] = {"insecure_skip_verify": False}
                if c["ca_file"]:
                    scrape["tls_config"]["ca_file"] = c["ca_file"]
                if c["server_name"]:
                    scrape["tls_config"]["server_name"] = c["server_name"]
            filters = []
            if c["metric_include"]:
                filters.append(
                    {
                        "source_labels": ["__name__"],
                        "regex": "(?:up|scrape_duration_seconds|scrape_samples_scraped)|"
                        + "|".join("(?:" + p + ")" for p in c["metric_include"]),
                        "action": "keep",
                    }
                )
            if c["metric_exclude"]:
                filters.append(
                    {
                        "source_labels": ["__name__"],
                        "regex": "|".join("(?:" + p + ")" for p in c["metric_exclude"]),
                        "action": "drop",
                    }
                )
            if filters:
                scrape["metric_relabel_configs"] = filters
            if c["credential_ref"]:
                scrape["authorization"] = {
                    "type": "Bearer",
                    "credentials": env_reference(c["credential_ref"]),
                }
            cfg = {"config": {"scrape_configs": [scrape]}}
            signals = ["metrics"]
        elif method.method_type == "SYSLOG_RECEIVER":
            pair = (c["bind"], c["port"])
            if pair in ports:
                raise ValueError("Enabled methods cannot share a listener")
            ports.add(pair)
            receiver = "syslog/" + suffix
            endpoint = (
                ("[" + c["bind"] + "]" if ":" in c["bind"] else c["bind"])
                + ":"
                + str(c["port"])
            )
            listen = {"listen_address": endpoint}
            if c["tls_certificate"]:
                listen["tls"] = {
                    "cert_file": c["tls_certificate"],
                    "key_file": c["tls_key_ref"],
                }
                if c["client_ca"]:
                    listen["tls"]["client_ca_file"] = c["client_ca"]
            cfg = {
                c["protocol"].lower(): listen,
                "protocol": c["format"].lower(),
                "operators": [
                    {
                        "type": "add",
                        "field": 'attributes["opscontrol.method.id"]',
                        "value": str(method.id),
                    }
                ],
            }
            signals = ["logs"]
        else:
            pair = (c["bind"], c["port"])
            if pair in ports:
                raise ValueError("Enabled OTLP methods cannot share a listener")
            ports.add(pair)
            receiver = "otlp/" + suffix
            protocol = {
                "endpoint": ("[" + c["bind"] + "]" if ":" in c["bind"] else c["bind"])
                + ":"
                + str(c["port"])
            }
            if c["tls_certificate"]:
                protocol["tls"] = {
                    "cert_file": c["tls_certificate"],
                    "key_file": c["tls_key_ref"],
                }
            if c["credential_ref"]:
                ext = "bearertokenauth/" + suffix
                extensions[ext] = {"token": env_reference(c["credential_ref"])}
                protocol["auth"] = {"authenticator": ext}
            cfg = {"protocols": {c["protocol"].lower(): protocol}}
            signals = [s.lower() for s in c["signals"]]
        receivers[receiver] = cfg
        if method.method_type == "HOST_METRICS":
            processor = "resource/method_" + suffix
            method_processors[processor] = {
                "attributes": [
                    {
                        "key": "opscontrol.method.id",
                        "value": str(method.id),
                        "action": "upsert",
                    }
                ]
            }
            method_metric_pipelines["metrics/" + suffix] = {
                "receivers": [receiver],
                "processors": ["memory_limiter", processor, "batch"],
                "exporters": ["otlphttp/opscontrol"],
            }
            continue
        for signal in signals:
            pipeline_receivers[signal].append(receiver)
    if (collector.configuration or {}).get("os_metrics") and not any(
        m.enabled
        and m.method_type == "HOST_METRICS"
        and not getattr(m, "deleted_at", None)
        for m in methods
    ):
        if os_type == "Unsupported":
            raise ValueError("Native host metrics require a supported host OS")
        receivers["hostmetrics/native"] = {
            "collection_interval": "30s",
            "scrapers": {
                "cpu": {"metrics": {"system.cpu.utilization": {"enabled": True}}},
                "memory": {},
                "disk": {},
                "filesystem": {},
                "network": {},
                "process": {},
            },
        }
        pipeline_receivers["metrics"].append("hostmetrics/native")
    if durable_file_logs:
        extensions["file_storage/opscontrol"]["fsync"] = True
    pipelines = {
        s: {
            "receivers": r,
            # An asynchronous batch acknowledges filelog before durable enqueue,
            # allowing its checkpoint to advance past records lost on SIGKILL.
            "processors": (
                ["memory_limiter"]
                if s == "logs" and durable_file_logs
                else ["memory_limiter", "batch"]
            ),
            "exporters": ["otlphttp/opscontrol"],
        }
        for s, r in pipeline_receivers.items()
        if r
    }
    pipelines.update(method_metric_pipelines)
    if not pipelines:
        raise ValueError("Enable at least one collection method or native OS Metrics")
    config = {
        "receivers": receivers,
        "processors": {
            **method_processors,
            "memory_limiter": {
                "check_interval": "1s",
                "limit_mib": 256,
                "spike_limit_mib": 64,
            },
            "batch": {"timeout": "5s", "send_batch_size": 512},
        },
        "exporters": {
            "otlphttp/opscontrol": {
                "endpoint": ingestion_url.rstrip("/") + "/api/v1/agent/otlp",
                "headers": {"Authorization": "Bearer ${env:OPSCONTROL_AGENT_TOKEN}"},
                "tls": {"insecure": False},
                "retry_on_failure": {
                    "enabled": True,
                    **({"max_elapsed_time": "0s"} if durable_file_logs else {}),
                },
                "sending_queue": {
                    "enabled": True,
                    "queue_size": 256,
                    "storage": "file_storage/opscontrol",
                },
            }
        },
        "extensions": extensions,
        "service": {"extensions": list(extensions), "pipelines": pipelines},
    }
    metadata = (source.connection_config or {}).get("opscontrol", {})
    tags = (
        [
            {
                "key": "opscontrol.collector.id",
                "value": str(collector.id),
                "action": "upsert",
            },
            {
                "key": "opscontrol.organization.id",
                "value": str(source.organization_id),
                "action": "upsert",
            },
        ]
        if hasattr(collector, "id") and hasattr(source, "organization_id")
        else []
    )
    for key, value in (
        ("deployment.environment", metadata.get("environment")),
        ("service.namespace", metadata.get("application")),
    ):
        if value:
            tags.append({"key": key, "value": str(value), "action": "upsert"})
    if tags:
        config["processors"]["resource/opscontrol"] = {"attributes": tags}
        for pipeline in pipelines.values():
            pipeline["processors"].insert(1, "resource/opscontrol")
    # The marker is covered by the version checksum. The matching Agent enables
    # only this fixed upstream gate; it never accepts arbitrary runtime flags.
    return (FILELOG_HANDOFF_MARKER if durable_file_logs else "") + yaml.safe_dump(
        config, sort_keys=False
    )


def validate_binary(text, binary=None):
    binary = binary or os.getenv("OPSCONTROL_OTEL_BINARY")
    if not binary:
        raise ValueError(
            "Collector validation binary is unavailable; configure OPSCONTROL_OTEL_BINARY for version "
            + RUNTIME_VERSION
        )
    try:
        version = subprocess.run(
            [binary, "--version"], capture_output=True, text=True, timeout=10
        )
        if version.returncode or not re.search(
            r"(?<![\d.])" + re.escape(RUNTIME_VERSION) + r"(?![\d.])", version.stdout
        ):
            raise ValueError(
                "Selected Collector binary version does not match " + RUNTIME_VERSION
            )
        with tempfile.TemporaryDirectory(prefix="opscontrol-otel-validation-") as temp:
            path = Path(temp) / "config.yaml"
            path.write_text(text)
            path.chmod(0o600)
            env = {**os.environ}
            for name in re.findall(r"\$\{env:([A-Z][A-Z0-9_]*)\}", text):
                env[name] = (
                    temp
                    if name == "OPSCONTROL_AGENT_STATE_DIR"
                    else "validation-only-not-a-credential"
                )
            result = subprocess.run(
                [binary, "validate", "--config", str(path)]
                + (
                    ["--feature-gates=stanza.synchronousLogEmitter"]
                    if text.startswith(FILELOG_HANDOFF_MARKER)
                    else []
                ),
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )
    except (OSError, subprocess.TimeoutExpired):
        raise ValueError(
            "Collector validation binary unavailable or timed out"
        ) from None
    if result.returncode:
        raise ValueError(
            "Collector rejected configuration; inspect private server validation diagnostics"
        )
    return True
