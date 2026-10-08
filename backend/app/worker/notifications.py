"""Alert notification delivery adapters.

Configuration is environment-backed for the initial implementation. Production
can replace these functions with a managed secret provider without changing
alert evaluation or delivery persistence.
"""

import json
import os
import smtplib
import ssl
from datetime import datetime, timezone
from email.message import EmailMessage
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import AlertNotificationDelivery, AlertState


MAX_ERROR_LENGTH = 2000


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
    with urlopen(request, timeout=timeout) as response:
        raw = response.read(4096)
        return response.status, raw.decode("utf-8", errors="replace")


def _severity_for_pagerduty(severity: str) -> str:
    return {
        "INFO": "info",
        "WARNING": "warning",
        "CRITICAL": "critical",
    }.get(str(severity).upper(), "warning")


def send_pagerduty(delivery: AlertNotificationDelivery, state: AlertState) -> str:
    routing_key = _env("OPSCONTROL_PAGERDUTY_ROUTING_KEY")
    event_action = "trigger" if delivery.event_type == "OPENED" else "resolve"
    payload = delivery.payload or {}
    request_payload = {
        "routing_key": routing_key,
        "event_action": event_action,
        "dedup_key": f"opscontrol:{state.id}",
    }
    if event_action == "trigger":
        request_payload["payload"] = {
            "summary": payload.get("message", state.message)[:1024],
            "source": f"opscontrol:metric:{state.metric_definition_id}",
            "severity": _severity_for_pagerduty(state.severity),
            "timestamp": state.last_evaluated_at.isoformat(),
            "custom_details": {
                "alert_state_id": str(state.id),
                "alert_rule_id": str(state.alert_rule_id),
                "metric_definition_id": str(state.metric_definition_id),
                "value": state.last_value,
                "breach_count": state.breach_count,
            },
        }
    status, response = _post_json("https://events.pagerduty.com/v2/enqueue", request_payload)
    if status < 200 or status >= 300:
        raise RuntimeError(f"PagerDuty returned HTTP {status}: {response[:500]}")
    return f"pagerduty:{state.id}"


def send_email(delivery: AlertNotificationDelivery, state: AlertState) -> str:
    host = _env("OPSCONTROL_SMTP_HOST")
    port = int(os.getenv("OPSCONTROL_SMTP_PORT", "587"))
    username = os.getenv("OPSCONTROL_SMTP_USERNAME")
    password = os.getenv("OPSCONTROL_SMTP_PASSWORD")
    sender = _env("OPSCONTROL_ALERT_EMAIL_FROM")
    recipients = [x.strip() for x in _env("OPSCONTROL_ALERT_EMAIL_TO").split(",") if x.strip()]
    if not recipients:
        raise RuntimeError("OPSCONTROL_ALERT_EMAIL_TO contains no recipients")

    message = EmailMessage()
    prefix = "RESOLVED" if delivery.event_type == "RESOLVED" else state.severity
    message["Subject"] = f"[OpsControl] [{prefix}] {state.message[:160]}"
    message["From"] = sender
    message["To"] = ", ".join(recipients)
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
    )

    context = ssl.create_default_context()
    with smtplib.SMTP(host, port, timeout=15) as smtp:
        smtp.starttls(context=context)
        if username:
            smtp.login(username, password or "")
        smtp.send_message(message)
    return f"email:{state.id}"


def send_servicenow(delivery: AlertNotificationDelivery, state: AlertState) -> str:
    base_url = _env("OPSCONTROL_SERVICENOW_URL").rstrip("/")
    username = _env("OPSCONTROL_SERVICENOW_USERNAME")
    password = _env("OPSCONTROL_SERVICENOW_PASSWORD")
    table = os.getenv("OPSCONTROL_SERVICENOW_TABLE", "incident")
    headers = {"Accept": "application/json"}

    if delivery.event_type == "OPENED":
        urgency = {"CRITICAL": "1", "WARNING": "2", "INFO": "3"}.get(state.severity, "2")
        payload = {
            "short_description": f"[OpsControl] {state.message[:150]}",
            "description": state.message,
            "urgency": urgency,
            "impact": urgency,
        }
        assignment_group = os.getenv("OPSCONTROL_SERVICENOW_ASSIGNMENT_GROUP")
        if assignment_group:
            payload["assignment_group"] = assignment_group
        body = json.dumps(payload).encode("utf-8")
        request = Request(
            f"{base_url}/api/now/table/{table}",
            data=body,
            headers={**headers, "Content-Type": "application/json"},
            method="POST",
        )
    else:
        open_delivery = None
        with SessionLocal() as db:
            open_delivery = db.scalar(
                select(AlertNotificationDelivery)
                .where(
                    AlertNotificationDelivery.alert_state_id == state.id,
                    AlertNotificationDelivery.channel == "SERVICENOW",
                    AlertNotificationDelivery.event_type == "OPENED",
                    AlertNotificationDelivery.status == "SENT",
                )
                .order_by(AlertNotificationDelivery.created_at.desc())
                .limit(1)
            )
        if not open_delivery or not open_delivery.external_reference:
            raise RuntimeError("Cannot resolve ServiceNow incident: no successful OPENED delivery reference")
        sys_id = open_delivery.external_reference
        payload = {
            "state": os.getenv("OPSCONTROL_SERVICENOW_RESOLVED_STATE", "6"),
            "close_notes": state.message,
        }
        body = json.dumps(payload).encode("utf-8")
        request = Request(
            f"{base_url}/api/now/table/{table}/{sys_id}",
            data=body,
            headers={**headers, "Content-Type": "application/json"},
            method="PUT",
        )

    import base64
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    request.add_header("Authorization", f"Basic {token}")
    with urlopen(request, timeout=15) as response:
        raw = response.read(8192).decode("utf-8", errors="replace")
        if response.status < 200 or response.status >= 300:
            raise RuntimeError(f"ServiceNow returned HTTP {response.status}: {raw[:500]}")
        if delivery.event_type == "OPENED":
            try:
                result = json.loads(raw).get("result", {})
                return str(result.get("sys_id") or result.get("number") or state.id)
            except json.JSONDecodeError:
                return str(state.id)
        return str(sys_id)


def deliver(delivery: AlertNotificationDelivery, state: AlertState) -> str:
    if delivery.channel == "PAGERDUTY":
        return send_pagerduty(delivery, state)
    if delivery.channel == "EMAIL":
        return send_email(delivery, state)
    if delivery.channel == "SERVICENOW":
        return send_servicenow(delivery, state)
    raise RuntimeError(f"Unsupported notification channel: {delivery.channel}")


def dispatch_pending_notifications():
    with SessionLocal() as db:
        deliveries = db.scalars(
            select(AlertNotificationDelivery)
            .where(
                AlertNotificationDelivery.status.in_(["PENDING", "FAILED"]),
                AlertNotificationDelivery.attempts < 5,
            )
            .order_by(AlertNotificationDelivery.created_at)
            .limit(20)
        ).all()

        for delivery in deliveries:
            state = db.get(AlertState, delivery.alert_state_id)
            if not state:
                delivery.status = "FAILED"
                delivery.last_error = "Alert state not found"
                delivery.attempts += 1
                continue

            delivery.attempts += 1
            try:
                reference = deliver(delivery, state)
                delivery.status = "SENT"
                delivery.external_reference = reference
                delivery.last_error = None
                delivery.sent_at = datetime.now(timezone.utc)
                references = dict(state.external_references or {})
                references[delivery.channel] = reference
                state.external_references = references
            except (HTTPError, URLError, TimeoutError, OSError, RuntimeError, ValueError) as exc:
                delivery.status = "FAILED"
                delivery.last_error = str(exc)[:MAX_ERROR_LENGTH]

        db.commit()
