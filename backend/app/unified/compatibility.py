"""Keep legacy creation contracts visible through one unified identity binding.

Manual ARCH-001 onboarding owns its binding explicitly. Legacy callers add a
binding in the same transaction; no active monitoring or customer grant is
created implicitly. Ambiguous host sources are retained for reconciliation.
"""

from sqlalchemy import event, select, func
from sqlalchemy.orm import Session
from app.models import VM, JobOrder, DataSource, Collector
from app.unified.models import MonitoringResource, ResourceMappingIssue

ENVIRONMENTS = {"PROD", "QA", "TEST", "DEV", "SANDBOX"}


@event.listens_for(Session, "before_flush")
def capture_legacy(db, context, instances):
    if db.info.get("unified_manual_binding"):
        return
    candidates = [
        obj for obj in db.new if isinstance(obj, (VM, JobOrder, DataSource, Collector))
    ]
    if candidates:
        db.info.setdefault("unified_legacy_candidates", []).extend(candidates)


@event.listens_for(Session, "after_flush_postexec")
def bind_legacy(db, context):
    candidates = db.info.pop("unified_legacy_candidates", [])
    for obj in candidates:
        if isinstance(obj, Collector):
            root = db.scalar(
                select(MonitoringResource).where(
                    MonitoringResource.data_source_id == obj.data_source_id
                )
            )
            if (
                root
                and root.primary_collector_id is None
                and (
                    (root.domain == "VM" and obj.collector_type == "OTEL")
                    or (
                        root.domain == "API"
                        and obj.collector_type in {"API", "NATIVE_API"}
                    )
                )
            ):
                root.primary_collector_id = obj.id
            continue
        if isinstance(obj, VM):
            domain = "VM"
            name = obj.hostname
            environment = obj.environment
            org = obj.organization_id
            id = obj.id
            values = {
                "vm_id": id,
                "configuration": {
                    "legacy": True,
                    "hostname": name,
                    "os_type": obj.os or "Other",
                },
            }
            initial_source_id = getattr(obj, "_unified_initial_source_id", None)
            if initial_source_id is not None:
                source = db.get(DataSource, initial_source_id)
                if source is None or source.organization_id != org:
                    from fastapi import HTTPException

                    raise HTTPException(
                        409, "Initial host source must belong to the VM customer"
                    )
                values["data_source_id"] = source.id
        elif isinstance(obj, JobOrder):
            domain = "ETL"
            name = obj.name
            environment = obj.environment
            org = obj.organization_id
            id = obj.id
            values = {
                "job_order_id": id,
                "linked_vm_id": obj.vm_id,
                "configuration": {
                    "legacy": True,
                    "platform": "PENTAHO",
                    "jobchain": name,
                },
            }
        elif isinstance(obj, DataSource) and obj.source_type.upper() in {
            "API",
            "HTTP",
            "HTTPS",
        }:
            domain = "API"
            name = obj.name
            environment = (
                (obj.connection_config or {})
                .get("opscontrol", {})
                .get("environment", "PROD")
            )
            org = obj.organization_id
            id = obj.id
            values = {
                "data_source_id": id,
                "configuration": {"legacy": True, "endpoint": obj.endpoint},
            }
        else:
            continue
        if db.get(MonitoringResource, id):
            continue
        if str(environment).upper() not in ENVIRONMENTS:
            if not db.scalar(
                select(ResourceMappingIssue.id).where(
                    ResourceMappingIssue.entity_type == domain,
                    ResourceMappingIssue.entity_id == id,
                )
            ):
                db.add(
                    ResourceMappingIssue(
                        organization_id=org,
                        entity_type=domain,
                        entity_id=id,
                        reason="UNSUPPORTED_LEGACY_ENVIRONMENT",
                    )
                )
            continue
        db.add(
            MonitoringResource(
                id=id,
                organization_id=org,
                domain=domain,
                name=name,
                environment=str(environment).upper(),
                activation_status="CONFIGURED",
                **values
            )
        )
        if isinstance(obj, JobOrder) and obj.vm_id and obj.host_data_source_id:
            parent = db.scalar(
                select(MonitoringResource).where(MonitoringResource.vm_id == obj.vm_id)
            )
            if parent and parent.data_source_id is None:
                source = db.get(DataSource, obj.host_data_source_id)
                if source and source.organization_id == org:
                    parent.data_source_id = source.id
