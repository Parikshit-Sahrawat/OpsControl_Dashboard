"""Actual migrated PostgreSQL, authenticated API and Chromium configuration flow."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models import (
    Organization,
    DataSource,
    Collector,
    JobOrder,
    ETLWorkflow,
    ETLWorkflowDependency,
    JobOrderHistory,
    ExecutionStatus,
    ExecutionType,
)
from app.security.models import User
from app.security.access_models import (
    CustomerAccessGrant,
    Role,
    RolePermission,
    UserRoleAssignment,
)
from app.security.passwords import hash_password
from tests import test_etl_workflow_scope as scope_tests


@unittest.skipUnless(
    os.getenv("ETL_WORKFLOW_UI_ACCEPTANCE") == "1",
    "Owned PostgreSQL/API/Chromium required",
)
class WorkflowUIAcceptance(unittest.TestCase):
    setUp = scope_tests.WorkflowScopeTests.setUp

    def test_real_configuration_browser_and_receipts(self):
        with SessionLocal() as db:
            source = DataSource(
                organization_id=self.a,
                name="UI stale telemetry fixture",
                source_type="API",
            )
            db.add(source)
            db.flush()
            collector = Collector(
                data_source_id=source.id,
                name="Synthetic stale collector",
                collector_type="HTTP",
                interval_seconds=30,
                last_success_at=datetime.now(timezone.utc) - timedelta(hours=1),
                enabled=True,
            )
            db.add(collector)
            db.flush()
            db.add(
                JobOrderHistory(
                    job_order_id=self.j1,
                    execution_type=ExecutionType.SCHEDULED,
                    status=ExecutionStatus.SUCCESS,
                    detected_at=datetime.now(timezone.utc),
                    source_evidence={"collector_id": str(collector.id)},
                    provider_execution_id="synthetic-ui-native-receipt",
                )
            )
            viewer = User(
                username="ui-viewer-" + uuid4().hex,
                password_hash=hash_password(self.password),
                platform_admin=False,
            )
            db.add(viewer)
            db.flush()
            role = Role(
                code="ui-viewer-" + uuid4().hex, name="UI read only " + uuid4().hex
            )
            db.add(role)
            db.flush()
            db.add_all(
                [
                    RolePermission(role_id=role.id, permission_key=key)
                    for key in ["etl.view", "resources.view", "customers.view"]
                ]
            )
            db.add(UserRoleAssignment(user_id=viewer.id, role_id=role.id))
            db.flush()
            db.add(
                CustomerAccessGrant(
                    user_id=viewer.id, role_id=role.id, organization_id=self.a
                )
            )
            legacy = JobOrder(
                organization_id=self.a,
                name="unassigned-ui-legacy-" + uuid4().hex,
                environment="PROD",
            )
            db.add(legacy)
            db.commit()
            legacy_id = legacy.id
            fixture = {
                "a": str(self.a),
                "b": str(self.b),
                "wa": str(self.wa),
                "wb": str(self.wb),
                "j1": str(self.j1),
                "j2": str(self.j2),
                "username": self.username,
                "password": self.password,
                "viewer": viewer.username,
            }
            before = db.scalar(
                select(JobOrder.workflow_id).where(JobOrder.id == self.jb)
            )
        with tempfile.TemporaryDirectory(prefix="etl004-private-") as private:
            file = Path(private) / "fixture.json"
            file.write_text(json.dumps(fixture))
            file.chmod(0o600)
            env = {**os.environ, "ETL_UI_FIXTURE": str(file)}
            root = Path(__file__).resolve().parents[2]
            result = subprocess.run(
                ["node", "frontend/scripts/workflow_configuration_acceptance.mjs"],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
                timeout=180,
            )
            Path(
                os.environ["ETL_SCOPE_EVIDENCE_DIR"], "workflow-browser.log"
            ).write_text(
                (result.stdout + "\n" + result.stderr).replace(
                    self.password, "[REDACTED]"
                )
            )
            self.assertEqual(result.returncode, 0, "See redacted workflow-browser.log")
        with SessionLocal() as db:
            self.assertIsNone(db.get(JobOrder, legacy_id).workflow_id)
            self.assertEqual(
                db.scalar(select(JobOrder.workflow_id).where(JobOrder.id == self.jb)),
                before,
            )
            self.assertEqual(db.get(Organization, self.a).id, self.a)
            workflow = db.scalar(
                select(ETLWorkflow).where(
                    ETLWorkflow.organization_id == self.a,
                    ETLWorkflow.name == "UI workflow edited",
                )
            )
            self.assertIsNotNone(workflow)
            self.assertEqual(workflow.sla_seconds, 900)
            self.assertEqual(workflow.expected_duration_seconds, 500)
            self.assertEqual(workflow.expected_window_start, "08:00")
            self.assertEqual(workflow.expected_window_end, "10:00")
            jobs = db.scalars(
                select(JobOrder).where(JobOrder.workflow_id == workflow.id)
            ).all()
            self.assertEqual(
                {j.name: j.expected_runtime_seconds for j in jobs},
                {"UI job one": 150, "UI job two": 120},
            )
            self.assertTrue(
                all(
                    j.organization_id == self.a
                    and j.environment == "PROD"
                    and j.vm.hostname == "ui-host.synthetic.invalid"
                    for j in jobs
                )
            )
            edges = db.scalars(
                select(ETLWorkflowDependency).where(
                    ETLWorkflowDependency.workflow_id == workflow.id
                )
            ).all()
            self.assertEqual(len(edges), 1)
            Path(
                os.environ["ETL_SCOPE_EVIDENCE_DIR"], "workflow-db-reconciliation.json"
            ).write_text(
                json.dumps(
                    {
                        "workflow_id": str(workflow.id),
                        "organization_id": str(workflow.organization_id),
                        "environment": workflow.environment,
                        "sla_seconds": workflow.sla_seconds,
                        "expected_duration_seconds": workflow.expected_duration_seconds,
                        "windows": [
                            workflow.expected_window_start,
                            workflow.expected_window_end,
                        ],
                        "jobs": {
                            j.name: {
                                "id": str(j.id),
                                "parent": str(j.workflow_id),
                                "duration": j.expected_runtime_seconds,
                                "hostname": j.vm.hostname,
                            }
                            for j in jobs
                        },
                        "persisted_dependency_count": len(edges),
                        "unassigned_legacy_preserved": True,
                        "cross_tenant_parent_preserved": True,
                    },
                    indent=2,
                )
                + "\n"
            )
