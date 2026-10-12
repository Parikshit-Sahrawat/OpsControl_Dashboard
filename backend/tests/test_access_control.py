"""Default-deny policy and complete HTTP authorization inventory regressions."""

import unittest
from uuid import uuid4
from pydantic import ValidationError
from app.security.scope import Principal
from app.security.access_control import route_permissions, request_permissions
from app.security.permission_catalog import ROLE_SPECS, PERMISSIONS
from app.api.access import EmployeeCreate, DepartmentCreate
from scripts.export_api_inventory import inventory


class AccessPolicyTests(unittest.TestCase):
    def test_default_deny_and_customer_action_scope(self):
        a, b = uuid4(), uuid4()
        p = Principal(
            uuid4(),
            "employee",
            False,
            {a: "viewer", b: "viewer"},
            permissions=frozenset({"resources.view", "incidents.view"}),
            customer_permissions={
                a: frozenset({"resources.view"}),
                b: frozenset({"incidents.view"}),
            },
        )
        self.assertTrue(p.allows("resources.view", a))
        self.assertFalse(p.allows("resources.view", b))
        self.assertFalse(p.allows("access.view"))
        context = request_permissions.set(("resources.view",))
        try:
            self.assertEqual(p.organizations, (a,))
        finally:
            request_permissions.reset(context)

    def test_unknown_routes_are_denied(self):
        self.assertEqual(
            route_permissions("POST", "/api/v1/future-resource"), ("unsupported",)
        )

    def test_every_existing_http_route_has_an_explicit_policy(self):
        for row in inventory():
            if (
                not row["path"].startswith("/api/")
                or row["identity_hint"] != "human-bearer/route-policy"
            ):
                continue
            for method in row["methods"]:
                with self.subTest(path=row["path"], method=method):
                    self.assertNotIn(
                        "unsupported", route_permissions(method, row["path"])
                    )

    def test_access_administrator_defaults_have_no_operational_permission(self):
        # Catalog is also frozen in the migration; runtime defaults must agree.
        keys = ROLE_SPECS["access-administrator"][1]
        self.assertTrue("access.view" in keys)
        self.assertTrue(all(k.startswith("access.") or k == "audit.view" for k in keys))
        self.assertTrue(set(keys) <= PERMISSIONS.keys())

    def test_mass_assignment_and_weak_password_rejected(self):
        for extra in ({"id": str(uuid4())}, {"service_provider_id": str(uuid4())}):
            with self.assertRaises(ValidationError):
                EmployeeCreate(
                    username="test",
                    full_name="Employee",
                    password="Long synthetic password",
                    **extra
                )
        with self.assertRaises(ValidationError):
            EmployeeCreate(username="test", full_name="Employee", password="short")
        with self.assertRaises(ValidationError):
            DepartmentCreate(name="Department", organization_id=str(uuid4()))


if __name__ == "__main__":
    unittest.main()
