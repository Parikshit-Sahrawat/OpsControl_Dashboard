"""Durable source scheduling; provider I/O occurs outside the commit transaction."""

import os
import uuid
from datetime import timedelta, datetime
from sqlalchemy import select, text, or_
from app.db.session import SessionLocal
from app.data_pipelines.models import (
    PipelineAssociation,
    PipelineCapability,
    PipelineConnection,
    PipelineHold,
    PipelineIntegration,
    PipelineJob,
    PipelineMethod,
    PipelineOperation,
    PipelineSource,
)
from app.data_pipelines import service as s
from app.data_pipelines.bridge import collect_method, discover

OWNER = uuid.uuid4()


def run_source(source_id, recovery_id=None, verification=False):
    with SessionLocal() as db:
        source = db.get(PipelineSource, source_id)
        if not source:
            return
        refs = [
            m for m in s.methods(db, source) if m.enabled and m.transport == "BACKEND"
        ]
        if not refs:
            return
        # A shared physical unit is read once, using a validated representative
        # connection. Job associations across integrations are combined explicitly.
        method = sorted(refs, key=lambda m: str(m.id))[0]
        integration = db.get(PipelineIntegration, method.integration_id)
        connection = db.get(PipelineConnection, method.connection_id)
        if not verification and not all(s.eligible(db, m) for m in refs):
            return
        if verification and os.getenv("OPSCONTROL_PIPELINE_RUNTIME_ACCEPTANCE") != "1":
            return
        ticket = s.acquire(db, source_id, OWNER, 120, verification=verification)
        rows = (
            db.execute(
                select(PipelineJob)
                .join(PipelineAssociation, PipelineAssociation.job_id == PipelineJob.id)
                .join(
                    PipelineMethod, PipelineMethod.id == PipelineAssociation.method_id
                )
                .where(
                    PipelineMethod.source_id == source.id,
                    PipelineAssociation.generation == source.generation,
                    PipelineMethod.enabled.is_(True),
                    PipelineJob.selected.is_(True),
                    PipelineJob.quarantined.is_(False),
                )
            )
            .scalars()
            .all()
        )
        jobs = list({j.native_id: j for j in rows}.values())
        source_identity = dict(source.identity)
        cursor = source.recovery_checkpoint if recovery_id else source.live_checkpoint
        recovery = db.get(PipelineOperation, recovery_id) if recovery_id else None
        if recovery:
            if source.next_run_at and source.next_run_at <= s.clock(db):
                raise s.PipelineError("LIVE_COLLECTION_HAS_PRIORITY")
            if recovery.state not in {"PENDING", "APPROVED"} or s.suspended(db, source):
                raise s.PipelineError("RECOVERY_NOT_ELIGIBLE")
            if recovery.configuration["generation"] != str(source.generation):
                raise s.PipelineError("RECOVERY_GENERATION_CHANGED")
            recovery.state = "RUNNING"
            recovery.fence += 1
            recovery.owner_id = OWNER
            recovery_fence = recovery.fence
            recovery.attempts += 1
            recovery.lease_until = s.clock(db) + timedelta(seconds=120)
        # Detached snapshots: no session lock or transaction crosses provider I/O.
        db.expunge(integration)
        db.expunge(method)
        db.expunge(connection)
        for job in jobs:
            db.expunge(job)
        config = dict(recovery.configuration) if recovery else None
        db.commit()
    try:
        if config:
            if integration.platform not in {"ADF", "NIFI"}:
                raise s.PipelineError("BOUNDED_PROVIDER_REPLAY_NOT_SUPPORTED")
            connection.configuration = (
                {
                    **connection.configuration,
                    "after": config["start"],
                    "before": config["end"],
                }
                if integration.platform == "ADF"
                else {**connection.configuration, "after": config["start"]}
            )
        records, checkpoint, complete = collect_method(
            integration,
            method,
            connection,
            jobs,
            cursor,
            source_identity=source_identity,
        )
        if config:
            start = datetime.fromisoformat(config["start"])
            end = datetime.fromisoformat(config["end"])
            records = [
                r
                for r in records
                if start <= datetime.fromisoformat(r["observed_at"]) <= end
            ]
        with SessionLocal() as definition_db:
            definition_hash = s.reader_definition(
                definition_db, definition_db.get(PipelineMethod, method.id)
            )
        for record in records:
            record["runtime_origin"] = "AUTHENTICATED_RUNTIME"
            record["reader_definition_hash"] = definition_hash
        with SessionLocal() as db:
            op = db.get(PipelineOperation, recovery_id) if recovery_id else None
            result = s.accept(
                db, ticket, records, checkpoint, complete, recovery_operation=op
            )
            source = s.locked_source(db, source_id)
            if not recovery_id:
                source.next_run_at = s.clock(db) + timedelta(
                    seconds=min(
                        m.configuration.get("interval_seconds", 60)
                        for m in s.methods(db, source)
                        if m.enabled
                    )
                )
            if op:
                op.state = "COMPLETE" if complete else "PENDING"
                op.result = {**op.result, **result, "complete_inventory": complete}
                if op.attempts >= 3 and not complete:
                    op.state = "UNRECOVERABLE"
                    op.result = {**op.result, "new_evidence_required": True}
            db.commit()
    except Exception as error:
        kind = getattr(error, "code", getattr(error, "kind", "RUNTIME_ERROR"))
        with SessionLocal() as db:
            source = s.locked_source(db, source_id)
            # An obsolete worker cannot overwrite health or release the new owner.
            if (
                source.fence == ticket["fence"]
                and str(source.generation) == ticket["generation"]
            ):
                source.health = "ERROR"
                source.lease_until = s.clock(db)
                source.next_run_at = s.clock(db) + timedelta(seconds=60)
                for m in s.methods(db, source):
                    m.last_error = kind
            if recovery_id:
                op = db.get(PipelineOperation, recovery_id)
                if (
                    op
                    and op.state == "RUNNING"
                    and op.owner_id == OWNER
                    and op.fence == recovery_fence
                ):
                    op.state = "UNRECOVERABLE"
                    op.result = {"error_code": kind, "new_evidence_required": True}
            db.commit()


def run_operation(id):
    with SessionLocal() as db:
        op = db.scalar(
            select(PipelineOperation)
            .where(PipelineOperation.id == id)
            .with_for_update()
        )
        if not op or op.state not in {"PENDING", "RUNNING"}:
            return
        if op.lease_until and op.lease_until > s.clock(db):
            return
        integration = db.get(PipelineIntegration, op.integration_id)
        refs = (
            list(
                db.scalars(
                    select(PipelineMethod).where(
                        PipelineMethod.integration_id == integration.id,
                        PipelineMethod.enabled.is_(True),
                    )
                )
            )
            if integration
            else []
        )
        if (
            not integration
            or not integration.enabled
            or not refs
            or not all(s.eligible(db, m) for m in refs)
        ):
            op.state = "BLOCKED"
            op.result = {"code": "LIVE_ACCEPTANCE_DEFERRED_OR_UNVERIFIED"}
            db.commit()
            return
        connection = db.get(PipelineConnection, refs[0].connection_id)
        op.state = "RUNNING"
        op.fence += 1
        op.owner_id = OWNER
        operation_fence = op.fence
        operation_kind = op.kind
        integration_revision = integration.revision
        source_versions = {
            m.source_id: (
                db.get(PipelineSource, m.source_id).generation,
                db.get(PipelineSource, m.source_id).revision,
            )
            for m in refs
        }
        op.attempts += 1
        op.lease_until = s.clock(db) + timedelta(seconds=120)
        db.expunge(connection)
        db.expunge(integration)
        db.commit()
    try:
        if operation_kind == "DISCOVERY":
            inventory, complete = discover(integration, connection)
        else:
            from app.pipeline_adapters import PLATFORM_ADAPTERS

            result = PLATFORM_ADAPTERS[integration.platform](
                connection.configuration
            ).discover_capabilities()
            inventory = []
            complete = False
        with SessionLocal() as db:
            current = db.scalar(
                select(PipelineOperation)
                .where(PipelineOperation.id == id)
                .with_for_update()
            )
            if (
                current.state != "RUNNING"
                or current.lease_until <= s.clock(db)
                or current.fence != operation_fence
                or current.owner_id != OWNER
            ):
                return
            row = db.get(PipelineIntegration, current.integration_id)
            if (
                not row.enabled
                or row.revision != integration_revision
                or any(
                    (
                        s.locked_source(db, sid).generation,
                        s.locked_source(db, sid).revision,
                    )
                    != version
                    or s.suspended(db, s.locked_source(db, sid))
                    for sid, version in source_versions.items()
                )
            ):
                current.state = "BLOCKED"
                db.commit()
                return
            if current.kind == "DISCOVERY":
                current.result = s.reconcile_discovery(
                    db, row, inventory, complete, True, current.actor_id
                )
                current.result = {
                    **current.result,
                    "inventory_native_ids": [x["native_id"] for x in inventory],
                }
            else:
                row.last_redetection_at = s.clock(db)
                current.result = {
                    "capabilities": result,
                    "evidence_status": "DOCUMENTED",
                    "runtime_verified": False,
                }
            current.state = (
                "COMPLETE"
                if complete or current.kind == "REDETECTION"
                else "INCOMPLETE"
            )
            db.commit()
    except Exception as error:
        with SessionLocal() as db:
            current = db.get(PipelineOperation, id)
            if (
                current.state == "RUNNING"
                and current.fence == operation_fence
                and current.owner_id == OWNER
            ):
                current.state = "FAILED"
                current.result = {
                    "code": getattr(
                        error, "code", getattr(error, "kind", "PROVIDER_ERROR")
                    ),
                    "complete": False,
                    "absence_reconciliation": False,
                }
                db.commit()


def tick(dispatch=True):
    """60-second durable reconciliation; daily discovery/cleanup and weekly detection."""
    with SessionLocal() as db:
        if not db.scalar(text("SELECT pg_try_advisory_xact_lock(1867331601)")):
            return
        current = s.clock(db)
        slot = "GLOBAL_60_SECOND_RECONCILIATION"
        for integration in db.scalars(
            select(PipelineIntegration).where(PipelineIntegration.deleted_at.is_(None))
        ):
            gate, new = s.operation(
                db,
                integration.organization_id,
                "RECONCILE",
                str(integration.id) + ":" + slot,
                {},
                None,
                integration_id=integration.id,
            )
            if not new and gate.lease_until and gate.lease_until > current:
                continue
            gate.lease_until = current + timedelta(seconds=60)
            for method in db.scalars(
                select(PipelineMethod).where(
                    PipelineMethod.integration_id == integration.id
                )
            ):
                if not integration.enabled:
                    s.hold(db, method.source_id, "INTEGRATION", str(integration.id))
                else:
                    source = s.locked_source(db, method.source_id)
                    interval = max(
                        120, int(method.configuration.get("interval_seconds", 60)) * 3
                    )
                    if (
                        source.health in {"RECEIVING", "IDLE"}
                        and source.last_observed_at
                        and (current - source.last_observed_at).total_seconds()
                        > interval
                    ):
                        source.health = "NO_DATA"
            for kind, stamp, period in (
                ("DISCOVERY", integration.last_discovery_at, 24 * 3600),
                ("REDETECTION", integration.last_redetection_at, 7 * 86400),
            ):
                if integration.enabled and (
                    not stamp or (current - stamp).total_seconds() >= period
                ):
                    s.operation(
                        db,
                        integration.organization_id,
                        kind,
                        str(integration.id) + ":" + current.strftime("%Y-%m-%d"),
                        {},
                        None,
                        integration_id=integration.id,
                    )
            clean, new = s.operation(
                db,
                integration.organization_id,
                "CLEANUP",
                current.strftime("%Y-%m-%d"),
                {},
                None,
            )
            if new:
                clean.result = s.cleanup(db)
                clean.state = "COMPLETE"
            gate.state = "COMPLETE"
        due = list(
            db.scalars(
                select(PipelineSource.id)
                .where(
                    or_(
                        PipelineSource.next_run_at.is_(None),
                        PipelineSource.next_run_at <= current,
                    ),
                    ~select(PipelineHold.id)
                    .where(
                        PipelineHold.source_id == PipelineSource.id,
                        PipelineHold.released_at.is_(None),
                        PipelineHold.kind != "LEGAL",
                    )
                    .exists(),
                    select(PipelineMethod.id)
                    .join(
                        PipelineCapability,
                        PipelineCapability.id == PipelineMethod.capability_id,
                    )
                    .join(
                        PipelineIntegration,
                        PipelineIntegration.id == PipelineMethod.integration_id,
                    )
                    .where(
                        PipelineMethod.source_id == PipelineSource.id,
                        PipelineMethod.enabled.is_(True),
                        PipelineMethod.transport == "BACKEND",
                        PipelineMethod.validation == "VALID",
                        PipelineCapability.evidence_status == "RUNTIME_VERIFIED",
                        PipelineSource.continuity_validated.is_(True),
                        PipelineIntegration.enabled.is_(True),
                        PipelineIntegration.deleted_at.is_(None),
                    )
                    .exists(),
                )
                .order_by(PipelineSource.id)
                .limit(16)
            )
        )
        operations = list(
            db.scalars(
                select(PipelineOperation.id)
                .where(
                    PipelineOperation.kind.in_(("DISCOVERY", "REDETECTION")),
                    or_(
                        PipelineOperation.state == "PENDING",
                        (PipelineOperation.state == "RUNNING")
                        & (PipelineOperation.lease_until <= current),
                    ),
                )
                .limit(16)
            )
        )
        recoveries = list(
            db.scalars(
                select(PipelineOperation.id)
                .where(
                    PipelineOperation.kind == "RECOVERY",
                    PipelineOperation.state.in_(("PENDING", "APPROVED")),
                )
                .limit(8)
            )
        )
        db.commit()
    work = {"sources": due, "operations": operations, "recoveries": recoveries}
    if not dispatch:
        return work
    for sid in due:
        try:
            run_source(sid)
        except s.PipelineError:
            pass
    for oid in operations:
        run_operation(oid)
    for oid in recoveries:
        with SessionLocal() as db:
            row = db.get(PipelineOperation, oid)
            sid = row.source_id
        try:
            run_source(sid, oid)
        except s.PipelineError:
            pass
