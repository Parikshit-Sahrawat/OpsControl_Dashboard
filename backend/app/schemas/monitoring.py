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
    metric_definition_id: UUID | None = None


class AlertRuleOut(AlertRuleBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    metric_definition_id: UUID
    created_at: datetime
    updated_at: datetime
