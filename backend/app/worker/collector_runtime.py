"""OpsControl collector runtime.

Runs as a separate process from FastAPI. The API adapter is the first real
transport and performs read-only HTTP collection with Basic Authentication.
"""
import asyncio
import json
import logging
import ssl
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.request import HTTPBasicAuthHandler, HTTPPasswordMgrWithPriorAuth, Request, build_opener

from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.models import Collector, CollectorRun, DataSource, MetricDefinition, MetricSample
from app.worker.alert_engine import evaluate_metric_sample
from app.worker.credentials import CredentialProviderError, resolve_basic_auth
from app.worker.notifications import dispatch_pending_notifications

logger = logging.getLogger("opscontrol.collector-runtime")

MAX_RESPONSE_BODY_BYTES = 64 * 1024
MAX_ERROR_LENGTH = 2000


@dataclass
class CollectionResult:
    success: bool
    message: str
    payload: dict | None = None


class CollectorAdapter:
    collector_type = "BASE"

    async def collect(self, collector: Collector) -> CollectionResult:
        raise NotImplementedError


class WindowsAdapter(CollectorAdapter):
    collector_type = "WINDOWS"

    async def collect(self, collector):
        cfg = collector.configuration or {}
        method = cfg.get("method", "AGENT")
        if method not in {"AGENT", "WINRM"}:
            return CollectionResult(False, f"Unsupported Windows method: {method}")
        if not cfg.get("hostname"):
            return CollectionResult(False, "Windows collector requires hostname")
        return CollectionResult(False, "Windows adapter transport is not installed yet; configuration validated only")


class LinuxAdapter(CollectorAdapter):
    collector_type = "LINUX"

    async def collect(self, collector):
        cfg = collector.configuration or {}
        method = cfg.get("method", "AGENT")
        if method not in {"AGENT", "SSH"}:
            return CollectionResult(False, f"Unsupported Linux method: {method}")
        if not cfg.get("hostname"):
            return CollectionResult(False, "Linux collector requires hostname")
        return CollectionResult(False, "Linux adapter transport is not installed yet; configuration validated only")


class ApiAdapter(CollectorAdapter):
    collector_type = "API"

    async def collect(self, collector):
        cfg = collector.configuration or {}
        url = cfg.get("url")
        if not url:
            return CollectionResult(False, "API collector requires URL", {"outcome": "CONFIGURATION_ERROR"})

        if str(cfg.get("auth_type", "BASIC")).upper() != "BASIC":
            return CollectionResult(False, "Initial API runtime supports Basic Authentication only", {"outcome": "CONFIGURATION_ERROR"})

        credential_ref = cfg.get("credential_ref")
        if not credential_ref:
            return CollectionResult(False, "API collector requires managed credential reference", {"outcome": "CONFIGURATION_ERROR"})
        try:
            username, password = resolve_basic_auth(credential_ref)
        except CredentialProviderError as exc:
            return CollectionResult(False, str(exc), {"outcome": "CREDENTIAL_ERROR"})

        method = str(cfg.get("method", "GET")).upper()
        if method not in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"}:
            return CollectionResult(False, f"Unsupported HTTP method: {method}", {"outcome": "CONFIGURATION_ERROR"})

        try:
            timeout_seconds = min(max(float(cfg.get("timeout_seconds", 15)), 1), 120)
            expected = cfg.get("expected_status", 200)
            expected_statuses = {int(x) for x in expected} if isinstance(expected, list) else {int(expected)}
            max_body_bytes = min(max(int(cfg.get("max_response_body_bytes", 4096)), 0), MAX_RESPONSE_BODY_BYTES)
        except (TypeError, ValueError):
            return CollectionResult(False, "timeout_seconds/expected_status/max_response_body_bytes has invalid value", {"outcome": "CONFIGURATION_ERROR"})

        capture_body = bool(cfg.get("capture_response_body", False))
        headers = {"User-Agent": "OpsControl-Collector/1.0", "Accept": "application/json, text/plain, */*"}
        configured_headers = cfg.get("headers") or {}
        if not isinstance(configured_headers, dict):
            return CollectionResult(False, "headers must be an object", {"outcome": "CONFIGURATION_ERROR"})
        for key, value in configured_headers.items():
            if str(key).lower() in {"authorization", "proxy-authorization"}:
                return CollectionResult(False, "Authorization headers must not be configured directly; use credential_ref", {"outcome": "CONFIGURATION_ERROR"})
            headers[str(key)] = str(value)

        body = cfg.get("request_body")
        data = None
        if body is not None:
            if isinstance(body, (dict, list)):
                data = json.dumps(body).encode("utf-8")
                headers.setdefault("Content-Type", "application/json")
            elif isinstance(body, str):
                data = body.encode("utf-8")
            else:
                return CollectionResult(False, "request_body must be an object, array, or string", {"outcome": "CONFIGURATION_ERROR"})

        return await asyncio.to_thread(
            self._request,
            url,
            method,
            username,
            password,
            timeout_seconds,
            expected_statuses,
            bool(cfg.get("verify_ssl", True)),
            capture_body,
            max_body_bytes,
            headers,
            data,
        )

    @staticmethod
    def _request(url, method, username, password, timeout_seconds, expected_statuses,
                 verify_ssl, capture_body, max_body_bytes, headers, data):
        started = time.perf_counter()
        password_manager = HTTPPasswordMgrWithPriorAuth()
        password_manager.add_password(None, url, username, password, is_authenticated=True)
        opener = build_opener(HTTPBasicAuthHandler(password_manager))
        context = None
        if url.lower().startswith("https://"):
            context = ssl.create_default_context() if verify_ssl else ssl._create_unverified_context()

        request = Request(url, data=data, headers=headers, method=method)
        try:
            kwargs = {"timeout": timeout_seconds}
            if context is not None:
                kwargs["context"] = context
            with opener.open(request, **kwargs) as response:
                raw = response.read(MAX_RESPONSE_BODY_BYTES + 1)
                status = response.getcode()
                elapsed = int((time.perf_counter() - started) * 1000)
                payload = {
                    "outcome": "SUCCESS" if status in expected_statuses else "UNEXPECTED_STATUS",
                    "http_status": status,
                    "response_time_ms": elapsed,
                    "response_size_bytes": len(raw),
                    "response_body": raw[:max_body_bytes].decode("utf-8", errors="replace") if capture_body and max_body_bytes else None,
                    "response_body_truncated": len(raw) > MAX_RESPONSE_BODY_BYTES,
                }
                if status not in expected_statuses:
                    return CollectionResult(False, f"Unexpected HTTP status {status}; expected {sorted(expected_statuses)}", payload)
                return CollectionResult(True, "API request completed successfully", payload)
        except HTTPError as exc:
            elapsed = int((time.perf_counter() - started) * 1000)
            payload = {
                "outcome": "AUTHENTICATION_ERROR" if exc.code in {401, 403} else "HTTP_ERROR",
                "http_status": exc.code,
                "response_time_ms": elapsed,
                "response_size_bytes": None,
                "response_body": None,
            }
            if capture_body:
                try:
                    raw = exc.read(MAX_RESPONSE_BODY_BYTES + 1)
                    payload["response_size_bytes"] = len(raw)
                    payload["response_body"] = raw[:max_body_bytes].decode("utf-8", errors="replace")
                    payload["response_body_truncated"] = len(raw) > MAX_RESPONSE_BODY_BYTES
                except Exception:
                    pass
            return CollectionResult(False, f"HTTP {exc.code} returned by API", payload)
        except TimeoutError:
            return CollectionResult(False, "API request timed out", {"outcome": "TIMEOUT", "response_time_ms": int((time.perf_counter() - started) * 1000)})
        except ssl.SSLError as exc:
            return CollectionResult(False, f"TLS error while connecting to API: {exc}", {"outcome": "TLS_ERROR"})
        except URLError as exc:
            return CollectionResult(False, f"API connection failed: {getattr(exc, 'reason', exc)}", {"outcome": "CONNECTION_ERROR"})
        except Exception as exc:
            return CollectionResult(False, f"API collection failed: {exc}", {"outcome": "REQUEST_ERROR"})


class PentahoAdapter(CollectorAdapter):
    collector_type = "PENTAHO"

    async def collect(self, collector):
        cfg = collector.configuration or {}
        if not cfg.get("endpoint"):
            return CollectionResult(False, "Pentaho collector requires endpoint")
        return CollectionResult(False, "Pentaho adapter is read-only and awaits provider implementation")


ADAPTERS = {
    "WINDOWS": WindowsAdapter(),
    "LINUX": LinuxAdapter(),
    "API": ApiAdapter(),
    "PENTAHO": PentahoAdapter(),
}


def _persist_run(collector, result, started_at, ended_at, db):
    payload = result.payload or {}
    run = CollectorRun(
        collector_id=collector.id,
        started_at=started_at,
        ended_at=ended_at,
        status="SUCCESS" if result.success else "FAILED",
        outcome=payload.get("outcome"),
        http_status=payload.get("http_status"),
        response_time_ms=payload.get("response_time_ms"),
        response_size_bytes=payload.get("response_size_bytes"),
        response_body=payload.get("response_body"),
        error_message=None if result.success else result.message[:MAX_ERROR_LENGTH],
    )
    db.add(run)
    db.flush()
    return run


def _extract_metric_value(metric, result):
    payload = result.payload or {}
    extract = str((metric.query_config or {}).get("extract", "")).upper()
    if extract == "AVAILABILITY":
        return 1.0 if result.success else 0.0
    mapping = {
        "HTTP_STATUS": payload.get("http_status"),
        "RESPONSE_TIME_MS": payload.get("response_time_ms"),
        "RESPONSE_SIZE_BYTES": payload.get("response_size_bytes"),
    }
    value = mapping.get(extract)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _persist_metric_samples(collector, run, result, ended_at, db):
    metrics = db.scalars(
        select(MetricDefinition).where(
            MetricDefinition.collector_id == collector.id,
            MetricDefinition.enabled.is_(True),
        )
    ).all()
    samples = []
    for metric in metrics:
        value = _extract_metric_value(metric, result)
        if value is None:
            continue
        sample = MetricSample(
                organization_id=metric.organization_id,
                metric_definition_id=metric.id,
                collector_id=collector.id,
                collector_run_id=run.id,
                observed_at=ended_at,
                value_numeric=value,
                unit=metric.unit,
                dimensions={
                    "collector_type": collector.collector_type,
                    "outcome": (result.payload or {}).get("outcome"),
                },
            )
        db.add(sample)
        db.flush()
        samples.append(sample)
    return samples


def _purge_expired_metric_samples(db, now):
    definitions = db.execute(select(MetricDefinition.id, MetricDefinition.retention_days)).all()
    deleted = 0
    for metric_id, retention_days in definitions:
        cutoff = now - timedelta(days=max(int(retention_days), 1))
        result = db.execute(delete(MetricSample).where(
            MetricSample.metric_definition_id == metric_id,
            MetricSample.observed_at < cutoff,
        ))
        deleted += result.rowcount or 0
    return deleted


async def execute_collector(collector_id):
    with SessionLocal() as db:
        collector = db.get(Collector, collector_id)
        if not collector or not collector.enabled:
            return

        data_source = db.get(DataSource, collector.data_source_id)
        if not data_source or not data_source.enabled:
            collector.status = "STOPPED"
            collector.last_error = "Data source is disabled or missing"
            db.commit()
            return

        started_at = datetime.now(timezone.utc)
        collector.status = "RUNNING"
        collector.last_run_at = started_at
        db.commit()

        adapter = ADAPTERS.get(collector.collector_type.upper())
        try:
            result = await adapter.collect(collector) if adapter else CollectionResult(
                False,
                f"No adapter registered for {collector.collector_type}",
                {"outcome": "UNSUPPORTED_COLLECTOR"},
            )
        except Exception:
            logger.exception("Collector %s failed", collector.name)
            result = CollectionResult(False, "Collector execution failed", {"outcome": "RUNTIME_ERROR"})

        ended_at = datetime.now(timezone.utc)
        run = _persist_run(collector, result, started_at, ended_at, db)
        samples = _persist_metric_samples(collector, run, result, ended_at, db)
        for sample in samples:
            evaluate_metric_sample(db, sample)

        if result.success:
            collector.status = "HEALTHY"
            collector.last_success_at = ended_at
            collector.last_error = None
            data_source.status = "HEALTHY"
            data_source.last_error = None
        else:
            collector.status = "ERROR"
            collector.last_error_at = ended_at
            collector.last_error = result.message[:MAX_ERROR_LENGTH]
            data_source.status = "ERROR"
            data_source.last_error = result.message[:MAX_ERROR_LENGTH]

        collector.next_run_at = ended_at + timedelta(seconds=max(collector.interval_seconds, 5))
        db.commit()


async def scheduler_loop(poll_seconds=5):
    logger.info("OpsControl collector runtime started")
    last_retention_cleanup = datetime.now(timezone.utc)
    while True:
        now = datetime.now(timezone.utc)
        with SessionLocal() as db:
            if (now - last_retention_cleanup).total_seconds() >= 3600:
                deleted = _purge_expired_metric_samples(db, now)
                if deleted:
                    logger.info("Purged %s expired metric samples", deleted)
                db.commit()
                last_retention_cleanup = now
            collectors = db.scalars(
                select(Collector).where(
                    Collector.enabled.is_(True),
                    (Collector.next_run_at.is_(None) | (Collector.next_run_at <= now)),
                )
            ).all()
            for collector in collectors:
                collector.next_run_at = now + timedelta(seconds=max(collector.interval_seconds, 5))
                db.commit()
                asyncio.create_task(execute_collector(collector.id))
        await asyncio.to_thread(dispatch_pending_notifications)
        await asyncio.sleep(poll_seconds)
