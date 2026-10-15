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


def _source_failure(ticket, error, operation_ticket=None):
    """Cleanup is fenced too: an old worker cannot release a replacement lease."""
    kind = getattr(error, "code", getattr(error, "kind", "RUNTIME_ERROR"))
    with SessionLocal() as db:
        source = s.locked_source(db, uuid.UUID(ticket["source_id"]))
        current = s.clock(db)
        owns = (
            source.fence == ticket["fence"]
            and str(source.generation) == ticket["generation"]
            and str(source.owner_id) == ticket["owner_id"]
            and source.lease_mode == ticket["lease_mode"]
            and source.lease_until is not None
            and source.lease_until > current
        )
        if owns:
            source.health = "ERROR"
            source.owner_id = None
            source.lease_until = None
            source.next_run_at = current + timedelta(seconds=60)
            for method in s.methods(db, source):
                method.last_error = kind
        if operation_ticket:
            op = db.scalar(
                select(PipelineOperation)
                .where(PipelineOperation.id == operation_ticket["id"])
                .with_for_update()
            )
            if (
                op
                and op.state == "RUNNING"
                and op.owner_id == OWNER
                and op.fence == operation_ticket["fence"]
                and op.source_id == source.id
                and op.configuration.get("generation") == ticket["generation"]
            ):
                op.state = "UNRECOVERABLE" if op.kind == "RECOVERY" else "FAILED"
                op.result = {"error_code": kind, "new_evidence_required": True}
                op.lease_until = current
        failure, _ = s.operation(
            db,
            source.organization_id,
            "COLLECTION_FAILURE",
            s.digest(ticket),
            {"ticket": ticket},
            None,
            source_id=source.id,
        )
        failure.state = "FAILED"
        failure.result = {"error_code": kind, "ownership_released": owns}
        db.commit()


def run_source(source_id, recovery_id=None, verification=False):
    ticket = operation_ticket = None
    try:
        with SessionLocal() as db:
            source = db.get(PipelineSource, source_id)
            if not source:
                return
            refs = [m for m in s.methods(db, source) if m.enabled]
            if not refs or not any(m.transport == "BACKEND" for m in refs):
                return
            # All active readers, including other transports, must agree before
            # selecting a representative. acquire() repeats this under its lock.
            s.reader_equivalence(db, source)
            if not verification and not all(s.eligible(db, m) for m in refs):
                return
            if (
                verification
                and os.getenv("OPSCONTROL_PIPELINE_RUNTIME_ACCEPTANCE") != "1"
            ):
                return
            ticket = s.acquire(db, source_id, OWNER, 120, verification=verification)
            # Commit the acquisition separately; all subsequent preparation is
            # guarded, and a failed preparation rolls back before fenced cleanup.
            db.commit()
            db.expire_all()  # refresh bindings after waiting for a concurrent handoff
            source = s.locked_source(db, source_id)
            s.check_ticket(db, source, ticket)
            recovery = db.get(PipelineOperation, recovery_id) if recovery_id else None
            if recovery_id:
                if (
                    not recovery
                    or recovery.kind != "RECOVERY"
                    or recovery.source_id != source.id
                    or recovery.organization_id != source.organization_id
                    or not (
                        recovery.state in {"PENDING", "APPROVED"}
                        or recovery.state == "RUNNING"
                        and recovery.lease_until
                        and recovery.lease_until <= s.clock(db)
                    )
                    or s.suspended(db, source)
                ):
                    raise s.PipelineError("RECOVERY_NOT_ELIGIBLE")
                if source.next_run_at and source.next_run_at <= s.clock(db):
                    raise s.PipelineError("LIVE_COLLECTION_HAS_PRIORITY")
                if recovery.configuration.get("generation") != str(source.generation):
                    raise s.PipelineError("RECOVERY_GENERATION_CHANGED")
                op = recovery
            elif verification:
                op = db.scalar(
                    select(PipelineOperation)
                    .where(
                        PipelineOperation.source_id == source.id,
                        PipelineOperation.kind == "VERIFY",
                        PipelineOperation.state == "RUNNING",
                        PipelineOperation.lease_until > s.clock(db),
                    )
                    .with_for_update()
                )
                if not op or op.configuration.get("generation") != str(
                    source.generation
                ):
                    raise s.PipelineError("VERIFICATION_NOT_ELIGIBLE")
            else:
                op = None
            if op:
                op.state = "RUNNING"
                op.fence += 1
                op.owner_id = OWNER
                op.attempts += 1
                op.lease_until = source.lease_until
                operation_ticket = {"id": op.id, "fence": op.fence}
            db.commit()  # persist operation ownership before fallible reader preparation
            source = s.locked_source(db, source_id)
            s.check_ticket(db, source, ticket)
            rows = db.scalars(
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
            ).all()
            jobs = list({j.native_id: j for j in rows}.values())
            source_identity = dict(source.identity)
            cursor = dict(
                source.recovery_checkpoint if recovery_id else source.live_checkpoint
            )
            refs = [m for m in s.methods(db, source) if m.enabled]
            method = sorted(refs, key=lambda m: str(m.id))[0]
            integration = db.get(PipelineIntegration, method.integration_id)
            connection = db.get(PipelineConnection, method.connection_id)
            config = dict(recovery.configuration) if recovery else None
            definition_hash = s.reader_definition(db, method)
            db.expunge(integration)
            db.expunge(method)
            db.expunge(connection)
            for job in jobs:
                db.expunge(job)
            db.commit()
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
        for record in records:
            record["runtime_origin"] = "AUTHENTICATED_RUNTIME"
            record["reader_definition_hash"] = definition_hash
        with SessionLocal() as db:
            source = s.locked_source(db, source_id)
            s.check_ticket(db, source, ticket)
            op = (
                db.scalar(
                    select(PipelineOperation)
                    .where(PipelineOperation.id == operation_ticket["id"])
                    .with_for_update()
                )
                if operation_ticket
                else None
            )
            if operation_ticket and (
                not op
                or op.state != "RUNNING"
                or op.owner_id != OWNER
                or op.fence != operation_ticket["fence"]
                or not op.lease_until
                or op.lease_until <= s.clock(db)
            ):
                raise s.PipelineError("OPERATION_CLAIM_EXPIRED")
            result = s.accept(
                db,
                ticket,
                records,
                checkpoint,
                complete,
                recovery_operation=op if recovery_id else None,
            )
            if recovery_id:
                op.state = "COMPLETE" if complete else "PENDING"
                op.result = {**op.result, **result, "complete_inventory": complete}
                if op.attempts >= 3 and not complete:
                    op.state = "UNRECOVERABLE"
                    op.result = {**op.result, "new_evidence_required": True}
            db.commit()
    except Exception as error:
        # Session context exit has rolled back preparation/evidence before any
        # cleanup transaction. Never let a failed transaction leak a checkpoint.
        if ticket is None:
            raise
        _source_failure(ticket, error, operation_ticket)


def read_only_connection(db, integration, op):
    """Inventory authorization is independent of collection runtime acceptance."""
    from app.models import Organization
    from app.security.models import User
    from app.security.access_control import resolve_access
    from app.pipeline_adapters import ADAPTER_DEFINITIONS, PLATFORM_ADAPTERS
    from app.pipeline_adapters.core import Adapter, secret

    if (
        not integration
        or integration.deleted_at
        or integration.platform not in ADAPTER_DEFINITIONS
    ):
        raise s.PipelineError("INTEGRATION_UNAVAILABLE")
    customer = db.get(Organization, integration.organization_id)
    user = db.get(User, op.actor_id or integration.owner_id)
    principal = resolve_access(db, user) if user and user.active else None
    if (
        not customer
        or not customer.active
        or not principal
        or not principal.allows("etl.configure", integration.organization_id)
    ):
        raise s.PipelineError("DISCOVERY_NOT_AUTHORIZED")
    if op.kind not in {"DISCOVERY", "REDETECTION"}:
        raise s.PipelineError("READ_ONLY_OPERATION_UNSUPPORTED")
    if op.kind == "DISCOVERY" and integration.platform in {"PENTAHO", "CUSTOM"}:
        raise s.PipelineError(
            "AUTHORITATIVE_DISCOVERY_UNAVAILABLE_MANUAL_REGISTRATION_REQUIRED"
        )
    connection = db.scalar(
        select(PipelineConnection)
        .where(
            PipelineConnection.integration_id == integration.id,
            PipelineConnection.organization_id == integration.organization_id,
            PipelineConnection.active.is_(True),
        )
        .order_by(PipelineConnection.version.desc())
    )
    if not connection:
        raise s.PipelineError("AUTHORIZED_CONNECTION_REQUIRED")
    cfg = s.bounded(
        connection.configuration, organization_id=integration.organization_id
    )
    descriptor = ADAPTER_DEFINITIONS[integration.platform]
    # Execution selectors are not prerequisites for a read-only inventory. All
    # actual connection/authority fields still use the existing adapter validator.
    excluded = {"dag_id", "task_id", "job_name", "jobchain", "component_ids", "path"}
    validator = type(
        "InventoryConnection",
        (Adapter,),
        {
            "platform": integration.platform,
            "capabilities": tuple(descriptor["capabilities"]),
            "step_semantics": PLATFORM_ADAPTERS[integration.platform].step_semantics,
            "fields": tuple(descriptor["fields"]),
            "required": tuple(k for k in descriptor["required"] if k not in excluded),
        },
    )(cfg)
    for key, value in cfg.items():
        if key.endswith("_ref") and value:
            secret(value)
    if integration.platform == "AWS_GLUE" and not cfg.get("profile_name"):
        raise s.PipelineError("CUSTOMER_BOUND_AWS_PROFILE_REQUIRED")
    return connection, validator


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
        try:
            connection, validator = read_only_connection(db, integration, op)
        except Exception as error:
            op.state = "BLOCKED"
            op.result = {
                "code": getattr(
                    error, "code", getattr(error, "kind", "CONNECTION_NOT_AUTHORIZED")
                ),
                "absence_reconciliation": False,
            }
            db.commit()
            return
        op.state = "RUNNING"
        op.fence += 1
        op.owner_id = OWNER
        operation_fence = op.fence
        operation_kind = op.kind
        integration_revision = integration.revision
        connection_id = connection.id
        connection_checksum = connection.checksum
        op.attempts += 1
        op.lease_until = s.clock(db) + timedelta(seconds=120)
        db.expunge(connection)
        db.expunge(integration)
        db.commit()
    try:
        if operation_kind == "DISCOVERY":
            inventory, complete = discover(integration, connection)
        else:
            result = validator.discover_capabilities()
            result["platform"] = integration.platform
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
            active_connection, _ = read_only_connection(db, row, current)
            if (
                row.revision != integration_revision
                or active_connection.id != connection_id
                or active_connection.checksum != connection_checksum
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
            current = db.scalar(
                select(PipelineOperation)
                .where(PipelineOperation.id == id)
                .with_for_update()
            )
            if (
                current
                and current.state == "RUNNING"
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
                    or_(
                        PipelineOperation.state.in_(("PENDING", "APPROVED")),
                        (PipelineOperation.state == "RUNNING")
                        & (PipelineOperation.lease_until <= current),
                    ),
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
