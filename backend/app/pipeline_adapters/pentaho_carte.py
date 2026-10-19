"""Opt-in R1 Carte GET reader. No persistent job discovery or control APIs."""

import base64
import hashlib
import ssl
from datetime import datetime, timezone
from urllib.parse import quote
from .core import AdapterError, Batch
from .pentaho_observations import context, normalize_observation
from app.worker import pentaho_status as legacy

READ_PATHS = {"/kettle/status/", "/kettle/jobStatus/", "/kettle/transStatus/"}


def _reader(configuration, transport=None):
    """Reuse worker-owned TLS, credentials, DNS pinning and both egress policies."""
    import os
    from app.worker.egress import (
        policy_hosts,
        policy_cidrs,
        check_target,
        resolve_target,
    )

    hosts = policy_hosts(
        [
            v.strip()
            for v in os.getenv("OPSCONTROL_LOCAL_ALLOWED_HOSTS", "").split(",")
            if v.strip()
        ]
    )
    nets = policy_cidrs(
        [
            v.strip()
            for v in os.getenv("OPSCONTROL_LOCAL_ALLOWED_CIDRS", "").split(",")
            if v.strip()
        ]
    )
    supplied_hosts = policy_hosts(configuration["allowed_hosts"])
    supplied_nets = policy_cidrs(configuration["allowed_cidrs"])
    if not set(supplied_hosts).issubset(hosts) or not all(
        any(n.subnet_of(local) for local in nets) for n in supplied_nets
    ):
        raise AdapterError("CONFIGURATION", "Carte policy exceeds local egress policy")
    parts, target_nets = check_target(
        configuration["url"], supplied_hosts, configuration["allowed_cidrs"]
    )
    if parts.path not in {"", "/", "/kettle"}:
        raise AdapterError("CONFIGURATION", "Only Carte root URL is supported")
    ip = resolve_target(parts.hostname, target_nets)
    basic = None
    secrets = ()
    if configuration.get("credential_ref"):
        username, password = legacy.resolve_basic_auth(configuration["credential_ref"])
        basic = base64.b64encode((username + ":" + password).encode()).decode()
        secrets = (username, password, basic)
    send = transport or legacy._transport

    def get(path, query):
        if path not in READ_PATHS:
            raise AdapterError(
                "UNSUPPORTED_CAPABILITY", "Carte endpoint is not read-only allowlisted"
            )
        try:
            status, body = send(parts.hostname, ip, path + "?" + query, basic)
        except ssl.SSLCertVerificationError:
            raise AdapterError(
                "TLS", "Carte TLS certificate validation failed"
            ) from None
        except OSError:
            raise AdapterError(
                "NETWORK", "Carte status transport unavailable"
            ) from None
        except legacy.PentahoStatusError:
            raise AdapterError("SCHEMA", "Invalid Carte transport response") from None
        if status in {401, 403}:
            raise AdapterError("AUTHENTICATION", "Carte rejected read credentials")
        if status != 200:
            raise AdapterError("PROVIDER", "Carte status read failed")
        return body

    return get, secrets


def reader(configuration, transport=None):
    from app.worker.egress import EgressDenied
    from app.worker.credentials import CredentialProviderError

    try:
        return _reader(configuration, transport)
    except EgressDenied:
        raise AdapterError(
            "CONFIGURATION", "Carte destination is not approved"
        ) from None
    except CredentialProviderError:
        raise AdapterError(
            "AUTHENTICATION", "Managed Carte credential is unavailable"
        ) from None
    except OSError:
        raise AdapterError("NETWORK", "Carte name resolution unavailable") from None


def xml(body):
    # Reject alternate XML encodings as well as DTD/entity declarations; the
    # old byte check alone does not recognize UTF-16 entity declarations.
    if not isinstance(body, bytes) or len(body) > 65536 or b"\x00" in body:
        raise AdapterError("SCHEMA", "Invalid or oversized Carte XML")
    try:
        body.decode("utf-8-sig")
        return legacy._xml(body)
    except (UnicodeError, legacy.PentahoStatusError):
        raise AdapterError("SCHEMA", "Unsafe or invalid Carte XML") from None


def parse_status(body, cfg, execution_id, observed_at, collect_logs=False, secrets=()):
    cfg = context(cfg)
    root = xml(body)
    allowed = (
        {"job_status", "jobstatus"}
        if cfg["workload_kind"] == "JOB"
        else {"trans_status", "transstatus", "transformation_status"}
    )
    if root.tag.replace("-", "_") not in allowed:
        raise AdapterError("SCHEMA", "Unexpected Carte workload status root")
    native = (root.findtext("id") or "").strip()
    if native != execution_id:
        raise AdapterError(
            "IDENTITY_SCOPE", "Carte returned another execution identity"
        )
    description = (
        root.findtext("status_desc") or root.findtext("status") or ""
    ).strip()
    if not description:
        raise AdapterError("SCHEMA", "Carte status missing")
    error_text = root.findtext("result/nr_errors")
    if error_text is None:
        error_text = root.findtext("nr_errors")
    errors = None
    if error_text is not None:
        if not error_text.isdecimal() or len(error_text) > 7:
            raise AdapterError("SCHEMA", "Invalid Carte error count")
        errors = int(error_text)
    normalized = "UNKNOWN"
    lower = description.casefold()
    if lower in {"running", "initializing", "preparing", "waiting"}:
        normalized = "RUNNING"
    elif lower in {"finished", "completed"} and errors is not None:
        normalized = "FAILED" if errors else "SUCCESS"
    elif lower in {"failed", "error", "finished (with errors)"}:
        normalized = "FAILED"
    # Stopped or unknown descriptions never imply success or failure.
    record = {
        **cfg,
        "native_execution_id": native,
        "observation_id": "status:" + native + ":" + hashlib.sha256(body).hexdigest(),
        "observed_at": observed_at,
        "status": normalized,
        "provider_status": description,
        "nr_errors": errors,
        "started_at": legacy._source_time(root.findtext("start_date")),
        "ended_at": legacy._source_time(root.findtext("end_date")),
    }
    if collect_logs:
        # Compressed/step schemas remain legacy-only until exact-build verified.
        record["logs"] = legacy.safe_text(root.findtext("log_text"), secrets)
    return record


def collect(configuration, checkpoint, customer_id, transport=None):
    cfg = context(configuration["monitoring_context"])
    if not customer_id:
        raise AdapterError(
            "IDENTITY_SCOPE", "Customer-bound collection bridge required"
        )
    if cfg["surface"] != "CARTE":
        raise AdapterError(
            "UNSUPPORTED_CAPABILITY",
            "Server/CLI require authenticated Agent observation transport; no universal Server endpoint is verified",
        )
    previous = dict(checkpoint or {})
    if previous.get("restart_epoch") not in {None, cfg["restart_epoch"]}:
        raise AdapterError(
            "CONTINUITY", "Carte checkpoint epoch changed; reviewed handoff required"
        )
    get, secrets = reader(configuration, transport)
    native = configuration.get("execution_id")
    if not native:
        inventory = xml(get("/kettle/status/", "xml=Y"))
        if inventory.tag.replace("-", "_") not in {"server_status", "serverstatus"}:
            raise AdapterError("SCHEMA", "Unexpected Carte inventory root")
        # Advisory only; no returned names become persistent native job IDs.
        return Batch(
            [],
            {
                "platform": "PENTAHO",
                "surface": "CARTE",
                "read_only": True,
                "persistent_inventory_authoritative": False,
                "runtime_verified": False,
            },
            dict(checkpoint or {}),
            False,
        )
    native = legacy._safe_token(native, "execution id")
    path = (
        "/kettle/jobStatus/"
        if cfg["workload_kind"] == "JOB"
        else "/kettle/transStatus/"
    )
    body = get(
        path,
        "name="
        + quote(configuration["job_name"], safe="")
        + "&id="
        + quote(native, safe="")
        + "&xml=Y",
    )
    body_hash = hashlib.sha256(body).hexdigest()
    if (
        previous.get("status_sha256") == body_hash
        and previous.get("execution_id") == native
    ):
        return Batch(
            [],
            {
                "platform": "PENTAHO",
                "read_only": True,
                "runtime_verified": False,
                "status_unchanged": True,
            },
            previous,
            False,
        )
    observation = parse_status(
        body,
        cfg,
        native,
        datetime.now(timezone.utc).isoformat(),
        configuration.get("collect_logs", False),
        secrets,
    )
    fact = normalize_observation(observation, cfg, customer_id)
    return Batch(
        [fact],
        {
            "platform": "PENTAHO",
            "surface": "CARTE",
            "read_only": True,
            "runtime_verified": False,
            "persistent_inventory_authoritative": False,
        },
        {
            "execution_id": native,
            "restart_epoch": cfg["restart_epoch"],
            "status_sha256": body_hash,
        },
        False,
    )
