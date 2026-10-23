"""SQL resource/environment constraints layered onto existing customer isolation.

Queries use Core subqueries so criteria never recursively apply themselves. A
shared source/incident is visible only if all of its bound resources are visible.
Unknown binding under a restriction fails closed. No per-inventory-row queries.
"""

from sqlalchemy import and_, or_, true, false, select, union_all
from uuid import UUID
from app.security.access_control import request_permissions
from app.security.boundaries import relevant


def predicates(p):
    from app.db.session import Base

    tables = {m.class_.__name__: m.local_table for m in Base.registry.mappers}
    r = tables["MonitoringResource"]
    keys = request_permissions.get()
    selected = set(p.organizations)
    affected = {
        UUID(cid)
        for b in p.boundaries
        if b["kind"] in {"LIMIT", "DENY"}
        and set(b["specification"]["permissions"]) & set(keys)
        for cid in b["specification"]["customers"]
    } & selected
    unrestricted = selected - affected
    resource_terms = [r.c.organization_id.in_(unrestricted)] if unrestricted else []
    for customer in affected:
        for key in keys:
            if not p.allows(key, customer):
                continue
            rows = relevant(p, customer, key)

            def match(b):
                s = b["specification"]
                terms = []
                if s["environments"]:
                    terms.append(r.c.environment.in_(s["environments"]))
                if s["resources"]:
                    terms.append(r.c.id.in_(s["resources"]))
                return and_(*terms) if terms else true()

            limits = [match(b) for b in rows if b["kind"] == "LIMIT"]
            denies = [match(b) for b in rows if b["kind"] == "DENY"]
            resource_terms.append(
                and_(
                    r.c.organization_id == customer,
                    and_(*limits) if limits else true(),
                    ~or_(*denies) if denies else true(),
                )
            )
    visible = select(r.c.id).where(or_(*resource_terms) if resource_terms else false())
    cache = {}
    working = set()

    def expr(name):
        if name in cache:
            return cache[name]
        if name in working or name not in tables:
            return false()
        working.add(name)
        t = tables[name]
        c = t.c
        if name == "MonitoringResource":
            value = c.id.in_(visible)
        elif name == "KubernetesClusterAssociation":
            # Cluster IDs are their own scoped resources; they are not VM
            # MonitoringResource IDs and cannot inherit VM visibility.
            terms = []
            for customer in affected:
                for key in keys:
                    if not p.allows(key, customer):
                        continue
                    rows = relevant(p, customer, key)

                    def matches(boundary):
                        scope = boundary["specification"]
                        return false() if scope["environments"] else (
                            c.cluster_id.in_(scope["resources"])
                            if scope["resources"] else true()
                        )

                    limits = [matches(b) for b in rows if b["kind"] == "LIMIT"]
                    denies = [matches(b) for b in rows if b["kind"] == "DENY"]
                    terms.append(and_(
                        c.organization_id == customer,
                        and_(*limits) if limits else true(),
                        ~or_(*denies) if denies else true(),
                    ))
            value = or_(*terms) if terms else false()
        elif name == "Organization":
            value = true()
        elif name == "JobOrder":
            value = c.id.in_(select(r.c.job_order_id).where(r.c.id.in_(visible)))
        elif name in {"VM", "DataSource", "Collector"}:
            col = {
                "VM": "vm_id",
                "DataSource": "data_source_id",
                "Collector": "primary_collector_id",
            }[name]
            bound = select(r.c[col]).where(r.c[col].is_not(None))
            value = and_(
                c.id.in_(bound.where(r.c.id.in_(visible))),
                ~c.id.in_(bound.where(~r.c.id.in_(visible))),
            )
        elif name == "PipelineIntegration":
            j = tables["PipelineJob"]
            jobs = select(j.c.integration_id)
            # Unknown/unselected bindings cannot certify a restricted integration.
            value = and_(
                c.id.in_(jobs.where(j.c.resource_id.in_(visible))),
                ~c.id.in_(
                    jobs.where(
                        or_(j.c.resource_id.is_(None), ~j.c.resource_id.in_(visible))
                    )
                ),
            )
        elif name == "PipelineSource":
            m = tables["PipelineMethod"]
            a = tables["PipelineAssociation"]
            j = tables["PipelineJob"]
            refs = select(m.c.source_id).select_from(
                m.join(a, a.c.method_id == m.c.id).join(j, j.c.id == a.c.job_id)
            )
            value = and_(
                c.id.in_(refs.where(j.c.resource_id.in_(visible))),
                ~c.id.in_(
                    refs.where(
                        or_(j.c.resource_id.is_(None), ~j.c.resource_id.in_(visible))
                    )
                ),
            )
        elif name == "OperationalIncident":
            f = tables["NativeIncidentFailure"]
            a = tables["NativeIncidentAlert"]
            condition = tables["ResourceCondition"]
            h = tables["JobOrderHistory"]
            refs = union_all(
                select(
                    f.c.incident_id.label("incident"), f.c.resource_id.label("resource")
                ),
                select(a.c.incident_id, condition.c.resource_id).select_from(
                    a.outerjoin(
                        condition, a.c.alert_state_id == condition.c.alert_state_id
                    )
                ),
                select(c.id, r.c.id).select_from(
                    t.join(h, c.history_id == h.c.id).join(
                        r, r.c.job_order_id == h.c.job_order_id
                    )
                ),
            ).subquery()
            value = and_(
                c.id.in_(select(refs.c.incident).where(refs.c.resource.in_(visible))),
                ~c.id.in_(
                    select(refs.c.incident).where(
                        or_(refs.c.resource.is_(None), ~refs.c.resource.in_(visible))
                    )
                ),
            )
        elif "resource_id" in c:
            value = c.resource_id.in_(visible)
        else:
            parents = {
                "history_id": "JobOrderHistory",
                "failed_history_id": "JobOrderHistory",
                "recovery_history_id": "JobOrderHistory",
                "job_order_id": "JobOrder",
                "incident_id": "OperationalIncident",
                "collector_id": "Collector",
                "data_source_id": "DataSource",
                "vm_id": "VM",
                "metric_definition_id": "MetricDefinition",
                "log_source_id": "LogSource",
                "alert_rule_id": "AlertRule",
                "alert_state_id": "AlertState",
                "catalog_id": "MonitoringRuleCatalog",
                "activation_id": "MonitoringActivation",
                "rule_version_id": "MonitoringRuleVersion",
            }
            if name.startswith(("Pipeline", "Pentaho")):
                parents.update(
                    source_id="PipelineSource",
                    integration_id="PipelineIntegration",
                    method_id="PipelineMethod",
                    link_id="PentahoRecoveryLink",
                    attempt_id="PentahoAttempt",
                    review_id="PentahoEvidenceReview",
                )
            terms = []
            present = []
            for col, parent in parents.items():
                if col in c and parent in tables:
                    terms.append(
                        or_(
                            c[col].is_(None),
                            c[col].in_(select(tables[parent].c.id).where(expr(parent))),
                        )
                    )
                    present.append(c[col].is_not(None))
            value = and_(*terms, or_(*present)) if terms else false()
            if name == "PipelineEvidence":
                j = tables["PipelineJob"]
                value = and_(
                    value,
                    c.native_job_id.in_(
                        select(j.c.native_id).where(j.c.resource_id.in_(visible))
                    ),
                )
        working.remove(name)
        cache[name] = value
        return value

    return tables, affected, expr


def resource_predicate(model, p, plan=None):
    if p.platform_admin or not any(
        b["kind"] in {"LIMIT", "DENY"} for b in p.boundaries
    ):
        return true()
    tables, affected, expr = plan if plan is not None else predicates(p)
    if not affected:
        return true()
    t = tables[model.__name__]
    if model.__name__ == "Organization":
        return true()
    constrained = expr(model.__name__)
    # Preserve unrestricted customers; restrict only the specifically scoped key.
    if "organization_id" in t.c:
        return or_(~model.organization_id.in_(affected), constrained)
    return constrained


def check_write(db, obj, p):
    if p.platform_admin or not any(
        b["kind"] in {"LIMIT", "DENY"} for b in p.boundaries
    ):
        return
    from sqlalchemy import inspect
    from fastapi import HTTPException
    from app.security.boundaries import permits

    keys = request_permissions.get()
    state = inspect(obj)
    org = getattr(obj, "organization_id", None)
    if org and not any(relevant(p, org, k) for k in keys):
        return
    if type(obj).__name__ == "MonitoringResource":
        if any(
            p.allows(k, org) and permits(p, k, org, obj.environment, obj.id)
            for k in keys
        ):
            return
        raise HTTPException(
            403, "Environment/resource restriction prohibits this change"
        )
    if state.persistent:
        model = type(obj)
        pk = next(iter(model.__table__.primary_key.columns))
        value = getattr(obj, pk.name)
        if (
            db.scalar(select(pk).where(pk == value, resource_predicate(model, p)))
            is not None
        ):
            return
    else:
        tables, affected, expr = predicates(p)
        if org and org not in affected:
            return
        parents = {
            "resource_id": "MonitoringResource",
            "history_id": "JobOrderHistory",
            "failed_history_id": "JobOrderHistory",
            "recovery_history_id": "JobOrderHistory",
            "incident_id": "OperationalIncident",
            "job_order_id": "JobOrder",
            "source_id": "PipelineSource",
            "integration_id": "PipelineIntegration",
            "method_id": "PipelineMethod",
            "attempt_id": "PentahoAttempt",
            "review_id": "PentahoEvidenceReview",
            "link_id": "PentahoRecoveryLink",
        }
        found = False
        for col, parent in parents.items():
            value = getattr(obj, col, None)
            if value is not None and parent in tables:
                found = True
                t = tables[parent]
                if (
                    db.scalar(select(t.c.id).where(t.c.id == value, expr(parent)))
                    is None
                ):
                    break
        else:
            if found:
                return
    raise HTTPException(403, "Resource restriction or ambiguous resource binding")


def source_authorized(db, principal, source, permission):
    """Workers must recheck boundaries as well as current role keys at use time."""
    if principal is None or not principal.allows(permission, source.organization_id):
        return False
    from app.data_pipelines.models import PipelineSource

    token = request_permissions.set((permission,))
    try:
        table = PipelineSource.__table__
        return (
            db.scalar(
                select(table.c.id).where(
                    table.c.id == source.id,
                    resource_predicate(PipelineSource, principal),
                )
            )
            is not None
        )
    finally:
        request_permissions.reset(token)
