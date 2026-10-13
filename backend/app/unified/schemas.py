"""Closed domain schemas: identity stays in resources, rules stay in versions."""

import ipaddress, json, re
from typing import Literal
from uuid import UUID
from datetime import time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import regex
import yaml
from croniter import croniter
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.security.secret_refs import require_safe_config
from app.telemetry.configuration import env_reference

Environment = Literal["PROD", "QA", "TEST", "DEV", "SANDBOX"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NewCustomer(Strict):
    name: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=1, max_length=50, pattern=r"^[A-Za-z0-9_-]+$")


class ResourceIdentity(Strict):
    name: str = Field(min_length=1, max_length=200)
    organization_id: UUID | None = None
    new_customer: NewCustomer | None = None
    environment: Environment | None = None
    description: str | None = Field(default=None, max_length=2000)
    tags: dict[str, str] = Field(default_factory=dict, max_length=30)
    active: bool = True

    @model_validator(mode="after")
    def secrets(self):
        require_safe_config(self.tags)
        return self


def host(value):
    if not value or len(value) > 253 or any(x in value for x in "/@?#% \r\n"):
        raise ValueError("DNS/IP must be a host identity, not a URL")
    try:
        ipaddress.ip_address(value)
    except ValueError:
        if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?", value):
            raise ValueError("Invalid DNS name")
    return value.lower()


class VMCreate(ResourceIdentity):
    hostname: str = Field(min_length=1, max_length=200)
    address: str = Field(min_length=1, max_length=253)
    os_type: Literal["Windows", "Linux"]
    vm_type: Literal["VM", "EC2"] = "VM"
    native_os_metrics: bool = True
    services: list[str] = Field(default_factory=list, max_length=50)
    processes: list[str] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def valid(self):
        self.address = host(self.address)
        if not self.environment:
            raise ValueError("Environment required")
        if bool(self.organization_id) == bool(self.new_customer):
            raise ValueError("Select or create exactly one customer")
        if len(set(self.processes)) != len(self.processes) or any(
            not re.fullmatch(r"[A-Za-z0-9_.@ -]{1,200}", v) for v in self.processes
        ):
            raise ValueError("Invalid or duplicate process names")
        if len(set(self.services)) != len(self.services) or any(
            not re.fullmatch(r"[A-Za-z0-9_.@ -]{1,200}", v) for v in self.services
        ):
            raise ValueError("Invalid or duplicate service names")
        return self


class LogParser(Strict):
    format: Literal["JSON", "REGEX"] = "JSON"
    pattern: str | None = Field(default=None, max_length=2000)
    timestamp_format: str | None = Field(default=None, max_length=100)
    field_mapping: dict[str, str] = Field(
        default_factory=lambda: {
            "execution_id": "execution_id",
            "event_type": "event",
            "status": "status",
            "step_id": "step_id",
            "step_name": "step",
            "attempt": "attempt",
            "timestamp": "timestamp",
        }
    )
    status_mapping: dict[str, Literal["RUNNING", "SUCCESS", "FAILED", "UNKNOWN"]] = (
        Field(
            default_factory=lambda: {
                "RUNNING": "RUNNING",
                "SUCCESS": "SUCCESS",
                "FAILED": "FAILED",
            }
        )
    )
    event_mapping: dict[
        str, Literal["START", "END", "STEP_START", "STEP_END", "STEP_FAILED", "STATUS"]
    ] = Field(default_factory=dict)
    timezone: str = "UTC"
    execution_type_mapping: dict[str, Literal["SCHEDULED", "MANUAL"]] = Field(
        default_factory=lambda: {"SCHEDULED": "SCHEDULED", "MANUAL": "MANUAL"}
    )
    default_execution_type: Literal["SCHEDULED", "MANUAL"] = "SCHEDULED"
    execution_identity_fields: list[str] = Field(
        default_factory=lambda: ["execution_id", "order_id"], min_length=1, max_length=8
    )

    @model_validator(mode="after")
    def valid(self):
        allowed = {
            "execution_id",
            "order_id",
            "jobchain",
            "event_type",
            "status",
            "step_id",
            "step_name",
            "attempt",
            "timestamp",
            "duration_seconds",
            "error",
            "execution_type",
            "scheduled_at",
            "started_at",
            "ended_at",
        }
        if set(self.field_mapping) - allowed:
            raise ValueError("Unsupported normalized field mapping")
        if any(
            not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]{0,150}", v)
            for v in self.field_mapping.values()
        ):
            raise ValueError("Invalid mapped field")
        if set(self.execution_identity_fields) - {
            "execution_id",
            "order_id",
            "scheduled_at",
            "started_at",
            "ended_at",
        }:
            raise ValueError("Invalid execution identification fields")
        try:
            ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError:
            raise ValueError("Unknown IANA timezone") from None
        if self.format == "REGEX":
            if not self.pattern:
                raise ValueError("Regex parser requires a pattern")
            try:
                regex.compile(self.pattern)
            except regex.error:
                raise ValueError("Invalid parser expression") from None
        require_safe_config(self.model_dump())
        return self


class Schedule(Strict):
    frequency: Literal[
        "HOURLY", "DAILY", "WEEKLY", "MONTHLY", "QUARTERLY", "CUSTOM"
    ] = "DAILY"
    time: str = "00:00"
    timezone: str = "UTC"
    weekdays: list[int] = Field(
        default_factory=lambda: list(range(7)), min_length=1, max_length=7
    )
    month_day: int = Field(default=1, ge=1, le=31)
    cron: str | None = Field(default=None, max_length=100)
    exceptions: list[str] = Field(default_factory=list, max_length=400)
    dst_policy: Literal["FIRST", "SECOND"] = "FIRST"
    catchup_hours: int = Field(default=24, ge=1, le=8784)

    @model_validator(mode="after")
    def valid(self):
        from datetime import date

        if not re.fullmatch(r"\d{2}:\d{2}", self.time):
            raise ValueError("Use minute precision HH:MM")
        time.fromisoformat(self.time)
        try:
            ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError:
            raise ValueError("Unknown IANA timezone") from None
        if set(self.weekdays) - set(range(7)) or len(set(self.weekdays)) != len(
            self.weekdays
        ):
            raise ValueError("Invalid weekdays")
        for exception in self.exceptions:
            date.fromisoformat(exception)
        if self.frequency == "CUSTOM" and (
            not self.cron
            or len(self.cron.split()) != 5
            or not croniter.is_valid(self.cron)
        ):
            raise ValueError(
                "Custom schedule requires a valid five-field cron expression"
            )
        return self


class ETLCreate(ResourceIdentity):
    platform: Literal["PENTAHO", "IICS"]
    vm_resource_id: UUID | None = None
    jobchain: str = Field(min_length=1, max_length=200)
    scheduler: str | None = Field(default=None, max_length=200)
    log_paths: list[str] = Field(default_factory=list, max_length=50)
    parser: LogParser = Field(default_factory=LogParser)
    frequency_seconds: int = Field(default=30, ge=5, le=86400)
    connector_url: str | None = Field(default=None, max_length=1000)
    credential_ref: str | None = None
    credential_header: Literal["Authorization", "icSessionId", "INFA-SESSION-ID"] = (
        "INFA-SESSION-ID"
    )
    connector_records_field: str = Field(
        default="records", pattern=r"^[A-Za-z_][A-Za-z0-9_.]{0,100}$"
    )
    schedule: Schedule | None = None

    @model_validator(mode="after")
    def valid(self):
        if not self.vm_resource_id and (
            not self.environment
            or bool(self.organization_id) == bool(self.new_customer)
        ):
            raise ValueError("SaaS ETL requires an explicit customer/environment")
        if self.vm_resource_id and self.new_customer:
            raise ValueError("VM relationship already determines the customer")
        if self.platform == "IICS" and self.log_paths:
            raise ValueError(
                "IICS cloud execution metadata is independent of local file paths"
            )
        if self.credential_ref:
            env_reference(self.credential_ref)
        if self.connector_url:
            from urllib.parse import urlsplit

            p = urlsplit(self.connector_url)
            if (
                p.scheme != "https"
                or not p.hostname
                or p.username
                or p.password
                or p.fragment
            ):
                raise ValueError(
                    "Connector URL requires HTTPS without embedded credentials"
                )
        return self


class APICreate(ResourceIdentity):
    dns: str
    port: int = Field(default=443, ge=1, le=65535)
    protocol: Literal["HTTP", "HTTPS"] = "HTTPS"
    path: str = Field(default="/", max_length=1000)
    frequency_seconds: int = Field(default=30, ge=5, le=86400)
    method: Literal["GET", "HEAD", "OPTIONS"] = "GET"
    auth_type: Literal["NONE", "BASIC", "BEARER"] = "NONE"
    credential_ref: str | None = None
    timeout_seconds: int = Field(default=10, ge=1, le=120)
    headers: dict[str, str] = Field(default_factory=dict, max_length=20)
    tls_validation: bool = True
    linked_vm_resource_id: UUID | None = None
    probe_location: str = Field(default="NATIVE", min_length=1, max_length=100)

    @model_validator(mode="after")
    def valid(self):
        self.dns = host(self.dns)
        if not self.environment or bool(self.organization_id) == bool(
            self.new_customer
        ):
            raise ValueError("Select/create customer and environment")
        if (
            not self.path.startswith("/")
            or "#" in self.path
            or any(ord(c) < 32 for c in self.path)
        ):
            raise ValueError("Invalid endpoint path")
        if not self.tls_validation:
            raise ValueError(
                "TLS verification cannot be disabled; configure trusted certificates"
            )
        if self.credential_ref:
            env_reference(self.credential_ref)
        if self.auth_type != "NONE":
            if self.protocol != "HTTPS" or not self.credential_ref:
                raise ValueError("Authentication requires HTTPS and a secret reference")
            env_reference(self.credential_ref)
        if any(
            k.lower() in {"authorization", "proxy-authorization", "cookie", "host"}
            or any(ord(c) < 32 for c in k + v)
            for k, v in self.headers.items()
        ):
            raise ValueError("Sensitive/invalid headers require managed authentication")
        require_safe_config(self.headers)
        return self


class Threshold(Strict):
    metric_definition_id: UUID | None = None
    metric_name: str = Field(min_length=1, max_length=200)
    operator: Literal["GT", "GTE", "LT", "LTE"] = "GT"
    warning: float | None = None
    critical: float
    recovery: float | None = None
    unit: Literal["%", "bytes", "ms", "s", "count", "1", "By", "By/s", "bits/s"]
    duration_seconds: int = Field(default=0, ge=0, le=86400)
    consecutive_breaches: int = Field(default=2, ge=1, le=10000)
    maximum_gap_seconds: int = Field(default=90, ge=5, le=86400)
    threshold_mode: Literal["STATIC", "DYNAMIC", "COMBINED"] = "STATIC"
    baseline_minutes: int = Field(default=60, ge=1, le=10080)
    baseline_minimum_samples: int = Field(default=20, ge=3, le=10000)
    standard_deviations: float = Field(default=3, gt=0, le=10)

    @model_validator(mode="after")
    def valid(self):
        import math

        values = [
            v for v in (self.warning, self.critical, self.recovery) if v is not None
        ]
        if any(not math.isfinite(v) for v in values):
            raise ValueError("Finite thresholds required")
        if self.unit == "%" and any(not 0 <= v <= 100 for v in values):
            raise ValueError("Percentage thresholds must be 0–100")
        high = self.operator in {"GT", "GTE"}
        if self.warning is not None and (
            (high and self.warning > self.critical)
            or (not high and self.warning < self.critical)
        ):
            raise ValueError("Warning and critical thresholds contradict")
        if self.recovery is not None and (
            (high and self.recovery > self.critical)
            or (not high and self.recovery < self.critical)
        ):
            raise ValueError("Recovery threshold contradicts the breach direction")
        return self


class ETLParameters(Strict):
    domain: Literal["ETL"] = "ETL"
    parser: LogParser = Field(default_factory=LogParser)
    schedule: Schedule | None = None
    no_run_grace_seconds: int = Field(default=900, ge=0, le=86400)
    delayed_start_seconds: int = Field(default=120, ge=0, le=86400)
    long_running_seconds: int = Field(default=3600, ge=1, le=604800)
    no_response_seconds: int = Field(default=300, ge=30, le=86400)
    completion_sla_seconds: int = Field(default=7200, ge=1, le=604800)
    require_dependencies: bool = True
    overrides: dict = Field(default_factory=dict)


class VMParameters(Strict):
    domain: Literal["VM"] = "VM"
    thresholds: list[Threshold] = Field(default_factory=list, max_length=100)
    missing_telemetry_seconds: int = Field(default=120, ge=30, le=86400)
    services: list[str] = Field(default_factory=list, max_length=50)
    processes: list[str] = Field(default_factory=list, max_length=50)
    service_failures: int = Field(default=2, ge=1, le=100)
    overrides: dict = Field(default_factory=dict)


class APIParameters(Strict):
    domain: Literal["API"] = "API"
    expected_statuses: list[int] = Field(
        default_factory=lambda: [200], min_length=1, max_length=50
    )
    warning_latency_ms: int = Field(default=1000, ge=1, le=120000)
    critical_latency_ms: int = Field(default=3000, ge=1, le=120000)
    consecutive_failures: int = Field(default=2, ge=1, le=100)
    recovery_successes: int = Field(default=2, ge=1, le=100)
    missing_results_seconds: int = Field(default=120, ge=10, le=86400)
    availability_percent: float = Field(default=99.9, ge=0, le=100)
    sla_window_minutes: int = Field(default=1440, ge=1, le=43200)
    overrides: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def valid(self):
        if any(not 100 <= s <= 599 for s in self.expected_statuses) or len(
            set(self.expected_statuses)
        ) != len(self.expected_statuses):
            raise ValueError("Invalid expected HTTP statuses")
        if self.warning_latency_ms > self.critical_latency_ms:
            raise ValueError("Latency thresholds contradict")
        return self


PARAMETERS = {"VM": VMParameters, "ETL": ETLParameters, "API": APIParameters}


def validate_parameters(domain, config):
    require_safe_config(config)
    result = PARAMETERS[domain].model_validate(config).model_dump(mode="json")
    allowed = {
        "VM": {
            "thresholds",
            "missing_telemetry_seconds",
            "services",
            "service_failures",
        },
        "ETL": {
            "no_run_grace_seconds",
            "delayed_start_seconds",
            "long_running_seconds",
            "no_response_seconds",
            "completion_sla_seconds",
        },
        "API": {
            "warning_latency_ms",
            "critical_latency_ms",
            "consecutive_failures",
            "recovery_successes",
            "availability_percent",
            "missing_results_seconds",
        },
    }[domain]
    if set(result["overrides"]) - allowed:
        raise ValueError("Identity/unsupported overrides are forbidden")
    for key, value in result["overrides"].items():
        result[key] = value
    result = PARAMETERS[domain].model_validate(result).model_dump(mode="json")
    if domain == "VM" and any(
        not re.fullmatch(r"[A-Za-z0-9_.@ -]{1,200}", v)
        for v in result["services"] + result["processes"]
    ):
        raise ValueError("Invalid service identity")
    return result


def import_document(content, format):
    if len(content.encode()) > 262144:
        raise ValueError("Import exceeds 256 KiB")
    try:
        obj = json.loads(content) if format == "JSON" else yaml.safe_load(content)
    except (json.JSONDecodeError, yaml.YAMLError, RecursionError):
        raise ValueError("Invalid or unsafe configuration document") from None

    def check(value, depth=0, seen=None):
        if depth > 12:
            raise ValueError("Configuration nesting exceeds limit")
        if isinstance(value, (dict, list)):
            seen = set() if seen is None else seen
            if id(value) in seen:
                raise ValueError("Cyclic YAML aliases are forbidden")
            seen = seen | {id(value)}
            if len(value) > 1000:
                raise ValueError("Configuration collection exceeds limit")
            for item in value.values() if isinstance(value, dict) else value:
                check(item, depth + 1, seen)

    check(obj)
    if not isinstance(obj, dict):
        raise ValueError("Configuration must be an object")
    return obj
