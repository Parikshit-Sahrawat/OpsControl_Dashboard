"""Atomic PostgreSQL-backed login throttling shared by every API replica.

Rules: 10 failed password attempts per normalized username / 15 minutes,
30 per direct client IP / 15 minutes. Never trust X-Forwarded-For unless a
separate explicitly configured trusted-proxy middleware validates it.
"""
from datetime import datetime, timedelta, timezone
import hashlib
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from app.security.models import AuthThrottleBucket

WINDOW = timedelta(minutes=15)
MAX_USERNAME_FAILURES = 10
MAX_IP_FAILURES = 30

def _key(kind: str, value: str) -> str:
    return hashlib.sha256((kind + ":" + value).encode("utf-8")).hexdigest()

def _lock(db: Session, key: str) -> None:
    # Prevent concurrent first-attempt races across workers; this is
    # transaction-scoped and uses only the hash, not a username/IP plaintext.
    unsigned = int(key[:16], 16)
    signed = unsigned if unsigned < 2**63 else unsigned - 2**64
    db.execute(text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": signed})

def _bucket(db: Session, key: str, now: datetime) -> AuthThrottleBucket:
    _lock(db, key)
    item = db.get(AuthThrottleBucket, key)
    if item is None:
        item = AuthThrottleBucket(key_hash=key, window_started_at=now, attempts=0)
        db.add(item)
        db.flush()
    elif now - item.window_started_at >= WINDOW:
        item.window_started_at = now
        item.attempts = 0
    return item

def login_allowed(db: Session, username: str, remote_ip: str) -> bool:
    now = datetime.now(timezone.utc)
    for key, limit in ((_key("user", username), MAX_USERNAME_FAILURES),
                       (_key("ip", remote_ip), MAX_IP_FAILURES)):
        item = _bucket(db, key, now)
        if item.attempts >= limit:
            return False
    return True

def failed_login(db: Session, username: str, remote_ip: str) -> None:
    now = datetime.now(timezone.utc)
    for key in (_key("user", username), _key("ip", remote_ip)):
        _bucket(db, key, now).attempts += 1
    db.flush()

def successful_login(db: Session, username: str) -> None:
    now = datetime.now(timezone.utc)
    _bucket(db, _key("user", username), now).attempts = 0
