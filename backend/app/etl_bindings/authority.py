"""Provider-independent signed evidence envelopes; no provider certifier.

No built-in trust keys/targets. Test-only signers can validate envelopes but can
never qualify a provider, persist authority, confirm or authorize receipt routing.
"""

import base64
import json
import os
import stat
from datetime import datetime, timezone
from uuid import UUID
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal, Annotated
from sqlalchemy import select
from app.data_pipelines import service as pipeline
from app.data_pipelines.models import (
    PipelineMethod,
    PipelineEvidence,
    PipelineCapability,
    PipelineSource,
)
from app.etl_bindings.models import (
    ETLNativeAttestation,
    ETLAuthorityRevocation,
    ETLBindingQualification,
)

DOMAIN = b"opscontrol/native-authority/v1\x00"
MAX_LIFETIME_SECONDS = 86400


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MethodProof(Strict):
    method_id: UUID
    source_id: UUID
    generation: UUID
    revision: int = Field(ge=1)
    reader_definition_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    evidence_id: UUID
    payload_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    exact_build: str = Field(min_length=1, max_length=100)


class AuthorityBody(Strict):
    schema_version: Literal[1]
    assurance: Literal["PROVIDER_QUALIFIED", "CONTRACT_TEST_ONLY"]
    organization_id: UUID
    environment: str = Field(pattern=r"^(PROD|QA|TEST|DEV|SANDBOX)$")
    platform: str = Field(min_length=1, max_length=30)
    binding_id: UUID
    native_job_id: UUID
    observed_native_id: str = Field(min_length=1, max_length=500)
    canonical_authority_id: str = Field(min_length=1, max_length=200)
    authority_aliases: list[Annotated[str, Field(min_length=1, max_length=200)]] = (
        Field(min_length=1, max_length=20)
    )
    canonical_object_key: str = Field(min_length=1, max_length=500)
    object_kind: Literal["JOB"]
    issued_at: datetime
    not_before: datetime
    expires_at: datetime
    methods: list[MethodProof] = Field(min_length=1, max_length=8)


class Envelope(Strict):
    issuer_key_id: str = Field(min_length=1, max_length=100)
    body: AuthorityBody
    signature: str = Field(min_length=80, max_length=100)


def signed_bytes(body):
    return (
        DOMAIN
        + json.dumps(
            body, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode()
    )


def trust_store():
    path = os.environ.get("OPSCONTROL_ETL_AUTHORITY_TRUST_STORE")
    if not path:
        raise HTTPException(409, "NATIVE_AUTHORITY_TRUST_NOT_CONFIGURED")
    try:
        # Public keys are not secrets, but who may change them is security-critical.
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(descriptor) as file:
            info = os.fstat(file.fileno())
            parent = os.stat(os.path.dirname(os.path.abspath(path)))
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_uid not in {0, os.geteuid()}
                or info.st_mode & 0o022
                or parent.st_mode & 0o022
                or info.st_size > 262144
            ):
                raise ValueError()
            result = json.load(file)
        if result.get("version") != 1 or not isinstance(result.get("issuers"), dict):
            raise ValueError()
        return result
    except (OSError, ValueError, TypeError):
        raise HTTPException(409, "NATIVE_AUTHORITY_TRUST_INVALID") from None


def verify_signature(envelope, store, now=None):
    """Positive here means signed-contract validity only, never provider certification."""
    now = now or datetime.now(timezone.utc)
    body = envelope.body
    issuer = store.get("issuers", {}).get(envelope.issuer_key_id)
    if not isinstance(issuer, dict) or issuer.get("revoked"):
        raise HTTPException(409, "NATIVE_AUTHORITY_ISSUER_UNAVAILABLE")
    if any(
        t.tzinfo is None for t in [body.issued_at, body.not_before, body.expires_at]
    ):
        raise HTTPException(422, "AUTHORITY_UTC_OFFSETS_REQUIRED")
    if (
        not body.not_before <= body.issued_at <= now < body.expires_at
        or (body.expires_at - body.not_before).total_seconds() > MAX_LIFETIME_SECONDS
    ):
        raise HTTPException(409, "NATIVE_AUTHORITY_EXPIRED_OR_CLOCK_INVALID")
    raw = body.model_dump(mode="json")
    try:
        public = base64.b64decode(issuer["public_key_base64"], validate=True)
        signature = base64.b64decode(envelope.signature, validate=True)
        Ed25519PublicKey.from_public_bytes(public).verify(signature, signed_bytes(raw))
    except (KeyError, ValueError, TypeError, InvalidSignature):
        raise HTTPException(409, "NATIVE_AUTHORITY_SIGNATURE_INVALID") from None
    if len(set(body.authority_aliases)) != len(body.authority_aliases) or len(
        {p.method_id for p in body.methods}
    ) != len(body.methods):
        raise HTTPException(422, "AUTHORITY_ALIAS_OR_METHOD_DUPLICATE")
    target = pipeline.digest(
        [
            str(body.organization_id),
            body.environment,
            body.platform,
            body.canonical_authority_id,
            body.object_kind,
            body.canonical_object_key,
        ]
    )
    qualified = (
        issuer.get("assurance") == "PROVIDER_QUALIFIED"
        and body.assurance == "PROVIDER_QUALIFIED"
    )
    # Approval inventory is server-owned and exact, not a wildcard/operator claim.
    approved = issuer.get("targets", {}).get(target)
    if qualified and (
        not isinstance(approved, dict)
        or not approved
        or not approved.get("approval_reference")
        or set(approved.get("exact_builds", []))
        != {p.exact_build for p in body.methods}
        or set(approved.get("source_ids", []))
        != {str(p.source_id) for p in body.methods}
    ):
        raise HTTPException(409, "NATIVE_AUTHORITY_TARGET_NOT_APPROVED")
    if body.assurance == "PROVIDER_QUALIFIED" and not qualified:
        raise HTTPException(409, "TEST_ISSUER_CANNOT_QUALIFY_PROVIDER")
    return {
        "target_key": target,
        "qualified": qualified,
        "status": (
            "SIGNED_ENVELOPE_VALID" if qualified else "CONTRACT_VALID_NOT_QUALIFIED"
        ),
    }


def validate_context(db, envelope, binding, snapshots, require_runtime=True):
    body = envelope.body
    identity = binding.identity_snapshot
    if (
        body.binding_id != binding.id
        or body.organization_id != binding.organization_id
        or body.native_job_id != binding.native_job_id
        or body.environment != identity["environment"]
        or body.platform != identity["platform"]
        or body.observed_native_id != identity["native_id"]
        or identity["authority_claim"] not in body.authority_aliases
    ):
        raise HTTPException(409, "NATIVE_AUTHORITY_BINDING_SCOPE_OR_ALIAS_MISMATCH")
    expected = {s["method_id"]: s for s in snapshots}
    if set(expected) != {str(p.method_id) for p in body.methods}:
        raise HTTPException(409, "NATIVE_AUTHORITY_METHOD_SET_CHANGED")
    for item in body.methods:
        snap = expected[str(item.method_id)]
        method = db.get(PipelineMethod, item.method_id, populate_existing=True)
        source = db.get(PipelineSource, item.source_id, populate_existing=True)
        if (
            str(item.source_id) != snap["source_id"]
            or str(item.generation) != snap["generation"]
            or item.revision != snap["revision"]
            or item.reader_definition_hash != snap["reader_definition_hash"]
            or not method
            or not source
            or source.generation != item.generation
            or method.source_id != item.source_id
            or method.revision != item.revision
            or pipeline.reader_definition(db, method) != item.reader_definition_hash
            or method.organization_id != binding.organization_id
        ):
            raise HTTPException(409, "NATIVE_AUTHORITY_METHOD_OR_GENERATION_CHANGED")
        if not require_runtime:
            continue  # Contract preview is deliberately NOT provider qualification.
        proof = db.get(PipelineEvidence, item.evidence_id)
        profile = db.get(PipelineCapability, method.capability_id)
        if (
            not pipeline.eligible(db, method)
            or not proof
            or proof.organization_id != binding.organization_id
            or proof.source_id != item.source_id
            or proof.generation != item.generation
            or proof.outcome != "ACCEPTED"
            or not body.not_before <= proof.created_at <= body.issued_at
            or not body.not_before <= proof.observed_at <= body.issued_at
            or proof.native_job_id != body.observed_native_id
            or proof.payload.get("runtime_origin") != "AUTHENTICATED_RUNTIME"
            or pipeline.digest(proof.payload) != item.payload_sha256
            or not profile
            or profile.platform_version != item.exact_build
        ):
            raise HTTPException(
                409, "NATIVE_AUTHORITY_CURRENT_RUNTIME_EVIDENCE_REQUIRED"
            )


def usable(db, attestation, binding, snapshots):
    if (
        not attestation
        or attestation.resource_id != binding.resource_id
        or attestation.organization_id != binding.organization_id
    ):
        raise HTTPException(409, "NATIVE_AUTHORITY_PROOF_UNAVAILABLE")
    if db.scalar(
        select(ETLAuthorityRevocation.id).where(
            ETLAuthorityRevocation.attestation_id == attestation.id
        )
    ):
        raise HTTPException(409, "NATIVE_AUTHORITY_REVOKED")
    envelope = Envelope.model_validate(attestation.envelope)
    result = verify_signature(envelope, trust_store())
    # Confirmed successor retains the immutable proof for its staged predecessor.
    expected_stage = binding.previous_id if binding.state == "CONFIRMED" else binding.id
    if envelope.body.binding_id != expected_stage:
        raise HTTPException(409, "NATIVE_AUTHORITY_VERSION_MISMATCH")
    from types import SimpleNamespace

    staged = SimpleNamespace(
        id=envelope.body.binding_id,
        organization_id=binding.organization_id,
        native_job_id=binding.native_job_id,
        identity_snapshot=binding.identity_snapshot,
    )
    validate_context(db, envelope, staged, snapshots)
    if not result["qualified"] or result["target_key"] != attestation.target_key:
        raise HTTPException(409, "NATIVE_AUTHORITY_NOT_PROVIDER_QUALIFIED")
    return result


def qualified_binding(db, binding):
    qualification = db.scalar(
        select(ETLBindingQualification).where(
            ETLBindingQualification.binding_id == binding.id,
            ETLBindingQualification.valid_until.is_(None),
        )
    )
    if not qualification:
        raise HTTPException(409, "NATIVE_AUTHORITY_QUALIFICATION_MISSING")
    proof = db.get(ETLNativeAttestation, qualification.attestation_id)
    return usable(db, proof, binding, binding.method_snapshot)
