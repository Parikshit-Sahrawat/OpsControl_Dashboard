"""Protect migration-defined uniqueness, query indexes and PostgreSQL types.

The owned PostgreSQL acceptance fixture additionally requires a zero-drift full
Alembic comparison. These checks cover index predicates and ordering, which an
autogeneration comparison alone does not completely validate.
"""

import unittest

from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, dialect
from sqlalchemy.schema import CreateIndex

from app.models import entities
from app.security import models
from app.services import rule_models
from app.worker import remote_models


class SchemaContractTests(unittest.TestCase):
    def index(self, model, name):
        indexes = {index.name: index for index in model.__table__.indexes}
        self.assertIn(name, indexes)
        return indexes[name]

    def ddl(self, model, name):
        return str(CreateIndex(self.index(model, name)).compile(dialect=dialect()))

    def test_unique_constraints_remain_separate_from_lookup_indexes(self):
        for model, column, constraint, index in (
            (
                models.AccessSession,
                "token_hash",
                "access_sessions_token_hash_key",
                "ix_access_sessions_token_hash",
            ),
            (
                entities.CorrelationRecord,
                "history_id",
                "correlation_records_history_id_key",
                "ix_correlation_records_history_id",
            ),
        ):
            with self.subTest(table=model.__tablename__):
                constraints = {
                    item.name: list(item.columns.keys())
                    for item in model.__table__.constraints
                    if isinstance(item, UniqueConstraint)
                }
                self.assertEqual(constraints[constraint], [column])
                self.assertFalse(self.index(model, index).unique)

    def test_partial_indexes_preserve_alert_and_scheduler_semantics(self):
        self.assertEqual(
            self.ddl(entities.AlertState, "uq_alert_states_open_rule"),
            "CREATE UNIQUE INDEX uq_alert_states_open_rule ON alert_states (alert_rule_id) WHERE status = 'OPEN'",
        )
        self.assertEqual(
            self.ddl(entities.Collector, "ix_collectors_due_local"),
            "CREATE INDEX ix_collectors_due_local ON collectors (next_run_at, id) WHERE enabled AND remote_worker_id IS NULL",
        )
        # Provider execution IDs are unique when non-null; PostgreSQL permits
        # multiple missing IDs for existing synthetic/legacy executions.
        self.assertEqual(
            self.ddl(entities.JobOrderHistory, "uq_etl_job_provider_execution"),
            "CREATE UNIQUE INDEX uq_etl_job_provider_execution ON job_order_histories (job_order_id, provider_execution_id)",
        )

    def test_latest_evidence_indexes_have_deterministic_descending_order(self):
        for model, name, timestamp in (
            (entities.CollectorRun, "ix_collector_runs_latest", "started_at"),
            (
                entities.InfrastructureEvidence,
                "ix_infra_evidence_latest",
                "observed_at",
            ),
        ):
            with self.subTest(table=model.__tablename__):
                self.assertIn(
                    f"(collector_id, {timestamp} DESC, id DESC)", self.ddl(model, name)
                )

    def test_named_lookup_and_chronological_indexes_match_migrations(self):
        for model, name, columns in (
            (
                entities.AlertNotificationDelivery,
                "ix_alert_notification_pending",
                ["status", "created_at"],
            ),
            (
                entities.MonitoringTemplateAttachment,
                "ix_template_attachment_data_source_id",
                ["data_source_id"],
            ),
            (
                entities.MonitoringTemplateAttachment,
                "ix_template_attachment_template_id",
                ["template_id"],
            ),
            (remote_models.RemoteProbeJob, "ix_remote_job_org_id", ["organization_id"]),
            (models.SecurityAuditEvent, "ix_security_audit_actor_id", ["actor_id"]),
            (
                models.SecurityAuditEvent,
                "ix_security_audit_organization_id",
                ["organization_id"],
            ),
            (
                models.SecurityAuditEvent,
                "ix_security_audit_occurred_at",
                ["occurred_at"],
            ),
            (
                models.SecurityAuditEvent,
                "ix_security_audit_occurred",
                ["occurred_at", "id"],
            ),
        ):
            with self.subTest(index=name):
                index = self.index(model, name)
                self.assertEqual(list(index.columns.keys()), columns)
                self.assertFalse(index.unique)
        self.assertNotIn(
            "ix_metric_samples_organization_id",
            {i.name for i in entities.MetricSample.__table__.indexes},
        )
        self.assertEqual(
            list(
                self.index(
                    entities.MetricSample, "ix_metric_samples_org_observed"
                ).columns.keys()
            ),
            ["organization_id", "observed_at"],
        )

    def test_jsonb_contract_without_converting_existing_json_columns(self):
        for model, column in (
            (rule_models.MonitoringRuleVersion, "definition"),
            (rule_models.MonitoringActivation, "details"),
            (remote_models.RemoteProbeJob, "config_snapshot"),
            (remote_models.RemoteProbeEvidence, "result"),
            (models.WorkerIdentity, "allowed_hosts"),
            (models.WorkerIdentity, "allowed_cidrs"),
        ):
            with self.subTest(table=model.__tablename__, column=column):
                self.assertIsInstance(model.__table__.c[column].type, JSONB)
        self.assertNotIsInstance(
            entities.MetricSample.__table__.c.dimensions.type, JSONB
        )

    def test_template_version_fk_preserves_existing_cascade(self):
        (fk,) = entities.MonitoringTemplateVersion.__table__.c.template_id.foreign_keys
        self.assertEqual(fk.target_fullname, "monitoring_templates.id")
        self.assertEqual(fk.ondelete, "CASCADE")


if __name__ == "__main__":
    unittest.main()
