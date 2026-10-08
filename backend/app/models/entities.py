import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

sa_relationship = relationship

from app.db.session import Base

class ExecutionType(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    MANUAL = "MANUAL"

class ExecutionStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    RUNNING = "RUNNING"
    LONG_RUNNING = "LONG_RUNNING"
    NO_RUN = "NO_RUN"
    NO_RESPONSE = "NO_RESPONSE"

class InvestigationStatus(str, enum.Enum):
    NEW = "NEW"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    INVESTIGATING = "INVESTIGATING"
    ROOT_CAUSE_IDENTIFIED = "ROOT_CAUSE_IDENTIFIED"
    RECOVERY_IN_PROGRESS = "RECOVERY_IN_PROGRESS"
    MONITORING = "MONITORING"
    RESOLVED = "RESOLVED"

class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    vms: Mapped[list["VM"]] = relationship(back_populates="organization")
    job_orders: Mapped[list["JobOrder"]] = relationship(back_populates="organization")
    data_sources: Mapped[list["DataSource"]] = relationship(back_populates="organization")
    metric_definitions: Mapped[list["MetricDefinition"]] = relationship(back_populates="organization")
    log_sources: Mapped[list["LogSource"]] = relationship(back_populates="organization")
    alert_rules: Mapped[list["AlertRule"]] = relationship(back_populates="organization")
    alert_states: Mapped[list["AlertState"]] = relationship(back_populates="organization")
    correlation_records: Mapped[list["CorrelationRecord"]] = relationship(back_populates="organization", cascade="all, delete-orphan")

class VM(Base):
    __tablename__ = "vms"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    hostname: Mapped[str] = mapped_column(String(200), nullable=False)
    environment: Mapped[str] = mapped_column(String(50), nullable=False, default="PROD")
    os: Mapped[str | None] = mapped_column(String(100))
    monitoring_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    organization: Mapped["Organization"] = relationship(back_populates="vms")
    applications: Mapped[list["Application"]] = relationship(back_populates="vm")
    pentaho_instances: Mapped[list["PentahoInstance"]] = relationship(back_populates="vm")
    job_orders: Mapped[list["JobOrder"]] = relationship(back_populates="vm")
    __table_args__ = (UniqueConstraint("organization_id", "hostname", name="uq_vm_org_hostname"),)

class Application(Base):
    __tablename__ = "applications"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vm_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vms.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    app_type: Mapped[str | None] = mapped_column(String(100))
    monitoring_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    vm: Mapped["VM"] = relationship(back_populates="applications")
    __table_args__ = (UniqueConstraint("vm_id", "name", name="uq_application_vm_name"),)

class PentahoInstance(Base):
    __tablename__ = "pentaho_instances"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vm_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vms.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(500))
    repository_name: Mapped[str | None] = mapped_column(String(200))
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    vm: Mapped["VM"] = relationship(back_populates="pentaho_instances")

class JobOrder(Base):
    __tablename__ = "job_orders"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    vm_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vms.id"), nullable=False, index=True)
    pentaho_instance_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pentaho_instances.id"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    environment: Mapped[str] = mapped_column(String(50), nullable=False, default="PROD")
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    expected_runtime_seconds: Mapped[int | None] = mapped_column(Integer)
    sla_seconds: Mapped[int | None] = mapped_column(Integer)
    schedule: Mapped[dict | None] = mapped_column(JSON)
    expected_window_start: Mapped[str | None] = mapped_column(String(10))
    expected_window_end: Mapped[str | None] = mapped_column(String(10))
    no_run_grace_seconds: Mapped[int | None] = mapped_column(Integer)
    monitoring_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    organization: Mapped["Organization"] = relationship(back_populates="job_orders")
    vm: Mapped["VM"] = relationship(back_populates="job_orders")
    histories: Mapped[list["JobOrderHistory"]] = relationship(back_populates="job_order", cascade="all, delete-orphan")
    __table_args__ = (UniqueConstraint("organization_id", "vm_id", "name", name="uq_job_order_identity"),)

class JobOrderHistory(Base):
    __tablename__ = "job_order_histories"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("job_orders.id"), nullable=False, index=True)
    execution_type: Mapped[ExecutionType] = mapped_column(Enum(ExecutionType), nullable=False)
    status: Mapped[ExecutionStatus] = mapped_column(Enum(ExecutionStatus), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    detected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expected_runtime_seconds: Mapped[int | None] = mapped_column(Integer)
    sla_seconds: Mapped[int | None] = mapped_column(Integer)
    sla_status: Mapped[str | None] = mapped_column(String(50))
    failed_step: Mapped[str | None] = mapped_column(String(200))
    source_error_code: Mapped[str | None] = mapped_column(String(100))
    source_error_message: Mapped[str | None] = mapped_column(Text)
    source_exception: Mapped[str | None] = mapped_column(Text)
    source_log_location: Mapped[str | None] = mapped_column(String(1000))
    source_result: Mapped[str | None] = mapped_column(String(200))
    incident_number: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    job_order: Mapped["JobOrder"] = relationship(back_populates="histories")
    steps: Mapped[list["JobStepExecution"]] = relationship(back_populates="history", cascade="all, delete-orphan")
    investigation: Mapped["Investigation | None"] = relationship(back_populates="history", uselist=False, cascade="all, delete-orphan")
    alert_events: Mapped[list["AlertIncidentEvent"]] = relationship(back_populates="history", cascade="all, delete-orphan")
    correlation: Mapped["CorrelationRecord | None"] = relationship(back_populates="history", uselist=False, cascade="all, delete-orphan")

class JobStepExecution(Base):
    __tablename__ = "job_step_executions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    history_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("job_order_histories.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    step_type: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    records_read: Mapped[int | None] = mapped_column(Integer)
    records_written: Mapped[int | None] = mapped_column(Integer)
    records_rejected: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    history: Mapped["JobOrderHistory"] = relationship(back_populates="steps")

class Investigation(Base):
    __tablename__ = "investigations"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    history_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("job_order_histories.id"), nullable=False, unique=True)
    status: Mapped[InvestigationStatus] = mapped_column(Enum(InvestigationStatus), nullable=False, default=InvestigationStatus.NEW)
    operator: Mapped[str | None] = mapped_column(String(200))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_category: Mapped[str | None] = mapped_column(String(100))
    suspected_cause: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[str | None] = mapped_column(String(50))
    root_cause: Mapped[str | None] = mapped_column(Text)
    root_cause_status: Mapped[str | None] = mapped_column(String(50))
    history: Mapped["JobOrderHistory"] = relationship(back_populates="investigation")
    transitions: Mapped[list["InvestigationTransition"]] = relationship(back_populates="investigation", cascade="all, delete-orphan")
    notes: Mapped[list["OperatorNote"]] = relationship(back_populates="investigation", cascade="all, delete-orphan")

class InvestigationTransition(Base):
    __tablename__ = "investigation_transitions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("investigations.id"), nullable=False, index=True)
    previous_status: Mapped[InvestigationStatus] = mapped_column(Enum(InvestigationStatus), nullable=False)
    new_status: Mapped[InvestigationStatus] = mapped_column(Enum(InvestigationStatus), nullable=False)
    operator: Mapped[str] = mapped_column(String(200), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    investigation: Mapped["Investigation"] = relationship(back_populates="transitions")

class OperatorNote(Base):
    __tablename__ = "operator_notes"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("investigations.id"), nullable=False, index=True)
    operator: Mapped[str] = mapped_column(String(200), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_reference: Mapped[str | None] = mapped_column(String(1000))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    investigation: Mapped["Investigation"] = relationship(back_populates="notes")

class AlertIncidentEvent(Base):
    __tablename__ = "alert_incident_events"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    history_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("job_order_histories.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(200))
    severity: Mapped[str | None] = mapped_column(String(50))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    history: Mapped["JobOrderHistory"] = relationship(back_populates="alert_events")


class MonitoringTemplate(Base):
    __tablename__ = "monitoring_templates"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    scope: Mapped[str] = mapped_column(String(200), nullable=False, default="VM + Application / Services")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="COMMITTED")
    package_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    committed_by: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    versions: Mapped[list["MonitoringTemplateVersion"]] = relationship(back_populates="template", cascade="all, delete-orphan", order_by="MonitoringTemplateVersion.version")

class MonitoringTemplateVersion(Base):
    __tablename__ = "monitoring_template_versions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("monitoring_templates.id"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="COMMITTED")
    package_config: Mapped[dict] = mapped_column(JSON, nullable=False)
    committed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    committed_by: Mapped[str | None] = mapped_column(String(200))
    template: Mapped["MonitoringTemplate"] = relationship(back_populates="versions")
    __table_args__ = (UniqueConstraint("template_id", "version", name="uq_monitoring_template_version"),)

class MonitoringTemplateAttachment(Base):
    __tablename__ = "monitoring_template_attachments"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    data_source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False, index=True)
    template_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("monitoring_templates.id", ondelete="RESTRICT"), nullable=False, index=True)
    template_version: Mapped[int] = mapped_column(Integer, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    overrides: Mapped[dict | None] = mapped_column(JSON)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    data_source: Mapped["DataSource"] = relationship(back_populates="template_attachments")
    template: Mapped["MonitoringTemplate"] = relationship()
    __table_args__ = (
        UniqueConstraint("data_source_id", "template_id", name="uq_template_attachment_source_template"),
    )

class DataSource(Base):
    __tablename__ = "data_sources"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_type: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    endpoint: Mapped[str | None] = mapped_column(String(1000))
    auth_type: Mapped[str | None] = mapped_column(String(100))
    connection_config: Mapped[dict | None] = mapped_column(JSON)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="UNKNOWN", nullable=False)
    last_test_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    organization: Mapped["Organization"] = relationship(back_populates="data_sources")
    collectors: Mapped[list["Collector"]] = relationship(back_populates="data_source", cascade="all, delete-orphan")
    metric_definitions: Mapped[list["MetricDefinition"]] = relationship(back_populates="data_source")
    log_sources: Mapped[list["LogSource"]] = relationship(back_populates="data_source")
    template_attachments: Mapped[list["MonitoringTemplateAttachment"]] = relationship(back_populates="data_source", cascade="all, delete-orphan")
    __table_args__ = (UniqueConstraint("organization_id", "name", name="uq_data_source_org_name"),)

class Collector(Base):
    __tablename__ = "collectors"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    data_source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("data_sources.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    collector_type: Mapped[str] = mapped_column(String(100), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    interval_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    configuration: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(50), default="STOPPED", nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    data_source: Mapped["DataSource"] = relationship(back_populates="collectors")
    metric_definitions: Mapped[list["MetricDefinition"]] = relationship(back_populates="collector")
    log_sources: Mapped[list["LogSource"]] = relationship(back_populates="collector")
    runs: Mapped[list["CollectorRun"]] = relationship(back_populates="collector", cascade="all, delete-orphan")
    __table_args__ = (UniqueConstraint("data_source_id", "name", name="uq_collector_source_name"),)

class CollectorRun(Base):
    __tablename__ = "collector_runs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collector_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("collectors.id"), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    outcome: Mapped[str | None] = mapped_column(String(100))
    http_status: Mapped[int | None] = mapped_column(Integer)
    response_time_ms: Mapped[int | None] = mapped_column(Integer)
    response_size_bytes: Mapped[int | None] = mapped_column(Integer)
    response_body: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    collector: Mapped["Collector"] = relationship(back_populates="runs")

class MetricDefinition(Base):
    __tablename__ = "metric_definitions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    data_source_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("data_sources.id"), index=True)
    collector_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("collectors.id"), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    metric_type: Mapped[str] = mapped_column(String(50), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(50))
    collection_interval_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    retention_days: Mapped[int] = mapped_column(Integer, default=365, nullable=False)
    aggregation: Mapped[str] = mapped_column(String(50), default="avg", nullable=False)
    query_config: Mapped[dict | None] = mapped_column(JSON)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    organization: Mapped["Organization"] = relationship(back_populates="metric_definitions")
    data_source: Mapped["DataSource | None"] = relationship(back_populates="metric_definitions")
    collector: Mapped["Collector | None"] = relationship(back_populates="metric_definitions")
    samples: Mapped[list["MetricSample"]] = relationship(back_populates="metric_definition", cascade="all, delete-orphan")

class MetricSample(Base):
    __tablename__ = "metric_samples"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    metric_definition_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("metric_definitions.id"), nullable=False, index=True)
    collector_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("collectors.id"), index=True)
    collector_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("collector_runs.id"), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    value_numeric: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(50))
    dimensions: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    metric_definition: Mapped["MetricDefinition"] = relationship(back_populates="samples")
    collector: Mapped["Collector | None"] = relationship()
    collector_run: Mapped["CollectorRun | None"] = relationship()

    __table_args__ = (
        Index("ix_metric_samples_metric_observed", "metric_definition_id", "observed_at"),
        Index("ix_metric_samples_org_observed", "organization_id", "observed_at"),
    )

class LogSource(Base):
    __tablename__ = "log_sources"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    data_source_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("data_sources.id"), index=True)
    collector_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("collectors.id"), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    location: Mapped[str | None] = mapped_column(String(1000))
    parser_type: Mapped[str] = mapped_column(String(100), default="RAW", nullable=False)
    parser_config: Mapped[dict | None] = mapped_column(JSON)
    start_position: Mapped[str] = mapped_column(String(50), default="NEW", nullable=False)
    collection_interval_seconds: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    retention_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    organization: Mapped["Organization"] = relationship(back_populates="log_sources")
    data_source: Mapped["DataSource | None"] = relationship(back_populates="log_sources")
    collector: Mapped["Collector | None"] = relationship(back_populates="log_sources")

class LogEvent(Base):
    __tablename__ = "log_events"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    log_source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("log_sources.id"), nullable=False, index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    severity: Mapped[str | None] = mapped_column(String(30))
    event_type: Mapped[str | None] = mapped_column(String(100))
    message: Mapped[str] = mapped_column(Text, nullable=False)
    parser_type: Mapped[str | None] = mapped_column(String(100))
    source_offset: Mapped[str | None] = mapped_column(String(200))
    fingerprint: Mapped[str | None] = mapped_column(String(128), index=True)
    attributes: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    log_source: Mapped["LogSource"] = relationship()

    __table_args__ = (
        Index("ix_log_events_source_observed", "log_source_id", "observed_at"),
        Index("ix_log_events_org_observed", "organization_id", "observed_at"),
    )


class AlertRule(Base):
    __tablename__ = "alert_rules"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    metric_definition_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("metric_definitions.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False, default="WARNING")
    operator: Mapped[str] = mapped_column(String(20), nullable=False, default="GT")
    threshold_value: Mapped[str] = mapped_column(String(100), nullable=False)
    evaluation_window_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    consecutive_breaches: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notification_channels: Mapped[list | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    organization: Mapped["Organization"] = relationship(back_populates="alert_rules")
    metric_definition: Mapped["MetricDefinition"] = relationship()
    alert_states: Mapped[list["AlertState"]] = relationship(back_populates="alert_rule", cascade="all, delete-orphan")
    __table_args__ = (UniqueConstraint("organization_id", "name", name="uq_alert_rule_org_name"),)

class AlertState(Base):
    __tablename__ = "alert_states"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    alert_rule_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("alert_rules.id"), nullable=False, index=True)
    metric_definition_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("metric_definitions.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    first_triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_value: Mapped[float] = mapped_column(Float, nullable=False)
    breach_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    external_references: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    organization: Mapped["Organization"] = relationship(back_populates="alert_states")
    alert_rule: Mapped["AlertRule"] = relationship(back_populates="alert_states")

class AlertNotificationDelivery(Base):
    __tablename__ = "alert_notification_deliveries"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_state_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("alert_states.id"), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    external_reference: Mapped[str | None] = mapped_column(String(500))
    last_error: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    alert_state: Mapped["AlertState"] = relationship()

class CorrelationRecord(Base):
    __tablename__ = "correlation_records"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    history_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("job_order_histories.id"), nullable=False, unique=True, index=True)
    anchor_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ANALYZED")
    primary_category: Mapped[str] = mapped_column(String(100), nullable=False, default="NO_RELATED_EVIDENCE")
    confidence: Mapped[str] = mapped_column(String(30), nullable=False, default="NONE")
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    analysis_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    organization: Mapped["Organization"] = relationship(back_populates="correlation_records")
    history: Mapped["JobOrderHistory"] = relationship(back_populates="correlation")
    evidence: Mapped[list["CorrelationEvidence"]] = relationship(back_populates="correlation", cascade="all, delete-orphan")

class CorrelationEvidence(Base):
    __tablename__ = "correlation_evidence"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    correlation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("correlation_records.id"), nullable=False, index=True)
    evidence_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    resource_type: Mapped[str | None] = mapped_column(String(100))
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    severity: Mapped[str | None] = mapped_column(String(50))
    relationship: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    correlation: Mapped["CorrelationRecord"] = sa_relationship(back_populates="evidence")
    __table_args__ = (
        Index("ix_correlation_evidence_corr_observed", "correlation_id", "observed_at"),
        Index("ix_correlation_evidence_resource_observed", "resource_id", "observed_at"),
    )
