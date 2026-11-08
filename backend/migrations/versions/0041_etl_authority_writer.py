"""Add authority provenance and fence legacy writers for opted-in Jobs.

No historical backfill; migration0040 and its preservation rules are unchanged.
"""

from alembic import op

revision = "0041_etl_authority_writer"
down_revision = "0040_etl_native_bindings"
branch_labels = None
depends_on = None

DDL = [
    "\nCREATE TABLE etl_native_attestations (\n\tbinding_id UUID NOT NULL, \n\tresource_id UUID NOT NULL, \n\ttarget_key VARCHAR(64) NOT NULL, \n\tenvelope JSONB NOT NULL, \n\tenvelope_sha256 VARCHAR(64) NOT NULL, \n\tissuer_key_id VARCHAR(100) NOT NULL, \n\texpires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tsubmitted_by UUID NOT NULL, \n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\trevision INTEGER NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT fk_attestation_binding FOREIGN KEY(organization_id, binding_id) REFERENCES etl_native_bindings (organization_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT fk_attestation_resource FOREIGN KEY(organization_id, resource_id) REFERENCES monitoring_resources (organization_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT uq_etl_native_attestation_scope UNIQUE (organization_id, id), \n\tUNIQUE (envelope_sha256), \n\tFOREIGN KEY(submitted_by) REFERENCES users (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n)\n\n",
    "CREATE INDEX ix_etl_native_attestations_organization_id ON etl_native_attestations (organization_id)",
    "\nCREATE TABLE etl_authority_revocations (\n\tattestation_id UUID NOT NULL, \n\tactor_id UUID NOT NULL, \n\treason VARCHAR(500) NOT NULL, \n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\trevision INTEGER NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT fk_authority_revocation FOREIGN KEY(organization_id, attestation_id) REFERENCES etl_native_attestations (organization_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT uq_etl_authority_revocation_scope UNIQUE (organization_id, id), \n\tUNIQUE (attestation_id), \n\tFOREIGN KEY(actor_id) REFERENCES users (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n)\n\n",
    "CREATE INDEX ix_etl_authority_revocations_organization_id ON etl_authority_revocations (organization_id)",
    "\nCREATE TABLE etl_binding_qualifications (\n\tbinding_id UUID NOT NULL, \n\tattestation_id UUID NOT NULL, \n\tjob_order_id UUID NOT NULL, \n\ttarget_key VARCHAR(64) NOT NULL, \n\tvalid_until TIMESTAMP WITH TIME ZONE, \n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\trevision INTEGER NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT fk_qualification_binding FOREIGN KEY(organization_id, binding_id) REFERENCES etl_native_bindings (organization_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT fk_qualification_attestation FOREIGN KEY(organization_id, attestation_id) REFERENCES etl_native_attestations (organization_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT uq_etl_binding_qualification_scope UNIQUE (organization_id, id), \n\tUNIQUE (binding_id), \n\tFOREIGN KEY(job_order_id) REFERENCES job_orders (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n)\n\n",
    "CREATE INDEX ix_etl_binding_qualifications_organization_id ON etl_binding_qualifications (organization_id)",
    "CREATE UNIQUE INDEX uq_native_qualified_owner ON etl_binding_qualifications (organization_id, target_key) WHERE valid_until IS NULL",
]

FENCED_TABLES = (
    "job_orders",
    "job_order_histories",
    "normalized_telemetry_events",
    "monitoring_resources",
    "pipeline_jobs",
    "pipeline_integrations",
    "pipeline_methods",
    "pipeline_connections",
    "pipeline_capabilities",
    "pipeline_associations",
    "pipeline_sources",
    "pipeline_evidence",
    "collectors",
    "collector_runs",
    "job_step_executions",
    "pentaho_execution_attempts",
    "pentaho_native_aliases",
    "pentaho_attempt_revisions",
    "pentaho_recovery_links",
    "pentaho_recovery_decisions",
    "pentaho_evidence_reviews",
    "pentaho_evidence_decisions",
    "pentaho_historical_notices",
)


def upgrade():
    for statement in DDL:
        op.execute(statement)
    op.execute(FUNCTIONS)
    for table in FENCED_TABLES:
        op.execute(
            f"CREATE TRIGGER etl_legacy_writer_fence BEFORE INSERT OR UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION etl_legacy_writer_fence()"
        )
    for table in (
        "etl_native_attestations",
        "etl_authority_revocations",
        "etl_binding_qualifications",
    ):
        op.execute(
            f"CREATE TRIGGER etl_authority_immutable BEFORE INSERT OR UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION etl_authority_immutable()"
        )
    op.execute(
        "CREATE TRIGGER etl_binding_optin_lock BEFORE INSERT ON etl_native_bindings FOR EACH ROW EXECUTE FUNCTION etl_binding_optin_lock()"
    )
    op.execute(
        "CREATE CONSTRAINT TRIGGER etl_receipt_authority AFTER INSERT ON etl_binding_receipts DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION etl_receipt_authority()"
    )
    op.execute(
        "CREATE CONSTRAINT TRIGGER etl_binding_qualified AFTER INSERT OR UPDATE ON etl_native_bindings DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION etl_binding_qualified()"
    )


def downgrade():
    # Central preflight refuses when ANY opted-in history exists, even if the
    # new tables are empty: dropping only the fence would enable old bypasses.
    op.execute("DROP TRIGGER etl_receipt_authority ON etl_binding_receipts")
    op.execute("DROP TRIGGER etl_binding_qualified ON etl_native_bindings")
    op.execute("DROP TRIGGER etl_binding_optin_lock ON etl_native_bindings")
    for table in FENCED_TABLES:
        op.execute(f"DROP TRIGGER etl_legacy_writer_fence ON {table}")
    for table in (
        "etl_binding_qualifications",
        "etl_authority_revocations",
        "etl_native_attestations",
    ):
        op.execute(f"DROP TABLE {table}")
    for function in (
        "etl_receipt_authority",
        "etl_binding_qualified",
        "etl_binding_optin_lock",
        "etl_authority_immutable",
        "etl_legacy_writer_fence",
    ):
        op.execute(f"DROP FUNCTION {function}()")


FUNCTIONS = r"""
CREATE FUNCTION etl_binding_optin_lock() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 PERFORM 1 FROM job_orders WHERE id=NEW.job_order_id FOR UPDATE;
 IF NEW.previous_id IS NULL AND (
   EXISTS(SELECT 1 FROM jsonb_array_elements(NEW.method_snapshot) snap
     JOIN pipeline_methods m ON m.source_id=(snap->>'source_id')::uuid
     JOIN pipeline_integrations i ON i.id=m.integration_id
     WHERE i.enabled AND i.deleted_at IS NULL)
   OR EXISTS(SELECT 1 FROM jsonb_array_elements(NEW.method_snapshot) snap
     JOIN pipeline_sources s ON s.id=(snap->>'source_id')::uuid
     JOIN collectors c ON c.id=s.legacy_collector_id WHERE c.enabled)
 ) THEN RAISE EXCEPTION 'Active shared source requires reviewed handoff before initial opt-in'; END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION etl_legacy_writer_fence() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE row_data jsonb; old_data jsonb; jobs uuid[]; jid uuid; identity uuid;
BEGIN
 IF current_setting('opscontrol.etl_writer_protocol',true)='1' THEN
   IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
 END IF;
 row_data := CASE WHEN TG_OP='DELETE' THEN to_jsonb(OLD) ELSE to_jsonb(NEW) END;
 old_data := CASE WHEN TG_OP='INSERT' THEN '{}'::jsonb ELSE to_jsonb(OLD) END;
 identity := (row_data->>'id')::uuid;
 IF TG_TABLE_NAME='job_orders' THEN jobs:=ARRAY[identity];
 ELSIF TG_TABLE_NAME='job_order_histories' THEN jobs:=ARRAY[(row_data->>'job_order_id')::uuid,(old_data->>'job_order_id')::uuid];
 ELSIF TG_TABLE_NAME='monitoring_resources' THEN jobs:=ARRAY[(row_data->>'job_order_id')::uuid,(old_data->>'job_order_id')::uuid];
 ELSIF TG_TABLE_NAME='normalized_telemetry_events' THEN
   SELECT array_agg(job_order_id) INTO jobs FROM monitoring_resources WHERE id IN ((row_data->>'resource_id')::uuid,(old_data->>'resource_id')::uuid);
 ELSIF TG_TABLE_NAME='job_step_executions' THEN
   SELECT array_agg(job_order_id) INTO jobs FROM job_order_histories WHERE id IN ((row_data->>'history_id')::uuid,(old_data->>'history_id')::uuid);
 ELSIF TG_TABLE_NAME IN ('pentaho_execution_attempts','pentaho_native_aliases','pentaho_attempt_revisions','pentaho_evidence_reviews','pentaho_evidence_decisions','pentaho_historical_notices') THEN
   SELECT array_agg(job_order_id) INTO jobs FROM monitoring_resources WHERE id IN ((row_data->>'resource_id')::uuid,(old_data->>'resource_id')::uuid);
 ELSIF TG_TABLE_NAME='pentaho_recovery_links' THEN
   SELECT array_agg(job_order_id) INTO jobs FROM job_order_histories WHERE id IN ((row_data->>'failed_history_id')::uuid,(row_data->>'recovery_history_id')::uuid,(old_data->>'failed_history_id')::uuid,(old_data->>'recovery_history_id')::uuid);
 ELSIF TG_TABLE_NAME='pentaho_recovery_decisions' THEN
   SELECT array_agg(h.job_order_id) INTO jobs FROM job_order_histories h JOIN pentaho_recovery_links l ON h.id=l.failed_history_id OR h.id=l.recovery_history_id
     WHERE l.id IN ((row_data->>'link_id')::uuid,(old_data->>'link_id')::uuid);
 ELSIF TG_TABLE_NAME='pipeline_jobs' THEN
   SELECT array_agg(job_order_id) INTO jobs FROM monitoring_resources WHERE id IN ((row_data->>'resource_id')::uuid,(old_data->>'resource_id')::uuid);
 ELSIF TG_TABLE_NAME='pipeline_integrations' THEN
   SELECT array_agg(job_order_id) INTO jobs FROM etl_native_bindings WHERE integration_id=identity;
 ELSIF TG_TABLE_NAME IN ('pipeline_methods','pipeline_connections','pipeline_capabilities') THEN
   SELECT array_agg(b.job_order_id) INTO jobs FROM etl_native_bindings b,
     LATERAL jsonb_array_elements(b.method_snapshot) m
     WHERE m->>(CASE TG_TABLE_NAME WHEN 'pipeline_methods' THEN 'method_id' WHEN 'pipeline_connections' THEN 'connection_id' ELSE 'capability_id' END)=identity::text;
 ELSIF TG_TABLE_NAME='pipeline_associations' THEN
   SELECT array_agg(job_order_id) INTO jobs FROM etl_native_bindings WHERE native_job_id IN ((row_data->>'job_id')::uuid,(old_data->>'job_id')::uuid);
 ELSIF TG_TABLE_NAME='pipeline_sources' THEN
   -- Ordinary lease/checkpoint updates remain usable for unaffected consumers.
   -- A legacy admission touching an opted-in native source is fenced below.
   IF TG_OP='UPDATE' AND (row_data->'identity',row_data->'generation',row_data->'canonical_key',row_data->'legacy_collector_id')
      IS NOT DISTINCT FROM (old_data->'identity',old_data->'generation',old_data->'canonical_key',old_data->'legacy_collector_id') THEN RETURN NEW; END IF;
   SELECT array_agg(b.job_order_id) INTO jobs FROM etl_native_bindings b,
     LATERAL jsonb_array_elements(b.method_snapshot) m WHERE m->>'source_id'=identity::text;
 ELSIF TG_TABLE_NAME='pipeline_evidence' THEN
   -- Unknown aliases cannot safely be classified by an old binary: source-level
   -- batches sharing an opted-in target must use the current authority reader.
   SELECT array_agg(b.job_order_id) INTO jobs FROM etl_native_bindings b,
     LATERAL jsonb_array_elements(b.method_snapshot) m
     WHERE m->>'source_id' IN (row_data->>'source_id',old_data->>'source_id');
 ELSIF TG_TABLE_NAME IN ('collectors','collector_runs') THEN
   SELECT array_agg(job_order_id) INTO jobs FROM monitoring_resources
     WHERE primary_collector_id=CASE WHEN TG_TABLE_NAME='collectors' THEN identity ELSE (row_data->>'collector_id')::uuid END;
 END IF;
 FOR jid IN SELECT DISTINCT j FROM unnest(jobs) j WHERE j IS NOT NULL ORDER BY j LOOP
   -- Same row lock as initial opt-in. A write admitted before opt-in commits
   -- first; a writer arriving later cannot see a false empty registry snapshot.
   PERFORM 1 FROM job_orders WHERE id=jid FOR UPDATE;
   IF EXISTS(SELECT 1 FROM etl_native_bindings WHERE job_order_id=jid) THEN
     RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='OC_ETL_WRITER_VERSION_REQUIRED',
       HINT='Retain schema/history; use authority-aware writer protocol1. Older writers cannot mutate opted-in Jobs.';
   END IF;
 END LOOP;
 IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
END $$;

CREATE FUNCTION etl_authority_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF current_setting('opscontrol.etl_writer_protocol',true) IS DISTINCT FROM '1' THEN
   RAISE EXCEPTION 'OC_ETL_WRITER_VERSION_REQUIRED';
 END IF;
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Authority/qualification provenance is append-only'; END IF;
 IF TG_OP='UPDATE' THEN
   IF TG_TABLE_NAME<>'etl_binding_qualifications' THEN RAISE EXCEPTION 'Authority provenance is append-only'; END IF;
   IF OLD.valid_until IS NOT NULL OR NEW.valid_until IS NULL
       OR (to_jsonb(NEW)-'valid_until') IS DISTINCT FROM (to_jsonb(OLD)-'valid_until') THEN
      RAISE EXCEPTION 'Qualification allows only first validity closure';
   END IF;
 END IF;
 IF TG_OP='INSERT' AND TG_TABLE_NAME='etl_binding_qualifications' THEN
 IF NOT EXISTS (
   SELECT 1 FROM etl_native_bindings b JOIN etl_native_attestations a ON a.id=NEW.attestation_id
   WHERE b.id=NEW.binding_id AND b.organization_id=NEW.organization_id
     AND a.organization_id=NEW.organization_id AND a.resource_id=b.resource_id
     AND a.target_key=NEW.target_key AND b.job_order_id=NEW.job_order_id
     AND a.envelope->'body'->>'assurance'='PROVIDER_QUALIFIED'
     AND a.expires_at>clock_timestamp()
     AND NOT EXISTS(SELECT 1 FROM etl_authority_revocations WHERE attestation_id=a.id)
 ) THEN RAISE EXCEPTION 'Qualified ownership requires current scoped authority'; END IF;
 END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION etl_binding_qualified() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.state='CONFIRMED' AND NOT EXISTS (
   SELECT 1 FROM etl_binding_qualifications q JOIN etl_native_attestations a ON a.id=q.attestation_id
   WHERE q.binding_id=NEW.id AND q.organization_id=NEW.organization_id
     AND q.job_order_id=NEW.job_order_id AND q.target_key=a.target_key
     AND q.valid_until IS NOT DISTINCT FROM NEW.valid_until
     AND (NEW.valid_until IS NOT NULL OR (a.expires_at>clock_timestamp()
       AND NOT EXISTS(SELECT 1 FROM etl_authority_revocations WHERE attestation_id=a.id)))
 ) THEN RAISE EXCEPTION 'Confirmed binding requires immutable authority qualification'; END IF;
 RETURN NULL;
END $$;

CREATE FUNCTION etl_receipt_authority() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS (
   SELECT 1 FROM etl_binding_qualifications q JOIN etl_native_attestations a ON a.id=q.attestation_id
   WHERE q.binding_id=NEW.binding_id AND q.organization_id=NEW.organization_id
     AND a.expires_at>clock_timestamp()
     AND NOT EXISTS(SELECT 1 FROM etl_authority_revocations WHERE attestation_id=a.id)
 ) THEN RAISE EXCEPTION 'Receipt authority expired, revoked or unqualified before commit'; END IF;
 RETURN NULL;
END $$;
"""
