"""Focused ETL Phase A contracts, compatible with unittest CI discovery."""
import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.schemas.etl import WorkflowCreate, WorkflowJobCreate, WorkflowDependencyCreate
from app.models.entities import ETLWorkflow, ETLWorkflowDependency, JobOrder


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

    def test_dependency_contract_rejects_bad_uuid(self):
        with self.assertRaises(ValidationError):
            WorkflowDependencyCreate(predecessor_job_id="invalid", successor_job_id=uuid4())


if __name__ == "__main__":
    unittest.main()
