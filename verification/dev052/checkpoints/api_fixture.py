"""Test-only independent durable response ledger; actual app authorizes/stores.

No production import/route/config changes. Record IDs/status/hashes, never tokens.
"""

import gzip
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from google.protobuf.json_format import MessageToDict
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import (
    ExportLogsServiceRequest,
)
from app.main import app as original
from app.core.config import settings

assert (
    settings.environment == "test"
    and os.environ.get("OPSCONTROL_ARCH001_ACCEPTANCE") == "1"
)
LEDGER = Path(os.environ["ARCH001_PRIVATE_DIR"]) / "api-ledger.sqlite"
with sqlite3.connect(LEDGER) as db:
    db.execute(
        "CREATE TABLE IF NOT EXISTS attempts(sequence INTEGER PRIMARY KEY, request_sha TEXT, payload_sha TEXT, status INTEGER, event_ids TEXT)"
    )
os.chmod(LEDGER, 0o600)


async def app(scope, receive, send):
    if scope["type"] != "http" or not scope.get("path", "").endswith(
        "/agent/otlp/v1/logs"
    ):
        return await original(scope, receive, send)
    messages, raw = [], bytearray()
    while True:
        message = await receive()
        messages.append(message)
        raw.extend(message.get("body", b""))
        if len(raw) > 2 * 1024 * 1024:
            # Let the original app reject its bounded stream; never weaken limits.
            break
        if not message.get("more_body"):
            break
    position = 0

    async def replay_receive():
        nonlocal position
        if position < len(messages):
            message = messages[position]
            position += 1
            return message
        return await receive()

    response = []

    async def capture(message):
        response.append(message)

    await original(scope, replay_receive, capture)
    status = next(m["status"] for m in response if m["type"] == "http.response.start")
    ids = []
    payload_sha = None
    if status == 200:
        headers = dict(scope.get("headers", []))
        content = (
            gzip.decompress(raw)
            if headers.get(b"content-encoding") == b"gzip"
            else bytes(raw)
        )
        payload_sha = hashlib.sha256(content).hexdigest()
        if headers.get(b"content-type", b"").startswith(b"application/json"):
            document = json.loads(content)
        else:
            envelope = ExportLogsServiceRequest()
            envelope.ParseFromString(content)
            document = MessageToDict(envelope)
        for resource in document.get("resourceLogs", []):
            for scope_logs in resource.get("scopeLogs", []):
                for record in scope_logs.get("logRecords", []):
                    attrs = {
                        a["key"]: a["value"].get("stringValue")
                        for a in record.get("attributes", [])
                    }
                    event_id = attrs.get("event_id")
                    if not event_id:
                        try:
                            event_id = json.loads(
                                record.get("body", {}).get("stringValue", "{}")
                            ).get("event_id")
                        except (ValueError, AttributeError):
                            pass
                    if event_id:
                        ids.append(event_id)
    with sqlite3.connect(LEDGER, timeout=30) as db:
        db.execute("PRAGMA synchronous=FULL")
        db.execute(
            "INSERT INTO attempts(request_sha,payload_sha,status,event_ids) VALUES (?,?,?,?)",
            (hashlib.sha256(raw).hexdigest(), payload_sha, status, json.dumps(ids)),
        )
    for message in response:
        await send(message)
