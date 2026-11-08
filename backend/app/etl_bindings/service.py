"""Binding configuration never starts a collector or infers provider certification."""

from datetime import datetime, timezone
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select
from app.data_pipelines import service as pipeline
from app.data_pipelines.models import (
    PipelineMethod,
    PipelineSource,
    PipelineHold,
    PipelineEvidence,
    PipelineConnection,
    PipelineCapability,
)
from app.etl_bindings.models import ETLNativeBinding, ETLBindingReceipt

POLICY = "ETL_SOURCE_RECEIPT_V1"


def current(db, job_id):
    return db.scalar(
        select(ETLNativeBinding).where(
            ETLNativeBinding.job_order_id == job_id,
            ETLNativeBinding.valid_until.is_(None),
        )
    )


def snapshots(db, native, ids):
    methods = db.scalars(
        select(PipelineMethod)
        .where(PipelineMethod.id.in_(ids))
        .order_by(PipelineMethod.id)
        .with_for_update()
    ).all()
    if len(methods) != len(ids) or not methods:
        raise HTTPException(409, "METHODS_REQUIRED_OR_UNAVAILABLE")
    sources = {}
    for source_id in sorted({m.source_id for m in methods}, key=str):
        source = db.scalar(
            select(PipelineSource)
            .where(PipelineSource.id == source_id)
            .with_for_update()
        )
        if not source or source.organization_id != native.organization_id:
            raise HTTPException(409, "SOURCE_UNAVAILABLE")
        sources[source_id] = source
    result = []
    for m in methods:
        source = sources[m.source_id]
        if (
            m.integration_id != native.integration_id
            or m.organization_id != native.organization_id
            or m.validation == "RETIRED"
        ):
            raise HTTPException(409, "METHOD_INTEGRATION_MISMATCH")
        connection = db.get(PipelineConnection, m.connection_id)
        capability = db.get(PipelineCapability, m.capability_id)
        if (
            not connection
            or not capability
            or connection.integration_id != native.integration_id
            or capability.integration_id != native.integration_id
            or connection.organization_id != native.organization_id
            or capability.organization_id != native.organization_id
        ):
            raise HTTPException(409, "READER_VERSION_OWNERSHIP_MISMATCH")
        result.append(
            {
                "method_id": str(m.id),
                "revision": m.revision,
                "source_id": str(source.id),
                "generation": str(source.generation),
                "fence": source.fence,
                "connection_id": str(m.connection_id),
                "connection_version": connection.version,
                "connection_checksum": connection.checksum,
                "source_identity_sha256": pipeline.digest(source.identity),
                "capability_platform_version": capability.platform_version,
                "verification_evidence_id": (
                    str(capability.verification_evidence_id)
                    if capability.verification_evidence_id
                    else None
                ),
                "capability_id": str(m.capability_id),
                "reader_definition_hash": pipeline.reader_definition(db, m),
            }
        )
    return result, sources


def stale_reasons(db, binding):
    reasons = []
    for snap in binding.method_snapshot:
        method = db.get(PipelineMethod, UUID(snap["method_id"]), populate_existing=True)
        source = db.get(PipelineSource, UUID(snap["source_id"]), populate_existing=True)
        if not method or not source:
            reasons.append("SOURCE_OR_METHOD_MISSING")
        elif (
            str(source.generation) != snap["generation"]
            or source.fence < snap["fence"]
            or method.revision != snap["revision"]
            or str(method.source_id) != snap["source_id"]
            or str(method.connection_id) != snap["connection_id"]
            or str(method.capability_id) != snap["capability_id"]
            or pipeline.reader_definition(db, method) != snap["reader_definition_hash"]
        ):
            reasons.append("SOURCE_GENERATION_OR_READER_CHANGED")
    if binding.state == "CONFIRMED":
        from app.etl_bindings.authority import qualified_binding

        try:
            qualified_binding(db, binding)
        except HTTPException as error:
            reasons.append(str(error.detail))
    return sorted(set(reasons))


def safe_cutover(db, sources):
    now = datetime.now(timezone.utc)
    for source in sources.values():
        if source.lease_until and source.lease_until > now:
            raise HTTPException(409, "SOURCE_IN_FLIGHT_WAIT_FOR_REVIEWED_HANDOFF")
        if db.scalar(
            select(PipelineHold.id).where(
                PipelineHold.source_id == source.id,
                PipelineHold.released_at.is_(None),
                PipelineHold.kind.in_(("LEGAL", "MANUAL", "CONTINUITY")),
            )
        ):
            raise HTTPException(409, "SOURCE_RETENTION_OR_CONTINUITY_HOLD")


def routing_binding(db, job, source, method):
    """Opted-in Jobs fail closed. Legacy Jobs retain their existing routing contract."""
    from app.unified.models import MonitoringResource

    resource = db.get(MonitoringResource, job.resource_id)
    if not resource or not resource.job_order_id:
        return True, None
    binding = current(db, resource.job_order_id)
    if binding is None:
        return True, None
    if (
        binding.state != "CONFIRMED"
        or binding.native_job_id != job.id
        or stale_reasons(db, binding)
    ):
        return False, None
    allowed = any(
        s["method_id"] == str(method.id)
        and s["source_id"] == str(source.id)
        and s["generation"] == str(source.generation)
        for s in binding.method_snapshot
    )
    return allowed, binding if allowed else None


def record_receipt(db, binding, evidence):
    db.info.setdefault("etl_admitted_bindings", set()).add(binding.id)
    db.add(
        ETLBindingReceipt(
            organization_id=binding.organization_id,
            binding_id=binding.id,
            evidence_id=evidence.id,
            payload_sha256=pipeline.digest(evidence.payload),
        )
    )


def receipt_freshness(now, observed_at, committed_at, threshold):
    """Both source and server clocks must be within the contextual policy."""
    source_age = (now - observed_at).total_seconds()
    commit_age = (now - committed_at).total_seconds()
    if source_age < 0 or commit_age < 0:
        return "CLOCK_UNCERTAIN"
    return "FRESH" if max(source_age, commit_age) <= threshold else "STALE"


def readiness(db, workflow, jobs):
    now = datetime.now(timezone.utc)
    results = []
    for job in jobs:
        binding = current(db, job.id)
        config_ok = (
            job.expected_runtime_seconds is not None
            and 1 <= job.expected_runtime_seconds <= 604800
        )
        binding_state = "MISSING" if binding is None else binding.state
        reasons = [] if binding is None else stale_reasons(db, binding)
        if reasons:
            binding_state = "STALE"
        connectivity = "UNVERIFIED"
        thresholds = []
        if binding:
            qualified = []
            for snap in binding.method_snapshot:
                m = db.get(PipelineMethod, UUID(snap["method_id"]))
                qualified.append(bool(m and pipeline.eligible(db, m)))
                thresholds.append(
                    max(120, int(m.configuration.get("interval_seconds", 60)) * 3)
                    if m
                    else 120
                )
            if qualified and all(qualified) and not reasons:
                connectivity = "RUNTIME_VERIFIED"
        receipt = None
        if binding and binding.state == "CONFIRMED" and not reasons:
            receipt = db.scalar(
                select(PipelineEvidence)
                .join(
                    ETLBindingReceipt,
                    ETLBindingReceipt.evidence_id == PipelineEvidence.id,
                )
                .where(ETLBindingReceipt.binding_id == binding.id)
                .order_by(PipelineEvidence.created_at.desc())
                .limit(1)
            )
        fresh = "MISSING"
        if receipt:
            fresh = receipt_freshness(
                now, receipt.observed_at, receipt.created_at, min(thresholds)
            )
        authority_state = (
            "QUALIFIED"
            if binding_state == "CONFIRMED" and not reasons
            else "UNVERIFIED"
        )
        reasons += [
            *(
                []
                if authority_state == "QUALIFIED"
                else ["PROVIDER_NATIVE_AUTHORITY_NOT_CERTIFIED"]
            ),
            "WORKFLOW_ACTIVATION_NOT_QUALIFIED",
        ]
        results.append(
            {
                "job_id": str(job.id),
                "binding_id": str(binding.id) if binding else None,
                "configuration_completeness": {
                    "state": "VALID" if config_ok else "INCOMPLETE",
                    "scope": "SUPPORTED_CHILD_RUNTIME_FIELDS_ONLY",
                },
                "binding_validity": {
                    "state": binding_state,
                    "authority": authority_state,
                },
                "monitoring_activation": {
                    "state": "BLOCKED",
                    "reason": "PROVIDER_QUALIFICATION_REQUIRED",
                },
                "source_connectivity": {"state": connectivity},
                "evidence_freshness": {
                    "state": fresh,
                    "threshold_seconds": min(thresholds) if thresholds else None,
                    "basis": "accepted_binding_receipt_observed_and_committed_at",
                    "evidence_id": str(receipt.id) if receipt else None,
                },
                "operational_health": {
                    "state": "UNVERIFIED",
                    "reason": "NO_QUALIFIED_NATIVE_EXECUTION_PROJECTION",
                },
                "reasons": sorted(set(reasons)),
            }
        )
    return {
        "schema_version": 1,
        "freshness_policy": POLICY,
        "evaluated_at": now.isoformat(),
        "workflow_id": str(workflow.id),
        "jobs": results,
        "activation_status": "BLOCKED",
        "scope": "MONITORING_ONLY",
        "provider_certification": "NOT_ESTABLISHED",
    }
