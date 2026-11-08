"""Task-owned real OTLP/HTTP + authenticated reads; never a throughput certificate."""

import app.main  # noqa: F401
import json
import os
import secrets
import time
import uuid
import subprocess
from pathlib import Path
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from sqlalchemy import select, func, text
from app.db.session import SessionLocal
from app.models import DataSource, Collector, MetricSample, MetricDefinition
from app.telemetry.models import ManagedAgent, TelemetryReceipt
from app.security.models import WorkerIdentity
from app.security.http import token_digest

assert os.environ.get("OPSCONTROL_V16_ACCEPTANCE") == "1"
base = os.environ["V16_API_URL"]
out = Path(os.environ["V16_EVIDENCE_DIR"])
f = json.loads(
    (Path(os.environ["V16_PRIVATE_DIR"]) / "browser-fixture.json").read_text()
)
secret = secrets.token_urlsafe(32)
with SessionLocal() as db:
    s = DataSource(
        organization_id=uuid.UUID(f["organization_id"]),
        name="OTLP load " + uuid.uuid4().hex,
        source_type="LINUX",
        enabled=True,
    )
    db.add(s)
    db.flush()
    c = Collector(
        data_source_id=s.id,
        name="Synthetic authenticated OTLP",
        collector_type="OTEL",
        enabled=True,
    )
    w = WorkerIdentity(
        organization_id=s.organization_id,
        name=uuid.uuid4().hex,
        token_hash=token_digest(secret),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db.add_all([c, w])
    db.flush()
    a = ManagedAgent(
        organization_id=s.organization_id,
        collector_id=c.id,
        worker_id=w.id,
        hostname="controlled.invalid",
        version="SYNTHETIC",
        runtime_version="0.123.0",
    )
    db.add(a)
    db.commit()
    cid = c.id
    agentid = a.id


def call(path, token, body=None):
    headers = {
        "Authorization": "Bearer " + token,
        "X-OpsControl-Customers": f["organization_id"],
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    with urlopen(
        Request(
            base + "/api/v1/" + path,
            headers=headers,
            data=json.dumps(body).encode() if body is not None else None,
        ),
        timeout=20,
    ) as r:
        return r.status, json.load(r)


_, login = call(
    "auth/login", "unused", {"username": "v16-api-admin", "password": f["password"]}
)
token = login["access_token"]
paths = [
    "infrastructure/resources?limit=25",
    "resource-management/data-sources?paginated=true&limit=25",
    "unified/resources?limit=25",
]


def reads(count):
    timings = []
    for i in range(count):
        start = time.perf_counter()
        status, _ = call(paths[i % len(paths)], token)
        timings.append((time.perf_counter() - start) * 1000)
        assert status == 200
    ordered = sorted(timings)
    return {
        "requests": count,
        "errors": 0,
        "p50_ms": ordered[(count - 1) // 2],
        "p95_ms": ordered[min(count - 1, int(count * 0.95))],
        "p99_ms": ordered[-1],
        "latencies_ms": timings,
    }


base_time = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(seconds=5)
payloads = []
for batch in range(20):
    points = [
        {
            "timeUnixNano": str(
                int(
                    (base_time + timedelta(milliseconds=batch * 10 + i)).timestamp()
                    * 1000
                )
                * 1000000
            ),
            "asDouble": batch * 10 + i,
        }
        for i in range(10)
    ]
    payloads.append(
        {
            "resourceMetrics": [
                {
                    "scopeMetrics": [
                        {
                            "metrics": [
                                {
                                    "name": "sprint.real.otlp",
                                    "unit": "1",
                                    "gauge": {"dataPoints": points},
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    )
before = reads(12)


def ingest():
    for payload in payloads:
        status, _ = call("agent/otlp/v1/metrics", secret, payload)
        assert status == 200
        time.sleep(0.03)


with ThreadPoolExecutor(max_workers=2) as pool:
    ingestion = pool.submit(ingest)
    reading = pool.submit(reads, 30)
    if os.environ.get("V16_UI_URL"):
        subprocess.run(
            [
                "node",
                str(
                    Path(__file__).resolve().parents[2]
                    / "frontend/scripts/sprint1_load_navigation.mjs"
                ),
            ],
            check=True,
            timeout=60,
        )
    during = reading.result()
    ingestion.result()
call("agent/otlp/v1/metrics", secret, payloads[0])  # deliberate transport replay
try:
    call("agent/otlp/v1/metrics", "invalid-synthetic-token", payloads[0])
    raise AssertionError("invalid token accepted")
except HTTPError as e:
    assert e.code == 401
recovery = reads(12)
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
        .where(TelemetryReceipt.agent_id == agentid)
    )
    plan = db.execute(
        text(
            "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) SELECT DISTINCT ON(metric_definition_id) id FROM metric_samples WHERE collector_id=:id ORDER BY metric_definition_id, observed_at DESC"
        ),
        {"id": cid},
    ).scalar()
assert len(values) == 200 and set(values) == set(range(200)) and receipts == 20
result = {
    "scope": "20 actual authenticated legacy-compatible OTLP JSON batches x10 samples; one replay and one invalid-token negative; 3 API paths; synthetic agent identity, not qualified provider/method generation",
    "baseline_no_ingestion": before,
    "concurrent_ingestion": during,
    "after_ingestion": recovery,
    "payload_attempts": 22,
    "accepted_http_responses": 21,
    "expected_rejection_401": 1,
    "distinct_batch_receipts": receipts,
    "expected_source_ids": list(range(200)),
    "persisted_source_ids": sorted(values),
    "persisted_distinct": len(set(values)),
    "physical_rows": len(values),
    "missing": 0,
    "duplicates": 0,
    "sample_latest_query_plan": plan,
    "sql_queries_per_api_request": "NOT MEASURED; representative query EXPLAIN only",
    "global_RM_DEF_036": "NOT REPRODUCED at this bounded load; not full-system certification",
}
(out / "otlp-performance.json").write_text(json.dumps(result, indent=2))
print("Actual OTLP performance probe PASS:200/200 IDs;20 receipts; replay deduplicated")
