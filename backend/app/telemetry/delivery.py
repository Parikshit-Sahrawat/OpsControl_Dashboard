"""Tenant-bound baseline notification adapters with pinned, allowlisted egress."""

import http.client, ipaddress, json, os, re, smtplib, socket, ssl, uuid
from email.message import EmailMessage
from urllib.parse import urlsplit
from sqlalchemy import select
from app.db.session import SessionLocal
from app.telemetry.models import NotificationDestination
from app.telemetry.configuration import env_reference
from app.worker.egress import check_target, resolve_target

EMAIL = r"[^\s@,;\r\n]+@[^\s@,;\r\n]+\.[^\s@,;\r\n]+"


def validate_destination(channel, c):
    allowed = {
        "SMTP": {"host", "port", "sender", "recipients", "credential_ref"},
        "WEBHOOK": {"url", "credential_ref"},
        "IN_APP": {"user_ids", "department_ids"},
    }[channel]
    if set(c) - allowed:
        raise ValueError("Unsupported destination fields")
    if channel == "IN_APP":
        for key in ("user_ids", "department_ids"):
            ids = c.get(key, [])
            if (
                not isinstance(ids, list)
                or len(ids) > 100
                or any(not isinstance(value, str) for value in ids)
                or len(set(ids)) != len(ids)
            ):
                raise ValueError("Recipient IDs must be a unique bounded array")
            for value in ids:
                if not isinstance(value, str):
                    raise ValueError("Recipient IDs must be UUID strings")
                uuid.UUID(value)
    if c.get("credential_ref"):
        env_reference(c["credential_ref"])
    if channel == "SMTP":
        if not re.fullmatch(r"[a-z0-9.-]{1,253}", c.get("host", "")):
            raise ValueError("SMTP hostname required")
        if c.get("port", 587) not in (465, 587):
            raise ValueError("SMTP TLS port must be 465 or 587")
        if not re.fullmatch(EMAIL, c.get("sender", "")):
            raise ValueError("Valid sender required")
        recipients = c.get("recipients", [])
        if (
            not isinstance(recipients, list)
            or not 1 <= len(recipients) <= 50
            or any(not re.fullmatch(EMAIL, r) for r in recipients)
        ):
            raise ValueError("One to 50 valid recipients required")
    if channel == "WEBHOOK":
        p = urlsplit(c.get("url", ""))
        if (
            p.scheme != "https"
            or not p.hostname
            or p.username
            or p.password
            or p.query
            or p.fragment
            or p.port not in (None, 443)
        ):
            raise ValueError("Webhook requires a credential-free HTTPS URL on port 443")


def secret(ref):
    env_reference(ref)
    result = os.environ.get(ref[4:])
    if not result:
        raise RuntimeError("Notification secret reference is unavailable")
    return result


def target(url):
    hosts = [
        x.strip()
        for x in os.getenv("OPSCONTROL_NOTIFICATION_ALLOWED_HOSTS", "").split(",")
        if x.strip()
    ]
    cidrs = [
        x.strip()
        for x in os.getenv("OPSCONTROL_NOTIFICATION_ALLOWED_CIDRS", "").split(",")
        if x.strip()
    ]
    p, networks = check_target(url, hosts, cidrs)
    return p, resolve_target(p.hostname, networks)


def send_destination(delivery, state, historical=False):
    id = uuid.UUID(delivery.channel.removeprefix("DEST:"))
    with SessionLocal() as db:
        row = db.scalar(
            select(NotificationDestination).where(
                NotificationDestination.id == id,
                NotificationDestination.organization_id == state.organization_id,
                NotificationDestination.enabled.is_(True),
            )
        )
        if row is None:
            raise RuntimeError("Notification destination disabled or unavailable")
        channel, c = row.channel, dict(row.configuration)
    validate_destination(channel, c)
    if channel == "IN_APP":
        from app.telemetry.inbox import persist

        if historical:
            from app.unified.pentaho_history import persist_in_app

            return persist_in_app(delivery, state, c)
        return persist(delivery, state, c)
    if channel == "WEBHOOK":
        p, ip = target(c["url"])
        body = json.dumps(
            {
                **(delivery.payload or {}),
                "delivery_id": str(delivery.id),
                "event": delivery.event_type,
            }
        ).encode()
        raw = socket.create_connection((ip, 443), timeout=10)
        try:
            secure = ssl.create_default_context().wrap_socket(
                raw, server_hostname=p.hostname
            )
            client = http.client.HTTPSConnection(p.hostname, timeout=10)
            client.sock = secure
            headers = {
                "Content-Type": "application/json",
                "Idempotency-Key": str(delivery.id),
            }
            if c.get("credential_ref"):
                key = secret(c["credential_ref"])
                if len(key) > 4096 or any(ord(x) < 32 or ord(x) > 126 for x in key):
                    raise RuntimeError("Invalid webhook authentication reference")
                headers["Authorization"] = "Bearer " + key
            try:
                client.request("POST", p.path or "/", body, headers)
                response = client.getresponse()
                if not 200 <= response.status < 300:
                    raise RuntimeError("Webhook delivery rejected")
                if len(response.read(8193)) > 8192:
                    raise RuntimeError("Webhook response too large")
            finally:
                client.close()
        finally:
            raw.close()
        return "webhook:" + str(delivery.id)
    p, ip = target("https://" + c["host"])

    class PinnedSMTP(smtplib.SMTP):
        def _get_socket(self, host, port, timeout):
            return socket.create_connection((ip, port), timeout)

    class PinnedSMTPS(smtplib.SMTP_SSL):
        def _get_socket(self, host, port, timeout):
            return self.context.wrap_socket(
                socket.create_connection((ip, port), timeout), server_hostname=host
            )

    port = c.get("port", 587)
    context = ssl.create_default_context()
    client = (
        PinnedSMTPS(c["host"], port, timeout=10, context=context)
        if port == 465
        else PinnedSMTP(c["host"], port, timeout=10)
    )
    with client as smtp:
        if port == 587:
            smtp.starttls(context=context)
        if c.get("credential_ref"):
            credentials = json.loads(secret(c["credential_ref"]))
            smtp.login(credentials["username"], credentials["password"])
        message = EmailMessage()
        message["From"] = c["sender"]
        message["To"] = ", ".join(c["recipients"])
        message["Subject"] = (
            "[OpsControl] "
            + state.severity
            + " "
            + state.message[:120].replace("\r", " ").replace("\n", " ")
        )
        message["Message-ID"] = "<opscontrol-" + str(delivery.id) + "@opscontrol.local>"
        message.set_content(state.message)
        smtp.send_message(message)
    return "smtp:" + str(delivery.id)


def queue_escalations():
    """One additional delivery per destination for an open unacknowledged alert."""
    from datetime import datetime, timedelta, timezone
    from app.models import AlertState, AlertRule, AlertNotificationDelivery

    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        pairs = db.execute(
            select(AlertState, AlertRule)
            .join(AlertRule, AlertRule.id == AlertState.alert_rule_id)
            .where(
                AlertState.status == "OPEN",
                AlertState.acknowledged_at.is_(None),
                AlertRule.evaluation_config.is_not(None),
            )
            .order_by(AlertState.first_triggered_at)
            .with_for_update(of=AlertState, skip_locked=True)
            .limit(100)
        ).all()
        for state, rule in pairs:
            config = rule.evaluation_config
            minutes = config.get("escalation_after_minutes")
            if not minutes or now - state.first_triggered_at < timedelta(
                minutes=minutes
            ):
                continue
            for id in dict.fromkeys(config.get("escalation_destinations", [])):
                channel = "DEST:" + id
                existing = db.scalar(
                    select(AlertNotificationDelivery.id).where(
                        AlertNotificationDelivery.alert_state_id == state.id,
                        AlertNotificationDelivery.channel == channel,
                        AlertNotificationDelivery.event_type == "ESCALATED",
                    )
                )
                destination = db.scalar(
                    select(NotificationDestination).where(
                        NotificationDestination.id == uuid.UUID(id),
                        NotificationDestination.organization_id
                        == state.organization_id,
                        NotificationDestination.enabled.is_(True),
                    )
                )
                if existing or not destination:
                    continue
                db.add(
                    AlertNotificationDelivery(
                        alert_state_id=state.id,
                        channel=channel,
                        event_type="ESCALATED",
                        status="PENDING",
                        payload={
                            "message": state.message,
                            "severity": state.severity,
                            "group_key": str(rule.id),
                            "alert_state_id": str(state.id),
                        },
                    )
                )
        db.commit()
