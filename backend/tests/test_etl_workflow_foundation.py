"""Focused ETL Phase A contracts, compatible with unittest CI discovery."""
import unittest
from unittest.mock import patch, MagicMock
from uuid import uuid4

from pydantic import ValidationError

from app.schemas.etl import WorkflowCreate, WorkflowJobCreate, WorkflowDependencyCreate
from app.models.entities import ETLWorkflow, ETLWorkflowDependency, JobOrder
from app.api.etl import create_workflow, list_workflows, create_workflow_job, list_workflow_jobs, create_workflow_dependency, list_workflow_dependencies
from fastapi import HTTPException


class ETLWorkflowFoundationTests(unittest.TestCase):
    def test_workflow_owns_schedule_and_sla(self):
        data = WorkflowCreate(
            organization_id=uuid4(), name="nightly", timezone="Asia/Kolkata",
            weekdays=[0, 2, 4], expected_window_start="01:00",
            expected_window_end="03:00", expected_duration_seconds=1800, sla_seconds=3600,
        )
        self.assertEqual(data.expected_window_start, "01:00")
        self.assertEqual(data.sla_seconds, 3600)

    def test_invalid_workflow_schedule_rejected(self):
        for values in (
            {"timezone": "Invalid/Zone"},
            {"weekdays": [8]},
            {"expected_window_start": "01:00"},
            {"expected_duration_seconds": 0},
        ):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                WorkflowCreate(organization_id=uuid4(), name="bad", **values)

    def test_job_contract_excludes_workflow_timing(self):
        self.assertNotIn("expected_window_start", WorkflowJobCreate.model_fields)
        self.assertNotIn("sla_seconds", WorkflowJobCreate.model_fields)
        job = WorkflowJobCreate(name="extract", hostname="etl-01", expected_duration_seconds=120)
        self.assertEqual(job.expected_duration_seconds, 120)

    def test_workflow_job_and_dependency_models_are_registered(self):
        self.assertTrue(JobOrder.__table__.c.workflow_id.nullable)
        self.assertEqual("etl_workflows", ETLWorkflow.__tablename__)
        self.assertEqual("etl_workflow_dependencies", ETLWorkflowDependency.__tablename__)

    def test_workflow_create_requires_customer_configure_permission(self):
        org = uuid4()
        payload = WorkflowCreate(organization_id=org, name="nightly")
        with patch("app.api.etl.require_permission", side_effect=HTTPException(403, "Permission required")) as guard:
            with self.assertRaises(HTTPException) as result:
                create_workflow(payload, db=MagicMock())
            self.assertEqual(result.exception.status_code, 403)
            guard.assert_called_once_with("etl.configure", org)

    def test_workflow_list_requires_customer_view_permission(self):
        org = uuid4()
        with patch("app.api.etl.require_permission", side_effect=HTTPException(403, "Permission required")) as guard:
            with self.assertRaises(HTTPException) as result:
                list_workflows(org, db=MagicMock())
            self.assertEqual(result.exception.status_code, 403)
            guard.assert_called_once_with("etl.view", org)

    def test_child_workflow_routes_enforce_customer_permissions(self):
        org, wid = uuid4(), uuid4()
        db = MagicMock()
        db.get.return_value = ETLWorkflow(id=wid, organization_id=org, name="nightly", environment="PROD")
        cases = [
            (create_workflow_job, (wid, WorkflowJobCreate(name="extract", hostname="etl-01", expected_duration_seconds=120)), "etl.configure"),
            (list_workflow_jobs, (wid,), "etl.view"),
            (create_workflow_dependency, (wid, WorkflowDependencyCreate(predecessor_job_id=uuid4(), successor_job_id=uuid4())), "etl.configure"),
            (list_workflow_dependencies, (wid,), "etl.view"),
        ]
        for func, args, permission in cases:
            with self.subTest(route=func.__name__), patch(
                "app.api.etl.require_permission",
                side_effect=HTTPException(403, "Permission required"),
            ) as guard:
                with self.assertRaises(HTTPException) as result:
                    func(*args, db=db)
                self.assertEqual(result.exception.status_code, 403)
                guard.assert_called_once_with(permission, org)

    def test_dependency_contract_rejects_bad_uuid(self):
        with self.assertRaises(ValidationError):
            WorkflowDependencyCreate(predecessor_job_id="invalid", successor_job_id=uuid4())


if __name__ == "__main__":
    unittest.main()
