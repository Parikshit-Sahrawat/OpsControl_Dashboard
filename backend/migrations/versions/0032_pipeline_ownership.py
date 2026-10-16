"""Add lossless multi-job integration/source ownership after V1.5."""

from alembic import op
import sqlalchemy as sa

revision = "0032_pipeline_ownership"
down_revision = "0031_in_app_notifications"
branch_labels = None
depends_on = None

STATEMENTS = [
    "\nCREATE TABLE pipeline_sources (\n\tmethod_type VARCHAR(30) NOT NULL, \n\tcanonical_key VARCHAR(64) NOT NULL, \n\tidentity JSONB NOT NULL, \n\tgeneration UUID NOT NULL, \n\tfence BIGINT NOT NULL, \n\towner_id UUID, \n\tlease_mode VARCHAR(20) NOT NULL, \n\tnext_run_at TIMESTAMP WITH TIME ZONE, \n\tlease_until TIMESTAMP WITH TIME ZONE, \n\tlive_checkpoint JSONB NOT NULL, \n\trecovery_checkpoint JSONB NOT NULL, \n\tcontinuity_validated BOOLEAN NOT NULL, \n\thealth VARCHAR(30) NOT NULL, \n\tlast_received_at TIMESTAMP WITH TIME ZONE, \n\tlast_observed_at TIMESTAMP WITH TIME ZONE, \n\tlegacy_collector_id UUID, \n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\trevision INTEGER NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_pipeline_canonical_source UNIQUE (organization_id, canonical_key), \n\tCONSTRAINT ck_pipeline_fence CHECK (fence >= 0), \n\tCONSTRAINT uq_pipeline_source_scope UNIQUE (organization_id, id), \n\tUNIQUE (legacy_collector_id), \n\tFOREIGN KEY(legacy_collector_id) REFERENCES collectors (id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n)\n\n",
    "CREATE INDEX ix_pipeline_sources_organization_id ON pipeline_sources (organization_id)",
    "\nCREATE TABLE pipeline_evidence (\n\tsource_id UUID NOT NULL, \n\tgeneration UUID NOT NULL, \n\texternal_key VARCHAR(500) NOT NULL, \n\tnative_job_id VARCHAR(500), \n\tpayload JSONB NOT NULL, \n\toutcome VARCHAR(30) NOT NULL, \n\tobserved_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\trevision INTEGER NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT fk_pipeline_evidence_scope FOREIGN KEY(organization_id, source_id) REFERENCES pipeline_sources (organization_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT uq_pipeline_evidence_identity UNIQUE (source_id, generation, external_key), \n\tCONSTRAINT uq_pipeline_evidence_scope UNIQUE (organization_id, id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n)\n\n",
    "CREATE INDEX ix_pipeline_evidence_generation ON pipeline_evidence (generation)",
    "CREATE INDEX ix_pipeline_evidence_organization_id ON pipeline_evidence (organization_id)",
    "CREATE INDEX ix_pipeline_evidence_source_id ON pipeline_evidence (source_id)",
    "\nCREATE TABLE pipeline_holds (\n\tsource_id UUID NOT NULL, \n\tkind VARCHAR(20) NOT NULL, \n\treference VARCHAR(120) NOT NULL, \n\tactor_id UUID, \n\treleased_at TIMESTAMP WITH TIME ZONE, \n\treleased_by UUID, \n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\trevision INTEGER NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT fk_pipeline_hold_scope FOREIGN KEY(organization_id, source_id) REFERENCES pipeline_sources (organization_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT uq_pipeline_hold_reference UNIQUE (source_id, kind, reference), \n\tCONSTRAINT ck_pipeline_hold_kind CHECK (kind IN ('INTEGRATION','MANUAL','LEGAL','CONTINUITY')), \n\tCONSTRAINT uq_pipeline_hold_scope UNIQUE (organization_id, id), \n\tFOREIGN KEY(actor_id) REFERENCES users (id), \n\tFOREIGN KEY(released_by) REFERENCES users (id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n)\n\n",
    "CREATE INDEX ix_pipeline_holds_organization_id ON pipeline_holds (organization_id)",
    "CREATE INDEX ix_pipeline_holds_source_id ON pipeline_holds (source_id)",
    "\nCREATE TABLE pipeline_integrations (\n\tname VARCHAR(200) NOT NULL, \n\tplatform VARCHAR(30) NOT NULL, \n\tenvironment VARCHAR(20) NOT NULL, \n\tvm_resource_id UUID, \n\tconfiguration JSONB NOT NULL, \n\tstage INTEGER NOT NULL, \n\tenabled BOOLEAN NOT NULL, \n\tdeleted_at TIMESTAMP WITH TIME ZONE, \n\towner_id UUID NOT NULL, \n\tlast_discovery_at TIMESTAMP WITH TIME ZONE, \n\tlast_redetection_at TIMESTAMP WITH TIME ZONE, \n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\trevision INTEGER NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT fk_pipeline_vm_scope FOREIGN KEY(organization_id, vm_resource_id) REFERENCES monitoring_resources (organization_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT ck_pipeline_stage CHECK (stage BETWEEN 1 AND 8), \n\tCONSTRAINT ck_pipeline_environment CHECK (environment IN ('PROD','QA','TEST','DEV','SANDBOX')), \n\tCONSTRAINT uq_pipeline_integration_scope UNIQUE (organization_id, id), \n\tFOREIGN KEY(owner_id) REFERENCES users (id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n)\n\n",
    "CREATE INDEX ix_pipeline_integrations_organization_id ON pipeline_integrations (organization_id)",
    "\nCREATE TABLE pipeline_capabilities (\n\tintegration_id UUID NOT NULL, \n\tplatform_version VARCHAR(100) NOT NULL, \n\tedition VARCHAR(100) NOT NULL, \n\tdeployment_type VARCHAR(50) NOT NULL, \n\tdefinition JSONB NOT NULL, \n\tcompatibility VARCHAR(20) NOT NULL, \n\tevidence_status VARCHAR(25) NOT NULL, \n\tverification_evidence_id UUID, \n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\trevision INTEGER NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT fk_pipeline_capability_scope FOREIGN KEY(organization_id, integration_id) REFERENCES pipeline_integrations (organization_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT fk_pipeline_capability_proof_scope FOREIGN KEY(organization_id, verification_evidence_id) REFERENCES pipeline_evidence (organization_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT ck_pipeline_compatibility CHECK (compatibility IN ('SUPPORTED','CONDITIONAL','UNSUPPORTED','UNVERIFIED')), \n\tCONSTRAINT ck_pipeline_capability_evidence CHECK (evidence_status IN ('DOCUMENTED','RUNTIME_VERIFIED','UNKNOWN')), \n\tCONSTRAINT uq_pipeline_capability_scope UNIQUE (organization_id, id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n)\n\n",
    "CREATE INDEX ix_pipeline_capabilities_organization_id ON pipeline_capabilities (organization_id)",
    "\nCREATE TABLE pipeline_connections (\n\tintegration_id UUID NOT NULL, \n\tversion INTEGER NOT NULL, \n\tconfiguration JSONB NOT NULL, \n\tchecksum VARCHAR(64) NOT NULL, \n\tactive BOOLEAN NOT NULL, \n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\trevision INTEGER NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT fk_pipeline_connection_scope FOREIGN KEY(organization_id, integration_id) REFERENCES pipeline_integrations (organization_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT uq_pipeline_connection_version UNIQUE (integration_id, version), \n\tCONSTRAINT uq_pipeline_connection_scope UNIQUE (organization_id, id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n)\n\n",
    "CREATE INDEX ix_pipeline_connections_organization_id ON pipeline_connections (organization_id)",
    "\nCREATE TABLE pipeline_jobs (\n\tintegration_id UUID NOT NULL, \n\tnative_id VARCHAR(500) NOT NULL, \n\tname VARCHAR(200) NOT NULL, \n\torigin VARCHAR(20) NOT NULL, \n\tselected BOOLEAN NOT NULL, \n\tquarantined BOOLEAN NOT NULL, \n\tstale_since TIMESTAMP WITH TIME ZONE, \n\tlast_seen_at TIMESTAMP WITH TIME ZONE, \n\tresource_id UUID, \n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\trevision INTEGER NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT fk_pipeline_job_scope FOREIGN KEY(organization_id, integration_id) REFERENCES pipeline_integrations (organization_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT fk_pipeline_job_resource_scope FOREIGN KEY(organization_id, resource_id) REFERENCES monitoring_resources (organization_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT uq_pipeline_native_job UNIQUE (integration_id, native_id), \n\tCONSTRAINT uq_pipeline_job_scope UNIQUE (organization_id, id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n)\n\n",
    "CREATE INDEX ix_pipeline_jobs_organization_id ON pipeline_jobs (organization_id)",
    "\nCREATE TABLE pipeline_operations (\n\tintegration_id UUID, \n\tsource_id UUID, \n\tkind VARCHAR(30) NOT NULL, \n\tidempotency_key VARCHAR(100) NOT NULL, \n\trequest_hash VARCHAR(64) NOT NULL, \n\tactor_id UUID, \n\treviewer_id UUID, \n\tstate VARCHAR(30) NOT NULL, \n\tconfiguration JSONB NOT NULL, \n\tresult JSONB NOT NULL, \n\tfence BIGINT NOT NULL, \n\towner_id UUID, \n\tattempts INTEGER NOT NULL, \n\tlease_until TIMESTAMP WITH TIME ZONE, \n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\trevision INTEGER NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT fk_pipeline_operation_integration FOREIGN KEY(organization_id, integration_id) REFERENCES pipeline_integrations (organization_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT fk_pipeline_operation_source FOREIGN KEY(organization_id, source_id) REFERENCES pipeline_sources (organization_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT uq_pipeline_operation_idempotency UNIQUE (organization_id, kind, idempotency_key), \n\tCONSTRAINT uq_pipeline_operation_scope UNIQUE (organization_id, id), \n\tFOREIGN KEY(actor_id) REFERENCES users (id), \n\tFOREIGN KEY(reviewer_id) REFERENCES users (id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n)\n\n",
    "CREATE INDEX ix_pipeline_operations_organization_id ON pipeline_operations (organization_id)",
    "\nCREATE TABLE pipeline_methods (\n\tintegration_id UUID NOT NULL, \n\tsource_id UUID NOT NULL, \n\tconnection_id UUID NOT NULL, \n\tcapability_id UUID NOT NULL, \n\tname VARCHAR(200) NOT NULL, \n\ttransport VARCHAR(15) NOT NULL, \n\tconfiguration JSONB NOT NULL, \n\tenabled BOOLEAN NOT NULL, \n\tvalidation VARCHAR(20) NOT NULL, \n\tlast_error VARCHAR(80), \n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\trevision INTEGER NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT fk_method_integration_id FOREIGN KEY(organization_id, integration_id) REFERENCES pipeline_integrations (organization_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT fk_method_source_id FOREIGN KEY(organization_id, source_id) REFERENCES pipeline_sources (organization_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT fk_method_connection_id FOREIGN KEY(organization_id, connection_id) REFERENCES pipeline_connections (organization_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT fk_method_capability_id FOREIGN KEY(organization_id, capability_id) REFERENCES pipeline_capabilities (organization_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT uq_pipeline_method_source UNIQUE (integration_id, source_id), \n\tCONSTRAINT ck_pipeline_transport CHECK (transport IN ('BACKEND','AGENT')), \n\tCONSTRAINT uq_pipeline_method_scope UNIQUE (organization_id, id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n)\n\n",
    "CREATE INDEX ix_pipeline_methods_capability_id ON pipeline_methods (capability_id)",
    "CREATE INDEX ix_pipeline_methods_connection_id ON pipeline_methods (connection_id)",
    "CREATE INDEX ix_pipeline_methods_organization_id ON pipeline_methods (organization_id)",
    "CREATE INDEX ix_pipeline_methods_source_id ON pipeline_methods (source_id)",
    "\nCREATE TABLE pipeline_associations (\n\tmethod_id UUID NOT NULL, \n\tjob_id UUID NOT NULL, \n\tgeneration UUID NOT NULL, \n\tconfirmed_by UUID NOT NULL, \n\tid UUID NOT NULL, \n\torganization_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\trevision INTEGER NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT fk_association_method_scope FOREIGN KEY(organization_id, method_id) REFERENCES pipeline_methods (organization_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT fk_association_job_scope FOREIGN KEY(organization_id, job_id) REFERENCES pipeline_jobs (organization_id, id) ON DELETE RESTRICT, \n\tCONSTRAINT uq_pipeline_association UNIQUE (method_id, job_id, generation), \n\tCONSTRAINT uq_pipeline_association_scope UNIQUE (organization_id, id), \n\tFOREIGN KEY(confirmed_by) REFERENCES users (id), \n\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n)\n\n",
    "CREATE INDEX ix_pipeline_associations_job_id ON pipeline_associations (job_id)",
    "CREATE INDEX ix_pipeline_associations_method_id ON pipeline_associations (method_id)",
    "CREATE INDEX ix_pipeline_associations_organization_id ON pipeline_associations (organization_id)",
]
TABLES = [
    "pipeline_sources",
    "pipeline_evidence",
    "pipeline_holds",
    "pipeline_integrations",
    "pipeline_capabilities",
    "pipeline_connections",
    "pipeline_jobs",
    "pipeline_operations",
    "pipeline_methods",
    "pipeline_associations",
]


def upgrade():
    for statement in STATEMENTS:
        op.execute(sa.text(statement))


def downgrade():
    db = op.get_bind()
    for table in TABLES:
        if db.scalar(sa.text("SELECT EXISTS(SELECT 1 FROM " + table + ")")):
            raise RuntimeError(
                "V1.6 identities/evidence/checkpoints exist; retain additive schema or restore verified backup"
            )
    for table in reversed(TABLES):
        op.drop_table(table)
