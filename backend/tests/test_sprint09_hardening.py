"""Scoped real-PostgreSQL regressions for bounded operational projections."""

import os
import unittest
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import event
from fastapi import HTTPException
from app.unified import api
from app.data_pipelines import api as pipelines
from app.native_incidents import api as incidents
from app.models import JobStepExecution, JobOrder
from app.unified.models import ExpectedExecutionWindow, MonitoringResource
from app.unified.pentaho_models import PentahoAlias
from app.data_pipelines.models import PipelineJob
from tests import test_sprint08_rbac as rbac
from tests import test_pentaho_incident_r1 as native


@unittest.skipUnless(
    os.getenv("OPSCONTROL_V16_ACCEPTANCE") == "1", "Owned PostgreSQL required"
)
class Sprint09Hardening(unittest.TestCase):
    setUp = native.PentahoIncidentTests.setUp
    raw = native.PentahoIncidentTests.raw
    emit = native.PentahoIncidentTests.emit
    attempts = native.PentahoIncidentTests.attempts
    grant = native.PentahoIncidentTests.grant
    failure = native.PentahoIncidentTests.failure
    principal = rbac.Sprint08RBAC.principal
    access = rbac.Sprint08RBAC.access

    def test_worker_restart_resumes_retained_recovery_without_reprocessing(self):
        from app.db.session import SessionLocal
        from app.data_pipelines import service as service
        from app.data_pipelines.models import PipelineSource, PipelineOperation
        from app.unified import pentaho_replay as replay

        first, _ = self.emit(self.raw(invocation="restart-a", run="restart-a"))
        self.emit(self.raw(invocation="restart-b", run="restart-b"))
        self.grant(self.user, ["etl.replay", "etl.configure", "etl.view"])
        stamp = datetime.fromisoformat(first.payload["timestamp"])
        op = service.plan_recovery(
            self.db,
            self.source,
            stamp - timedelta(seconds=1),
            stamp + timedelta(seconds=1),
            self.user.id,
            uuid.uuid4().hex,
            mode=replay.MODE,
        )
        if op.state == "APPROVAL_REQUIRED":
            self.grant(self.reviewer, ["etl.approve_replay"])
            op.reviewer_id = self.reviewer.id
            op.state = "APPROVED"
        self.source.next_run_at = service.clock(self.db) + timedelta(minutes=1)
        self.db.commit()
        source_id, op_id = self.source.id, op.id
        checkpoint = dict(self.source.live_checkpoint)
        ticket = service.acquire(self.db, source_id, uuid.uuid4())
        self.db.commit()
        self.assertEqual(replay.run_batch(self.db, self.source, op, ticket, limit=1), 1)
        self.db.commit()
        cursor = dict(op.result["reconciliation_cursor"])
        self.db.close()
        # New Session and source/operation objects represent lost process memory.
        with SessionLocal() as restarted:
            source, operation = restarted.get(PipelineSource, source_id), restarted.get(
                PipelineOperation, op_id
            )
            self.assertEqual(operation.result["reconciliation_cursor"], cursor)
            ticket = service.acquire(restarted, source_id, uuid.uuid4())
            restarted.commit()
            self.assertEqual(
                replay.run_batch(restarted, source, operation, ticket, limit=1), 1
            )
            restarted.commit()
            self.assertEqual(operation.state, "COMPLETE")
            self.assertEqual(operation.result["processed"], 2)
            self.assertEqual(source.live_checkpoint, checkpoint)
            # A completed operation cannot be re-executed after another restart.
            ticket = service.acquire(restarted, source_id, uuid.uuid4())
            restarted.commit()
            with self.assertRaises(service.PipelineError) as denied:
                replay.run_batch(restarted, source, operation, ticket, limit=1)
            self.assertEqual(denied.exception.code, "RECOVERY_NOT_ELIGIBLE")
            restarted.rollback()

    def test_inventory_projection_queries_are_constant_for_a_page(self):
        self.access()
        for i in range(25):
            job = JobOrder(
                id=uuid.uuid4(),
                organization_id=self.org.id,
                name=str(i),
                monitoring_enabled=False,
            )
            self.db.add(job)
            self.db.flush()
            self.db.add(
                MonitoringResource(
                    organization_id=self.org.id,
                    domain="ETL",
                    environment="TEST",
                    name=str(i),
                    job_order_id=job.id,
                    configuration={},
                )
            )
        self.db.commit()
        calls = []
        with self.principal(("resources.view",)) as (_, db):

            def count(*args):
                calls.append(1)

            event.listen(db.bind, "before_cursor_execute", count)
            try:
                result = api.inventory("ETL", [], None, "", None, 50, 0, db)
            finally:
                event.remove(db.bind, "before_cursor_execute", count)
            self.assertEqual(len(calls), 4)  # count/page + parameters/customer batch
            self.assertEqual(result["total"], 26)
            self.assertTrue(
                all(
                    r["inherited"]["customer"] == self.org.name for r in result["items"]
                )
            )

    def test_outcome_filter_keeps_pending_retry_nonterminal(self):
        self.access()
        self.emit(
            self.raw(
                invocation="pending", run="pending", outcome="FAILED", retry="PENDING"
            )
        )
        self.emit(self.raw(invocation="failed", run="failed", outcome="FAILED"))
        with self.principal(("etl.view",)) as (_, db):
            failed = api.executions(self.resource.id, 20, 0, "FAILED", db)
            pending = api.executions(self.resource.id, 20, 0, "WAITING_FOR_RETRY", db)
            self.assertEqual(failed["total"], 1)
            self.assertEqual(pending["total"], 1)
            self.assertEqual(
                pending["items"][0]["pentaho_lifecycle"], "WAITING_FOR_RETRY"
            )
            # Native-only outcomes must not be bound as invalid legacy PG enums.
            for key in ("SUCCESS_AFTER_RETRY", "CANCELLED"):
                self.assertEqual(
                    api.executions(self.resource.id, 20, 0, key, db)["total"], 0
                )

    def test_execution_children_are_batched_and_bounded(self):
        self.access()
        for i in range(3):
            _, h = self.emit(self.raw(invocation=str(i)))
        self.db.add_all(
            [
                JobStepExecution(history_id=h.id, name=str(i), status="SUCCESS")
                for i in range(205)
            ]
        )
        self.db.commit()
        calls = []
        resource_id = self.resource.id
        with self.principal(("etl.view",)) as (_, db):

            def count(*args):
                calls.append(1)

            event.listen(db.bind, "before_cursor_execute", count)
            try:
                result = api.executions(resource_id, 20, 0, None, db)
            finally:
                event.remove(db.bind, "before_cursor_execute", count)
            self.assertEqual(len(calls), 5)  # resource, count, page, steps, attempts
            row = next(r for r in result["items"] if r["id"] == h.id)
            self.assertEqual(row["attempt_count"], 1)
            self.assertEqual(row["steps_total"], 205)
            self.assertEqual(len(row["steps"]), 200)
            self.assertTrue(row["steps_has_more"])
            tail = api.execution_steps(self.resource.id, h.id, 20, 200, db)
            self.assertEqual(len(tail["items"]), 5)

    def test_schedule_archive_beyond_legacy_cap_and_stable_order(self):
        self.access()
        now = datetime.now(timezone.utc)
        self.db.add_all(
            [
                ExpectedExecutionWindow(
                    organization_id=self.org.id,
                    resource_id=self.resource.id,
                    scheduled_at=now - timedelta(minutes=i),
                    deadline=now + timedelta(seconds=60),
                    status="INCOMPLETE" if i % 2 else "UNKNOWN",
                    parameter_version=1,
                )
                for i in range(505)
            ]
        )
        self.db.commit()
        with self.principal(("etl.view",)) as (_, db):
            self.assertEqual(len(api.windows(self.resource.id, 500, db)), 500)
            one = api.occurrence_page(self.resource.id, None, 200, 0, db)
            two = api.occurrence_page(self.resource.id, None, 200, 200, db)
            self.assertEqual(one["total"], 505)
            self.assertFalse(
                {r["id"] for r in one["items"]} & {r["id"] for r in two["items"]}
            )
            self.assertEqual(
                api.occurrence_page(self.resource.id, "NO_RUN", 20, 0, db)["total"], 0
            )
            self.assertEqual(
                api.occurrence_page(self.resource.id, "INCOMPLETE", 20, 0, db)["total"],
                252,
            )

    def test_attempt_alias_archive_and_child_idor(self):
        self.access()
        _, h = self.emit(self.raw())
        a = self.attempts(h)[0]
        self.db.add_all(
            [
                PentahoAlias(
                    organization_id=self.org.id,
                    resource_id=self.resource.id,
                    history_id=h.id,
                    attempt_id=a.id,
                    alias_key=uuid.uuid4().hex,
                    kind="INVOCATION",
                    native_identity={},
                )
                for _ in range(205)
            ]
        )
        self.db.commit()
        with self.principal(("etl.view",)) as (_, db):
            summary = api.pentaho_attempts(self.resource.id, h.id, 20, 0, db)["items"][
                0
            ]
            self.assertGreater(summary["aliases_total"], 200)
            self.assertEqual(len(summary["aliases"]), 200)
            tail = api.attempt_evidence(
                self.resource.id, h.id, a.id, "aliases", 20, 200, db
            )
            self.assertGreater(len(tail["items"]), 0)
            with self.assertRaises(HTTPException):
                api.attempt_evidence(
                    self.resource.id, uuid.uuid4(), a.id, "aliases", 20, 0, db
                )
            with self.assertRaises(HTTPException):
                api.attempt_evidence(
                    self.resource.id, h.id, uuid.uuid4(), "revisions", 20, 0, db
                )

    def test_large_integration_detail_has_safe_readiness_and_pages(self):
        self.access()
        self.db.add_all(
            [
                PipelineJob(
                    organization_id=self.org.id,
                    integration_id=self.integration.id,
                    native_id=uuid.uuid4().hex,
                    name=str(i),
                    origin="MANUAL",
                    selected=False,
                )
                for i in range(505)
            ]
        )
        self.db.commit()
        with self.principal(("etl.view",)) as (_, db):
            detail = pipelines.detail(self.integration.id, db)
            self.assertEqual(len(detail["jobs"]), 500)
            self.assertFalse(detail["readiness_complete"])
            self.assertEqual(
                detail["activation_blockers"], ["READINESS_PREVIEW_INCOMPLETE"]
            )
            self.assertTrue(detail["pagination"]["jobs"]["has_more"])
            tail = pipelines.integration_records(
                self.integration.id, "jobs", 20, 500, db
            )
            self.assertEqual(tail["total"], 506)
            self.assertEqual(len(tail["items"]), 6)

    def test_incident_association_filter_and_activity_scope(self):
        self.access()
        _, h, f = self.failure()
        with self.principal(("incidents.view",)) as (_, db):
            result = incidents.inventory(
                None, None, self.resource.id, h.id, None, 20, 0, db
            )
            self.assertEqual(result["total"], 1)
            self.assertEqual(result["items"][0]["id"], f.incident_id)
            empty = incidents.inventory(None, None, uuid.uuid4(), h.id, None, 20, 0, db)
            self.assertEqual(empty["total"], 0)
            activities = incidents.activities(f.incident_id, 20, 0, db)
            self.assertGreater(activities["total"], 0)
        with self.principal(("incidents.view",), selection=False) as (_, db):
            with self.assertRaises(HTTPException):
                incidents.activities(f.incident_id, 20, 0, db)
