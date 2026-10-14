"""Bounded PostgreSQL maintenance; evidence linked to investigations is pinned.

Audit, runs, incidents and ETL histories are deliberately retained until an
approved archive/deletion policy exists. Never disable their integrity triggers.
Each batch is atomic; separate maintenance scheduling also covers remote workers.
"""
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.orm import Session

_RAW_EVIDENCE = {
    "metric_samples": ("metric_definitions", "metric_definition_id"),
    "log_events": ("log_sources", "log_source_id"),
}

def prune_batch(db: Session, *, now: datetime | None = None, batch_size: int = 1000) -> dict[str, int]:
    if type(batch_size) is not int or not 1 <= batch_size <= 10000:
        raise ValueError("batch_size must be 1..10000")
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("An aware UTC cutoff is required")
    counts = {}
    # Names are internal constants, never user-supplied SQL identifiers.
    for table, (parent, key) in _RAW_EVIDENCE.items():
        statement = text(f"""
            WITH expired AS (
                SELECT e.id FROM {table} e JOIN {parent} p ON p.id = e.{key}
                WHERE e.observed_at < :now - make_interval(days => greatest(p.retention_days, 1))
                  AND NOT EXISTS (SELECT 1 FROM correlation_evidence c WHERE c.source_id = e.id)
                ORDER BY e.observed_at, e.id LIMIT :limit FOR UPDATE OF e SKIP LOCKED
            ) DELETE FROM {table} WHERE id IN (SELECT id FROM expired)
        """)
        counts[table] = db.execute(statement, {"now": now, "limit": batch_size}).rowcount
    for table, condition in (
        ("access_sessions", "expires_at < :now"),
        ("auth_throttle_buckets", "window_started_at < :now - interval '1 day'"),
    ):
        key = "key_hash" if table == "auth_throttle_buckets" else "id"
        counts[table] = db.execute(text(f"""
            WITH expired AS (SELECT {key} FROM {table} WHERE {condition}
                ORDER BY {key} LIMIT :limit FOR UPDATE SKIP LOCKED)
            DELETE FROM {table} WHERE {key} IN (SELECT {key} FROM expired)
        """), {"now": now, "limit": batch_size}).rowcount
    return counts
