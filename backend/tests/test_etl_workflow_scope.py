"""Real shared ORM hooks and HTTP on a task-owned migrated PostgreSQL database."""

import json
import os
import secrets
import unittest
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from uuid import uuid4
from urllib.request import Request, urlopen
from urllib.error import HTTPError

import app.main  # register actual scope/audit/ownership hooks
from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from app.db.session import SessionLocal
from app.models import Organization, VM, JobOrder, ETLWorkflow, ETLWorkflowDependency
from app.security.models import User, SecurityAuditEvent
from app.security.access_models import (
    Role,
    RolePermission,
    UserRoleAssignment,
    CustomerAccessGrant,
)
from app.security.passwords import hash_password
from app.security.scope import Principal, current_principal, configure_request_session
from app.security.access_control import request_permissions
from app.security.boundaries import selected_customers


@unittest.skipUnless(
    os.getenv("OPSCONTROL_ETL_SCOPE_ACCEPTANCE") == "1",
    "Owned migrated PostgreSQL required",
)
class WorkflowScopeTests(unittest.TestCase):
    def setUp(self):
        self.password = secrets.token_urlsafe(24)
        with SessionLocal() as db:
            a = Organization(name="Scope A " + uuid4().hex, code="A-" + uuid4().hex)
            b = Organization(name="Scope B " + uuid4().hex, code="B-" + uuid4().hex)
            user = User(
                username="scope-" + uuid4().hex,
                password_hash=hash_password(self.password),
                platform_admin=True,
            )
            db.add_all([a, b, user])
            db.commit()
            self.a, self.b, self.uid, self.username = a.id, b.id, user.id, user.username
            wa = ETLWorkflow(organization_id=self.a, name="wa", environment="PROD")
            wb = ETLWorkflow(organization_id=self.b, name="wb", environment="PROD")
            wc = ETLWorkflow(organization_id=self.a, name="wc", environment="PROD")
            db.add_all([wa, wb, wc])
            db.flush()
            jobs = [
                JobOrder(
                    organization_id=o,
                    workflow_id=w.id,
                    name="job-" + str(i),
                    environment="PROD",
                )
                for i, (o, w) in enumerate(
                    [(self.a, wa), (self.a, wa), (self.b, wb), (self.a, wc)]
                )
            ]
            db.add_all(jobs)
            db.commit()
            self.wa, self.wb, self.wc = wa.id, wb.id, wc.id
            self.j1, self.j2, self.jb, self.jc = [j.id for j in jobs]
        keys = frozenset({"etl.view", "etl.configure"})
        self.editor = Principal(
            self.uid,
            self.username,
            False,
            {},
            permissions=keys,
            customer_permissions={self.a: keys},
            customer_directory_ids=frozenset([self.a, self.b]),
        )
        # Principal.organizations uses roles as its directory for ordinary users.
        self.editor = replace(self.editor, roles={self.a: "org_admin"})
        self.admin = replace(self.editor, platform_admin=True)

    @contextmanager
    def scoped(self, principal=None, selection=None, keys=("etl.configure",)):
        tokens = [
            (current_principal, current_principal.set(principal or self.editor)),
            (request_permissions, request_permissions.set(keys)),
            (
                selected_customers,
                selected_customers.set(
                    frozenset([self.a]) if selection is None else frozenset(selection)
                ),
            ),
        ]
        try:
            with SessionLocal() as db:
                configure_request_session(db)
                yield db
        finally:
            for var, token in reversed(tokens):
                var.reset(token)

    def deny(self, obj, status=409, principal=None):
        with self.scoped(principal) as db:
            db.add(obj)
            with self.assertRaises(HTTPException) as result:
                db.commit()
            self.assertEqual(result.exception.status_code, status)
            db.rollback()

    def edge(self, successor=None, workflow=None):
        return ETLWorkflowDependency(
            workflow_id=workflow or self.wa,
            predecessor_job_id=self.j1,
            successor_job_id=successor or self.j2,
        )

    def test_authorized_workflow_and_dependency_commit_with_audit(self):
        with self.scoped(self.admin) as db:
            w = ETLWorkflow(
                organization_id=self.a, name="authorized", environment="PROD"
            )
            db.add(w)
            db.commit()
            wid = w.id
        with self.scoped() as db:
            edge = self.edge()
            db.add(edge)
            db.commit()
            eid = edge.id
        with SessionLocal() as db:
            self.assertIsNotNone(db.get(ETLWorkflow, wid))
            self.assertIsNotNone(db.get(ETLWorkflowDependency, eid))
            self.assertGreaterEqual(
                db.scalar(
                    select(func.count())
                    .select_from(SecurityAuditEvent)
                    .where(
                        SecurityAuditEvent.actor_id == self.uid,
                        SecurityAuditEvent.event_type == "CONFIG_MUTATION",
                    )
                ),
                2,
            )

    def test_viewer_cannot_write(self):
        viewer = replace(
            self.editor,
            permissions=frozenset({"etl.view"}),
            customer_permissions={self.a: frozenset({"etl.view"})},
        )
        self.deny(
            ETLWorkflow(organization_id=self.a, name="denied", environment="PROD"),
            403,
            viewer,
        )

    def test_selected_scope_limits_even_admin(self):
        self.deny(
            ETLWorkflow(organization_id=self.b, name="denied", environment="PROD"),
            403,
            self.admin,
        )

    def test_cross_customer_job_workflow_reference_rejected(self):
        self.deny(
            JobOrder(
                organization_id=self.a,
                workflow_id=self.wb,
                name="invalid",
                environment="PROD",
            )
        )

    def test_same_customer_wrong_workflow_dependency_rejected(self):
        self.deny(self.edge(self.jc))

    def test_cross_customer_dependency_rejected(self):
        self.deny(self.edge(self.jb))

    def test_missing_dependency_parent_rejected(self):
        self.deny(self.edge(workflow=uuid4()), 404)

    def test_dependency_self_edge_rejected(self):
        self.deny(self.edge(self.j1))

    def test_job_environment_must_match_parent(self):
        self.deny(
            JobOrder(
                organization_id=self.a,
                workflow_id=self.wa,
                name="invalid-env",
                environment="DEV",
            )
        )

    def test_existing_job_parent_is_immutable(self):
        with self.scoped() as db:
            db.get(JobOrder, self.j1).workflow_id = self.wc
            with self.assertRaises(HTTPException) as result:
                db.commit()
            self.assertEqual(result.exception.status_code, 403)
            db.rollback()
        with SessionLocal() as db:
            self.assertEqual(db.get(JobOrder, self.j1).workflow_id, self.wa)

    def test_dependency_endpoints_are_immutable(self):
        with self.scoped() as db:
            edge = self.edge()
            db.add(edge)
            db.commit()
            eid = edge.id
        with self.scoped() as db:
            db.get(ETLWorkflowDependency, eid).successor_job_id = self.jc
            with self.assertRaises(HTTPException) as result:
                db.commit()
            self.assertEqual(result.exception.status_code, 403)
            db.rollback()
        with SessionLocal() as db:
            self.assertEqual(
                db.get(ETLWorkflowDependency, eid).successor_job_id, self.j2
            )

    def test_workflow_owner_is_immutable(self):
        with self.scoped(self.admin, selection=[self.a, self.b]) as db:
            db.get(ETLWorkflow, self.wa).organization_id = self.b
            with self.assertRaises(HTTPException) as result:
                db.commit()
            self.assertEqual(result.exception.status_code, 403)
            db.rollback()

    def test_workflow_environment_cannot_invalidate_existing_jobs(self):
        with self.scoped() as db:
            db.get(ETLWorkflow, self.wa).environment = "DEV"
            with self.assertRaises(HTTPException) as result:
                db.commit()
            self.assertEqual(result.exception.status_code, 409)
            db.rollback()

    def test_read_scope_and_empty_selection(self):
        with SessionLocal() as db:
            edge = self.edge()
            db.add(edge)
            db.commit()
            eid = edge.id
        with self.scoped(keys=("etl.view",)) as db:
            self.assertIsNone(db.get(ETLWorkflow, self.wb))
            self.assertIsNotNone(db.get(ETLWorkflow, self.wa))
            self.assertIsNotNone(db.get(ETLWorkflowDependency, eid))
        with self.scoped(selection=[], keys=("etl.view",)) as db:
            self.assertEqual(db.scalars(select(ETLWorkflow)).all(), [])
            self.assertEqual(db.scalars(select(ETLWorkflowDependency)).all(), [])

    def test_resource_restricted_unknown_workflow_fails_closed(self):
        boundary = {
            "kind": "LIMIT",
            "specification": {
                "permissions": ["etl.configure", "etl.view"],
                "customers": [str(self.a)],
                "environments": ["PROD"],
                "resources": [],
            },
        }
        principal = replace(self.editor, boundaries=(boundary,))
        self.deny(
            ETLWorkflow(organization_id=self.a, name="unbound", environment="PROD"),
            403,
            principal,
        )
        # Existing JobOrder hooks create canonical ETL resources. All PROD
        # children are visible under this environment limit; empty is unknown.
        with SessionLocal() as db:
            empty = ETLWorkflow(
                organization_id=self.a, name="empty-" + uuid4().hex, environment="PROD"
            )
            db.add(empty)
            db.commit()
            empty_id = empty.id
        with self.scoped(principal, keys=("etl.view",)) as db:
            self.assertIsNotNone(db.get(ETLWorkflow, self.wa))
            self.assertIsNone(db.get(ETLWorkflow, empty_id))
        denied = replace(
            principal,
            boundaries=(
                {
                    "kind": "LIMIT",
                    "specification": {
                        **boundary["specification"],
                        "environments": ["DEV"],
                    },
                },
            ),
        )
        with self.scoped(denied, keys=("etl.view",)) as db:
            self.assertIsNone(db.get(ETLWorkflow, self.wa))

    def test_workflow_requires_visibility_of_every_child_resource(self):
        from app.unified.models import MonitoringResource

        with SessionLocal() as db:
            rid = db.scalar(
                select(MonitoringResource.id).where(
                    MonitoringResource.job_order_id == self.j1
                )
            )
            self.assertIsNotNone(rid)
            edge = self.edge()
            db.add(edge)
            db.commit()
            eid = edge.id
        boundary = {
            "kind": "LIMIT",
            "specification": {
                "permissions": ["etl.view", "etl.configure"],
                "customers": [str(self.a)],
                "environments": [],
                "resources": [str(rid)],
            },
        }
        limited = replace(self.editor, boundaries=(boundary,))
        with self.scoped(limited, keys=("etl.view",)) as db:
            self.assertIsNotNone(db.get(JobOrder, self.j1))
            self.assertIsNone(db.get(JobOrder, self.j2))
            self.assertIsNone(db.get(ETLWorkflow, self.wa))
            self.assertIsNone(db.get(ETLWorkflowDependency, eid))

    def test_failed_reference_preserves_existing_resources_and_no_success_audit(self):
        with SessionLocal() as db:
            before = db.scalar(
                select(func.count())
                .select_from(SecurityAuditEvent)
                .where(SecurityAuditEvent.actor_id == self.uid)
            )
        self.deny(self.edge(self.jb))
        self.deny(
            VM(
                organization_id=self.b,
                hostname="cross.example.test",
                environment="PROD",
            ),
            403,
        )
        with SessionLocal() as db:
            self.assertEqual(db.get(JobOrder, self.jb).organization_id, self.b)
            self.assertEqual(
                db.scalar(
                    select(func.count())
                    .select_from(SecurityAuditEvent)
                    .where(SecurityAuditEvent.actor_id == self.uid)
                ),
                before,
            )

    def test_invalid_organization_cannot_persist(self):
        missing = uuid4()
        p = replace(self.admin, customer_directory_ids=frozenset([missing]))
        with self.scoped(p, selection=[missing]) as db:
            db.add(
                ETLWorkflow(
                    organization_id=missing, name="missing-parent", environment="PROD"
                )
            )
            with self.assertRaises(IntegrityError):
                db.commit()
            db.rollback()

    def test_authenticated_http_workflow_job_dependency_updates_and_negatives(self):
        base = os.environ["ETL_SCOPE_API_URL"]
        checks = []

        def req(path, method="GET", body=None, token=None, scope=None, expected=200):
            headers = {"Content-Type": "application/json"}
            if token:
                headers["Authorization"] = "Bearer " + token
            if scope is not None:
                headers["X-OpsControl-Customers"] = ",".join(map(str, scope))
            try:
                with urlopen(
                    Request(
                        base + "/api/v1/" + path,
                        data=json.dumps(body).encode() if body is not None else None,
                        headers=headers,
                        method=method,
                    ),
                    timeout=15,
                ) as r:
                    status = r.status
                    data = json.load(r)
            except HTTPError as e:
                status = e.code
                data = json.load(e)
            checks.append(
                {"method": method, "path": path, "expected": expected, "actual": status}
            )
            self.assertEqual(status, expected, str(checks[-1]))
            return data

        def login(username):
            return req(
                "auth/login", "POST", {"username": username, "password": self.password}
            )["access_token"]

        admin = login(self.username)
        with SessionLocal() as db:
            viewer = User(
                username="viewer-" + uuid4().hex,
                password_hash=hash_password(self.password),
                platform_admin=False,
            )
            editor = User(
                username="editor-" + uuid4().hex,
                password_hash=hash_password(self.password),
                platform_admin=False,
            )
            db.add_all([viewer, editor])
            db.flush()
            for u, keys in [
                (viewer, ["etl.view"]),
                (editor, ["etl.view", "etl.configure"]),
            ]:
                role = Role(
                    code="role-" + uuid4().hex, name="ETL scope test " + uuid4().hex
                )
                db.add(role)
                db.flush()
                db.add_all(
                    [RolePermission(role_id=role.id, permission_key=k) for k in keys]
                )
                db.add(UserRoleAssignment(user_id=u.id, role_id=role.id))
                db.flush()
                db.add(
                    CustomerAccessGrant(
                        user_id=u.id, role_id=role.id, organization_id=self.a
                    )
                )
            db.commit()
            viewer_name, editor_name = viewer.username, editor.username
        viewer_token = login(viewer_name)
        editor_token = login(editor_name)
        w = req(
            "etl/workflows",
            "POST",
            {
                "organization_id": str(self.a),
                "name": "http-workflow",
                "environment": "PROD",
            },
            admin,
            [self.a],
            201,
        )
        wid = w["id"]
        req(
            "etl/workflows/" + wid,
            "PATCH",
            {"name": "http-updated"},
            editor_token,
            [self.a],
        )
        jobs = [
            req(
                "etl/workflows/" + wid + "/jobs",
                "POST",
                {
                    "name": "http-" + str(i),
                    "hostname": "host-" + uuid4().hex,
                    "expected_duration_seconds": 30,
                },
                editor_token,
                [self.a],
                201,
            )["id"]
            for i in range(2)
        ]
        req(
            "etl/workflows/" + wid + "/jobs/" + jobs[0],
            "PATCH",
            {"expected_duration_seconds": 60},
            editor_token,
            [self.a],
        )
        edge = {"predecessor_job_id": jobs[0], "successor_job_id": jobs[1]}
        req(
            "etl/workflows/" + wid + "/dependencies",
            "POST",
            edge,
            editor_token,
            [self.a],
            201,
        )
        req(
            "etl/workflows/" + wid + "/dependencies", token=viewer_token, scope=[self.a]
        )
        req("etl/workflows/" + wid + "/monitoring", token=viewer_token, scope=[self.a])
        req(
            "etl/workflows/" + wid,
            "PATCH",
            {"name": "viewer-forged"},
            viewer_token,
            [self.a],
            403,
        )
        req(
            "etl/workflows",
            "POST",
            {"organization_id": str(self.b), "name": "foreign"},
            editor_token,
            [self.a],
            403,
        )
        req(
            "etl/workflows/" + str(self.wb),
            token=editor_token,
            scope=[self.a],
            expected=404,
        )
        req(
            "etl/workflows/" + wid + "/dependencies",
            "POST",
            {"predecessor_job_id": jobs[0], "successor_job_id": str(self.jb)},
            editor_token,
            [self.a],
            409,
        )
        req(
            "etl/workflows/" + wid + "/dependencies",
            "POST",
            {"predecessor_job_id": jobs[0], "successor_job_id": str(self.jc)},
            editor_token,
            [self.a],
            409,
        )
        req(
            "etl/workflows/" + wid + "/jobs/" + str(self.jb),
            "PATCH",
            {"active": False},
            editor_token,
            [self.a],
            404,
        )
        req(
            "etl/workflows/" + wid + "/dependencies",
            "POST",
            {"predecessor_job_id": jobs[1], "successor_job_id": jobs[0]},
            editor_token,
            [self.a],
            409,
        )
        req("etl/workflows/" + wid, "PATCH", {"active": False}, editor_token, [self.a])
        req(
            "etl/workflows/" + wid + "/jobs/" + jobs[0],
            "PATCH",
            {"active": True},
            editor_token,
            [self.a],
            409,
        )
        req("etl/workflows/" + wid, expected=401)
        with SessionLocal() as db:
            self.assertEqual(
                db.get(ETLWorkflow, __import__("uuid").UUID(wid)).name, "http-updated"
            )
            self.assertEqual(
                db.get(
                    JobOrder, __import__("uuid").UUID(jobs[0])
                ).expected_runtime_seconds,
                60,
            )
        Path(os.environ["ETL_SCOPE_EVIDENCE_DIR"], "http-results.json").write_text(
            json.dumps(
                {"status": "PASS", "checks": checks, "provider_certification": False},
                indent=2,
            )
            + "\n"
        )
