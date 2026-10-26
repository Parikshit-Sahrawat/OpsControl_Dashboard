"""Independent per-case PostgreSQL reconciliation; missing IDs remain FAIL."""

import collections
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tarfile
import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from app.main import app
from app.db.session import SessionLocal
from app.models import LogEvent, LogSource
from app.telemetry.models import TelemetryReceipt

assert (
    os.environ["ENVIRONMENT"] == "test"
    and os.environ["OPSCONTROL_ARCH001_ACCEPTANCE"] == "1"
)
root = Path(os.environ["ARCH001_PRIVATE_DIR"])
out = Path(os.environ["ARCH001_EVIDENCE_DIR"])
report = json.loads((root / "e2e.json").read_text())
with sqlite3.connect(root / "api-ledger.sqlite") as db:
    db.row_factory = sqlite3.Row
    timeline = [dict(r) for r in db.execute("SELECT * FROM timeline ORDER BY sequence")]
for row in timeline:
    row["event_ids"] = json.loads(row["event_ids"])
    row["receipts"] = json.loads(row["receipts"])
with SessionLocal() as db:
    events = db.scalars(
        select(LogEvent)
        .join(LogSource)
        .where(LogSource.collector_id == uuid.UUID(report["collector_id"]))
    ).all()
    receipts = db.scalars(
        select(TelemetryReceipt).where(
            TelemetryReceipt.agent_id == uuid.UUID(report["agent_id"]),
            TelemetryReceipt.signal == "logs",
        )
    ).all()
    rows = []
    for event in events:
        eid = (event.attributes or {}).get("event_id")
        if not eid:
            try:
                eid = json.loads(event.message).get("event_id")
            except (ValueError, AttributeError):
                pass
        if eid:
            rows.append(
                {
                    "row_id": str(event.id),
                    "event_id": eid,
                    "created_at": event.created_at.isoformat(),
                    "observed_at": event.observed_at.isoformat(),
                    "method_id": (event.attributes or {}).get("opscontrol.method.id"),
                }
            )
    receipts = [
        {
            "id": str(r.id),
            "payload_sha256": r.payload_hash,
            "record_count": r.record_count,
            "received_at": r.received_at.isoformat(),
        }
        for r in receipts
    ]
counts = collections.Counter(r["event_id"] for r in rows)
accepted = collections.Counter(
    e for r in timeline if r["stage"] == "api_committed" for e in r["event_ids"]
)
ledger_hashes = {r["payload_sha"] for r in timeline if r["stage"] == "api_committed"}
receipt_hashes = {r["payload_sha256"] for r in receipts}
assert (
    ledger_hashes == receipt_hashes
), "Independent API and PostgreSQL receipt hashes differ"
result = []
for c in report["cases"]:
    expected = set(c["expected_ids"])
    missing = sorted(expected - set(counts))
    physical = sum(counts[e] for e in expected)
    attempts = sum(accepted[e] for e in expected)
    result.append(
        {
            "name": c["name"],
            "status": "FAIL" if missing or c["status"] != "PASS" else "PASS",
            "expected_ids": sorted(expected),
            "expected_distinct": len(expected),
            "persisted_distinct": len(expected & set(counts)),
            "missing_ids": missing,
            "api_accepted_attempts": attempts,
            "api_duplicate_attempts": attempts - len(expected & set(accepted)),
            "physical_rows": physical,
            "physical_duplicate_rows": physical - len(expected & set(counts)),
            "db_counts_by_id": {e: counts[e] for e in sorted(expected)},
            "api_counts_by_id": {e: accepted[e] for e in sorted(expected)},
            "controller_status": c["status"],
            "error": c.get("error"),
        }
    )
expected_all = {e for c in report["cases"] for e in c["expected_ids"]}
assert not set(counts) - expected_all, "Unexpected IDs"
assert all(
    accepted[e] >= counts[e] for e in counts
), "Physical rows exceed independently observed accepted attempts"
assert all(r["method_id"] == report["method_id"] for r in rows)
for name, data in [
    ("reconciliation.json", result),
    ("api-timeline.json", timeline),
    ("db-events.json", rows),
    ("db-receipts.json", receipts),
]:
    (out / name).write_text(json.dumps(data, indent=2) + "\n")
# Reconstruct every native/replay cut from independently queried final PG rows.
# A later successful replay must never erase the earlier missing-ID evidence.
phases = []
for c in report["cases"]:
    expected = set(c["expected_ids"])
    for phase in c.get("phases", []):
        snapshot = json.loads((root / c["name"] / phase["label"]).read_text())
        historical = []
        for row in rows:
            at = datetime.fromisoformat(row["created_at"])
            if at.tzinfo is None:
                at = at.replace(tzinfo=timezone.utc)
            if row["event_id"] in expected and int(at.timestamp() * 10**9) <= snapshot["cut_ns"]:
                historical.append(row)
        assert {r["row_id"] for r in historical} == {r["id"] for r in snapshot["rows"]}, "PG phase snapshot differs from persisted row/time reconstruction"
        counts_at_cut = collections.Counter(r["event_id"] for r in historical)
        missing = sorted(expected - set(counts_at_cut))
        assert missing == phase["missing_ids"]
        phases.append({"case": c["name"], **phase,
                       "independent_pg_row_time_reconstruction": "PASS",
                       "delivery_status": "FAIL" if missing else "PASS"})
(out / "phase-reconciliation.json").write_text(json.dumps(phases, indent=2) + "\n")
if (root / "tools.json").exists():
    (out / "tools.json").write_bytes((root / "tools.json").read_bytes())
# Only synthetic input/config/checkpoint files; token is an env reference in YAML.
secrets = [
    json.loads((root / "fixture.json").read_text())["password"],
    json.loads((root / "identity.json").read_text())["access_token"],
]
files = [
    f for c in report["cases"] for f in (root / c["name"]).rglob("*") if f.is_file()
]
manifest = []
with tarfile.open(out / "synthetic-state.tar.gz", "w:gz") as archive:
    for f in files:
        data = f.read_bytes()
        assert not any(s.encode() in data for s in secrets)
        manifest.append(
            {
                "path": str(f.relative_to(root)),
                "bytes": len(data),
                "mode": oct(f.stat().st_mode & 0o777),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
        archive.add(f, arcname=str(f.relative_to(root)), recursive=False)
(out / "state-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(
    json.dumps(
        {
            "independent_reconciliation": "COMPLETE",
            "counts": dict(collections.Counter(c["status"] for c in result)),
            "receipt_hashes_match": True,
        }
    )
)
