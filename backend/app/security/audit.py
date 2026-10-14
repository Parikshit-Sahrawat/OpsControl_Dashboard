"""Redacted, append-only security event emission.

Never pass request bodies, passwords, bearer tokens, secret references, or
untrusted query strings into this log. Designed for audit review, not general
application access logging.
"""
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.security.models import SecurityAuditEvent

def log_event(db: Session, *, event_type: str, outcome: str,
              actor_id=None, organization_id=None, target_type=None,
              target_id=None, request_id=None):
    if outcome not in {"SUCCESS", "DENIED", "FAILURE"}:
        raise ValueError("Invalid audit outcome")
    event = SecurityAuditEvent(
        event_type=event_type, outcome=outcome, actor_id=actor_id,
        organization_id=organization_id,
        target_type=target_type,
        target_id=str(target_id)[:120] if target_id is not None else None,
        request_id=str(request_id)[:100] if request_id else None,
        occurred_at=datetime.now(timezone.utc),
    )
    db.add(event)
    return event
