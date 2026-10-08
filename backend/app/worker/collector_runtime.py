"""OpsControl collector runtime.

Runs as a separate process from FastAPI. It schedules enabled collectors,
updates runtime state, and delegates collection to provider-neutral adapters.
No production credentials are read from collector JSON.
"""
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Collector

logger = logging.getLogger("opscontrol.collector-runtime")


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
        if not cfg.get("url"):
            return CollectionResult(False, "API collector requires URL")
        if cfg.get("auth_type", "BASIC") != "BASIC":
            return CollectionResult(False, "Initial API runtime supports Basic Authentication only")
        if not cfg.get("credential_ref"):
            return CollectionResult(False, "API collector requires managed credential reference")
        return CollectionResult(False, "API runtime is blocked until managed credential provider is configured")


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


async def execute_collector(collector_id):
    with SessionLocal() as db:
        collector = db.get(Collector, collector_id)
        if not collector or not collector.enabled:
            return
        collector.status = "RUNNING"
        collector.last_run_at = datetime.now(timezone.utc)
        db.commit()
        adapter = ADAPTERS.get(collector.collector_type)
        if not adapter:
            result = CollectionResult(False, f"No adapter registered for {collector.collector_type}")
        else:
            try:
                result = await adapter.collect(collector)
            except Exception as exc:
                logger.exception("Collector %s failed", collector.name)
                result = CollectionResult(False, str(exc))
        if result.success:
            collector.status = "HEALTHY"
            collector.last_success_at = datetime.now(timezone.utc)
            collector.last_error = None
        else:
            collector.status = "ERROR"
            collector.last_error_at = datetime.now(timezone.utc)
            collector.last_error = result.message
        collector.next_run_at = datetime.now(timezone.utc)
        db.commit()


async def scheduler_loop(poll_seconds=5):
    logger.info("OpsControl collector runtime started")
    while True:
        now = datetime.now(timezone.utc)
        with SessionLocal() as db:
            collectors = db.scalars(select(Collector).where(Collector.enabled.is_(True))).all()
            due = [
                c for c in collectors
                if c.next_run_at is None or c.next_run_at <= now
            ]
            for collector in due:
                collector.next_run_at = now
                db.commit()
                asyncio.create_task(execute_collector(collector.id))
                collector.next_run_at = now + timedelta(seconds=collector.interval_seconds)
                db.commit()
        await asyncio.sleep(poll_seconds)
