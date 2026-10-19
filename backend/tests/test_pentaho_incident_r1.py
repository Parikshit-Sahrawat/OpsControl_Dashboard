"""Controlled PostgreSQL incident evidence; never genuine native certification."""

import os
import unittest
from datetime import timedelta
from unittest.mock import patch
from sqlalchemy import select, func, text
from sqlalchemy.exc import DBAPIError
from fastapi import HTTPException
from app.models import OperationalIncident
from app.unified import pentaho_history as historical
from app.unified.pentaho_models import PentahoRecoveryLink
from app.native_incidents.models import (
    NativeIncidentFailure as Failure,
)
from app.native_incidents import pentaho as p, service
from app.data_pipelines import service as pipelines
from tests import test_pentaho_history_r1 as history_tests
from tests import test_pentaho_execution_r1 as execution_tests


@unittest.skipUnless(
    os.getenv("OPSCONTROL_V16_ACCEPTANCE") == "1", "Owned PostgreSQL required"
)
class PentahoIncidentTests(unittest.TestCase):
    setUp = execution_tests.PentahoExecutionTests.setUp
    raw = execution_tests.PentahoExecutionTests.raw
    emit = execution_tests.PentahoExecutionTests.emit
    attempts = execution_tests.PentahoExecutionTests.attempts
    from contextlib import contextmanager

    @contextmanager
    def operator(self, roles=None):
        from app.security.scope import Principal, current_principal

        keys = (
            frozenset({"incidents.manage", "incidents.view"})
            if roles is None
            else frozenset()
        )
        token = current_principal.set(
            Principal(
                self.user.id,
                self.user.username,
                False,
                {self.org.id: "operator"},
                permissions=keys,
                customer_permissions={self.org.id: keys},
            )
        )
        try:
            yield
        finally:
            current_principal.reset(token)

    grant = history_tests.PentahoHistoryTests.grant

    def failure(self, name="failed", root=None, retry="EXHAUSTED"):
        if root:
            self.profile.definition = {
                **self.profile.definition,
                "verified_pentaho_claims": self.profile.definition[
                    "verified_pentaho_claims"
                ]
                + ["FAILURE_CAUSE"],
            }
            self.db.commit()
        raw = self.raw(invocation=name, outcome="FAILED", run=name, retry=retry)
        if root:
            raw["failure_cause"] = {
                "authority_id": "controlled-cause-authority",
                "occurrence_id": root,
                "evidence_sha256": "c" * 64,
            }
        event, history = self.emit(raw)
        historical.reconcile(self.db, self.resource)
        self.db.commit()
        return (
            event,
            history,
            self.db.scalar(select(Failure).where(Failure.event_id == event.id)),
        )

    def test_verified_failure_creates_native_incident_and_replay_is_idempotent(self):
        event, history, row = self.failure()
        self.assertIsNotNone(row)
        incident = self.db.get(OperationalIncident, row.incident_id)
        self.assertEqual(incident.status, "OPEN")
        historical.reconcile(self.db, self.resource)
        self.db.commit()
        self.assertEqual(
            self.db.scalar(
                select(func.count())
                .select_from(Failure)
                .where(Failure.history_id == history.id)
            ),
            1,
        )
        self.assertTrue(row.reassessment)
        self.assertLess(row.occurred_at, row.discovered_at)

    def test_common_root_groups_distinct_failures_and_preserves_evidence(self):
        _, a, first = self.failure("a", "outage-1")
        _, b, second = self.failure("b", "outage-1")
        self.assertNotEqual(a.id, b.id)
        self.assertEqual(first.incident_id, second.incident_id)
        self.assertNotEqual(first.event_id, second.event_id)

    def test_unrelated_same_job_and_time_stay_separate(self):
        _, _, a = self.failure("a")
        _, _, b = self.failure("b")
        self.assertNotEqual(a.incident_id, b.incident_id)

    def test_waiting_for_retry_creates_no_terminal_incident(self):
        _, history, row = self.failure(retry="PENDING")
        self.assertEqual(history.pentaho_lifecycle, "WAITING_FOR_RETRY")
        self.assertIsNone(row)

    def test_historical_root_never_reopens_resolved_incident(self):
        _, _, a = self.failure("a", "outage-1")
        incident = self.db.get(OperationalIncident, a.incident_id)
        incident.status = "RESOLVED"
        self.db.commit()
        _, _, b = self.failure("b", "outage-1")
        self.assertEqual(a.incident_id, b.incident_id)
        self.assertEqual(incident.status, "RESOLVED")
        self.assertEqual(b.reassessment["incident_status"], "RESOLVED")

    def test_conflicted_failure_cannot_create_authoritative_association(self):
        raw = self.raw(outcome="FAILED", run="conflict")
        _, history = self.emit(raw)
        self.emit(self.raw(outcome="SUCCESS", run="conflict"))
        historical.reconcile(self.db, self.resource)
        self.db.commit()
        self.assertEqual(history.pentaho_review_state, "CONFLICTED_EVIDENCE")
        self.assertIsNone(
            self.db.scalar(select(Failure).where(Failure.history_id == history.id))
        )

    def recovered(self):
        _, original, row = self.failure()
        now = pipelines.clock(self.db)
        raw = self.raw(invocation="recovery", outcome="SUCCESS")
        raw["process_start"] = (now - timedelta(seconds=5)).isoformat()
        raw["result"]["ended_at"] = (now - timedelta(seconds=1)).isoformat()
        raw["observed_at"] = now.isoformat()
        _, run = self.emit(raw)
        # Relationship service itself is exercised in existing Sprint 03 regressions.
        self.db.add(
            PentahoRecoveryLink(
                organization_id=self.org.id,
                failed_history_id=original.id,
                recovery_history_id=run.id,
                proposed_by=self.user.id,
                status="CONFIRMED",
                revision=1,
            )
        )
        incident = self.db.get(OperationalIncident, row.incident_id)
        incident.status = "MONITORING"
        service.details(self.db, incident).monitoring_started_at = now
        self.db.commit()
        return original, run, incident, now

    def test_manual_recovery_preserves_failed_original_and_requires_observation(self):
        original, run, incident, now = self.recovered()
        import uuid

        ticket = pipelines.acquire(self.db, self.source.id, uuid.uuid4())
        self.db.commit()
        pipelines.accept(self.db, ticket, [], self.source.live_checkpoint, True)
        self.db.commit()
        now = pipelines.clock(self.db)
        with self.operator():
            d = service.details(self.db, incident)
            first = p.assess(self.db, incident, d.revision, "first", now=now)
            self.assertEqual(first.result, "RECOVERY_CANDIDATE")
            self.db.commit()
            second = p.assess(
                self.db, incident, d.revision, "second", now=now + timedelta(seconds=30)
            )
            self.assertEqual(second.result, "VALIDATION_PENDING")
            self.db.commit()
            third = p.assess(
                self.db, incident, d.revision, "third", now=now + timedelta(seconds=61)
            )
            self.assertEqual(third.result, "VALIDATED_RECOVERY")
            service.transition(
                self.db,
                incident,
                "RESOLVED",
                d.revision,
                "spoofed",
                now=now + timedelta(seconds=61),
            )
            service.transition(
                self.db,
                incident,
                "CLOSED",
                d.revision,
                "spoofed",
                now=now + timedelta(seconds=62),
            )
            self.db.commit()
        self.assertEqual(original.pentaho_outcome, "FAILED")
        self.assertEqual(incident.status, "CLOSED")

    def test_unhealthy_monitoring_blocks_and_resets_window(self):
        _, _, incident, now = self.recovered()
        with self.operator(), patch.object(p, "health", return_value=False):
            result = p.assess(
                self.db,
                incident,
                service.details(self.db, incident).revision,
                "bad",
                now=now,
            )
            self.assertEqual(result.result, "VALIDATION_FAILED")
            self.assertIsNone(result.evidence["healthy_since"])

    def test_incomplete_recovery_is_not_restoration(self):
        _, _, row = self.failure()
        incident = self.db.get(OperationalIncident, row.incident_id)
        with patch.object(p, "health", return_value=True):
            proof = p.recovery(self.db, incident, pipelines.clock(self.db))
        self.assertEqual(proof["result"], "INSUFFICIENT_EVIDENCE")
        self.assertFalse(proof["ready"])

    def test_stale_idempotent_and_unauthorized_assessments(self):
        _, _, incident, now = self.recovered()
        with self.operator(), patch.object(p, "health", return_value=True):
            revision = service.details(self.db, incident).revision
            first = p.assess(self.db, incident, revision, "same", now=now)
            self.db.commit()
            self.assertEqual(
                first.id, p.assess(self.db, incident, revision, "same", now=now).id
            )
            with self.assertRaises(HTTPException):
                p.assess(self.db, incident, revision, "stale", now=now)
        with self.operator(roles={}):
            with self.assertRaises(HTTPException) as caught:
                p.assess(self.db, incident, revision, "denied", now=now)
            self.assertEqual(caught.exception.status_code, 403)

    def test_failure_and_assessment_evidence_is_immutable(self):
        _, _, incident, now = self.recovered()
        with self.operator():
            p.assess(
                self.db,
                incident,
                service.details(self.db, incident).revision,
                "immutable",
                now=now,
            )
            self.db.commit()
        for table in ("native_incident_failures", "native_recovery_assessments"):
            for mutation in (
                "DELETE FROM " + table,
                "UPDATE " + table + " SET evidence='{}'::jsonb",
            ):
                with self.assertRaises(DBAPIError):
                    self.db.execute(
                        text(mutation + " WHERE incident_id=:id"), {"id": incident.id}
                    )
                    self.db.commit()
                self.db.rollback()

    def test_distinct_failure_observations_are_all_preserved(self):
        event, history, first = self.failure()
        later, _ = self.emit(
            self.raw(invocation="failed", outcome="FAILED", run="failed")
        )
        historical.reconcile(self.db, self.resource)
        self.db.commit()
        # The persisted fair scan first wraps its prior history cursor.
        historical.reconcile(self.db, self.resource)
        self.db.commit()
        rows = list(
            self.db.scalars(select(Failure).where(Failure.history_id == history.id))
        )
        self.assertEqual({r.event_id for r in rows}, {event.id, later.id})
        self.assertEqual({r.incident_id for r in rows}, {first.incident_id})

    def test_unhealthy_downstream_dependency_blocks_recovery(self):
        from app.unified.models import (
            MonitoringResource,
            ResourceDependency,
            ResourceCondition,
        )

        _, _, incident, now = self.recovered()
        from app.models import DataSource

        source = DataSource(
            organization_id=self.org.id,
            name="Controlled downstream source",
            source_type="API",
        )
        self.db.add(source)
        self.db.flush()
        target = MonitoringResource(
            organization_id=self.org.id,
            domain="API",
            name="Controlled downstream",
            data_source_id=source.id,
            environment="TEST",
            configuration={},
        )
        self.db.add(target)
        self.db.flush()
        self.db.add(
            ResourceDependency(
                organization_id=self.org.id,
                resource_id=target.id,
                depends_on_id=self.resource.id,
                relationship_type="DEPENDS_ON",
            )
        )
        self.db.add(
            ResourceCondition(
                organization_id=self.org.id,
                resource_id=target.id,
                condition_key="health",
                condition_type="HTTP_UNHEALTHY",
                active=True,
                severity="ERROR",
                message="Controlled downstream failed",
                first_observed_at=now,
                last_observed_at=now,
                evidence={"probe": "controlled"},
            )
        )
        self.db.commit()
        with patch.object(p, "health", return_value=True):
            proof = p.recovery(self.db, incident, now)
        self.assertEqual(proof["result"], "VALIDATION_FAILED")
        self.assertFalse(proof["evidence"]["dependencies"][0]["ready"])

    def test_gap_in_observation_restarts_period(self):
        _, _, incident, now = self.recovered()
        with self.operator(), patch.object(p, "health", return_value=True):
            d = service.details(self.db, incident)
            p.assess(self.db, incident, d.revision, "first", now=now)
            self.db.commit()
            next = p.assess(
                self.db, incident, d.revision, "gap", now=now + timedelta(seconds=121)
            )
            self.assertEqual(next.result, "VALIDATION_PENDING")
            self.assertEqual(
                next.evidence["healthy_since"],
                (now + timedelta(seconds=121)).isoformat(),
            )

    def test_missing_schedule_compliance_blocks_validation(self):
        from types import SimpleNamespace

        _, _, incident, now = self.recovered()
        with patch.object(p, "health", return_value=True), patch(
            "app.unified.engines.active_parameters",
            return_value=SimpleNamespace(
                version=1, configuration={"schedule": {"frequency": "DAILY"}}
            ),
        ):
            proof = p.recovery(self.db, incident, now)
        self.assertEqual(proof["result"], "VALIDATION_FAILED")
        self.assertFalse(proof["evidence"]["schedules"][0]["ready"])

    def test_conflicting_recovery_evidence_blocks_validation(self):
        _, run, incident, now = self.recovered()
        raw = self.raw(invocation="recovery", outcome="FAILED")
        raw["process_start"] = run.started_at.isoformat()
        raw["result"]["ended_at"] = run.ended_at.isoformat()
        self.emit(raw)
        with patch.object(p, "health", return_value=True):
            proof = p.recovery(self.db, incident, now)
        self.assertEqual(proof["result"], "VALIDATION_FAILED")
        self.assertFalse(proof["ready"])

    def test_current_source_requires_complete_receipt(self):
        _, _, _, now = self.recovered()
        self.assertFalse(p.health(self.db, self.resource, now))
        import uuid

        ticket = pipelines.acquire(self.db, self.source.id, uuid.uuid4())
        self.db.commit()
        pipelines.accept(self.db, ticket, [], self.source.live_checkpoint, True)
        self.db.commit()
        self.assertTrue(p.health(self.db, self.resource, pipelines.clock(self.db)))

    def test_concurrent_assessments_serialize_revision(self):
        from concurrent.futures import ThreadPoolExecutor
        from app.db.session import SessionLocal
        from app.native_incidents.api import checked

        _, _, incident, _ = self.recovered()
        id, revision = incident.id, service.details(self.db, incident).revision
        self.db.commit()

        # Eager scalar snapshots: never share a SQLAlchemy session across threads.
        _ = self.user.id, self.user.username, self.org.id

        def apply(key):
            with self.operator(), SessionLocal() as db:
                try:
                    row = checked(db, id, "incidents.manage", True)
                    assessment = p.assess(db, row, revision, key)
                    db.commit()
                    return assessment.result
                except HTTPException as error:
                    db.rollback()
                    return error.status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(apply, ["race-a", "race-b"]))
        self.assertEqual(results.count(409), 1)
        self.assertEqual(results.count("VALIDATION_FAILED"), 1)

    def test_live_failure_after_closed_root_creates_new_episode(self):
        _, _, first = self.failure("old", "same-root")
        previous = self.db.get(OperationalIncident, first.incident_id)
        previous.status = "CLOSED"
        self.db.commit()
        now = pipelines.clock(self.db)
        raw = self.raw(invocation="live", outcome="FAILED", run="live")
        raw["process_start"] = (now - timedelta(seconds=3)).isoformat()
        raw["result"]["ended_at"] = (now - timedelta(seconds=1)).isoformat()
        raw["observed_at"] = now.isoformat()
        raw["failure_cause"] = {
            "authority_id": "controlled-cause-authority",
            "occurrence_id": "same-root",
            "evidence_sha256": "c" * 64,
        }
        event, _ = self.emit(raw)
        historical.reconcile(self.db, self.resource)
        self.db.commit()
        row = self.db.scalar(select(Failure).where(Failure.event_id == event.id))
        self.assertNotEqual(row.incident_id, previous.id)
        self.assertEqual(previous.status, "CLOSED")
        self.assertEqual(row.reassessment, {})

    def test_concurrent_correlation_preserves_single_incident(self):
        from concurrent.futures import ThreadPoolExecutor
        from app.db.session import SessionLocal
        from app.unified.models import MonitoringResource, NormalizedEvent
        from app.models import JobOrder, JobOrderHistory

        event, history = self.emit(
            self.raw(invocation="race", outcome="FAILED", run="race")
        )
        rid, hid, eid = self.resource.id, history.id, event.id
        self.db.commit()

        def apply(_):
            with SessionLocal() as db:
                resource = db.scalar(
                    select(MonitoringResource)
                    .where(MonitoringResource.id == rid)
                    .with_for_update()
                )
                db.scalar(
                    select(JobOrder)
                    .where(JobOrder.id == resource.job_order_id)
                    .with_for_update()
                )
                row = p.correlate(
                    db,
                    resource,
                    db.get(JobOrderHistory, hid),
                    db.get(NormalizedEvent, eid),
                    pipelines.clock(db),
                )
                incident_id = row.incident_id
                db.commit()
                return incident_id

        with ThreadPoolExecutor(max_workers=2) as pool:
            ids = list(pool.map(apply, range(2)))
        self.assertEqual(ids[0], ids[1])
        self.assertEqual(
            self.db.scalar(
                select(func.count())
                .select_from(Failure)
                .where(Failure.history_id == hid)
            ),
            1,
        )
