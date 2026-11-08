"""Existing staged native binding contract on owned PostgreSQL and real HTTP.

No production handler, provider verification or new binding authority is added.
"""

import hashlib
import json
import os
from pathlib import Path
import unittest
from datetime import datetime, timezone
from uuid import UUID, uuid4
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from sqlalchemy import select, func, text
from app.db.session import SessionLocal
from app.models import JobOrderHistory, ExecutionStatus, ExecutionType
from app.unified.models import MonitoringResource
from app.data_pipelines.models import (
    PipelineJob,
    PipelineOperation,
    PipelineSource,
    PipelineAssociation,
    PipelineEvidence,
    PipelineIntegration,
)
from app.security.models import User, SecurityAuditEvent
from app.security.access_models import (
    Role,
    RolePermission,
    UserRoleAssignment,
    CustomerAccessGrant,
)
from app.security.passwords import hash_password
from tests import test_etl_workflow_scope as scope_tests


@unittest.skipUnless(
    os.getenv("OPSCONTROL_ETL_SCOPE_ACCEPTANCE") == "1",
    "Owned migrated PostgreSQL/API required",
)
class NativeBindingContractTests(unittest.TestCase):
    def setUp(self):
        self.assertEqual(os.getenv("ENVIRONMENT"), "test")
        self.assertTrue(os.getenv("ETL_SCOPE_CONTAINER", "").startswith("oc-etl002-"))
        self.assertTrue(
            os.getenv("ETL_SCOPE_API_URL", "").startswith("http://127.0.0.1:")
        )
        scope_tests.WorkflowScopeTests.setUp(self)

    def test_existing_staged_bridge_authorization_and_generation(self):
        checks = []

        def req(
            path, method="GET", payload=None, token=None, status=200, customer=None
        ):
            headers = {
                "Content-Type": "application/json",
                "X-OpsControl-Customers": str(customer or self.a),
            }
            if token:
                headers["Authorization"] = "Bearer " + token
            try:
                with urlopen(
                    Request(
                        os.environ["ETL_SCOPE_API_URL"] + "/api/v1/" + path,
                        method=method,
                        headers=headers,
                        data=(
                            json.dumps(payload).encode()
                            if payload is not None
                            else None
                        ),
                    ),
                    timeout=15,
                ) as response:
                    actual = response.status
                    data = json.load(response) if actual != 204 else None
            except HTTPError as error:
                actual = error.code
                data = json.load(error)
            checks.append(
                {"method": method, "path": path, "expected": status, "actual": actual}
            )
            if actual != status:
                Path(
                    os.environ["ETL_SCOPE_EVIDENCE_DIR"],
                    "native-binding-contract-failure.json",
                ).write_text(
                    json.dumps(
                        {
                            **checks[-1],
                            "detail": (
                                data.get("detail") if isinstance(data, dict) else None
                            ),
                        },
                        indent=2,
                    )
                    + "\n"
                )
            self.assertEqual(actual, status, checks[-1])
            return data

        def mutation(payload=None):
            return {"idempotency_key": uuid4().hex, **(payload or {})}

        def login(name):
            return req(
                "auth/login", "POST", {"username": name, "password": self.password}
            )["access_token"]

        native = "synthetic-native-" + uuid4().hex
        with SessionLocal() as db:
            resource = db.scalar(
                select(MonitoringResource).where(
                    MonitoringResource.job_order_id == self.j1
                )
            )
            foreign = db.scalar(
                select(MonitoringResource).where(
                    MonitoringResource.job_order_id == self.jb
                )
            )
            rid = str(resource.id)
            foreign_id = str(foreign.id)
            resource.configuration = {**resource.configuration, "native_job_id": native}
            history = JobOrderHistory(
                job_order_id=self.j1,
                execution_type=ExecutionType.SCHEDULED,
                status=ExecutionStatus.FAILED,
                provider_execution_id="synthetic-historical-execution",
                detected_at=datetime.now(timezone.utc),
            )
            reviewer = User(
                username="binding-reviewer-" + uuid4().hex,
                password_hash=hash_password(self.password),
                platform_admin=True,
            )
            editor = User(
                username="binding-editor-" + uuid4().hex,
                password_hash=hash_password(self.password),
                platform_admin=False,
            )
            role = Role(
                code="binding-role-" + uuid4().hex,
                name="Binding configuration " + uuid4().hex,
            )
            db.add_all([history, reviewer, editor, role])
            db.flush()
            db.add_all(
                [
                    RolePermission(role_id=role.id, permission_key=k)
                    for k in ["etl.view", "etl.configure"]
                ]
            )
            db.add(UserRoleAssignment(user_id=editor.id, role_id=role.id))
            db.flush()
            db.add(
                CustomerAccessGrant(
                    user_id=editor.id, role_id=role.id, organization_id=self.a
                )
            )
            db.commit()
            history_id = history.id
            reviewer_name = reviewer.username
            editor_name = editor.username
            role_id = str(role.id)
            original_history = db.scalar(
                text(
                    "SELECT to_jsonb(h)::text FROM job_order_histories h WHERE id=:id"
                ),
                {"id": history_id},
            )
        admin = login(self.username)
        reviewer_token = login(reviewer_name)
        editor_token = login(editor_name)
        integration = req(
            "data-pipelines/integrations",
            "POST",
            mutation(
                {
                    "organization_id": str(self.a),
                    "name": "Native binding contract fixture",
                    "platform": "PENTAHO",
                    "environment": "PROD",
                }
            ),
            admin,
            201,
        )
        prefix = "data-pipelines/integrations/" + integration["id"]
        body = mutation(
            {
                "native_id": native,
                "name": "Display name is not native identity",
                "resource_id": rid,
            }
        )
        staged = req(prefix + "/jobs", "POST", body, admin, 201)
        self.assertEqual(
            req(prefix + "/jobs", "POST", body, admin, 201)["id"], staged["id"]
        )
        self.assertEqual(staged["resource_id"], rid)
        self.assertTrue(staged["quarantined"])
        self.assertFalse(staged["selected"])
        self.assertEqual(staged["origin"], "LEGACY_PENDING")
        rejected_key = uuid4().hex
        req(
            prefix + "/jobs",
            "POST",
            {**body, "idempotency_key": rejected_key},
            admin,
            409,
        )
        req(
            prefix + "/jobs",
            "POST",
            mutation(
                {
                    "native_id": "different-native",
                    "name": "Conflicting identity",
                    "resource_id": rid,
                }
            ),
            admin,
            409,
        )
        req(
            prefix + "/jobs",
            "POST",
            mutation(
                {
                    "native_id": native + "-foreign",
                    "name": "Foreign",
                    "resource_id": foreign_id,
                }
            ),
            admin,
            404,
        )
        with SessionLocal() as db:
            self.assertEqual(
                db.scalar(
                    select(func.count())
                    .select_from(PipelineJob)
                    .where(PipelineJob.integration_id == UUID(integration["id"]))
                ),
                1,
            )
            self.assertIsNone(
                db.scalar(
                    select(PipelineOperation.id).where(
                        PipelineOperation.idempotency_key == rejected_key
                    )
                )
            )
            self.assertEqual(
                db.get(MonitoringResource, UUID(rid)).job_order_id, self.j1
            )
        req(
            "data-pipelines/jobs/" + staged["id"] + "/selection",
            "POST",
            mutation(
                {
                    "selected": True,
                    "confirmed": True,
                    "expected_revision": staged["revision"],
                }
            ),
            admin,
            409,
        )
        req(prefix + "/activate", "POST", mutation({"confirmed": True}), admin, 409)
        verification = req("unified/resources/" + rid + "/verification", token=admin)
        self.assertFalse(verification["ready"])
        req(
            "unified/resources/" + rid + "/activate",
            "POST",
            {"approve": True},
            admin,
            409,
        )
        qa = req(
            "etl/workflows",
            "POST",
            {
                "organization_id": str(self.a),
                "name": "QA binding fixture",
                "environment": "QA",
            },
            admin,
            201,
        )
        qa_job = req(
            "etl/workflows/" + qa["id"] + "/jobs",
            "POST",
            {
                "name": "QA Job",
                "hostname": "qa.synthetic.invalid",
                "expected_duration_seconds": 60,
            },
            admin,
            201,
        )
        with SessionLocal() as db:
            qa_resource = db.scalar(
                select(MonitoringResource.id).where(
                    MonitoringResource.job_order_id == UUID(qa_job["id"])
                )
            )
        req(
            prefix + "/jobs",
            "POST",
            mutation(
                {
                    "native_id": "qa-native",
                    "name": "Wrong environment",
                    "resource_id": str(qa_resource),
                }
            ),
            admin,
            422,
        )
        connection = req(
            prefix + "/connections",
            "POST",
            mutation({"configuration": {"url": "https://pentaho.synthetic.invalid"}}),
            admin,
            201,
        )
        capability = req(
            prefix + "/capabilities",
            "POST",
            mutation(
                {
                    "platform_version": "10.2-candidate",
                    "edition": "Synthetic unverified",
                    "deployment_type": "Self-hosted",
                    "supported_methods": ["PLATFORM_API"],
                }
            ),
            admin,
            201,
        )
        method = req(
            prefix + "/methods",
            "POST",
            mutation(
                {
                    "name": "Unverified read-only method",
                    "method_type": "PLATFORM_API",
                    "transport": "BACKEND",
                    "identity": {
                        "platform": "PENTAHO",
                        "endpoint": "https://pentaho.synthetic.invalid",
                        "account": "synthetic-account",
                        "physical_scope": "synthetic-authority",
                    },
                    "connection_id": connection["id"],
                    "capability_id": capability["id"],
                    "configuration": {},
                }
            ),
            admin,
            201,
        )
        association = req(
            prefix + "/associations",
            "POST",
            mutation(
                {"job_id": staged["id"], "method_id": method["id"], "confirmed": True}
            ),
            admin,
            201,
        )
        req(
            prefix + "/associations",
            "POST",
            mutation(
                {"job_id": staged["id"], "method_id": method["id"], "confirmed": True}
            ),
            admin,
            409,
        )
        validation = req(prefix + "/validate", "POST", {}, admin)
        self.assertFalse(validation["eligible"])
        self.assertTrue(
            any("RUNTIME_VERIFIED" in reason for reason in validation["blockers"])
        )
        req(prefix + "/activate", "POST", mutation({"confirmed": True}), admin, 409)
        # Existing reviewed reader handoff; NOT a new native-binding replacement.
        before_generation = association["generation"]
        with SessionLocal() as db:
            evidence = PipelineEvidence(
                organization_id=self.a,
                source_id=UUID(method["source_id"]),
                generation=UUID(before_generation),
                external_key="synthetic-retained",
                native_job_id=native,
                payload={"fixture": True},
                outcome="QUARANTINED_IDENTITY",
                observed_at=datetime.now(timezone.utc),
            )
            db.add(evidence)
            db.commit()
            evidence_id = evidence.id
        preview = req(
            "data-pipelines/sources/" + method["source_id"] + "/change-preview",
            "POST",
            mutation({"configuration": {"method_configuration": {}}}),
            admin,
        )
        req(
            "data-pipelines/operations/" + preview["id"] + "/approve",
            "POST",
            mutation({"confirmed": True}),
            admin,
            403,
        )
        req(
            "data-pipelines/operations/" + preview["id"] + "/approve",
            "POST",
            mutation({"confirmed": True}),
            reviewer_token,
        )
        req(
            "data-pipelines/operations/" + preview["id"] + "/apply",
            "POST",
            mutation({"confirmed": True}),
            admin,
        )
        with SessionLocal() as db:
            source = db.get(PipelineSource, UUID(method["source_id"]))
            link = db.get(PipelineAssociation, UUID(association["id"]))
            self.assertNotEqual(source.generation, link.generation)
            self.assertEqual(str(link.generation), before_generation)
            self.assertIsNone(source.last_received_at)
            self.assertFalse(source.continuity_validated)
            after_generation = str(source.generation)
        req(prefix + "/activate", "POST", mutation({"confirmed": True}), admin, 409)
        # Current source association removal is physical deletion; preserve and
        # report this limitation instead of claiming temporal binding history.
        req(
            "data-pipelines/associations/" + association["id"],
            "DELETE",
            mutation({"confirmed": True}),
            admin,
        )
        editor_job = req(
            prefix + "/jobs",
            "POST",
            mutation(
                {
                    "native_id": "editor-native-" + uuid4().hex,
                    "name": "Editor authorized draft",
                }
            ),
            editor_token,
            201,
        )
        role = next(
            row for row in req("access/roles", token=admin) if row["id"] == role_id
        )
        req(
            "access/roles/" + role_id,
            "PATCH",
            {
                "name": role["name"],
                "permissions": ["etl.view"],
                "expected_revision": role["authorization_revision"],
            },
            admin,
        )
        req(
            prefix + "/jobs",
            "POST",
            mutation({"native_id": "revoked-native", "name": "Must not persist"}),
            editor_token,
            403,
        )
        req(
            "data-pipelines/integrations/" + integration["id"],
            token=editor_token,
            customer=self.b,
            status=404,
        )
        req(
            prefix + "/jobs",
            "POST",
            mutation({"native_id": "unauthenticated", "name": "Denied"}),
            status=401,
        )
        monitoring = req("etl/workflows/" + str(self.wa) + "/monitoring", token=admin)
        self.assertEqual(monitoring["readiness"]["activation_status"], "BLOCKED")
        self.assertEqual(monitoring["readiness"]["provider_status"], "UNVERIFIED")
        with SessionLocal() as db:
            self.assertEqual(
                db.scalar(
                    text(
                        "SELECT to_jsonb(h)::text FROM job_order_histories h WHERE id=:id"
                    ),
                    {"id": history_id},
                ),
                original_history,
            )
            self.assertIsNotNone(db.get(PipelineEvidence, evidence_id))
            self.assertIsNotNone(db.get(PipelineJob, UUID(editor_job["id"])))
            self.assertIsNone(
                db.scalar(
                    select(PipelineJob.id).where(
                        PipelineJob.native_id == "revoked-native"
                    )
                )
            )
            self.assertIsNone(db.get(PipelineAssociation, UUID(association["id"])))
            self.assertEqual(
                db.get(PipelineJob, UUID(staged["id"])).resource_id, UUID(rid)
            )
            self.assertFalse(
                db.get(PipelineIntegration, UUID(integration["id"])).enabled
            )
            self.assertIsNotNone(
                db.scalar(
                    select(SecurityAuditEvent.id).where(
                        SecurityAuditEvent.target_id == association["id"],
                        SecurityAuditEvent.event_type == "PIPELINE_ASSOCIATION_REMOVE",
                    )
                )
            )
        Path(
            os.environ["ETL_SCOPE_EVIDENCE_DIR"], "native-binding-contract-results.json"
        ).write_text(
            json.dumps(
                {
                    "status": "PASS",
                    "scope": "Existing staged/legacy bridge and reviewed source handoff only; no new native-binding activation authority",
                    "checks": checks,
                    "structural_chain": {
                        "workflow_id": str(self.wa),
                        "job_order_id": str(self.j1),
                        "resource_id": rid,
                        "pipeline_job_id": staged["id"],
                        "method_id": method["id"],
                        "source_id": method["source_id"],
                    },
                    "before_generation": before_generation,
                    "after_generation": after_generation,
                    "historical_receipt_sha256": hashlib.sha256(
                        original_history.encode()
                    ).hexdigest(),
                    "historical_receipt_unchanged": True,
                    "old_evidence_retained": True,
                    "removed_association_row_retained": False,
                    "temporal_binding_replacement": "BLOCKED / NOT IMPLEMENTED",
                    "genuine_provider_certification": "NOT TESTED",
                    "workflow_activation": "BLOCKED",
                },
                indent=2,
            )
            + "\n"
        )
