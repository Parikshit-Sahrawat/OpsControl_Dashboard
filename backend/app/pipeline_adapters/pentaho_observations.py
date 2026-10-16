"""Read-only R1 observation contract, not a Pentaho launcher or certifier.

The producer observes native evidence. Backend-owned connection context supplies
customer/source scope; untrusted record fields cannot select a different scope.
Server exports are supported as observations, not invented universal Server APIs.
"""

import hashlib
import json
import re
from copy import deepcopy
from .core import AdapterError, execution, instant, redact_provider_record

SURFACES = {"KITCHEN_PAN", "PENTAHO_SERVER", "CARTE"}
CONTEXT_FIELDS = {
    "version",
    "surface",
    "exact_build",
    "authority_id",
    "environment",
    "workload_kind",
    "native_job_id",
    "restart_epoch",
    "host_resource_id",
}


def token(value, label):
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= 300
        or any(ord(c) < 32 or ord(c) == 127 for c in value)
    ):
        raise AdapterError("SCHEMA", "Invalid Pentaho " + label)
    return value


def context(value):
    if not isinstance(value, dict) or set(value) - CONTEXT_FIELDS:
        raise AdapterError("CONFIGURATION", "Unsupported Pentaho monitoring context")
    if value.get("version") != 1 or type(value.get("version")) is not int:
        raise AdapterError("CONFIGURATION", "Pentaho observation version must be 1")
    if value.get("surface") not in SURFACES or value.get("workload_kind") not in {
        "JOB",
        "TRANSFORMATION",
    }:
        raise AdapterError("CONFIGURATION", "Unsupported Pentaho surface/workload")
    build = token(value.get("exact_build"), "exact build")
    # A family, unknown value or successful connection is never an installed build.
    if not re.fullmatch(r"\d+\.\d+\.\d+\.\d+(?:[-+][A-Za-z0-9_.-]+)?", build):
        raise AdapterError(
            "UNVERIFIED_CAPABILITY",
            "Exact installed Pentaho build required; version families are candidates only",
        )
    for key in ("authority_id", "environment", "native_job_id"):
        token(value.get(key), key)
    if value["surface"] == "CARTE":
        token(value.get("restart_epoch"), "Carte restart epoch")
    if value["surface"] == "KITCHEN_PAN":
        token(value.get("host_resource_id"), "host resource")
    return deepcopy(value)


def scoped_identity(customer_id, cfg, native_execution_id, process_start=None):
    """Scope run identity independently of display name, PID and observation time."""
    cfg = context(cfg)
    parts = [
        str(customer_id),
        cfg["surface"],
        cfg["authority_id"],
        cfg["environment"],
        cfg["workload_kind"],
        cfg["native_job_id"],
        token(native_execution_id, "native execution ID"),
    ]
    if cfg["surface"] == "CARTE":
        parts.append(cfg["restart_epoch"])
    elif cfg["surface"] == "KITCHEN_PAN":
        stamp = instant(process_start)
        if not stamp:
            raise AdapterError("SCHEMA", "Process start epoch required")
        parts.extend([cfg["host_resource_id"], stamp])
    return (
        "pentaho-r1:"
        + hashlib.sha256(json.dumps(parts, separators=(",", ":")).encode()).hexdigest()
    )


def normalize_observation(record, cfg, customer_id):
    """Normalize an authenticated observation; identity assertions need live review.

    This neither proves that an Agent observed the asserted native record nor
    certifies its build. The existing independent runtime gate owns that decision.
    """
    cfg = context(cfg)
    if not isinstance(record, dict) or len(json.dumps(record, default=str)) > 65536:
        raise AdapterError("SCHEMA", "Bounded Pentaho observation required")
    for field in (
        "version",
        "surface",
        "exact_build",
        "authority_id",
        "environment",
        "workload_kind",
        "native_job_id",
    ):
        if record.get(field) != cfg[field]:
            raise AdapterError(
                "IDENTITY_SCOPE",
                "Pentaho observation scope/build differs from immutable connection",
            )
    if (
        cfg["surface"] == "CARTE"
        and record.get("restart_epoch") != cfg["restart_epoch"]
    ):
        raise AdapterError(
            "IDENTITY_SCOPE",
            "Carte restart epoch changed; reviewed generation handoff required",
        )
    permitted = CONTEXT_FIELDS | {
        "observed_at",
        "observation_id",
        "native_execution_id",
        "host_resource_id",
        "os",
        "executable_kind",
        "executable_sha256",
        "execution_origin",
        "scheduler_identity",
        "invocation_id",
        "process_start",
        "argv",
        "pid",
        "state",
        "exit_code",
        "result",
        "authority",
        "source_evidence_sha256",
        "status",
        "started_at",
        "ended_at",
        "provider_status",
        "nr_errors",
        "logs",
    }
    if set(record) - permitted:
        raise AdapterError(
            "SCHEMA",
            "Unsupported observation fields; raw commands/credentials are not accepted",
        )
    scheduler = record.get("scheduler_identity")
    if scheduler is not None:
        allowed = {
            "authority_id",
            "native_run_id",
            "native_attempt_id",
            "native_occurrence_id",
            "attempt_order",
            "previous_attempt_id",
            "retry_state",
            "authority_revision",
            "authority_evidence_sha256",
        }
        if (
            not isinstance(scheduler, dict)
            or set(scheduler) - allowed
            or not scheduler.get("authority_id")
        ):
            raise AdapterError(
                "SCHEMA", "Scoped scheduler identity observation required"
            )
        for key, value in scheduler.items():
            if key in {"attempt_order", "authority_revision"}:
                if type(value) is not int or not 1 <= value <= 10000:
                    raise AdapterError(
                        "SCHEMA", "Bounded native scheduler ordinal/revision required"
                    )
            else:
                token(value, key)
        if scheduler.get("retry_state") not in {
            None,
            "PENDING",
            "EXHAUSTED",
            "UNKNOWN",
        }:
            raise AdapterError("SCHEMA", "Unsupported native retry state")
        if scheduler.get("authority_evidence_sha256") is not None and not re.fullmatch(
            r"[a-f0-9]{64}", scheduler["authority_evidence_sha256"]
        ):
            raise AdapterError("SCHEMA", "Native scheduler evidence hash required")
    if record.get("execution_origin", "SCHEDULED") not in {"SCHEDULED", "MANUAL"}:
        raise AdapterError("SCHEMA", "Unsupported execution origin")
    observed = instant(record.get("observed_at"))
    if not observed:
        raise AdapterError("SCHEMA", "Pentaho observation timestamp required")
    observation_id = token(record.get("observation_id"), "observation ID")
    native = token(record.get("native_execution_id"), "native execution ID")
    start = end = None
    status = "UNKNOWN"
    raw = deepcopy(record)
    authority = "EXECUTION_OBSERVATION"
    surface = cfg["surface"]
    if surface == "KITCHEN_PAN":
        if record.get("host_resource_id") != cfg["host_resource_id"] or record.get(
            "os"
        ) not in {"Linux", "Windows"}:
            raise AdapterError(
                "IDENTITY_SCOPE",
                "Supported resource-bound Windows/Linux observation required",
            )
        if not re.fullmatch(r"[a-f0-9]{64}", str(record.get("executable_sha256", ""))):
            raise AdapterError("SCHEMA", "Native executable hash observation required")
        executable = "KITCHEN" if cfg["workload_kind"] == "JOB" else "PAN"
        if (
            record.get("executable_kind") != executable
            or record.get("invocation_id") != native
        ):
            raise AdapterError(
                "IDENTITY_SCOPE", "Verified Kitchen/Pan invocation identity required"
            )
        start = instant(record.get("process_start"))
        if not start:
            raise AdapterError(
                "SCHEMA", "Process start epoch required; PID alone is insufficient"
            )
        for key in ("pid", "exit_code"):
            if key in record and type(record[key]) is not int:
                raise AdapterError("SCHEMA", "Numeric process metadata required")
        argv = raw.pop("argv", None)
        if argv is not None:
            if (
                not isinstance(argv, list)
                or len(argv) > 200
                or not all(isinstance(x, str) for x in argv)
            ):
                raise AdapterError(
                    "SCHEMA", "Bounded command argument evidence required"
                )
            # Never persist raw command arguments (including positional secrets).
            raw["command_evidence"] = {
                "sha256": hashlib.sha256(json.dumps(argv).encode()).hexdigest(),
                "argument_count": len(argv),
            }
        if record.get("state") == "PROCESS_STARTED":
            status = "RUNNING"
        elif record.get("state") not in {"PROCESS_EXITED", "EXECUTION_RESULT"}:
            raise AdapterError("SCHEMA", "Unsupported process observation state")
        # Exit alone conveys process health, never verified workload completion.
        if record.get("state") == "EXECUTION_RESULT":
            result = record.get("result")
            if (
                not isinstance(result, dict)
                or set(result)
                - {"invocation_id", "source", "evidence_sha256", "status", "ended_at"}
                or result.get("invocation_id") != native
                or result.get("source") != "NATIVE_STRUCTURED_LOG"
                or not re.fullmatch(
                    r"[a-f0-9]{64}", str(result.get("evidence_sha256", ""))
                )
            ):
                raise AdapterError(
                    "IDENTITY_SCOPE", "Invocation-bound native result evidence required"
                )
            status = {
                "SUCCESS": "SUCCESS",
                "FAILED": "FAILED",
                "CANCELLED": "CANCELLED",
            }.get(result.get("status"), "UNKNOWN")
            end = instant(result.get("ended_at"))
            if status == "UNKNOWN" or not end:
                raise AdapterError("SCHEMA", "Native result status/end time required")
    elif surface == "PENTAHO_SERVER":
        authority = record.get("authority")
        if authority not in {"REPOSITORY", "SCHEDULER", "EXECUTION_HISTORY"}:
            raise AdapterError("SCHEMA", "Unsupported Server evidence authority")
        if not re.fullmatch(
            r"[a-f0-9]{64}", str(record.get("source_evidence_sha256", ""))
        ):
            raise AdapterError("SCHEMA", "Native Server export evidence hash required")
        # Trigger acceptance/completion is not an ETL execution result.
        if authority == "EXECUTION_HISTORY":
            status = {
                "RUNNING": "RUNNING",
                "SUCCESS": "SUCCESS",
                "FAILED": "FAILED",
                "CANCELLED": "CANCELLED",
            }.get(record.get("status"), "UNKNOWN")
            start, end = instant(record.get("started_at")), instant(
                record.get("ended_at")
            )
    else:
        status = {"RUNNING": "RUNNING", "SUCCESS": "SUCCESS", "FAILED": "FAILED"}.get(
            record.get("status"), "UNKNOWN"
        )
        start, end = instant(record.get("started_at")), instant(record.get("ended_at"))
    identity = scoped_identity(customer_id, cfg, native, record.get("process_start"))
    fact = execution(
        "PENTAHO",
        cfg["native_job_id"],
        identity,
        "UNKNOWN" if status == "CANCELLED" else status,
        start,
        end,
        observed,
        {
            "surface": surface,
            "exact_build": cfg["exact_build"],
            "authority": authority,
            "native_execution_id": native,
            "observation_id": observation_id,
            "native_observation": redact_provider_record(raw),
            "runtime_certified": False,
        },
    )
    # Observation time must remain distinct from execution event time.
    fact["observed_at"] = observed
    fact["native_job_id"] = cfg["native_job_id"]
    fact["event"].update(
        workload_kind=cfg["workload_kind"],
        evidence_authority=authority,
        execution_type=record.get("execution_origin", "SCHEDULED"),
        pentaho_identity={
            "version": 1,
            "invocation_alias": identity,
            "observation_id": observation_id,
            "native_execution_id": native,
            "surface": surface,
            "authority_id": cfg["authority_id"],
            "environment": cfg["environment"],
            "native_job_id": cfg["native_job_id"],
            "workload_kind": cfg["workload_kind"],
            "restart_epoch": cfg.get("restart_epoch"),
            "host_resource_id": cfg.get("host_resource_id"),
            "process_start": record.get("process_start"),
            "scheduler": deepcopy(scheduler),
            "native_outcome": status,
            "native_started_at": start,
            "native_ended_at": end,
            "completion_evidence": status in {"SUCCESS", "FAILED", "CANCELLED"},
        },
    )
    if surface == "PENTAHO_SERVER" and authority != "EXECUTION_HISTORY":
        # Retain non-execution claims but never let them change a projection.
        fact["native_job_id"] = None
    fact["key"] = (
        "PENTAHO:"
        + hashlib.sha256(
            json.dumps(
                [identity, observation_id, raw], sort_keys=True, default=str
            ).encode()
        ).hexdigest()
    )
    return fact


def prepare_records(db, source, records, recovery=False):
    """Optional R1 bridge inside existing acceptance transaction, after fencing.

    All shared reader options already participate in generation-bound equivalence.
    Raw observations cannot bypass normalization by supplying a forged event.
    """
    from app.data_pipelines import service as s
    from app.data_pipelines.models import PipelineConnection, PipelineIntegration

    refs = [m for m in s.methods(db, source) if m.enabled]
    contexts = []
    for method in refs:
        integration = db.get(PipelineIntegration, method.integration_id)
        if integration.platform != "PENTAHO":
            continue
        connection = db.get(PipelineConnection, method.connection_id)
        effective = {
            **connection.configuration,
            **method.configuration.get("adapter_overrides", {}),
        }
        cfg = effective.get("monitoring_context")
        if cfg is None:
            continue
        cfg = method_context(
            integration.platform, source.method_type, source.identity, effective
        )
        if recovery:
            raise AdapterError(
                "UNSUPPORTED_CAPABILITY",
                "R1 native observation replay requires separately verified continuity/range support",
            )
        if cfg["environment"] != integration.environment:
            raise AdapterError(
                "IDENTITY_SCOPE", "Pentaho environment differs from integration"
            )
        if (
            source.method_type == "FILE_LOG"
            and cfg.get("host_resource_id")
            and cfg["host_resource_id"] != source.identity.get("host_resource_id")
        ):
            raise AdapterError(
                "IDENTITY_SCOPE", "Pentaho host differs from canonical source"
            )
        contexts.append(cfg)
    if not contexts:
        if any("pentaho_observation" in r for r in records):
            raise AdapterError(
                "CONFIGURATION", "Versioned Pentaho observation context required"
            )
        return records
    if any(c != contexts[0] for c in contexts):
        raise AdapterError(
            "IDENTITY_SCOPE", "Shared Pentaho observation contexts differ"
        )
    cfg = contexts[0]
    if source.method_type != "FILE_LOG":
        return records  # Backend Carte reader already performs this normalization.
    result = []
    for item in records:
        raw = item.get("pentaho_observation")
        if (
            cfg["surface"] == "KITCHEN_PAN"
            and isinstance(raw, dict)
            and raw.get("os") != source.identity.get("os")
        ):
            raise AdapterError(
                "IDENTITY_SCOPE", "Process OS differs from inherited host OS"
            )
        if not isinstance(raw, dict):
            raise AdapterError(
                "SCHEMA",
                "Raw Pentaho observation required; normalized-event bypass forbidden",
            )
        fact = normalize_observation(raw, cfg, source.organization_id)
        result.append(
            {
                **{
                    k: v
                    for k, v in item.items()
                    if k
                    in {
                        "key",
                        "evidence_origin",
                        "runtime_origin",
                        "reader_definition_hash",
                    }
                },
                **fact,
                "key": item["key"],
                "evidence": {
                    **fact["evidence"],
                    "source_path": item.get("evidence", {}).get("source_path"),
                    "byte_offset": item.get("evidence", {}).get("byte_offset"),
                },
            }
        )
        # Avoid preserving raw argv from the wire alongside the sanitized fact.
        result[-1].pop("pentaho_observation", None)
    return result


def method_context(platform, method_type, identity, configuration):
    if platform != "PENTAHO" or "monitoring_context" not in configuration:
        return None
    cfg = context(configuration["monitoring_context"])
    expected = "PLATFORM_API" if cfg["surface"] == "CARTE" else "FILE_LOG"
    if method_type != expected:
        raise AdapterError(
            "UNSUPPORTED_CAPABILITY",
            "Pentaho surface requires " + expected + " transport",
        )
    if (
        method_type == "FILE_LOG"
        and cfg.get("host_resource_id")
        and cfg["host_resource_id"] != identity.get("host_resource_id")
    ):
        raise AdapterError(
            "IDENTITY_SCOPE", "Pentaho host differs from canonical source"
        )
    return cfg


def proof_matches(cfg, profile, proof):
    """Extra exact-build/surface check; never a replacement for existing gates."""
    try:
        cfg = context(cfg)
    except (AdapterError, TypeError, ValueError):
        return False
    evidence = proof.payload.get("evidence", {}) if proof else {}
    if not isinstance(evidence, dict):
        return False
    return bool(
        profile
        and profile.platform_version == cfg["exact_build"]
        and evidence.get("exact_build") == cfg["exact_build"]
        and evidence.get("surface") == cfg["surface"]
    )
