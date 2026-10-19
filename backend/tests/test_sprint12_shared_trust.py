"""Disposable Sprint 12 scope fixture; does not certify cross-customer sharing."""

import os
import unittest
import uuid
from contextlib import contextmanager

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from starlette.requests import Request

import app.main  # noqa: F401 - register scoped ORM models
from app.db.session import SessionLocal
from app.models import Application, Organization, VM
from app.security.access_control import request_permissions, resolve_access
from app.security.access_models import (
    CustomerAccessGrant,
    Role,
    RolePermission,
    UserRoleAssignment,
)
from app.security.boundaries import choose, selected_customers
from app.security.models import User
from app.security.permission_catalog import PROVIDER_ID
from app.security.scope import configure_request_session, current_principal
from app.telemetry.ingestion import validate_method_identity
from app.unified.api import details, inventory, resource
from app.unified.models import MonitoringResource, ResourceDependency


@unittest.skipUnless(
    os.getenv("OPSCONTROL_V16_ACCEPTANCE") == "1",
    "Owned disposable PostgreSQL required",
)
class SharedTrustFixture(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        self.addCleanup(self.db.close)
        token = uuid.uuid4().hex[:12]
        self.a = Organization(name="S12 A " + token, code="S12A-" + token, active=True)
        self.b = Organization(name="S12 B " + token, code="S12B-" + token, active=True)
        self.users = [
            User(
                username="s12-" + uuid.uuid4().hex,
                full_name="Controlled scope actor",
                password_hash="controlled-fixture-no-login",
                active=True,
                service_provider_id=PROVIDER_ID,
            )
            for _ in range(3)
        ]
        self.db.add_all([self.a, self.b, *self.users])
        self.db.flush()
        self.vma = VM(
            organization_id=self.a.id, hostname="a-" + token, environment="TEST"
        )
        self.vmb = VM(
            organization_id=self.b.id, hostname="b-" + token, environment="TEST"
        )
        self.db.add_all([self.vma, self.vmb])
        self.db.flush()
        self.db.flush()  # Persist canonical bindings queued by the compatibility hook.
        self.appa = Application(vm_id=self.vma.id, name="Application A")
        self.appb = Application(vm_id=self.vmb.id, name="Application B")
        # Legacy VM onboarding creates its one canonical resource binding.
        self.ra = self.db.scalar(
            select(MonitoringResource).where(MonitoringResource.vm_id == self.vma.id)
        )
        self.rb = self.db.scalar(
            select(MonitoringResource).where(MonitoringResource.vm_id == self.vmb.id)
        )
        self.assertIsNotNone(self.ra)
        self.assertIsNotNone(self.rb)
        self.db.add_all([self.appa, self.appb])
        self.db.flush()
        role = Role(
            service_provider_id=PROVIDER_ID,
            code="s12-" + token,
            name="S12 view " + token,
        )
        self.db.add(role)
        self.db.flush()
        self.db.add(RolePermission(role_id=role.id, permission_key="resources.view"))
        for user in self.users[:2]:
            self.db.add(
                UserRoleAssignment(
                    user_id=user.id, role_id=role.id, service_provider_id=PROVIDER_ID
                )
            )
        self.db.flush()  # The grant FK requires an existing paired assignment.
        for user, customers in (
            (self.users[0], (self.a, self.b)),
            (self.users[1], (self.a,)),
        ):
            for customer in customers:
                self.db.add(
                    CustomerAccessGrant(
                        user_id=user.id,
                        role_id=role.id,
                        organization_id=customer.id,
                        service_provider_id=PROVIDER_ID,
                    )
                )
        self.db.commit()

    @contextmanager
    def scoped(self, actor, selected):
        principal = resolve_access(self.db, actor)
        a = current_principal.set(principal)
        b = request_permissions.set(("resources.view",))
        c = selected_customers.set(frozenset(selected))
        try:
            with SessionLocal() as db:
                configure_request_session(db)
                yield principal, db
        finally:
            current_principal.reset(a)
            request_permissions.reset(b)
            selected_customers.reset(c)

    def test_two_customer_and_one_customer_scope_with_forged_selection(self):
        with self.scoped(self.users[0], (self.a.id, self.b.id)) as (principal, db):
            self.assertEqual(
                set(db.scalars(select(MonitoringResource.id))), {self.ra.id, self.rb.id}
            )
            self.assertTrue(principal.allows("resources.view", self.b.id))
            self.assertFalse(principal.allows("resources.update", self.b.id))
        with self.scoped(self.users[1], (self.a.id,)) as (principal, db):
            self.assertEqual(
                db.scalars(select(MonitoringResource.id)).all(), [self.ra.id]
            )
            self.assertEqual(db.scalars(select(Application.id)).all(), [self.appa.id])
            listed = inventory(
                domain="VM",
                organization_id=[self.a.id, self.b.id],
                environment=None,
                search="",
                active=None,
                limit=50,
                offset=0,
                db=db,
            )
            self.assertEqual([row["id"] for row in listed["items"]], [self.ra.id])
            self.assertIsNone(
                db.scalar(
                    select(MonitoringResource.id).where(
                        MonitoringResource.id == self.rb.id
                    )
                )
            )
            with self.assertRaises(HTTPException) as denied:
                resource(db, self.rb.id)
            self.assertEqual(denied.exception.status_code, 404)
            with self.assertRaises(HTTPException) as denied:
                details(self.rb.id, db=db)
            self.assertEqual(denied.exception.status_code, 404)
            forged = Request(
                {
                    "type": "http",
                    "headers": [],
                    "query_string": ("organization_id=" + str(self.b.id)).encode(),
                }
            )
            self.assertEqual(choose(principal, forged), frozenset())
        with self.scoped(self.users[2], (self.a.id, self.b.id)) as (_, db):
            self.assertEqual(db.scalars(select(MonitoringResource.id)).all(), [])

    def test_cross_customer_edge_and_second_vm_binding_fail_closed(self):
        # A B-owned edge cannot point at A's canonical resource.
        self.db.add(
            ResourceDependency(
                organization_id=self.b.id,
                resource_id=self.rb.id,
                depends_on_id=self.ra.id,
                relationship_type="DEPENDS_ON",
            )
        )
        with self.assertRaisesRegex(DBAPIError, "fk_dependency_parent_scope"):
            self.db.flush()
        self.db.rollback()
        # The same VM identity cannot be registered as a second resource for B.
        self.db.add(
            MonitoringResource(
                organization_id=self.b.id,
                domain="VM",
                name="Shared host alias",
                environment="TEST",
                vm_id=self.vma.id,
            )
        )
        with self.assertRaisesRegex(DBAPIError, "resource VM scope mismatch"):
            self.db.flush()
        self.db.rollback()

    def test_unapproved_method_identity_cannot_relabel_source(self):
        method = str(uuid.uuid4())
        allowed = {method: {"metrics"}}
        self.assertEqual(
            validate_method_identity(
                {"opscontrol.method.id": method}, allowed, "metrics"
            ),
            method,
        )
        for attrs in (
            {"opscontrol.method.id": str(uuid.uuid4())},
            {"opscontrol.method.id": method, "opscontrol_method_id": str(uuid.uuid4())},
        ):
            with self.assertRaises(HTTPException) as denied:
                validate_method_identity(attrs, allowed, "metrics")
            self.assertEqual(denied.exception.status_code, 422)
