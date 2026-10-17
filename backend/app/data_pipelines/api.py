"""Scoped V1.6 APIs. Live provider reads are never triggered by saving drafts."""

from typing import Literal

import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from app.db.session import get_db
from app.security.access_control import require_permission
from app.security.scope import current_principal
from app.security.http import require_admin
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
from app.data_pipelines import service as s
from app.pipeline_adapters import ADAPTER_DEFINITIONS, CONFIG_SCHEMAS
from app.pipeline_adapters.pentaho_contracts import PENTAHO_VERSION_CANDIDATES

router = APIRouter(prefix="/api/v1/data-pipelines", tags=["Data Pipelines V1.6"])


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Mutation(Strict):
    idempotency_key: str = Field(min_length=1, max_length=100)
    expected_revision: int | None = Field(default=None, ge=1)


class IntegrationInput(Mutation):
    organization_id: uuid.UUID
    name: str = Field(min_length=1, max_length=200)
    platform: str
    environment: str
    vm_resource_id: uuid.UUID | None = None
    configuration: dict = Field(default_factory=dict)
    stage: int = Field(default=1, ge=1, le=8)


class ConfigurationInput(Mutation):
    configuration: dict


class CapabilityInput(Mutation):
    platform_version: str = Field(min_length=1, max_length=100)
    edition: str = Field(min_length=1, max_length=100)
    deployment_type: str = Field(min_length=1, max_length=50)
    supported_methods: list[str] = Field(min_length=1, max_length=4)
    required_permissions: list[str] = Field(default_factory=list, max_length=30)
    authentication_requirements: list[str] = Field(default_factory=list, max_length=10)


class MethodInput(Mutation):
    name: str = Field(min_length=1, max_length=200)
    method_type: str
    transport: str
    identity: dict
    connection_id: uuid.UUID
    capability_id: uuid.UUID
    configuration: dict = Field(default_factory=dict)
    enabled: bool = True


class JobInput(Mutation):
    native_id: str = Field(min_length=1, max_length=500)
    name: str = Field(min_length=1, max_length=200)
    resource_id: uuid.UUID | None = None


class SelectionInput(Mutation):
    selected: bool
    confirmed: bool


class AssociationInput(Mutation):
    job_id: uuid.UUID
    method_id: uuid.UUID
    confirmed: bool


class HoldInput(Mutation):
    kind: str
    reference: str = Field(min_length=1, max_length=100)


class RecoveryInput(Mutation):
    mode: Literal["ACCEPTED_PENTAHO_EVIDENCE"] | None = None
    start: datetime
    end: datetime
    manual: bool = False


class ActionInput(Mutation):
    confirmed: bool = False


def actor():
    p = current_principal.get()
    if not p:
        raise HTTPException(401, "Authentication required")
    return p


def checked(db, model, id, write=False):
    row = db.scalar(
        select(model).where(model.id == id).with_for_update()
        if write
        else select(model).where(model.id == id)
    )
    if not row:
        raise HTTPException(404, "Record unavailable")
    require_permission("etl.configure" if write else "etl.view", row.organization_id)
    return row


def doc(row):
    from app.telemetry.api import item
    from fastapi.encoders import jsonable_encoder

    return jsonable_encoder(item(row))


def finish(db):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            409, "Concurrent change or invalid scoped relationship"
        ) from None


def revision(row, payload):
    if payload.expected_revision != row.revision:
        raise HTTPException(409, "Refresh the changed configuration")


def mutate(db, row, kind, payload):
    op, new = s.operation(
        db,
        row.organization_id,
        kind,
        payload.idempotency_key,
        {"target_id": str(row.id), **payload.model_dump(mode="json")},
        actor().user_id,
        integration_id=row.id if isinstance(row, PipelineIntegration) else None,
        source_id=row.id if isinstance(row, PipelineSource) else None,
    )
    if not new:
        return op, False
    if payload.expected_revision is not None:
        revision(row, payload)
    return op, True


@router.get("/catalogue")
def catalogue():
    require_permission("etl.view")
    return {
        "discovery_interval_hours": 24,
        "redetection_interval_days": 7,
        "reconciliation_interval_seconds": 60,
        "recovery_bounds_seconds": s.RECOVERY_BOUNDS,
        "platforms": [
            {
                "platform": p,
                "versions": [
                    {
                        "version": v,
                        "candidate_only": True,
                        "compatibility": "UNVERIFIED",
                        "evidence_status": "DOCUMENTED",
                    }
                    for v in (
                        PENTAHO_VERSION_CANDIDATES
                        if p == "PENTAHO"
                        else ["Operator-supplied installed version"]
                    )
                ],
                "adapter": ADAPTER_DEFINITIONS[p],
                "schema": CONFIG_SCHEMAS[p],
            }
            for p in sorted(s.PLATFORMS)
        ],
    }


@router.get("/integrations")
def list_integrations(
    organization_id: uuid.UUID | None = None,
    search: str = "",
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db=Depends(get_db),
):
    stmt = select(PipelineIntegration).where(PipelineIntegration.deleted_at.is_(None))
    if organization_id:
        require_permission("etl.view", organization_id)
        stmt = stmt.where(PipelineIntegration.organization_id == organization_id)
    if search:
        stmt = stmt.where(PipelineIntegration.name.ilike("%" + search[:200] + "%"))
    return {
        "items": [
            doc(r)
            for r in db.scalars(
                stmt.order_by(PipelineIntegration.name, PipelineIntegration.id)
                .offset(offset)
                .limit(limit)
            )
        ],
        "total": db.scalar(select(func.count()).select_from(stmt.subquery())),
    }


@router.post("/integrations", status_code=201)
def create_integration(payload: IntegrationInput, db=Depends(get_db)):
    require_permission("resources.create", payload.organization_id)
    require_permission("etl.configure", payload.organization_id)
    from app.models import Organization
    from app.unified.models import MonitoringResource

    org = db.get(Organization, payload.organization_id)
    if not org or not org.active:
        raise HTTPException(404, "Organization unavailable")
    if payload.platform not in s.PLATFORMS or payload.environment not in {
        "PROD",
        "QA",
        "TEST",
        "DEV",
        "SANDBOX",
    }:
        raise HTTPException(422, "Supported platform and environment required")
    if payload.vm_resource_id:
        vm = checked(db, MonitoringResource, payload.vm_resource_id)
        if (
            vm.domain != "VM"
            or vm.organization_id != payload.organization_id
            or vm.environment != payload.environment
        ):
            raise HTTPException(
                422,
                "Customer/environment must be inherited from the selected Compute Instance",
            )
    config = s.bounded(payload.configuration, organization_id=payload.organization_id)
    op, new = s.operation(
        db,
        payload.organization_id,
        "INTEGRATION_CREATE",
        payload.idempotency_key,
        payload.model_dump(mode="json"),
        actor().user_id,
    )
    if not new:
        return doc(checked(db, PipelineIntegration, uuid.UUID(op.result["id"])))
    row = PipelineIntegration(
        organization_id=payload.organization_id,
        name=payload.name,
        platform=payload.platform,
        environment=payload.environment,
        vm_resource_id=payload.vm_resource_id,
        configuration=config,
        stage=payload.stage,
        owner_id=actor().user_id,
    )
    db.add(row)
    db.flush()
    op.integration_id = row.id
    op.state = "COMPLETE"
    op.result = {"id": str(row.id)}
    s.event(db, row, "CREATE", actor().user_id)
    finish(db)
    return doc(row)


@router.get("/integrations/{id}")
def detail(id: uuid.UUID, db=Depends(get_db)):
    row = checked(db, PipelineIntegration, id)
    output = doc(row)
    for key, model in (
        ("connections", PipelineConnection),
        ("capabilities", PipelineCapability),
        ("methods", PipelineMethod),
        ("jobs", PipelineJob),
        ("operations", PipelineOperation),
    ):
        output[key] = [
            doc(x)
            for x in db.scalars(
                select(model)
                .where(model.integration_id == id)
                .order_by(model.created_at)
                .limit(500)
            )
        ]
    mids = [x["id"] for x in output["methods"]]
    output["associations"] = [
        doc(x)
        for x in db.scalars(
            select(PipelineAssociation).where(
                PipelineAssociation.method_id.in_([uuid.UUID(x) for x in mids])
            )
        )
    ]
    output["sources"] = [
        doc(x)
        for x in db.scalars(
            select(PipelineSource).where(
                PipelineSource.id.in_(
                    [uuid.UUID(x["source_id"]) for x in output["methods"]]
                )
            )
        )
    ]
    output["activation_blockers"] = s.blockers(db, row)
    output["coverage"] = {
        "selected_jobs": db.scalar(
            select(func.count())
            .select_from(PipelineJob)
            .where(PipelineJob.integration_id == id, PipelineJob.selected.is_(True))
        ),
        "unverified_methods": sum(
            not s.eligible(db, x)
            for x in db.scalars(
                select(PipelineMethod).where(PipelineMethod.integration_id == id)
            )
        ),
    }
    return output


@router.put("/integrations/{id}")
def edit_integration(id: uuid.UUID, payload: IntegrationInput, db=Depends(get_db)):
    row = checked(db, PipelineIntegration, id, True)
    op, new = mutate(db, row, "DRAFT_EDIT", payload)
    if not new:
        return doc(row)
    revision(row, payload)
    if (row.organization_id, row.platform, row.environment, row.vm_resource_id) != (
        payload.organization_id,
        payload.platform,
        payload.environment,
        payload.vm_resource_id,
    ):
        raise HTTPException(
            409,
            "Resource identity requires a reviewed handoff; generic editing cannot change ownership",
        )
    row.name = payload.name
    row.stage = payload.stage
    row.configuration = s.bounded(
        payload.configuration, organization_id=row.organization_id
    )
    row.revision += 1
    op.state = "COMPLETE"
    s.event(db, row, "EDIT", actor().user_id)
    finish(db)
    return doc(row)


@router.post("/integrations/{id}/connections", status_code=201)
def add_connection(id: uuid.UUID, payload: ConfigurationInput, db=Depends(get_db)):
    row = checked(db, PipelineIntegration, id, True)
    row = db.scalar(
        select(PipelineIntegration)
        .where(PipelineIntegration.id == row.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    op, new = mutate(db, row, "CONNECTION_VERSION", payload)
    if not new:
        return doc(checked(db, PipelineConnection, uuid.UUID(op.result["id"])))
    cfg = s.bounded(payload.configuration, organization_id=row.organization_id)
    allowed = set(ADAPTER_DEFINITIONS[row.platform]["fields"])
    if set(cfg) - allowed:
        raise HTTPException(422, "Unsupported adapter connection fields")
    if row.platform == "PENTAHO" and "monitoring_context" in cfg:
        from app.pipeline_adapters.pentaho_observations import context
        from app.pipeline_adapters.core import AdapterError

        try:
            context(cfg["monitoring_context"])
        except AdapterError as error:
            raise HTTPException(422, {"code": "PENTAHO_" + error.kind}) from None
    for key, value in cfg.items():
        if key in {"base_url", "url"}:
            from urllib.parse import urlsplit

            p = urlsplit(value)
            if p.scheme != "https" or p.username or p.password or p.query or p.fragment:
                raise HTTPException(422, "Credential-free HTTPS endpoint required")
    version = (
        db.scalar(
            select(func.max(PipelineConnection.version)).where(
                PipelineConnection.integration_id == id
            )
        )
        or 0
    ) + 1
    connection = PipelineConnection(
        organization_id=row.organization_id,
        integration_id=id,
        version=version,
        configuration=cfg,
        checksum=s.digest(cfg),
        active=version == 1,
    )
    db.add(connection)
    db.flush()
    row.revision += 1
    op.state = "COMPLETE"
    op.result = {"id": str(connection.id), "saving_is_not_deployment": True}
    s.event(db, connection, "CONNECTION_VERSION", actor().user_id)
    finish(db)
    return doc(connection)


@router.post("/integrations/{id}/capabilities", status_code=201)
def add_capability(id: uuid.UUID, payload: CapabilityInput, db=Depends(get_db)):
    row = checked(db, PipelineIntegration, id, True)
    op, new = mutate(db, row, "CAPABILITY_PROFILE", payload)
    if not new:
        return doc(checked(db, PipelineCapability, uuid.UUID(op.result["id"])))
    if set(payload.supported_methods) - s.METHODS:
        raise HTTPException(422, "Unsupported collection method")
    capability = PipelineCapability(
        organization_id=row.organization_id,
        integration_id=id,
        platform_version=payload.platform_version,
        edition=payload.edition,
        deployment_type=payload.deployment_type,
        definition={
            "supported_methods": payload.supported_methods,
            "required_permissions": payload.required_permissions,
            "authentication_requirements": payload.authentication_requirements,
        },
        compatibility="UNVERIFIED",
        evidence_status="DOCUMENTED",
    )
    db.add(capability)
    db.flush()
    op.state = "COMPLETE"
    op.result = {"id": str(capability.id)}
    s.event(db, capability, "PROFILE_CREATE", actor().user_id)
    finish(db)
    return doc(capability)


@router.post("/integrations/{id}/methods", status_code=201)
def add_method(id: uuid.UUID, payload: MethodInput, db=Depends(get_db)):
    row = checked(db, PipelineIntegration, id, True)
    require_permission("collectors.manage", row.organization_id)
    op, new = mutate(db, row, "METHOD_CREATE", payload)
    if not new:
        return doc(checked(db, PipelineMethod, uuid.UUID(op.result["id"])))
    identity, key = s.canonical(payload.method_type, payload.identity)
    connection = checked(db, PipelineConnection, payload.connection_id)
    capability = checked(db, PipelineCapability, payload.capability_id)
    if (
        connection.integration_id != id
        or capability.integration_id != id
        or payload.transport not in {"AGENT", "BACKEND"}
    ):
        raise HTTPException(
            422, "Integration-owned connection, capability and valid transport required"
        )
    if payload.method_type == "FILE_LOG":
        from app.unified.models import MonitoringResource

        vm = checked(db, MonitoringResource, uuid.UUID(identity["host_resource_id"]))
        if vm.domain != "VM" or vm.id != row.vm_resource_id:
            raise HTTPException(
                422, "File source must belong to the inherited Compute Instance"
            )
        from app.models import DataSource
        from app.telemetry.configuration import host_os

        data_source = db.get(DataSource, vm.data_source_id)
        if not data_source or identity["os"] != host_os(data_source):
            raise HTTPException(
                422, "File source OS must match the supported inherited host OS"
            )
    elif identity["platform"] != row.platform:
        raise HTTPException(422, "Source platform differs from integration")
    cfg = s.bounded(payload.configuration, organization_id=row.organization_id)
    if payload.method_type == "PLATFORM_API" and row.platform not in {"SSIS", "CUSTOM"}:
        endpoint = connection.configuration.get(
            "base_url"
        ) or connection.configuration.get("url")
        if row.platform == "AWS_GLUE":
            region = connection.configuration.get("region", "")
            effective = {**connection.configuration, **cfg.get("adapter_overrides", {})}
            if not effective.get("profile_name"):
                raise HTTPException(
                    422,
                    "A provisioned customer-bound AWS profile is required; backend default credentials cannot be delegated",
                )
            suffix = "amazonaws.com.cn" if region.startswith("cn-") else "amazonaws.com"
            endpoint = "https://glue." + region + "." + suffix
            if (
                not region
                or not identity["account"].isdigit()
                or len(identity["account"]) != 12
                or identity["physical_scope"] != "region:" + region
            ):
                raise HTTPException(
                    422,
                    "Glue requires its 12-digit account ID and region:<configured-region> physical scope",
                )
        if (
            not endpoint
            or s.canonical("PLATFORM_API", {**identity, "endpoint": endpoint})[0][
                "endpoint"
            ]
            != identity["endpoint"]
        ):
            raise HTTPException(
                422,
                "Canonical endpoint must match the immutable connection destination",
            )
    if payload.transport == "AGENT" and payload.method_type != "FILE_LOG":
        raise HTTPException(
            422,
            "This Agent transport supports structured File Log sources; platform API/database sources use backend adapters",
        )
    if payload.method_type == "FILE_LOG" and payload.transport != "AGENT":
        raise HTTPException(
            422, "Host file sources require the source-bound Agent transport"
        )
    allowed = {
        "interval_seconds",
        "adapter_overrides",
        "native_identity_field",
        "collector_method_id",
    }
    if (
        set(cfg) - allowed
        or not isinstance(cfg.get("interval_seconds", 60), int)
        or not 5 <= cfg.get("interval_seconds", 60) <= 3600
    ):
        raise HTTPException(422, "Bounded method configuration required")
    s.validate_reader_target(
        row.platform,
        payload.method_type,
        identity,
        {**connection.configuration, **cfg.get("adapter_overrides", {})},
    )
    source = db.scalar(
        select(PipelineSource)
        .where(
            PipelineSource.organization_id == row.organization_id,
            PipelineSource.canonical_key == key,
        )
        .with_for_update()
    )
    if not source:
        # The unique physical unit must also survive simultaneous onboarding.
        db.execute(
            insert(PipelineSource)
            .values(
                organization_id=row.organization_id,
                method_type=payload.method_type,
                canonical_key=key,
                identity=identity,
                continuity_validated=True,
            )
            .on_conflict_do_nothing(index_elements=["organization_id", "canonical_key"])
        )
        source = db.scalar(
            select(PipelineSource)
            .where(
                PipelineSource.organization_id == row.organization_id,
                PipelineSource.canonical_key == key,
            )
            .with_for_update()
        )
    if any(m.transport != payload.transport for m in s.methods(db, source)):
        raise HTTPException(
            409,
            "Shared source already uses another transport; preview and approve a fenced handoff",
        )
    if any(m.integration_id == id for m in s.methods(db, source)):
        raise HTTPException(
            409, "This integration already references the canonical physical source"
        )
    source.revision += 1
    method = PipelineMethod(
        organization_id=row.organization_id,
        integration_id=id,
        source_id=source.id,
        connection_id=connection.id,
        capability_id=capability.id,
        name=payload.name,
        transport=payload.transport,
        configuration={**cfg, "method_type": payload.method_type},
        enabled=payload.enabled,
        validation="VALID",
    )
    db.add(method)
    db.flush()
    s.reader_equivalence(db, source, persist=True)
    row.revision += 1
    if not row.enabled:
        s.hold(db, source.id, "INTEGRATION", str(id), actor().user_id)
    op.state = "COMPLETE"
    op.result = {"id": str(method.id)}
    s.event(db, method, "METHOD_ADD", actor().user_id)
    finish(db)
    return doc(method)


@router.post("/integrations/{id}/jobs", status_code=201)
def register_job(id: uuid.UUID, payload: JobInput, db=Depends(get_db)):
    row = checked(db, PipelineIntegration, id, True)
    op, new = mutate(db, row, "MANUAL_JOB", payload)
    if not new:
        return doc(checked(db, PipelineJob, uuid.UUID(op.result["id"])))
    legacy_pending = False
    if payload.resource_id:
        from app.unified.models import MonitoringResource

        r = checked(db, MonitoringResource, payload.resource_id)
        if not r.configuration.get("pipeline_integration_id"):
            # A staged association is not permission to collect or activate.
            legacy_pending = True
            if (
                r.configuration.get("native_job_id")
                and r.configuration["native_job_id"] != payload.native_id
            ):
                raise HTTPException(409, "Existing native identity cannot be rebound")
            if row.vm_resource_id:
                parent = checked(db, MonitoringResource, row.vm_resource_id)
                if r.linked_vm_id != parent.vm_id:
                    raise HTTPException(
                        409,
                        "Legacy VM inheritance differs; explicit resource migration required",
                    )
        if r.configuration.get("pipeline_integration_id") and (
            r.configuration.get("pipeline_integration_id") != str(id)
            or r.configuration.get("native_job_id") != payload.native_id
        ):
            raise HTTPException(
                409, "Existing V1.6 resource belongs to another verified native job"
            )
        if (
            r.domain != "ETL"
            or r.organization_id != row.organization_id
            or r.environment != row.environment
        ):
            raise HTTPException(422, "Existing Data Pipeline scope does not match")
    job = PipelineJob(
        organization_id=row.organization_id,
        integration_id=id,
        native_id=payload.native_id,
        name=payload.name,
        origin="LEGACY_PENDING" if legacy_pending else "MANUAL",
        quarantined=legacy_pending,
        resource_id=payload.resource_id,
    )
    db.add(job)
    db.flush()
    op.state = "COMPLETE"
    op.result = {"id": str(job.id)}
    s.event(db, job, "JOB_REGISTER", actor().user_id)
    finish(db)
    return doc(job)


@router.post("/jobs/{id}/selection")
def select_job(id: uuid.UUID, payload: SelectionInput, db=Depends(get_db)):
    job = checked(db, PipelineJob, id, True)
    op, new = mutate(db, job, "JOB_SELECTION", payload)
    if not new:
        return doc(job)
    if not payload.confirmed:
        raise HTTPException(422, "Explicit job selection confirmation required")
    if job.quarantined:
        raise HTTPException(409, "Confirm and reconcile the ambiguous identity first")
    if payload.selected and not job.resource_id:
        from app.data_pipelines.bridge import create_job_resource

        db.info["pipeline_initial_job_binding"] = job.id
        job.resource_id = create_job_resource(
            db, db.get(PipelineIntegration, job.integration_id), job
        ).id
    job.selected = payload.selected
    job.revision += 1
    op.state = "COMPLETE"
    s.event(db, job, "JOB_SELECT", actor().user_id)
    finish(db)
    return doc(job)


@router.post("/integrations/{id}/associations", status_code=201)
def associate(id: uuid.UUID, payload: AssociationInput, db=Depends(get_db)):
    row = checked(db, PipelineIntegration, id, True)
    op, new = mutate(db, row, "ASSOCIATION", payload)
    if not new:
        return op.result
    job = checked(db, PipelineJob, payload.job_id)
    method = checked(db, PipelineMethod, payload.method_id)
    if not payload.confirmed or job.integration_id != id or method.integration_id != id:
        raise HTTPException(422, "Confirm an integration-owned source and job")
    link = PipelineAssociation(
        organization_id=row.organization_id,
        method_id=method.id,
        job_id=job.id,
        generation=s.locked_source(db, method.source_id).generation,
        confirmed_by=actor().user_id,
    )
    db.add(link)
    db.flush()
    op.state = "COMPLETE"
    op.result = {"id": str(link.id)}
    s.event(db, link, "ASSOCIATION_CONFIRM", actor().user_id)
    finish(db)
    return doc(link)


@router.post("/integrations/{id}/validate")
def validate(id: uuid.UUID, db=Depends(get_db)):
    row = checked(db, PipelineIntegration, id)
    return {
        "eligible": not s.blockers(db, row),
        "blockers": s.blockers(db, row),
        "live_test_executed": False,
        "fixtures_are_not_runtime_verification": True,
    }


@router.post("/integrations/{id}/activate")
def activate(id: uuid.UUID, payload: ActionInput, db=Depends(get_db)):
    row = checked(db, PipelineIntegration, id, True)
    op, new = mutate(db, row, "ACTIVATE", payload)
    if not new:
        return doc(row)
    issues = s.blockers(db, row)
    if issues:
        raise HTTPException(409, {"code": "ACTIVATION_BLOCKED", "blockers": issues})
    if not payload.confirmed:
        raise HTTPException(422, "Explicit activation approval required")
    sources = set(
        db.scalars(
            select(PipelineMethod.source_id).where(PipelineMethod.integration_id == id)
        )
    )
    for sid in sorted(sources, key=str):
        source = s.locked_source(db, sid)
        s.reader_equivalence(db, source, persist=True)
        for h in db.scalars(
            select(PipelineHold).where(
                PipelineHold.source_id == sid,
                PipelineHold.kind == "INTEGRATION",
                PipelineHold.reference == str(id),
                PipelineHold.released_at.is_(None),
            )
        ):
            s.release_hold(db, h.id, actor().user_id)
    from app.unified.models import MonitoringResource
    from app.unified.engines import source_readiness
    from app.models import JobOrder, Collector

    jobs = db.scalars(
        select(PipelineJob).where(
            PipelineJob.integration_id == id, PipelineJob.selected.is_(True)
        )
    ).all()
    for job in jobs:
        resource = checked(db, MonitoringResource, job.resource_id, True)
        require_permission("resources.update", resource.organization_id)
        collector = db.get(Collector, resource.primary_collector_id)
        if not collector or collector.collector_type != "PIPELINE_V16_PROXY":
            raise HTTPException(
                409,
                "Existing V1.5 Collector requires an explicit reviewed checkpoint-preserving handoff",
            )
        readiness = source_readiness(db, resource)
        if not readiness["ready"]:
            raise HTTPException(
                409, {"code": "V15_SOURCE_READINESS_REQUIRED", "checks": readiness}
            )
        resource.activation_status = "ACTIVE"
        resource.active = True
        db.get(JobOrder, resource.job_order_id).monitoring_enabled = True
    row.enabled = True
    row.configuration = {**row.configuration, "lifecycle": "ACTIVE"}
    row.revision += 1
    op.state = "COMPLETE"
    s.event(db, row, "ACTIVATE", actor().user_id)
    finish(db)
    return doc(row)


@router.post("/integrations/{id}/suspend")
def suspend(id: uuid.UUID, payload: ActionInput, db=Depends(get_db)):
    row = checked(db, PipelineIntegration, id, True)
    op, new = mutate(db, row, "SUSPEND", payload)
    if new:
        s.pause(db, row, actor().user_id)
        op.state = "COMPLETE"
        finish(db)
    return doc(row)


@router.post("/integrations/{id}/discovery")
def discover(id: uuid.UUID, payload: ActionInput, db=Depends(get_db)):
    row = checked(db, PipelineIntegration, id, True)
    # Queue only; the runtime decides whether an approved connection can be read.
    op, new = mutate(db, row, "DISCOVERY", payload)
    if new:
        op.result = {"cadence_hours": 24, "never_auto_select": True}
        finish(db)
    return doc(op)


@router.post("/integrations/{id}/redetection")
def redetect(id: uuid.UUID, payload: ActionInput, db=Depends(get_db)):
    row = checked(db, PipelineIntegration, id, True)
    op, new = mutate(db, row, "REDETECTION", payload)
    if new:
        op.result = {
            "cadence_days": 7,
            "connection_validation_is_not_runtime_verification": True,
        }
        finish(db)
    return doc(op)


@router.get("/sources/{id}/impact")
def impact(id: uuid.UUID, db=Depends(get_db)):
    source = checked(db, PipelineSource, id)
    refs = s.methods(db, source)
    return {
        "source": doc(source),
        "shared_integration_ids": sorted(set(str(m.integration_id) for m in refs)),
        "suspended": s.suspended(db, source),
        "confirmed_job_resource_mappings": [
            {
                "job_id": str(job.id),
                "native_id": job.native_id,
                "resource_id": str(job.resource_id) if job.resource_id else None,
                "quarantined": job.quarantined,
                "origin": job.origin,
            }
            for job in db.scalars(
                select(PipelineJob)
                .join(PipelineAssociation, PipelineAssociation.job_id == PipelineJob.id)
                .join(
                    PipelineMethod, PipelineMethod.id == PipelineAssociation.method_id
                )
                .where(
                    PipelineMethod.source_id == source.id,
                    PipelineAssociation.generation == source.generation,
                )
            )
        ],
        "source_change_requires_fenced_handoff": True,
        "high_risk_requires_independent_reviewer": True,
        "overlap_warnings": [
            str(x.id)
            for x in db.scalars(
                select(PipelineSource).where(
                    PipelineSource.organization_id == source.organization_id,
                    PipelineSource.id != source.id,
                    PipelineSource.method_type == "FILE_LOG",
                )
            )
            if source.method_type == "FILE_LOG"
            and x.identity.get("host_resource_id")
            == source.identity.get("host_resource_id")
            and x.identity.get("path") != source.identity.get("path")
        ],
    }


@router.post("/sources/{id}/holds")
def add_hold(id: uuid.UUID, payload: HoldInput, db=Depends(get_db)):
    source = checked(db, PipelineSource, id, True)
    op, new = mutate(db, source, "HOLD", payload)
    if payload.kind not in {"MANUAL", "LEGAL"}:
        raise HTTPException(422, "Manual or legal hold required")
    if new:
        h = s.hold(db, id, payload.kind, payload.reference, actor().user_id)
        db.flush()
        op.state = "COMPLETE"
        op.result = {"id": str(h.id)}
        finish(db)
    return op.result


@router.post("/holds/{id}/release")
def release(id: uuid.UUID, payload: ActionInput, db=Depends(get_db)):
    row = checked(db, PipelineHold, id, True)
    if not payload.confirmed:
        raise HTTPException(422, "Explicit release approval required")
    if row.kind == "LEGAL":
        require_admin()
    s.release_hold(db, id, actor().user_id)
    finish(db)
    return doc(row)


@router.post("/sources/{id}/recovery")
def recovery(id: uuid.UUID, payload: RecoveryInput, db=Depends(get_db)):
    source = checked(db, PipelineSource, id, True)
    from app.unified.pentaho_replay import is_pentaho

    if is_pentaho(db, source):
        principal = require_permission("etl.replay", source.organization_id)
        from app.security.resource_scope import source_authorized

        if not source_authorized(db, principal, source, "etl.replay"):
            raise HTTPException(
                403, "Replay request exceeds current resource authority"
            )
    op = s.plan_recovery(
        db,
        source,
        payload.start,
        payload.end,
        actor().user_id,
        payload.idempotency_key,
        payload.manual,
        payload.mode,
    )
    finish(db)
    return doc(op)


@router.post("/sources/{id}/change-preview")
def change_preview(id: uuid.UUID, payload: ConfigurationInput, db=Depends(get_db)):
    source = checked(db, PipelineSource, id, True)
    s.bounded(payload.configuration, organization_id=source.organization_id)
    op, new = mutate(db, source, "SOURCE_CHANGE", payload)
    if new:
        op.state = "APPROVAL_REQUIRED"
        op.result = {
            "before": doc(source),
            "impact": impact(id, db),
            "high_risk": True,
            "before_methods": {
                str(method.id): doc(method) for method in s.methods(db, source)
            },
        }
        finish(db)
    return doc(op)


@router.post("/operations/{id}/approve")
def approve(id: uuid.UUID, payload: ActionInput, db=Depends(get_db)):
    row = checked(db, PipelineOperation, id, True)
    if (
        row.kind == "RECOVERY"
        and row.configuration.get("mode") == "ACCEPTED_PENTAHO_EVIDENCE"
    ):
        principal = require_permission("etl.approve_replay", row.organization_id)
        source = s.locked_source(db, row.source_id)
        if row.configuration.get("generation") != str(source.generation):
            raise HTTPException(409, "Replay source generation changed")
        from app.security.resource_scope import source_authorized

        if not source_authorized(db, principal, source, "etl.approve_replay"):
            raise HTTPException(
                403, "Replay approval exceeds current resource authority"
            )
    else:
        require_admin()
    if not payload.confirmed or row.actor_id == actor().user_id:
        raise HTTPException(403, "Independent reviewer confirmation required")
    if row.state == "APPROVED":
        return doc(row)
    if row.state != "APPROVAL_REQUIRED":
        raise HTTPException(409, "Operation is not awaiting approval")
    row.reviewer_id = actor().user_id
    row.state = "APPROVED"
    s.event(db, row, "INDEPENDENT_APPROVAL", actor().user_id)
    finish(db)
    return doc(row)


@router.get("/operations/{id}")
def operation(id: uuid.UUID, db=Depends(get_db)):
    return doc(checked(db, PipelineOperation, id))


@router.get("/integrations/{id}/deletion-preview")
def deletion_preview(id: uuid.UUID, db=Depends(get_db)):
    checked(db, PipelineIntegration, id)
    return {
        "integration_id": str(id),
        "soft_delete_only": True,
        "jobs": db.scalar(
            select(func.count())
            .select_from(PipelineJob)
            .where(PipelineJob.integration_id == id)
        ),
        "evidence_and_history_retained": True,
        "shared_sources_suspended_until_holds_clear": True,
    }


@router.delete("/integrations/{id}")
def retire(id: uuid.UUID, payload: ActionInput, db=Depends(get_db)):
    row = checked(db, PipelineIntegration, id, True)
    if not payload.confirmed:
        raise HTTPException(422, "Deletion preview confirmation required")
    op, new = mutate(db, row, "RETIRE", payload)
    if new:
        s.pause(db, row, actor().user_id)
        for method in db.scalars(
            select(PipelineMethod).where(PipelineMethod.integration_id == id)
        ):
            method.enabled = False
            method.validation = "RETIRED"
        row.deleted_at = s.clock(db)
        op.state = "COMPLETE"
        s.event(db, row, "RETIRE", actor().user_id)
        finish(db)
    return {"retired": True, "evidence_preserved": True}


class MethodEdit(Mutation):
    name: str = Field(min_length=1, max_length=200)
    enabled: bool


@router.put("/methods/{id}")
def edit_method(id: uuid.UUID, payload: MethodEdit, db=Depends(get_db)):
    method = checked(db, PipelineMethod, id, True)
    require_permission("collectors.manage", method.organization_id)
    source = s.locked_source(db, method.source_id)
    op, new = mutate(db, method, "METHOD_EDIT", payload)
    if new:
        revision(method, payload)
        method.name = payload.name
        method.enabled = payload.enabled
        db.flush()
        s.reader_equivalence(db, source, persist=True)
        method.revision += 1
        source.fence += 1
        source.revision += 1
        source.lease_until = None
        source.owner_id = None
        op.state = "COMPLETE"
        s.event(db, method, "METHOD_EDIT", actor().user_id)
        finish(db)
    return doc(method)


@router.delete("/methods/{id}")
def retire_method(id: uuid.UUID, payload: ActionInput, db=Depends(get_db)):
    method = checked(db, PipelineMethod, id, True)
    if not payload.confirmed:
        raise HTTPException(422, "Confirm method retirement; evidence remains retained")
    source = s.locked_source(db, method.source_id)
    op, new = mutate(db, method, "METHOD_RETIRE", payload)
    if new:
        method.enabled = False
        method.validation = "RETIRED"
        method.revision += 1
        source.fence += 1
        source.revision += 1
        source.owner_id = None
        source.lease_until = None
        op.state = "COMPLETE"
        s.event(db, method, "METHOD_RETIRE", actor().user_id)
        finish(db)
    return doc(method)


@router.delete("/associations/{id}")
def remove_association(id: uuid.UUID, payload: ActionInput, db=Depends(get_db)):
    row = checked(db, PipelineAssociation, id, True)
    if not payload.confirmed:
        raise HTTPException(422, "Confirm source association removal")
    method = checked(db, PipelineMethod, row.method_id)
    s.locked_source(db, method.source_id)
    op, new = mutate(db, row, "ASSOCIATION_REMOVE", payload)
    if new:
        s.event(db, row, "ASSOCIATION_REMOVE", actor().user_id)
        db.delete(row)
        op.state = "COMPLETE"
        finish(db)
    return {"removed": True, "execution_dependencies_changed": False}


@router.post("/jobs/{id}/confirm-discovered-identity")
def confirm_identity(id: uuid.UUID, payload: ActionInput, db=Depends(get_db)):
    job = checked(db, PipelineJob, id, True)
    if not payload.confirmed or job.origin != "MANUAL":
        raise HTTPException(422, "Confirm the manual/discovered native identity match")
    discoveries = db.scalars(
        select(PipelineOperation)
        .where(
            PipelineOperation.integration_id == job.integration_id,
            PipelineOperation.kind == "DISCOVERY",
            PipelineOperation.state == "COMPLETE",
        )
        .order_by(PipelineOperation.created_at.desc())
        .limit(10)
    ).all()
    if not any(
        op.result.get("authorized")
        and op.result.get("complete")
        and job.native_id in op.result.get("inventory_native_ids", [])
        and not op.result.get("ambiguous")
        for op in discoveries
    ):
        raise HTTPException(
            409, "Complete authorized unambiguous discovery evidence required"
        )
    job.origin = "CONFIRMED_MERGE"
    job.quarantined = False
    job.revision += 1
    s.event(db, job, "MANUAL_DISCOVERY_MERGE", actor().user_id)
    finish(db)
    return doc(job)


@router.post("/operations/{id}/apply")
def apply_change(id: uuid.UUID, payload: ActionInput, db=Depends(get_db)):
    op = checked(db, PipelineOperation, id, True)
    require_admin()
    if op.state == "COMPLETE":
        return doc(op)
    if (
        not payload.confirmed
        or op.kind != "SOURCE_CHANGE"
        or op.state != "APPROVED"
        or not op.reviewer_id
        or op.actor_id == op.reviewer_id
    ):
        raise HTTPException(409, "Independent approved source change required")
    source = s.locked_source(db, op.source_id)
    previous = op.result["before"]
    if (
        str(source.generation) != previous["generation"]
        or source.revision != previous["revision"]
    ):
        raise HTTPException(409, "Source changed after impact preview")
    cfg = op.configuration["configuration"]
    allowed = {
        "identity",
        "connection_id",
        "method_configuration",
        "transport",
        "legacy_collector_id",
        "method_versions",
    }
    if set(cfg) - allowed:
        raise HTTPException(422, "Unsupported source handoff fields")
    if cfg.get("legacy_collector_id"):
        from app.models import Collector, DataSource
        from app.unified.models import MonitoringResource
        from app.registry.models import CollectorRuntimeState
        from app.pipeline_adapters.core import redact_provider_record

        collector = db.get(Collector, uuid.UUID(cfg["legacy_collector_id"]))
        target = db.get(DataSource, collector.data_source_id) if collector else None
        if (
            not target
            or target.organization_id != source.organization_id
            or collector.collector_type
            not in {"PIPELINE_NATIVE", "IICS_NATIVE", "PENTAHO"}
        ):
            raise HTTPException(404, "Legacy Collector unavailable")
        import hashlib
        from sqlalchemy import text

        key = int.from_bytes(
            hashlib.sha256(f"local-collector:{collector.id}".encode()).digest()[:8],
            "big",
            signed=True,
        )
        if not db.scalar(text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": key}):
            raise HTTPException(
                409, "Legacy Collector is running; retry handoff after it completes"
            )
        state = db.get(CollectorRuntimeState, collector.id)
        if source.live_checkpoint or source.last_received_at:
            raise HTTPException(
                409, "Legacy cursor cannot overwrite accepted V1.6 progress"
            )
        op.result = {
            **op.result,
            "legacy_configuration": {
                "collector_type": collector.collector_type,
                "configuration": redact_provider_record(collector.configuration),
                "checkpoint": state.checkpoint if state else {},
            },
        }
        source.legacy_collector_id = collector.id
        mappings = (
            db.execute(
                select(PipelineJob)
                .join(PipelineAssociation, PipelineAssociation.job_id == PipelineJob.id)
                .join(
                    PipelineMethod, PipelineMethod.id == PipelineAssociation.method_id
                )
                .where(
                    PipelineMethod.source_id == source.id,
                    PipelineAssociation.generation == source.generation,
                    PipelineJob.resource_id.is_not(None),
                )
            )
            .scalars()
            .all()
        )
        matching = [
            j
            for j in mappings
            if db.get(MonitoringResource, j.resource_id).primary_collector_id
            == collector.id
        ]
        if len(matching) != 1:
            raise HTTPException(
                409,
                "Exactly one operator-confirmed legacy native job/cursor mapping is required",
            )
        legacy_job = matching[0]
        legacy_resource = checked(db, MonitoringResource, legacy_job.resource_id, True)
        owning_integration = checked(db, PipelineIntegration, legacy_job.integration_id)
        declared_platform = (
            legacy_resource.configuration.get("platform")
            or collector.configuration.get("platform")
            or {"IICS_NATIVE": "IICS", "PENTAHO": "PENTAHO"}.get(
                collector.collector_type
            )
        )
        if (
            declared_platform != owning_integration.platform
            or legacy_resource.environment != owning_integration.environment
        ):
            raise HTTPException(
                409, "Unmapped legacy platform/environment; handoff stopped"
            )
        if legacy_resource.configuration.get("pipeline_integration_id") not in {
            None,
            str(owning_integration.id),
        }:
            raise HTTPException(
                409, "Legacy resource already belongs to another integration"
            )
        legacy_resource.configuration = {
            **legacy_resource.configuration,
            "pipeline_integration_id": str(owning_integration.id),
            "native_job_id": legacy_job.native_id,
        }
        legacy_resource.activation_status = "CONFIGURED"
        from app.models import JobOrder

        order = db.get(JobOrder, legacy_resource.job_order_id)
        if order:
            order.monitoring_enabled = False
        legacy_job.quarantined = False
        legacy_job.origin = "CONFIRMED_LEGACY"
        legacy_job.revision += 1
        s.event(db, legacy_job, "LEGACY_BINDING_APPROVE", actor().user_id)
        from app.data_pipelines.bridge import SCOPED_SELECTORS

        cursor_key = (
            matching[0].native_id
            if source.identity.get("platform") in SCOPED_SELECTORS
            else "__inventory__"
        )
        source.live_checkpoint = {
            "jobs": {cursor_key: dict(state.checkpoint) if state else {}},
            "legacy_checkpoint": dict(state.checkpoint) if state else {},
        }
        collector.collector_type = (
            "PIPELINE_V16_PROXY"  # old UUID/config/history/cursor preserved
        )
    if cfg.get("identity"):
        identity, key = s.canonical(source.method_type, cfg["identity"])
        if db.scalar(
            select(PipelineSource.id).where(
                PipelineSource.organization_id == source.organization_id,
                PipelineSource.canonical_key == key,
                PipelineSource.id != source.id,
            )
        ):
            raise HTTPException(
                409,
                "Canonical target already exists; explicit association transfer required",
            )
        if source.method_type != "FILE_LOG" and any(
            identity[k] != source.identity[k]
            for k in ("platform", "account", "physical_scope")
        ):
            raise HTTPException(
                409,
                "A different native authority requires new integration/job identities; existing execution history cannot be silently rebound",
            )
        if (
            source.method_type == "FILE_LOG"
            and identity["host_resource_id"] != source.identity["host_resource_id"]
        ):
            raise HTTPException(
                409,
                "Compute Instance inheritance cannot change through a source handoff",
            )
        source.identity = identity
        source.canonical_key = key
    current_methods = s.methods(db, source)
    versions = cfg.get("method_versions")
    if versions is not None and set(versions) != {
        str(method.id) for method in current_methods
    }:
        raise HTTPException(
            409, "Rollback method membership changed; create a fresh impact plan"
        )
    for method in current_methods:
        if versions is not None:
            restored = versions[str(method.id)]
            connection = checked(
                db, PipelineConnection, uuid.UUID(restored["connection_id"])
            )
            capability = checked(
                db, PipelineCapability, uuid.UUID(restored["capability_id"])
            )
            if (
                connection.integration_id != method.integration_id
                or capability.integration_id != method.integration_id
            ):
                raise HTTPException(422, "Rollback cannot change integration ownership")
            if restored["transport"] not in {"AGENT", "BACKEND"}:
                raise HTTPException(422, "Valid rollback transport required")
            method.connection_id = connection.id
            method.capability_id = capability.id
            method.transport = restored["transport"]
            method.configuration = s.bounded(
                restored["configuration"], organization_id=source.organization_id
            )
            method.name = restored["name"]
            method.enabled = restored["enabled"]
            for prior in db.scalars(
                select(PipelineConnection).where(
                    PipelineConnection.integration_id == method.integration_id
                )
            ):
                prior.active = prior.id == connection.id
        if cfg.get("connection_id"):
            connection = checked(
                db, PipelineConnection, uuid.UUID(cfg["connection_id"])
            )
            if connection.integration_id != method.integration_id:
                raise HTTPException(
                    422,
                    "Shared-source connection must be owned by every affected integration; split or provide reviewed per-integration versions",
                )
            for old in db.scalars(
                select(PipelineConnection).where(
                    PipelineConnection.integration_id == method.integration_id
                )
            ):
                old.active = old.id == connection.id
            method.connection_id = connection.id
        if cfg.get("method_configuration"):
            method.configuration = {
                **s.bounded(
                    cfg["method_configuration"], organization_id=source.organization_id
                ),
                "method_type": source.method_type,
            }
        if cfg.get("transport"):
            if cfg["transport"] not in {"BACKEND", "AGENT"}:
                raise HTTPException(422, "Valid transport required")
            method.transport = cfg["transport"]
        owning_integration = checked(db, PipelineIntegration, method.integration_id)
        owning_connection = checked(db, PipelineConnection, method.connection_id)
        s.validate_reader_target(
            owning_integration.platform,
            source.method_type,
            source.identity,
            {
                **owning_connection.configuration,
                **method.configuration.get("adapter_overrides", {}),
            },
        )
        method.revision += 1
        method.validation = "UNVALIDATED"
    source.fence += 1
    source.generation = uuid.uuid4()
    db.flush()
    s.reader_equivalence(db, source, persist=True)
    source.health = "NO_DATA"
    source.last_received_at = None
    source.last_observed_at = None
    source.owner_id = None
    source.lease_until = None
    source.revision += 1
    if cfg.get("identity"):
        source.live_checkpoint = {}
        source.recovery_checkpoint = {}
        source.last_received_at = None
        source.last_observed_at = None
        source.health = "NO_DATA"
    if "restore_checkpoint" in op.result:
        source.live_checkpoint = s.bounded(op.result["restore_checkpoint"])
        source.recovery_checkpoint = {}
    s.hold(db, source.id, "CONTINUITY", str(op.id), actor().user_id)
    op.state = "COMPLETE"
    op.result = {
        **op.result,
        "applied_generation": str(source.generation),
        "checkpoint_archive": previous["live_checkpoint"],
    }
    s.event(db, source, "SOURCE_HANDOFF", actor().user_id)
    finish(db)
    return doc(op)


@router.post("/operations/{id}/rollback-preview")
def rollback_preview(id: uuid.UUID, payload: ActionInput, db=Depends(get_db)):
    old = checked(db, PipelineOperation, id)
    if old.kind != "SOURCE_CHANGE" or old.state != "COMPLETE":
        raise HTTPException(409, "Completed source change required")
    source = checked(db, PipelineSource, old.source_id, True)
    new, created = s.operation(
        db,
        source.organization_id,
        "SOURCE_CHANGE",
        payload.idempotency_key,
        {
            "configuration": {
                "identity": old.result["before"]["identity"],
                "method_versions": old.result.get("before_methods", {}),
            },
            "rollback_of": str(old.id),
        },
        actor().user_id,
        source_id=source.id,
    )
    if created:
        new.state = "APPROVAL_REQUIRED"
        new.result = {
            "before": doc(source),
            "restore_checkpoint": old.result["checkpoint_archive"],
            "before_methods": {
                str(method.id): doc(method) for method in s.methods(db, source)
            },
            "high_risk": True,
        }
        finish(db)
    return doc(new)


@router.post("/sources/{id}/continuity-plan")
def continuity_plan(id: uuid.UUID, payload: ActionInput, db=Depends(get_db)):
    source = checked(db, PipelineSource, id, True)
    op, new = s.operation(
        db,
        source.organization_id,
        "CONTINUITY",
        payload.idempotency_key,
        {
            "generation": str(source.generation),
            "checkpoint_hash": s.digest(source.live_checkpoint),
        },
        actor().user_id,
        source_id=id,
    )
    if new:
        if source.method_type != "FILE_LOG":
            op.state = "BLOCKED"
            op.result = {
                "code": "PROVIDER_CONTINUITY_PROOF_REQUIRED",
                "manual_runtime_acceptance_required": True,
            }
        op.lease_until = s.clock(db) + __import__("datetime").timedelta(minutes=5)
        finish(db)
    return doc(op)


@router.post("/sources/{id}/verification-plan")
def verification_plan(id: uuid.UUID, payload: ActionInput, db=Depends(get_db)):
    source = checked(db, PipelineSource, id, True)
    require_admin()
    if not payload.confirmed:
        raise HTTPException(
            422, "Explicit genuine-runtime acceptance authorization required"
        )
    op, new = s.operation(
        db,
        source.organization_id,
        "VERIFY",
        payload.idempotency_key,
        {"generation": str(source.generation)},
        actor().user_id,
        source_id=id,
    )
    if new:
        op.state = "APPROVAL_REQUIRED"
        op.result = {
            "code": "GENUINE_RUNTIME_ACCEPTANCE_DEFERRED",
            "fixture_verification_forbidden": True,
        }
        finish(db)
    return doc(op)


class ProfileVerification(Mutation):
    evidence_id: uuid.UUID
    compatibility: str
    confirmed: bool


@router.post("/capabilities/{id}/verify-runtime")
def verify_profile(id: uuid.UUID, payload: ProfileVerification, db=Depends(get_db)):
    profile = checked(db, PipelineCapability, id, True)
    require_admin()
    proof = checked(db, PipelineEvidence, payload.evidence_id)
    methods = list(
        db.scalars(
            select(PipelineMethod).where(
                PipelineMethod.capability_id == id,
                PipelineMethod.source_id == proof.source_id,
            )
        )
    )
    if (
        not payload.confirmed
        or payload.compatibility not in {"SUPPORTED", "CONDITIONAL"}
        or profile.platform_version.lower()
        in {"unknown", "operator-supplied installed version"}
        or not methods
        or proof.outcome != "ACCEPTED"
        or proof.payload.get("runtime_origin") != "AUTHENTICATED_RUNTIME"
    ):
        raise HTTPException(
            409,
            "Accepted native-identity evidence from genuine authenticated collection and installed-version confirmation required; fixtures/connection tests are insufficient",
        )
    session = db.scalar(
        select(PipelineOperation)
        .where(
            PipelineOperation.source_id == proof.source_id,
            PipelineOperation.kind == "VERIFY",
            PipelineOperation.state == "COMPLETE",
            PipelineOperation.created_at <= proof.created_at,
        )
        .order_by(PipelineOperation.created_at.desc())
        .limit(1)
    )
    if (
        not session
        or session.actor_id == actor().user_id
        or not session.reviewer_id
        or s.is_sample_evidence(proof.payload)
        or proof.generation != s.locked_source(db, proof.source_id).generation
        or not any(
            proof.payload.get("reader_definition_hash")
            == s.reader_definition(db, method)
            for method in methods
        )
    ):
        raise HTTPException(
            409,
            "Independent genuine-runtime evidence attestation required; fixture certification forbidden",
        )
    # R1 build/surface assertions must match the independent native proof before
    # even the profile label changes; eligible() repeats this during collection.
    from app.pipeline_adapters.pentaho_observations import proof_matches

    r1_profile = False
    for method in methods:
        connection = db.get(PipelineConnection, method.connection_id)
        cfg = {
            **connection.configuration,
            **method.configuration.get("adapter_overrides", {}),
        }
        r1_profile = r1_profile or "monitoring_context" in cfg
        if "monitoring_context" in cfg and not proof_matches(
            cfg["monitoring_context"], profile, proof
        ):
            raise HTTPException(409, {"code": "PENTAHO_BUILD_SURFACE_PROOF_REQUIRED"})
    from app.unified.pentaho_execution import proof_covers_claims

    if r1_profile and not proof_covers_claims(profile.definition, proof.payload):
        raise HTTPException(409, {"code": "PENTAHO_NATIVE_CLAIM_PROOF_REQUIRED"})
    profile.compatibility = payload.compatibility
    profile.evidence_status = "RUNTIME_VERIFIED"
    profile.verification_evidence_id = proof.id
    profile.revision += 1
    s.event(db, profile, "RUNTIME_PROFILE_VERIFY", actor().user_id)
    finish(db)
    return doc(profile)


@router.post("/methods/{id}/validate")
def validate_method(id: uuid.UUID, db=Depends(get_db)):
    method = checked(db, PipelineMethod, id, True)
    source = s.locked_source(db, method.source_id)
    s.reader_equivalence(db, source, persist=True)
    cfg = method.configuration
    if set(cfg) - {
        "method_type",
        "interval_seconds",
        "adapter_overrides",
        "native_identity_field",
        "collector_method_id",
    }:
        raise HTTPException(422, "Unsupported method configuration attributes")
    if (
        not isinstance(cfg.get("interval_seconds", 60), int)
        or not 5 <= cfg.get("interval_seconds", 60) <= 3600
    ):
        raise HTTPException(422, "Collection interval must be 5–3600 seconds")
    connection = checked(db, PipelineConnection, method.connection_id)
    integration = checked(db, PipelineIntegration, method.integration_id)
    if connection.integration_id != integration.id:
        raise HTTPException(422, "Connection ownership mismatch")
    if set(cfg.get("adapter_overrides", {})) - set(
        ADAPTER_DEFINITIONS[integration.platform]["fields"]
    ):
        raise HTTPException(422, "Unsupported adapter override fields")
    s.validate_reader_target(
        integration.platform,
        cfg["method_type"],
        s.locked_source(db, method.source_id).identity,
        {**connection.configuration, **cfg.get("adapter_overrides", {})},
    )
    method.validation = "VALID"
    method.revision += 1
    s.event(db, method, "METHOD_VALIDATE", actor().user_id)
    finish(db)
    return {
        "method": doc(method),
        "runtime_verified": s.eligible(db, method),
        "validation": "STRUCTURE_ONLY",
    }


@router.post("/operations/{id}/start-verification")
def start_verification(id: uuid.UUID, payload: ActionInput, db=Depends(get_db)):
    import os

    operation = checked(db, PipelineOperation, id, True)
    require_admin()
    if os.getenv("OPSCONTROL_PIPELINE_RUNTIME_ACCEPTANCE") != "1":
        raise HTTPException(
            409,
            "Genuine-runtime acceptance is deferred; operator must explicitly enable it in an approved environment",
        )
    if (
        not payload.confirmed
        or operation.kind != "VERIFY"
        or operation.state != "APPROVED"
    ):
        raise HTTPException(409, "Independent approved verification plan required")
    source = s.locked_source(db, operation.source_id)
    if operation.configuration.get("generation") != str(source.generation):
        raise HTTPException(409, "Source generation changed")
    holds = list(
        db.scalars(
            select(PipelineHold).where(
                PipelineHold.source_id == source.id,
                PipelineHold.released_at.is_(None),
                PipelineHold.kind != "LEGAL",
            )
        )
    )
    if any(h.kind != "INTEGRATION" for h in holds) or (
        bool(source.live_checkpoint or source.last_received_at)
        and not source.continuity_validated
    ):
        raise HTTPException(
            409,
            "Existing or manually suspended source requires real continuity proof and explicit hold release",
        )
    # Fresh empty sources have no prior cursor to bridge. All shared references
    # participate in this explicitly approved initial verification, never silently.
    for method in s.methods(db, source):
        profile = checked(db, PipelineCapability, method.capability_id)
        if (
            profile.platform_version.lower()
            in {"unknown", "operator-supplied installed version"}
            or method.validation != "VALID"
        ):
            raise HTTPException(
                409, "Installed version and valid source configuration required"
            )
    for h in holds:
        h.released_at = s.clock(db)
        h.released_by = actor().user_id
    source.continuity_validated = True
    for method in s.methods(db, source):
        integration = checked(db, PipelineIntegration, method.integration_id, True)
        integration.enabled = True
        integration.configuration = {
            **integration.configuration,
            "lifecycle": "VERIFYING",
        }
    operation.state = "RUNNING"
    operation.lease_until = s.clock(db) + __import__("datetime").timedelta(minutes=10)
    finish(db)
    if all(m.transport == "BACKEND" for m in s.methods(db, source)):
        from app.data_pipelines.runtime import run_source

        run_source(source.id, verification=True)
    return doc(operation)


@router.post("/operations/{id}/retry-recovery")
def retry_recovery(id: uuid.UUID, payload: ActionInput, db=Depends(get_db)):
    operation = checked(db, PipelineOperation, id, True)
    source = checked(db, PipelineSource, operation.source_id, True)
    if (
        operation.kind != "RECOVERY"
        or operation.state != "UNRECOVERABLE"
        or not payload.confirmed
    ):
        raise HTTPException(409, "Explicit unrecoverable range review required")
    if not source.last_received_at or source.last_received_at <= operation.created_at:
        raise HTTPException(409, "New durable source evidence required before retry")
    operation.state = "APPROVAL_REQUIRED"
    operation.actor_id = actor().user_id
    operation.reviewer_id = None
    s.event(db, operation, "RECOVERY_REVIEW", actor().user_id)
    finish(db)
    return doc(operation)


@router.get("/sources/{id}/evidence")
def evidence_list(
    id: uuid.UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db=Depends(get_db),
):
    checked(db, PipelineSource, id)
    stmt = select(PipelineEvidence).where(PipelineEvidence.source_id == id)
    return {
        "items": [
            doc(x)
            for x in db.scalars(
                stmt.order_by(PipelineEvidence.created_at.desc(), PipelineEvidence.id)
                .offset(offset)
                .limit(limit)
            )
        ],
        "total": db.scalar(select(func.count()).select_from(stmt.subquery())),
    }


@router.get("/integrations/{id}/jobs")
def jobs_page(
    id: uuid.UUID,
    search: str = "",
    selected: bool | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db=Depends(get_db),
):
    checked(db, PipelineIntegration, id)
    stmt = select(PipelineJob).where(PipelineJob.integration_id == id)
    if selected is not None:
        stmt = stmt.where(PipelineJob.selected.is_(selected))
    if search:
        stmt = stmt.where(
            PipelineJob.name.ilike("%" + search[:200] + "%")
            | PipelineJob.native_id.ilike("%" + search[:200] + "%")
        )
    return {
        "items": [
            doc(j)
            for j in db.scalars(
                stmt.order_by(PipelineJob.name, PipelineJob.id)
                .offset(offset)
                .limit(limit)
            )
        ],
        "total": db.scalar(select(func.count()).select_from(stmt.subquery())),
    }


@router.get("/agent-client")
def agent_client():
    require_permission("etl.view")
    from pathlib import Path
    from fastapi.responses import FileResponse

    path = Path(__file__).resolve().parent / "transport.py"
    # Repository builds keep backend and Agent separately; package distributors
    # must explicitly supply the helper path instead of reporting a fake download.
    if not path.is_file():
        path = Path(
            __import__("os").getenv(
                "OPSCONTROL_PIPELINE_AGENT_CLIENT",
                "/opt/opscontrol/pipeline_transport.py",
            )
        )
    if not path.is_file():
        raise HTTPException(
            503,
            "Pipeline transport helper not packaged in this deployment; use the documented source distribution",
        )
    return FileResponse(
        path, filename="pipeline_transport.py", media_type="text/x-python"
    )
