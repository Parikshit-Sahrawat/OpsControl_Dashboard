from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class DataSourceBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    source_type: str = Field(min_length=1, max_length=100)
    description: str | None = None
    endpoint: str | None = Field(default=None, max_length=1000)
    auth_type: str | None = Field(default=None, max_length=100)
    connection_config: dict | None = None
    enabled: bool = True


class DataSourceCreate(DataSourceBase):
    organization_id: UUID


class DataSourceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    source_type: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    endpoint: str | None = Field(default=None, max_length=1000)
    auth_type: str | None = Field(default=None, max_length=100)
    connection_config: dict | None = None
    enabled: bool | None = None


class DataSourceOut(DataSourceBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    status: str
    last_test_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class CollectorBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    collector_type: str = Field(min_length=1, max_length=100)
    enabled: bool = True
    interval_seconds: int = Field(default=60, ge=5)
    configuration: dict | None = None


class CollectorCreate(CollectorBase):
    data_source_id: UUID


class CollectorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    collector_type: str | None = Field(default=None, min_length=1, max_length=100)
    enabled: bool | None = None
    interval_seconds: int | None = Field(default=None, ge=5)
    configuration: dict | None = None


class CollectorOut(CollectorBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    data_source_id: UUID
    status: str
    last_run_at: datetime | None
    last_success_at: datetime | None
    last_error_at: datetime | None
    last_error: str | None
    next_run_at: datetime | None
    created_at: datetime
    updated_at: datetime


class MetricDefinitionBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    resource_type: str = Field(min_length=1, max_length=100)
    resource_id: UUID | None = None
    metric_type: str = Field(min_length=1, max_length=50)
    unit: str | None = Field(default=None, max_length=50)
    collection_interval_seconds: int = Field(default=60, ge=5)
    retention_days: int = Field(default=365, ge=1)
    aggregation: str = Field(default="avg", max_length=50)
    query_config: dict | None = None
    enabled: bool = True


class MetricDefinitionCreate(MetricDefinitionBase):
    organization_id: UUID
    data_source_id: UUID | None = None
    collector_id: UUID | None = None


class MetricDefinitionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    resource_type: str | None = Field(default=None, min_length=1, max_length=100)
    resource_id: UUID | None = None
    metric_type: str | None = Field(default=None, min_length=1, max_length=50)
    unit: str | None = Field(default=None, max_length=50)
    collection_interval_seconds: int | None = Field(default=None, ge=5)
    retention_days: int | None = Field(default=None, ge=1)
    aggregation: str | None = Field(default=None, max_length=50)
    query_config: dict | None = None
    enabled: bool | None = None
    data_source_id: UUID | None = None
    collector_id: UUID | None = None


class MetricDefinitionOut(MetricDefinitionBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    data_source_id: UUID | None
    collector_id: UUID | None
    created_at: datetime
    updated_at: datetime


class LogSourceBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    source_type: str = Field(min_length=1, max_length=100)
    resource_type: str = Field(min_length=1, max_length=100)
    resource_id: UUID | None = None
    location: str | None = Field(default=None, max_length=1000)
    parser_type: str = Field(default="RAW", max_length=100)
    parser_config: dict | None = None
    start_position: str = Field(default="NEW", max_length=50)
    collection_interval_seconds: int = Field(default=30, ge=5)
    retention_days: int = Field(default=30, ge=1)
    enabled: bool = True


class LogSourceCreate(LogSourceBase):
    organization_id: UUID
    data_source_id: UUID | None = None
    collector_id: UUID | None = None


class LogSourceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    source_type: str | None = Field(default=None, max_length=100)
    resource_type: str | None = Field(default=None, max_length=100)
    resource_id: UUID | None = None
    location: str | None = Field(default=None, max_length=1000)
    parser_type: str | None = Field(default=None, max_length=100)
    parser_config: dict | None = None
    start_position: str | None = Field(default=None, max_length=50)
    collection_interval_seconds: int | None = Field(default=None, ge=5)
    retention_days: int | None = Field(default=None, ge=1)
    enabled: bool | None = None
    data_source_id: UUID | None = None
    collector_id: UUID | None = None


class LogSourceOut(LogSourceBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    data_source_id: UUID | None
    collector_id: UUID | None
    created_at: datetime
    updated_at: datetime


class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    code: str
    active: bool


class AlertRuleBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    severity: str = Field(default="WARNING", max_length=50)
    operator: str = Field(default="GT", max_length=20)
    threshold_value: str = Field(min_length=1, max_length=100)
    evaluation_window_seconds: int = Field(default=60, ge=5)
    consecutive_breaches: int = Field(default=1, ge=1)
    enabled: bool = True
    notification_channels: list[str] | None = None


class AlertRuleCreate(AlertRuleBase):
    organization_id: UUID
    metric_definition_id: UUID


class AlertRuleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    severity: str | None = Field(default=None, max_length=50)
    operator: str | None = Field(default=None, max_length=20)
    threshold_value: str | None = Field(default=None, min_length=1, max_length=100)
    evaluation_window_seconds: int | None = Field(default=None, ge=5)
    consecutive_breaches: int | None = Field(default=None, ge=1)
    enabled: bool | None = None
    notification_channels: list[str] | None = None
    metric_definition_id: UUID | None = None


class AlertRuleOut(AlertRuleBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    metric_definition_id: UUID
    created_at: datetime
    updated_at: datetime


class AlertStateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    alert_rule_id: UUID
    metric_definition_id: UUID
    status: str
    severity: str
    first_triggered_at: datetime
    last_evaluated_at: datetime
    resolved_at: datetime | None
    last_value: float
    breach_count: int
    message: str
    external_references: dict | None
    created_at: datetime
    updated_at: datetime


class AlertNotificationDeliveryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    alert_state_id: UUID
    channel: str
    event_type: str
    status: str
    attempts: int
    external_reference: str | None
    last_error: str | None
    sent_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CollectorRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    collector_id: UUID
    started_at: datetime
    ended_at: datetime | None
    status: str
    outcome: str | None
    http_status: int | None
    response_time_ms: int | None
    response_size_bytes: int | None
    response_body: str | None
    error_message: str | None


class MetricSampleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    metric_definition_id: UUID
    collector_id: UUID | None
    collector_run_id: UUID | None
    observed_at: datetime
    value_numeric: float
    unit: str | None
    dimensions: dict | None
    created_at: datetime


class LogEventCreate(BaseModel):
    organization_id: UUID
    log_source_id: UUID
    observed_at: datetime
    severity: str | None = Field(default=None, max_length=30)
    event_type: str | None = Field(default=None, max_length=100)
    message: str = Field(min_length=1)
    parser_type: str | None = Field(default=None, max_length=100)
    source_offset: str | None = Field(default=None, max_length=200)
    fingerprint: str | None = Field(default=None, max_length=128)
    attributes: dict | None = None


class LogEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    log_source_id: UUID
    observed_at: datetime
    severity: str | None
    event_type: str | None
    message: str
    parser_type: str | None
    source_offset: str | None
    fingerprint: str | None
    attributes: dict | None
    created_at: datetime

class CorrelationEvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    correlation_id: UUID
    evidence_type: str
    source_id: UUID
    resource_type: str | None
    resource_id: UUID | None
    observed_at: datetime
    severity: str | None
    relationship: str
    details: dict | None
    created_at: datetime

class CorrelationRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    history_id: UUID
    anchor_at: datetime
    window_start: datetime
    window_end: datetime
    status: str
    primary_category: str
    confidence: str
    summary: str
    evidence_count: int
    analysis_version: int
    created_at: datetime
    updated_at: datetime
    evidence: list[CorrelationEvidenceOut] = []
