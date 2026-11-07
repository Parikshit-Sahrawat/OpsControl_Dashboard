"""Bounded multi-level HTTP ingestion/load study with independent DB accounting."""

import app.main  # noqa: F401
import json
import os
import time
import uuid
import secrets
import threading
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from urllib.request import Request, urlopen
from sqlalchemy import select, func, text
from app.db.session import SessionLocal
from app.models import DataSource, Collector, MetricDefinition, MetricSample
from app.telemetry.models import ManagedAgent, TelemetryReceipt
from app.security.models import WorkerIdentity
from app.security.http import token_digest

assert os.environ.get("OPSCONTROL_V16_ACCEPTANCE") == "1"
assert os.environ.get("ENVIRONMENT") == "test"
out = Path(os.environ["V16_EVIDENCE_DIR"])
fixture = json.loads(
    (Path(os.environ["V16_PRIVATE_DIR"]) / "browser-fixture.json").read_text()
)
base = os.environ["V16_API_URL"]
org = fixture["organization_id"]


def call(path, token, payload=None):
    start = time.perf_counter()
    headers = {"Authorization": "Bearer " + token, "X-OpsControl-Customers": org}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    with urlopen(
        Request(
            base + "/api/v1/" + path,
            headers=headers,
            data=json.dumps(payload).encode() if payload is not None else None,
        ),
        timeout=20,
    ) as r:
        body = json.load(r)
        return body, {
            "path": path.split("?")[0],
            "ms": (time.perf_counter() - start) * 1000,
            "status": r.status,
            "sql_queries": int(r.headers["x-sprint-test-sql-count"]),
        }


login, _ = call(
    "auth/login",
    "unused",
    {"username": "v16-api-admin", "password": fixture["password"]},
)
token = login["access_token"]
secret = secrets.token_urlsafe(32)
with SessionLocal() as db:
    sources = [
        DataSource(
            organization_id=uuid.UUID(org),
            name="load-" + uuid.uuid4().hex,
            source_type="LINUX",
            enabled=True,
        )
        for _ in range(30)
    ]
    db.add_all(sources)
    db.flush()
    collectors = [
        Collector(
            data_source_id=s.id,
            name="bounded-load-collector",
            collector_type="OTEL",
            enabled=True,
        )
        for s in sources
    ]
    db.add_all(collectors)
    worker = WorkerIdentity(
        organization_id=uuid.UUID(org),
        name=uuid.uuid4().hex,
        token_hash=token_digest(secret),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db.add(worker)
    db.flush()
    agent = ManagedAgent(
        organization_id=uuid.UUID(org),
        collector_id=collectors[0].id,
        worker_id=worker.id,
        hostname="synthetic.invalid",
        version="SYNTHETIC",
        runtime_version="0.123.0",
    )
    db.add(agent)
    db.commit()
    cid, aid, sid = collectors[0].id, agent.id, sources[0].id
paths = [
    "infrastructure/resources?limit=25",
    "resource-management/data-sources?paginated=true&limit=25",
    "unified/resources?limit=25",
    f"monitoring/data-sources/{sid}/effective-configuration",
]
levels = []
base_time = datetime.now(timezone.utc) - timedelta(minutes=1)
ordinal = 0
api_pid = int(os.environ["V16_API_PID"])


def process_sample():
    fields = Path(f"/proc/{api_pid}/stat").read_text().split()
    return {
        "monotonic": time.monotonic(),
        "cpu_ticks": int(fields[13]) + int(fields[14]),
        "rss_bytes": int(fields[23]) * os.sysconf("SC_PAGE_SIZE"),
    }


for name, users, producers, pause in [
    ("idle", 1, 0, 0.04),
    ("moderate", 2, 1, 0.05),
    ("higher", 4, 2, 0.02),
]:
    started = time.monotonic()
    stop = threading.Event()
    metrics = []
    errors = []
    lock = threading.Lock()
    samples = []
    inventory = []

    def sampler():
        while not stop.is_set():
            samples.append(process_sample())
            stop.wait(0.1)

    def reader():
        i = 0
        while time.monotonic() - started < 5:
            try:
                _, m = call(paths[i % len(paths)], token)
                with lock:
                    metrics.append(m)
            except Exception as exc:
                with lock:
                    errors.append(type(exc).__name__)
            i += 1
            time.sleep(0.02)

    def producer(number):
        global ordinal
        for batch in range(25):
            with lock:
                ids = list(range(ordinal, ordinal + 10))
                ordinal += 10
                inventory.extend(ids)
            payload = {
                "resourceMetrics": [
                    {
                        "scopeMetrics": [
                            {
                                "metrics": [
                                    {
                                        "name": "sprint.sustained." + str(number),
                                        "gauge": {
                                            "dataPoints": [
                                                {
                                                    "timeUnixNano": str(
                                                        int(
                                                            (
                                                                base_time
                                                                + timedelta(
                                                                    milliseconds=i
                                                                )
                                                            ).timestamp()
                                                            * 1e9
                                                        )
                                                    ),
                                                    "asDouble": i,
                                                }
                                                for i in ids
                                            ]
                                        },
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
            _, m = call("agent/otlp/v1/metrics", secret, payload)
            assert m["status"] == 200
            time.sleep(pause)

    sampling = threading.Thread(target=sampler)
    sampling.start()
    try:
        with ThreadPoolExecutor(max_workers=users + producers + 1) as pool:
            readers = [pool.submit(reader) for _ in range(users)]
            writers = [pool.submit(producer, n) for n in range(producers)]
            if name == "higher":
                subprocess.run(
                    [
                        "node",
                        str(
                            Path(__file__).resolve().parents[2]
                            / "frontend/scripts/sprint1_load_navigation.mjs"
                        ),
                    ],
                    check=True,
                    timeout=50,
                )
            for future in readers + writers:
                future.result()
    finally:
        stop.set()
        sampling.join()
    elapsed = time.monotonic() - started
    ordered = sorted(m["ms"] for m in metrics)
    assert ordered and not errors
    with SessionLocal() as db:
        values = list(
            db.scalars(
                select(MetricSample.value_numeric)
                .join(MetricDefinition)
                .where(MetricDefinition.collector_id == cid)
            )
        )
        receipts = db.scalar(
            select(func.count())
            .select_from(TelemetryReceipt)
            .where(TelemetryReceipt.agent_id == aid)
        )
        db_bytes = db.scalar(text("SELECT pg_database_size(current_database())"))
    expected = set(range(ordinal))
    persisted = set(values)
    missing = sorted(expected - persisted)
    assert not missing and len(values) == len(persisted) == ordinal
    ticks = os.sysconf("SC_CLK_TCK")
    levels.append(
        {
            "level": name,
            "duration_s": elapsed,
            "concurrent_readers": users,
            "concurrent_ingestion_producers": producers,
            "new_samples": len(inventory),
            "new_sample_rate_per_s": len(inventory) / elapsed,
            "resources_added": 30,
            "collectors_added": 30,
            "active_simulated_transports": 1 if producers else 0,
            "series_per_transport": 2 if producers == 2 else producers,
            "request_count": len(metrics),
            "errors": errors,
            "p50_ms": ordered[(len(ordered) - 1) // 2],
            "p95_ms": ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))],
            "p99_ms": ordered[min(len(ordered) - 1, int(len(ordered) * 0.99))],
            "sql_query_counts_by_path": {
                p: sorted(set(m["sql_queries"] for m in metrics if m["path"] == p))
                for p in sorted(set(m["path"] for m in metrics))
            },
            "request_metrics": metrics,
            "api_process_samples": samples,
            "api_cpu_seconds": (samples[-1]["cpu_ticks"] - samples[0]["cpu_ticks"])
            / ticks,
            "api_max_rss_bytes": max(s["rss_bytes"] for s in samples),
            "postgres_database_bytes": db_bytes,
            "cumulative_expected": ordinal,
            "cumulative_distinct": len(persisted),
            "physical_rows": len(values),
            "missing_ids": missing,
            "duplicates": len(values) - len(persisted),
            "cumulative_receipts": receipts,
        }
    )
with SessionLocal() as db:
    plan = db.execute(
        text(
            "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) SELECT DISTINCT ON(metric_definition_id) id FROM metric_samples WHERE collector_id=:id ORDER BY metric_definition_id,observed_at DESC"
        ),
        {"id": cid},
    ).scalar()
    total_resources = db.scalar(select(func.count()).select_from(DataSource))
    total_collectors = db.scalar(select(func.count()).select_from(Collector))
result = {
    "status": "PASS for bounded accounting, not global throughput acceptance",
    "levels": levels,
    "resources_total": total_resources,
    "collectors_total": total_collectors,
    "missing": 0,
    "duplicates": 0,
    "expected_ids": list(range(ordinal)),
    "persisted_ids": sorted(persisted),
    "latest_sample_plan": plan,
    "cpu_count": os.cpu_count(),
    "cgroup_cpu_max": Path("/sys/fs/cgroup/cpu.max").read_text().strip(),
    "cgroup_memory_max": Path("/sys/fs/cgroup/memory.max").read_text().strip(),
    "limitations": [
        "5-second API reader windows; finite producers can stop before window ends",
        "synthetic legacy-compatible OTLP auth; no qualified method/version/provider proof",
        "only API process CPU/RSS measured; not all container/browser processes",
        "one representative SQL plan; query counts include request auth/security queries",
        "not production scale or a defined SLO",
    ],
    "RM_DEF_036": "NOT REPRODUCED in tested boundary",
}
(out / "representative-load.json").write_text(json.dumps(result, indent=2))
print(
    "MULTILEVEL REAL OTLP: "
    + str(ordinal)
    + " expected/distinct/physical;0 missing/duplicate; SQL and process metrics retained"
)
