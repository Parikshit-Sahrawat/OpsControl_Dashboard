"""Read-only Pentaho Carte status polling over pinned HTTPS.

Not Pentaho server automation: only GET /kettle/jobStatus with fixed
parameter names. Requires host policy from operator-controlled agent ENV plus
collector config policy. Does not execute, stop, kill or modify ETL jobs.
"""
import base64
import http.client
import os
import re
import socket
import ssl
from datetime import datetime, timezone
from urllib.parse import quote
from xml.etree import ElementTree as ET
from app.worker.egress import (EgressDenied,check_target,resolve_target,policy_hosts,policy_cidrs)
from app.worker.credentials import resolve_basic_auth,CredentialProviderError

class PentahoStatusError(ValueError): pass

def _safe_token(value,label):
    if not isinstance(value,str) or not 1<=len(value)<=200 or any(ord(c)<32 for c in value):
        raise PentahoStatusError(f"Invalid {label}")
    return value

def _transport(host,ip,path,authorization=None,timeout=8):
    # Resolve IP first via approved DNS policy; connect to that exact address
    # with hostname verification and pinned peer destination.
    context=ssl.create_default_context()
    sock=socket.create_connection((ip,443),timeout=timeout)
    sock.settimeout(timeout)
    try:
        secure=context.wrap_socket(sock,server_hostname=host)
        try:
            headers=[f"GET {path} HTTP/1.1",f"Host: {host}",
                     "Accept: application/xml","User-Agent: OpsControl-Pentaho/1",
                     "Connection: close"]
            if authorization:
                headers.append("Authorization: Basic "+authorization)
            secure.sendall(("\r\n".join(headers)+"\r\n\r\n").encode("ascii"))
            response=http.client.HTTPResponse(secure)
            response.begin()
            data=response.read(65537)
            if len(data)>65536: raise PentahoStatusError("Carte status exceeds 64 KiB")
            return response.status,data
        finally:secure.close()
    except Exception:
        sock.close()
        raise

def safe_text(value, secrets=()):
    """Bound source text and redact common credential forms before persistence."""
    value = str(value or '')[:16384]
    for secret in secrets:
        if secret: value = value.replace(secret, '[REDACTED]')
    value = re.sub(r'''(?i)(password|passwd|pwd|token|secret|api[_-]?key)(\s*[:=]\s*)(["'])(.*?)\3''', r'\1\2[REDACTED]', value)
    value = re.sub(r'(?i)(password|passwd|pwd|token|secret|api[_-]?key)(\s*[:=]\s*)([^\s;,]+)', r'\1\2[REDACTED]', value)
    value = re.sub(r'(?i)(Bearer|Basic)\s+[A-Za-z0-9+/=_-]+', r'\1 [REDACTED]', value)
    return re.sub(r'(?i)(https?://)[^\s/@]+:[^\s/@]+@', r'\1[REDACTED]@', value)

def _source_time(value):
    if not value: return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace('Z', '+00:00'))
        if parsed.tzinfo is None: return None
        return parsed.astimezone(timezone.utc).isoformat()
    except ValueError: return None

def _xml(body):
    if not isinstance(body,bytes) or len(body)>65536 or b"<!DOCTYPE" in body.upper() or b"<!ENTITY" in body.upper():
        raise PentahoStatusError("Invalid or unsafe Carte XML response")
    try: root=ET.fromstring(body)
    except ET.ParseError as exc:raise PentahoStatusError("Invalid Carte status XML") from exc
    return root

def parse_carte_status(body, collect_logs=False, secrets=()):
    root = _xml(body)
    # Pentaho may return <job_status> or <job-status>, but no arbitrary XML is trusted.
    if root.tag.replace("-","_") not in {"job_status","jobstatus"}:
        raise PentahoStatusError("Unexpected Carte XML root")
    execution_id=(root.findtext("id") or "").strip()
    status=(root.findtext("status_desc") or root.findtext("status") or "").strip()
    if not execution_id or not status:
        raise PentahoStatusError("Carte response lacks execution id or status")
    errors_raw=(root.findtext(".//nr_errors") or "0").strip()
    if not errors_raw.isdecimal(): raise PentahoStatusError("Carte returned invalid error count")
    errors=min(int(errors_raw),1000000)
    lower=status.lower()
    if "running" in lower or "initializ" in lower or "prepar" in lower:
        normalized="RUNNING"
    elif "finish" in lower or "complete" in lower or "stopp" in lower:
        normalized="FAILED" if errors>0 or "error" in lower or "stop" in lower else "SUCCESS"
    elif "error" in lower or "fail" in lower:
        normalized="FAILED"
    else:
        normalized="NO_RESPONSE"  # unknown status is not a successful job
    steps = []
    for entry in root.findall('.//jobentry_result') + root.findall('.//jobentry-result'):
        if len(steps) >= 100: raise PentahoStatusError('Too many Carte job entries')
        step_name = entry.findtext('name') or entry.findtext('jobentry/name')
        if not step_name: continue
        raw_errors = entry.findtext('result/nr_errors') or entry.findtext('nr_errors') or '0'
        if not raw_errors.isdecimal(): raise PentahoStatusError('Invalid job entry error count')
        step_errors = int(raw_errors)
        steps.append({'name': safe_text(step_name, secrets)[:200], 'step_type': 'CARTE_JOB_ENTRY',
                      'status': 'FAILED' if step_errors else 'SUCCESS',
                      'error_code': 'CARTE_REPORTED_ERRORS' if step_errors else None,
                      'error_message': safe_text(entry.findtext('comment') or entry.findtext('result/log_text'), secrets)[:2000] or None})
    result = {"execution_id":_safe_token(execution_id,"execution id"),
            "execution_status":normalized,
            "nr_errors":errors, 'steps': steps,
            'started_at': _source_time(root.findtext('start_date')),
            'ended_at': _source_time(root.findtext('end_date'))}
    if result['started_at'] and result['ended_at'] and result['ended_at'] < result['started_at']:
        raise PentahoStatusError('Carte end precedes start')
    if collect_logs:
        logs = root.findtext('log_text')
        if logs is None and root.findtext('logging_string'):
            try:
                import gzip, io
                encoded = base64.b64decode(root.findtext('logging_string'), validate=True)
                if encoded[:2] == b'\x1f\x8b':
                    with gzip.GzipFile(fileobj=io.BytesIO(encoded)) as stream: encoded = stream.read(16385)
                logs = encoded[:16384].decode('utf-8', errors='replace')
            except (ValueError, OSError): logs = '[Source log encoding unavailable]'
        result['logs'] = safe_text(logs, secrets)
    return result

def get_job_status(cfg,transport=_transport,resolver=None,credential_resolver=resolve_basic_auth):
    if not isinstance(cfg,dict):raise PentahoStatusError("Pentaho collector config must be JSON")
    keys={"url","job_name","execution_id","credential_ref","allowed_hosts","allowed_cidrs","job_order_id", "collect_logs"}
    if set(cfg)-keys:raise PentahoStatusError("Unsupported Pentaho configuration key")
    url=cfg.get("url")
    name=_safe_token(cfg.get("job_name"),"job name")
    execution=_safe_token(cfg['execution_id'],"execution id") if cfg.get('execution_id') else None
    if type(cfg.get('collect_logs', False)) is not bool: raise PentahoStatusError('collect_logs must be boolean')
    # Server-controlled policy alone is insufficient. A customer-side worker
    # must have an independent locally approved host/CIDR policy.
    local_hosts=policy_hosts([x.strip() for x in os.getenv("OPSCONTROL_LOCAL_ALLOWED_HOSTS","").split(",") if x.strip()])
    local_cidrs=policy_cidrs([x.strip() for x in os.getenv("OPSCONTROL_LOCAL_ALLOWED_CIDRS","").split(",") if x.strip()])
    supplied_hosts=policy_hosts(cfg.get("allowed_hosts",[]))
    supplied_nets=policy_cidrs(cfg.get("allowed_cidrs",[]))
    if not set(supplied_hosts).issubset(set(local_hosts)) or not all(
        any(n.subnet_of(local) for local in local_cidrs) for n in supplied_nets
    ):raise PentahoStatusError("Collector policy exceeds local egress policy")
    parts,nets=check_target(url,supplied_hosts,cfg["allowed_cidrs"])
    if parts.path not in ("","/","/kettle"):
        raise PentahoStatusError("Only Carte root URL is supported")
    ip=resolve_target(parts.hostname,nets,resolver) if resolver else resolve_target(parts.hostname,nets)
    credential_ref=cfg.get("credential_ref")
    basic=None
    secrets=()
    if credential_ref:
        username,password=credential_resolver(credential_ref)
        basic=base64.b64encode((username+":"+password).encode()).decode()
        secrets=(username, password, basic)
    if execution is None:
        status,body=transport(parts.hostname,ip,'/kettle/status/?xml=Y',basic)
        if status!=200: raise PentahoStatusError('Carte inventory read failed')
        root=_xml(body)
        if root.tag.replace('-', '_') != 'server_status': raise PentahoStatusError('Unexpected Carte inventory XML root')
        entries=root.findall('.//job_status')+root.findall('.//job-status')
        if len(entries)>200: raise PentahoStatusError('Carte inventory exceeds bounded polling limit')
        executions=[]
        for entry in entries:
            if entry.findtext('jobname')!=name: continue
            identity=_safe_token(entry.findtext('id'),'execution id')
            if any(item['execution_id']==identity for item in executions): raise PentahoStatusError('Duplicate Carte execution identity')
            path='/kettle/jobStatus/?name='+quote(name,safe='')+'&id='+quote(identity,safe='')+'&xml=Y'
            status,body=transport(parts.hostname,ip,path,basic)
            if status!=200: raise PentahoStatusError('Carte execution detail read failed')
            record=parse_carte_status(body,cfg.get('collect_logs',False),secrets)
            if record['execution_id']!=identity: raise PentahoStatusError('Carte response execution id mismatch')
            executions.append(record)
        return {'provider':'PENTAHO','outcome':'SUCCESS','inventory_complete':True,'executions':executions}
    path="/kettle/jobStatus/?name="+quote(name,safe="")+"&id="+quote(execution,safe="")+"&xml=Y"
    status,body=transport(parts.hostname,ip,path,basic)
    if status!=200:raise PentahoStatusError("Carte read-only status request failed")
    result=parse_carte_status(body,cfg.get('collect_logs',False),secrets)
    if result["execution_id"]!=execution:
        raise PentahoStatusError("Carte response execution id mismatch")
    return {"provider":"PENTAHO","outcome":"SUCCESS" if result["execution_status"] in {"RUNNING","SUCCESS"} else "DEGRADED",
            **result}
