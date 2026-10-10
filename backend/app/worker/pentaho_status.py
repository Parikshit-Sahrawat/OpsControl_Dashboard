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

def parse_carte_status(body):
    if not isinstance(body,bytes) or len(body)>65536 or b"<!DOCTYPE" in body.upper() or b"<!ENTITY" in body.upper():
        raise PentahoStatusError("Invalid or unsafe Carte XML response")
    try: root=ET.fromstring(body)
    except ET.ParseError as exc:raise PentahoStatusError("Invalid Carte status XML") from exc
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
    return {"execution_id":_safe_token(execution_id,"execution id"),
            "execution_status":normalized,
            "nr_errors":errors}

def get_job_status(cfg,transport=_transport,resolver=None,credential_resolver=resolve_basic_auth):
    if not isinstance(cfg,dict):raise PentahoStatusError("Pentaho collector config must be JSON")
    keys={"url","job_name","execution_id","credential_ref","allowed_hosts","allowed_cidrs","job_order_id"}
    if set(cfg)-keys:raise PentahoStatusError("Unsupported Pentaho configuration key")
    url=cfg.get("url")
    name=_safe_token(cfg.get("job_name"),"job name")
    execution=_safe_token(cfg.get("execution_id"),"execution id")
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
    if credential_ref:
        username,password=credential_resolver(credential_ref)
        basic=base64.b64encode((username+":"+password).encode()).decode()
    path="/kettle/jobStatus/?name="+quote(name,safe="")+"&id="+quote(execution,safe="")+"&xml=Y"
    status,body=transport(parts.hostname,ip,path,basic)
    if status!=200:raise PentahoStatusError("Carte read-only status request failed")
    result=parse_carte_status(body)
    if result["execution_id"]!=execution:
        raise PentahoStatusError("Carte response execution id mismatch")
    return {"provider":"PENTAHO","outcome":"SUCCESS" if result["execution_status"] in {"RUNNING","SUCCESS"} else "DEGRADED",
            **result}
