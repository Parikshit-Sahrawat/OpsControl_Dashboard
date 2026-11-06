"""Secured configuration commands; no workload execution or source activation."""

from typing import Literal
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from app.db.session import get_db
from app.models import JobOrder, ETLWorkflow, Collector
from app.unified.models import MonitoringResource
from app.data_pipelines.models import (
    PipelineJob,
    PipelineIntegration,
    PipelineMethod,
    PipelineSource,
)
from app.data_pipelines.api import Mutation, checked, actor, doc, finish
from app.data_pipelines import service as pipeline
from app.security.access_control import require_permission
from app.etl_bindings.models import ETLNativeBinding
from app.etl_bindings import service

router = APIRouter(prefix="/api/v1/etl/workflows", tags=["ETL Native Binding"])


class BindingCommand(Mutation):
    command: Literal["STAGE", "CONFIRM", "REPLACE", "RETIRE"]
    current_binding_id: UUID | None = None
    native_job_id: UUID
    attestation_id: UUID | None = None
    authority_claim: str = Field(
        min_length=3, max_length=200, pattern=r"^[A-Za-z0-9._:/@-]+$"
    )
    method_ids: list[UUID] = Field(min_length=1, max_length=8)
    expected_sources: dict[UUID, UUID]
    reason: str = Field(min_length=3, max_length=500)
    confirmed: bool = False


def ownership(db, workflow_id, job_id, write=False):
    workflow = checked(db, ETLWorkflow, workflow_id)
    job = checked(db, JobOrder, job_id, write)
    if (
        job.workflow_id != workflow.id
        or job.organization_id != workflow.organization_id
        or job.environment != workflow.environment
    ):
        raise HTTPException(404, "Workflow Job unavailable")
    return workflow, job


@router.get("/{workflow_id}/jobs/{job_id}/native-bindings")
def bindings(workflow_id: UUID, job_id: UUID, db=Depends(get_db)):
    ownership(db, workflow_id, job_id)
    rows = db.scalars(
        select(ETLNativeBinding)
        .where(ETLNativeBinding.job_order_id == job_id)
        .order_by(ETLNativeBinding.valid_from, ETLNativeBinding.id)
    ).all()
    from app.etl_bindings.models import ETLNativeAttestation, ETLAuthorityRevocation

    proofs = db.scalars(
        select(ETLNativeAttestation).where(
            ETLNativeAttestation.binding_id.in_([b.id for b in rows])
        )
    ).all()
    revoked = set(
        db.scalars(
            select(ETLAuthorityRevocation.attestation_id).where(
                ETLAuthorityRevocation.attestation_id.in_([p.id for p in proofs])
            )
        ).all()
    )
    return {
        "versions": [doc(b) for b in rows],
        "authority_proofs": [
            {
                "id": str(p.id),
                "binding_id": str(p.binding_id),
                "issuer_key_id": p.issuer_key_id,
                "expires_at": p.expires_at.isoformat(),
                "revoked": p.id in revoked,
            }
            for p in proofs
        ],
        "authority_status": (
            "QUALIFIED"
            if any(
                b.state == "CONFIRMED"
                and b.valid_until is None
                and not service.stale_reasons(db, b)
                for b in rows
            )
            else "UNVERIFIED_UNTIL_PROVIDER_QUALIFICATION"
        ),
    }


@router.get("/{workflow_id}/jobs/{job_id}/native-binding-options")
def options(workflow_id: UUID, job_id: UUID, db=Depends(get_db)):
    workflow, job = ownership(db, workflow_id, job_id)
    resource = db.scalar(
        select(MonitoringResource).where(MonitoringResource.job_order_id == job.id)
    )
    # Only explicit existing Resource candidates. Do not silently bind/reparent unassigned native Jobs.
    candidates = db.scalars(
        select(PipelineJob)
        .join(PipelineIntegration, PipelineIntegration.id == PipelineJob.integration_id)
        .where(
            PipelineJob.resource_id == resource.id if resource else False,
            PipelineIntegration.environment == workflow.environment,
            PipelineIntegration.deleted_at.is_(None),
        )
        .order_by(PipelineJob.id)
        .limit(201)
    ).all()
    if len(candidates) > 200:
        raise HTTPException(409, "Too many candidates; refine inventory before binding")
    result = []
    for n in candidates:
        methods = db.scalars(
            select(PipelineMethod)
            .where(
                PipelineMethod.integration_id == n.integration_id,
                PipelineMethod.validation != "RETIRED",
            )
            .order_by(PipelineMethod.id)
            .limit(201)
        ).all()
        if len(methods) > 200:
            raise HTTPException(
                409, "Too many methods; refine integration before binding"
            )
        result.append(
            {
                "id": str(n.id),
                "name": n.name,
                "native_id": n.native_id,
                "quarantined": n.quarantined,
                "methods": [
                    {
                        "id": str(m.id),
                        "name": m.name,
                        "source_id": str(m.source_id),
                        "generation": str(
                            db.get(PipelineSource, m.source_id).generation
                        ),
                        "validation": m.validation,
                    }
                    for m in methods
                ],
            }
        )
    return {"candidates": result, "native_authority": "OPERATOR_CLAIM_ONLY"}


@router.post("/{workflow_id}/jobs/{job_id}/native-bindings", status_code=201)
def command(
    workflow_id: UUID, job_id: UUID, payload: BindingCommand, db=Depends(get_db)
):
    try:
        db.execute(text("SET LOCAL lock_timeout = '5s'"))
        return _command(workflow_id, job_id, payload, db)
    except DBAPIError as error:
        db.rollback()
        if getattr(error.orig, "sqlstate", None) in {
            "55P03",
            "40P01",
            "40001",
            "23505",
            "23503",
            "23514",
            "P0001",
        }:
            raise HTTPException(
                409, "BINDING_CONFLICT_OR_INVARIANT_REFUSED_REFRESH_AND_REVIEW"
            ) from None
        raise


def _command(workflow_id, job_id, payload, db):
    workflow, job = ownership(db, workflow_id, job_id, True)
    from app.etl_bindings.writer import mark

    mark(db)
    if not payload.confirmed:
        raise HTTPException(
            422, "Explicit monitoring-configuration confirmation required"
        )
    if len(set(payload.method_ids)) != len(payload.method_ids):
        raise HTTPException(422, "Duplicate method IDs")
    native = checked(db, PipelineJob, payload.native_job_id, True)
    integration = checked(db, PipelineIntegration, native.integration_id, True)
    resource = db.scalar(
        select(MonitoringResource)
        .where(MonitoringResource.job_order_id == job.id)
        .with_for_update()
    )
    if (
        not resource
        or native.resource_id != resource.id
        or native.organization_id != job.organization_id
        or integration.environment != job.environment
        or integration.deleted_at is not None
        or resource.environment != job.environment
        or resource.domain != "ETL"
    ):
        raise HTTPException(409, "NATIVE_JOB_RESOURCE_OR_ENVIRONMENT_MISMATCH")
    require_permission("etl.configure", integration.organization_id)
    collector = (
        db.get(Collector, resource.primary_collector_id)
        if resource.primary_collector_id
        else None
    )
    if collector and collector.enabled:
        raise HTTPException(409, "ACTIVE_LEGACY_COLLECTOR_REQUIRES_REVIEWED_HANDOFF")
    identity = {
        "schema": "NATIVE_AUTHORITY_CLAIM_V1",
        "platform": integration.platform,
        "environment": integration.environment,
        "authority_claim": payload.authority_claim,
        "object_kind": "JOB",
        "native_id": native.native_id,
    }
    key = pipeline.digest(identity)
    # Per-target transaction lock handles an initially absent unique row. Job row
    # lock plus unique indexes serialize same-Job and cross-Job races.
    lock = int(key[:15], 16)
    db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock})
    operation, new = pipeline.operation(
        db,
        job.organization_id,
        "NATIVE_BINDING",
        payload.idempotency_key,
        {
            "workflow_id": str(workflow_id),
            "job_id": str(job_id),
            **payload.model_dump(mode="json"),
        },
        actor().user_id,
        integration_id=integration.id,
    )
    if not new:
        finish(db)
        return doc(checked(db, ETLNativeBinding, UUID(operation.result["id"])))
    old = service.current(db, job.id)
    if (old.id if old else None) != payload.current_binding_id:
        raise HTTPException(409, "CURRENT_BINDING_CHANGED_REFRESH")
    if old and payload.expected_revision != old.revision:
        raise HTTPException(409, "BINDING_REVISION_CHANGED_REFRESH")
    if not old and payload.command != "STAGE":
        raise HTTPException(409, "STAGE_BINDING_FIRST")
    if old and payload.command == "STAGE":
        raise HTTPException(409, "USE_EXPLICIT_REPLACEMENT_OR_RETIREMENT")
    if old and (old.identity_key != key or old.native_job_id != native.id):
        raise HTTPException(
            409, "NATIVE_IDENTITY_RETARGET_FORBIDDEN_CREATE_DISTINCT_JOB"
        )
    if old and old.state == "RETIRED":
        raise HTTPException(409, "RETIRED_BINDING_IS_TERMINAL")
    snapshots, sources = service.snapshots(db, native, payload.method_ids)
    if set(payload.expected_sources) != set(sources) or any(
        payload.expected_sources[s.id] != s.generation for s in sources.values()
    ):
        raise HTTPException(409, "SOURCE_GENERATION_CHANGED_REFRESH")
    service.safe_cutover(db, sources)
    if integration.enabled or native.selected:
        raise HTTPException(409, "ACTIVE_NATIVE_SOURCE_REQUIRES_REVIEWED_HANDOFF")
    if old:
        old_ids = [UUID(s["method_id"]) for s in old.method_snapshot]
        # Lock both old and new source sets before closure. Stale old generations
        # require reviewed source handoff/reconciliation, never silent rebasing.
        _, old_sources = service.snapshots(db, native, old_ids)
        sources.update(old_sources)
        if service.stale_reasons(db, old) and payload.command != "RETIRE":
            raise HTTPException(409, "STALE_BINDING_REQUIRES_SOURCE_REVIEW")
        service.safe_cutover(db, sources)
    if payload.command == "CONFIRM":
        if old.actor_id == actor().user_id:
            raise HTTPException(403, "INDEPENDENT_BINDING_REVIEWER_REQUIRED")
        if any(
            not pipeline.eligible(db, db.get(PipelineMethod, m))
            for m in payload.method_ids
        ):
            raise HTTPException(409, "CURRENT_AUTHENTICATED_RUNTIME_PROOF_REQUIRED")
        from app.etl_bindings.authority import usable
        from app.etl_bindings.models import ETLNativeAttestation

        if not payload.attestation_id:
            raise HTTPException(409, "NATIVE_AUTHORITY_CERTIFICATION_REQUIRED_D09")
        proof = checked(db, ETLNativeAttestation, payload.attestation_id)
        usable(db, proof, old, snapshots)
    if old and old.state == "CONFIRMED" and payload.command != "RETIRE":
        # Qualified active readers require the existing independently reviewed
        # handoff protocol. No live per-binding shortcut is authorized here.
        raise HTTPException(409, "ACTIVE_BINDING_REQUIRES_REVIEWED_SOURCE_HANDOFF")
    instant = datetime.now(timezone.utc)
    if old:
        old.valid_until = instant
        from app.etl_bindings.models import ETLBindingQualification

        qualification = db.scalar(
            select(ETLBindingQualification).where(
                ETLBindingQualification.binding_id == old.id,
                ETLBindingQualification.valid_until.is_(None),
            )
        )
        if qualification:
            qualification.valid_until = instant
        db.flush()  # release partial uniqueness in the same transaction
    row = ETLNativeBinding(
        organization_id=job.organization_id,
        workflow_id=workflow.id,
        job_order_id=job.id,
        resource_id=resource.id,
        native_job_id=native.id,
        integration_id=integration.id,
        previous_id=old.id if old else None,
        identity_key=key,
        identity_snapshot=identity,
        method_snapshot=(
            old.method_snapshot if payload.command == "RETIRE" else snapshots
        ),
        state=(
            "RETIRED"
            if payload.command == "RETIRE"
            else ("CONFIRMED" if payload.command == "CONFIRM" else "STAGED")
        ),
        valid_from=instant,
        actor_id=actor().user_id,
        reason=payload.reason,
        operation_id=operation.id,
    )
    db.add(row)
    db.flush()
    if payload.command == "CONFIRM":
        from app.etl_bindings.models import ETLBindingQualification

        db.add(
            ETLBindingQualification(
                organization_id=row.organization_id,
                binding_id=row.id,
                attestation_id=proof.id,
                job_order_id=row.job_order_id,
                target_key=proof.target_key,
            )
        )
    from app.security.audit import log_event

    log_event(
        db,
        event_type="ETL_NATIVE_BINDING_" + payload.command,
        outcome="SUCCESS",
        actor_id=actor().user_id,
        organization_id=job.organization_id,
        target_type="ETLNativeBinding",
        target_id=row.id,
    )
    operation.state = "COMPLETE"
    operation.result = {"id": str(row.id)}
    finish(db)
    return doc(row)


@router.get("/{workflow_id}/readiness")
def readiness(workflow_id: UUID, db=Depends(get_db)):
    workflow = checked(db, ETLWorkflow, workflow_id)
    jobs = db.scalars(
        select(JobOrder)
        .where(JobOrder.workflow_id == workflow.id)
        .order_by(JobOrder.id)
    ).all()
    return service.readiness(db, workflow, jobs)
