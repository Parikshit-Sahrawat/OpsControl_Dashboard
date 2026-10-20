"""Read-only Pentaho Carte status polling over pinned HTTPS.

Not Pentaho server automation: only GET /kettle/jobStatus with fixed
parameter names. Requires host policy from operator-controlled agent ENV plus
collector config policy. Does not execute, stop, kill or modify ETL jobs.
"""

import base64
import binascii
import gzip
import http.client
import io
import os
import re
import socket
import ssl
from datetime import datetime, timezone
from urllib.parse import quote
from xml.etree import ElementTree as ET
from app.worker.egress import (
    check_target,
    resolve_target,
    policy_hosts,
    policy_cidrs,
)
from app.worker.credentials import resolve_basic_auth


class PentahoStatusError(ValueError):
    pass


def _safe_token(value, label):
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= 200
        or any(ord(c) < 32 for c in value)
    ):
        raise PentahoStatusError(f"Invalid {label}")
    return value


def _transport(host, ip, path, authorization=None, timeout=8):
    # Resolve IP first via approved DNS policy; connect to that exact address
    # with hostname verification and pinned peer destination.
    context = ssl.create_default_context()
    sock = socket.create_connection((ip, 443), timeout=timeout)
    sock.settimeout(timeout)
    try:
        secure = context.wrap_socket(sock, server_hostname=host)
        try:
            headers = [
                f"GET {path} HTTP/1.1",
                f"Host: {host}",
                "Accept: application/xml",
                "User-Agent: OpsControl-Pentaho/1",
                "Connection: close",
            ]
            if authorization:
                headers.append("Authorization: Basic " + authorization)
            secure.sendall(("\r\n".join(headers) + "\r\n\r\n").encode("ascii"))
            response = http.client.HTTPResponse(secure)
            response.begin()
            data = response.read(65537)
            if len(data) > 65536:
                raise PentahoStatusError("Carte status exceeds 64 KiB")
            return response.status, data
        finally:
            secure.close()
    except Exception:
        sock.close()
        raise


def safe_text(value, secrets=()):
    """Bound source text and redact common credential forms before persistence."""
    value = str(value or "")[:16384]
    for secret in secrets:
        if secret:
            value = value.replace(secret, "[REDACTED]")
    value = re.sub(
        r"""(?i)(password|passwd|pwd|token|secret|api[_-]?key)(\s*[:=]\s*)(["'])(.*?)\3""",
        r"\1\2[REDACTED]",
        value,
    )
    value = re.sub(
        r"(?i)(password|passwd|pwd|token|secret|api[_-]?key)(\s*[:=]\s*)([^\s;,]+)",
        r"\1\2[REDACTED]",
        value,
    )
    value = re.sub(r"(?i)(Bearer|Basic)\s+[A-Za-z0-9+/=_-]+", r"\1 [REDACTED]", value)
    return re.sub(r"(?i)(https?://)[^\s/@]+:[^\s/@]+@", r"\1[REDACTED]@", value)


def _source_time(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return None
        return parsed.astimezone(timezone.utc).isoformat()
    except ValueError:
        return None


def _xml(body):
    if (
        not isinstance(body, bytes)
        or len(body) > 65536
        or b"<!DOCTYPE" in body.upper()
        or b"<!ENTITY" in body.upper()
    ):
        raise PentahoStatusError("Invalid or unsafe Carte XML response")
    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        raise PentahoStatusError("Invalid Carte status XML") from exc
    return root


def _native_number(value, label):
    if value is None:
        return None
    value = value.strip()
    if not re.fullmatch(r"[0-9]{1,7}", value):
        raise PentahoStatusError("Invalid Carte " + label)
    return int(value)


def _native_result(root, description, workload_kind="JOB", step_error_evidence=False):
    """Keep missing native evidence distinct from numeric zero and transport state."""
    nested = root.findtext("result/nr_errors")
    direct = root.findtext("nr_errors")
    errors = _native_number(nested if nested is not None else direct, "error count")
    exit_status = _native_number(root.findtext("result/exit_status"), "exit status")
    indicator = root.findtext("result/result")
    if indicator is not None:
        indicator = indicator.strip().upper()
        if indicator not in {"Y", "N"}:
            raise PentahoStatusError("Invalid Carte result indicator")
    warnings = []
    if nested is not None and direct is not None and nested.strip() != direct.strip():
        warnings.append("CONFLICTED_ERROR_COUNTS")
    if workload_kind == "TRANSFORMATION" and errors == 0 and step_error_evidence:
        warnings.append("CONFLICTED_ERROR_COUNTS")
    state = description.strip().casefold()
    if state in {"running", "initializing", "preparing", "waiting"}:
        return "RUNNING", errors, indicator, exit_status, warnings
    if state in {"finished", "completed", "finished (with errors)", "failed", "error"}:
        if state in {"finished", "completed"} and exit_status not in {None, 0}:
            warnings.append("CONFLICTED_EXIT_STATUS")
        success = (
            state in {"finished", "completed"} and indicator == "Y" and errors == 0
        )
        failure = (
            state
            in {"finished", "completed", "finished (with errors)", "failed", "error"}
            and indicator in {None, "N"}
            and errors is not None
            and errors > 0
        )
        if workload_kind == "TRANSFORMATION" and state in {
            "finished (with errors)",
            "failed",
            "error",
        }:
            if (errors is not None and errors > 0) or (
                errors is None and step_error_evidence
            ):
                failure = True
                if indicator == "Y":
                    warnings.append("NATIVE_RESULT_Y_WITH_ERRORS")
        if any(
            w in {"CONFLICTED_ERROR_COUNTS", "CONFLICTED_EXIT_STATUS"} for w in warnings
        ) or (
            not success
            and not failure
            and (indicator is not None or errors is not None)
        ):
            warnings.append("CONFLICTED_OR_INCOMPLETE_NATIVE_RESULT")
        return (
            (
                "SUCCESS"
                if success and not warnings
                else (
                    "FAILED"
                    if failure
                    and not any(
                        warning in {"CONFLICTED_ERROR_COUNTS", "CONFLICTED_EXIT_STATUS"}
                        for warning in warnings
                    )
                    else "UNKNOWN"
                )
            ),
            errors,
            indicator,
            exit_status,
            warnings,
        )
    return "UNKNOWN", errors, indicator, exit_status, warnings


def _transformation_steps(root, secrets=()):
    entries = root.findall("./stepstatuslist/stepstatus")
    if len(entries) > 100:
        raise PentahoStatusError("Too many Carte transformation steps")
    rows = []
    counters = ("errors", "linesWritten", "linesRead", "linesInput", "linesOutput")
    for position, entry in enumerate(entries):
        name = _safe_token(entry.findtext("stepname"), "step name")
        copy = entry.findtext("copy")
        if copy is not None and not re.fullmatch(r"[0-9]{1,7}", copy.strip()):
            raise PentahoStatusError("Invalid Carte step copy")
        metrics = {key: _native_number(entry.findtext(key), key) for key in counters}
        description = safe_text(entry.findtext("statusDescription"), secrets)[:200]
        errors = metrics["errors"]
        state = description.casefold()
        status = (
            "FAILED"
            if errors is not None and errors > 0
            else (
                "SUCCESS"
                if state in {"finished", "completed"} and errors == 0
                else (
                    "RUNNING"
                    if state in {"running", "initializing", "preparing", "waiting"}
                    else "UNKNOWN"
                )
            )
        )
        rows.append(
            {
                "name": safe_text(name, secrets)[:200],
                "copy": copy.strip() if copy is not None else None,
                "status": status,
                "statusDescription": description or None,
                "nr_errors": errors,
                "metrics": metrics,
                "step_type": "PENTAHO_TRANSFORMATION_STEP",
                "observed_entry_position": position,
            }
        )
    return rows


def _inventory_entries(root, workload_kind, name):
    if workload_kind == "TRANSFORMATION":
        paths = ("./transstatuslist/transstatus", ".//trans_status", ".//trans-status")
        field = "transname"
    else:
        paths = ("./jobstatuslist/jobstatus", ".//job_status", ".//job-status")
        field = "jobname"
    entries = [entry for path in paths for entry in root.findall(path)]
    if len(entries) > 200:
        raise PentahoStatusError("Carte inventory exceeds bounded polling limit")
    selected = []
    identities = set()
    for entry in entries:
        if entry.findtext(field) != name:
            continue
        identity = _safe_token(entry.findtext("id"), "execution id")
        if identity in identities:
            raise PentahoStatusError("Duplicate Carte execution identity")
        identities.add(identity)
        selected.append((identity, (entry.findtext("status_desc") or "").strip()))
    return selected


def _decoded_log(value, secrets):
    if value is None:
        return None, "NOT_AVAILABLE"
    try:
        value = value.strip()
        if value.startswith("<![CDATA[") and value.endswith("]]>"):
            value = value[len("<![CDATA[") : -len("]]>")]
        elif "<![CDATA[" in value or value.endswith("]]>"):
            raise ValueError("Malformed Carte log wrapper")
        encoded = "".join(value.split()).encode("ascii")
        data = base64.b64decode(encoded, validate=True)
        if data[:2] == b"\x1f\x8b":
            with gzip.GzipFile(fileobj=io.BytesIO(data)) as stream:
                data = stream.read(16385)
        if len(data) > 16384:
            raise ValueError("Carte log exceeds limit")
        return safe_text(data.decode("utf-8", errors="replace"), secrets), "AVAILABLE"
    except (ValueError, OSError, UnicodeError, binascii.Error):
        return None, "DECODE_FAILED"


def parse_carte_status(body, collect_logs=False, secrets=(), workload_kind="JOB"):
    root = _xml(body)
    allowed = (
        {"trans_status", "transstatus", "transformation_status"}
        if workload_kind == "TRANSFORMATION"
        else {"job_status", "jobstatus"}
    )
    if root.tag.replace("-", "_") not in allowed:
        raise PentahoStatusError("Unexpected Carte XML root")
    execution_id = (root.findtext("id") or "").strip()
    status = (root.findtext("status_desc") or root.findtext("status") or "").strip()
    if not execution_id or not status:
        raise PentahoStatusError("Carte response lacks execution id or status")
    steps = (
        _transformation_steps(root, secrets)
        if workload_kind == "TRANSFORMATION"
        else []
    )
    normalized, errors, indicator, exit_status, warnings = _native_result(
        root,
        status,
        workload_kind,
        any(row["nr_errors"] is not None and row["nr_errors"] > 0 for row in steps),
    )
    for entry in (
        []
        if workload_kind == "TRANSFORMATION"
        else root.findall(".//jobentry_result") + root.findall(".//jobentry-result")
    ):
        if len(steps) >= 100:
            raise PentahoStatusError("Too many Carte job entries")
        step_name = entry.findtext("name") or entry.findtext("jobentry/name")
        if not step_name:
            continue
        step_errors = _native_number(
            (
                entry.findtext("result/nr_errors")
                if entry.findtext("result/nr_errors") is not None
                else entry.findtext("nr_errors")
            ),
            "job entry error count",
        )
        steps.append(
            {
                "name": safe_text(step_name, secrets)[:200],
                "step_type": "CARTE_JOB_ENTRY",
                "status": (
                    "FAILED"
                    if step_errors is not None and step_errors > 0
                    else "UNKNOWN"
                ),
                "nr_errors": step_errors,
                "error_code": (
                    "CARTE_REPORTED_ERRORS"
                    if step_errors is not None and step_errors > 0
                    else None
                ),
                "error_message": safe_text(
                    entry.findtext("comment") or entry.findtext("result/log_text"),
                    secrets,
                )[:2000]
                or None,
            }
        )
    result = {
        "execution_id": _safe_token(execution_id, "execution id"),
        "execution_status": normalized,
        "native_status_desc": safe_text(status, secrets)[:200],
        "native_result": indicator,
        "native_exit_status": exit_status,
        "native_log_channel_id": safe_text(
            root.findtext("result/log_channel_id"), secrets
        ).strip()[:200]
        or None,
        "native_log_date_raw": safe_text(root.findtext("log_date"), secrets).strip()[
            :100
        ]
        or None,
        "evidence_warnings": warnings,
        "nr_errors": errors,
        "steps": steps,
        "started_at": _source_time(root.findtext("start_date")),
        "ended_at": _source_time(root.findtext("end_date")),
    }
    if (
        result["started_at"]
        and result["ended_at"]
        and result["ended_at"] < result["started_at"]
    ):
        raise PentahoStatusError("Carte end precedes start")
    if collect_logs:
        logs = root.findtext("log_text")
        if logs is not None:
            result["logs"] = safe_text(logs, secrets)
            result["log_evidence_status"] = "AVAILABLE"
        else:
            result["logs"], result["log_evidence_status"] = _decoded_log(
                root.findtext("logging_string"), secrets
            )
    return result


def get_job_status(
    cfg, transport=_transport, resolver=None, credential_resolver=resolve_basic_auth
):
    if not isinstance(cfg, dict):
        raise PentahoStatusError("Pentaho collector config must be JSON")
    keys = {
        "url",
        "job_name",
        "execution_id",
        "credential_ref",
        "allowed_hosts",
        "allowed_cidrs",
        "job_order_id",
        "collect_logs",
        "workload_kind",
    }
    if set(cfg) - keys:
        raise PentahoStatusError("Unsupported Pentaho configuration key")
    url = cfg.get("url")
    name = _safe_token(cfg.get("job_name"), "job name")
    workload_kind = cfg.get("workload_kind", "JOB")
    if workload_kind not in {"JOB", "TRANSFORMATION"}:
        raise PentahoStatusError("Unsupported Carte workload kind")
    execution = (
        _safe_token(cfg["execution_id"], "execution id")
        if cfg.get("execution_id")
        else None
    )
    if type(cfg.get("collect_logs", False)) is not bool:
        raise PentahoStatusError("collect_logs must be boolean")
    # Server-controlled policy alone is insufficient. A customer-side worker
    # must have an independent locally approved host/CIDR policy.
    local_hosts = policy_hosts(
        [
            x.strip()
            for x in os.getenv("OPSCONTROL_LOCAL_ALLOWED_HOSTS", "").split(",")
            if x.strip()
        ]
    )
    local_cidrs = policy_cidrs(
        [
            x.strip()
            for x in os.getenv("OPSCONTROL_LOCAL_ALLOWED_CIDRS", "").split(",")
            if x.strip()
        ]
    )
    supplied_hosts = policy_hosts(cfg.get("allowed_hosts", []))
    supplied_nets = policy_cidrs(cfg.get("allowed_cidrs", []))
    if not set(supplied_hosts).issubset(set(local_hosts)) or not all(
        any(n.subnet_of(local) for local in local_cidrs) for n in supplied_nets
    ):
        raise PentahoStatusError("Collector policy exceeds local egress policy")
    parts, nets = check_target(url, supplied_hosts, cfg["allowed_cidrs"])
    if parts.path not in ("", "/", "/kettle"):
        raise PentahoStatusError("Only Carte root URL is supported")
    ip = (
        resolve_target(parts.hostname, nets, resolver)
        if resolver
        else resolve_target(parts.hostname, nets)
    )
    credential_ref = cfg.get("credential_ref")
    basic = None
    secrets = ()
    if credential_ref:
        username, password = credential_resolver(credential_ref)
        basic = base64.b64encode((username + ":" + password).encode()).decode()
        secrets = (username, password, basic)
    if execution is None:
        status, body = transport(parts.hostname, ip, "/kettle/status/?xml=Y", basic)
        if status != 200:
            raise PentahoStatusError("Carte inventory read failed")
        root = _xml(body)
        if root.tag.replace("-", "_") not in {"server_status", "serverstatus"}:
            raise PentahoStatusError("Unexpected Carte inventory XML root")
        entries = _inventory_entries(root, workload_kind, name)
        executions = []
        detail_path = (
            "/kettle/jobStatus/" if workload_kind == "JOB" else "/kettle/transStatus/"
        )
        for identity, inventory_status in entries:
            path = (
                detail_path
                + "?name="
                + quote(name, safe="")
                + "&id="
                + quote(identity, safe="")
                + "&xml=Y"
            )
            status, body = transport(parts.hostname, ip, path, basic)
            if status != 200:
                raise PentahoStatusError("Carte execution detail read failed")
            record = parse_carte_status(
                body, cfg.get("collect_logs", False), secrets, workload_kind
            )
            if record["execution_id"] != identity:
                raise PentahoStatusError("Carte response execution id mismatch")
            if inventory_status and record["native_status_desc"] != inventory_status:
                record["evidence_warnings"].append("INVENTORY_DETAIL_STATUS_CHANGED")
            executions.append(record)
        return {
            "provider": "PENTAHO",
            "outcome": "SUCCESS",
            "inventory_complete": False,
            "executions": executions,
        }
    path = (
        ("/kettle/jobStatus/" if workload_kind == "JOB" else "/kettle/transStatus/")
        + "?name="
        + quote(name, safe="")
        + "&id="
        + quote(execution, safe="")
        + "&xml=Y"
    )
    status, body = transport(parts.hostname, ip, path, basic)
    if status != 200:
        raise PentahoStatusError("Carte read-only status request failed")
    result = parse_carte_status(
        body, cfg.get("collect_logs", False), secrets, workload_kind
    )
    if result["execution_id"] != execution:
        raise PentahoStatusError("Carte response execution id mismatch")
    return {"provider": "PENTAHO", "outcome": "SUCCESS", **result}
