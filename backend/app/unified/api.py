"""Scoped ARCH-001 control plane. Existing contracts remain available for compatibility."""

import hashlib, json, uuid
from dataclasses import replace
from functools import wraps
from typing import Literal
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import Field
from sqlalchemy import select, func, or_, case, cast, String
from sqlalchemy.exc import IntegrityError
from app.db.session import get_db
from app.api.pagination import page, children
from app.models import (
    Organization,
    VM,
    JobOrder,
    DataSource,
    Collector,
    MetricDefinition,
    JobOrderHistory,
    JobStepExecution,
)
from app.telemetry.models import (
    ManagedAgent,
    CollectorMethod,
    TelemetryReceipt,
)
from app.telemetry.configuration import MethodInput, validate_method, host_os
from app.security.access_control import require_permission
from app.security.audit import log_event
from app.security.scope import current_principal
from app.unified.models import (
    ExpectedExecutionWindow,
    MonitoringResource,
    ParameterActivation,
    ParameterVersion,
    ResourceCondition,
    ResourceDependency,
    ResourceMappingIssue,
)
from app.unified.schemas import (
    APICreate,
    ETLCreate,
    Environment,
    Strict,
    VMCreate,
    import_document,
    require_safe_config,
    validate_parameters,
)

router = APIRouter(prefix="/api/v1/unified", tags=["Unified Monitoring"])


def checked_parameters(domain, configuration):
    try:
        return validate_parameters(domain, configuration)
    except ValueError as error:
        raise HTTPException(422, str(error)) from None


def utc():
    return datetime.now(timezone.utc)


def document(row):
    from app.telemetry.api import item

    return item(row)


def audit(db, resource, action):
    p = current_principal.get()
    log_event(
        db,
        event_type=action,
        outcome="SUCCESS",
        actor_id=p.user_id,
        organization_id=resource.organization_id,
        target_type="monitoring_resource",
        target_id=resource.id,
    )


def commit(db):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            409, "Duplicate identity or invalid resource relationship"
        ) from None


def checked_resource_parameters(db, r, configuration):
    config = checked_parameters(r.domain, configuration)
    if r.domain == "ETL" and r.configuration.get("platform") == "PENTAHO":
        from app.unified.pentaho_schedule import authority

        authority(db, r, config, utc(), strict=True)
    if (
        r.domain == "ETL"
        and r.configuration.get("platform") == "NIFI"
        and config.get("schedule")
    ):
        raise HTTPException(
            422, "NiFi flow monitoring does not imply a scheduled jobchain run"
        )
    if r.domain == "VM":
        for spec in config["thresholds"]:
            if not spec.get("metric_definition_id"):
                continue
            metric = db.get(MetricDefinition, uuid.UUID(spec["metric_definition_id"]))
            if (
                not metric
                or metric.organization_id != r.organization_id
                or metric.data_source_id != r.data_source_id
                or metric.metric_type == "DERIVED_CONDITION"
                or metric.unit != spec["unit"]
            ):
                raise HTTPException(
                    422,
                    "Select an observed metric and matching unit belonging to this VM Resource",
                )
    return config


def resource(db, id, permission="resources.view", write=False):
    query = select(MonitoringResource).where(MonitoringResource.id == id)
    item = db.scalar(query.with_for_update() if write else query)
    if item is None:
        raise HTTPException(404, "Resource unavailable")
    require_permission(permission, item.organization_id)
    return item


def customer(db, payload):
    if payload.new_customer:
        if payload.organization_id:
            raise HTTPException(422, "Choose an existing customer or create one")
        require_permission("customers.create")
        # Preserve the existing no-implicit-grant contract. Inline creation by
        # a non-break-glass user requires separate, explicit grant assignment.
        if not current_principal.get().platform_admin:
            raise HTTPException(
                403,
                "Inline customer creation/onboarding requires a platform administrator; existing customer scopes remain unchanged",
            )
        org = Organization(**payload.new_customer.model_dump())
        db.add(org)
        db.flush()
        # Explicit inline creation selects only the newly created ID for this
        # atomic request. Existing platform authority, not customer selection,
        # authorizes it. No employee grant, ALL authority or session is changed.
        from app.security.boundaries import selected_customers

        prior = current_principal.get()
        scoped = replace(
            prior, customer_directory_ids=prior.customer_directory_ids | {org.id}
        )
        db.info.setdefault("inline_customer_contexts", []).append(
            (
                current_principal.set(scoped),
                selected_customers.set(
                    frozenset(selected_customers.get() or ()) | {org.id}
                ),
                db.info.get("opscontrol_principal"),
            )
        )
        db.info["opscontrol_principal"] = scoped
        return org
    if not payload.organization_id:
        raise HTTPException(422, "Customer required")
    require_permission("resources.create", payload.organization_id)
    org = db.get(Organization, payload.organization_id)
    if org is None or not org.active:
        raise HTTPException(404, "Customer unavailable")
    return org


def inline_creation_scope(handler):
    """Restore request filters on success/error; never expand persistent grants."""

    @wraps(handler)
    def guarded(*args, **kwargs):
        db = kwargs.get("db") if "db" in kwargs else args[1]
        try:
            return handler(*args, **kwargs)
        finally:
            from app.security.boundaries import selected_customers

            for principal_token, selection_token, session_principal in reversed(
                db.info.pop("inline_customer_contexts", [])
            ):
                db.info["opscontrol_principal"] = session_principal
                selected_customers.reset(selection_token)
                current_principal.reset(principal_token)

    return guarded


def linked_vm(db, id, permission="resources.view"):
    parent = resource(db, id, permission)
    if parent.domain != "VM":
        raise HTTPException(422, "Select a VM Resource")
    return parent


def binding(db, r, projection=None):
    config = dict(r.configuration or {})
    if r.domain == "API" and config.get("legacy"):
        from urllib.parse import urlsplit

        source = (
            projection["sources"].get(r.data_source_id)
            if projection is not None
            else db.get(DataSource, r.data_source_id)
        )
        if source is None:
            raise HTTPException(404, "Resource source unavailable")
        parsed = urlsplit(source.endpoint or "")
        config.update(
            {
                "dns": parsed.hostname,
                "port": parsed.port or (443 if parsed.scheme == "https" else 80),
                "protocol": parsed.scheme.upper(),
                "path": parsed.path or "/",
            }
        )
    parent = None
    if r.linked_vm_id:
        parent = (
            projection["parents"].get(r.linked_vm_id)
            if projection is not None
            else db.scalar(
                select(MonitoringResource).where(
                    MonitoringResource.vm_id == r.linked_vm_id
                )
            )
        )
    organization = (
        projection["organizations"].get(r.organization_id)
        if projection is not None
        else db.get(Organization, r.organization_id)
    )
    if organization is None:
        raise HTTPException(404, "Resource customer unavailable")
    inherited = {
        "resource_id": str(r.id),
        "customer_id": str(r.organization_id),
        "customer": organization.name,
        "environment": r.environment,
        "domain": r.domain,
    }
    if parent:
        inherited.update(
            {
                "vm_resource_id": str(parent.id),
                "vm_id": str(parent.vm_id),
                "hostname": (parent.configuration or {}).get("hostname"),
                "collector_id": (
                    str(parent.primary_collector_id)
                    if parent.primary_collector_id
                    else None
                ),
            }
        )
    elif r.domain == "VM":
        inherited.update(
            {
                "vm_id": str(r.vm_id),
                "hostname": config.get("hostname"),
                "collector_id": (
                    str(r.primary_collector_id) if r.primary_collector_id else None
                ),
            }
        )
    if r.domain == "API":
        inherited.update(
            {
                k: config.get(k)
                for k in (
                    "dns",
                    "port",
                    "protocol",
                    "path",
                    "frequency_seconds",
                    "probe_location",
                )
            }
        )
    if r.domain == "ETL":
        inherited.update(
            {
                k: config.get(k)
                for k in (
                    "platform",
                    "jobchain",
                    "scheduler",
                    "frequency_seconds",
                    "log_paths",
                )
            }
        )
    return inherited


def output(db, r, projection=None):
    parameters = (
        r.id in projection["parameters"]
        if projection is not None
        else db.scalar(
            select(ParameterVersion.version).where(
                ParameterVersion.resource_id == r.id,
                ParameterVersion.status == "ACTIVE",
            )
        )
    )
    setup = (r.configuration or {}).get("alert_setup") or {}
    inherited = binding(db, r, projection)
    return {
        **document(r),
        "event_parameters_configured": bool(parameters),
        "alerting_configured": bool(setup.get("enabled")),
        "notification_delivery_configured": bool(
            setup.get("destinations") or setup.get("in_app")
        ),
        "inherited": inherited,
        "has_collector": bool(
            r.primary_collector_id or (r.linked_vm_id and inherited.get("collector_id"))
        ),
    }


def inventory_projection(db, rows):
    """Authorized, page-bounded preload; never reused between requests/scopes."""
    ids = [r.id for r in rows]
    organizations = {r.organization_id for r in rows}
    vms = {r.linked_vm_id for r in rows if r.linked_vm_id}
    sources = {
        r.data_source_id
        for r in rows
        if r.domain == "API" and (r.configuration or {}).get("legacy")
    }
    return {
        "parameters": (
            set(
                db.scalars(
                    select(ParameterVersion.resource_id).where(
                        ParameterVersion.resource_id.in_(ids),
                        ParameterVersion.status == "ACTIVE",
                    )
                )
            )
            if ids
            else set()
        ),
        "organizations": (
            {
                o.id: o
                for o in db.scalars(
                    select(Organization).where(Organization.id.in_(organizations))
                )
            }
            if organizations
            else {}
        ),
        "parents": (
            {
                r.vm_id: r
                for r in db.scalars(
                    select(MonitoringResource).where(MonitoringResource.vm_id.in_(vms))
                )
            }
            if vms
            else {}
        ),
        "sources": (
            {
                d.id: d
                for d in db.scalars(
                    select(DataSource).where(DataSource.id.in_(sources))
                )
            }
            if sources
            else {}
        ),
    }


@router.get("/resources")
def inventory(
    domain: Literal["VM", "ETL", "API"] | None = None,
    organization_id: list[uuid.UUID] = Query(default=[]),
    environment: Environment | None = None,
    search: str = "",
    active: bool | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db=Depends(get_db),
    environments: list[Environment] = Query(default=[]),
):
    query = select(MonitoringResource)
    if domain:
        query = query.where(MonitoringResource.domain == domain)
    if organization_id:
        query = query.where(MonitoringResource.organization_id.in_(organization_id))
    listed_environments = environments if isinstance(environments, list) else []
    if environment and listed_environments:
        raise HTTPException(422, "Use environment or environments, not both")
    selected_environments = (
        [environment] if environment else list(dict.fromkeys(listed_environments))
    )
    if selected_environments:
        query = query.where(MonitoringResource.environment.in_(selected_environments))
    if search:
        query = query.where(MonitoringResource.name.ilike("%" + search[:200] + "%"))
    if active is not None:
        query = query.where(MonitoringResource.active == active)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.scalars(
        query.order_by(MonitoringResource.name, MonitoringResource.id)
        .offset(offset)
        .limit(limit)
    ).all()
    projection = inventory_projection(db, rows)
    return {
        "items": [output(db, r, projection) for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(rows) < total,
    }


@router.get("/resources/{id}")
def details(id: uuid.UUID, db=Depends(get_db)):
    r = resource(db, id)
    dependencies = page(
        db,
        select(ResourceDependency).where(ResourceDependency.resource_id == id),
        (ResourceDependency.valid_from.desc(), ResourceDependency.id.desc()),
        50,
        0,
        document,
    )
    versions = db.scalars(
        select(ParameterVersion)
        .where(ParameterVersion.resource_id == id)
        .order_by(ParameterVersion.version.desc())
        .limit(50)
    ).all()
    conditions = db.scalars(
        select(ResourceCondition)
        .where(ResourceCondition.resource_id == id)
        .order_by(ResourceCondition.last_observed_at.desc())
        .limit(100)
    ).all()
    return {
        **output(db, r),
        "dependencies": dependencies["items"],
        "dependency_total": dependencies["total"],
        "dependency_has_more": dependencies["has_more"],
        "parameter_versions": [document(v) for v in versions],
        "conditions": [document(v) for v in conditions],
    }


@router.get("/resources/{id}/dependencies")
def dependency_history(
    id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db=Depends(get_db),
):
    resource(db, id)
    return page(
        db,
        select(ResourceDependency).where(ResourceDependency.resource_id == id),
        (ResourceDependency.valid_from.desc(), ResourceDependency.id.desc()),
        limit,
        offset,
        document,
    )


@router.get("/mapping-issues")
def issues(limit: int = Query(100, ge=1, le=500), db=Depends(get_db)):
    return [
        document(v)
        for v in db.scalars(
            select(ResourceMappingIssue)
            .where(ResourceMappingIssue.resolved_at.is_(None))
            .limit(limit)
        )
    ]


@router.post("/resources/vm", status_code=201)
@inline_creation_scope
def create_vm(payload: VMCreate, db=Depends(get_db)):
    db.info["unified_manual_binding"] = True
    org = customer(db, payload)
    require_permission("resources.create", org.id)
    require_permission("collectors.manage", org.id)
    vm = VM(
        organization_id=org.id,
        hostname=payload.hostname,
        environment=payload.environment,
        os=payload.os_type,
        monitoring_enabled=False,
    )
    db.add(vm)
    db.flush()
    source = DataSource(
        organization_id=org.id,
        name=payload.hostname,
        source_type=payload.os_type.upper(),
        endpoint=payload.address,
        description=payload.description,
        enabled=True,
        connection_config={
            "opscontrol": {
                "hostname": payload.hostname,
                "os_type": payload.os_type,
                "deployment_type": payload.deployment_type,
                "environment": payload.environment,
                "visible_name": payload.name,
                "vm_id": str(vm.id),
            }
        },
    )
    db.add(source)
    db.flush()
    collector = Collector(
        data_source_id=source.id,
        name=payload.name + " Agent Configuration",
        collector_type="OTEL",
        enabled=True,
        configuration={
            "os_metrics": payload.native_os_metrics,
            "services": payload.services,
            "processes": payload.processes,
        },
    )
    db.add(collector)
    db.flush()
    r = MonitoringResource(
        id=vm.id,
        organization_id=org.id,
        domain="VM",
        name=payload.name,
        environment=payload.environment,
        vm_id=vm.id,
        data_source_id=source.id,
        primary_collector_id=collector.id,
        configuration=payload.model_dump(
            mode="json",
            exclude={
                "organization_id",
                "new_customer",
                "environment",
                "name",
                "active",
            },
        ),
        active=payload.active,
    )
    db.add(r)
    db.flush()
    audit(db, r, "ARCH_RESOURCE_CREATE")
    commit(db)
    return output(db, r)


@router.post("/resources/etl", status_code=201)
@inline_creation_scope
def create_etl(payload: ETLCreate, db=Depends(get_db)):
    db.info["unified_manual_binding"] = True
    parent = linked_vm(db, payload.vm_resource_id) if payload.vm_resource_id else None
    if parent:
        require_permission("resources.create", parent.organization_id)
        require_permission("etl.configure", parent.organization_id)
        if (
            payload.organization_id
            and payload.organization_id != parent.organization_id
        ):
            raise HTTPException(422, "Customer is inherited from the VM")
        if payload.environment and payload.environment != parent.environment:
            raise HTTPException(422, "Environment is inherited from the VM")
        org = db.get(Organization, parent.organization_id)
        env = parent.environment
    else:
        org = customer(db, payload)
        env = payload.environment
        require_permission("etl.configure", org.id)
    job = JobOrder(
        organization_id=org.id,
        vm_id=parent.vm_id if parent else None,
        host_data_source_id=parent.data_source_id if parent else None,
        name=payload.jobchain,
        environment=env,
        monitoring_enabled=False,
    )
    db.add(job)
    db.flush()
    config = payload.model_dump(
        mode="json",
        exclude={
            "organization_id",
            "new_customer",
            "environment",
            "name",
            "active",
            "vm_resource_id",
        },
    )
    r = MonitoringResource(
        id=job.id,
        organization_id=org.id,
        domain="ETL",
        name=payload.name,
        environment=env,
        job_order_id=job.id,
        linked_vm_id=parent.vm_id if parent else None,
        configuration=config,
        active=payload.active,
    )
    if payload.connector_url or payload.integration_configuration:
        require_permission("collectors.manage", org.id)
        source = DataSource(
            organization_id=org.id,
            name=payload.name + " metadata",
            source_type=payload.platform,
            endpoint=payload.connector_url
            or payload.integration_configuration.get("base_url")
            or payload.integration_configuration.get("url"),
            enabled=True,
            connection_config={"opscontrol": {"environment": env}},
        )
        db.add(source)
        db.flush()
        collector = Collector(
            data_source_id=source.id,
            name=payload.name + " read-only metadata",
            collector_type=(
                "PIPELINE_NATIVE"
                if payload.integration_configuration
                else "IICS_NATIVE"
            ),
            enabled=False,
            interval_seconds=payload.frequency_seconds,
            configuration={
                "resource_id": str(r.id),
                "url": payload.connector_url,
                "credential_ref": payload.credential_ref,
                "credential_header": payload.credential_header,
                "records_field": payload.connector_records_field,
                "platform": payload.platform,
                "integration_configuration": payload.integration_configuration,
                "parser": payload.parser.model_dump(mode="json"),
                "jobchain": payload.jobchain,
            },
        )
        db.add(collector)
        db.flush()
        r.data_source_id = source.id
        r.primary_collector_id = collector.id
    db.add(r)
    db.flush()
    if parent:
        db.add(
            ResourceDependency(
                organization_id=org.id,
                resource_id=r.id,
                depends_on_id=parent.id,
                relationship_type="HOSTED_ON",
            )
        )
        if payload.log_paths:
            if not parent.primary_collector_id or not parent.data_source_id:
                raise HTTPException(
                    409, "Reconcile the VM Collector before adding ETL log paths"
                )
            require_permission("collectors.manage", org.id)
            for index, path in enumerate(payload.log_paths):
                method = MethodInput(
                    name=payload.name + " log " + str(index + 1),
                    method_type="FILE_LOG",
                    configuration={"paths": [path]},
                )
                try:
                    validate_method(
                        method, host_os(db.get(DataSource, parent.data_source_id))
                    )
                except ValueError as error:
                    raise HTTPException(422, str(error)) from None
                db.add(
                    CollectorMethod(
                        organization_id=org.id,
                        collector_id=parent.primary_collector_id,
                        **method.model_dump(exclude={"expected_revision"}),
                        validation_status="SCHEMA_VALID"
                    )
                )
    audit(db, r, "ARCH_RESOURCE_CREATE")
    commit(db)
    return output(db, r)


@router.post("/resources/api", status_code=201)
@inline_creation_scope
def create_api(payload: APICreate, db=Depends(get_db)):
    db.info["unified_manual_binding"] = True
    org = customer(db, payload)
    require_permission("resources.create", org.id)
    require_permission("collectors.manage", org.id)
    parent = (
        linked_vm(db, payload.linked_vm_resource_id)
        if payload.linked_vm_resource_id
        else None
    )
    if parent and (
        parent.organization_id != org.id or parent.environment != payload.environment
    ):
        raise HTTPException(422, "Linked VM customer/environment must match")
    address = "[" + payload.dns + "]" if ":" in payload.dns else payload.dns
    url = (
        payload.protocol.lower()
        + "://"
        + address
        + ":"
        + str(payload.port)
        + payload.path
    )
    source = DataSource(
        organization_id=org.id,
        name=payload.name,
        source_type="API",
        endpoint=url,
        enabled=True,
        connection_config={
            "opscontrol": {"environment": payload.environment},
            "credential_ref": payload.credential_ref,
        },
    )
    db.add(source)
    db.flush()
    configuration = payload.model_dump(
        mode="json",
        exclude={
            "organization_id",
            "new_customer",
            "environment",
            "name",
            "active",
            "linked_vm_resource_id",
        },
    )
    collector = Collector(
        data_source_id=source.id,
        name=payload.name + " native probe",
        collector_type="NATIVE_API",
        enabled=False,
        interval_seconds=payload.frequency_seconds,
        configuration={**configuration, "url": url},
    )
    db.add(collector)
    db.flush()
    r = MonitoringResource(
        id=source.id,
        organization_id=org.id,
        domain="API",
        name=payload.name,
        environment=payload.environment,
        data_source_id=source.id,
        primary_collector_id=collector.id,
        linked_vm_id=parent.vm_id if parent else None,
        configuration=configuration,
        active=payload.active,
    )
    db.add(r)
    db.flush()
    if parent:
        db.add(
            ResourceDependency(
                organization_id=org.id,
                resource_id=r.id,
                depends_on_id=parent.id,
                relationship_type="HOSTED_ON",
            )
        )
    audit(db, r, "ARCH_RESOURCE_CREATE")
    commit(db)
    return output(db, r)


class ResourceEdit(Strict):
    expected_revision: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=200)
    environment: Environment
    configuration: dict
    active: bool = True


@router.put("/resources/{id}")
def edit(id: uuid.UUID, payload: ResourceEdit, db=Depends(get_db)):
    r = resource(db, id, "resources.update", True)
    if payload.expected_revision != r.revision:
        raise HTTPException(409, "Resource changed; reload before editing")
    config = dict(payload.configuration)
    # Alert setup has a separate permission/revision contract. A generic edit
    # may echo it unchanged but must never create, change or erase it.
    internal = {
        key: value
        for key, value in (r.configuration or {}).items()
        if key
        in {"alert_setup", "log_method_ids", "pipeline_integration_id", "native_job_id"}
    }
    for key in internal.keys() | {
        "alert_setup",
        "log_method_ids",
        "pipeline_integration_id",
        "native_job_id",
    }:
        if key in config and config.pop(key) != internal.get(key):
            raise HTTPException(
                403, "Use the authorized configuration-specific endpoint"
            )
    require_safe_config(config)
    base = {
        "name": payload.name,
        "organization_id": str(r.organization_id),
        "environment": payload.environment,
        "active": payload.active,
        **config,
    }
    base.pop("legacy", None)
    if r.domain == "VM":
        typed = VMCreate.model_validate(base)
        config = typed.model_dump(
            mode="json",
            exclude={
                "name",
                "organization_id",
                "new_customer",
                "environment",
                "active",
            },
        )
        if typed.hostname != (r.configuration or {}).get(
            "hostname", db.get(VM, r.vm_id).hostname
        ):
            raise HTTPException(
                409,
                "Host identity is immutable; preserve history by onboarding a new host",
            )
        if r.data_source_id:
            source = db.get(DataSource, r.data_source_id)
            if typed.os_type != host_os(source):
                raise HTTPException(
                    409, "Changing an enrolled host OS requires deliberate migration"
                )
            source.endpoint = typed.address
            source.connection_config = {
                **(source.connection_config or {}),
                "opscontrol": {
                    **(source.connection_config or {}).get("opscontrol", {}),
                    "environment": payload.environment,
                    "visible_name": payload.name,
                },
            }
        db.get(VM, r.vm_id).environment = payload.environment
        if r.primary_collector_id:
            require_permission("collectors.manage", r.organization_id)
            c = db.get(Collector, r.primary_collector_id)
            c.configuration = {
                **(c.configuration or {}),
                "services": typed.services,
                "processes": typed.processes,
                "os_metrics": typed.native_os_metrics,
            }
        # Parent identity propagation never edits a saved threshold override.
        for child in db.scalars(
            select(MonitoringResource).where(MonitoringResource.linked_vm_id == r.vm_id)
        ):
            if child.domain in {"ETL", "API"}:
                child.environment = payload.environment
                child.revision += 1
                if child.job_order_id:
                    db.get(JobOrder, child.job_order_id).environment = (
                        payload.environment
                    )
                if child.domain == "API" and child.data_source_id:
                    cs = db.get(DataSource, child.data_source_id)
                    cs.connection_config = {
                        **(cs.connection_config or {}),
                        "opscontrol": {
                            **(cs.connection_config or {}).get("opscontrol", {}),
                            "environment": payload.environment,
                        },
                    }
    elif r.domain == "ETL":
        parent = (
            db.scalar(
                select(MonitoringResource).where(
                    MonitoringResource.vm_id == r.linked_vm_id
                )
            )
            if r.linked_vm_id
            else None
        )
        if parent and payload.environment != parent.environment:
            raise HTTPException(422, "ETL environment is inherited")
        typed = ETLCreate.model_validate(
            {**base, "vm_resource_id": str(parent.id) if parent else None}
        )
        config = typed.model_dump(
            mode="json",
            exclude={
                "name",
                "organization_id",
                "new_customer",
                "environment",
                "active",
                "vm_resource_id",
            },
        )
        job = db.get(JobOrder, r.job_order_id)
        if typed.jobchain != job.name:
            raise HTTPException(
                409, "Jobchain identity is immutable; create a new resource"
            )
        if r.primary_collector_id:
            require_permission("collectors.manage", r.organization_id)
            collector = db.get(Collector, r.primary_collector_id)
            expected_type = (
                "PIPELINE_NATIVE" if typed.integration_configuration else "IICS_NATIVE"
            )
            if collector.collector_type != expected_type:
                raise HTTPException(
                    409, "Changing provider transport requires explicit re-onboarding"
                )
            collector.interval_seconds = typed.frequency_seconds
            collector.configuration = {
                **(collector.configuration or {}),
                "platform": typed.platform,
                "integration_configuration": typed.integration_configuration,
                "url": typed.connector_url,
                "credential_ref": typed.credential_ref,
                "credential_header": typed.credential_header,
                "records_field": typed.connector_records_field,
                "parser": typed.parser.model_dump(mode="json"),
                "jobchain": typed.jobchain,
            }
        elif typed.integration_configuration or typed.connector_url:
            raise HTTPException(
                409, "Adding a provider transport requires explicit re-onboarding"
            )
        if sorted(typed.log_paths) != sorted(
            (r.configuration or {}).get("log_paths", [])
        ):
            if not parent or not parent.primary_collector_id:
                raise HTTPException(
                    409, "Log paths require an associated Compute Instance"
                )
            require_permission("collectors.manage", r.organization_id)
            paths = {
                path
                for method in db.scalars(
                    select(CollectorMethod).where(
                        CollectorMethod.collector_id == parent.primary_collector_id,
                        CollectorMethod.enabled.is_(True),
                        CollectorMethod.method_type == "FILE_LOG",
                    )
                )
                for path in method.configuration.get("paths", [])
            }
            if not set(typed.log_paths) <= paths:
                raise HTTPException(
                    409,
                    "Configure the paths in VM Collection Methods before binding them",
                )

    else:
        typed = APICreate.model_validate(base)
        config = typed.model_dump(
            mode="json",
            exclude={
                "name",
                "organization_id",
                "new_customer",
                "environment",
                "active",
                "linked_vm_resource_id",
            },
        )
        if any(
            config.get(k) != (r.configuration or {}).get(k)
            for k in ("dns", "port", "protocol", "path")
        ):
            raise HTTPException(
                409,
                "Endpoint identity is immutable; preserve history by creating a new endpoint",
            )
        if r.primary_collector_id:
            require_permission("collectors.manage", r.organization_id)
            c = db.get(Collector, r.primary_collector_id)
            c.interval_seconds = typed.frequency_seconds
            c.configuration = {**(c.configuration or {}), **config}
    r.name = payload.name
    r.environment = payload.environment
    r.configuration = {**config, **internal}
    r.active = payload.active
    r.revision += 1
    r.updated_at = utc()
    if not r.active:
        r.activation_status = "PAUSED"
        if r.data_source_id:
            db.get(DataSource, r.data_source_id).enabled = False
        if r.primary_collector_id:
            db.get(Collector, r.primary_collector_id).enabled = False
        if r.vm_id:
            db.get(VM, r.vm_id).monitoring_enabled = False
        if r.job_order_id:
            db.get(JobOrder, r.job_order_id).monitoring_enabled = False
    audit(db, r, "ARCH_RESOURCE_UPDATE")
    commit(db)
    return output(db, r)


class ParameterInput(Strict):
    expected_resource_revision: int = Field(ge=1)
    configuration: dict


@router.post("/parameters/{id}/preview")
def preview(id: uuid.UUID, payload: ParameterInput, db=Depends(get_db)):
    r = resource(db, id, "templates.view")
    config = checked_resource_parameters(db, r, payload.configuration)
    inherited = binding(db, r)
    attributes = [
        {"name": k, "value": v, "provenance": "INHERITED", "read_only": True}
        for k, v in inherited.items()
    ]
    attributes += [
        {
            "name": k,
            "value": v,
            "provenance": "OVERRIDDEN" if k in config["overrides"] else "CONFIGURED",
            "read_only": False,
        }
        for k, v in config.items()
        if k not in {"domain", "overrides"}
    ]
    if r.primary_collector_id:
        last = db.scalar(
            select(func.max(TelemetryReceipt.received_at))
            .join(ManagedAgent, ManagedAgent.id == TelemetryReceipt.agent_id)
            .where(ManagedAgent.collector_id == r.primary_collector_id)
        )
        attributes.append(
            {
                "name": "last_telemetry_receipt",
                "value": last,
                "provenance": "TELEMETRY_DERIVED",
                "read_only": True,
            }
        )
    return {
        "resource_revision": r.revision,
        "configuration": config,
        "attributes": attributes,
        "identity_overrides_allowed": False,
    }


@router.post("/parameters/{id}", status_code=201)
def save_parameters(id: uuid.UUID, payload: ParameterInput, db=Depends(get_db)):
    r = resource(db, id, "templates.manage", True)
    if r.revision != payload.expected_resource_revision:
        raise HTTPException(409, "Inherited identity changed; reload effective preview")
    config = checked_resource_parameters(db, r, payload.configuration)
    version = (
        db.scalar(
            select(func.max(ParameterVersion.version)).where(
                ParameterVersion.resource_id == id
            )
        )
        or 0
    ) + 1
    p = ParameterVersion(
        organization_id=r.organization_id,
        resource_id=id,
        version=version,
        configuration=config,
        sha256=hashlib.sha256(
            json.dumps(config, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        actor_id=current_principal.get().user_id,
    )
    db.add(p)
    db.flush()
    audit(db, r, "ARCH_PARAMETERS_SAVE")
    commit(db)
    return document(p)


class ImportInput(Strict):
    content: str
    format: Literal["YAML", "JSON"]
    expected_resource_revision: int = Field(ge=1)
    save: bool = False


@router.post("/parameters/{id}/import")
def import_parameters(
    id: uuid.UUID, payload: ImportInput, response: Response, db=Depends(get_db)
):
    r = resource(db, id, "templates.manage" if payload.save else "templates.view")
    try:
        parsed = import_document(payload.content, payload.format)
    except ValueError as error:
        raise HTTPException(422, str(error)) from None
    config = checked_resource_parameters(db, r, parsed)
    args = ParameterInput(
        expected_resource_revision=payload.expected_resource_revision,
        configuration=config,
    )
    if payload.save:
        response.status_code = 201
    return save_parameters(id, args, db) if payload.save else preview(id, args, db)


@router.get("/parameters/{id}")
def versions(id: uuid.UUID, db=Depends(get_db)):
    r = resource(db, id, "templates.view")
    return {
        "inherited": binding(db, r),
        "activations": [
            document(a)
            for a in db.scalars(
                select(ParameterActivation)
                .where(ParameterActivation.resource_id == id)
                .order_by(ParameterActivation.effective_from.desc())
                .limit(100)
            )
        ],
        "versions": [
            document(p)
            for p in db.scalars(
                select(ParameterVersion)
                .where(ParameterVersion.resource_id == id)
                .order_by(ParameterVersion.version.desc())
                .limit(100)
            )
        ],
    }


class Approval(Strict):
    approve: bool
    version: int | None = None


@router.post("/parameters/{id}/activate")
def activate_parameters(id: uuid.UUID, payload: Approval, db=Depends(get_db)):
    r = resource(db, id, "templates.manage", True)
    if not payload.approve or not payload.version:
        raise HTTPException(422, "Explicit version approval required")
    p = db.scalar(
        select(ParameterVersion).where(
            ParameterVersion.resource_id == id,
            ParameterVersion.version == payload.version,
        )
    )
    if not p:
        raise HTTPException(404, "Parameter version unavailable")
    config = checked_resource_parameters(db, r, p.configuration)
    setup = (r.configuration or {}).get("alert_setup") or {}
    if setup.get("enabled") and setup.get("parameter_version") != p.version:
        r.configuration = {
            **r.configuration,
            "alert_setup": {
                **setup,
                "enabled": False,
                "reason": "PARAMETER_VERSION_CHANGED",
            },
        }
        from app.models import AlertRule

        for rule in db.scalars(
            select(AlertRule)
            .join(MetricDefinition)
            .where(
                MetricDefinition.resource_id == r.id,
                MetricDefinition.metric_type == "DERIVED_CONDITION",
            )
        ):
            rule.enabled = False
    current = db.scalar(
        select(ParameterActivation).where(
            ParameterActivation.resource_id == id,
            ParameterActivation.effective_to.is_(None),
        )
    )
    if current and current.parameter_version == p.version and p.status == "ACTIVE":
        return document(p)
    if current:
        current.effective_to = utc()
    db.flush()
    db.add(
        ParameterActivation(
            organization_id=r.organization_id,
            resource_id=id,
            parameter_version=p.version,
            actor_id=current_principal.get().user_id,
        )
    )
    for old in db.scalars(
        select(ParameterVersion).where(
            ParameterVersion.resource_id == id, ParameterVersion.status == "ACTIVE"
        )
    ):
        old.status = "SUPERSEDED"
    db.flush()
    p.status = "ACTIVE"
    if r.domain == "ETL":
        job = db.get(JobOrder, r.job_order_id)
        job.expected_runtime_seconds = config["long_running_seconds"]
        job.sla_seconds = config["completion_sla_seconds"]
        job.no_run_grace_seconds = config["no_run_grace_seconds"]
        if r.primary_collector_id:
            require_permission("collectors.manage", r.organization_id)
            c = db.get(Collector, r.primary_collector_id)
            c.configuration = {
                **(c.configuration or {}),
                "parser": config["parser"],
                "jobchain": r.configuration["jobchain"],
            }
    if r.domain == "VM" and r.primary_collector_id:
        c = db.get(Collector, r.primary_collector_id)
        if not set(config["services"]).issubset(
            (c.configuration or {}).get("services", [])
        ) or not set(config["processes"]).issubset(
            (c.configuration or {}).get("processes", [])
        ):
            raise HTTPException(
                422,
                "Configure service/process collection in the VM Resource before activating monitoring parameters",
            )
    audit(db, r, "ARCH_PARAMETERS_ACTIVATE")
    commit(db)
    return document(p)


class NativeAlertSetup(Strict):
    enabled: bool = False
    parameter_version: int | None = Field(default=None, ge=1)
    severities: list[Literal["WARNING", "CRITICAL"]] = Field(
        default_factory=lambda: ["WARNING", "CRITICAL"], min_length=1, max_length=2
    )
    destinations: list[uuid.UUID] = Field(default_factory=list, max_length=30)
    in_app: bool = False


@router.get("/resources/{id}/alert-setup")
def alert_setup(id: uuid.UUID, db=Depends(get_db)):
    r = resource(db, id, "alerts.view")
    setup = (r.configuration or {}).get("alert_setup")
    return setup or {
        "enabled": False,
        "parameter_version": None,
        "severities": ["WARNING", "CRITICAL"],
        "destinations": [],
        "in_app": False,
        "revision": 0,
    }


@router.post("/resources/{id}/alert-setup")
def save_alert_setup(id: uuid.UUID, payload: NativeAlertSetup, db=Depends(get_db)):
    r = resource(db, id, "templates.manage", True)
    parameter = (
        db.scalar(
            select(ParameterVersion).where(
                ParameterVersion.resource_id == id,
                ParameterVersion.version == payload.parameter_version,
            )
        )
        if payload.parameter_version
        else None
    )
    if payload.enabled and (not parameter or parameter.status != "ACTIVE"):
        raise HTTPException(
            422,
            "Enabled native alert rules must reference an active Event Parameters version",
        )
    from app.telemetry.models import NotificationDestination

    for target in payload.destinations:
        destination = db.get(NotificationDestination, target)
        if (
            not destination
            or destination.organization_id != r.organization_id
            or not destination.enabled
        ):
            raise HTTPException(
                422, "Select enabled notification destinations in this customer scope"
            )
    previous = (r.configuration or {}).get("alert_setup", {})
    setup = {
        **payload.model_dump(mode="json"),
        "revision": previous.get("revision", 0) + 1,
        "configured_at": utc().isoformat(),
    }
    r.configuration = {**r.configuration, "alert_setup": setup}
    from app.models import AlertRule

    for rule in db.scalars(
        select(AlertRule)
        .join(MetricDefinition)
        .where(
            MetricDefinition.resource_id == r.id,
            MetricDefinition.metric_type == "DERIVED_CONDITION",
        )
    ):
        rule.enabled = payload.enabled and rule.severity in payload.severities
        rule.notification_channels = (["IN_APP"] if payload.in_app else []) + [
            "DEST:" + str(v) for v in payload.destinations
        ]
    audit(db, r, "NATIVE_ALERT_SETUP_SAVE")
    commit(db)
    return setup


@router.get("/resources/{id}/verification")
def verification(id: uuid.UUID, db=Depends(get_db)):
    r = resource(db, id)
    from app.unified.engines import source_readiness

    return {
        "resource_id": id,
        **source_readiness(db, r),
        "activation_status": r.activation_status,
    }


@router.post("/resources/{id}/activate")
def activate_resource(id: uuid.UUID, payload: Approval, db=Depends(get_db)):
    r = resource(db, id, "resources.update", True)
    if r.configuration.get("pipeline_integration_id"):
        from app.data_pipelines.models import PipelineIntegration
        from app.data_pipelines.service import blockers as pipeline_blockers

        integration = db.get(
            PipelineIntegration, uuid.UUID(r.configuration["pipeline_integration_id"])
        )
        if (
            not integration
            or not integration.enabled
            or integration.configuration.get("lifecycle") != "ACTIVE"
            or pipeline_blockers(db, integration)
        ):
            raise HTTPException(
                409,
                "Activate through the V1.6 integration after source eligibility validation",
            )
    if not payload.approve:
        raise HTTPException(422, "Explicit activation approval required")
    from app.unified.engines import source_readiness

    evidence = source_readiness(db, r)
    if not evidence["ready"]:
        raise HTTPException(
            409,
            {
                "message": "Required telemetry verification has not passed",
                "checks": evidence,
            },
        )
    r.activation_status = "ACTIVE"
    r.active = True
    if r.vm_id:
        db.get(VM, r.vm_id).monitoring_enabled = True
    if r.job_order_id:
        db.get(JobOrder, r.job_order_id).monitoring_enabled = True
    audit(db, r, "ARCH_RESOURCE_ACTIVATE")
    commit(db)
    return output(db, r)


@router.post("/resources/{id}/start-probe")
def start_probe(id: uuid.UUID, payload: Approval, db=Depends(get_db)):
    r = resource(db, id, "collectors.manage", True)
    if r.configuration.get("pipeline_integration_id"):
        raise HTTPException(
            409,
            "Use V1.6 source verification; this resource has no independent legacy probe",
        )
    if r.domain not in {"API", "ETL"} or not r.primary_collector_id:
        raise HTTPException(422, "No native probe/connector configured")
    if not current_principal.get().platform_admin or not payload.approve:
        raise HTTPException(
            403,
            "Platform administrator approval is required for native outbound probes",
        )
    c = db.get(Collector, r.primary_collector_id)
    if c.remote_worker_id:
        raise HTTPException(409, "Use the assigned remote worker control plane")
    c.enabled = True
    c.next_run_at = utc()
    r.activation_status = "VERIFYING"
    audit(db, r, "ARCH_NATIVE_PROBE_APPROVE")
    commit(db)
    return {"status": "APPROVED_PENDING_REAL_COLLECTION", "collector_id": c.id}


class DependencyInput(Strict):
    depends_on_id: uuid.UUID
    relationship_type: Literal["HOSTED_ON", "REQUIRES_SERVICE", "DEPENDS_ON"] = (
        "DEPENDS_ON"
    )
    service_identity: str = Field(default="", max_length=200)


@router.post("/resources/{id}/dependencies", status_code=201)
def add_dependency(id: uuid.UUID, payload: DependencyInput, db=Depends(get_db)):
    r = resource(db, id, "resources.update")
    db.execute(
        select(
            func.pg_advisory_xact_lock(
                int.from_bytes(
                    hashlib.sha256(
                        ("arch001-dependency:" + str(r.organization_id)).encode()
                    ).digest()[:8],
                    "big",
                    signed=True,
                )
            )
        )
    )
    r = resource(db, id, "resources.update", True)
    parent = resource(db, payload.depends_on_id)
    if (
        r.organization_id != parent.organization_id
        or r.environment != parent.environment
        or r.id == parent.id
    ):
        raise HTTPException(
            422,
            "Dependency must reference a different resource in the same customer/environment",
        )
    if payload.relationship_type == "REQUIRES_SERVICE":
        c = (
            db.get(Collector, parent.primary_collector_id)
            if parent.primary_collector_id
            else None
        )
        configured = (
            set(
                (c.configuration or {}).get("services", [])
                + (c.configuration or {}).get("processes", [])
            )
            if c
            else set()
        )
        if parent.domain != "VM" or payload.service_identity not in configured:
            raise HTTPException(
                422, "Select an actual configured VM service/process identity"
            )
    if payload.relationship_type == "HOSTED_ON" and (
        parent.domain != "VM" or r.linked_vm_id != parent.vm_id
    ):
        raise HTTPException(
            422, "Host relationships must match resource onboarding inheritance"
        )
    seen = {r.id}
    queue = [parent.id]
    while queue:
        item = queue.pop()
        if item == r.id:
            raise HTTPException(409, "Dependency cycle detected")
        if item in seen:
            continue
        seen.add(item)
        queue.extend(
            db.scalars(
                select(ResourceDependency.depends_on_id).where(
                    ResourceDependency.resource_id == item,
                    ResourceDependency.valid_to.is_(None),
                )
            ).all()
        )
        if len(seen) > 1000:
            raise HTTPException(409, "Dependency graph exceeds validation bound")
    d = ResourceDependency(
        organization_id=r.organization_id, resource_id=id, **payload.model_dump()
    )
    db.add(d)
    db.flush()
    audit(db, r, "ARCH_DEPENDENCY_CREATE")
    commit(db)
    return document(d)


@router.delete("/resources/{id}/dependencies/{dependency_id}", status_code=204)
def remove_dependency(id: uuid.UUID, dependency_id: uuid.UUID, db=Depends(get_db)):
    r = resource(db, id, "resources.update", True)
    d = db.get(ResourceDependency, dependency_id)
    if not d or d.resource_id != id:
        raise HTTPException(404, "Dependency unavailable")
    if d.relationship_type == "HOSTED_ON":
        raise HTTPException(
            409, "Inherited host relationship cannot be removed independently"
        )
    d.valid_to = utc()
    audit(db, r, "ARCH_DEPENDENCY_RETIRE")
    commit(db)


@router.get("/resources/{id}/executions")
def executions(
    id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    outcome: (
        Literal[
            "SUCCESS",
            "SUCCESS_AFTER_RETRY",
            "FAILED",
            "CANCELLED",
            "UNKNOWN",
            "WAITING_FOR_RETRY",
        ]
        | None
    ) = None,
    db=Depends(get_db),
):
    r = resource(db, id, "etl.view")
    if r.domain != "ETL":
        raise HTTPException(422, "ETL Resource required")
    query = select(JobOrderHistory).where(
        JobOrderHistory.job_order_id == r.job_order_id
    )
    if outcome:
        # Match the existing display projection without upgrading incomplete
        # native evidence from a legacy process/scheduler status.
        native = JobOrderHistory.pentaho_resource_id.is_not(None)
        projected = func.coalesce(
            JobOrderHistory.pentaho_outcome,
            case(
                (JobOrderHistory.pentaho_lifecycle == "RUNNING", "RUNNING"),
                else_="UNKNOWN",
            ),
        )
        waiting = JobOrderHistory.pentaho_lifecycle == "WAITING_FOR_RETRY"
        if outcome == "WAITING_FOR_RETRY":
            query = query.where(waiting)
        else:
            query = query.where(
                or_(
                    native & (projected == outcome) & ~func.coalesce(waiting, False),
                    ~native & (cast(JobOrderHistory.status, String) == outcome),
                )
            )
    result = page(
        db,
        query,
        (JobOrderHistory.created_at.desc(), JobOrderHistory.id),
        limit,
        offset,
        document,
    )
    ids = [uuid.UUID(str(h["id"])) for h in result["items"]]
    steps, totals = children(
        db,
        JobStepExecution,
        JobStepExecution.history_id,
        ids,
        (JobStepExecution.started_at.asc().nulls_last(), JobStepExecution.id),
        200,
        document,
    )
    from app.unified.pentaho_models import PentahoAttempt

    counts = (
        dict(
            db.execute(
                select(PentahoAttempt.history_id, func.count())
                .where(PentahoAttempt.history_id.in_(ids))
                .group_by(PentahoAttempt.history_id)
            ).all()
        )
        if ids
        else {}
    )
    for h in result["items"]:
        key = uuid.UUID(str(h["id"]))
        h.update(
            steps=steps[key],
            steps_total=totals.get(key, 0),
            steps_has_more=totals.get(key, 0) > len(steps[key]),
            attempt_count=counts.get(key, 0),
        )
    return result


def execution_history(db, id, history_id):
    r = resource(db, id, "etl.view")
    h = db.scalar(
        select(JobOrderHistory).where(
            JobOrderHistory.id == history_id,
            JobOrderHistory.job_order_id == r.job_order_id,
        )
    )
    if r.domain != "ETL" or not h:
        raise HTTPException(404, "Execution unavailable")
    return h


@router.get("/resources/{id}/executions/{history_id}/steps")
def execution_steps(
    id: uuid.UUID,
    history_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db=Depends(get_db),
):
    h = execution_history(db, id, history_id)
    return page(
        db,
        select(JobStepExecution).where(JobStepExecution.history_id == h.id),
        (JobStepExecution.started_at.asc().nulls_last(), JobStepExecution.id),
        limit,
        offset,
        document,
    )


def window_query(id, status=None):
    query = select(ExpectedExecutionWindow).where(
        ExpectedExecutionWindow.resource_id == id
    )
    return query.where(ExpectedExecutionWindow.status == status) if status else query


@router.get("/resources/{id}/schedule-windows")
def windows(id: uuid.UUID, limit: int = Query(100, ge=1, le=500), db=Depends(get_db)):
    resource(db, id, "etl.view")
    return [
        document(w)
        for w in db.scalars(
            window_query(id)
            .order_by(
                ExpectedExecutionWindow.scheduled_at.desc(), ExpectedExecutionWindow.id
            )
            .limit(limit)
        )
    ]


@router.get("/resources/{id}/schedule-occurrences")
def occurrence_page(
    id: uuid.UUID,
    status: (
        Literal[
            "PENDING_GRACE", "OBSERVED", "DELAYED", "NO_RUN", "UNKNOWN", "INCOMPLETE"
        ]
        | None
    ) = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db=Depends(get_db),
):
    resource(db, id, "etl.view")
    return page(
        db,
        window_query(id, status),
        (ExpectedExecutionWindow.scheduled_at.desc(), ExpectedExecutionWindow.id),
        limit,
        offset,
        document,
    )


class StandaloneImport(Strict):
    domain: Literal["ETL", "VM", "API"]
    content: str
    format: Literal["JSON", "YAML"]


@router.post("/import/validate")
def validate_import(payload: StandaloneImport):
    require_permission("templates.view")
    try:
        parsed = import_document(payload.content, payload.format)
    except ValueError as error:
        raise HTTPException(422, str(error)) from None
    return {
        "configuration": checked_parameters(payload.domain, parsed),
        "validated": True,
        "saved": False,
        "activated": False,
    }


@router.get("/resources/{id}/metrics")
def available_metrics(id: uuid.UUID, db=Depends(get_db)):
    r = resource(db, id)
    source = r.data_source_id
    if r.linked_vm_id and r.domain == "ETL":
        vm = db.scalar(
            select(MonitoringResource).where(MonitoringResource.vm_id == r.linked_vm_id)
        )
        source = vm.data_source_id if vm else None
    if not source:
        return []
    return [
        {
            "id": m.id,
            "name": (m.query_config or {}).get("otel_metric_name", m.name),
            "unit": m.unit,
            "dimensions": (m.query_config or {}).get("dimensions", {}),
        }
        for m in db.scalars(
            select(MetricDefinition)
            .where(
                MetricDefinition.data_source_id == source,
                MetricDefinition.metric_type != "DERIVED_CONDITION",
            )
            .order_by(MetricDefinition.name)
            .limit(500)
        )
    ]


@router.get("/pipeline-platforms/{platform}")
def platform_definition(platform: str):
    from app.pipeline_adapters import describe_platform, AdapterError

    require_permission("etl.view")
    try:
        return describe_platform(platform)
    except AdapterError:
        raise HTTPException(422, "Unsupported pipeline platform") from None


@router.post("/resources/{id}/test-connection")
def test_connection(id: uuid.UUID, db=Depends(get_db)):
    from app.pipeline_adapters import test_platform_connection, AdapterError

    r = resource(db, id, "etl.configure")
    require_permission("collectors.manage", r.organization_id)
    if r.domain != "ETL" or not r.configuration.get("integration_configuration"):
        raise HTTPException(422, "Configure a native pipeline integration first")
    if not current_principal.get().platform_admin:
        raise HTTPException(
            403,
            "A platform administrator must authorize provider network/credential reads",
        )
    # Adapter egress validation uses deployment-approved host/CIDR/port lists.
    # The result is an actual read, never inferred from configuration saving.
    try:
        result = test_platform_connection(
            r.configuration["platform"], r.configuration["integration_configuration"]
        )
    except AdapterError as error:
        log_event(
            db,
            event_type="PIPELINE_CONNECTION_TEST",
            outcome="FAILURE",
            actor_id=current_principal.get().user_id,
            organization_id=r.organization_id,
            target_type="monitoring_resource",
            target_id=r.id,
        )
        db.commit()
        return {"connected": False, "error_kind": error.kind, "live_verified": False}
    audit(db, r, "PIPELINE_CONNECTION_TEST")
    commit(db)
    return {
        "connected": True,
        "observation": result,
        "observed_at": utc(),
        "connection_verified": True,
        "live_verified": False,  # Genuine provider acceptance is separately recorded.
    }


class PentahoRecoveryProposal(Strict):
    recovery_history_id: uuid.UUID
    evidence_ids: list[uuid.UUID] = Field(min_length=2, max_length=25)
    reason: str = Field(min_length=10, max_length=2000)
    idempotency_key: str = Field(min_length=1, max_length=100)


class PentahoRecoveryReview(Strict):
    action: Literal["CONFIRM", "REVERSE"]
    expected_revision: int = Field(ge=1)
    reason: str = Field(min_length=10, max_length=2000)
    idempotency_key: str = Field(min_length=1, max_length=100)


@router.get("/resources/{id}/executions/{history_id}/attempts")
def pentaho_attempts(
    id: uuid.UUID,
    history_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db=Depends(get_db),
):
    from app.unified.pentaho_recovery import history
    from app.unified.pentaho_models import PentahoAttempt, PentahoAlias, PentahoRevision

    r = resource(db, id, "etl.view")
    h = history(db, r, history_id)
    query = select(PentahoAttempt).where(PentahoAttempt.history_id == h.id)
    attempts = db.scalars(
        query.order_by(PentahoAttempt.attempt_order).offset(offset).limit(limit)
    ).all()
    ids = [a.id for a in attempts]
    aliases, alias_totals = children(
        db,
        PentahoAlias,
        PentahoAlias.attempt_id,
        ids,
        (PentahoAlias.created_at, PentahoAlias.id),
        200,
        document,
    )
    revisions, revision_totals = children(
        db,
        PentahoRevision,
        PentahoRevision.attempt_id,
        ids,
        (PentahoRevision.revision.desc(), PentahoRevision.id),
        100,
        document,
    )
    return {
        "execution": document(h),
        "total": db.scalar(select(func.count()).select_from(query.subquery())),
        "items": [
            {
                **document(a),
                "aliases": aliases[a.id],
                "aliases_total": alias_totals.get(a.id, 0),
                "revisions": revisions[a.id],
                "revisions_total": revision_totals.get(a.id, 0),
            }
            for a in attempts
        ],
    }


@router.get(
    "/resources/{id}/executions/{history_id}/attempts/{attempt_id}/{collection}"
)
def attempt_evidence(
    id: uuid.UUID,
    history_id: uuid.UUID,
    attempt_id: uuid.UUID,
    collection: Literal["aliases", "revisions"],
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db=Depends(get_db),
):
    from app.unified.pentaho_models import PentahoAttempt, PentahoAlias, PentahoRevision

    h = execution_history(db, id, history_id)
    a = db.scalar(
        select(PentahoAttempt).where(
            PentahoAttempt.id == attempt_id, PentahoAttempt.history_id == h.id
        )
    )
    if not a:
        raise HTTPException(404, "Attempt unavailable")
    model = PentahoAlias if collection == "aliases" else PentahoRevision
    ordering = (
        (model.created_at, model.id)
        if collection == "aliases"
        else (model.revision.desc(), model.id)
    )
    return page(
        db,
        select(model).where(model.attempt_id == a.id),
        ordering,
        limit,
        offset,
        document,
    )


@router.get("/resources/{id}/executions/{history_id}/recovery-links")
def pentaho_recovery_links(
    id: uuid.UUID,
    history_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db=Depends(get_db),
):
    from app.unified.pentaho_recovery import history
    from app.unified.pentaho_models import PentahoRecoveryLink, PentahoRecoveryDecision

    r = resource(db, id, "etl.view")
    h = history(db, r, history_id)
    query = select(PentahoRecoveryLink).where(
        PentahoRecoveryLink.organization_id == r.organization_id,
        or_(
            PentahoRecoveryLink.failed_history_id == h.id,
            PentahoRecoveryLink.recovery_history_id == h.id,
        ),
    )
    rows = db.scalars(
        query.order_by(PentahoRecoveryLink.created_at, PentahoRecoveryLink.id)
        .offset(offset)
        .limit(limit)
    ).all()
    return {
        "total": db.scalar(select(func.count()).select_from(query.subquery())),
        "items": [
            {
                **document(row),
                "decisions": [
                    document(d)
                    for d in db.scalars(
                        select(PentahoRecoveryDecision)
                        .where(PentahoRecoveryDecision.link_id == row.id)
                        .order_by(PentahoRecoveryDecision.revision)
                        .limit(100)
                    )
                ],
            }
            for row in rows
        ],
    }


@router.post("/resources/{id}/executions/{history_id}/recovery-links", status_code=201)
def propose_pentaho_recovery(
    id: uuid.UUID,
    history_id: uuid.UUID,
    payload: PentahoRecoveryProposal,
    db=Depends(get_db),
):
    from app.unified import pentaho_recovery as recovery

    r = resource(db, id, "etl.investigate")
    h = recovery.history(db, r, history_id, "etl.investigate")
    row = recovery.propose(
        db,
        h,
        payload.recovery_history_id,
        current_principal.get().user_id,
        payload.idempotency_key,
        payload.reason,
        payload.evidence_ids,
    )
    commit(db)
    return document(row)


@router.post(
    "/resources/{id}/executions/{history_id}/recovery-links/{link_id}/decision"
)
def review_pentaho_recovery(
    id: uuid.UUID,
    history_id: uuid.UUID,
    link_id: uuid.UUID,
    payload: PentahoRecoveryReview,
    db=Depends(get_db),
):
    from app.unified import pentaho_recovery as recovery

    r = resource(db, id, "etl.investigate")
    h = recovery.history(db, r, history_id, "etl.investigate")
    row = recovery.review(
        db,
        h,
        link_id,
        current_principal.get().user_id,
        payload.idempotency_key,
        payload.reason,
        payload.action,
        payload.expected_revision,
    )
    commit(db)
    return document(row)


class PentahoEvidenceReviewDecision(Strict):
    action: Literal["DEFER", "REJECT_CLAIM", "ACCEPT_VERIFIED_CLAIM", "ADOPT_LEGACY"]
    expected_revision: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=10, max_length=2000)


@router.get("/resources/{id}/evidence-reviews")
def pentaho_evidence_reviews(
    id: uuid.UUID,
    status: Literal["OPEN", "ACCEPTED", "REJECTED"] | None = None,
    category: (
        Literal[
            "AMBIGUOUS_IDENTITY",
            "NATIVE_ALIAS_CONFLICT",
            "RETRY_RELATIONSHIP",
            "EXECUTION_OUTCOME",
            "LEGACY_ADOPTION",
            "RECOVERY_IDENTITY",
        ]
        | None
    ) = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db=Depends(get_db),
):
    from app.unified.pentaho_models import PentahoEvidenceReview

    r = resource(db, id, "etl.view")
    query = select(PentahoEvidenceReview).where(
        PentahoEvidenceReview.resource_id == r.id,
        PentahoEvidenceReview.organization_id == r.organization_id,
    )
    if status:
        query = query.where(PentahoEvidenceReview.status == status)
    if category:
        query = query.where(PentahoEvidenceReview.category == category)
    return {
        "total": db.scalar(select(func.count()).select_from(query.subquery())),
        "items": [
            document(row)
            for row in db.scalars(
                query.order_by(
                    PentahoEvidenceReview.created_at, PentahoEvidenceReview.id
                )
                .offset(offset)
                .limit(limit)
            )
        ],
    }


@router.get("/resources/{id}/evidence-reviews/{review_id}")
def pentaho_evidence_review_details(
    id: uuid.UUID,
    review_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db=Depends(get_db),
):
    from app.unified.pentaho_models import (
        PentahoEvidenceReview,
        PentahoEvidenceDecision,
    )

    r = resource(db, id, "etl.view")
    row = db.scalar(
        select(PentahoEvidenceReview).where(
            PentahoEvidenceReview.id == review_id,
            PentahoEvidenceReview.resource_id == r.id,
            PentahoEvidenceReview.organization_id == r.organization_id,
        )
    )
    if not row:
        raise HTTPException(404, "Evidence review unavailable")
    query = select(PentahoEvidenceDecision).where(
        PentahoEvidenceDecision.review_id == row.id
    )
    return {
        "review": document(row),
        "total": db.scalar(select(func.count()).select_from(query.subquery())),
        "decisions": [
            document(v)
            for v in db.scalars(
                query.order_by(PentahoEvidenceDecision.revision)
                .offset(offset)
                .limit(limit)
            )
        ],
    }


@router.post("/resources/{id}/evidence-reviews/{review_id}/decision")
def decide_pentaho_evidence_review(
    id: uuid.UUID,
    review_id: uuid.UUID,
    payload: PentahoEvidenceReviewDecision,
    db=Depends(get_db),
):
    from app.unified.pentaho_review import decide

    r = resource(db, id, "etl.resolve_identity")
    row = decide(
        db,
        r,
        review_id,
        current_principal.get().user_id,
        payload.action,
        payload.expected_revision,
        payload.idempotency_key,
        payload.reason,
    )
    commit(db)
    return document(row)


class PentahoRecoveryIdentityIssue(Strict):
    category: Literal["RECOVERY_IDENTITY"]
    event_id: uuid.UUID
    expected_revision: Literal[0]
    idempotency_key: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=10, max_length=2000)


@router.post("/resources/{id}/evidence-reviews", status_code=201)
def flag_pentaho_recovery_identity(
    id: uuid.UUID, payload: PentahoRecoveryIdentityIssue, db=Depends(get_db)
):
    from app.unified.pentaho_review import flag_recovery_identity

    r = resource(db, id, "etl.resolve_identity")
    row = flag_recovery_identity(
        db,
        r,
        payload.event_id,
        current_principal.get().user_id,
        payload.idempotency_key,
        payload.reason,
    )
    commit(db)
    return document(row)


class PentahoHistoricalPolicy(Strict):
    enabled: bool
    destination_ids: list[uuid.UUID] = Field(default_factory=list, max_length=20)
    historical_after_seconds: int = Field(default=3600, ge=60, le=2592000)
    expected_revision: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=100)


@router.put("/resources/{id}/historical-notifications")
def pentaho_historical_policy(
    id: uuid.UUID, payload: PentahoHistoricalPolicy, db=Depends(get_db)
):
    from app.telemetry.models import NotificationDestination
    from app.telemetry.inbox import validate_targets
    from app.data_pipelines.service import operation

    r = resource(db, id, "templates.manage", True)
    require_permission("etl.configure", r.organization_id)
    if r.configuration.get("platform") != "PENTAHO":
        raise HTTPException(409, "Pentaho resource required")
    policy = payload.model_dump(
        mode="json", exclude={"expected_revision", "idempotency_key"}
    )
    if len(set(payload.destination_ids)) != len(payload.destination_ids) or (
        payload.enabled and not payload.destination_ids
    ):
        raise HTTPException(422, "Explicit unique destinations required")
    p = current_principal.get()
    for destination_id in payload.destination_ids:
        target = db.get(NotificationDestination, destination_id)
        if (
            not target
            or target.organization_id != r.organization_id
            or not target.enabled
        ):
            raise HTTPException(422, "Scoped enabled destination required")
        if target.channel == "IN_APP":
            if not target.configuration.get(
                "user_ids"
            ) and not target.configuration.get("department_ids"):
                raise HTTPException(
                    422, "Explicit users or teams required for historical notifications"
                )
            validate_targets(
                db, target.configuration, r.organization_id, p.service_provider_id
            )
    op, new = operation(
        db,
        r.organization_id,
        "PENTAHO_NOTICE_POLICY",
        payload.idempotency_key,
        {
            "resource_id": str(r.id),
            "policy": policy,
            "expected_revision": payload.expected_revision,
        },
        p.user_id,
    )
    if new:
        if r.revision != payload.expected_revision:
            raise HTTPException(409, "Resource changed; refresh before saving")
        r.configuration = {**r.configuration, "historical_notifications": policy}
        r.revision += 1
        op.state = "COMPLETE"
        op.result = {"resource_revision": r.revision}
        audit(db, r, "PENTAHO_HISTORICAL_POLICY_UPDATE")
    commit(db)
    return {
        "policy": r.configuration.get("historical_notifications"),
        "revision": r.revision,
    }


@router.get("/resources/{id}/historical-notifications")
def pentaho_historical_notices(
    id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db=Depends(get_db),
):
    from app.unified.pentaho_models import PentahoHistoricalNotice

    r = resource(db, id, "alerts.view")
    query = select(PentahoHistoricalNotice).where(
        PentahoHistoricalNotice.resource_id == r.id
    )
    return {
        "policy": r.configuration.get("historical_notifications", {"enabled": False}),
        "total": db.scalar(select(func.count()).select_from(query.subquery())),
        "items": [
            document(v)
            for v in db.scalars(
                query.order_by(
                    PentahoHistoricalNotice.created_at.desc(),
                    PentahoHistoricalNotice.id,
                )
                .offset(offset)
                .limit(limit)
            )
        ],
    }
