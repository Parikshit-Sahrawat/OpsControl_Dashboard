"""Deny-by-default request context, ORM read isolation and write integrity.

This defense covers existing legacy routers as well as nested evidence reads.
Background workers explicitly run without a request principal and must use
separate worker/service authentication before accepting external instructions.
"""

from contextvars import ContextVar
from dataclasses import dataclass
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import event, select
from sqlalchemy.orm import Session, with_loader_criteria
from sqlalchemy import inspect


@dataclass(frozen=True)
class Principal:
    user_id: UUID
    username: str
    platform_admin: bool
    roles: dict[UUID, str]

    service_provider_id: UUID | None = None
    permissions: frozenset[str] = frozenset()
    customer_permissions: dict[UUID, frozenset[str]] | None = None
    provenance: tuple = ()
    role_ids: frozenset[UUID] = frozenset()
    denied_customers: frozenset[UUID] = frozenset()
    denied_permissions: frozenset[str] = frozenset()
    authorization_revision: str = "legacy"

    def allows(self, permission: str, organization_id: UUID | None = None) -> bool:
        if self.platform_admin:
            return True
        if self.customer_permissions is None:
            from app.security.permission_catalog import (
                READ,
                LEGACY_ADMIN,
                LEGACY_OPERATOR,
            )

            mapping = {
                "viewer": READ,
                "operator": LEGACY_OPERATOR,
                "org_admin": LEGACY_ADMIN,
            }
            if organization_id is not None:
                return permission in mapping.get(self.roles.get(organization_id), ())
            return any(
                permission in mapping.get(role, ()) for role in self.roles.values()
            )
        if organization_id is not None:
            return permission in self.customer_permissions.get(organization_id, ())
        return permission in self.permissions

    @property
    def organizations(self) -> tuple[UUID, ...]:
        from app.security.access_control import request_permissions

        required = request_permissions.get()
        return tuple(
            org
            for org in self.roles
            if not required or any(self.allows(key, org) for key in required)
        )

    def can_edit(self, organization_id: UUID) -> bool:
        from app.security.access_control import request_permissions

        required = request_permissions.get()
        return (
            any(self.allows(key, organization_id) for key in required)
            if required
            else self.allows("resources.update", organization_id)
        )


current_principal: ContextVar[Principal | None] = ContextVar(
    "opscontrol_principal", default=None
)

# The intermediary relationship paths are declarative mapper properties.
# Every table reachable from the public API MUST appear here, or be explicitly
# platform-only. Unmapped future tables are blocked for non-admin requests.
_PATHS = {
    "Organization": (),
    "VM": ("organization",),
    "Application": ("vm", "organization"),
    "PentahoInstance": ("vm", "organization"),
    "JobOrder": ("organization",),
    "JobOrderHistory": ("job_order", "organization"),
    "JobStepExecution": ("history", "job_order", "organization"),
    "Investigation": ("history", "job_order", "organization"),
    "InvestigationTransition": (
        "investigation",
        "history",
        "job_order",
        "organization",
    ),
    "OperatorNote": ("investigation", "history", "job_order", "organization"),
    "AlertIncidentEvent": ("history", "job_order", "organization"),
    "OperationalIncident": ("organization",),
    "IncidentActivity": ("organization",),
    "DataSource": ("organization",),
    "Collector": ("data_source", "organization"),
    "InfrastructureEvidence": ("organization",),
    "CollectorRun": ("collector", "data_source", "organization"),
    "MetricDefinition": ("organization",),
    "MetricSample": ("metric_definition", "organization"),
    "LogSource": ("organization",),
    "LogEvent": ("organization",),
    "AlertRule": ("organization",),
    "AlertState": ("organization",),
    "AlertNotificationDelivery": ("alert_state", "organization"),
    "CorrelationRecord": ("organization",),
    "CorrelationEvidence": ("correlation", "organization"),
    "MonitoringTemplateAttachment": ("data_source", "organization"),
    "MonitoringRuleCatalog": ("organization",),
    "MonitoringRuleVersion": ("catalog", "organization"),
    "MonitoringActivation": ("organization",),
    "MonitoringRuleBinding": ("activation", "organization"),
}
_PATHS.update(
    {
        name: ()
        for name in (
            "CollectorMethod",
            "ManagedAgent",
            "AgentRegistration",
            "CollectorConfigVersion",
            "AgentDeployment",
            "TelemetryReceipt",
            "TraceSpan",
            "NotificationDestination",
            "InAppNotification",
            "MonitoringResource",
            "ResourceDependency",
            "ParameterVersion",
            "ParameterActivation",
            "NormalizedEvent",
            "ExpectedExecutionWindow",
            "ResourceCondition",
            "EventCorrelationGroup",
            "EventCorrelationMember",
            "ResourceMappingIssue",
            "CollectorRuntimeState",
            "NativeIncidentDetails",
            "NativeIncidentAlert",
        )
    }
)
_GLOBAL = {
    "MonitoringTemplate",
    "MonitoringTemplateVersion",
    "AttributeRegistryVersion",
}


def _predicate(model, allowed):
    """Build a correlated EXISTS condition across ORM relationships."""
    if model.__name__ == "Organization":
        return model.id.in_(allowed)
    if hasattr(model, "organization_id"):
        return model.organization_id.in_(allowed)
    path = _PATHS[model.__name__]

    def build(cls, rest):
        rel = getattr(cls, rest[0])
        target = rel.property.mapper.class_
        if hasattr(target, "organization_id"):
            inner = target.organization_id.in_(allowed)
        elif target.__name__ == "Organization":
            inner = target.id.in_(allowed)
        else:
            inner = build(target, rest[1:])
        return rel.has(inner)

    return build(model, path)


def configure_request_session(db: Session):
    principal = current_principal.get()
    if principal is None:
        # Middleware is expected to reject missing credentials before routers.
        raise HTTPException(401, "Authentication required")
    db.info["opscontrol_principal"] = principal


@event.listens_for(Session, "do_orm_execute")
def scope_reads(execute_state):
    principal = execute_state.session.info.get("opscontrol_principal")
    if principal is None or principal.platform_admin or not execute_state.is_select:
        return
    from app.db.session import Base

    allowed = principal.organizations
    stmt = execute_state.statement
    for mapper in Base.registry.mappers:
        model = mapper.class_
        if model.__name__ == "ResourceDraft":
            from sqlalchemy import and_, or_

            stmt = stmt.options(
                with_loader_criteria(
                    model,
                    and_(
                        model.owner_id == principal.user_id,
                        model.service_provider_id == principal.service_provider_id,
                        or_(
                            model.organization_id.is_(None),
                            model.organization_id.in_(allowed),
                        ),
                    ),
                    include_aliases=True,
                )
            )
        elif model.__name__ in _PATHS:
            stmt = stmt.options(
                with_loader_criteria(
                    model,
                    _predicate(model, allowed),
                    include_aliases=True,
                )
            )
    execute_state.statement = stmt


def _resolve_org(db, obj, depth=0):
    if depth > 7:
        raise HTTPException(409, "Invalid nested organization relationship")
    model = type(obj)
    if model.__name__ == "Organization":
        return obj.id
    if hasattr(obj, "organization_id"):
        return obj.organization_id
    if model.__name__ not in _PATHS or not _PATHS[model.__name__]:
        raise HTTPException(403, "Cannot modify a platform resource")
    relation_name = _PATHS[model.__name__][0]
    rel = inspect(model).relationships[relation_name]
    parent = getattr(obj, relation_name, None)
    if parent is None:
        fks = list(rel.local_columns)
        if len(fks) != 1:
            raise HTTPException(409, "Unsupported organization relationship")
        parent_id = getattr(obj, next(iter(fks)).key)
        if not parent_id:
            raise HTTPException(409, "Missing parent resource")
        parent = db.get(rel.mapper.class_, parent_id)
    if parent is None:
        raise HTTPException(404, "Parent resource not found")
    return _resolve_org(db, parent, depth + 1)


@event.listens_for(Session, "before_flush")
def enforce_writes(db, flush_context, instances):
    principal = db.info.get("opscontrol_principal")
    if principal is None:
        return  # local CLI/worker is outside the HTTP request identity contract
    for obj in db.new.union(db.dirty).union(db.deleted):
        model = type(obj)
        if model.__name__ == "ResourceDraft":
            if (
                obj.owner_id != principal.user_id
                or obj.service_provider_id != principal.service_provider_id
            ):
                raise HTTPException(403, "Draft owner/provider identity mismatch")
            state = inspect(obj)
            if state.persistent and any(
                state.attrs[k].history.has_changes()
                for k in ("owner_id", "service_provider_id", "domain")
            ):
                raise HTTPException(403, "Draft identity is immutable")
            if obj.organization_id and not principal.allows(
                "resources.create", obj.organization_id
            ):
                raise HTTPException(403, "Customer draft permission required")
            continue
        if model.__name__ == "WorkerIdentity":
            state = inspect(obj)
            changed = {
                attribute.key
                for attribute in state.attrs
                if attribute.history.has_changes()
            }
            if (
                obj in db.new
                or obj in db.deleted
                or not state.persistent
                or db.info.get("agent_revocation_worker") != obj.id
                or changed != {"enabled"}
                or obj.enabled is not False
                or not principal.allows("collectors.manage", obj.organization_id)
            ):
                raise HTTPException(
                    403, "Only authorized bound Agent credential revocation is allowed"
                )
            from app.telemetry.models import ManagedAgent

            bound = db.scalar(
                select(ManagedAgent).where(
                    ManagedAgent.worker_id == obj.id,
                    ManagedAgent.organization_id == obj.organization_id,
                )
            )
            if not bound or bound.enabled:
                raise HTTPException(403, "Credential is not bound to a revoked Agent")
            continue
        if model.__name__ == "SecurityAuditEvent":
            # Services append server-derived audit events in the mutation's
            # transaction. No client route accepts audit model payloads.
            if (
                obj not in db.new
                or obj.actor_id != principal.user_id
                or obj.outcome not in {"SUCCESS", "DENIED", "FAILURE"}
            ):
                raise HTTPException(403, "Invalid audit mutation")
            if obj.organization_id is not None and not principal.can_edit(
                obj.organization_id
            ):
                raise HTTPException(403, "Audit organization permission required")
            continue
        if model.__name__ in _GLOBAL:
            if not principal.platform_admin:
                raise HTTPException(403, "Platform administrator required")
            continue
        if model.__name__ not in _PATHS:
            raise HTTPException(403, "Resource cannot be modified through this API")
        if model.__name__ == "Collector" and not principal.platform_admin:
            from app.worker.infrastructure import INFRA_TYPES

            state = inspect(obj)
            previous_types = state.attrs.collector_type.history.deleted
            protected_types = INFRA_TYPES | {
                "PENTAHO",
                "API",
                "NATIVE_API",
                "IICS_NATIVE",
                "PIPELINE_NATIVE",
            }
            protected_type = obj.collector_type.upper() in protected_types or any(
                str(t).upper() in protected_types for t in previous_types
            )
            if protected_type and (
                (obj in db.new and obj.enabled)
                or (
                    obj not in db.new
                    and any(
                        state.attrs[key].history.has_changes()
                        for key in ("configuration", "collector_type")
                    )
                )
                or (state.attrs.enabled.history.has_changes() and obj.enabled)
            ):
                raise HTTPException(
                    403,
                    "Platform administrator must authorize local provider collection",
                )
        org_id = _resolve_org(db, obj)
        from app.security.access_control import request_permissions

        can_investigate = (
            not request_permissions.get()
            and model.__name__
            in {
                "Investigation",
                "InvestigationTransition",
                "OperatorNote",
                "CorrelationRecord",
                "CorrelationEvidence",
                "OperationalIncident",
                "IncidentActivity",
            }
            and (
                principal.allows("etl.investigate", org_id)
                or principal.allows("incidents.manage", org_id)
                or principal.allows("incidents.acknowledge", org_id)
            )
        )
        if not (
            principal.can_edit(org_id)
            or can_investigate
            or (
                model.__name__ == "Organization"
                and obj in db.new
                and principal.allows("customers.create")
            )
        ):
            raise HTTPException(403, "Organization permission required")
        state = inspect(obj)
        if state.persistent:
            for attr in (
                "organization_id",
                "data_source_id",
                "collector_id",
                "job_order_id",
                "vm_id",
                "history_id",
                "metric_definition_id",
                "log_source_id",
                "alert_rule_id",
                "alert_state_id",
                "incident_id",
                "episode_key",
                "source_reference",
                "source_kind",
                "catalog_id",
                "activation_id",
                "rule_version_id",
                "host_data_source_id",
                "resource_id",
                "depends_on_id",
                "group_id",
                "condition_id",
            ):
                if attr in state.attrs and state.attrs[attr].history.has_changes():
                    raise HTTPException(
                        403, "Changing resource ownership is not supported"
                    )
        # All tenant-owned foreign keys must point to resources in the SAME org.
        for attr, parent_type in (
            ("data_source_id", "DataSource"),
            ("collector_id", "Collector"),
            ("metric_definition_id", "MetricDefinition"),
            ("log_source_id", "LogSource"),
            ("alert_rule_id", "AlertRule"),
            ("catalog_id", "MonitoringRuleCatalog"),
            ("activation_id", "MonitoringActivation"),
            ("rule_version_id", "MonitoringRuleVersion"),
            ("vm_id", "VM"),
            ("job_order_id", "JobOrder"),
            ("history_id", "JobOrderHistory"),
            ("host_data_source_id", "DataSource"),
            ("incident_id", "OperationalIncident"),
            ("alert_state_id", "AlertState"),
            ("template_id", "MonitoringTemplate"),
            ("linked_vm_id", "VM"),
            ("resource_id", "MonitoringResource"),
            ("depends_on_id", "MonitoringResource"),
            ("group_id", "EventCorrelationGroup"),
            ("condition_id", "ResourceCondition"),
        ):
            if attr == "resource_id" and model.__name__ == "MetricDefinition":
                continue  # Legacy untyped reference; organization/source ownership remains enforced.
            if not hasattr(obj, attr):
                continue
            parent_id = getattr(obj, attr)
            if parent_id is None or parent_type in _GLOBAL:
                continue
            from app.db.session import Base

            parent_model = next(
                (
                    m.class_
                    for m in Base.registry.mappers
                    if m.class_.__name__ == parent_type
                ),
                None,
            )
            parent = (
                db.get(parent_model, parent_id) if parent_model is not None else None
            )
            if parent is None or _resolve_org(db, parent) != org_id:
                raise HTTPException(
                    409, "Referenced resource is unavailable in this organization"
                )
    if (db.new or db.dirty or db.deleted) and not db.info.get(
        "opscontrol_mutation_audited"
    ):
        # Append only AFTER all authorization/FK checks pass, inside the same
        # transaction as the mutation. A later rollback also rolls back audit.
        from app.security.audit import log_event

        log_event(
            db,
            event_type="CONFIG_MUTATION",
            outcome="SUCCESS",
            actor_id=principal.user_id,
            target_type="route",
            target_id=db.info.get("opscontrol_route", "scoped-transaction"),
        )
        db.info["opscontrol_mutation_audited"] = True


@event.listens_for(Session, "after_commit")
@event.listens_for(Session, "after_rollback")
def reset_mutation_audit(db):
    db.info.pop("opscontrol_mutation_audited", None)
