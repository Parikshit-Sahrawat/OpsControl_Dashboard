"""OpsControl collector runtime.

Runs as a separate process from FastAPI. The API adapter is the first real
transport and performs read-only HTTP collection with Basic Authentication.
"""

import asyncio
import json
import logging
import ssl
import time
import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.request import (
    HTTPBasicAuthHandler,
    HTTPPasswordMgrWithPriorAuth,
    HTTPSHandler,
    HTTPRedirectHandler,
    ProxyHandler,
    Request,
    build_opener,
)

from sqlalchemy import select, func, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, engine
from app.core.config import settings
from app.security.models import (
    WorkerIdentity,
)  # Register collector FK metadata in standalone workers.
from app.models import (
    Collector,
    Organization,
    CollectorRun,
    DataSource,
    MetricDefinition,
    MetricSample,
)
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
        return CollectionResult(
            False,
            "Windows adapter transport is not installed yet; configuration validated only",
        )


class LinuxAdapter(CollectorAdapter):
    collector_type = "LINUX"

    async def collect(self, collector):
        cfg = collector.configuration or {}
        method = cfg.get("method", "AGENT")
        if method not in {"AGENT", "SSH"}:
            return CollectionResult(False, f"Unsupported Linux method: {method}")
        if not cfg.get("hostname"):
            return CollectionResult(False, "Linux collector requires hostname")
        return CollectionResult(
            False,
            "Linux adapter transport is not installed yet; configuration validated only",
        )


class ApiAdapter(CollectorAdapter):
    collector_type = "API"

    async def collect(self, collector):
        # Legacy collection shares the control plane's workload identity and
        # lacks the remote protocol's tenant-bound destination/secret policy.
        # Fail closed in production, including collectors created before RBAC
        # hardening. Use an explicitly assigned, egress-restricted remote worker.
        if settings.environment.lower() == "production":
            return CollectionResult(
                False,
                "Production API collection requires an approved remote worker",
                {"outcome": "CONFIGURATION_ERROR"},
            )
        cfg = collector.configuration or {}
        url = cfg.get("url")
        if not url:
            return CollectionResult(
                False, "API collector requires URL", {"outcome": "CONFIGURATION_ERROR"}
            )

        if str(cfg.get("auth_type", "BASIC")).upper() != "BASIC":
            return CollectionResult(
                False,
                "Initial API runtime supports Basic Authentication only",
                {"outcome": "CONFIGURATION_ERROR"},
            )

        credential_ref = cfg.get("credential_ref")
        if not credential_ref:
            return CollectionResult(
                False,
                "API collector requires managed credential reference",
                {"outcome": "CONFIGURATION_ERROR"},
            )
        try:
            username, password = resolve_basic_auth(credential_ref)
        except CredentialProviderError as exc:
            return CollectionResult(False, str(exc), {"outcome": "CREDENTIAL_ERROR"})

        method = str(cfg.get("method", "GET")).upper()
        if method not in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"}:
            return CollectionResult(
                False,
                f"Unsupported HTTP method: {method}",
                {"outcome": "CONFIGURATION_ERROR"},
            )

        try:
            timeout_seconds = min(max(float(cfg.get("timeout_seconds", 15)), 1), 120)
            expected = cfg.get("expected_status", 200)
            expected_statuses = (
                {int(x) for x in expected}
                if isinstance(expected, list)
                else {int(expected)}
            )
            max_body_bytes = min(
                max(int(cfg.get("max_response_body_bytes", 4096)), 0),
                MAX_RESPONSE_BODY_BYTES,
            )
        except (TypeError, ValueError):
            return CollectionResult(
                False,
                "timeout_seconds/expected_status/max_response_body_bytes has invalid value",
                {"outcome": "CONFIGURATION_ERROR"},
            )

        capture_body = bool(cfg.get("capture_response_body", False))
        headers = {
            "User-Agent": "OpsControl-Collector/1.0",
            "Accept": "application/json, text/plain, */*",
        }
        configured_headers = cfg.get("headers") or {}
        if not isinstance(configured_headers, dict):
            return CollectionResult(
                False, "headers must be an object", {"outcome": "CONFIGURATION_ERROR"}
            )
        for key, value in configured_headers.items():
            if str(key).lower() in {"authorization", "proxy-authorization"}:
                return CollectionResult(
                    False,
                    "Authorization headers must not be configured directly; use credential_ref",
                    {"outcome": "CONFIGURATION_ERROR"},
                )
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
                return CollectionResult(
                    False,
                    "request_body must be an object, array, or string",
                    {"outcome": "CONFIGURATION_ERROR"},
                )

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
    def _request(
        url,
        method,
        username,
        password,
        timeout_seconds,
        expected_statuses,
        verify_ssl,
        capture_body,
        max_body_bytes,
        headers,
        data,
    ):
        started = time.perf_counter()
        password_manager = HTTPPasswordMgrWithPriorAuth()
        password_manager.add_password(
            None, url, username, password, is_authenticated=True
        )
        context = None
        if url.lower().startswith("https://"):
            context = (
                ssl.create_default_context()
                if verify_ssl
                else ssl._create_unverified_context()
            )

        class NoRedirect(HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None  # Never forward credentials to a redirected target.

        opener = build_opener(
            ProxyHandler({}),
            NoRedirect(),
            HTTPBasicAuthHandler(password_manager),
            HTTPSHandler(context=context),
        )
        request = Request(url, data=data, headers=headers, method=method)
        try:
            with opener.open(request, timeout=timeout_seconds) as response:
                raw = response.read(MAX_RESPONSE_BODY_BYTES + 1)
                status = response.getcode()
                elapsed = int((time.perf_counter() - started) * 1000)
                payload = {
                    "outcome": (
                        "SUCCESS"
                        if status in expected_statuses
                        else "UNEXPECTED_STATUS"
                    ),
                    "http_status": status,
                    "response_time_ms": elapsed,
                    "response_size_bytes": len(raw),
                    "response_body": (
                        raw[:max_body_bytes].decode("utf-8", errors="replace")
                        if capture_body and max_body_bytes
                        else None
                    ),
                    "response_body_truncated": len(raw) > MAX_RESPONSE_BODY_BYTES,
                }
                if status not in expected_statuses:
                    return CollectionResult(
                        False,
                        f"Unexpected HTTP status {status}; expected {sorted(expected_statuses)}",
                        payload,
                    )
                return CollectionResult(
                    True, "API request completed successfully", payload
                )
        except HTTPError as exc:
            elapsed = int((time.perf_counter() - started) * 1000)
            payload = {
                "outcome": (
                    "AUTHENTICATION_ERROR" if exc.code in {401, 403} else "HTTP_ERROR"
                ),
                "http_status": exc.code,
                "response_time_ms": elapsed,
                "response_size_bytes": None,
                "response_body": None,
            }
            if capture_body:
                try:
                    raw = exc.read(MAX_RESPONSE_BODY_BYTES + 1)
                    payload["response_size_bytes"] = len(raw)
                    payload["response_body"] = raw[:max_body_bytes].decode(
                        "utf-8", errors="replace"
                    )
                    payload["response_body_truncated"] = (
                        len(raw) > MAX_RESPONSE_BODY_BYTES
                    )
                except Exception:
                    pass
            return CollectionResult(False, f"HTTP {exc.code} returned by API", payload)
        except TimeoutError:
            return CollectionResult(
                False,
                "API request timed out",
                {
                    "outcome": "TIMEOUT",
                    "response_time_ms": int((time.perf_counter() - started) * 1000),
                },
            )
        except ssl.SSLError as exc:
            return CollectionResult(
                False,
                f"TLS error while connecting to API: {exc}",
                {"outcome": "TLS_ERROR"},
            )
        except URLError as exc:
            return CollectionResult(
                False,
                f"API connection failed: {getattr(exc, 'reason', exc)}",
                {"outcome": "CONNECTION_ERROR"},
            )
        except Exception as exc:
            return CollectionResult(
                False, f"API collection failed: {exc}", {"outcome": "REQUEST_ERROR"}
            )


class AwsEC2Adapter(CollectorAdapter):
    collector_type = "AWS_EC2"

    async def collect(self, collector):
        from app.worker.provider_checks import ec2_health, ProviderCheckError

        try:
            payload = await asyncio.to_thread(ec2_health, collector.configuration or {})
            return CollectionResult(
                payload["outcome"] == "SUCCESS",
                "Read-only EC2 status collected",
                payload,
            )
        except (ProviderCheckError, ImportError):
            return CollectionResult(
                False,
                "EC2 configuration or SDK unavailable",
                {"outcome": "CONFIGURATION_ERROR"},
            )
        except Exception:
            return CollectionResult(
                False, "EC2 read-only API unavailable", {"outcome": "PROVIDER_ERROR"}
            )


class KubernetesAdapter(CollectorAdapter):
    collector_type = "KUBERNETES"

    async def collect(self, collector):
        from app.worker.provider_checks import kubernetes_health, ProviderCheckError

        try:
            payload = await asyncio.to_thread(
                kubernetes_health, collector.configuration or {}
            )
            return CollectionResult(
                payload["outcome"] == "SUCCESS",
                "Read-only Kubernetes status collected",
                payload,
            )
        except (ProviderCheckError, ImportError):
            return CollectionResult(
                False,
                "Kubernetes RBAC/configuration/SDK unavailable",
                {"outcome": "CONFIGURATION_ERROR"},
            )
        except Exception:
            return CollectionResult(
                False,
                "Kubernetes read-only API unavailable",
                {"outcome": "PROVIDER_ERROR"},
            )


class PentahoAdapter(CollectorAdapter):
    collector_type = "PENTAHO"

    async def collect(self, collector):
        from app.worker.pentaho_status import get_job_status, PentahoStatusError

        try:
            # Validate tenant association before resolving privileged credentials
            # or making an outbound request, including legacy Collector API paths.
            from uuid import UUID
            from app.models import JobOrder

            with SessionLocal() as db:
                job = db.get(
                    JobOrder, UUID((collector.configuration or {})["job_order_id"])
                )
                source = db.get(DataSource, collector.data_source_id)
                if (
                    not job
                    or not source
                    or job.organization_id != source.organization_id
                ):
                    raise PentahoStatusError(
                        "Job Order unavailable in source organization"
                    )
            payload = await asyncio.to_thread(
                get_job_status, collector.configuration or {}
            )
            return CollectionResult(
                payload["outcome"] == "SUCCESS",
                "Read-only Pentaho execution status collected",
                payload,
            )
        except (
            PentahoStatusError,
            CredentialProviderError,
            ValueError,
            KeyError,
            TypeError,
        ):
            return CollectionResult(
                False,
                "Pentaho status configuration, credentials or network policy invalid",
                {"outcome": "CONFIGURATION_ERROR"},
            )
        except Exception:
            return CollectionResult(
                False,
                "Pentaho Carte read-only status unavailable",
                {"outcome": "PROVIDER_ERROR"},
            )


class LinuxHostMetricsAdapter(CollectorAdapter):
    collector_type = "LINUX_HOST"

    async def collect(self, collector):
        from app.worker.deep_checks import linux_host_health, DeepCheckError

        try:
            payload = await asyncio.to_thread(
                linux_host_health, collector.configuration or {}
            )
            return CollectionResult(
                payload["outcome"] == "SUCCESS",
                "Read-only Linux host/process metrics",
                payload,
            )
        except (DeepCheckError, ValueError, OSError):
            return CollectionResult(
                False,
                "Host configuration or metrics unavailable",
                {"outcome": "CONFIGURATION_ERROR"},
            )


class WindowsHostMetricsAdapter(CollectorAdapter):
    collector_type = "WINDOWS_HOST"

    async def collect(self, collector):
        from app.worker.deep_checks import windows_host_health, DeepCheckError

        try:
            payload = await asyncio.to_thread(
                windows_host_health, collector.configuration or {}
            )
            return CollectionResult(
                payload["outcome"] == "SUCCESS",
                "Read-only Windows host/process metrics",
                payload,
            )
        except (DeepCheckError, ValueError, OSError):
            return CollectionResult(
                False,
                "Windows host metrics unavailable",
                {"outcome": "CONFIGURATION_ERROR"},
            )


class ApacheStatusAdapter(CollectorAdapter):
    collector_type = "APACHE"

    async def collect(self, collector):
        from app.worker.deep_checks import apache_status, DeepCheckError

        try:
            payload = await asyncio.to_thread(
                apache_status, collector.configuration or {}
            )
            return CollectionResult(True, "Read-only Apache status", payload)
        except Exception:
            return CollectionResult(
                False,
                "Apache status unavailable or unauthorized",
                {"outcome": "PROVIDER_ERROR"},
            )


class TomcatStatusAdapter(CollectorAdapter):
    collector_type = "TOMCAT"

    async def collect(self, collector):
        from app.worker.deep_checks import tomcat_status, DeepCheckError

        try:
            payload = await asyncio.to_thread(
                tomcat_status, collector.configuration or {}
            )
            return CollectionResult(True, "Read-only Tomcat JVM status", payload)
        except Exception:
            return CollectionResult(
                False,
                "Tomcat status unavailable or unauthorized",
                {"outcome": "PROVIDER_ERROR"},
            )


from app.unified.adapters import NativeAPIAdapter, IICSAdapter

ADAPTERS = {
    "NATIVE_API": NativeAPIAdapter(),
    "IICS_NATIVE": IICSAdapter(),
    "WINDOWS": WindowsAdapter(),
    "LINUX": LinuxAdapter(),
    "API": ApiAdapter(),
    "PENTAHO": PentahoAdapter(),
    "AWS_EC2": AwsEC2Adapter(),
    "EC2": AwsEC2Adapter(),
    "KUBERNETES": KubernetesAdapter(),
    "K8S": KubernetesAdapter(),
    "LINUX_HOST": LinuxHostMetricsAdapter(),
    "WINDOWS_HOST": WindowsHostMetricsAdapter(),
    "APACHE": ApacheStatusAdapter(),
    "TOMCAT": TomcatStatusAdapter(),
}


def _persist_run(collector, result, started_at, ended_at, db):
    payload = result.payload or {}
    run = CollectorRun(
        collector_id=collector.id,
        started_at=started_at,
        ended_at=ended_at,
        status="SUCCESS" if result.success else "FAILED",
        outcome=payload.get("outcome"),
        source_metadata={
            k: payload[k]
            for k in (
                "inventory_complete",
                "provider",
                "record_count",
                "resource_id",
                "probe_location",
                "execution_records",
                "unresolved_record_count",
                "provider_evidence",
            )
            if k in payload
        },
        http_status=payload.get("http_status"),
        response_time_ms=payload.get("response_time_ms"),
        response_size_bytes=payload.get("response_size_bytes"),
        response_body=payload.get("response_body"),
        error_message=None if result.success else result.message[:MAX_ERROR_LENGTH],
    )
    if collector.collector_type == "NATIVE_API":
        from app.unified.models import (
            MonitoringResource,
            ParameterVersion,
            ParameterActivation,
        )

        root = db.scalar(
            select(MonitoringResource).where(
                MonitoringResource.primary_collector_id == collector.id,
                MonitoringResource.domain == "API",
            )
        )
        policy = (
            db.scalar(
                select(ParameterVersion)
                .join(
                    ParameterActivation,
                    (ParameterActivation.resource_id == ParameterVersion.resource_id)
                    & (
                        ParameterActivation.parameter_version
                        == ParameterVersion.version
                    ),
                )
                .where(
                    ParameterActivation.resource_id == root.id,
                    ParameterActivation.effective_from <= ended_at,
                    (
                        ParameterActivation.effective_to.is_(None)
                        | (ParameterActivation.effective_to > ended_at)
                    ),
                )
            )
            if root
            else None
        )
        if policy:
            run.source_metadata = {
                **(run.source_metadata or {}),
                "policy_version": policy.version,
                "policy_sha256": policy.sha256,
                "expected_statuses": policy.configuration["expected_statuses"],
            }
            if run.http_status is not None:
                matched = run.http_status in policy.configuration["expected_statuses"]
                run.outcome = "SUCCESS" if matched else "ASSERTION_FAILED"
                run.status = "SUCCESS" if matched else "FAILED"
                result.success = matched
        else:
            run.source_metadata = {
                **(run.source_metadata or {}),
                "policy_assessed": False,
            }
    db.add(run)
    db.flush()
    return run


def _extract_metric_value(metric, result):
    payload = result.payload or {}
    extract = str((metric.query_config or {}).get("extract", "")).upper()
    if extract == "AVAILABILITY":
        return 1.0 if result.success else 0.0
    mapping = {
        "HOST_CPU_PERCENT": payload.get("cpu_percent"),
        "HOST_PROCESS_RUNNING": (
            1
            if payload.get("process_running") is True
            else 0 if payload.get("process_running") is False else None
        ),
        "K8S_NODE_READY": (
            1
            if payload.get("node_ready") is True
            else 0 if payload.get("node_ready") is False else None
        ),
        "HOST_MEMORY_USED_PERCENT": payload.get("memory_used_percent"),
        "HOST_DISK_USED_PERCENT": payload.get("disk_used_percent"),
        "APACHE_BUSY_WORKERS": payload.get("busy_workers"),
        "TOMCAT_HEAP_USED_PERCENT": payload.get("jvm_heap_used_percent"),
        "EC2_CPU_PERCENT": payload.get("cpu_percent"),
        "K8S_RESTARTS": payload.get("restarts"),
        "K8S_AVAILABLE_REPLICAS": payload.get("available_replicas"),
        "PENTAHO_ERRORS": payload.get("nr_errors"),
        "PENTAHO_RUNNING": (
            1
            if payload.get("execution_status") == "RUNNING"
            else 0 if payload.get("execution_status") in {"SUCCESS", "FAILED"} else None
        ),
        "HTTP_STATUS": payload.get("http_status"),
        "RESPONSE_TIME_MS": payload.get("response_time_ms"),
        "RESPONSE_SIZE_BYTES": payload.get("response_size_bytes"),
    }
    value = mapping.get(extract)
    if value is None:
        return None
    try:
        import math

        numeric = float(value)
        return numeric if math.isfinite(numeric) else None
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
    from app.services.retention import prune_batch

    return prune_batch(db, now=now)["metric_samples"]


def _persist_pentaho_history(collector, result, observed_at, db):
    from app.services.etl_monitoring import ingest_snapshot

    ingest_snapshot(collector, result, observed_at, db)


async def execute_collector(collector_id, *, scheduled=False):
    # Session advisory locks fence the SAME collector across local processes.
    # PostgreSQL releases them on process/connection death. Never return a
    # locked connection to the pool; a failed unlock invalidates it instead.
    key = int.from_bytes(
        hashlib.sha256(f"local-collector:{collector_id}".encode()).digest()[:8],
        "big",
        signed=True,
    )
    with engine.connect() as connection:
        acquired = connection.scalar(
            text("SELECT pg_try_advisory_lock(:key)"), {"key": key}
        )
        connection.commit()
        if not acquired:
            return
        try:
            with Session(bind=connection) as db:
                await _execute_locked(collector_id, db, scheduled=scheduled)
        finally:
            try:
                connection.rollback()
                connection.execute(
                    text("SELECT pg_advisory_unlock(:key)"), {"key": key}
                )
                connection.commit()
            except SQLAlchemyError:
                connection.invalidate()


async def _execute_locked(collector_id, db, *, scheduled=False):
    collector = db.get(Collector, collector_id)
    if not collector or not collector.enabled or collector.remote_worker_id is not None:
        return
    due = collector.next_run_at
    if due and due.tzinfo is None:
        due = due.replace(tzinfo=timezone.utc)
    if scheduled and due and due > datetime.now(timezone.utc):
        return

    data_source = db.get(DataSource, collector.data_source_id)
    customer = (
        db.get(Organization, data_source.organization_id) if data_source else None
    )
    if (
        not data_source
        or not data_source.enabled
        or not customer
        or not customer.active
    ):
        collector.status = "STOPPED"
        collector.last_error = "Data source is disabled or missing"
        db.commit()
        return

    started_at = datetime.now(timezone.utc)
    collector.status = "RUNNING"
    collector.last_run_at = started_at
    collector.next_run_at = started_at + timedelta(
        seconds=max(collector.interval_seconds, 5)
    )
    db.commit()

    adapter = ADAPTERS.get(collector.collector_type.upper())
    try:
        if collector.collector_type.upper() == "PIPELINE_NATIVE":
            from app.registry.runtime import collect_pipeline

            result = await collect_pipeline(db, collector, data_source)
        else:
            result = (
                await adapter.collect(collector)
                if adapter
                else CollectionResult(
                    False,
                    f"No adapter registered for {collector.collector_type}",
                    {"outcome": "UNSUPPORTED_COLLECTOR"},
                )
            )
    except Exception:
        logger.error("Collector %s execution failed", collector.id)
        result = CollectionResult(
            False, "Collector execution failed", {"outcome": "RUNTIME_ERROR"}
        )

    ended_at = datetime.now(timezone.utc)
    run = _persist_run(collector, result, started_at, ended_at, db)
    from app.worker.infrastructure import INFRA_TYPES, normalize, safe_evidence

    if collector.collector_type.upper() in INFRA_TYPES:
        from app.models import InfrastructureEvidence

        db.add(
            InfrastructureEvidence(
                organization_id=data_source.organization_id,
                data_source_id=data_source.id,
                collector_id=collector.id,
                collector_run_id=run.id,
                observed_at=ended_at,
                provider=normalize(collector.collector_type),
                payload=safe_evidence(result.payload),
            )
        )
    samples = _persist_metric_samples(collector, run, result, ended_at, db)
    _persist_pentaho_history(collector, result, ended_at, db)
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

    collector.next_run_at = ended_at + timedelta(
        seconds=max(collector.interval_seconds, 5)
    )
    db.commit()


def _due_collector_ids(limit, excluded=()):
    with SessionLocal() as db:
        return list(
            db.scalars(
                select(Collector.id)
                .join(DataSource, Collector.data_source_id == DataSource.id)
                .join(Organization, DataSource.organization_id == Organization.id)
                .where(
                    DataSource.enabled.is_(True),
                    Organization.active.is_(True),
                    Collector.enabled.is_(True),
                    func.upper(Collector.collector_type).not_in(
                        ("OTEL", "PIPELINE_V16_PROXY")
                    ),
                    Collector.remote_worker_id.is_(None),
                    Collector.id.not_in(excluded),
                    (
                        Collector.next_run_at.is_(None)
                        | (Collector.next_run_at <= datetime.now(timezone.utc))
                    ),
                )
                .order_by(Collector.next_run_at.nullsfirst(), Collector.id)
                .limit(limit)
            )
        )


def _retention_once():
    with SessionLocal() as db:
        _purge_expired_metric_samples(db, datetime.now(timezone.utc))
        db.commit()


async def _notification_loop(poll_seconds):
    while True:
        try:
            await asyncio.to_thread(dispatch_pending_notifications)
        except Exception:
            logger.error("Notification dispatch unavailable; retrying")
        await asyncio.sleep(poll_seconds)


async def _native_engine_loop(poll_seconds):
    from app.unified.engines import cycle

    while True:
        try:
            await asyncio.to_thread(cycle)

            def incidents_once():
                from app.native_incidents.service import process_incidents

                with SessionLocal() as db:
                    process_incidents(db)
                    db.commit()

            await asyncio.to_thread(incidents_once)
        except Exception:
            logger.error(
                "Native engine evaluation unavailable; durable state will retry"
            )
        await asyncio.sleep(poll_seconds)


async def scheduler_loop(poll_seconds=5):
    logger.info("OpsControl collector runtime started")
    last_retention_cleanup = datetime.now(timezone.utc)
    # Reserve a connection for polling/maintenance; retain at most this many
    # task objects, instead of queuing an unbounded fleet behind a semaphore.
    capacity = min(
        settings.collector_max_concurrency, max(1, settings.database_pool_size - 2)
    )
    pending = {}
    notifications = asyncio.create_task(_notification_loop(poll_seconds))
    native_engines = asyncio.create_task(_native_engine_loop(poll_seconds))

    async def pipeline_control_loop():
        from app.data_pipelines.runtime import tick, run_source, run_operation
        from app.data_pipelines.models import PipelineOperation
        from app.data_pipelines.service import PipelineError

        tasks = {}
        last_reconcile = None
        backlog = []

        async def execute(kind, id):
            try:
                if kind == "sources":
                    await asyncio.to_thread(run_source, id)
                elif kind == "operations":
                    await asyncio.to_thread(run_operation, id)
                else:

                    def recovery_source():
                        with SessionLocal() as db:
                            return db.get(PipelineOperation, id).source_id

                    sid = await asyncio.to_thread(recovery_source)
                    await asyncio.to_thread(run_source, sid, id)
            except PipelineError:
                pass  # held/unverified/claimed sources are intentionally fail closed
            except Exception:
                logger.error("Pipeline operation unavailable; durable state retained")

        try:
            while True:
                tasks = {k: v for k, v in tasks.items() if not v.done()}
                now = datetime.now(timezone.utc)
                if (
                    last_reconcile is None
                    or (now - last_reconcile).total_seconds() >= 60
                ):
                    try:
                        work = await asyncio.to_thread(tick, False) or {}
                        backlog = [
                            (kind, id)
                            for kind in ("sources", "operations", "recoveries")
                            for id in work.get(kind, [])
                        ]
                        last_reconcile = now
                    except Exception:
                        logger.error("Pipeline reconciliation unavailable; fail closed")
                while backlog and len(tasks) < max(
                    1, min(4, settings.database_pool_size // 2)
                ):
                    key = backlog.pop(0)
                    if key not in tasks:
                        tasks[key] = asyncio.create_task(execute(*key))
                await asyncio.sleep(5)
        finally:
            for task in tasks.values():
                task.cancel()
            if tasks:
                await asyncio.gather(*tasks.values(), return_exceptions=True)

    pipeline_control = asyncio.create_task(pipeline_control_loop())
    try:
        while True:
            for cid, task in list(pending.items()):
                if task.done():
                    pending.pop(cid)
                    try:
                        task.result()
                    except Exception:
                        logger.error("Collector task failed; next poll will retry")
            try:
                now = datetime.now(timezone.utc)
                if (now - last_retention_cleanup).total_seconds() >= 3600:
                    await asyncio.to_thread(_retention_once)
                    last_retention_cleanup = now
                slots = capacity - len(pending)
                if slots:
                    for cid in await asyncio.to_thread(
                        _due_collector_ids, slots, tuple(pending)
                    ):
                        if cid not in pending:
                            pending[cid] = asyncio.create_task(
                                execute_collector(cid, scheduled=True)
                            )
            except Exception:
                logger.error("Collector scheduling unavailable; next poll will retry")
            await asyncio.sleep(poll_seconds)
    finally:
        notifications.cancel()
        native_engines.cancel()
        pipeline_control.cancel()
        for task in pending.values():
            task.cancel()
        await asyncio.gather(
            notifications,
            native_engines,
            pipeline_control,
            *pending.values(),
            return_exceptions=True,
        )
