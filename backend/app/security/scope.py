"""Deny-by-default request context, ORM read isolation and write integrity.

This defense covers existing legacy routers as well as nested evidence reads.
Background workers explicitly run without a request principal and must use
separate worker/service authentication before accepting external instructions.
"""
from contextvars import ContextVar
from dataclasses import dataclass
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import event
from sqlalchemy.orm import Session, with_loader_criteria
from sqlalchemy import inspect

@dataclass(frozen=True)
class Principal:
    user_id: UUID
    username: str
    platform_admin: bool
    roles: dict[UUID, str]

    @property
    def organizations(self) -> tuple[UUID, ...]:
        return tuple(self.roles)

    def can_edit(self, organization_id: UUID) -> bool:
        return self.platform_admin or self.roles.get(organization_id) == "org_admin"

current_principal: ContextVar[Principal | None] = ContextVar("opscontrol_principal", default=None)

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
    "InvestigationTransition": ("investigation", "history", "job_order", "organization"),
    "OperatorNote": ("investigation", "history", "job_order", "organization"),
    "AlertIncidentEvent": ("history", "job_order", "organization"),
    "DataSource": ("organization",),
    "Collector": ("data_source", "organization"),
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
}
_GLOBAL = {"MonitoringTemplate", "MonitoringTemplateVersion"}

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
        if model.__name__ in _PATHS:
            stmt = stmt.options(with_loader_criteria(
                model, _predicate(model, allowed), include_aliases=True,
            ))
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
        if model.__name__ in _GLOBAL:
            if not principal.platform_admin:
                raise HTTPException(403, "Platform administrator required")
            continue
        if model.__name__ not in _PATHS:
            raise HTTPException(403, "Resource cannot be modified through this API")
        org_id = _resolve_org(db, obj)
        can_investigate = (model.__name__ in {"Investigation", "InvestigationTransition", "OperatorNote"}
                           and principal.roles.get(org_id) in {"operator", "org_admin"})
        if not (principal.can_edit(org_id) or can_investigate):
            raise HTTPException(403, "Organization permission required")
        state = inspect(obj)
        if state.persistent:
            for attr in ("organization_id", "data_source_id", "collector_id", "job_order_id",
                         "vm_id", "history_id", "metric_definition_id", "log_source_id",
                         "alert_rule_id", "alert_state_id"):
                if attr in state.attrs and state.attrs[attr].history.has_changes():
                    raise HTTPException(403, "Changing resource ownership is not supported")
        # All tenant-owned foreign keys must point to resources in the SAME org.
        for attr, parent_type in (("data_source_id", "DataSource"), ("collector_id", "Collector"),
                                  ("metric_definition_id", "MetricDefinition"), ("log_source_id", "LogSource"),
                                  ("alert_rule_id", "AlertRule"), ("vm_id", "VM"),
                                  ("job_order_id", "JobOrder"), ("history_id", "JobOrderHistory"),
                                  ("template_id", "MonitoringTemplate")):
            if not hasattr(obj, attr):
                continue
            parent_id = getattr(obj, attr)
            if parent_id is None or parent_type in _GLOBAL:
                continue
            from app.db.session import Base
            parent_model = next((m.class_ for m in Base.registry.mappers if m.class_.__name__ == parent_type), None)
            parent = db.get(parent_model, parent_id) if parent_model is not None else None
            if parent is None or _resolve_org(db, parent) != org_id:
                raise HTTPException(409, "Referenced resource is unavailable in this organization")
