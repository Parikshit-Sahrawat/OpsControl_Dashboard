"""Alert notification delivery adapters.

Customer destination configuration uses approved external secret references. Delivery uses short fenced leases; provider IO
never owns the claim transaction.
"""

import json
import os
import re
import uuid
import smtplib
import ssl
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, HTTPRedirectHandler, HTTPSHandler, build_opener

from sqlalchemy import select, func, text

from app.db.session import SessionLocal
from app.models import AlertNotificationDelivery, AlertState


def _env(name: str, required: bool = True) -> str | None:
    value = os.getenv(name)
    if required and not value:
        raise RuntimeError(f"Missing required notification setting: {name}")
    return value


def _post_json(url: str, payload: dict, headers: dict | None = None, timeout: int = 15):
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    with _notification_open(request, timeout=timeout) as response:
        raw = response.read(4096)
        return response.status, raw.decode("utf-8", errors="replace")


def _email_message_id(delivery: AlertNotificationDelivery) -> str:
    return f"<opscontrol-{delivery.id}@opscontrol.local>"


def send_email(delivery: AlertNotificationDelivery, state: AlertState) -> str:
    host = _env("OPSCONTROL_SMTP_HOST")
    port = int(os.getenv("OPSCONTROL_SMTP_PORT", "587"))
    username = os.getenv("OPSCONTROL_SMTP_USERNAME")
    password = os.getenv("OPSCONTROL_SMTP_PASSWORD")
    sender = _env("OPSCONTROL_ALERT_EMAIL_FROM")
    recipients = [
        x.strip() for x in _env("OPSCONTROL_ALERT_EMAIL_TO").split(",") if x.strip()
    ]
    if not recipients:
        raise RuntimeError("OPSCONTROL_ALERT_EMAIL_TO contains no recipients")

    message = EmailMessage()
    prefix = "RESOLVED" if delivery.event_type == "RESOLVED" else state.severity
    message["Subject"] = f"[OpsControl] [{prefix}] {state.message[:160]}"
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    message["Message-ID"] = _email_message_id(delivery)
    message["X-OpsControl-Delivery-ID"] = str(delivery.id)
    message["X-OpsControl-Alert-State-ID"] = str(state.id)
    message["X-OpsControl-Event"] = delivery.event_type
    message.set_content(
        "OpsControl alert notification\n\n"
        f"State: {state.status}\n"
        f"Severity: {state.severity}\n"
        f"Alert State: {state.id}\n"
        f"Rule: {state.alert_rule_id}\n"
        f"Metric: {state.metric_definition_id}\n"
        f"Value: {state.last_value}\n"
        f"Breach count: {state.breach_count}\n"
        f"Message: {state.message}\n"
        f"OpsControl Delivery ID: {delivery.id}\n"
    )

    context = ssl.create_default_context()
    with smtplib.SMTP(host, port, timeout=15) as smtp:
        smtp.starttls(context=context)
        if username:
            smtp.login(username, password or "")
        smtp.send_message(message)
    return f"email:{delivery.id}"


def deliver(delivery, state):
    if delivery.channel.startswith("DEST:"):
        from app.telemetry.delivery import send_destination

        return send_destination(delivery, state)
    if delivery.channel == "EMAIL":
        return send_email(delivery, state)
    if delivery.channel == "IN_APP":
        from app.telemetry.inbox import persist
        return persist(delivery, state)
    raise RuntimeError("Unsupported or retired notification channel")


MAX_ATTEMPTS = 5
LEASE_SECONDS = 120


def _claim_notification():
    """One short SKIP LOCKED claim; detach snapshots before provider IO."""
    from sqlalchemy.orm import aliased

    opened = aliased(AlertNotificationDelivery)
    active = aliased(AlertNotificationDelivery)
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        exhausted = db.scalars(
            select(AlertNotificationDelivery)
            .where(
                AlertNotificationDelivery.status == "PROCESSING",
                (AlertNotificationDelivery.channel.in_(["EMAIL","IN_APP"]) | AlertNotificationDelivery.channel.startswith("DEST:")),
                AlertNotificationDelivery.lease_expires_at <= now,
                AlertNotificationDelivery.attempts >= MAX_ATTEMPTS,
            )
            .with_for_update(skip_locked=True)
            .limit(20)
        ).all()
        for row in exhausted:
            row.status = "FAILED"
            row.last_error = "Delivery retry limit reached"
            row.lease_token = None
            row.lease_expires_at = None
        ready = (
            (AlertNotificationDelivery.status == "PENDING")
            | (
                (AlertNotificationDelivery.status == "FAILED")
                & (
                    AlertNotificationDelivery.updated_at
                    + func.make_interval(
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        func.least(
                            3600, func.power(2, AlertNotificationDelivery.attempts) * 15
                        ),
                    )
                    <= now
                )
            )
            | (
                (AlertNotificationDelivery.status == "PROCESSING")
                & (AlertNotificationDelivery.lease_expires_at <= now)
            )
        )
        prerequisite = (
            select(opened.id)
            .where(
                opened.alert_state_id == AlertNotificationDelivery.alert_state_id,
                opened.channel == AlertNotificationDelivery.channel,
                opened.event_type == "OPENED",
                opened.status == "SENT",
                opened.external_reference.is_not(None),
            )
            .exists()
        )
        inflight = (
            select(active.id)
            .where(
                active.alert_state_id == AlertNotificationDelivery.alert_state_id,
                active.channel == AlertNotificationDelivery.channel,
                active.id != AlertNotificationDelivery.id,
                active.status == "PROCESSING",
                active.lease_expires_at > now,
            )
            .exists()
        )
        throttle = max(
            0, min(300, int(os.getenv("OPSCONTROL_NOTIFICATION_THROTTLE_SECONDS", "1")))
        )
        channel_busy = (
            select(active.id)
            .where(
                active.channel == AlertNotificationDelivery.channel,
                active.id != AlertNotificationDelivery.id,
                active.status == "PROCESSING",
                active.lease_expires_at > now,
            )
            .exists()
        )
        channel_recent = (
            select(opened.id)
            .where(
                opened.channel == AlertNotificationDelivery.channel,
                opened.status == "SENT",
                opened.updated_at > now - timedelta(seconds=throttle),
            )
            .exists()
        )
        supported = AlertNotificationDelivery.channel.in_(
            ["EMAIL", "IN_APP"]
        ) | AlertNotificationDelivery.channel.startswith("DEST:")
        delivery = db.scalar(
            select(AlertNotificationDelivery)
            .where(
                ready,
                supported,
                ~channel_busy,
                ~channel_recent,
                AlertNotificationDelivery.attempts < MAX_ATTEMPTS,
                ~inflight,
                (AlertNotificationDelivery.event_type != "RESOLVED") | prerequisite,
            )
            .order_by(
                AlertNotificationDelivery.created_at, AlertNotificationDelivery.id
            )
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if delivery is None:
            db.commit()
            return None
        # Serialize destination claims across replicas, then recheck committed
        # leases. Provider IO remains outside this short transaction.
        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:channel,0))"),
            {"channel": delivery.channel},
        )
        if db.scalar(
            select(AlertNotificationDelivery.id)
            .where(
                AlertNotificationDelivery.channel == delivery.channel,
                AlertNotificationDelivery.id != delivery.id,
                AlertNotificationDelivery.status == "PROCESSING",
                AlertNotificationDelivery.lease_expires_at > now,
            )
            .limit(1)
        ):
            db.commit()
            return None
        # Serialize claims for an alert, including legacy duplicate event rows.
        state = db.scalar(
            select(AlertState)
            .where(AlertState.id == delivery.alert_state_id)
            .with_for_update()
        )
        if state is None:
            delivery.status = "FAILED"
            delivery.attempts += 1
            delivery.last_error = "Alert state unavailable"
            db.commit()
            return None
        current = db.scalar(
            select(AlertNotificationDelivery.id)
            .where(
                AlertNotificationDelivery.alert_state_id == state.id,
                AlertNotificationDelivery.channel == delivery.channel,
                AlertNotificationDelivery.id != delivery.id,
                AlertNotificationDelivery.status == "PROCESSING",
                AlertNotificationDelivery.lease_expires_at > now,
            )
            .limit(1)
        )
        if current:
            db.commit()
            return None
        previous = db.scalar(
            select(AlertNotificationDelivery)
            .where(
                AlertNotificationDelivery.alert_state_id == state.id,
                AlertNotificationDelivery.channel == delivery.channel,
                AlertNotificationDelivery.event_type == delivery.event_type,
                AlertNotificationDelivery.status == "SENT",
            )
            .order_by(AlertNotificationDelivery.created_at)
            .limit(1)
        )
        if previous:
            delivery.status = "SENT"
            delivery.external_reference = previous.external_reference
            delivery.sent_at = now
            delivery.last_error = None
            db.commit()
            return None
        token = uuid.uuid4()
        delivery.status = "PROCESSING"
        delivery.attempts += 1
        delivery.lease_token = token
        delivery.lease_expires_at = now + timedelta(seconds=LEASE_SECONDS)
        delivery.updated_at = now
        db.flush()
        db.expunge(delivery)
        db.expunge(state)
        db.commit()
        return delivery, state, token


def _finish_notification(delivery_id, token, reference=None, error=None):
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        delivery = db.scalar(
            select(AlertNotificationDelivery)
            .where(
                AlertNotificationDelivery.id == delivery_id,
                AlertNotificationDelivery.lease_token == token,
                AlertNotificationDelivery.status == "PROCESSING",
                AlertNotificationDelivery.lease_expires_at > now,
            )
            .with_for_update()
        )
        if delivery is None:
            return False  # expired/reclaimed completion is fenced
        delivery.lease_token = None
        delivery.lease_expires_at = None
        delivery.updated_at = now
        if error:
            delivery.status = "FAILED"
            delivery.last_error = error
        else:
            delivery.status = "SENT"
            delivery.external_reference = reference
            delivery.sent_at = now
            delivery.last_error = None
            state = db.scalar(
                select(AlertState)
                .where(AlertState.id == delivery.alert_state_id)
                .with_for_update()
            )
            if state:
                refs = dict(state.external_references or {})
                refs[delivery.channel] = reference
                state.external_references = refs
        db.commit()
        return True


def _safe_delivery_error(error):
    # A provider can echo credentials/URLs/body contents in its errors. Keep a
    # bounded classification, never str(error) or response bodies in evidence.
    if isinstance(error, HTTPError):
        return f"Notification provider HTTP {error.code}"
    if isinstance(error, ssl.SSLError):
        return "Notification TLS verification failed"
    if isinstance(error, (URLError, TimeoutError, OSError)):
        return "Notification transport unavailable"
    return "Notification configuration or provider response rejected"


def dispatch_pending_notifications():
    from app.telemetry.delivery import queue_escalations

    queue_escalations()
    counts = {"claimed": 0, "sent": 0, "failed": 0, "fenced": 0}
    for _ in range(20):
        claim = _claim_notification()
        if claim is None:
            break
        delivery, state, token = claim
        counts["claimed"] += 1
        try:
            reference = deliver(delivery, state)
            if not isinstance(reference, str) or not reference or len(reference) > 500:
                raise RuntimeError("Invalid notification reference")
            completed = _finish_notification(delivery.id, token, reference=reference)
            counts["sent" if completed else "fenced"] += 1
        except Exception as error:
            completed = _finish_notification(
                delivery.id, token, error=_safe_delivery_error(error)
            )
            counts["failed" if completed else "fenced"] += 1
    return counts
