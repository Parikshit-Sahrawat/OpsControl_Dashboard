"""Add managed telemetry without deleting archived incidents or legacy memberships.

Downgrade is allowed only in an empty disposable fixture. Populated installations
retain the additive schema and use an application rollback/backup recovery plan.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0026_managed_telemetry_uat"
down_revision = "0025_provider_department_rbac"
branch_labels = None
depends_on = None
DDL = (
    "\nCREATE TABLE notification_destinations (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tname VARCHAR(160) NOT NULL, \n\tchannel VARCHAR(20) NOT NULL, \n\tconfiguration JSONB NOT NULL, \n\tenabled BOOLEAN NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_notification_destination_name UNIQUE (organization_id, name), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n)\n\n",
    "CREATE INDEX ix_notification_destinations_organization_id ON notification_destinations (organization_id)",
    "\nCREATE TABLE agent_registrations (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tcollector_id UUID NOT NULL, \n\ttoken_hash VARCHAR(64) NOT NULL, \n\texpires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tconsumed_at TIMESTAMP WITH TIME ZONE, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tFOREIGN KEY(collector_id) REFERENCES collectors (id), \n\tUNIQUE (token_hash)\n)\n\n",
    "CREATE INDEX ix_agent_registrations_collector_id ON agent_registrations (collector_id)",
    "CREATE INDEX ix_agent_registrations_organization_id ON agent_registrations (organization_id)",
    "\nCREATE TABLE collector_config_versions (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tcollector_id UUID NOT NULL, \n\trevision INTEGER NOT NULL, \n\tyaml_text TEXT NOT NULL, \n\tsha256 VARCHAR(64) NOT NULL, \n\truntime_version VARCHAR(80) NOT NULL, \n\tvalidation_status VARCHAR(30) NOT NULL, \n\tmethod_snapshot JSONB NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_collector_config_revision UNIQUE (collector_id, revision), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tFOREIGN KEY(collector_id) REFERENCES collectors (id)\n)\n\n",
    "CREATE INDEX ix_collector_config_versions_collector_id ON collector_config_versions (collector_id)",
    "CREATE INDEX ix_collector_config_versions_organization_id ON collector_config_versions (organization_id)",
    "\nCREATE TABLE collector_methods (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tcollector_id UUID NOT NULL, \n\tname VARCHAR(160) NOT NULL, \n\tmethod_type VARCHAR(30) NOT NULL, \n\tconfiguration JSONB NOT NULL, \n\tenabled BOOLEAN NOT NULL, \n\tvalidation_status VARCHAR(30) NOT NULL, \n\trevision INTEGER NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tdeleted_at TIMESTAMP WITH TIME ZONE, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tFOREIGN KEY(collector_id) REFERENCES collectors (id)\n)\n\n",
    "CREATE INDEX ix_collector_methods_collector_id ON collector_methods (collector_id)",
    "CREATE INDEX ix_collector_methods_organization_id ON collector_methods (organization_id)",
    "\nCREATE TABLE managed_agents (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tcollector_id UUID NOT NULL, \n\tworker_id UUID NOT NULL, \n\thostname VARCHAR(255) NOT NULL, \n\tversion VARCHAR(80) NOT NULL, \n\truntime_version VARCHAR(80) NOT NULL, \n\tlast_seen_at TIMESTAMP WITH TIME ZONE, \n\tdesired_revision INTEGER, \n\tapplied_revision INTEGER, \n\thealth VARCHAR(30) NOT NULL, \n\tlast_error VARCHAR(500), \n\tenabled BOOLEAN NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tUNIQUE (collector_id), \n\tFOREIGN KEY(collector_id) REFERENCES collectors (id), \n\tUNIQUE (worker_id), \n\tFOREIGN KEY(worker_id) REFERENCES worker_identities (id)\n)\n\n",
    "CREATE INDEX ix_managed_agents_organization_id ON managed_agents (organization_id)",
    "\nCREATE TABLE agent_deployments (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tagent_id UUID NOT NULL, \n\trevision INTEGER NOT NULL, \n\tprevious_revision INTEGER, \n\tstatus VARCHAR(30) NOT NULL, \n\tactor_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tcompleted_at TIMESTAMP WITH TIME ZONE, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tFOREIGN KEY(agent_id) REFERENCES managed_agents (id), \n\tFOREIGN KEY(actor_id) REFERENCES users (id)\n)\n\n",
    "CREATE INDEX ix_agent_deployments_agent_id ON agent_deployments (agent_id)",
    "CREATE INDEX ix_agent_deployments_organization_id ON agent_deployments (organization_id)",
    "\nCREATE TABLE telemetry_receipts (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tagent_id UUID NOT NULL, \n\tsignal VARCHAR(10) NOT NULL, \n\trecord_count INTEGER NOT NULL, \n\tpayload_hash VARCHAR(64) NOT NULL, \n\treceived_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_telemetry_batch UNIQUE (agent_id, signal, payload_hash), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tFOREIGN KEY(agent_id) REFERENCES managed_agents (id)\n)\n\n",
    "CREATE INDEX ix_telemetry_agent_signal_time ON telemetry_receipts (agent_id, signal, received_at)",
    "CREATE INDEX ix_telemetry_receipts_agent_id ON telemetry_receipts (agent_id)",
    "CREATE INDEX ix_telemetry_receipts_organization_id ON telemetry_receipts (organization_id)",
    "\nCREATE TABLE trace_spans (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tagent_id UUID NOT NULL, \n\ttrace_id VARCHAR(32) NOT NULL, \n\tspan_id VARCHAR(16) NOT NULL, \n\tname VARCHAR(255) NOT NULL, \n\tstarted_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tended_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tattributes JSONB NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tFOREIGN KEY(agent_id) REFERENCES managed_agents (id)\n)\n\n",
    "CREATE INDEX ix_trace_spans_agent_id ON trace_spans (agent_id)",
    "CREATE INDEX ix_trace_spans_organization_id ON trace_spans (organization_id)",
)


def upgrade():
    for statement in DDL:
        op.execute(statement)
    op.add_column(
        "alert_rules", sa.Column("evaluation_config", postgresql.JSONB(), nullable=True)
    )
    op.add_column(
        "alert_states",
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "alert_states",
        sa.Column(
            "acknowledged_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
    )
    op.execute("UPDATE service_providers SET name='OpsControl Services' WHERE id='45c4acb0-64fe-532b-ae18-678c1324902d' AND code='DEFAULT' AND name='PTC'")
    # Retain retired permission rows for history; map only existing equivalent
    # role capabilities to the monitoring-alert replacements, never to admin.
    op.execute(
        "INSERT INTO permissions(key,description,delegable) VALUES ('alerts.view','View monitoring alerts',true),('alerts.acknowledge','Acknowledge monitoring alerts',true) ON CONFLICT DO NOTHING"
    )
    op.execute(
        "INSERT INTO role_permissions(role_id,permission_key) SELECT role_id,CASE WHEN permission_key='incidents.view' THEN 'alerts.view' ELSE 'alerts.acknowledge' END FROM role_permissions WHERE permission_key IN ('incidents.view','incidents.acknowledge','incidents.manage') ON CONFLICT DO NOTHING"
    )
    op.execute(
        "UPDATE roles SET name='Alert Operator' WHERE name='Incident Operator' AND code='incident-operator'"
    )
    # Legacy multiple memberships survive. Future inserts/reactivations enforce
    # one department, with a user row lock also protecting direct SQL writers.
    op.execute(
        """CREATE FUNCTION opscontrol_single_department() RETURNS trigger LANGUAGE plpgsql AS $$
      BEGIN
        IF NEW.active AND (TG_OP='INSERT' OR NOT OLD.active OR NEW.user_id<>OLD.user_id OR NEW.department_id<>OLD.department_id) THEN
          PERFORM id FROM users WHERE id=NEW.user_id FOR UPDATE;
          IF EXISTS(SELECT 1 FROM department_memberships WHERE user_id=NEW.user_id AND active AND id<>NEW.id) THEN
            RAISE EXCEPTION 'Employee already has an active department' USING ERRCODE='23514';
          END IF;
        END IF;
        RETURN NEW;
      END $$"""
    )
    op.execute(
        "CREATE TRIGGER trg_single_department BEFORE INSERT OR UPDATE ON department_memberships FOR EACH ROW EXECUTE FUNCTION opscontrol_single_department()"
    )


def downgrade():
    db = op.get_bind()
    names = [
        "notification_destinations",
        "agent_registrations",
        "collector_config_versions",
        "collector_methods",
        "managed_agents",
        "agent_deployments",
        "telemetry_receipts",
        "trace_spans",
    ]
    if (
        any(
            db.execute(sa.text("SELECT EXISTS(SELECT 1 FROM " + name + ")")).scalar()
            for name in names
        )
        or db.execute(
            sa.text(
                "SELECT EXISTS(SELECT 1 FROM alert_rules WHERE evaluation_config IS NOT NULL)"
            )
        ).scalar()
    ):
        raise RuntimeError(
            "Populated managed telemetry schema cannot be downgraded; retain schema and use reviewed application rollback"
        )
    op.execute("DROP TRIGGER trg_single_department ON department_memberships")
    op.execute("DROP FUNCTION opscontrol_single_department()")
    op.drop_column("alert_states", "acknowledged_by")
    op.drop_column("alert_states", "acknowledged_at")
    op.drop_column("alert_rules", "evaluation_config")
    for name in reversed(names):
        op.drop_table(name)
    # Additive alert permissions are intentionally retained on empty rollback.
