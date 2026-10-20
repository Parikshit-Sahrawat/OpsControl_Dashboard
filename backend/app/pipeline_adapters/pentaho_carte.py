"""Opt-in R1 Carte GET reader. No persistent job discovery or control APIs."""

import base64
import hashlib
import ssl
from datetime import datetime, timezone
from urllib.parse import quote
from .core import AdapterError, Batch, step_event
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
    try:
        steps = (
            legacy._transformation_steps(root, secrets)
            if cfg["workload_kind"] == "TRANSFORMATION"
            else []
        )
        normalized, errors, indicator, exit_status, warnings = legacy._native_result(
            root,
            description,
            cfg["workload_kind"],
            any(row["nr_errors"] is not None and row["nr_errors"] > 0 for row in steps),
        )
    except legacy.PentahoStatusError:
        raise AdapterError("SCHEMA", "Invalid Carte native result") from None
    record = {
        **cfg,
        "native_execution_id": native,
        "observation_id": "status:" + native + ":" + hashlib.sha256(body).hexdigest(),
        "observed_at": observed_at,
        "status": normalized,
        "provider_status": description,
        "nr_errors": errors,
        "native_result": indicator,
        "native_exit_status": exit_status,
        "native_log_channel_id": (
            legacy.safe_text(root.findtext("result/log_channel_id"), secrets).strip()[
                :200
            ]
            or None
        ),
        "native_log_date_raw": (
            legacy.safe_text(root.findtext("log_date"), secrets).strip()[:100] or None
        ),
        "evidence_warnings": warnings,
        "native_steps": steps,
        "started_at": legacy._source_time(root.findtext("start_date")),
        "ended_at": legacy._source_time(root.findtext("end_date")),
    }
    if collect_logs:
        plain = root.findtext("log_text")
        if plain is not None:
            record["logs"] = legacy.safe_text(plain, secrets)
            record["log_evidence_status"] = "AVAILABLE"
        else:
            record["logs"], record["log_evidence_status"] = legacy._decoded_log(
                root.findtext("logging_string"), secrets
            )
    return record


def _facts(body, cfg, native, customer_id, collect_logs, secrets):
    observation = parse_status(
        body, cfg, native, datetime.now(timezone.utc).isoformat(), collect_logs, secrets
    )
    parent = normalize_observation(observation, cfg, customer_id)
    facts = [parent]
    occurrences = {}
    for row in observation["native_steps"]:
        # Position and native copy distinguish observed rows; neither is a
        # native child execution UUID or a stable invocation identity.
        pair = (row["name"], row.get("copy"))
        ordinal = occurrences.get(pair, 0)
        occurrences[pair] = ordinal + 1
        step_id = (
            "observed-step:"
            + hashlib.sha256(repr((pair, ordinal)).encode()).hexdigest()
        )
        facts.append(
            step_event("PENTAHO", parent, row, step_id, row["name"], row["status"])
        )
    return facts


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
    path = (
        "/kettle/jobStatus/"
        if cfg["workload_kind"] == "JOB"
        else "/kettle/transStatus/"
    )

    def detail(identity):
        return get(
            path,
            "name="
            + quote(configuration["job_name"], safe="")
            + "&id="
            + quote(identity, safe="")
            + "&xml=Y",
        )

    native = configuration.get("execution_id")
    if not native:
        inventory = xml(get("/kettle/status/", "xml=Y"))
        if inventory.tag.replace("-", "_") not in {"server_status", "serverstatus"}:
            raise AdapterError("SCHEMA", "Unexpected Carte inventory root")
        try:
            entries = legacy._inventory_entries(
                inventory, cfg["workload_kind"], configuration["job_name"]
            )
        except legacy.PentahoStatusError:
            raise AdapterError("SCHEMA", "Invalid Carte inventory identity") from None
        prior_hashes = previous.get("inventory_hashes", {})
        if not isinstance(prior_hashes, dict) or len(prior_hashes) > 200:
            prior_hashes = {}
        hashes = {}
        facts = []
        for identity, inventory_status in entries:
            body = detail(identity)
            body_hash = hashlib.sha256(body).hexdigest()
            hashes[identity] = body_hash
            if prior_hashes.get(identity) == body_hash:
                continue
            observations = _facts(
                body,
                cfg,
                identity,
                customer_id,
                configuration.get("collect_logs", False),
                secrets,
            )
            native_status = observations[0]["evidence"]["native_observation"][
                "provider_status"
            ]
            if inventory_status and native_status != inventory_status:
                observations[0]["evidence"]["inventory_status_desc"] = inventory_status
            facts.extend(observations)
        return Batch(
            facts,
            {
                "platform": "PENTAHO",
                "surface": "CARTE",
                "read_only": True,
                "persistent_inventory_authoritative": False,
                "runtime_verified": False,
                "inventory_complete": False,
                "observed_execution_count": len(entries),
            },
            (
                {"restart_epoch": cfg["restart_epoch"], "inventory_hashes": hashes}
                if entries
                else previous
            ),
            False,
        )
    native = legacy._safe_token(native, "execution id")
    body = detail(native)
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
    facts = _facts(
        body,
        cfg,
        native,
        customer_id,
        configuration.get("collect_logs", False),
        secrets,
    )
    return Batch(
        facts,
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
