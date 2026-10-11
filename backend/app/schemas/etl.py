from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator
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
    organization_id: UUID
    duration_seconds: int | None = None
    provider_execution_id: str | None = None
    monitoring_status: str = 'UNKNOWN'
class ExecutionOut(ExecutionListItem):
    source_error_code: str | None
    source_error_message: str | None
    source_exception: str | None
    source_log_location: str | None
    source_result: str | None
    steps: list[StepOut]
    source_evidence: dict | None = None

class JobOrderCreate(BaseModel):
    organization_id: UUID
    hostname: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=200)
    environment: str = Field(default='PROD', min_length=1, max_length=50)
    host_data_source_id: UUID | None = None
    expected_runtime_seconds: int = Field(ge=1, le=604800)
    sla_seconds: int = Field(ge=1, le=604800)
    expected_window_start: str | None = Field(default=None, pattern=r'^\d{2}:\d{2}$')
    expected_window_end: str | None = Field(default=None, pattern=r'^\d{2}:\d{2}$')
    no_run_grace_seconds: int = Field(default=900, ge=0, le=86400)
    timezone: str = 'UTC'
    weekdays: list[int] = Field(default_factory=lambda: list(range(7)), min_length=1, max_length=7)

    @model_validator(mode='after')
    def validate_policy(self):
        from datetime import time
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
        try: ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError): raise ValueError('Valid schedule timezone required')
        if any(type(day) is not int or day not in range(7) for day in self.weekdays): raise ValueError('Invalid weekdays')
        if self.sla_seconds < self.expected_runtime_seconds: raise ValueError('SLA must be at least expected runtime')
        if bool(self.expected_window_start) != bool(self.expected_window_end): raise ValueError('Both window endpoints required')
        for value in (self.expected_window_start, self.expected_window_end):
            if value: time.fromisoformat(value)
        return self
