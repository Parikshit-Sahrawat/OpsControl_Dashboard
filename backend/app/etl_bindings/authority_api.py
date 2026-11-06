"""Evidence admission/revocation, not a provider verifier or execution controller."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from app.db.session import get_db
from app.data_pipelines.api import checked, actor, finish, doc
from app.data_pipelines.models import PipelineSource
from app.data_pipelines import service as pipeline
from app.etl_bindings.models import (
    ETLNativeBinding,
    ETLNativeAttestation,
    ETLAuthorityRevocation,
)
from app.etl_bindings.authority import (
    Envelope,
    trust_store,
    verify_signature,
    validate_context,
)
from app.etl_bindings.writer import mark
from app.security.audit import log_event

router = APIRouter(prefix="/api/v1/etl/native-authority", tags=["ETL Native Authority"])


class Submission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    envelope: Envelope


class Revocation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=3, max_length=500)


@router.post("/validate-envelope")
def preview(payload: Submission, db=Depends(get_db)):
    binding = checked(db, ETLNativeBinding, payload.envelope.body.binding_id, True)
    body = payload.envelope.body
    if (
        body.organization_id != binding.organization_id
        or body.native_job_id != binding.native_job_id
    ):
        raise HTTPException(409, "NATIVE_AUTHORITY_SCOPE_MISMATCH")
    result = verify_signature(payload.envelope, trust_store(), pipeline.clock(db))
    validate_context(
        db,
        payload.envelope,
        binding,
        binding.method_snapshot,
        require_runtime=result["qualified"],
    )
    return {
        **result,
        "provider_certification": "NOT_ESTABLISHED_BY_ENVELOPE_PREVIEW",
        "persisted": False,
        "monitoring_activation": "BLOCKED",
    }


@router.post("/attestations", status_code=201)
def submit(payload: Submission, db=Depends(get_db)):
    binding = checked(db, ETLNativeBinding, payload.envelope.body.binding_id, True)
    if binding.state != "STAGED" or binding.valid_until is not None:
        raise HTTPException(409, "CURRENT_STAGED_BINDING_REQUIRED")
    if actor().user_id == binding.actor_id:
        raise HTTPException(403, "INDEPENDENT_BINDING_REVIEWER_REQUIRED")
    result = verify_signature(payload.envelope, trust_store(), pipeline.clock(db))
    if not result["qualified"]:
        raise HTTPException(409, "CONTRACT_TEST_ENVELOPE_CANNOT_QUALIFY_PROVIDER")
    validate_context(db, payload.envelope, binding, binding.method_snapshot)
    mark(db)
    encoded = payload.envelope.model_dump(mode="json")
    digest = pipeline.digest(encoded)
    existing = db.scalar(
        select(ETLNativeAttestation).where(
            ETLNativeAttestation.envelope_sha256 == digest
        )
    )
    if existing:
        return doc(existing)
    row = ETLNativeAttestation(
        organization_id=binding.organization_id,
        binding_id=binding.id,
        resource_id=binding.resource_id,
        target_key=result["target_key"],
        envelope=encoded,
        envelope_sha256=digest,
        issuer_key_id=payload.envelope.issuer_key_id,
        expires_at=payload.envelope.body.expires_at,
        submitted_by=actor().user_id,
    )
    db.add(row)
    db.flush()
    log_event(
        db,
        event_type="ETL_AUTHORITY_ADMITTED",
        outcome="SUCCESS",
        actor_id=actor().user_id,
        organization_id=binding.organization_id,
        target_type="ETLNativeAttestation",
        target_id=row.id,
    )
    finish(db)
    return doc(row)


@router.post("/attestations/{id}/revoke", status_code=201)
def revoke(id: UUID, payload: Revocation, db=Depends(get_db)):
    row = checked(db, ETLNativeAttestation, id, True)
    for source_id in sorted(
        {UUID(m["source_id"]) for m in row.envelope["body"]["methods"]}, key=str
    ):
        checked(db, PipelineSource, source_id, True)
    mark(db)
    existing = db.scalar(
        select(ETLAuthorityRevocation).where(
            ETLAuthorityRevocation.attestation_id == id
        )
    )
    if existing:
        return doc(existing)
    event = ETLAuthorityRevocation(
        organization_id=row.organization_id,
        attestation_id=id,
        actor_id=actor().user_id,
        reason=payload.reason,
    )
    db.add(event)
    db.flush()
    log_event(
        db,
        event_type="ETL_AUTHORITY_REVOKED",
        outcome="SUCCESS",
        actor_id=actor().user_id,
        organization_id=row.organization_id,
        target_type="ETLNativeAttestation",
        target_id=id,
    )
    finish(db)
    return doc(event)
