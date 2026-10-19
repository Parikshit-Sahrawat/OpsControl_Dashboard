"""Owned PostgreSQL scope, preservation and delegation regressions."""

import os, unittest, uuid
from contextlib import contextmanager
from dataclasses import replace
from sqlalchemy import select, func, event, text
from sqlalchemy.exc import DBAPIError
from fastapi import HTTPException
from starlette.requests import Request
from app.db.session import SessionLocal
from app.security.access_models import (
    AccessBoundary,
    AccessBoundaryDecision,
    Department,
    DepartmentMembership,
    UserRoleAssignment,
    Role,
    RolePermission,
    CustomerAccessGrant,
    DepartmentRoleAssignment,
)
from app.security.access_control import (
    resolve_access,
    request_permissions,
    effective_document,
)
from app.security.boundaries import selected_customers, choose, specification
from app.security.scope import current_principal, configure_request_session
from app.security.permission_catalog import PROVIDER_ID
from app.security.delegation import check_role
from app.models import Organization
from app.unified.models import MonitoringResource
from tests.test_pentaho_incident_r1 import PentahoIncidentTests


@unittest.skipUnless(
    os.getenv("OPSCONTROL_V16_ACCEPTANCE") == "1", "Owned PostgreSQL required"
)
class Sprint08RBAC(unittest.TestCase):
    setUp = PentahoIncidentTests.setUp
    grant = PentahoIncidentTests.grant

    def role(self, keys):
        r = Role(
            service_provider_id=PROVIDER_ID,
            code="s08-" + uuid.uuid4().hex,
            name="Scoped " + uuid.uuid4().hex,
        )
        self.db.add(r)
        self.db.flush()
        for key in keys:
            self.db.add(RolePermission(role_id=r.id, permission_key=key))
        self.db.commit()
        return r

    def boundary(self, kind="LIMIT", subject=None, **spec):
        doc = specification(kind, spec)
        b = AccessBoundary(
            service_provider_id=PROVIDER_ID,
            user_id=subject or self.user.id,
            kind=kind,
            specification=doc,
            active=True,
            revision=1,
        )
        self.db.add(b)
        self.db.commit()
        return b

    @contextmanager
    def principal(self, keys=("resources.view",), selection=True, user=None):
        p = resolve_access(self.db, user or self.user)
        a = current_principal.set(p)
        b = request_permissions.set(keys)
        c = selected_customers.set(
            frozenset([self.org.id]) if selection else frozenset()
        )
        try:
            with SessionLocal() as scoped:
                configure_request_session(scoped)
                yield p, scoped
        finally:
            current_principal.reset(a)
            request_permissions.reset(b)
            selected_customers.reset(c)

    def access(self):
        self.grant(self.user, ["resources.view", "etl.view", "incidents.view"])

    def test_one_customer_sql_scope(self):
        self.access()
        with self.principal() as (p, db):
            self.assertEqual(
                db.scalars(select(MonitoringResource.id)).all(), [self.resource.id]
            )

    def test_no_selection_is_empty(self):
        self.access()
        with self.principal(selection=False) as (p, db):
            self.assertEqual(db.scalars(select(MonitoringResource.id)).all(), [])

    def test_omitted_selection_and_wildcard_fail_closed(self):
        self.access()
        p = resolve_access(self.db, self.user)
        self.assertEqual(
            choose(p, Request({"type": "http", "headers": [], "query_string": b""})),
            frozenset(),
        )
        with self.assertRaises(HTTPException):
            choose(
                p,
                Request(
                    {
                        "type": "http",
                        "headers": [(b"x-opscontrol-customers", b"*")],
                        "query_string": b"",
                    }
                ),
            )

    def test_all_requires_separate_authority(self):
        self.access()
        p = resolve_access(self.db, self.user)
        with self.assertRaises(HTTPException):
            choose(
                p,
                Request(
                    {
                        "type": "http",
                        "headers": [(b"x-opscontrol-customers", b"ALL")],
                        "query_string": b"",
                    }
                ),
            )

    def test_all_future_and_snapshot_semantics(self):
        r = self.role(["etl.view"])
        self.db.add(
            UserRoleAssignment(
                user_id=self.user.id, role_id=r.id, service_provider_id=PROVIDER_ID
            )
        )
        self.db.commit()
        b = self.boundary(
            "ALL_CUSTOMERS",
            permissions=["etl.view"],
            role_id=r.id,
            customers=[self.org.id],
        )
        future = Organization(
            name="Future " + uuid.uuid4().hex, code=uuid.uuid4().hex[:16], active=True
        )
        self.db.add(future)
        self.db.commit()
        self.assertNotIn(future.id, resolve_access(self.db, self.user).roles)
        b.specification = specification(
            "ALL_CUSTOMERS", {**b.specification, "include_future": True}
        )
        b.revision += 1
        self.db.commit()
        p = resolve_access(self.db, self.user)
        self.assertTrue(p.all_customers)
        self.assertTrue(p.allows("etl.view", future.id))

    def test_unassigned_all_role_never_grants(self):
        r = self.role(["etl.view"])
        self.boundary(
            "ALL_CUSTOMERS", permissions=["etl.view"], role_id=r.id, include_future=True
        )
        p = resolve_access(self.db, self.user)
        self.assertFalse(p.all_customers)
        self.assertFalse(p.allows("etl.view", self.org.id))

    def test_environment_limit_filters_before_pagination(self):
        self.access()
        self.boundary(
            permissions=["resources.view"],
            customers=[self.org.id],
            environments=["PROD"],
        )
        with self.principal() as (p, db):
            self.assertEqual(
                db.scalar(select(func.count()).select_from(MonitoringResource)), 0
            )

    def test_resource_limit_allows_exact_id(self):
        self.access()
        self.boundary(
            permissions=["resources.view"],
            customers=[self.org.id],
            resources=[self.resource.id],
        )
        with self.principal() as (p, db):
            self.assertIsNotNone(
                db.scalar(
                    select(MonitoringResource).where(
                        MonitoringResource.id == self.resource.id
                    )
                )
            )

    def test_deny_overrides_limit_and_inherited_allow(self):
        self.access()
        self.boundary(
            permissions=["resources.view"],
            customers=[self.org.id],
            resources=[self.resource.id],
        )
        self.boundary(
            "DENY",
            permissions=["resources.view"],
            customers=[self.org.id],
            environments=["TEST"],
        )
        with self.principal() as (p, db):
            self.assertEqual(db.scalars(select(MonitoringResource.id)).all(), [])

    def test_global_employee_deny_survives_other_grants(self):
        self.access()
        r = self.role(["etl.view"])
        self.db.add(
            UserRoleAssignment(
                user_id=self.user.id,
                role_id=r.id,
                service_provider_id=PROVIDER_ID,
                effect="DENY",
            )
        )
        self.db.commit()
        self.assertFalse(
            resolve_access(self.db, self.user).allows("etl.view", self.org.id)
        )

    def test_direct_and_legacy_multi_department_inheritance_preserved(self):
        self.access()
        r = self.role(["etl.investigate"])
        deps = []
        # Controlled fixture representing memberships predating the existing
        # single-department trigger; production creation is tested via HTTP.
        self.db.execute(
            text(
                "ALTER TABLE department_memberships DISABLE TRIGGER trg_single_department"
            )
        )
        for _ in range(2):
            d = Department(
                name=uuid.uuid4().hex, service_provider_id=PROVIDER_ID, active=True
            )
            self.db.add(d)
            self.db.flush()
            deps.append(d.id)
            self.db.add_all(
                [
                    DepartmentMembership(
                        user_id=self.user.id,
                        department_id=d.id,
                        service_provider_id=PROVIDER_ID,
                    ),
                    DepartmentRoleAssignment(
                        department_id=d.id,
                        role_id=r.id,
                        service_provider_id=PROVIDER_ID,
                    ),
                ]
            )
            self.db.flush()
            self.db.add(
                CustomerAccessGrant(
                    department_id=d.id,
                    organization_id=self.org.id,
                    role_id=r.id,
                    service_provider_id=PROVIDER_ID,
                )
            )
        self.db.execute(
            text(
                "ALTER TABLE department_memberships ENABLE TRIGGER trg_single_department"
            )
        )
        self.db.commit()
        p = resolve_access(self.db, self.user)
        self.assertTrue(p.allows("etl.investigate", self.org.id))
        self.assertEqual(
            sum(
                s["source"] == "department" and "customer_id" in s for s in p.provenance
            ),
            2,
        )
        self.assertEqual(
            self.db.scalar(
                select(func.count())
                .select_from(DepartmentMembership)
                .where(DepartmentMembership.user_id == self.user.id)
            ),
            2,
        )

    def test_invalid_persisted_policy_fails_closed(self):
        self.access()
        b = self.boundary(
            permissions=["etl.view"], customers=[self.org.id], environments=["TEST"]
        )
        b.specification = {"permissions": ["unimplemented"]}
        self.db.commit()
        self.assertIsNone(resolve_access(self.db, self.user))

    def test_revocation_changes_existing_session_projection(self):
        self.access()
        a = resolve_access(self.db, self.user)
        b = self.boundary("DENY", permissions=["etl.view"], customers=[self.org.id])
        fresh = resolve_access(self.db, self.user)
        self.assertNotEqual(a.authorization_revision, fresh.authorization_revision)
        b.active = False
        b.revision += 1
        self.db.commit()
        self.assertNotEqual(
            fresh.authorization_revision,
            resolve_access(self.db, self.user).authorization_revision,
        )

    def test_delegation_is_not_inferred_from_access_role(self):
        self.grant(self.user, ["access.view", "access.manage_users"])
        from app.security.delegation import budget

        with self.assertRaises(HTTPException):
            budget(resolve_access(self.db, self.user))

    def test_delegation_budget_prevents_role_escalation(self):
        d = Department(name=uuid.uuid4().hex, service_provider_id=PROVIDER_ID)
        self.db.add(d)
        self.db.commit()
        self.boundary(
            "DELEGATE",
            permissions=["etl.view"],
            customers=[self.org.id],
            departments=[d.id],
        )
        p = resolve_access(self.db, self.user)
        good = self.role(["etl.view"])
        bad = self.role(["etl.resolve_identity"])
        check_role(self.db, good, p)
        with self.assertRaises(HTTPException):
            check_role(self.db, bad, p)

    def test_scope_revision_explains_restrictions(self):
        self.access()
        self.boundary(
            permissions=["etl.view"], customers=[self.org.id], environments=["TEST"]
        )
        doc = effective_document(resolve_access(self.db, self.user))
        self.assertEqual(doc["access_boundaries"][0]["kind"], "LIMIT")
        self.assertTrue(doc["inherited_and_direct"])
        self.assertFalse(doc["all_customers_authorized"])

    def test_inventory_query_count_is_not_per_row(self):
        self.access()
        self.boundary(
            permissions=["resources.view"],
            customers=[self.org.id],
            resources=[self.resource.id],
        )
        calls = []
        with self.principal() as (p, db):

            def count(*args):
                calls.append(1)

            event.listen(db.bind, "before_cursor_execute", count)
            try:
                db.scalars(select(MonitoringResource).limit(200)).all()
            finally:
                event.remove(db.bind, "before_cursor_execute", count)
        self.assertEqual(len(calls), 1)

    def test_large_customer_selection_keeps_restriction_sql_bounded(self):
        from app.security.resource_scope import predicates

        self.access()
        self.boundary(
            permissions=["resources.view"],
            customers=[self.org.id],
            resources=[self.resource.id],
        )
        p = resolve_access(self.db, self.user)
        customers = {self.org.id, *(uuid.uuid4() for _ in range(1000))}
        p = replace(
            p,
            roles={c: "viewer" for c in customers},
            customer_permissions={c: frozenset(["resources.view"]) for c in customers},
        )
        a = selected_customers.set(frozenset(customers))
        b = request_permissions.set(("resources.view",))
        try:
            compiled = predicates(p)[2]("MonitoringResource").compile()
            # Customer IDs belong in one expanding bind, not 1,000 repeated ORs.
            self.assertLess(len(str(compiled)), 2000)
            self.assertLessEqual(len(compiled.params), 4)
        finally:
            selected_customers.reset(a)
            request_permissions.reset(b)

    def test_boundary_decision_history_cannot_be_rewritten_or_deleted(self):
        boundary = self.boundary(
            "DENY", permissions=["etl.view"], customers=[self.org.id]
        )
        decision = AccessBoundaryDecision(
            boundary_id=boundary.id,
            actor_id=self.user.id,
            request_key=uuid.uuid4().hex,
            request_hash="0" * 64,
            reason="Preserved authorization evidence",
            revision=1,
            evidence={"after": {"active": True}},
        )
        self.db.add(decision)
        self.db.commit()
        decision.reason = "Rewritten"
        with self.assertRaises(DBAPIError):
            self.db.commit()
        self.db.rollback()
        self.db.delete(decision)
        with self.assertRaises(DBAPIError):
            self.db.commit()
        self.db.rollback()
        self.assertEqual(decision.reason, "Preserved authorization evidence")

    def test_separate_delegations_cannot_form_permission_customer_cross_product(self):
        from app.security.delegation import covers

        deps = []
        for _ in range(2):
            d = Department(name=uuid.uuid4().hex, service_provider_id=PROVIDER_ID)
            self.db.add(d)
            self.db.flush()
            deps.append(d.id)
        self.db.commit()
        self.boundary(
            "DELEGATE",
            permissions=["etl.view"],
            customers=[self.org.id],
            departments=[deps[0]],
        )
        self.boundary(
            "DELEGATE",
            permissions=["etl.resolve_identity"],
            customers=[],
            departments=[deps[1]],
        )
        p = resolve_access(self.db, self.user)
        self.assertFalse(
            covers(
                p,
                departments=[deps[0]],
                customers=[self.org.id],
                permissions=["etl.resolve_identity"],
            )
        )
        self.assertTrue(
            covers(
                p,
                departments=[deps[0]],
                customers=[self.org.id],
                permissions=["etl.view"],
            )
        )

    def test_worker_replay_rechecks_resource_restrictions(self):
        from app.security.resource_scope import source_authorized

        self.grant(self.user, ["etl.replay"])
        p = resolve_access(self.db, self.user)
        self.assertTrue(source_authorized(self.db, p, self.source, "etl.replay"))
        self.boundary(
            "DENY",
            permissions=["etl.replay"],
            customers=[self.org.id],
            resources=[self.resource.id],
        )
        p = resolve_access(self.db, self.user)
        self.assertTrue(p.allows("etl.replay", self.org.id))
        self.assertFalse(source_authorized(self.db, p, self.source, "etl.replay"))

    def test_multiple_limits_intersect_instead_of_bypassing_a_restriction(self):
        self.access()
        self.boundary(
            permissions=["resources.view"],
            customers=[self.org.id],
            environments=["PROD"],
        )
        self.boundary(
            permissions=["resources.view"],
            customers=[self.org.id],
            resources=[self.resource.id],
        )
        with self.principal() as (p, db):
            self.assertEqual(db.scalars(select(MonitoringResource.id)).all(), [])
