"""Independent PostgreSQL/SQLite reconciliation; no exactly-once inference."""

import collections
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tarfile
import uuid
from sqlalchemy import select
from app.main import app
from app.db.session import SessionLocal
from app.models import LogEvent, LogSource
from app.telemetry.models import TelemetryReceipt

assert (
    os.environ["ENVIRONMENT"] == "test"
    and os.environ["OPSCONTROL_ARCH001_ACCEPTANCE"] == "1"
)
private = Path(os.environ["ARCH001_PRIVATE_DIR"])
out = Path(os.environ["ARCH001_EVIDENCE_DIR"])
result = json.loads((private / "e2e.json").read_text())
assert result.get("recovery_completed") is True
expected = set(result["expected_ids"])
with sqlite3.connect(private / "api-ledger.sqlite") as db:
    attempts = [
        {
            "sequence": row[0],
            "request_sha256": row[1],
            "payload_sha256": row[2],
            "status": row[3],
            "event_ids": json.loads(row[4]),
        }
        for row in db.execute(
            "SELECT sequence,request_sha,payload_sha,status,event_ids FROM attempts ORDER BY sequence"
        )
    ]
accepted = collections.Counter(
    event for row in attempts if row["status"] == 200 for event in row["event_ids"]
)
with SessionLocal() as db:
    events = db.scalars(
        select(LogEvent)
        .join(LogSource)
        .where(LogSource.collector_id == uuid.UUID(result["collector_id"]))
    ).all()
    receipts = db.scalars(
        select(TelemetryReceipt).where(
            TelemetryReceipt.agent_id == uuid.UUID(result["agent_id"]),
            TelemetryReceipt.signal == "logs",
        )
    ).all()
    counts = collections.Counter()
    control_records = 0
    rows = []
    for event in events:
        event_id = (event.attributes or {}).get("event_id")
        if not event_id:
            try:
                event_id = json.loads(event.message).get("event_id")
            except (ValueError, AttributeError):
                pass
        if event_id:
            counts[event_id] += 1
            rows.append(
                {
                    "row_id": str(event.id),
                    "event_id": event_id,
                    "observed_at": event.observed_at.isoformat(),
                    "created_at": event.created_at.isoformat(),
                    "method_id": (event.attributes or {}).get("opscontrol.method.id"),
                }
            )
        else:
            control_records += 1
    receipt_rows = [
        {
            "id": str(row.id),
            "payload_sha256": row.payload_hash,
            "record_count": row.record_count,
            "received_at": row.received_at.isoformat(),
        }
        for row in receipts
    ]
missing, unexpected = sorted(expected - set(counts)), sorted(set(counts) - expected)
assert not missing and not unexpected, (missing, unexpected)
assert set(counts) == expected == set(accepted)
assert all(accepted[event] >= counts[event] for event in expected)
assert {r["payload_sha256"] for r in receipt_rows} == {
    r["payload_sha256"] for r in attempts if r["status"] == 200
}
assert all(row["method_id"] == result["method_id"] for row in rows)
report = {
    "status": "PASS",
    "scope": "finite synthetic ID set; no general exactly-once claim",
    "expected_distinct_ids": len(expected),
    "persisted_distinct_ids": len(counts),
    "lost_ids": missing,
    "unexpected_ids": unexpected,
    "api_accepted_record_attempts": sum(accepted.values()),
    "api_duplicate_record_attempts": sum(accepted.values()) - len(expected),
    "db_source_event_rows": sum(counts.values()),
    "db_duplicate_event_rows": sum(counts.values()) - len(expected),
    "api_counts_by_id": dict(sorted(accepted.items())),
    "db_counts_by_id": dict(sorted(counts.items())),
    "db_control_marker_rows": control_records,
    "db_batch_receipts": len(receipt_rows),
    "all_receipt_payload_hashes_reconciled": True,
    "repeated_restarts_checked": True,
}
for name, value in [
    ("event-accounting.json", report),
    ("api-receipts.json", attempts),
    ("db-receipts.json", receipt_rows),
    ("db-events.json", rows),
]:
    (out / name).write_text(json.dumps(value, indent=2) + "\n")
shutil.copy2(private / "checkpoint-home/otel.yaml", out / "generated.yaml")
# Preserve only synthetic state/log evidence, never identity/TLS/credential files.
secrets = [
    json.loads((private / "fixture.json").read_text())["password"],
    json.loads((private / "checkpoint-home/identity.json").read_text())["access_token"],
]
roots = [
    private / "vault",
    private / "checkpoint-home/otel-checkpoints",
    private / "logs",
    private / "retention",
]
inventory = []
for root in roots:
    for file in root.rglob("*"):
        if file.is_file():
            data = file.read_bytes()
            assert not any(
                secret.encode() in data for secret in secrets
            ), "Credential found; refusing opaque evidence export"
            inventory.append(
                {
                    "path": str(file.relative_to(private)),
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "size": len(data),
                    "mode": oct(file.stat().st_mode & 0o777),
                }
            )
archive = out / "synthetic-checkpoint-evidence.tar.gz"
with tarfile.open(archive, "w:gz") as tar:
    for root in roots:
        tar.add(root, arcname=str(root.relative_to(private)))
os.chmod(archive, 0o600)
(out / "state-hashes.json").write_text(
    json.dumps(
        {
            "files": inventory,
            "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        },
        indent=2,
    )
    + "\n"
)
print(json.dumps(report))
