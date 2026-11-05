"""Focused Phase A validation; no external scheduler or database needed."""
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.etl import WorkflowCreate, WorkflowJobCreate, WorkflowDependencyCreate
from app.models.entities import ETLWorkflow, ETLWorkflowDependency, JobOrder


def test_workflow_owns_schedule_and_sla():
    data = WorkflowCreate(
        organization_id=uuid4(), name="nightly", timezone="Asia/Kolkata",
        weekdays=[0, 2, 4], expected_window_start="01:00",
        expected_window_end="03:00", expected_duration_seconds=1800, sla_seconds=3600,
    )
    assert data.expected_window_start == "01:00"
    assert data.sla_seconds == 3600


@pytest.mark.parametrize("values", [
    {"timezone": "Invalid/Zone"},
    {"weekdays": [8]},
    {"expected_window_start": "01:00"},
    {"expected_duration_seconds": 0},
])
def test_invalid_workflow_schedule_rejected(values):
    with pytest.raises(ValidationError):
        WorkflowCreate(organization_id=uuid4(), name="bad", **values)


def test_job_contract_excludes_workflow_timing():
    assert "expected_window_start" not in WorkflowJobCreate.model_fields
    assert "sla_seconds" not in WorkflowJobCreate.model_fields
    job = WorkflowJobCreate(name="extract", hostname="etl-01", expected_duration_seconds=120)
    assert job.expected_duration_seconds == 120


def test_workflow_job_and_dependency_models_are_registered():
    assert JobOrder.__table__.c.workflow_id.nullable
    assert "etl_workflows" == ETLWorkflow.__tablename__
    assert "etl_workflow_dependencies" == ETLWorkflowDependency.__tablename__


def test_dependency_contract_rejects_bad_uuid():
    with pytest.raises(ValidationError):
        WorkflowDependencyCreate(predecessor_job_id="invalid", successor_job_id=uuid4())
