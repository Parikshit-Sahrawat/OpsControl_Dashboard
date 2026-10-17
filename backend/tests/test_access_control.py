"""Default-deny policy and complete HTTP authorization inventory regressions."""

import unittest
from unittest.mock import Mock, patch
from fastapi import HTTPException
from starlette.requests import Request
from uuid import uuid4
from pydantic import ValidationError
from app.security.scope import Principal
from app.security.access_control import route_permissions, request_permissions
from app.security.permission_catalog import ROLE_SPECS, PERMISSIONS
from app.api.access import EmployeeCreate, DepartmentCreate
from scripts.export_api_inventory import inventory


class AccessPolicyTests(unittest.TestCase):
    def test_transaction_denial_releases_session_and_authorization_lock(self):
        from app.db.session import get_db
        from app.security.scope import current_principal

        db = Mock(info={})
        request = Request(
            {"type": "http", "method": "POST", "path": "/api/v1/unified/resources"}
        )
        ctx = current_principal.set(Principal(uuid4(), "employee", False, {}))
        try:
            with patch("app.db.session.SessionLocal", return_value=db), patch(
                "app.security.boundaries.transaction_authority",
                side_effect=HTTPException(403, "Authorization changed"),
            ):
                with self.assertRaises(HTTPException):
                    next(get_db(request))
        finally:
            current_principal.reset(ctx)
        db.close.assert_called_once_with()

    def test_agent_transport_keeps_its_separate_handler_authentication(self):
        from app.db.session import get_db
        from app.security.scope import current_principal

        db = Mock(info={})
        ctx = current_principal.set(None)
        try:
            with patch("app.db.session.SessionLocal", return_value=db), patch(
                "app.security.boundaries.transaction_authority"
            ) as human_authority, patch("app.security.scope.configure_request_session"):
                dependency = get_db(
                    Request(
                        {
                            "type": "http",
                            "headers": [],
                            "method": "POST",
                            "path": "/api/v1/agent/pipeline-claim",
                        }
                    )
                )
                self.assertIs(next(dependency), db)
                dependency.close()
                human_authority.assert_not_called()
        finally:
            current_principal.reset(ctx)
        db.close.assert_called_once_with()

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
