"""Additional pipeline transport protocol; existing VM enrollment/installation unchanged."""

import uuid
from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from app.db.session import get_db
from app.telemetry.api import authenticate
from app.data_pipelines.models import PipelineOperation, PipelineSource
from app.data_pipelines import service as s

router = APIRouter(prefix="/api/v1/agent", tags=["Pipeline Agent Transport"])


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: uuid.UUID
    verification: bool = False
    recovery_operation_id: uuid.UUID | None = None


class Batch(Claim):
    ticket: dict
    records: list[dict] = Field(max_length=1000)
    checkpoint: dict
    complete: bool = False


class Continuity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_id: uuid.UUID
    files: dict


def bound(db, request, source_id):
    agent, collector, ds, worker = authenticate(db, request)
    source = db.get(PipelineSource, source_id)
    from app.unified.models import MonitoringResource

    parent = (
        db.get(
            MonitoringResource, uuid.UUID(source.identity.get("host_resource_id", ""))
        )
        if source and source.method_type == "FILE_LOG"
        else None
    )
    if (
        not source
        or source.organization_id != agent.organization_id
        or not parent
        or parent.primary_collector_id != collector.id
        or parent.domain != "VM"
    ):
        raise HTTPException(404, "Pipeline source unavailable")
    refs = [m for m in s.methods(db, source) if m.enabled and m.transport == "AGENT"]
    if not refs:
        raise HTTPException(404, "Pipeline source unavailable")
    # The source cannot be read simultaneously by an existing VM file receiver.
    from app.telemetry.models import CollectorConfigVersion

    cfg = db.scalar(
        select(CollectorConfigVersion).where(
            CollectorConfigVersion.collector_id == collector.id,
            CollectorConfigVersion.revision == agent.applied_revision,
        )
    )
    path = source.identity["path"]
    if not cfg or any(
        m.get("enabled")
        and m.get("method_type") == "FILE_LOG"
        and path
        in {
            s.canonical("FILE_LOG", {**source.identity, "path": configured})[0]["path"]
            for configured in m.get("configuration", {}).get("paths", [])
        }
        for m in cfg.method_snapshot
    ):
        raise HTTPException(
            409,
            "Apply the approved VM source handoff before claiming pipeline collection",
        )
    return agent, source


@router.post("/pipeline-claim")
def claim(payload: Claim, request: Request, db=Depends(get_db)):
    agent, source = bound(db, request, payload.source_id)
    if payload.verification:
        operation = db.scalar(
            select(PipelineOperation).where(
                PipelineOperation.source_id == source.id,
                PipelineOperation.kind == "VERIFY",
                PipelineOperation.state == "RUNNING",
            )
        )
        if not operation:
            raise HTTPException(409, "Approved runtime verification session required")
    recovery = (
        db.get(PipelineOperation, payload.recovery_operation_id)
        if payload.recovery_operation_id
        else None
    )
    if recovery:
        source = s.locked_source(db, source.id)
        if (
            recovery.source_id != source.id
            or recovery.kind != "RECOVERY"
            or recovery.state not in {"PENDING", "APPROVED"}
            or recovery.configuration.get("generation") != str(source.generation)
        ):
            raise HTTPException(409, "Eligible generation-bound recovery plan required")
        if not source.next_run_at or source.next_run_at <= s.clock(db):
            raise HTTPException(409, "Live collection has priority")
    ticket = s.acquire(db, source.id, agent.id, 120, verification=payload.verification)
    if recovery:
        recovery.state = "RUNNING"
        recovery.fence += 1
        recovery.owner_id = agent.id
        recovery.attempts += 1
        recovery.lease_until = source.lease_until
        ticket["checkpoint"] = source.recovery_checkpoint
        ticket["recovery_operation_id"] = str(recovery.id)
        ticket["recovery_fence"] = recovery.fence
    method = next(
        m for m in s.methods(db, source) if m.transport == "AGENT" and m.enabled
    )
    db.commit()
    return {
        "ticket": ticket,
        "identity": source.identity,
        "configuration": method.configuration,
        "recovery_range": recovery.configuration if recovery else None,
    }


@router.post("/pipeline-evidence")
def evidence(payload: Batch, request: Request, db=Depends(get_db)):
    agent, source = bound(db, request, payload.source_id)
    if payload.ticket.get("source_id") != str(source.id) or payload.ticket.get(
        "owner_id"
    ) != str(agent.id):
        raise HTTPException(403, "Source-bound Agent ownership required")
    method = next(
        m for m in s.methods(db, source) if m.enabled and m.transport == "AGENT"
    )
    records = [
        {
            **r,
            "runtime_origin": "AUTHENTICATED_RUNTIME",
            "reader_definition_hash": s.reader_definition(db, method),
        }
        for r in payload.records
    ]
    recovery = (
        db.get(PipelineOperation, payload.recovery_operation_id)
        if payload.recovery_operation_id
        else None
    )
    if recovery and (
        recovery.source_id != source.id
        or recovery.owner_id != agent.id
        or recovery.fence != payload.ticket.get("recovery_fence")
        or str(recovery.id) != payload.ticket.get("recovery_operation_id")
    ):
        raise HTTPException(409, "Recovery range ownership changed")
    if payload.ticket.get("recovery_operation_id") and not recovery:
        raise HTTPException(
            422, "Recovery acknowledgement cannot advance the live cursor"
        )
    result = s.accept(
        db,
        payload.ticket,
        records,
        payload.checkpoint,
        payload.complete,
        recovery_operation=recovery,
    )
    if recovery:
        recovery.state = "COMPLETE" if payload.complete else "PENDING"
        recovery.result = {**recovery.result, **result}
        if recovery.attempts >= 3 and not payload.complete:
            recovery.state = "UNRECOVERABLE"
            recovery.result = {**recovery.result, "new_evidence_required": True}
    db.commit()
    return result


@router.post("/pipeline-continuity")
def continuity(payload: Continuity, request: Request, db=Depends(get_db)):
    operation = db.get(PipelineOperation, payload.operation_id)
    if not operation or operation.kind != "CONTINUITY":
        raise HTTPException(404, "Continuity challenge unavailable")
    agent, source = bound(db, request, operation.source_id)
    source = s.locked_source(db, source.id)
    if (
        operation.state != "PENDING"
        or not operation.lease_until
        or operation.lease_until <= s.clock(db)
        or operation.configuration.get("generation") != str(source.generation)
        or operation.configuration.get("checkpoint_hash")
        != s.digest(source.live_checkpoint)
    ):
        raise HTTPException(409, "Continuity challenge changed or expired")
    old = source.live_checkpoint.get("sources", {})
    for path, cursor in old.items():
        proof = payload.files.get(path)
        if (
            not proof
            or not proof.get("readable")
            or proof.get("inode") != cursor.get("inode")
            or proof.get("device") != cursor.get("device")
            or proof.get("size", -1) < cursor.get("offset", 0)
        ):
            raise HTTPException(
                409,
                "File continuity lost; bounded recovery or reviewed generation handoff required",
            )
    import fnmatch

    matching = {
        path: proof
        for path, proof in payload.files.items()
        if fnmatch.fnmatchcase(
            (
                path.replace("\\", "/").casefold()
                if source.identity.get("os") == "Windows"
                else path
            ),
            (
                source.identity["path"].replace("\\", "/").casefold()
                if source.identity.get("os") == "Windows"
                else source.identity["path"]
            ),
        )
    }
    if not old and not any(proof.get("readable") for proof in matching.values()):
        raise HTTPException(409, "Readable physical source proof required")
    source.continuity_validated = True
    operation.state = "COMPLETE"
    operation.result = {
        "authenticated_agent_id": str(agent.id),
        "checkpoint_hash": s.digest(source.live_checkpoint),
        "continuity_verified": True,
    }
    s.event(db, source, "CONTINUITY_VERIFY")
    db.commit()
    return operation.result
