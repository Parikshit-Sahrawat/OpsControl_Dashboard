"""Fenced V1.6 transactions. A source lock serializes commits, holds and handoffs."""

from fastapi import HTTPException
import hashlib
import json
import posixpath
import uuid
from copy import deepcopy
from datetime import timedelta
from urllib.parse import urlsplit, urlunsplit
from sqlalchemy import select, func
from app.data_pipelines.models import (
    PipelineAssociation,
    PipelineCapability,
    PipelineConnection,
    PipelineEvidence,
    PipelineHold,
    PipelineIntegration,
    PipelineJob,
    PipelineMethod,
    PipelineOperation,
    PipelineSource,
)
from app.pipeline_adapters.core import redact_provider_record
from app.security.audit import log_event

METHODS = {"PLATFORM_API", "FILE_LOG", "DATABASE"}
RECOVERY_BOUNDS = {
    "PLATFORM_API": 86400,
    "FILE_LOG": 21600,
    "DATABASE": 86400,
}
PLATFORMS = {
    "PENTAHO",
    "IICS",
    "AIRFLOW",
    "NIFI",
    "ADF",
    "AWS_GLUE",
    "SSIS",
    "TALEND",
    "CUSTOM",
}


class PipelineError(HTTPException):
    def __init__(self, code):
        self.code = code
        super().__init__(409, {"code": code})


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def bounded(value, maximum=65536, organization_id=None):
    if not isinstance(value, dict) or len(json.dumps(value, default=str)) > maximum:
        raise PipelineError("CONFIGURATION_LIMIT")

    def inspect(item):
        if isinstance(item, dict):
            for key, child in item.items():
                if key.lower() in {
                    "password",
                    "token",
                    "access_token",
                    "secret",
                    "authorization",
                    "connection_string",
                }:
                    raise PipelineError("MANAGED_SECRET_REFERENCE_REQUIRED")
                if key == "profile_name" and organization_id is not None:
                    prefix = (
                        "opsc-pipeline-" + uuid.UUID(str(organization_id)).hex + "-"
                    )
                    if (
                        not isinstance(child, str)
                        or not child.startswith(prefix)
                        or len(child) <= len(prefix)
                    ):
                        raise PipelineError("CUSTOMER_BOUND_AWS_PROFILE_REQUIRED")
                if key.endswith("_ref") and child:
                    from app.telemetry.configuration import env_reference

                    try:
                        env_reference(child)
                        prefix = "env:OPSCONTROL_PIPELINE_SECRET_"
                        if organization_id is not None:
                            prefix += uuid.UUID(str(organization_id)).hex.upper() + "_"
                        if not child.startswith(prefix) or len(child) <= len(prefix):
                            raise ValueError("Customer-bound pipeline secret required")
                    except ValueError:
                        raise PipelineError("INVALID_SECRET_REFERENCE") from None
                inspect(child)
        elif isinstance(item, list):
            for child in item:
                inspect(child)

    inspect(value)
    return deepcopy(value)


def is_sample_evidence(value, depth=0):
    """Explicit fixture labels cannot become genuine-runtime attestation."""
    if depth > 20:
        return True
    if isinstance(value, dict):
        if value.get("fixture_state") or str(
            value.get("evidence_origin", "")
        ).upper() in {"CONTROLLED", "CONTROLLED_FIXTURE", "SAMPLE"}:
            return True
        for key, child in value.items():
            if key == "redacted_json" and isinstance(child, str):
                try:
                    child = json.loads(child)
                except (TypeError, ValueError):
                    continue
            if is_sample_evidence(child, depth + 1):
                return True
    elif isinstance(value, list):
        return any(is_sample_evidence(child, depth + 1) for child in value)
    return False


def canonical(method_type, identity):
    if method_type not in METHODS:
        raise PipelineError("UNSUPPORTED_METHOD")
    allowed = (
        {"host_resource_id", "path", "os"}
        if method_type == "FILE_LOG"
        else {"platform", "endpoint", "account", "physical_scope"}
    )
    if (
        not isinstance(identity, dict)
        or set(identity) != allowed
        or any(not isinstance(v, str) or not v.strip() for v in identity.values())
    ):
        raise PipelineError("CANONICAL_IDENTITY_REQUIRED")
    result = {k: v.strip() for k, v in identity.items()}
    if method_type == "FILE_LOG":
        try:
            result["host_resource_id"] = str(uuid.UUID(result["host_resource_id"]))
        except ValueError:
            raise PipelineError("HOST_RESOURCE_UUID_REQUIRED") from None
        if result["os"] not in {"Windows", "Linux"}:
            raise PipelineError("HOST_OS_REQUIRED")
        path = result["path"].replace("\\", "/")
        if not (
            path.startswith("/")
            or (result["os"] == "Windows" and len(path) > 2 and path[1:3] == ":/")
        ) or ".." in path.split("/"):
            raise PipelineError("ABSOLUTE_SAFE_PATH_REQUIRED")
        result["path"] = posixpath.normpath(path)
        if result["os"] == "Windows":
            result["path"] = result["path"].casefold()
    else:
        if result["platform"] not in PLATFORMS:
            raise PipelineError("PLATFORM_REQUIRED")
        p = urlsplit(result["endpoint"])
        if (
            p.scheme
            not in ({"mssql", "sqlserver"} if method_type == "DATABASE" else {"https"})
            or not p.hostname
            or p.username
            or p.password
            or p.query
            or p.fragment
        ):
            raise PipelineError("CREDENTIAL_FREE_TLS_ENDPOINT_REQUIRED")
        result["endpoint"] = urlunsplit(
            (
                p.scheme,
                p.hostname.lower()
                + ((":" + str(p.port)) if p.port and p.port != 443 else ""),
                p.path.rstrip("/"),
                "",
                "",
            )
        )
    return result, digest([method_type, result])


def validate_reader_target(platform, method_type, identity, configuration):
    from app.pipeline_adapters.pentaho_observations import method_context
    from app.pipeline_adapters.core import AdapterError

    try:
        method_context(platform, method_type, identity, configuration)
    except AdapterError as error:
        raise PipelineError("PENTAHO_" + error.kind) from None
    if method_type != "PLATFORM_API" or platform in {"SSIS", "CUSTOM"}:
        return
    endpoint = configuration.get("base_url") or configuration.get("url")
    if platform == "AWS_GLUE":
        region = configuration.get("region", "")
        suffix = "amazonaws.com.cn" if region.startswith("cn-") else "amazonaws.com"
        endpoint = "https://glue." + region + "." + suffix
        if not region or identity.get("physical_scope") != "region:" + region:
            raise PipelineError("GLUE_REGION_SCOPE_MISMATCH")
    if (
        not endpoint
        or canonical("PLATFORM_API", {**identity, "endpoint": endpoint})[0]["endpoint"]
        != identity["endpoint"]
    ):
        raise PipelineError("CANONICAL_READER_DESTINATION_MISMATCH")


def clock(db):
    return db.scalar(select(func.clock_timestamp()))


def locked_source(db, source_id):
    # SessionLocal disables autoflush. Persist this transaction's own pending
    # handoff fields before refreshing the locked row, without committing them.
    db.flush()
    row = db.scalar(
        select(PipelineSource)
        .where(PipelineSource.id == source_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if row is None:
        raise PipelineError("SOURCE_UNAVAILABLE")
    return row


def event(db, row, action, actor_id=None):
    log_event(
        db,
        event_type="PIPELINE_" + action,
        outcome="SUCCESS",
        actor_id=actor_id,
        organization_id=row.organization_id,
        target_type=type(row).__name__,
        target_id=row.id,
    )


def methods(db, source):
    return list(
        db.scalars(
            select(PipelineMethod)
            .where(
                PipelineMethod.source_id == source.id,
                PipelineMethod.validation != "RETIRED",
            )
            .execution_options(populate_existing=True)
        ).all()
    )


def suspended(db, source):
    from app.models import Organization

    customer = db.get(Organization, source.organization_id)
    if not customer or not customer.active:
        return True
    if db.scalar(
        select(PipelineHold.id)
        .where(
            PipelineHold.source_id == source.id,
            PipelineHold.released_at.is_(None),
            PipelineHold.kind != "LEGAL",
        )
        .limit(1)
    ):
        return True
    refs = methods(db, source)
    if not refs:
        return True
    for method in refs:
        integration = db.get(PipelineIntegration, method.integration_id)
        if (
            integration is None
            or not integration.enabled
            or integration.deleted_at is not None
        ):
            return True
    return False


def reader_definition(db, method):
    source = db.get(PipelineSource, method.source_id)
    connection = db.get(PipelineConnection, method.connection_id)
    return digest(
        [
            source.canonical_key,
            connection.configuration,
            method.transport,
            method.configuration.get("method_type"),
            method.configuration.get("adapter_overrides", {}),
            method.configuration.get("native_identity_field"),
        ]
    )


def reader_contract(db, source, method):
    """Conservative equivalence: unknown reader options must never be ignored.

    Connection versions may differ, but their effective settings, credential
    references and checkpoint interpretation must agree. Poll cadence is the
    only excluded setting; it does not change the returned evidence or cursor.
    """
    integration = db.get(
        PipelineIntegration, method.integration_id, populate_existing=True
    )
    connection = db.get(
        PipelineConnection, method.connection_id, populate_existing=True
    )
    if (
        not integration
        or not connection
        or connection.integration_id != integration.id
        or connection.organization_id != source.organization_id
        or integration.organization_id != source.organization_id
        or method.organization_id != source.organization_id
    ):
        raise PipelineError("SHARED_SOURCE_READER_CONFLICT")
    return digest(
        {
            "contract_version": 1,
            "customer": str(source.organization_id),
            "canonical_key": source.canonical_key,
            "physical_identity": source.identity,
            "method_type": source.method_type,
            "platform": integration.platform,
            "transport": method.transport,
            "connection": connection.configuration,
            "effective_connection": {
                **connection.configuration,
                **method.configuration.get("adapter_overrides", {}),
            },
            "reader_options": {
                k: v for k, v in method.configuration.items() if k != "interval_seconds"
            },
            "checkpoint_contract": [integration.platform, source.method_type, 1],
        }
    )


def reader_equivalence(db, source, persist=False):
    """Validate every active binding against a durable generation contract.

    Writers call this under the canonical source lock. The existing operation
    table stores the immutable hash, so no schema change or secret copy is needed.
    A reader change requires a new generation through the reviewed handoff API.
    """
    refs = [m for m in methods(db, source) if m.enabled]
    hashes = {reader_contract(db, source, m) for m in refs}
    if len(hashes) > 1:
        raise PipelineError("SHARED_SOURCE_READER_CONFLICT")
    if not hashes:
        return None
    reader_hash = hashes.pop()
    key = f"{source.id}:{source.generation}"
    saved = db.scalar(
        select(PipelineOperation).where(
            PipelineOperation.organization_id == source.organization_id,
            PipelineOperation.kind == "READER_CONTRACT",
            PipelineOperation.idempotency_key == key,
        )
    )
    if saved and saved.configuration.get("reader_hash") != reader_hash:
        raise PipelineError("SHARED_SOURCE_READER_CONFLICT")
    if persist and not saved:
        principal = db.info.get("opscontrol_principal")
        saved, _ = operation(
            db,
            source.organization_id,
            "READER_CONTRACT",
            key,
            {"reader_hash": reader_hash, "contract_version": 1},
            principal.user_id if principal else None,
            source_id=source.id,
        )
        saved.state = "COMPLETE"
    return reader_hash


def eligible(db, method):
    profile = db.get(PipelineCapability, method.capability_id)
    connection = db.get(PipelineConnection, method.connection_id)
    integration = db.get(PipelineIntegration, method.integration_id)
    proof = (
        db.get(PipelineEvidence, profile.verification_evidence_id)
        if profile and profile.verification_evidence_id
        else None
    )
    source = db.get(PipelineSource, method.source_id)
    if integration and integration.platform == "PENTAHO" and connection:
        cfg = {
            **connection.configuration,
            **method.configuration.get("adapter_overrides", {}),
        }
        if "monitoring_context" in cfg:
            from app.pipeline_adapters.pentaho_observations import (
                proof_matches,
                method_context,
            )
            from app.pipeline_adapters.core import AdapterError

            try:
                ctx = method_context(
                    integration.platform,
                    method.configuration.get("method_type"),
                    source.identity if source else {},
                    cfg,
                )
            except AdapterError:
                return False
            if ctx["environment"] != integration.environment or not proof_matches(
                ctx, profile, proof
            ):
                return False
    return bool(
        proof
        and proof.payload.get("reader_definition_hash") == reader_definition(db, method)
        and source
        and proof.source_id == source.id
        and proof.generation == source.generation
        and proof.outcome == "ACCEPTED"
        and proof.payload.get("runtime_origin") == "AUTHENTICATED_RUNTIME"
        and method.enabled
        and method.validation == "VALID"
        and integration
        and integration.deleted_at is None
        and profile
        and profile.integration_id == integration.id
        and profile.compatibility in {"SUPPORTED", "CONDITIONAL"}
        and profile.evidence_status == "RUNTIME_VERIFIED"
        and profile.verification_evidence_id
        and method.source_id
        and connection
        and connection.active
        and connection.integration_id == integration.id
        and method.configuration.get("method_type")
        in profile.definition.get("supported_methods", [])
    )


def acquire(db, source_id, owner_id, lease_seconds=60, verification=False):
    if not 5 <= lease_seconds <= 120:
        raise PipelineError("LEASE_BOUND")
    source = locked_source(db, source_id)
    reader_equivalence(db, source, persist=True)
    current = clock(db)
    if suspended(db, source):
        raise PipelineError("SOURCE_SUSPENDED")
    if not source.continuity_validated:
        raise PipelineError("CONTINUITY_NOT_VERIFIED")
    if not any(m.enabled for m in methods(db, source)):
        raise PipelineError("NO_ENABLED_METHODS")
    if not verification and not all(
        eligible(db, m) for m in methods(db, source) if m.enabled
    ):
        raise PipelineError("CAPABILITY_NOT_RUNTIME_VERIFIED")
    if source.lease_until and source.lease_until > current:
        raise PipelineError("SOURCE_ALREADY_OWNED")
    source.fence += 1
    source.lease_mode = "VERIFY" if verification else "LIVE"
    source.owner_id = owner_id
    source.lease_until = current + timedelta(seconds=lease_seconds)
    return {
        "source_id": str(source.id),
        "generation": str(source.generation),
        "fence": source.fence,
        "owner_id": str(owner_id),
        "lease_mode": source.lease_mode,
        "checkpoint": deepcopy(source.live_checkpoint),
        "lease_until": source.lease_until.isoformat(),
    }


def check_ticket(db, source, ticket):
    if (
        str(source.id) != ticket.get("source_id")
        or str(source.generation) != ticket.get("generation")
        or source.fence != ticket.get("fence")
        or str(source.owner_id) != ticket.get("owner_id")
        or source.lease_mode != ticket.get("lease_mode", "LIVE")
        or not source.lease_until
        or source.lease_until <= clock(db)
    ):
        raise PipelineError("STALE_OWNER_OR_GENERATION")
    reader_equivalence(db, source)
    if suspended(db, source):
        raise PipelineError("SOURCE_SUSPENDED")
    if source.lease_mode != "VERIFY" and not all(
        eligible(db, m) for m in methods(db, source) if m.enabled
    ):
        raise PipelineError("CAPABILITY_NOT_RUNTIME_VERIFIED")


def projected_records(fact, resource, source_id):
    original = dict(fact["event"])
    original["provider_jobchain"] = original.get("jobchain")
    original["jobchain"] = resource.configuration["jobchain"]
    record = {**fact, "event": original, "source_id": str(source_id)}
    records = [record]
    if (
        not original.get("pentaho_identity")
        and original.get("started_at")
        and original.get("event_type")
        not in {
            "START",
            "STEP_START",
        }
    ):
        step = str(original.get("event_type", "")).startswith("STEP")
        records.append(
            {
                **record,
                "key": fact["key"] + ":start",
                "observed_at": original["started_at"],
                "event": {
                    **original,
                    "event_type": "STEP_START" if step else "START",
                    "status": "RUNNING",
                    "timestamp": original["started_at"],
                    "ended_at": None,
                    "terminal_status_observed": False,
                    "timestamp_provenance": "SOURCE",
                },
            }
        )
    return records


def validate_checkpoint(source, checkpoint, previous=None):
    bounded(checkpoint)
    if source.method_type != "FILE_LOG":
        return
    import fnmatch

    entries = checkpoint.get("sources")
    if not isinstance(entries, dict) or len(entries) > 100:
        raise PipelineError("FILE_CHECKPOINT_SCHEMA_REQUIRED")
    pattern = source.identity["path"]
    windows = source.identity.get("os") == "Windows"
    for path, cursor in entries.items():
        candidate = path.replace("\\", "/") if isinstance(path, str) else ""
        if not candidate or not fnmatch.fnmatchcase(
            candidate.casefold() if windows else candidate,
            pattern.casefold() if windows else pattern,
        ):
            raise PipelineError("FILE_CHECKPOINT_OUTSIDE_SOURCE")
        if not isinstance(cursor, dict) or any(
            type(cursor.get(key)) is not int or cursor[key] < 0
            for key in ("device", "inode", "offset")
        ):
            raise PipelineError("FILE_CHECKPOINT_INVALID_POSITION")
        old = (previous or {}).get("sources", {}).get(path)
        if old and (
            old.get("inode") != cursor["inode"]
            or old.get("device") != cursor["device"]
            or cursor["offset"] < old.get("offset", 0)
        ):
            raise PipelineError("SOURCE_GENERATION_OR_CURSOR_REGRESSION")


def accept(db, ticket, records, checkpoint, complete, recovery_operation=None):
    """Caller commits once. Any exception rolls back evidence, projection and cursor."""
    source = locked_source(db, uuid.UUID(ticket["source_id"]))
    check_ticket(db, source, ticket)
    validate_checkpoint(
        source,
        checkpoint,
        source.recovery_checkpoint if recovery_operation else source.live_checkpoint,
    )
    if (
        not isinstance(records, list)
        or len(records) > 10000
        or len(json.dumps(records, default=str)) > 8 * 1024 * 1024
    ):
        raise PipelineError("EVIDENCE_BATCH_LIMIT")
    from app.pipeline_adapters.pentaho_observations import prepare_records
    from app.pipeline_adapters.core import AdapterError

    if any(
        not isinstance(r, dict) or not isinstance(r.get("key"), str) for r in records
    ):
        raise PipelineError("STABLE_EVIDENCE_ID_REQUIRED")
    try:
        records = prepare_records(
            db, source, records, recovery=recovery_operation is not None
        )
    except (AdapterError, ValueError, TypeError) as error:
        raise PipelineError("PENTAHO_" + getattr(error, "kind", "SCHEMA")) from None
    if recovery_operation:
        if (
            recovery_operation.state != "RUNNING"
            or recovery_operation.lease_until <= clock(db)
        ):
            raise PipelineError("RECOVERY_CLAIM_EXPIRED")
        if recovery_operation.configuration.get("generation") != str(source.generation):
            raise PipelineError("RECOVERY_GENERATION_CHANGED")
    accepted = quarantined = 0
    projections = {}
    from app.unified.models import MonitoringResource
    from app.models import CollectorRun

    for item in records:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("key"), str)
            or not 1 <= len(item["key"]) <= 500
            or not isinstance(item.get("event"), dict)
        ):
            raise PipelineError("STABLE_EVIDENCE_ID_REQUIRED")
        key = item["key"]
        previous = db.scalar(
            select(PipelineEvidence).where(
                PipelineEvidence.source_id == source.id,
                PipelineEvidence.generation == source.generation,
                PipelineEvidence.external_key == key,
            )
        )
        if previous:
            if (
                previous.payload.get("payload_sha256")
                if previous.payload.get("raw_retired")
                else digest(previous.payload)
            ) != digest(redact_provider_record(item)):
                raise PipelineError("IDEMPOTENCY_PAYLOAD_MISMATCH")
            continue
        native = item.get("native_job_id")
        links = (
            db.execute(
                select(PipelineJob, PipelineMethod)
                .join(PipelineAssociation, PipelineAssociation.job_id == PipelineJob.id)
                .join(
                    PipelineMethod, PipelineMethod.id == PipelineAssociation.method_id
                )
                .join(
                    PipelineIntegration,
                    PipelineIntegration.id == PipelineMethod.integration_id,
                )
                .where(
                    PipelineMethod.source_id == source.id,
                    PipelineAssociation.generation == source.generation,
                    PipelineMethod.enabled.is_(True),
                    PipelineIntegration.enabled.is_(True),
                    PipelineJob.native_id == native,
                    PipelineJob.selected.is_(True),
                    PipelineJob.quarantined.is_(False),
                )
            ).all()
            if native
            else []
        )
        resources = {
            job.resource_id: job for job, method in links if job.resource_id is not None
        }
        if len(resources) > 1:
            resources = {}  # identical native ID with conflicting targets is ambiguous
        clean = redact_provider_record(item)
        observed = item.get("observed_at") or item["event"].get("timestamp")
        try:
            from datetime import datetime

            stamp = datetime.fromisoformat(observed.replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                raise ValueError()
        except (AttributeError, ValueError, TypeError):
            raise PipelineError("SOURCE_TIMESTAMP_REQUIRED") from None
        outcome = "ACCEPTED" if resources else "QUARANTINED_IDENTITY"
        evidence = PipelineEvidence(
            organization_id=source.organization_id,
            source_id=source.id,
            generation=source.generation,
            external_key=key,
            native_job_id=native,
            payload=clean,
            outcome=outcome,
            observed_at=stamp,
        )
        db.add(evidence)
        db.flush()
        if not resources:
            quarantined += 1
        for resource_id, job in resources.items():
            resource = db.get(MonitoringResource, resource_id)
            if (
                not resource
                or resource.domain != "ETL"
                or resource.organization_id != source.organization_id
            ):
                raise PipelineError("RESOURCE_SCOPE_CHANGED")
            # Raw provider records belong only to the 30-day evidence store.
            # Historical V1.5 projections keep normalized events and references.
            event_payload = dict(clean["event"])
            # Trust comes from the current independently approved method profile,
            # never a producer-provided verified boolean or a VERIFY lease.
            from app.unified.pentaho_execution import verified_projection

            event_payload = verified_projection(
                db, source, event_payload, links, evidence.id
            )
            fact = {
                "native_job_id": native,
                "event": event_payload,
                "evidence": {
                    "semantics": clean.get("evidence", {}).get("semantics"),
                    "v16_evidence_id": str(evidence.id),
                    "source_id": str(source.id),
                    "payload_sha256": digest(clean),
                },
                "key": "v16:" + str(evidence.id),
                "observed_at": stamp.isoformat(),
            }
            projections.setdefault(resource_id, []).extend(
                projected_records(fact, resource, source.id)
            )
        accepted += 1
    # Retrying an identical batch never repeats projected evidence.
    observed = clock(db)
    if complete:
        covered = checkpoint.get("_covered_native_ids")
        quiet = (
            db.execute(
                select(PipelineJob.resource_id)
                .join(PipelineAssociation, PipelineAssociation.job_id == PipelineJob.id)
                .join(
                    PipelineMethod, PipelineMethod.id == PipelineAssociation.method_id
                )
                .where(
                    PipelineMethod.source_id == source.id,
                    PipelineAssociation.generation == source.generation,
                    PipelineMethod.enabled.is_(True),
                    PipelineJob.selected.is_(True),
                    PipelineJob.native_id.in_(covered) if covered is not None else True,
                    PipelineJob.quarantined.is_(False),
                )
            )
            .scalars()
            .all()
        )
        for rid in quiet:
            if rid:
                projections.setdefault(rid, [])
    for rid, facts in projections.items():
        resource = db.get(MonitoringResource, rid)
        if not resource.primary_collector_id:
            raise PipelineError("RESOURCE_COMPATIBILITY_BINDING_REQUIRED")
        db.add(
            CollectorRun(
                collector_id=resource.primary_collector_id,
                started_at=observed,
                ended_at=observed,
                status="SUCCESS",
                outcome="SUCCESS",
                source_metadata={
                    "inventory_complete": bool(complete),
                    "provider": resource.configuration.get("platform"),
                    "resource_id": str(resource.id),
                    "record_count": len(facts),
                    "execution_records": facts,
                    "v16_source_id": str(source.id),
                    "generation": str(source.generation),
                },
            )
        )
    receipt, _ = operation(
        db,
        source.organization_id,
        "ACCEPTANCE",
        digest(
            [
                str(source.id),
                str(source.generation),
                records,
                checkpoint,
                bool(complete),
                str(recovery_operation.id) if recovery_operation else None,
            ]
        ),
        {
            "source_id": str(source.id),
            "generation": str(source.generation),
            "checkpoint_hash": digest(checkpoint),
        },
        None,
        source_id=source.id,
    )
    receipt.state = "COMPLETE"
    receipt.result = {"accepted": accepted, "quarantined": quarantined}
    db.flush()  # constraints/evidence durability precede cursor advancement in this transaction
    check_ticket(db, source, ticket)
    if recovery_operation:
        source.recovery_checkpoint = deepcopy(checkpoint)
    else:
        source.live_checkpoint = deepcopy(checkpoint)
    source.revision += 1
    source.last_observed_at = observed
    source.next_run_at = observed + timedelta(
        seconds=min(
            (
                m.configuration.get("interval_seconds", 60)
                for m in methods(db, source)
                if m.enabled
            ),
            default=60,
        )
    )
    if accepted:
        source.last_received_at = observed
    source.health = "DEGRADED" if quarantined else ("RECEIVING" if accepted else "IDLE")
    source.lease_until = observed  # yield ownership; next claim receives a higher fence
    if source.lease_mode == "VERIFY":
        verify = db.scalar(
            select(PipelineOperation).where(
                PipelineOperation.source_id == source.id,
                PipelineOperation.kind == "VERIFY",
                PipelineOperation.state == "RUNNING",
            )
        )
        if verify and accepted and not quarantined:
            verify.state = "COMPLETE"
            verify.result = {
                "accepted_native_evidence": accepted,
                "generation": str(source.generation),
                "genuine_runtime_attestation_required": True,
            }
    return {
        "accepted": accepted,
        "quarantined": quarantined,
        "generation": str(source.generation),
        "fence": source.fence,
    }


def hold(db, source_id, kind, reference, actor_id=None):
    source = locked_source(db, source_id)
    row = db.scalar(
        select(PipelineHold).where(
            PipelineHold.source_id == source.id,
            PipelineHold.kind == kind,
            PipelineHold.reference == reference,
        )
    )
    if not row:
        row = PipelineHold(
            organization_id=source.organization_id,
            source_id=source.id,
            kind=kind,
            reference=reference,
            actor_id=actor_id,
        )
        db.add(row)
    elif row.released_at is None:
        return (
            row  # reference holds are idempotent; reconciliation does not churn fences
        )
    elif row.released_at is not None:
        row.released_at = None
        row.released_by = None
        row.actor_id = actor_id
        row.created_at = clock(db)
    if kind != "LEGAL":
        source.health = "SUSPENDED"
        source.fence += 1
        source.owner_id = None
        source.lease_until = None
        source.continuity_validated = False
    event(db, source, "HOLD_ADD", actor_id)
    return row


def release_hold(db, hold_id, actor_id):
    row = db.get(PipelineHold, hold_id)
    if not row:
        raise PipelineError("HOLD_UNAVAILABLE")
    source = locked_source(db, row.source_id)
    if row.kind == "LEGAL" and (actor_id is None or row.actor_id == actor_id):
        raise PipelineError("INDEPENDENT_LEGAL_RELEASE_REQUIRED")
    if row.kind != "LEGAL" and not source.continuity_validated:
        raise PipelineError("CONTINUITY_NOT_VERIFIED")
    row.released_at = clock(db)
    row.released_by = actor_id
    event(db, source, "HOLD_RELEASE", actor_id)


def pause(db, integration, actor_id):
    integration.enabled = False
    integration.revision += 1
    for sid in sorted(
        set(
            db.scalars(
                select(PipelineMethod.source_id).where(
                    PipelineMethod.integration_id == integration.id
                )
            ).all()
        ),
        key=str,
    ):
        hold(db, sid, "INTEGRATION", str(integration.id), actor_id)
    event(db, integration, "SUSPEND", actor_id)


def blockers(db, integration):
    issues = []
    if integration.vm_resource_id:
        from app.unified.models import MonitoringResource

        parent = db.get(MonitoringResource, integration.vm_resource_id)
        if (
            not parent
            or parent.domain != "VM"
            or parent.organization_id != integration.organization_id
            or parent.environment != integration.environment
        ):
            issues.append("COMPUTE_INHERITANCE_CHANGED")
    refs = list(
        db.scalars(
            select(PipelineMethod).where(
                PipelineMethod.integration_id == integration.id,
                PipelineMethod.enabled.is_(True),
                PipelineMethod.validation != "RETIRED",
            )
        ).all()
    )
    jobs = list(
        db.scalars(
            select(PipelineJob).where(
                PipelineJob.integration_id == integration.id,
                PipelineJob.selected.is_(True),
            )
        ).all()
    )
    if not refs:
        issues.append("NO_COLLECTION_METHODS")
    if not jobs:
        issues.append("NO_EXPLICITLY_SELECTED_JOBS")
    for method in refs:
        if not eligible(db, method):
            issues.append("METHOD_NOT_RUNTIME_VERIFIED:" + str(method.id))
        source = db.get(PipelineSource, method.source_id)
        try:
            reader_equivalence(db, source)
        except PipelineError as error:
            issues.append(error.code + ":" + str(source.id))
        if not source.continuity_validated:
            issues.append("CONTINUITY_NOT_VERIFIED:" + str(source.id))
        if db.scalar(
            select(PipelineHold.id).where(
                PipelineHold.source_id == source.id,
                PipelineHold.released_at.is_(None),
                PipelineHold.kind.in_(("MANUAL", "CONTINUITY")),
            )
        ):
            issues.append("SOURCE_HELD:" + str(source.id))
        if not source.last_received_at:
            issues.append("NO_DURABLE_TELEMETRY:" + str(source.id))
    for job in jobs:
        if job.quarantined or not job.resource_id:
            issues.append("JOB_IDENTITY_OR_RESOURCE_UNVERIFIED:" + str(job.id))
        if not db.scalar(
            select(PipelineAssociation.id)
            .join(PipelineMethod, PipelineMethod.id == PipelineAssociation.method_id)
            .join(PipelineSource, PipelineSource.id == PipelineMethod.source_id)
            .where(
                PipelineAssociation.job_id == job.id,
                PipelineAssociation.generation == PipelineSource.generation,
                PipelineMethod.enabled.is_(True),
                PipelineMethod.validation != "RETIRED",
            )
        ):
            issues.append("JOB_SOURCE_ASSOCIATION_REQUIRED:" + str(job.id))
    return sorted(set(issues))


def reconcile_discovery(
    db,
    integration,
    inventory,
    complete,
    authorized,
    actor_id=None,
    confirm_manual_ids=(),
):
    if not isinstance(inventory, list) or len(inventory) > 10000:
        raise PipelineError("DISCOVERY_LIMIT")
    current = clock(db)
    seen = set()
    duplicates = set()
    for item in inventory:
        native = item.get("native_id")
        name = item.get("name")
        if (
            not isinstance(native, str)
            or not 1 <= len(native) <= 500
            or not isinstance(name, str)
            or not 1 <= len(name) <= 200
        ):
            raise PipelineError("NATIVE_JOB_ID_REQUIRED")
        if native in seen:
            duplicates.add(native)
        seen.add(native)
    # Unauthorized or incomplete discovery never reconciles absence or claims completeness.
    if not authorized:
        raise PipelineError("DISCOVERY_NOT_AUTHORIZED")
    for item in inventory:
        job = db.scalar(
            select(PipelineJob).where(
                PipelineJob.integration_id == integration.id,
                PipelineJob.native_id == item["native_id"],
            )
        )
        if job is None:
            job = PipelineJob(
                organization_id=integration.organization_id,
                integration_id=integration.id,
                native_id=item["native_id"],
                name=item["name"],
                origin="DISCOVERED",
                selected=False,
            )
            db.add(job)
        elif job.origin == "LEGACY_PENDING":
            job.quarantined = True
            job.last_seen_at = current
            continue  # discovery cannot replace independent migration approval
        elif job.origin == "MANUAL" and job.native_id not in confirm_manual_ids:
            job.quarantined = True
            continue
        else:
            job.name = item["name"]
            job.stale_since = None
            if job.origin == "MANUAL":
                job.origin = "CONFIRMED_MERGE"
        job.last_seen_at = current
        job.quarantined = job.native_id in duplicates
    if complete:
        for job in db.scalars(
            select(PipelineJob).where(
                PipelineJob.integration_id == integration.id,
                PipelineJob.origin != "MANUAL",
            )
        ):
            if job.native_id not in seen and job.stale_since is None:
                job.stale_since = current
        integration.last_discovery_at = current
    event(db, integration, "DISCOVERY", actor_id)
    return {
        "complete": complete,
        "authorized": authorized,
        "found": len(seen),
        "ambiguous": len(duplicates),
    }


def operation(
    db,
    organization_id,
    kind,
    key,
    configuration,
    actor_id,
    integration_id=None,
    source_id=None,
):
    if not 1 <= len(key) <= 100:
        raise PipelineError("IDEMPOTENCY_KEY_REQUIRED")
    hashed = digest(configuration)
    existing = db.scalar(
        select(PipelineOperation).where(
            PipelineOperation.organization_id == organization_id,
            PipelineOperation.kind == kind,
            PipelineOperation.idempotency_key == key,
        )
    )
    if existing:
        if existing.request_hash != hashed:
            raise PipelineError("IDEMPOTENCY_PAYLOAD_MISMATCH")
        return existing, False
    row = PipelineOperation(
        organization_id=organization_id,
        kind=kind,
        idempotency_key=key,
        request_hash=hashed,
        actor_id=actor_id,
        configuration=deepcopy(configuration),
        integration_id=integration_id,
        source_id=source_id,
    )
    db.add(row)
    db.flush()
    event(db, row, "OPERATION_CREATE", actor_id)
    return row, True


def plan_recovery(db, source, start, end, actor_id, key, manual=False):
    if start.tzinfo is None or end.tzinfo is None or end <= start:
        raise PipelineError("RECOVERY_RANGE_INVALID")
    bound = RECOVERY_BOUNDS[source.method_type]
    current = clock(db)
    if end > current:
        raise PipelineError("RECOVERY_FUTURE_RANGE")
    config = {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "generation": str(source.generation),
        "checkpoint_hash": digest(source.recovery_checkpoint),
        "manual": manual,
    }
    row, new = operation(
        db,
        source.organization_id,
        "RECOVERY",
        key,
        config,
        actor_id,
        source_id=source.id,
    )
    if new:
        row.state = (
            "APPROVAL_REQUIRED"
            if (end - start).total_seconds() > bound
            or (current - start).total_seconds() > bound
            else "PENDING"
        )
        row.result = {"automatic_bound_seconds": bound, "live_priority": True}
    return row


def cleanup(db):
    """Daily bounded lifecycle work. Source configuration deletion never cascades evidence."""

    from app.unified.pentaho_models import PentahoRevision, PentahoEvidenceReview

    current = clock(db)
    removed = {"evidence": 0, "jobs": 0, "checkpoints": 0, "gaps": 0}
    protected = set(
        db.scalars(
            select(PipelineHold.source_id).where(
                PipelineHold.kind == "LEGAL", PipelineHold.released_at.is_(None)
            )
        )
    )
    for row in db.scalars(
        select(PipelineEvidence)
        .where(
            PipelineEvidence.created_at < current - timedelta(days=30),
            PipelineEvidence.source_id.not_in(protected),
            ~select(PentahoEvidenceReview.id)
            .where(PentahoEvidenceReview.source_evidence_id == PipelineEvidence.id)
            .exists(),
            ~select(PentahoRevision.id)
            .where(PentahoRevision.source_evidence_id == PipelineEvidence.id)
            .exists(),
            PipelineEvidence.payload["raw_retired"].as_boolean().is_not(True),
        )
        .limit(500)
    ):
        locked_source(db, row.source_id)
        legally_held = db.scalar(
            select(PipelineHold.id).where(
                PipelineHold.source_id == row.source_id,
                PipelineHold.kind == "LEGAL",
                PipelineHold.released_at.is_(None),
            )
        )
        if not legally_held:
            if db.scalar(
                select(PipelineCapability.id).where(
                    PipelineCapability.verification_evidence_id == row.id
                )
            ):
                if not row.payload.get("raw_retired"):
                    row.payload = {
                        "runtime_origin": row.payload.get("runtime_origin"),
                        "reader_definition_hash": row.payload.get(
                            "reader_definition_hash"
                        ),
                        "payload_sha256": digest(row.payload),
                        "raw_retired": True,
                    }
            else:
                db.delete(row)
            removed["evidence"] += 1
    for job in db.scalars(
        select(PipelineJob)
        .where(
            PipelineJob.selected.is_(False),
            PipelineJob.stale_since < current - timedelta(days=7),
            PipelineJob.resource_id.is_(None),
            ~select(PipelineAssociation.id)
            .where(PipelineAssociation.job_id == PipelineJob.id)
            .exists(),
        )
        .limit(100)
    ):
        # Any association or historical resource identity protects this candidate.
        if job.resource_id or db.scalar(
            select(PipelineAssociation.id).where(PipelineAssociation.job_id == job.id)
        ):
            continue
        integration_sources = set(
            db.scalars(
                select(PipelineMethod.source_id).where(
                    PipelineMethod.integration_id == job.integration_id
                )
            )
        )
        if integration_sources & protected:
            continue
        event(db, job, "STALE_JOB_DELETE")
        db.delete(job)
        removed["jobs"] += 1
    for source in db.scalars(
        select(PipelineSource)
        .where(
            PipelineSource.created_at < current - timedelta(days=14),
            PipelineSource.id.not_in(protected),
            (PipelineSource.live_checkpoint != {})
            | (PipelineSource.recovery_checkpoint != {}),
            ~select(PipelineMethod.id)
            .where(
                PipelineMethod.source_id == PipelineSource.id,
                PipelineMethod.validation != "RETIRED",
            )
            .exists(),
        )
        .limit(100)
    ):
        if (
            source.id in protected
            or source.lease_until
            and source.lease_until > current
        ):
            continue
        if source.last_received_at and source.last_received_at >= current - timedelta(
            days=14
        ):
            continue
        if methods(db, source) or db.scalar(
            select(PipelineOperation.id).where(
                PipelineOperation.source_id == source.id,
                PipelineOperation.state.in_(
                    ("PENDING", "RUNNING", "APPROVAL_REQUIRED")
                ),
            )
        ):
            continue
        source.live_checkpoint = {}
        source.recovery_checkpoint = {}
        source.continuity_validated = False
        removed["checkpoints"] += 1
    for row in db.scalars(
        select(PipelineOperation)
        .where(
            PipelineOperation.kind == "RECOVERY",
            PipelineOperation.state.in_(("COMPLETE", "UNRECOVERABLE")),
            PipelineOperation.created_at < current - timedelta(days=30),
            PipelineOperation.source_id.not_in(protected),
        )
        .limit(100)
    ):
        if row.source_id not in protected:
            event(db, row, "GAP_EXPIRE")
            db.delete(row)
            removed["gaps"] += 1
    # Existing append-only security audit is preserved; never reduce its >=365d policy.
    return removed
