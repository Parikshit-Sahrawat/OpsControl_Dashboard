"""ARCH-001 lossless resource bindings, reconstruction and schedule state.

Historical records remain untouched. Ambiguous mappings are staged explicitly.
Populated downgrade refuses; retain the additive schema for app rollback.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0027_unified_monitoring"
down_revision = "0026_managed_telemetry_uat"
branch_labels = None
depends_on = None
DDL = (
    "\nCREATE TABLE event_correlation_groups (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tenvironment VARCHAR(20) NOT NULL, \n\tgroup_key VARCHAR(200) NOT NULL, \n\ttitle VARCHAR(300) NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\tconfidence VARCHAR(40) NOT NULL, \n\tevidence JSONB NOT NULL, \n\topened_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tlast_observed_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tresolved_at TIMESTAMP WITH TIME ZONE, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_correlation_group_org_id UNIQUE (organization_id, id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tUNIQUE (group_key)\n)\n\n",
    "CREATE INDEX ix_correlation_group_inventory ON event_correlation_groups (organization_id, environment, opened_at, id)",
    "CREATE INDEX ix_event_correlation_groups_organization_id ON event_correlation_groups (organization_id)",
    "\nCREATE TABLE resource_mapping_issues (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tentity_type VARCHAR(50) NOT NULL, \n\tentity_id UUID NOT NULL, \n\treason VARCHAR(100) NOT NULL, \n\tcandidates JSONB NOT NULL, \n\tresolved_at TIMESTAMP WITH TIME ZONE, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_mapping_issue_entity UNIQUE (entity_type, entity_id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n)\n\n",
    "CREATE INDEX ix_resource_mapping_issues_organization_id ON resource_mapping_issues (organization_id)",
    "\nCREATE TABLE monitoring_resources (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tdomain VARCHAR(10) NOT NULL, \n\tname VARCHAR(200) NOT NULL, \n\tenvironment VARCHAR(20) NOT NULL, \n\tvm_id UUID, \n\tjob_order_id UUID, \n\tdata_source_id UUID, \n\tprimary_collector_id UUID, \n\tlinked_vm_id UUID, \n\tconfiguration JSONB NOT NULL, \n\trevision INTEGER NOT NULL, \n\tactive BOOLEAN NOT NULL, \n\tactivation_status VARCHAR(30) NOT NULL, \n\tschedule_watermark TIMESTAMP WITH TIME ZONE, \n\tlast_engine_attempt_at TIMESTAMP WITH TIME ZONE, \n\tlast_engine_success_at TIMESTAMP WITH TIME ZONE, \n\tlast_engine_error VARCHAR(80), \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_monitoring_resource_org_id UNIQUE (organization_id, id), \n\tCONSTRAINT ck_resource_domain CHECK (domain IN ('VM','ETL','API')), \n\tCONSTRAINT ck_resource_environment CHECK (environment IN ('PROD','QA','TEST','DEV','SANDBOX')), \n\tCONSTRAINT ck_resource_binding CHECK ((domain='VM' AND vm_id IS NOT NULL AND job_order_id IS NULL) OR (domain='ETL' AND job_order_id IS NOT NULL AND vm_id IS NULL) OR (domain='API' AND data_source_id IS NOT NULL AND vm_id IS NULL AND job_order_id IS NULL)), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tUNIQUE (vm_id), \n\tFOREIGN KEY(vm_id) REFERENCES vms (id), \n\tUNIQUE (job_order_id), \n\tFOREIGN KEY(job_order_id) REFERENCES job_orders (id), \n\tUNIQUE (data_source_id), \n\tFOREIGN KEY(data_source_id) REFERENCES data_sources (id), \n\tFOREIGN KEY(primary_collector_id) REFERENCES collectors (id), \n\tFOREIGN KEY(linked_vm_id) REFERENCES vms (id)\n)\n\n",
    "CREATE INDEX ix_monitoring_resources_linked_vm_id ON monitoring_resources (linked_vm_id)",
    "CREATE INDEX ix_monitoring_resources_organization_id ON monitoring_resources (organization_id)",
    "CREATE INDEX ix_resource_domain_inventory ON monitoring_resources (organization_id, domain, environment, name, id)",
    "\nCREATE TABLE expected_execution_windows (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tresource_id UUID NOT NULL, \n\tscheduled_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tdeadline TIMESTAMP WITH TIME ZONE NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\thistory_id UUID, \n\tparameter_version INTEGER NOT NULL, \n\tevaluated_at TIMESTAMP WITH TIME ZONE, \n\tevidence JSONB NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT fk_schedule_resource_scope FOREIGN KEY(organization_id, resource_id) REFERENCES monitoring_resources (organization_id, id), \n\tCONSTRAINT uq_expected_execution_window UNIQUE (resource_id, scheduled_at), \n\tCONSTRAINT ck_schedule_deadline CHECK (deadline >= scheduled_at), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tFOREIGN KEY(history_id) REFERENCES job_order_histories (id)\n)\n\n",
    "CREATE INDEX ix_expected_evaluate ON expected_execution_windows (resource_id, status, scheduled_at)",
    "CREATE INDEX ix_expected_execution_windows_organization_id ON expected_execution_windows (organization_id)",
    "CREATE INDEX ix_expected_execution_windows_resource_id ON expected_execution_windows (resource_id)",
    "\nCREATE TABLE normalized_telemetry_events (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tresource_id UUID NOT NULL, \n\texternal_key VARCHAR(200) NOT NULL, \n\tsource_kind VARCHAR(30) NOT NULL, \n\tlog_event_id UUID, \n\thistory_id UUID, \n\tobserved_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\treceived_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tpayload JSONB NOT NULL, \n\tprocessing_status VARCHAR(20) NOT NULL, \n\tprocessing_error VARCHAR(80), \n\tparameter_version INTEGER, \n\tPRIMARY KEY (id), \n\tCONSTRAINT fk_normalized_resource_scope FOREIGN KEY(organization_id, resource_id) REFERENCES monitoring_resources (organization_id, id), \n\tCONSTRAINT uq_normalized_event_key UNIQUE (resource_id, external_key), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tFOREIGN KEY(log_event_id) REFERENCES log_events (id), \n\tFOREIGN KEY(history_id) REFERENCES job_order_histories (id)\n)\n\n",
    "CREATE INDEX ix_normalized_pending ON normalized_telemetry_events (resource_id, processing_status, observed_at, id)",
    "CREATE INDEX ix_normalized_telemetry_events_history_id ON normalized_telemetry_events (history_id)",
    "CREATE INDEX ix_normalized_telemetry_events_log_event_id ON normalized_telemetry_events (log_event_id)",
    "CREATE INDEX ix_normalized_telemetry_events_observed_at ON normalized_telemetry_events (observed_at)",
    "CREATE INDEX ix_normalized_telemetry_events_organization_id ON normalized_telemetry_events (organization_id)",
    "CREATE INDEX ix_normalized_telemetry_events_resource_id ON normalized_telemetry_events (resource_id)",
    "\nCREATE TABLE resource_dependencies (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tresource_id UUID NOT NULL, \n\tdepends_on_id UUID NOT NULL, \n\trelationship_type VARCHAR(30) NOT NULL, \n\tservice_identity VARCHAR(200) NOT NULL, \n\tvalid_from TIMESTAMP WITH TIME ZONE NOT NULL, \n\tvalid_to TIMESTAMP WITH TIME ZONE, \n\tPRIMARY KEY (id), \n\tCONSTRAINT fk_dependency_resource_scope FOREIGN KEY(organization_id, resource_id) REFERENCES monitoring_resources (organization_id, id), \n\tCONSTRAINT fk_dependency_parent_scope FOREIGN KEY(organization_id, depends_on_id) REFERENCES monitoring_resources (organization_id, id), \n\tCONSTRAINT ck_dependency_not_self CHECK (resource_id <> depends_on_id), \n\tCONSTRAINT ck_dependency_type CHECK (relationship_type IN ('HOSTED_ON','REQUIRES_SERVICE','DEPENDS_ON')), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n)\n\n",
    "CREATE INDEX ix_resource_dependencies_depends_on_id ON resource_dependencies (depends_on_id)",
    "CREATE INDEX ix_resource_dependencies_organization_id ON resource_dependencies (organization_id)",
    "CREATE INDEX ix_resource_dependencies_resource_id ON resource_dependencies (resource_id)",
    "CREATE UNIQUE INDEX uq_dependency_current ON resource_dependencies (resource_id, depends_on_id, relationship_type, service_identity) WHERE valid_to IS NULL",
    "\nCREATE TABLE resource_parameter_versions (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tresource_id UUID NOT NULL, \n\tversion INTEGER NOT NULL, \n\tconfiguration JSONB NOT NULL, \n\tsha256 VARCHAR(64) NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\tactor_id UUID, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT fk_parameter_resource_scope FOREIGN KEY(organization_id, resource_id) REFERENCES monitoring_resources (organization_id, id), \n\tCONSTRAINT uq_resource_parameter_version UNIQUE (resource_id, version), \n\tCONSTRAINT ck_parameter_status CHECK (status IN ('VALIDATED','ACTIVE','SUPERSEDED')), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tFOREIGN KEY(actor_id) REFERENCES users (id)\n)\n\n",
    "CREATE INDEX ix_resource_parameter_versions_organization_id ON resource_parameter_versions (organization_id)",
    "CREATE INDEX ix_resource_parameter_versions_resource_id ON resource_parameter_versions (resource_id)",
    "CREATE UNIQUE INDEX uq_parameter_active ON resource_parameter_versions (resource_id) WHERE status='ACTIVE'",
    "\nCREATE TABLE resource_conditions (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tresource_id UUID NOT NULL, \n\tcondition_key VARCHAR(200) NOT NULL, \n\tcondition_type VARCHAR(60) NOT NULL, \n\tactive BOOLEAN NOT NULL, \n\tseverity VARCHAR(20) NOT NULL, \n\tmessage VARCHAR(500) NOT NULL, \n\tfirst_observed_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tlast_observed_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tresolved_at TIMESTAMP WITH TIME ZONE, \n\talert_state_id UUID, \n\tevidence JSONB NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT fk_condition_resource_scope FOREIGN KEY(organization_id, resource_id) REFERENCES monitoring_resources (organization_id, id), \n\tCONSTRAINT uq_resource_condition UNIQUE (resource_id, condition_key), \n\tCONSTRAINT uq_condition_org_id UNIQUE (organization_id, id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tFOREIGN KEY(alert_state_id) REFERENCES alert_states (id)\n)\n\n",
    "CREATE INDEX ix_resource_conditions_alert_state_id ON resource_conditions (alert_state_id)",
    "CREATE INDEX ix_resource_conditions_organization_id ON resource_conditions (organization_id)",
    "CREATE INDEX ix_resource_conditions_resource_id ON resource_conditions (resource_id)",
    "\nCREATE TABLE resource_parameter_activations (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tresource_id UUID NOT NULL, \n\tparameter_version INTEGER NOT NULL, \n\teffective_from TIMESTAMP WITH TIME ZONE NOT NULL, \n\teffective_to TIMESTAMP WITH TIME ZONE, \n\tactor_id UUID, \n\tPRIMARY KEY (id), \n\tCONSTRAINT fk_parameter_activation_scope FOREIGN KEY(organization_id, resource_id) REFERENCES monitoring_resources (organization_id, id), \n\tCONSTRAINT fk_parameter_activation_version FOREIGN KEY(resource_id, parameter_version) REFERENCES resource_parameter_versions (resource_id, version), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tFOREIGN KEY(actor_id) REFERENCES users (id)\n)\n\n",
    "CREATE INDEX ix_resource_parameter_activations_organization_id ON resource_parameter_activations (organization_id)",
    "CREATE INDEX ix_resource_parameter_activations_resource_id ON resource_parameter_activations (resource_id)",
    "CREATE UNIQUE INDEX uq_current_parameter_activation ON resource_parameter_activations (resource_id) WHERE effective_to IS NULL",
    "\nCREATE TABLE event_correlation_members (\n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tgroup_id UUID NOT NULL, \n\tcondition_id UUID NOT NULL, \n\trelationship_id UUID, \n\tadded_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tevidence JSONB NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT fk_member_group_scope FOREIGN KEY(organization_id, group_id) REFERENCES event_correlation_groups (organization_id, id), \n\tCONSTRAINT fk_member_condition_scope FOREIGN KEY(organization_id, condition_id) REFERENCES resource_conditions (organization_id, id), \n\tCONSTRAINT uq_correlation_member UNIQUE (group_id, condition_id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n\tFOREIGN KEY(relationship_id) REFERENCES resource_dependencies (id)\n)\n\n",
    "CREATE INDEX ix_event_correlation_members_condition_id ON event_correlation_members (condition_id)",
    "CREATE INDEX ix_event_correlation_members_group_id ON event_correlation_members (group_id)",
    "CREATE INDEX ix_event_correlation_members_organization_id ON event_correlation_members (organization_id)",
)
TABLES = (
    "event_correlation_groups",
    "resource_mapping_issues",
    "monitoring_resources",
    "expected_execution_windows",
    "normalized_telemetry_events",
    "resource_dependencies",
    "resource_parameter_versions",
    "resource_conditions",
    "resource_parameter_activations",
    "event_correlation_members",
)


def upgrade():
    op.execute("ALTER TYPE executionstatus ADD VALUE IF NOT EXISTS 'DELAYED'")
    op.execute("ALTER TYPE executionstatus ADD VALUE IF NOT EXISTS 'UNKNOWN'")
    op.alter_column("job_orders", "vm_id", nullable=True)
    op.create_index(
        "uq_saas_job_order_identity",
        "job_orders",
        ["organization_id", "name", "environment"],
        unique=True,
        postgresql_where=sa.text("vm_id IS NULL"),
    )
    op.add_column(
        "collector_runs",
        sa.Column("source_metadata", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "job_order_histories",
        sa.Column("monitoring_conditions", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "job_step_executions",
        sa.Column("external_step_id", sa.String(200), nullable=True),
    )
    op.add_column(
        "job_step_executions",
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
    )
    op.alter_column("job_step_executions", "attempt", server_default=None)
    op.add_column(
        "job_step_executions",
        sa.Column("source_evidence", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "collector_config_versions",
        sa.Column(
            "agent_configuration",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.alter_column(
        "collector_config_versions", "agent_configuration", server_default=None
    )
    op.create_index(
        "uq_step_external_attempt",
        "job_step_executions",
        ["history_id", "external_step_id", "attempt"],
        unique=True,
        postgresql_where=sa.text("external_step_id IS NOT NULL"),
    )
    for ddl in DDL:
        op.execute(ddl)
    # Preserve known identities and original metadata. Do not invent a host
    # address or silently convert custom environments to production.
    op.execute(
        """INSERT INTO monitoring_resources
      (id,organization_id,domain,name,environment,vm_id,configuration,revision,active,activation_status,created_at,updated_at)
      SELECT id,organization_id,'VM',hostname,upper(environment),id,
        jsonb_build_object('hostname',hostname,'os_type',coalesce(os,'Other'),'legacy',true),1,monitoring_enabled,'CONFIGURED',created_at,now()
      FROM vms WHERE upper(environment) IN ('PROD','QA','TEST','DEV','SANDBOX')"""
    )
    op.execute(
        """WITH matches AS (
      SELECT v.id, array_agg(s.id) AS ids FROM vms v JOIN data_sources s ON s.organization_id=v.organization_id
      AND upper(s.source_type) IN ('LINUX','LINUX_HOST','WINDOWS','WINDOWS_HOST')
      AND lower(coalesce(s.connection_config::jsonb->'opscontrol'->>'hostname',s.endpoint,s.name))=lower(v.hostname)
      AND upper(coalesce(s.connection_config::jsonb->'opscontrol'->>'environment','PROD'))=upper(v.environment)
      GROUP BY v.id)
      UPDATE monitoring_resources r SET data_source_id=m.ids[1] FROM matches m WHERE r.vm_id=m.id AND cardinality(m.ids)=1"""
    )
    op.execute(
        """INSERT INTO monitoring_resources
      (id,organization_id,domain,name,environment,job_order_id,linked_vm_id,configuration,revision,active,activation_status,created_at,updated_at)
      SELECT id,organization_id,'ETL',name,upper(environment),id,vm_id,
        jsonb_build_object('platform','PENTAHO','jobchain',name,'legacy',true),1,active,'CONFIGURED',created_at,now()
      FROM job_orders WHERE upper(environment) IN ('PROD','QA','TEST','DEV','SANDBOX') AND (vm_id IS NULL OR EXISTS(SELECT 1 FROM vms v WHERE v.id=job_orders.vm_id AND v.organization_id=job_orders.organization_id))"""
    )
    op.execute(
        """INSERT INTO monitoring_resources
      (id,organization_id,domain,name,environment,data_source_id,configuration,revision,active,activation_status,created_at,updated_at)
      SELECT id,organization_id,'API',name,upper(coalesce(connection_config::jsonb->'opscontrol'->>'environment','PROD')),id,
        jsonb_build_object('legacy',true,'endpoint',endpoint),1,enabled,'CONFIGURED',created_at,now()
      FROM data_sources WHERE upper(source_type) IN ('API','HTTP','HTTPS')
      AND upper(coalesce(connection_config::jsonb->'opscontrol'->>'environment','PROD')) IN ('PROD','QA','TEST','DEV','SANDBOX')"""
    )
    op.execute(
        """WITH candidates AS (SELECT data_source_id,array_agg(id) AS ids FROM collectors WHERE upper(collector_type)='OTEL' GROUP BY data_source_id)
      UPDATE monitoring_resources r SET primary_collector_id=c.ids[1] FROM candidates c
      WHERE r.domain='VM' AND r.data_source_id=c.data_source_id AND cardinality(c.ids)=1"""
    )
    op.execute(
        """WITH candidates AS (SELECT data_source_id,array_agg(id) AS ids FROM collectors WHERE upper(collector_type) IN ('API','NATIVE_API') GROUP BY data_source_id)
      UPDATE monitoring_resources r SET primary_collector_id=c.ids[1] FROM candidates c
      WHERE r.domain='API' AND r.data_source_id=c.data_source_id AND cardinality(c.ids)=1"""
    )
    op.execute(
        """UPDATE monitoring_resources r SET configuration=r.configuration||jsonb_build_object('legacy_template_attachments',a.docs)
      FROM (SELECT j.id,jsonb_agg(jsonb_build_object('template_id',t.template_id,'version',t.template_version,'enabled',t.enabled)) AS docs
      FROM job_orders j JOIN monitoring_template_attachments t ON t.data_source_id=j.host_data_source_id GROUP BY j.id) a
      WHERE r.job_order_id=a.id"""
    )
    # Deterministic UUIDs avoid introducing a pgcrypto installation dependency.
    op.execute(
        """INSERT INTO resource_mapping_issues(id,organization_id,entity_type,entity_id,reason,candidates)
      SELECT md5('arch001:VM:'||v.id::text)::uuid,v.organization_id,'VM',v.id,
      CASE WHEN r.id IS NULL THEN 'UNSUPPORTED_LEGACY_ENVIRONMENT' ELSE 'NO_UNAMBIGUOUS_HOST_SOURCE' END,'[]'::jsonb
      FROM vms v LEFT JOIN monitoring_resources r ON r.vm_id=v.id WHERE r.id IS NULL OR r.data_source_id IS NULL"""
    )
    op.execute(
        """INSERT INTO resource_mapping_issues(id,organization_id,entity_type,entity_id,reason,candidates)
      SELECT md5('arch001:ETL:'||j.id::text)::uuid,j.organization_id,'ETL',j.id,CASE WHEN upper(j.environment) NOT IN ('PROD','QA','TEST','DEV','SANDBOX') THEN 'UNSUPPORTED_LEGACY_ENVIRONMENT' ELSE 'CUSTOMER_VM_MISMATCH' END,'[]'::jsonb
      FROM job_orders j LEFT JOIN monitoring_resources r ON r.job_order_id=j.id WHERE r.id IS NULL"""
    )
    op.execute(
        """INSERT INTO resource_mapping_issues(id,organization_id,entity_type,entity_id,reason,candidates)
      SELECT md5('arch001:COLLECTOR:'||r.id::text)::uuid,r.organization_id,'COLLECTOR',r.id,'MULTIPLE_VM_COLLECTORS_REQUIRE_SELECTION',
      coalesce((SELECT jsonb_agg(c.id) FROM collectors c WHERE c.data_source_id=r.data_source_id AND upper(c.collector_type)='OTEL'),'[]'::jsonb)
      FROM monitoring_resources r WHERE r.domain='VM' AND (SELECT count(*) FROM collectors c WHERE c.data_source_id=r.data_source_id AND upper(c.collector_type)='OTEL')>1"""
    )
    op.execute(
        """CREATE FUNCTION opscontrol_resource_identity_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE parent_org uuid; source_id uuid;
    BEGIN
      IF NEW.vm_id IS NOT NULL THEN SELECT organization_id INTO parent_org FROM vms WHERE id=NEW.vm_id;
        IF parent_org IS DISTINCT FROM NEW.organization_id THEN RAISE EXCEPTION 'resource VM scope mismatch'; END IF; END IF;
      IF NEW.linked_vm_id IS NOT NULL THEN SELECT organization_id INTO parent_org FROM vms WHERE id=NEW.linked_vm_id;
        IF parent_org IS DISTINCT FROM NEW.organization_id THEN RAISE EXCEPTION 'linked VM scope mismatch'; END IF; END IF;
      IF NEW.job_order_id IS NOT NULL THEN SELECT organization_id INTO parent_org FROM job_orders WHERE id=NEW.job_order_id;
        IF parent_org IS DISTINCT FROM NEW.organization_id THEN RAISE EXCEPTION 'job scope mismatch'; END IF; END IF;
      IF NEW.data_source_id IS NOT NULL THEN SELECT organization_id INTO parent_org FROM data_sources WHERE id=NEW.data_source_id;
        IF parent_org IS DISTINCT FROM NEW.organization_id THEN RAISE EXCEPTION 'source scope mismatch'; END IF; END IF;
      IF NEW.primary_collector_id IS NOT NULL THEN SELECT data_source_id INTO source_id FROM collectors WHERE id=NEW.primary_collector_id;
        IF source_id IS DISTINCT FROM NEW.data_source_id THEN RAISE EXCEPTION 'collector source mismatch'; END IF; END IF;
      RETURN NEW;
    END $$"""
    )
    op.execute(
        "CREATE TRIGGER resource_identity_guard BEFORE INSERT OR UPDATE ON monitoring_resources FOR EACH ROW EXECUTE FUNCTION opscontrol_resource_identity_guard()"
    )
    op.execute(
        """CREATE FUNCTION opscontrol_parameter_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
      BEGIN IF TG_OP='DELETE' THEN RAISE EXCEPTION 'parameter versions are immutable'; END IF; IF NEW.configuration IS DISTINCT FROM OLD.configuration OR NEW.resource_id IS DISTINCT FROM OLD.resource_id
      OR NEW.version IS DISTINCT FROM OLD.version OR NEW.sha256 IS DISTINCT FROM OLD.sha256
      OR NEW.organization_id IS DISTINCT FROM OLD.organization_id THEN RAISE EXCEPTION 'parameter versions are immutable'; END IF; RETURN NEW; END $$"""
    )
    op.execute(
        "CREATE TRIGGER parameter_version_immutable BEFORE UPDATE OR DELETE ON resource_parameter_versions FOR EACH ROW EXECUTE FUNCTION opscontrol_parameter_immutable()"
    )


def downgrade():
    bind = op.get_bind()
    if bind.scalar(sa.text("SELECT count(*) FROM job_orders WHERE vm_id IS NULL")):
        raise RuntimeError(
            "VM-less executions prevent safe downgrade; retain additive schema"
        )
    for query in (
        "SELECT count(*) FROM collector_config_versions WHERE agent_configuration <> '{}'::jsonb",
        "SELECT count(*) FROM job_order_histories WHERE monitoring_conditions IS NOT NULL",
        "SELECT count(*) FROM job_step_executions WHERE external_step_id IS NOT NULL OR attempt<>1 OR source_evidence IS NOT NULL",
        "SELECT count(*) FROM collector_runs WHERE source_metadata IS NOT NULL AND source_metadata<>'{}'::jsonb",
    ):
        if bind.scalar(sa.text(query)):
            raise RuntimeError(
                "Populated native evidence/configuration prevents data-losing downgrade"
            )
    for table in TABLES:
        if bind.scalar(sa.text("SELECT count(*) FROM " + table)):
            raise RuntimeError(
                "Populated ARCH-001 data prevents destructive downgrade; retain additive schema"
            )
    op.execute(
        "DROP TRIGGER parameter_version_immutable ON resource_parameter_versions"
    )
    op.execute("DROP FUNCTION opscontrol_parameter_immutable()")
    op.execute("DROP TRIGGER resource_identity_guard ON monitoring_resources")
    op.execute("DROP FUNCTION opscontrol_resource_identity_guard()")
    for table in reversed(TABLES):
        op.drop_table(table)
    op.drop_index("uq_step_external_attempt", table_name="job_step_executions")
    for column in ("source_evidence", "attempt", "external_step_id"):
        op.drop_column("job_step_executions", column)
    op.drop_column("job_order_histories", "monitoring_conditions")
    op.drop_column("collector_runs", "source_metadata")
    op.drop_column("collector_config_versions", "agent_configuration")
    op.drop_index("uq_saas_job_order_identity", table_name="job_orders")
    op.alter_column("job_orders", "vm_id", nullable=False)
    # Enum labels are additive; dropping them would require rewriting history.
