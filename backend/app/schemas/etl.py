from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.models.entities import ExecutionStatus, ExecutionType
class StepCreate(BaseModel):
    name: str
    step_type: str | None = None
    status: str
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_seconds: int | None = Field(default=None, ge=0)
    records_read: int | None = None
    records_written: int | None = None
    records_rejected: int | None = None
    error_code: str | None = None
    error_message: str | None = None
class StepOut(StepCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
class ExecutionCreate(BaseModel):
    execution_type: ExecutionType
    status: ExecutionStatus
    started_at: datetime | None = None
    ended_at: datetime | None = None
    detected_at: datetime | None = None
    expected_runtime_seconds: int | None = Field(default=None, ge=0)
    sla_seconds: int | None = Field(default=None, ge=0)
    sla_status: str | None = None
    failed_step: str | None = None
    source_error_code: str | None = None
    source_error_message: str | None = None
    source_exception: str | None = None
    source_log_location: str | None = None
    source_result: str | None = None
    incident_number: str | None = None
    steps: list[StepCreate] = Field(default_factory=list)
class ExecutionListItem(BaseModel):
    id: UUID
    job_order_id: UUID
    execution_type: ExecutionType
    status: ExecutionStatus
    started_at: datetime | None
    ended_at: datetime | None
    detected_at: datetime | None
    expected_runtime_seconds: int | None
    sla_seconds: int | None
    sla_status: str | None
    failed_step: str | None
    incident_number: str | None
    job_name: str
    server: str
    environment: str
    organization: str
class ExecutionOut(ExecutionListItem):
    source_error_code: str | None
    source_error_message: str | None
    source_exception: str | None
    source_log_location: str | None
    source_result: str | None
    steps: list[StepOut]
