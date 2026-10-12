"""Alert notification delivery adapters.

Destination configuration is deployment-owned. ServiceNow production credentials
use approved external references. Delivery uses short fenced leases; provider IO
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

from sqlalchemy import select

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


def _email_message_id(delivery: AlertNotificationDelivery) -> str:
    return f"<opscontrol-{delivery.id}@opscontrol.local>"


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

def _servicenow_auth(username: str, password: str) -> str:
    import base64
    if ':' in username or any(ord(c)<32 or ord(c)==127 for c in username):
        raise RuntimeError('Invalid ServiceNow credential encoding')
    result = base64.b64encode(f'{username}:{password}'.encode()).decode()
    if len(result)>8192: raise RuntimeError('ServiceNow credential exceeds header limit')
    return result

class _NoNotificationRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError('Notification redirects forbidden')

def _notification_open(request, timeout=10):
    client = build_opener(_NoNotificationRedirect(), HTTPSHandler(context=ssl.create_default_context()))
    return client.open(request, timeout=timeout)

def _servicenow_config():
    from app.core.config import settings
    from app.worker.credentials import resolve_basic_auth
    base = _env('OPSCONTROL_SERVICENOW_URL').rstrip('/')
    try: parsed = urlsplit(base); port = parsed.port
    except ValueError: raise RuntimeError('Invalid ServiceNow HTTPS origin') from None
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
            or parsed.path or parsed.query or parsed.fragment):
        raise RuntimeError('ServiceNow requires a fixed HTTPS origin')
    table = os.getenv('OPSCONTROL_SERVICENOW_TABLE', 'incident')
    field = os.getenv('OPSCONTROL_SERVICENOW_CORRELATION_FIELD', 'correlation_id')
    if not all(re.fullmatch(r'[a-z][a-z0-9_]{0,79}', value) for value in (table, field)):
        raise RuntimeError('Invalid ServiceNow table or correlation field')
    reference = os.getenv('OPSCONTROL_SERVICENOW_CREDENTIAL_REF')
    if reference:
        username, password = resolve_basic_auth(reference)
    elif settings.environment == 'production':
        raise RuntimeError('Production ServiceNow requires an external credential reference')
    else:
        username, password = _env('OPSCONTROL_SERVICENOW_USERNAME'), _env('OPSCONTROL_SERVICENOW_PASSWORD')
    return base, table, field, {'Accept':'application/json', 'Authorization':'Basic '+_servicenow_auth(username,password)}

def _servicenow_request(url, method, headers, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    request = Request(url, data=data, headers={**headers, 'Content-Type':'application/json'}, method=method)
    with _notification_open(request) as response:
        if not 200 <= response.status < 300:
            raise RuntimeError('Invalid ServiceNow response status')
        raw = response.read(8193)
        if len(raw)>8192: raise RuntimeError('ServiceNow response exceeds 8 KiB')
        def unique_fields(pairs):
            obj = {}
            for key, value in pairs:
                if key in obj: raise ValueError('Duplicate provider JSON property')
                obj[key] = value
            return obj
        decoded = json.loads(raw, object_pairs_hook=unique_fields)
        if not isinstance(decoded,dict) or 'result' not in decoded:
            raise RuntimeError('Invalid ServiceNow response envelope')
        return decoded['result']

def _servicenow_sys_id(record):
    value = record.get('sys_id') if isinstance(record,dict) else None
    if not isinstance(value,str) or not re.fullmatch(r'[0-9a-f]{32}',value):
        raise RuntimeError('Invalid ServiceNow incident identity')
    return value

def _find_servicenow_incident(base_url, table, correlation_field, correlation_id, headers):
    query = quote(f'{correlation_field}={correlation_id}', safe='')
    result = _servicenow_request(f'{base_url}/api/now/table/{table}?sysparm_query={query}&sysparm_limit=1&sysparm_fields=sys_id,number', 'GET', headers)
    if not isinstance(result,list) or len(result)>1:
        raise RuntimeError('Invalid ServiceNow correlation lookup')
    return _servicenow_sys_id(result[0]) if result else None

def send_servicenow(delivery: AlertNotificationDelivery, state: AlertState) -> str:
    if delivery.event_type not in {'OPENED','RESOLVED'}:
        raise RuntimeError('Unsupported ServiceNow lifecycle event')
    base, table, field, headers = _servicenow_config()
    correlation_id = f'opscontrol:{state.id}:OPENED'
    message = str((delivery.payload or {}).get('message') or state.message)[:4000]
    if delivery.event_type == 'OPENED':
        existing = _find_servicenow_incident(base,table,field,correlation_id,headers)
        if existing: return existing
        urgency = {'CRITICAL':'1','WARNING':'2','INFO':'3'}.get(state.severity,'2')
        payload = {'short_description':'[OpsControl] '+message[:150], 'description':message,
                   'urgency':urgency, 'impact':urgency, field:correlation_id}
        if os.getenv('OPSCONTROL_SERVICENOW_ASSIGNMENT_GROUP'):
            payload['assignment_group'] = os.environ['OPSCONTROL_SERVICENOW_ASSIGNMENT_GROUP']
        try:
            result = _servicenow_request(f'{base}/api/now/table/{table}','POST',headers,payload)
        except HTTPError as error:
            if error.code != 409: raise
            existing = _find_servicenow_incident(base,table,field,correlation_id,headers)
            if existing: return existing
            raise RuntimeError('ServiceNow correlation conflict without incident') from None
        return _servicenow_sys_id(result)
    # No network IO while the lookup database transaction is open.
    with SessionLocal() as db:
        reference = db.scalar(select(AlertNotificationDelivery.external_reference).where(
            AlertNotificationDelivery.alert_state_id==state.id,
            AlertNotificationDelivery.channel=='SERVICENOW',
            AlertNotificationDelivery.event_type=='OPENED',
            AlertNotificationDelivery.status=='SENT').order_by(AlertNotificationDelivery.created_at.desc()).limit(1))
    sys_id = _servicenow_sys_id({'sys_id':reference})
    closure = {'state':os.getenv('OPSCONTROL_SERVICENOW_RESOLVED_STATE','6'), 'close_notes':message}
    if os.getenv('OPSCONTROL_SERVICENOW_CLOSE_CODE'):
        closure['close_code'] = os.environ['OPSCONTROL_SERVICENOW_CLOSE_CODE']
    result = _servicenow_request(f'{base}/api/now/table/{table}/{sys_id}','PATCH',headers,closure)
    if _servicenow_sys_id(result)!=sys_id:
        raise RuntimeError('ServiceNow resolution changed incident identity')
    return sys_id

def deliver(delivery: AlertNotificationDelivery, state: AlertState) -> str:
    if delivery.channel == "PAGERDUTY":
        return send_pagerduty(delivery, state)
    if delivery.channel == "EMAIL":
        return send_email(delivery, state)
    if delivery.channel == "SERVICENOW":
        return send_servicenow(delivery, state)
    raise RuntimeError(f"Unsupported notification channel: {delivery.channel}")


MAX_ATTEMPTS = 5
LEASE_SECONDS = 120

def _claim_notification():
    """One short SKIP LOCKED claim; detach snapshots before provider IO."""
    from sqlalchemy.orm import aliased
    opened = aliased(AlertNotificationDelivery)
    active = aliased(AlertNotificationDelivery)
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        exhausted = db.scalars(select(AlertNotificationDelivery).where(
            AlertNotificationDelivery.status=='PROCESSING',
            AlertNotificationDelivery.lease_expires_at<=now,
            AlertNotificationDelivery.attempts>=MAX_ATTEMPTS
        ).with_for_update(skip_locked=True).limit(20)).all()
        for row in exhausted:
            row.status='FAILED'; row.last_error='Delivery retry limit reached'
            row.lease_token=None; row.lease_expires_at=None
        ready = ((AlertNotificationDelivery.status=='PENDING') |
            ((AlertNotificationDelivery.status=='FAILED') & (AlertNotificationDelivery.updated_at<=now-timedelta(seconds=30))) |
            ((AlertNotificationDelivery.status=='PROCESSING') & (AlertNotificationDelivery.lease_expires_at<=now)))
        prerequisite = select(opened.id).where(opened.alert_state_id==AlertNotificationDelivery.alert_state_id,
            opened.channel==AlertNotificationDelivery.channel, opened.event_type=='OPENED',
            opened.status=='SENT', opened.external_reference.is_not(None)).exists()
        inflight = select(active.id).where(active.alert_state_id==AlertNotificationDelivery.alert_state_id,
            active.channel==AlertNotificationDelivery.channel, active.id!=AlertNotificationDelivery.id,
            active.status=='PROCESSING', active.lease_expires_at>now).exists()
        delivery = db.scalar(select(AlertNotificationDelivery).where(ready,
            AlertNotificationDelivery.attempts<MAX_ATTEMPTS, ~inflight,
            (AlertNotificationDelivery.event_type!='RESOLVED') | prerequisite
        ).order_by(AlertNotificationDelivery.created_at,AlertNotificationDelivery.id)
         .with_for_update(skip_locked=True).limit(1))
        if delivery is None: db.commit(); return None
        # Serialize claims for an alert, including legacy duplicate event rows.
        state = db.scalar(select(AlertState).where(AlertState.id==delivery.alert_state_id).with_for_update())
        if state is None:
            delivery.status='FAILED'; delivery.attempts+=1; delivery.last_error='Alert state unavailable'
            db.commit(); return None
        current = db.scalar(select(AlertNotificationDelivery.id).where(
            AlertNotificationDelivery.alert_state_id==state.id, AlertNotificationDelivery.channel==delivery.channel,
            AlertNotificationDelivery.id!=delivery.id, AlertNotificationDelivery.status=='PROCESSING',
            AlertNotificationDelivery.lease_expires_at>now).limit(1))
        if current: db.commit(); return None
        previous = db.scalar(select(AlertNotificationDelivery).where(
            AlertNotificationDelivery.alert_state_id==state.id, AlertNotificationDelivery.channel==delivery.channel,
            AlertNotificationDelivery.event_type==delivery.event_type, AlertNotificationDelivery.status=='SENT'
        ).order_by(AlertNotificationDelivery.created_at).limit(1))
        if previous:
            delivery.status='SENT'; delivery.external_reference=previous.external_reference
            delivery.sent_at=now; delivery.last_error=None
            db.commit(); return None
        token=uuid.uuid4()
        delivery.status='PROCESSING'; delivery.attempts+=1
        delivery.lease_token=token; delivery.lease_expires_at=now+timedelta(seconds=LEASE_SECONDS)
        delivery.updated_at=now
        db.flush()
        db.expunge(delivery); db.expunge(state)
        db.commit()
        return delivery,state,token

def _finish_notification(delivery_id, token, reference=None, error=None):
    now=datetime.now(timezone.utc)
    with SessionLocal() as db:
        delivery=db.scalar(select(AlertNotificationDelivery).where(
            AlertNotificationDelivery.id==delivery_id, AlertNotificationDelivery.lease_token==token,
            AlertNotificationDelivery.status=='PROCESSING', AlertNotificationDelivery.lease_expires_at>now
        ).with_for_update())
        if delivery is None: return False  # expired/reclaimed completion is fenced
        delivery.lease_token=None; delivery.lease_expires_at=None; delivery.updated_at=now
        if error:
            delivery.status='FAILED'; delivery.last_error=error
        else:
            delivery.status='SENT'; delivery.external_reference=reference
            delivery.sent_at=now; delivery.last_error=None
            state=db.scalar(select(AlertState).where(AlertState.id==delivery.alert_state_id).with_for_update())
            if state:
                refs=dict(state.external_references or {}); refs[delivery.channel]=reference
                state.external_references=refs
        db.commit()
        return True

def _safe_delivery_error(error):
    # A provider can echo credentials/URLs/body contents in its errors. Keep a
    # bounded classification, never str(error) or response bodies in evidence.
    if isinstance(error,HTTPError): return f'Notification provider HTTP {error.code}'
    if isinstance(error,ssl.SSLError): return 'Notification TLS verification failed'
    if isinstance(error,(URLError,TimeoutError,OSError)): return 'Notification transport unavailable'
    return 'Notification configuration or provider response rejected'

def dispatch_pending_notifications():
    counts={'claimed':0,'sent':0,'failed':0,'fenced':0}
    for _ in range(20):
        claim=_claim_notification()
        if claim is None: break
        delivery,state,token=claim; counts['claimed']+=1
        try:
            reference=deliver(delivery,state)
            if not isinstance(reference,str) or not reference or len(reference)>500:
                raise RuntimeError('Invalid notification reference')
            completed=_finish_notification(delivery.id,token,reference=reference)
            counts['sent' if completed else 'fenced']+=1
        except Exception as error:
            completed=_finish_notification(delivery.id,token,error=_safe_delivery_error(error))
            counts['failed' if completed else 'fenced']+=1
    return counts
