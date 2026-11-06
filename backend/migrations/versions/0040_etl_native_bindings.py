"""Add temporal native binding claims; no inferred historical backfill."""

from alembic import op

revision = "0040_etl_native_bindings"
down_revision = "0039_etl_workflow_foundation"
branch_labels = None
depends_on = None

DDL = [
    "\nCREATE TABLE etl_native_bindings (\n\tworkflow_id UUID NOT NULL, \n\tjob_order_id UUID NOT NULL, \n\tresource_id UUID NOT NULL, \n\tnative_job_id UUID NOT NULL, \n\tintegration_id UUID NOT NULL, \n\tprevious_id UUID, \n\tidentity_key VARCHAR(64) NOT NULL, \n\tidentity_snapshot JSONB NOT NULL, \n\tmethod_snapshot JSONB NOT NULL, \n\tstate VARCHAR(20) NOT NULL, \n\tvalid_from TIMESTAMP WITH TIME ZONE NOT NULL, \n\tvalid_until TIMESTAMP WITH TIME ZONE, \n\tactor_id UUID NOT NULL, \n\treason VARCHAR(500) NOT NULL, \n\toperation_id UUID NOT NULL, \n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\trevision INTEGER NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT fk_binding_resource FOREIGN KEY(organization_id, resource_id) REFERENCES monitoring_resources (organization_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT fk_binding_native FOREIGN KEY(organization_id, native_job_id) REFERENCES pipeline_jobs (organization_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT fk_binding_integration FOREIGN KEY(organization_id, integration_id) REFERENCES pipeline_integrations (organization_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT fk_binding_operation FOREIGN KEY(organization_id, operation_id) REFERENCES pipeline_operations (organization_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT fk_binding_previous FOREIGN KEY(organization_id, previous_id) REFERENCES etl_native_bindings (organization_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT ck_binding_state CHECK (state IN ('STAGED','CONFIRMED','RETIRED')), \n\tCONSTRAINT ck_binding_validity CHECK (valid_until IS NULL OR valid_until >= valid_from), \n\tCONSTRAINT uq_etl_native_binding_scope UNIQUE (organization_id, id), \n\tFOREIGN KEY(workflow_id) REFERENCES etl_workflows (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(job_order_id) REFERENCES job_orders (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(actor_id) REFERENCES users (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n)\n\n",
    "CREATE INDEX ix_etl_native_bindings_organization_id ON etl_native_bindings (organization_id)",
    "CREATE UNIQUE INDEX uq_binding_current_job ON etl_native_bindings (job_order_id) WHERE valid_until IS NULL",
    "CREATE UNIQUE INDEX uq_binding_current_target ON etl_native_bindings (organization_id, identity_key) WHERE valid_until IS NULL AND state <> 'RETIRED'",
    "CREATE UNIQUE INDEX uq_binding_successor ON etl_native_bindings (previous_id)",
    "\nCREATE TABLE etl_binding_receipts (\n\tbinding_id UUID NOT NULL, \n\tevidence_id UUID NOT NULL, \n\tpayload_sha256 VARCHAR(64) NOT NULL, \n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\trevision INTEGER NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT fk_binding_receipt_binding FOREIGN KEY(organization_id, binding_id) REFERENCES etl_native_bindings (organization_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT fk_binding_receipt_evidence FOREIGN KEY(organization_id, evidence_id) REFERENCES pipeline_evidence (organization_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT uq_etl_binding_receipt_scope UNIQUE (organization_id, id), \n\tUNIQUE (evidence_id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n)\n\n",
    "CREATE INDEX ix_etl_binding_receipts_organization_id ON etl_binding_receipts (organization_id)",
]


def upgrade():
    for statement in DDL:
        op.execute(statement)
    op.execute(INTEGRITY)


def downgrade():
    # Central online preflight locks/checks both tables before any DDL.
    for table in (
        "job_orders",
        "pipeline_jobs",
        "monitoring_resources",
        "pipeline_integrations",
        "etl_workflows",
    ):
        op.execute(f"DROP TRIGGER etl_binding_parent_identity ON {table}")
    op.execute("DROP TABLE etl_binding_receipts")
    op.execute("DROP TABLE etl_native_bindings")
    op.execute("DROP FUNCTION etl_binding_integrity()")
    op.execute("DROP FUNCTION etl_binding_chain()")
    op.execute("DROP FUNCTION etl_binding_parent_identity()")


INTEGRITY = r"""
CREATE FUNCTION etl_binding_integrity() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE m jsonb;
BEGIN
 IF TG_OP = 'DELETE' THEN
   RAISE EXCEPTION 'ETL binding provenance is append-only; retire instead of deleting';
 END IF;
 IF TG_OP = 'UPDATE' THEN
   IF TG_TABLE_NAME = 'etl_binding_receipts' THEN
     RAISE EXCEPTION 'Binding receipts are immutable';
   END IF;
   IF OLD.valid_until IS NOT NULL
      OR NEW.valid_until IS NULL
      OR (to_jsonb(NEW) - 'valid_until') IS DISTINCT FROM (to_jsonb(OLD) - 'valid_until') THEN
      RAISE EXCEPTION 'ETL binding identity/snapshots are immutable; only first validity closure allowed';
   END IF;
   RETURN NEW;
 END IF;
 IF TG_TABLE_NAME = 'etl_native_bindings' THEN
   IF NEW.identity_snapshot->>'schema' <> 'NATIVE_AUTHORITY_CLAIM_V1'
      OR NEW.identity_snapshot->>'object_kind' <> 'JOB'
      OR NOT (NEW.identity_snapshot ?& ARRAY['platform','environment','authority_claim','native_id','schema','object_kind'])
      OR NEW.identity_snapshot->>'authority_claim' !~ '^[A-Za-z0-9._:/@-]{3,200}$' THEN
     RAISE EXCEPTION 'Invalid canonical native identity claim';
   END IF;
   IF NEW.previous_id IS NULL AND EXISTS (SELECT 1 FROM etl_native_bindings b WHERE b.job_order_id=NEW.job_order_id) THEN
     RAISE EXCEPTION 'Historical Job cannot start a second binding chain';
   END IF;
   IF NOT EXISTS (
     SELECT 1 FROM job_orders j JOIN etl_workflows w ON w.id=j.workflow_id
     JOIN monitoring_resources r ON r.job_order_id=j.id
     JOIN pipeline_jobs n ON n.id=NEW.native_job_id AND n.resource_id=r.id
     JOIN pipeline_integrations i ON i.id=n.integration_id
     WHERE j.id=NEW.job_order_id AND w.id=NEW.workflow_id AND r.id=NEW.resource_id
       AND i.id=NEW.integration_id AND j.organization_id=NEW.organization_id
       AND w.organization_id=NEW.organization_id AND r.organization_id=NEW.organization_id
       AND n.organization_id=NEW.organization_id AND i.organization_id=NEW.organization_id
       AND j.environment=w.environment AND r.environment=w.environment AND i.environment=w.environment
       AND NEW.identity_snapshot->>'environment'=w.environment
       AND NEW.identity_snapshot->>'platform'=i.platform
       AND NEW.identity_snapshot->>'native_id'=n.native_id AND r.domain='ETL'
   ) THEN RAISE EXCEPTION 'ETL binding ownership/environment mismatch'; END IF;
   IF NEW.previous_id IS NOT NULL AND NOT EXISTS (
     SELECT 1 FROM etl_native_bindings b WHERE b.id=NEW.previous_id
       AND b.organization_id=NEW.organization_id AND b.job_order_id=NEW.job_order_id
       AND b.workflow_id=NEW.workflow_id AND b.resource_id=NEW.resource_id
       AND b.native_job_id=NEW.native_job_id AND b.integration_id=NEW.integration_id
       AND b.identity_key=NEW.identity_key AND b.valid_until=NEW.valid_from
   ) THEN RAISE EXCEPTION 'Binding successor cannot retarget or reparent history'; END IF;
   IF jsonb_typeof(NEW.method_snapshot) <> 'array' OR jsonb_array_length(NEW.method_snapshot)=0 THEN
     RAISE EXCEPTION 'Binding requires explicit collection method snapshots';
   END IF;
   IF NEW.state <> 'RETIRED' THEN
     FOR m IN SELECT * FROM jsonb_array_elements(NEW.method_snapshot) LOOP
       IF NOT EXISTS (
         SELECT 1 FROM pipeline_methods pm JOIN pipeline_sources s ON s.id=pm.source_id
         WHERE pm.id=(m->>'method_id')::uuid AND pm.integration_id=NEW.integration_id
          AND pm.organization_id=NEW.organization_id AND s.organization_id=NEW.organization_id
          AND pm.source_id=(m->>'source_id')::uuid AND s.generation=(m->>'generation')::uuid
          AND s.fence=(m->>'fence')::bigint AND pm.revision=(m->>'revision')::integer
          AND pm.connection_id=(m->>'connection_id')::uuid AND pm.capability_id=(m->>'capability_id')::uuid
       ) THEN RAISE EXCEPTION 'Binding method snapshot is stale or out of scope'; END IF;
     END LOOP;
   END IF;
 ELSE
   IF NOT EXISTS (
     SELECT 1 FROM etl_native_bindings b JOIN pipeline_evidence e ON e.id=NEW.evidence_id
     WHERE b.id=NEW.binding_id AND b.organization_id=NEW.organization_id
       AND e.organization_id=NEW.organization_id AND b.state='CONFIRMED'
       AND e.created_at >= b.valid_from AND (b.valid_until IS NULL OR e.created_at < b.valid_until)
       AND e.native_job_id=b.identity_snapshot->>'native_id' AND e.outcome='ACCEPTED'
       AND EXISTS (SELECT 1 FROM jsonb_array_elements(b.method_snapshot) m
         WHERE m->>'source_id'=e.source_id::text AND m->>'generation'=e.generation::text)
   ) THEN RAISE EXCEPTION 'Receipt cannot claim unverified binding provenance'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER etl_binding_integrity BEFORE INSERT OR UPDATE OR DELETE ON etl_native_bindings
 FOR EACH ROW EXECUTE FUNCTION etl_binding_integrity();
CREATE TRIGGER etl_binding_receipt_integrity BEFORE INSERT OR UPDATE OR DELETE ON etl_binding_receipts
 FOR EACH ROW EXECUTE FUNCTION etl_binding_integrity();

CREATE UNIQUE INDEX uq_binding_current_claim_tuple ON etl_native_bindings
 (organization_id, (identity_snapshot->>'platform'), (identity_snapshot->>'environment'),
 (identity_snapshot->>'authority_claim'), (identity_snapshot->>'object_kind'), (identity_snapshot->>'native_id'))
 WHERE valid_until IS NULL AND state <> 'RETIRED';
CREATE FUNCTION etl_binding_chain() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF EXISTS (SELECT 1 FROM etl_native_bindings b WHERE b.job_order_id=NEW.job_order_id
   AND b.valid_until IS NOT NULL AND NOT EXISTS (SELECT 1 FROM etl_native_bindings n
     WHERE n.previous_id=b.id AND n.valid_from=b.valid_until)) THEN
   RAISE EXCEPTION 'Binding closure requires atomic successor; rollback the transaction';
 END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER etl_binding_chain AFTER INSERT OR UPDATE ON etl_native_bindings
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION etl_binding_chain();
CREATE FUNCTION etl_binding_parent_identity() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_TABLE_NAME='job_orders' THEN
   IF (NEW.organization_id,NEW.environment,NEW.workflow_id) IS DISTINCT FROM (OLD.organization_id,OLD.environment,OLD.workflow_id)
     AND EXISTS (SELECT 1 FROM etl_native_bindings WHERE job_order_id=OLD.id) THEN
      RAISE EXCEPTION 'Binding history prevents Job ownership changes'; END IF;
 ELSIF TG_TABLE_NAME='pipeline_jobs' THEN
   IF (NEW.organization_id,NEW.integration_id,NEW.resource_id,NEW.native_id) IS DISTINCT FROM (OLD.organization_id,OLD.integration_id,OLD.resource_id,OLD.native_id)
     AND EXISTS (SELECT 1 FROM etl_native_bindings WHERE native_job_id=OLD.id) THEN
      RAISE EXCEPTION 'Binding history prevents native identity changes'; END IF;
 ELSIF TG_TABLE_NAME='monitoring_resources' THEN
   IF (NEW.organization_id,NEW.environment,NEW.job_order_id,NEW.domain) IS DISTINCT FROM (OLD.organization_id,OLD.environment,OLD.job_order_id,OLD.domain)
     AND EXISTS (SELECT 1 FROM etl_native_bindings WHERE resource_id=OLD.id) THEN
      RAISE EXCEPTION 'Binding history prevents resource reassignment'; END IF;
 ELSIF TG_TABLE_NAME='etl_workflows' THEN
   IF (NEW.organization_id,NEW.environment) IS DISTINCT FROM (OLD.organization_id,OLD.environment)
     AND EXISTS (SELECT 1 FROM etl_native_bindings WHERE workflow_id=OLD.id) THEN
      RAISE EXCEPTION 'Binding history prevents Workflow ownership changes'; END IF;
 ELSIF TG_TABLE_NAME='pipeline_integrations' THEN
   IF (NEW.organization_id,NEW.environment,NEW.platform) IS DISTINCT FROM (OLD.organization_id,OLD.environment,OLD.platform)
     AND EXISTS (SELECT 1 FROM etl_native_bindings WHERE integration_id=OLD.id) THEN
      RAISE EXCEPTION 'Binding history prevents integration reassignment'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER etl_binding_parent_identity BEFORE UPDATE ON etl_workflows FOR EACH ROW EXECUTE FUNCTION etl_binding_parent_identity();
CREATE TRIGGER etl_binding_parent_identity BEFORE UPDATE ON job_orders FOR EACH ROW EXECUTE FUNCTION etl_binding_parent_identity();
CREATE TRIGGER etl_binding_parent_identity BEFORE UPDATE ON pipeline_jobs FOR EACH ROW EXECUTE FUNCTION etl_binding_parent_identity();
CREATE TRIGGER etl_binding_parent_identity BEFORE UPDATE ON monitoring_resources FOR EACH ROW EXECUTE FUNCTION etl_binding_parent_identity();
CREATE TRIGGER etl_binding_parent_identity BEFORE UPDATE ON pipeline_integrations FOR EACH ROW EXECUTE FUNCTION etl_binding_parent_identity();
"""
