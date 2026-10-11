"""Local incident episodes, durable activity and historical alert backfill."""
from alembic import op
import sqlalchemy as sa

revision = "0021_operational_incidents"
down_revision = "0020_etl_monitoring_evidence"
branch_labels = depends_on = None

def upgrade():
    op.create_table("operational_incidents",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("organization_id", sa.UUID(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("episode_key", sa.String(120), nullable=False, unique=True),
        sa.Column("source_kind", sa.String(20), nullable=False),
        sa.Column("source_reference", sa.String(200), nullable=False),
        sa.Column("alert_state_id", sa.UUID(), sa.ForeignKey("alert_states.id")),
        sa.Column("history_id", sa.UUID(), sa.ForeignKey("job_order_histories.id")),
        sa.Column("data_source_id", sa.UUID(), sa.ForeignKey("data_sources.id")),
        sa.Column("title", sa.String(300), nullable=False), sa.Column("severity", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False), sa.Column("condition_status", sa.String(20), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recovered_at", sa.DateTime(timezone=True)), sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("status IN ('OPEN','ACKNOWLEDGED','INVESTIGATING','RESOLVED')", name="ck_incident_status"),
        sa.CheckConstraint("condition_status IN ('ACTIVE','RECOVERED')", name="ck_incident_condition"))
    op.create_index("ix_operational_incidents_organization_id", "operational_incidents", ["organization_id"])
    op.create_index("ix_operational_incidents_source_reference", "operational_incidents", ["source_reference"])
    op.create_index("ix_incident_org_opened", "operational_incidents", ["organization_id", "opened_at"])
    op.create_table("incident_activities",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("organization_id", sa.UUID(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("incident_id", sa.UUID(), sa.ForeignKey("operational_incidents.id"), nullable=False),
        sa.Column("event_type", sa.String(40), nullable=False), sa.Column("actor", sa.String(200), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False), sa.Column("text", sa.Text()),
        sa.Column("previous_status", sa.String(20)), sa.Column("new_status", sa.String(20)))
    for key in ("organization_id", "incident_id"):
        op.create_index("ix_incident_activities_" + key, "incident_activities", [key])
    # Deterministic backfill IDs are identifiers, never credentials. Recovered
    # alerts still require operator closure; source facts are not rewritten.
    op.execute("""INSERT INTO operational_incidents
        (id,organization_id,episode_key,source_kind,source_reference,alert_state_id,data_source_id,
         title,severity,status,condition_status,opened_at,recovered_at)
        SELECT md5('metric:'||a.id::text)::uuid,a.organization_id,'metric:'||a.id::text,'METRIC',a.id::text,
               a.id,m.data_source_id,left(coalesce(s.name||' · ','')||replace(r.name,coalesce(m.data_source_id::text,'')||':',''),300),a.severity,'OPEN',
               CASE WHEN a.status='RESOLVED' THEN 'RECOVERED' ELSE 'ACTIVE' END,a.first_triggered_at,a.resolved_at
        FROM alert_states a JOIN alert_rules r ON r.id=a.alert_rule_id
        JOIN metric_definitions m ON m.id=a.metric_definition_id LEFT JOIN data_sources s ON s.id=m.data_source_id""")
    op.execute("""INSERT INTO operational_incidents
        (id,organization_id,episode_key,source_kind,source_reference,history_id,data_source_id,
         title,severity,status,condition_status,opened_at,recovered_at)
        SELECT md5('etl:'||e.id::text)::uuid,j.organization_id,'etl:'||e.id::text,'ETL',e.reference,e.history_id,
               j.host_data_source_id,left(j.name||' · '||regexp_replace(e.event_type,'_OPEN$',''),300),
               coalesce(e.severity,'WARNING'),'OPEN',CASE WHEN x.recovered_at IS NULL THEN 'ACTIVE' ELSE 'RECOVERED' END,
               e.timestamp,x.recovered_at
        FROM alert_incident_events e JOIN job_order_histories h ON h.id=e.history_id JOIN job_orders j ON j.id=h.job_order_id
        LEFT JOIN LATERAL (SELECT min(r.timestamp) recovered_at FROM alert_incident_events r
            JOIN job_order_histories rh ON rh.id=r.history_id
            WHERE rh.job_order_id=j.id AND r.reference=e.reference AND r.timestamp>=e.timestamp
              AND r.event_type LIKE '%_RESOLVED' AND r.source='ETL_MONITOR') x ON TRUE
        WHERE e.source='ETL_MONITOR' AND e.event_type LIKE '%_OPEN' AND e.reference IS NOT NULL""")
    op.execute("""INSERT INTO incident_activities(id,organization_id,incident_id,event_type,actor,occurred_at)
        SELECT md5(id::text||'-opened')::uuid,organization_id,id,'SOURCE_OPENED','migration',opened_at FROM operational_incidents""")
    op.execute("""INSERT INTO incident_activities(id,organization_id,incident_id,event_type,actor,occurred_at)
        SELECT md5(id::text||'-recovered')::uuid,organization_id,id,'SOURCE_RECOVERED','migration',recovered_at
        FROM operational_incidents WHERE recovered_at IS NOT NULL""")
    op.execute("""CREATE FUNCTION opscontrol_incident_activity_guard() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'Incident activity is append-only'; END; $$""")
    op.execute("""CREATE TRIGGER opscontrol_incident_activity_append_only BEFORE UPDATE OR DELETE ON incident_activities
        FOR EACH ROW EXECUTE FUNCTION opscontrol_incident_activity_guard()""")

def downgrade():
    op.drop_table("incident_activities")
    op.execute("DROP FUNCTION opscontrol_incident_activity_guard()")
    op.drop_table("operational_incidents")
