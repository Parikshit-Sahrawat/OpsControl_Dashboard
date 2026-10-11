"""Transactional alert-to-incident projection; reads never create evidence."""
from sqlalchemy import select
from app.models import OperationalIncident, IncidentActivity, MetricDefinition

def activity(db, incident, event_type, at, actor="collector", **values):
    db.add(IncidentActivity(organization_id=incident.organization_id, incident_id=incident.id,
                           event_type=event_type, actor=actor, occurred_at=at, **values))

def recover(db, incident, at):
    if incident and incident.condition_status == "ACTIVE":
        incident.condition_status = "RECOVERED"
        incident.recovered_at = at
        activity(db, incident, "SOURCE_RECOVERED", at)

def metric_episode(db, state):
    key = "metric:" + str(state.id)
    incident = db.scalar(select(OperationalIncident).where(OperationalIncident.episode_key == key))
    if incident is None:
        metric = db.get(MetricDefinition, state.metric_definition_id)
        source = metric.data_source if metric else None
        rule_name = state.alert_rule.name.removeprefix(str(metric.data_source_id) + ":") if metric else state.alert_rule.name
        incident = OperationalIncident(organization_id=state.organization_id, episode_key=key,
            source_kind="METRIC", source_reference=str(state.id), alert_state_id=state.id,
            data_source_id=metric.data_source_id if metric else None,
            title=((source.name + " · " if source else "") + rule_name)[:300], severity=state.severity, status="OPEN",
            condition_status="ACTIVE", opened_at=state.first_triggered_at)
        db.add(incident); db.flush()
        activity(db, incident, "SOURCE_OPENED", state.first_triggered_at)
    if state.status == "RESOLVED": recover(db, incident, state.resolved_at)
    return incident

def etl_episode(db, job, event):
    if event.event_type.endswith("_OPEN"):
        incident = OperationalIncident(organization_id=job.organization_id,
            episode_key="etl:" + str(event.id), source_kind="ETL", source_reference=event.reference,
            history_id=event.history_id, data_source_id=job.host_data_source_id,
            title=(job.name + " · " + event.event_type.removesuffix("_OPEN"))[:300],
            severity=event.severity or "WARNING", status="OPEN", condition_status="ACTIVE",
            opened_at=event.timestamp)
        db.add(incident); db.flush(); activity(db, incident, "SOURCE_OPENED", event.timestamp)
    else:
        incident = db.scalar(select(OperationalIncident).where(
            OperationalIncident.organization_id == job.organization_id,
            OperationalIncident.source_kind == "ETL",
            OperationalIncident.source_reference == event.reference,
            OperationalIncident.condition_status == "ACTIVE").order_by(OperationalIncident.opened_at.desc()).limit(1))
        recover(db, incident, event.timestamp)
