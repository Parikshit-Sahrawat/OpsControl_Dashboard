"""Read-only integration contract. No adapter infers connection success from configuration."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import base64
import json
import os
import time
import ssl
from urllib.parse import urlsplit, urlencode
from app.unified.transport import PinnedHTTPS
from app.worker.egress import resolve_target, policy_cidrs, EgressDenied
from app.telemetry.configuration import env_reference
from app.telemetry.delivery import secret


def redact_provider_record(value, depth=0):
    """Redact structured secrets before source records enter telemetry evidence."""
    from app.worker.pentaho_status import safe_text

    if depth > 16:
        return "[OMITTED:DEPTH_LIMIT]"
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            normalized = str(key).lower().replace("-", "_")
            sensitive = (
                normalized
                in {
                    "authorization",
                    "cookie",
                    "set_cookie",
                    "pwd",
                    "passwd",
                    "credentials",
                    "connection_string",
                }
                or any(
                    marker in normalized
                    for marker in (
                        "password",
                        "secret",
                        "access_token",
                        "refresh_token",
                        "api_key",
                        "apikey",
                    )
                )
                or normalized in {"token", "bearer", "client_key", "private_key"}
            )
            result[str(key)] = (
                "[REDACTED]" if sensitive else redact_provider_record(item, depth + 1)
            )
        return result
    if isinstance(value, (list, tuple)):
        return [redact_provider_record(item, depth + 1) for item in value[:1000]]
    if isinstance(value, str):
        # Providers sometimes nest serialized execution parameters in a string.
        if len(value) < 16000 and value.lstrip().startswith(("{", "[")):
            try:
                return json.dumps(
                    redact_provider_record(json.loads(value), depth + 1), sort_keys=True
                )
            except (ValueError, TypeError):
                pass
        return safe_text(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


class AdapterError(ValueError):
    def __init__(self, kind, message):
        self.kind = kind
        super().__init__(message)


@dataclass
class Batch:
    events: list = field(default_factory=list)
    evidence: dict = field(default_factory=dict)
    checkpoint: dict = field(default_factory=dict)
    complete: bool = True


def instant(value):
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, (float, int)):
        parsed = datetime.fromtimestamp(
            value / 1000 if value > 1e11 else value, timezone.utc
        )
    elif value:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    else:
        return None
    if parsed.tzinfo is None:
        raise AdapterError("SCHEMA", "Provider timestamp must include timezone")
    return parsed.astimezone(timezone.utc).isoformat()


def execution(
    platform,
    jobchain,
    identity,
    status,
    started=None,
    ended=None,
    observed=None,
    evidence=None,
    mode="SCHEDULED",
):
    if not identity or not jobchain:
        raise AdapterError(
            "SCHEMA", "Provider execution identity and jobchain are required"
        )
    start, end = instant(started), instant(ended)
    if start and end and end < start:
        raise AdapterError("SCHEMA", "Execution end precedes start")
    timestamp = end or start or instant(observed)
    observation_only = timestamp is None
    if observation_only:
        # A real read observed the state, but did not supply execution timing.
        # Do not substitute this observation for start/end in reconstruction.
        timestamp = datetime.now(timezone.utc).isoformat()
    event = dict(
        execution_id=str(identity),
        jobchain=str(jobchain),
        status=status,
        source_status=status,
        event_type=(
            "END" if end else "START" if start and status == "RUNNING" else "STATUS"
        ),
        timestamp=timestamp,
        started_at=start,
        ended_at=end,
        execution_type=mode,
        terminal_status_observed=status in {"SUCCESS", "FAILED"} and end is None,
        timestamp_provenance="RECEIVED_OBSERVATION" if observation_only else "SOURCE",
        provider_status_observed=True,
    )
    # Identity includes provider, execution, state and evidence revision; distinct raw records remain evidence.
    key = hashlib.sha256(
        json.dumps(
            [
                platform,
                {
                    k: v
                    for k, v in event.items()
                    if not (observation_only and k == "timestamp")
                },
                evidence,
            ],
            sort_keys=True,
            default=str,
        ).encode()
    ).hexdigest()
    return dict(
        key=f"{platform}:{key}",
        event=event,
        observed_at=timestamp,
        evidence={
            **redact_provider_record(evidence or {}),
            "timestamp_provenance": event["timestamp_provenance"],
        },
    )


def http_request(url, cfg, method="GET", body=None):
    """Pinned TLS, deployment-owned allowlists, bounded response, no redirects or URL credentials."""
    parsed = urlsplit(url)
    host, port = parsed.hostname, parsed.port or 443
    allowed = {
        x.strip().lower()
        for x in os.getenv("OPSCONTROL_NATIVE_ALLOWED_HOSTS", "").split(",")
        if x.strip()
    }
    ports = {
        int(x)
        for x in os.getenv("OPSCONTROL_NATIVE_ALLOWED_PORTS", "443").split(",")
        if x.isdigit()
    }
    if (
        parsed.scheme != "https"
        or not host
        or host.lower() not in allowed
        or port not in ports
        or parsed.username
        or parsed.password
        or parsed.fragment
    ):
        raise AdapterError(
            "CONFIGURATION",
            "Platform endpoint requires deployment-approved TLS host and port",
        )
    if any(ord(x) < 33 or ord(x) > 126 for x in url):
        raise AdapterError("CONFIGURATION", "Invalid URL encoding")
    try:
        ip = resolve_target(
            host,
            policy_cidrs(
                [
                    x.strip()
                    for x in os.getenv("OPSCONTROL_NATIVE_ALLOWED_CIDRS", "").split(",")
                    if x.strip()
                ]
            ),
        )
    except EgressDenied:
        raise AdapterError(
            "CONFIGURATION", "Platform destination is not approved"
        ) from None
    except OSError:
        raise AdapterError("NETWORK", "Platform name resolution unavailable") from None
    headers = {
        "Accept": "application/json",
        "User-Agent": "OpsControl-Platform-Adapter/1.0",
    }
    ref = cfg.get("credential_ref")
    if ref and cfg.get("auth_type", "BEARER") != "NONE":
        env_reference(ref)
        try:
            token = secret(ref)
        except (ValueError, RuntimeError):
            raise AdapterError(
                "AUTHENTICATION", "Managed provider credential is unavailable"
            ) from None
        header = cfg.get("credential_header", "Authorization")
        if header not in {"Authorization", "INFA-SESSION-ID", "icSessionId"}:
            raise AdapterError("CONFIGURATION", "Unsupported authentication header")
        if cfg.get("auth_type") == "BASIC":
            if header != "Authorization":
                raise AdapterError(
                    "CONFIGURATION", "Basic auth requires Authorization header"
                )
            try:
                credentials = json.loads(token)
                token = base64.b64encode(
                    (credentials["username"] + ":" + credentials["password"]).encode()
                ).decode()
            except (TypeError, KeyError, ValueError) as exc:
                raise AdapterError(
                    "CONFIGURATION",
                    "Basic authentication secret must contain username/password",
                ) from exc
            headers[header] = "Basic " + token
        else:
            headers[header] = "Bearer " + token if header == "Authorization" else token
    payload = json.dumps(body).encode() if body is not None else None
    if payload:
        headers["Content-Type"] = "application/json"
    conn = PinnedHTTPS(
        host, str(ip), port, min(int(cfg.get("timeout_seconds", 20)), 60)
    )
    try:
        conn.request(
            method,
            parsed.path + ("?" + parsed.query if parsed.query else ""),
            body=payload,
            headers=headers,
        )
        response = conn.getresponse()
        data = response.read(4 * 1024 * 1024 + 1)
        if len(data) > 4 * 1024 * 1024:
            raise AdapterError("SCHEMA", "Provider response exceeds 4 MiB")
        if response.status in {401, 403}:
            raise AdapterError("AUTHENTICATION", "Provider rejected credentials")
        if response.status == 429:
            raise AdapterError(
                "THROTTLED", "Provider rate limited request; retry with backoff"
            )
        if not 200 <= response.status < 300:
            raise AdapterError("PROVIDER", "Provider read request failed")
        try:
            return json.loads(data) if data else {}
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise AdapterError("SCHEMA", "Provider response is not valid JSON") from exc
    except ssl.SSLCertVerificationError as exc:
        raise AdapterError(
            "TLS", "Provider TLS certificate verification failed"
        ) from exc
    except OSError as exc:
        raise AdapterError("NETWORK", "Provider transport unavailable") from exc
    finally:
        conn.close()


class Adapter:
    platform = ""
    required = ()
    fields = ("credential_ref", "timeout_seconds", "page_size", "auth_type")
    capabilities = ()
    step_semantics = "NOT_AVAILABLE"

    def __init__(self, configuration, transport=None):
        self.config = dict(configuration)
        self.transport = transport or http_request
        self.validate()

    def validate(self):
        if set(self.config) - set(self.fields) - set(self.required):
            raise AdapterError("CONFIGURATION", "Unknown platform configuration fields")
        for key in self.required:
            if not self.config.get(key):
                raise AdapterError("CONFIGURATION", f"Missing {key}")
        if self.config.get("credential_ref"):
            env_reference(self.config["credential_ref"])
        if self.config.get("auth_type", "BEARER") not in {"BEARER", "BASIC", "NONE"}:
            raise AdapterError("CONFIGURATION", "Unsupported authentication type")
        size = self.config.get("page_size", 100)
        if type(size) is not int or not 1 <= size <= 1000:
            raise AdapterError("CONFIGURATION", "page_size must be 1..1000")
        timeout = self.config.get("timeout_seconds", 20)
        if type(timeout) is not int or not 1 <= timeout <= 60:
            raise AdapterError("CONFIGURATION", "timeout_seconds must be 1..60")
        for key in ("base_url", "url"):
            if key in self.config:
                parsed = urlsplit(self.config[key])
                if (
                    parsed.scheme != "https"
                    or not parsed.hostname
                    or parsed.username
                    or parsed.password
                    or parsed.query
                    or parsed.fragment
                ):
                    raise AdapterError(
                        "CONFIGURATION",
                        "Platform URL must be TLS without embedded credentials or query",
                    )
        return self.config

    def collect_with_retry(self, checkpoint=None, attempts=3, sleep=time.sleep):
        """Read-only retries preserve the same checkpoint; no successful progress on errors."""
        if not 1 <= attempts <= 5:
            raise AdapterError("CONFIGURATION", "Retry attempts must be 1..5")
        for attempt in range(attempts):
            try:
                return self.collect(checkpoint)
            except AdapterError as error:
                if (
                    error.kind not in {"THROTTLED", "NETWORK", "PROVIDER"}
                    or attempt == attempts - 1
                ):
                    raise
                sleep(min(2**attempt, 8))

    def discover_capabilities(self):
        return {
            "platform": self.platform,
            "supported": list(self.capabilities),
            "read_only": True,
            "live_verified": False,
            "step_collection": self.step_semantics,
        }

    def test_connection(self):
        batch = self.collect({})
        return {
            "connected": True,
            "record_count": len(batch.events),
            "inventory_complete": batch.complete,
            "evidence": batch.evidence,
        }

    def get(self, path, query=None, method="GET", body=None):
        base = self.config["base_url"].rstrip("/")
        if not path.startswith("/"):
            raise AdapterError("CONFIGURATION", "Provider path must be absolute")
        return self.transport(
            base + path + ("?" + urlencode(query) if query else ""),
            self.config,
            method,
            body,
        )

    def health(self, batch):
        return {
            "status": "CONNECTED" if batch.complete else "COLLECTING",
            "inventory_complete": batch.complete,
            "record_count": len(batch.events),
            "platform": self.platform,
        }

    def normalize(self, record):
        raise NotImplementedError

    def normalize_steps(self, record, parent):
        return []

    def batch(self, records, checkpoint, complete=True):
        if not isinstance(records, list) or len(records) > 1000:
            raise AdapterError("SCHEMA", "Invalid provider inventory")
        events = []
        from app.worker.pentaho_status import safe_text

        for record in records:
            event = self.normalize(record)
            if event:
                raw = json.dumps(record, sort_keys=True, default=str)
                event["evidence"]["raw_record"] = (
                    {
                        "redacted_json": json.dumps(
                            redact_provider_record(record), sort_keys=True, default=str
                        )
                    }
                    if len(raw) <= 16000
                    else {
                        "record_sha256": hashlib.sha256(raw.encode()).hexdigest(),
                        "omitted": "RECORD_TOO_LARGE",
                    }
                )
                event["key"] = (
                    self.platform
                    + ":"
                    + hashlib.sha256(
                        json.dumps(
                            [event["event"], record], sort_keys=True, default=str
                        ).encode()
                    ).hexdigest()
                )
                events.append(event)
                events.extend(self.normalize_steps(record, event))
        return Batch(
            events,
            {
                "platform": self.platform,
                "source_record_count": len(records),
                "read_only": True,
            },
            checkpoint,
            complete,
        )


def provider_error(error):
    code = getattr(error, "response", {}).get("Error", {}).get("Code", "")
    name = type(error).__name__
    sqlstate = str(error.args[0]) if error.args else ""
    if (
        code
        in {
            "AccessDeniedException",
            "UnrecognizedClientException",
            "ExpiredTokenException",
            "InvalidClientTokenId",
        }
        or name in {"NoCredentialsError", "PartialCredentialsError"}
        or sqlstate == "28000"
    ):
        return AdapterError(
            "AUTHENTICATION", "Provider authentication/authorization unavailable"
        )
    if code in {
        "ThrottlingException",
        "TooManyRequestsException",
        "RequestLimitExceeded",
    }:
        return AdapterError("THROTTLED", "Provider rate limited read request")
    if code in {
        "EntityNotFoundException",
        "ResourceNotFoundException",
        "InvalidInputException",
    }:
        return AdapterError(
            "CONFIGURATION", "Provider resource configuration is unavailable"
        )
    if name in {
        "EndpointConnectionError",
        "ConnectTimeoutError",
        "ReadTimeoutError",
    } or sqlstate.startswith("08"):
        return AdapterError("NETWORK", "Provider connection unavailable")
    return AdapterError("PROVIDER", "Provider read failed")


def step_event(
    platform,
    parent,
    record,
    identity,
    name,
    status,
    started=None,
    ended=None,
    attempt=1,
    observed=None,
):
    """A step observation retains source times; observing completion never invents end time."""
    if (
        not identity
        or not name
        or type(attempt) is not int
        or not 1 <= attempt <= 100000
    ):
        raise AdapterError("SCHEMA", "Step identity/name/attempt are invalid")
    start, end = instant(started), instant(ended)
    if start and end and end < start:
        raise AdapterError("SCHEMA", "Step end precedes start")
    timestamp = end or start or instant(observed)
    if not timestamp:
        # The provider supplied actual terminal result but no timing. This is an
        # observation timestamp, explicitly labeled, never a made-up source end.
        timestamp = datetime.now(timezone.utc).isoformat()
        observation_only = True
    else:
        observation_only = False
    event = {
        **parent["event"],
        "event_type": (
            "STEP_FAILED"
            if status == "FAILED"
            else (
                "STEP_END"
                if status == "SUCCESS"
                else "STEP_START" if status == "RUNNING" and start else "STEP_STATUS"
            )
        ),
        "status": status,
        "source_status": status,
        "step_id": str(identity),
        "step_name": str(name),
        "attempt": attempt,
        "timestamp": timestamp,
        "started_at": start,
        "ended_at": end,
        "terminal_status_observed": status in {"SUCCESS", "FAILED"} and end is None,
        "timestamp_provenance": (
            "RECEIVED_OBSERVATION" if observation_only else "SOURCE"
        ),
    }
    from app.worker.pentaho_status import safe_text

    raw = json.dumps(record, sort_keys=True, default=str)
    evidence = {
        "provider": platform,
        "raw_record": {
            "redacted_json": json.dumps(
                redact_provider_record(record), sort_keys=True, default=str
            )
        },
        "timestamp_provenance": event["timestamp_provenance"],
    }
    # Timing-free snapshots retain stable identity across polls even when their
    # received observation time advances.
    key_payload = {
        k: v for k, v in event.items() if not (observation_only and k == "timestamp")
    }
    key = hashlib.sha256(
        json.dumps([key_payload, record], sort_keys=True, default=str).encode()
    ).hexdigest()
    return {
        "key": platform + ":step:" + key,
        "event": event,
        "observed_at": timestamp,
        "evidence": evidence,
    }
