"""Owned test-only causal ledger around the actual authenticated API transaction.

No success response is synthesized. Gates are durable files in the private lab.
No credentials or raw OTLP bodies are retained. PostgreSQL is independently read.
"""

import asyncio
import gzip
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time
import uuid
import collections

from google.protobuf.json_format import MessageToDict
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import (
    ExportLogsServiceRequest,
)
from sqlalchemy import select
from app.main import app as original
from app.core.config import settings
from app.db.session import SessionLocal
from app.telemetry.models import TelemetryReceipt
from app.models import LogEvent, LogSource

assert (
    settings.environment == "test"
    and os.environ.get("OPSCONTROL_ARCH001_ACCEPTANCE") == "1"
)
ROOT = Path(os.environ["ARCH001_PRIVATE_DIR"])
LEDGER = ROOT / "api-ledger.sqlite"
with sqlite3.connect(LEDGER) as db:
    db.execute(
        "CREATE TABLE IF NOT EXISTS timeline(sequence INTEGER PRIMARY KEY, time_ns INTEGER, stage TEXT, payload_sha TEXT, event_ids TEXT, status INTEGER, receipts TEXT)"
    )
os.chmod(LEDGER, 0o600)


def record(stage, sha, ids, status=None, receipts=None):
    with sqlite3.connect(LEDGER, timeout=30) as db:
        db.execute("PRAGMA synchronous=FULL")
        db.execute(
            "INSERT INTO timeline(time_ns,stage,payload_sha,event_ids,status,receipts) VALUES (?,?,?,?,?,?)",
            (time.time_ns(), stage, sha, json.dumps(ids), status, json.dumps(receipts)),
        )


def mode():
    try:
        return json.loads((ROOT / "api-mode.json").read_text())
    except FileNotFoundError:
        return {}


async def app(scope, receive, send):
    # Owned test control via a private file, not a new product API endpoint.
    if scope.get("path") == "/health" and (ROOT / "receipt-request.json").exists():
        request = json.loads((ROOT / "receipt-request.json").read_text())
        case = request["case"]
        assert case.replace("-", "").replace("_", "").replace(".", "").isalnum()
        with SessionLocal() as db:
            events = db.scalars(
                select(LogEvent)
                .join(LogSource)
                .where(LogSource.collector_id == uuid.UUID(request["collector_id"]))
            ).all()
            rows = []
            for event in events:
                eid = (event.attributes or {}).get("event_id")
                if not eid:
                    try:
                        eid = json.loads(event.message).get("event_id")
                    except (ValueError, AttributeError):
                        pass
                if eid in request["expected_ids"]:
                    rows.append(
                        {
                            "id": str(event.id),
                            "event_id": eid,
                            "created_at": event.created_at.isoformat(),
                        }
                    )
        data = {
            "scope": request["collector_id"],
            "source": "postgresql",
            "writer_stopped": request["writer_stopped"],
            "cut_ns": time.time_ns(),
            "counts_by_id": dict(collections.Counter(r["event_id"] for r in rows)),
            "rows": rows,
        }
        output = ROOT / case / request["label"]
        assert output.parent == ROOT / case and output.name.endswith(".json")
        temp = output.with_suffix(".tmp")
        with temp.open("w") as stream:
            os.chmod(temp, 0o600)
            json.dump(data, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, output)
        (ROOT / "receipt-request.json").unlink()
    if scope["type"] != "http" or not scope.get("path", "").endswith(
        "/agent/otlp/v1/logs"
    ):
        return await original(scope, receive, send)
    messages, raw = [], bytearray()
    while True:
        message = await receive()
        messages.append(message)
        raw.extend(message.get("body", b""))
        if len(raw) > 2 * 1024 * 1024 or not message.get("more_body"):
            break
    position = 0

    async def replay_receive():
        nonlocal position
        if position < len(messages):
            message = messages[position]
            position += 1
            return message
        return await receive()

    headers = dict(scope.get("headers", []))
    content = (
        gzip.decompress(raw)
        if headers.get(b"content-encoding") == b"gzip"
        else bytes(raw)
    )
    sha = hashlib.sha256(content).hexdigest()
    if headers.get(b"content-type", b"").startswith(b"application/json"):
        document = json.loads(content)
    else:
        envelope = ExportLogsServiceRequest()
        envelope.ParseFromString(content)
        document = MessageToDict(envelope)
    ids = []
    for resource in document.get("resourceLogs", []):
        for scope_logs in resource.get("scopeLogs", []):
            for row in scope_logs.get("logRecords", []):
                attrs = {
                    a["key"]: a["value"].get("stringValue")
                    for a in row.get("attributes", [])
                }
                event = attrs.get("event_id")
                if not event:
                    try:
                        event = json.loads(
                            row.get("body", {}).get("stringValue", "{}")
                        ).get("event_id")
                    except (ValueError, AttributeError):
                        pass
                if event:
                    ids.append(event)
    gate = mode()
    record("received", sha, ids)
    if gate.get("mode") in {"unavailable", "hold_before_commit", "permanent_rejection"}:
        if gate["mode"] == "hold_before_commit":
            record("held_before_commit", sha, ids)
            while mode().get("generation") == gate.get("generation"):
                await asyncio.sleep(0.02)
        status = 400 if gate["mode"] == "permanent_rejection" else 503
        await send({"type": "http.response.start", "status": status, "headers": []})
        await send({"type": "http.response.body", "body": b"Owned fault injection"})
        record("injected_rejection", sha, ids, status)
        return
    response = []

    async def capture(message):
        response.append(message)

    await original(scope, replay_receive, capture)
    status = next(m["status"] for m in response if m["type"] == "http.response.start")
    receipts = []
    if status == 200:
        # Separate SQLAlchemy connection/transaction after original request commits.
        with SessionLocal() as db:
            receipts = [
                {
                    "id": str(r.id),
                    "received_at": r.received_at.isoformat(),
                    "record_count": r.record_count,
                }
                for r in db.scalars(
                    select(TelemetryReceipt).where(TelemetryReceipt.payload_hash == sha)
                ).all()
            ]
        assert receipts, "API returned success without an independently visible receipt"
    record(
        "api_committed" if status == 200 else "api_rejected", sha, ids, status, receipts
    )
    if gate.get("mode") == "hold_after_commit":
        record("held_after_commit", sha, ids, status, receipts)
        while mode().get("generation") == gate.get("generation"):
            await asyncio.sleep(0.02)
    for message in response:
        await send(message)
    # Server send completion is explicitly NOT proof of client acknowledgement.
    record("server_response_sent", sha, ids, status)


# Test-only syscall observer for exact pre-enqueue/pre-checkpoint barriers. These
# installed host tools are copied into this lab's private mount, never an image.
# No ptrace capability or seccomp exception is granted; only an owned child.
import shutil

TOOLS = [
    "/usr/bin/strace",
    "/lib/x86_64-linux-gnu/libunwind-ptrace.so.0",
    "/lib/x86_64-linux-gnu/libunwind-x86_64.so.8",
    "/lib/x86_64-linux-gnu/libc.so.6",
    "/lib/x86_64-linux-gnu/liblzma.so.5",
    "/lib/x86_64-linux-gnu/libunwind.so.8",
    "/lib64/ld-linux-x86-64.so.2",
]
(ROOT / "tools").mkdir(exist_ok=True, mode=0o700)
tool_inventory = []
for source in TOOLS:
    target = ROOT / "tools" / Path(source).name
    shutil.copyfile(source, target)
    os.chmod(target, 0o700)
    tool_inventory.append(
        {"host_path": source, "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}
    )
(ROOT / "tools.json").write_text(json.dumps(tool_inventory, indent=2))
