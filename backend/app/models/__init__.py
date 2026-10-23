from app.models.entities import (
    OperationalIncident, IncidentActivity,
    InfrastructureEvidence, AlertIncidentEvent, Application, Collector, CollectorRun, CorrelationEvidence, CorrelationRecord, DataSource, ExecutionStatus, ExecutionType,
    Investigation, InvestigationStatus, InvestigationTransition, JobOrder, JobOrderHistory,
    KubernetesCluster, KubernetesClusterAssociation, KubernetesClusterAssociationDecision,
    JobStepExecution, AlertNotificationDelivery, AlertRule, AlertState, LogEvent, LogSource, MetricDefinition, MetricSample, OperatorNote, Organization, PentahoInstance, VM, MonitoringTemplate, MonitoringTemplateVersion, MonitoringTemplateAttachment,
)

__all__ = [
    "OperationalIncident", "IncidentActivity",
    "InfrastructureEvidence", "AlertIncidentEvent", "AlertNotificationDelivery", "CorrelationEvidence", "CorrelationRecord", "LogEvent", "AlertRule", "AlertState", "Application", "Collector", "CollectorRun", "DataSource", "ExecutionStatus", "ExecutionType",
    "Investigation", "InvestigationStatus", "InvestigationTransition", "JobOrder", "JobOrderHistory",
    "KubernetesCluster", "KubernetesClusterAssociation", "KubernetesClusterAssociationDecision",
    "JobStepExecution", "LogSource", "MetricDefinition", "MetricSample", "OperatorNote", "Organization",
    "PentahoInstance", "VM", "MonitoringTemplate", "MonitoringTemplateVersion", "MonitoringTemplateAttachment",
]

# Alert acknowledgment now references users. Register identity/access metadata
# for standalone collector/notification workers as well as the FastAPI process.
import app.security.models  # noqa: E402,F401

# Register canonical resource metadata for standalone ORM consumers.
# JobOrderHistory has a tenant-scoped FK to monitoring_resources.
import app.unified.models  # noqa: E402,F401
