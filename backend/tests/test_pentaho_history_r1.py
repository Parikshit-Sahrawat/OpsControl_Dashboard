"""Owned PostgreSQL Sprint 05 acceptance. Native authority is controlled, not certified."""

import os
import uuid
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from types import SimpleNamespace
from sqlalchemy import select, func, text
from sqlalchemy.exc import DBAPIError
from fastapi import HTTPException
from app.models import JobOrderHistory, OperationalIncident
from app.security.models import OrganizationMembership, SecurityAuditEvent
from app.security.access_models import (
    Role,
    RolePermission,
    UserRoleAssignment,
    CustomerAccessGrant,
)
from app.security.permission_catalog import PROVIDER_ID
from app.unified.models import ParameterVersion, ExpectedExecutionWindow
from app.unified.schemas import ETLParameters, Schedule
from app.unified import (
    pentaho_history as h,
    pentaho_schedule as schedule,
    pentaho_replay as replay,
)
from app.unified.pentaho_models import PentahoHistoricalNotice as Notice
from app.telemetry.models import NotificationDestination, InAppNotification
from app.data_pipelines import service as s
from app.data_pipelines.models import PipelineHold, PipelineOperation
from tests import test_pentaho_execution_r1 as execution


@unittest.skipUnless(
    os.getenv("OPSCONTROL_V16_ACCEPTANCE") == "1",
    "Owned disposable PostgreSQL required",
)
class PentahoHistoryTests(unittest.TestCase):
    setUp = execution.PentahoExecutionTests.setUp
    raw = execution.PentahoExecutionTests.raw
    emit = execution.PentahoExecutionTests.emit
    attempts = execution.PentahoExecutionTests.attempts

    def grant(self, user, keys):
        role = Role(
            service_provider_id=PROVIDER_ID,
            code="controlled-history-" + uuid.uuid4().hex,
            name="Controlled history " + uuid.uuid4().hex,
        )
        self.db.add(role)
        self.db.flush()
        for key in keys:
            self.db.add(RolePermission(role_id=role.id, permission_key=key))
        self.db.add(
            UserRoleAssignment(
                service_provider_id=PROVIDER_ID, user_id=user.id, role_id=role.id
            )
        )
        self.db.flush()
        self.db.add(
            CustomerAccessGrant(
                service_provider_id=PROVIDER_ID,
                user_id=user.id,
                role_id=role.id,
                organization_id=self.org.id,
            )
        )
        self.db.commit()

    def enable_policy(self):
        self.db.add(
            OrganizationMembership(
                user_id=self.user.id, organization_id=self.org.id, role="viewer"
            )
        )
        self.destination = NotificationDestination(
            organization_id=self.org.id,
            name="Controlled in-app " + uuid.uuid4().hex,
            channel="IN_APP",
            configuration={"user_ids": [str(self.user.id)]},
            enabled=True,
        )
        self.db.add(self.destination)
        self.db.flush()
        self.resource.configuration = {
            **self.resource.configuration,
            "historical_notifications": {
                "enabled": True,
                "historical_after_seconds": 60,
                "destination_ids": [str(self.destination.id)],
            },
        }
        self.db.commit()

    def failure(self):
        now = s.clock(self.db)
        raw = self.raw(outcome="FAILED", run="controlled-historical")
        raw["process_start"] = (now - timedelta(hours=3)).isoformat()
        raw["result"]["ended_at"] = (now - timedelta(hours=2)).isoformat()
        raw["observed_at"] = (
            now - timedelta(hours=2) + timedelta(seconds=1)
        ).isoformat()
        return self.emit(raw)

    def notice(self):
        self.enable_policy()
        event, history = self.failure()
        self.assertEqual(h.reconcile(self.db, self.resource), 1)
        self.db.commit()
        row = self.db.scalar(select(Notice).where(Notice.history_id == history.id))
        return event, history, row

    def test_historical_failure_obligation_keeps_occurrence_discovery_and_identity(
        self,
    ):
        event, history, row = self.notice()
        self.assertEqual(row.payload["classification"], "HISTORICAL_FAILURE")
        self.assertEqual(row.payload["occurred_at"], history.ended_at.isoformat())
        self.assertEqual(row.payload["discovered_at"], event.received_at.isoformat())
        self.assertGreater(event.received_at - history.ended_at, timedelta(hours=1))
        self.assertEqual(h.reconcile(self.db, self.resource), 0)
        self.db.commit()
        self.assertEqual(
            self.db.scalar(
                select(func.count())
                .select_from(Notice)
                .where(Notice.history_id == history.id)
            ),
            1,
        )

    def test_delivery_retries_audits_and_recipient_scoped_inbox(self):
        _, history, row = self.notice()
        with patch(
            "app.telemetry.delivery.send_destination",
            side_effect=TimeoutError("provider must not leak secrets"),
        ):
            result = h.dispatch_notices(limit=1, organization_id=self.org.id)
        self.assertEqual(result["failed"], 1)
        self.db.refresh(row)
        self.assertEqual(row.last_error, "Notification transport unavailable")
        row.next_attempt_at = s.clock(self.db) - timedelta(seconds=1)
        self.db.commit()
        self.assertEqual(
            h.dispatch_notices(limit=1, organization_id=self.org.id)["sent"], 1
        )
        self.db.refresh(row)
        self.assertEqual(row.status, "SENT")
        self.assertEqual(row.attempts, 2)
        self.assertEqual(
            self.db.scalar(
                select(func.count())
                .select_from(InAppNotification)
                .where(InAppNotification.historical_notice_id == row.id)
            ),
            1,
        )
        self.assertTrue(
            self.db.scalar(
                select(SecurityAuditEvent.id).where(
                    SecurityAuditEvent.target_id == str(row.id),
                    SecurityAuditEvent.event_type == "PENTAHO_HISTORICAL_NOTICE_SENT",
                )
            )
        )
        self.assertEqual(
            h.dispatch_notices(limit=1, organization_id=self.org.id)["sent"], 0
        )

    def test_conflicted_failure_cannot_queue_or_deliver_authoritative_notice(self):
        self.enable_policy()
        event, history = self.failure()
        # A distinct verified native result for the same invocation is disputed.
        raw = self.raw(outcome="SUCCESS", run="controlled-historical")
        raw["process_start"] = event.payload["pentaho_identity"]["process_start"]
        raw["result"]["ended_at"] = history.ended_at.isoformat()
        self.emit(raw)
        self.assertEqual(history.pentaho_review_state, "CONFLICTED_EVIDENCE")
        self.assertEqual(h.reconcile(self.db, self.resource), 0)

    def test_queued_notice_blocked_if_identity_later_quarantined(self):
        _, history, row = self.notice()
        history.pentaho_identity_state = "REVIEW_REQUIRED"
        self.db.commit()
        self.assertIsNone(h.claim_notice(self.org.id))
        self.db.refresh(row)
        self.assertEqual(row.status, "BLOCKED")
        self.assertIsNone(
            self.db.scalar(
                select(InAppNotification.id).where(
                    InAppNotification.historical_notice_id == row.id
                )
            )
        )

    def test_recipient_access_revocation_is_respected_at_delivery(self):
        _, _, row = self.notice()
        self.user.active = False
        self.db.commit()
        self.assertEqual(
            h.dispatch_notices(limit=1, organization_id=self.org.id)["failed"], 1
        )
        self.assertIsNone(
            self.db.scalar(
                select(InAppNotification.id).where(
                    InAppNotification.historical_notice_id == row.id
                )
            )
        )

    def test_notice_and_inbox_are_immutable_under_legal_hold(self):
        _, history, row = self.notice()
        self.db.add(
            PipelineHold(
                organization_id=self.org.id,
                source_id=self.source.id,
                kind="LEGAL",
                reference="controlled-historical-hold",
                actor_id=self.user.id,
            )
        )
        self.db.commit()
        self.assertEqual(
            h.dispatch_notices(limit=1, organization_id=self.org.id)["sent"], 1
        )
        for sql in [
            "DELETE FROM pentaho_historical_notices WHERE id=:id",
            "UPDATE pentaho_historical_notices SET payload='{}' WHERE id=:id",
            "DELETE FROM in_app_notifications WHERE historical_notice_id=:id",
        ]:
            with self.assertRaises(DBAPIError):
                with self.db.begin_nested():
                    self.db.execute(text(sql), {"id": row.id})
        s.cleanup(self.db)
        self.db.commit()
        self.assertIsNotNone(self.db.get(JobOrderHistory, history.id))

    def test_late_failure_keeps_closed_incident_closed(self):
        self.enable_policy()
        _, history = self.failure()
        incident = OperationalIncident(
            organization_id=self.org.id,
            episode_key=uuid.uuid4().hex,
            source_kind="ETL",
            source_reference=str(history.id),
            history_id=history.id,
            title="Controlled preserved closed incident",
            severity="CRITICAL",
            status="CLOSED",
            condition_status="RECOVERED",
            opened_at=s.clock(self.db),
            resolved_at=s.clock(self.db),
        )
        self.db.add(incident)
        self.db.commit()
        h.reconcile(self.db, self.resource)
        self.db.commit()
        h.dispatch_notices(limit=1, organization_id=self.org.id)
        self.db.refresh(incident)
        self.assertEqual(incident.status, "CLOSED")

    def parameters(self, mode="MONITORING_EXPECTATION", persist=True):
        self.base = s.clock(self.db).replace(second=0, microsecond=0) + timedelta(
            minutes=2
        )
        config = ETLParameters(
            schedule=Schedule(frequency="CUSTOM", cron="* * * * *", timezone="UTC"),
            pentaho_schedule_authority=(
                {"mode": mode, "revision": "controlled-1"} if mode else None
            ),
            no_run_grace_seconds=30,
        ).model_dump(mode="json")
        p = ParameterVersion(
            organization_id=self.org.id,
            resource_id=self.resource.id,
            version=1,
            configuration=config,
            sha256=s.digest(config),
            status="ACTIVE",
            created_at=self.base - timedelta(minutes=2),
        )
        self.resource.created_at = self.base - timedelta(minutes=2)
        self.resource.schedule_watermark = self.base - timedelta(minutes=1)
        self.db.add(p)
        if persist:
            self.db.commit()
        return p

    def tick(self, p, stamp, healthy=True):
        self.source.last_observed_at = stamp
        self.source.health = "IDLE" if healthy else "ERROR"
        receipt, _ = s.operation(
            self.db,
            self.org.id,
            "ACCEPTANCE",
            "controlled-schedule-poll-" + uuid.uuid4().hex,
            {"generation": str(self.source.generation)},
            None,
            source_id=self.source.id,
        )
        receipt.state = "COMPLETE"
        receipt.result = {
            "complete": True,
            "accepted_at": stamp.isoformat(),
            "origin": "CONTROLLED_COMPLETE_POLL",
        }
        self.db.flush()
        schedule.evaluate(self.db, self.resource, p, stamp)
        self.db.commit()

    def window(self):
        return self.db.scalar(
            select(ExpectedExecutionWindow).where(
                ExpectedExecutionWindow.resource_id == self.resource.id,
                ExpectedExecutionWindow.scheduled_at == self.base,
            )
        )

    def test_explicit_expectation_grace_and_legitimate_no_run(self):
        p = self.parameters()
        self.tick(p, self.base - timedelta(seconds=20))
        self.tick(p, self.base + timedelta(seconds=10))
        self.assertEqual(self.window().status, "PENDING_GRACE")
        self.tick(p, self.base + timedelta(seconds=31))
        self.assertEqual(self.window().status, "NO_RUN")
        self.assertEqual(
            self.window().pentaho_authority["selection"]["mode"],
            "MONITORING_EXPECTATION",
        )
        self.assertIsNone(self.window().history_id)

    def test_unhealthy_or_suspended_collection_never_infers_no_run(self):
        p = self.parameters()
        self.tick(p, self.base - timedelta(seconds=20))
        self.tick(p, self.base + timedelta(seconds=31), healthy=False)
        self.assertEqual(self.window().status, "INCOMPLETE")
        s.hold(
            self.db, self.source.id, "MANUAL", "controlled-schedule-hold", self.user.id
        )
        self.db.commit()
        self.tick(p, self.base + timedelta(seconds=45))
        self.assertEqual(self.window().status, "INCOMPLETE")

    def test_unknown_and_manual_schedule_not_native_success_or_no_run(self):
        p = self.parameters(mode=None)
        self.tick(p, self.base + timedelta(seconds=31))
        self.assertEqual(self.window().status, "UNKNOWN")
        self.assertIsNone(self.window().history_id)

    def test_verified_native_schedule_and_freshness(self):
        p = self.parameters(persist=False)
        export = {
            "authority_id": "controlled-scheduler",
            "revision": "native-7",
            "schedule": p.configuration["schedule"],
            "observed_at": (self.base - timedelta(minutes=1)).isoformat(),
            "valid_until": (self.base + timedelta(hours=1)).isoformat(),
            "evidence_sha256": "c" * 64,
            "occurrences": [
                {
                    "native_occurrence_id": "occurrence-1",
                    "scheduled_at": self.base.isoformat(),
                }
            ],
        }
        self.profile.definition = {
            **self.profile.definition,
            "verified_pentaho_claims": [
                "INVOCATION",
                "EXECUTION_OUTCOME",
                "SCHEDULER_RETRY",
                "SCHEDULE",
            ],
        }
        self.proof.native_job_id = self.cfg["native_job_id"]
        self.proof.payload = {
            **self.proof.payload,
            "event": {"pentaho_identity": {"schedule": export}},
            "reader_definition_hash": s.reader_definition(self.db, self.method),
        }
        p.configuration = {
            **p.configuration,
            "pentaho_schedule_authority": {
                "mode": "VERIFIED_SCHEDULER",
                "authority_id": "controlled-scheduler",
                "revision": "native-7",
                "evidence_id": str(self.proof.id),
                "capability_id": str(self.profile.id),
            },
        }
        self.db.commit()
        result = schedule.authority(
            self.db, self.resource, p.configuration, self.base, strict=True
        )
        self.assertEqual(result["mode"], "VERIFIED_SCHEDULER")
        self.assertEqual(
            schedule.authority(
                self.db, self.resource, p.configuration, self.base + timedelta(hours=2)
            )["mode"],
            "UNKNOWN",
        )
        self.tick(p, self.base - timedelta(seconds=20))
        self.tick(p, self.base + timedelta(seconds=31))
        self.assertEqual(self.window().status, "NO_RUN")
        self.assertEqual(
            self.window().pentaho_authority["native_occurrence_id"], "occurrence-1"
        )

    def plan(self, age=3600):
        self.grant(self.user, ["etl.replay", "etl.configure", "etl.view"])
        now = s.clock(self.db)
        op = s.plan_recovery(
            self.db,
            self.source,
            now - timedelta(seconds=age),
            now - timedelta(seconds=1),
            self.user.id,
            uuid.uuid4().hex,
            mode=replay.MODE,
        )
        self.db.commit()
        return op

    def test_provider_replay_explicitly_unsupported(self):
        now = s.clock(self.db)
        op = s.plan_recovery(
            self.db,
            self.source,
            now - timedelta(minutes=1),
            now,
            self.user.id,
            uuid.uuid4().hex,
        )
        self.assertEqual(op.state, "UNSUPPORTED")
        self.assertFalse(op.result["provider_replay_supported"])

    def test_bounded_reconciliation_preserves_live_and_physical_recovery_cursors(self):
        self.emit(self.raw())
        op = self.plan()
        self.source.next_run_at = s.clock(self.db) + timedelta(minutes=1)
        self.db.commit()
        live = dict(self.source.live_checkpoint)
        physical = dict(self.source.recovery_checkpoint)
        ticket = s.acquire(self.db, self.source.id, uuid.uuid4())
        self.db.commit()
        # Include actual accepted event time in the range without reading providers.
        from app.unified.models import NormalizedEvent

        event = self.db.scalar(
            select(NormalizedEvent).where(
                NormalizedEvent.resource_id == self.resource.id
            )
        )
        op.configuration = {
            **op.configuration,
            "start": (event.observed_at - timedelta(seconds=1)).isoformat(),
            "end": (event.observed_at + timedelta(seconds=1)).isoformat(),
        }
        # Historical fixtures may exceed automatic bounds and need real role approval.
        self.grant(self.reviewer, ["etl.approve_replay"])
        op.reviewer_id = self.reviewer.id
        self.db.commit()
        self.assertEqual(replay.run_batch(self.db, self.source, op, ticket), 1)
        self.db.commit()
        self.assertEqual(self.source.live_checkpoint, live)
        self.assertEqual(self.source.recovery_checkpoint, physical)
        self.assertEqual(op.state, "COMPLETE")
        self.assertTrue(op.result["reconciliation_cursor"])

    def test_beyond_bound_requires_independent_approval(self):
        op = self.plan(age=7 * 3600)
        self.assertEqual(op.state, "APPROVAL_REQUIRED")
        self.source.next_run_at = s.clock(self.db) + timedelta(minutes=1)
        self.db.commit()
        ticket = s.acquire(self.db, self.source.id, uuid.uuid4())
        self.db.commit()
        op.state = "PENDING"
        with self.assertRaises(s.PipelineError):
            replay.run_batch(self.db, self.source, op, ticket)
        self.db.rollback()

    def test_live_priority_and_holds_fail_closed_without_cursor_advance(self):
        op = self.plan()
        ticket = s.acquire(self.db, self.source.id, uuid.uuid4())
        self.db.commit()
        self.source.next_run_at = s.clock(self.db) - timedelta(seconds=1)
        self.db.commit()
        with self.assertRaises(s.PipelineError):
            replay.run_batch(self.db, self.source, op, ticket)
        self.db.rollback()
        s.hold(self.db, self.source.id, "MANUAL", "held-backlog", self.user.id)
        self.db.commit()
        with self.assertRaises(s.PipelineError):
            s.acquire(self.db, self.source.id, uuid.uuid4())
        self.db.rollback()
        self.assertNotIn("reconciliation_cursor", op.result)

    def test_stale_generation_or_fence_rejects_replay(self):
        op = self.plan()
        self.source.next_run_at = s.clock(self.db) + timedelta(minutes=1)
        self.db.commit()
        ticket = s.acquire(self.db, self.source.id, uuid.uuid4())
        self.db.commit()
        self.source.fence += 1
        self.source.generation = uuid.uuid4()
        self.db.commit()
        with self.assertRaises(s.PipelineError):
            replay.run_batch(self.db, self.source, op, ticket)
        self.db.rollback()
        self.assertNotIn("reconciliation_cursor", op.result)

    def test_notification_claims_and_completions_are_fenced(self):
        _, _, row = self.notice()
        first = h.claim_notice(self.org.id)
        self.assertEqual(first.id, row.id)
        self.assertIsNone(h.claim_notice(self.org.id))
        self.db.refresh(row)
        row.lease_until = s.clock(self.db) - timedelta(seconds=1)
        self.db.commit()
        replacement = h.claim_notice(self.org.id)
        self.assertNotEqual(first.lease_token, replacement.lease_token)
        self.assertFalse(
            h.finish_notice(
                first.id, first.lease_token, error="controlled stale completion"
            )
        )
        self.assertTrue(
            h.finish_notice(
                replacement.id,
                replacement.lease_token,
                error="controlled local failure",
            )
        )
        self.db.refresh(row)
        self.assertEqual(row.status, "FAILED")

    def test_schedule_occurrence_does_not_claim_attempt_success(self):
        p = self.parameters()
        self.tick(p, self.base - timedelta(seconds=20))
        raw = self.raw(outcome="FAILED", run="schedule-compliance", retry="PENDING")
        raw["process_start"] = (self.base + timedelta(seconds=3)).isoformat()
        raw["result"]["ended_at"] = (self.base + timedelta(seconds=15)).isoformat()
        raw["observed_at"] = raw["result"]["ended_at"]
        _, history = self.emit(raw)
        self.tick(p, self.base + timedelta(seconds=20))
        window = self.window()
        self.assertEqual(window.status, "OBSERVED")
        self.assertEqual(window.history_id, history.id)
        self.assertNotEqual(window.id, history.id)
        self.assertNotEqual(window.id, self.attempts(history)[0].id)
        self.assertEqual(history.pentaho_lifecycle, "WAITING_FOR_RETRY")
        self.assertIsNone(history.pentaho_outcome)

    def test_manual_mode_creates_no_expected_occurrences(self):
        p = self.parameters(mode="MANUAL")
        self.tick(p, self.base + timedelta(minutes=1))
        self.assertIsNone(self.window())

    def test_persisted_occurrence_authority_cannot_be_rewritten(self):
        p = self.parameters()
        self.tick(p, self.base + timedelta(seconds=5))
        window = self.window()
        with self.assertRaises(DBAPIError):
            with self.db.begin_nested():
                self.db.execute(
                    text(
                        "UPDATE expected_execution_windows SET pentaho_authority='{}' WHERE id=:id"
                    ),
                    {"id": window.id},
                )

    def test_shared_holds_compose_and_no_failover_is_possible(self):
        op = self.plan()
        s.hold(
            self.db,
            self.source.id,
            "INTEGRATION",
            str(self.integration.id),
            self.user.id,
        )
        hold = s.hold(
            self.db, self.source.id, "MANUAL", "independent-backlog-hold", self.user.id
        )
        self.db.commit()
        with self.assertRaises(s.PipelineError):
            s.release_hold(self.db, hold.id, self.reviewer.id)
        self.db.rollback()
        # Controlled preverified continuity fixture; clearing one reference still
        # cannot override the independent integration hold.
        self.source.continuity_validated = True
        self.db.commit()
        s.release_hold(self.db, hold.id, self.reviewer.id)
        self.db.commit()
        self.assertTrue(s.suspended(self.db, self.source))
        with self.assertRaises(s.PipelineError):
            s.acquire(self.db, self.source.id, uuid.uuid4())
        self.db.rollback()
        self.assertEqual(op.result.get("reconciliation_cursor"), None)

    def test_replay_preparation_failure_keeps_live_health_and_checkpoint(self):
        op = self.plan()
        self.source.next_run_at = s.clock(self.db) + timedelta(minutes=1)
        self.source.health = "IDLE"
        self.db.commit()
        before = dict(self.source.live_checkpoint)
        with patch(
            "app.unified.pentaho_replay.run_batch",
            side_effect=ValueError("controlled preparation failure"),
        ):
            replay.run(op.id)
        self.db.expire_all()
        self.assertEqual(self.source.live_checkpoint, before)
        self.assertEqual(self.source.health, "IDLE")
        self.assertEqual(op.state, "UNRECOVERABLE")

    def test_stale_replay_cleanup_cannot_release_replacement_owner(self):
        op = self.plan()
        ticket = s.acquire(self.db, self.source.id, uuid.uuid4())
        self.db.commit()
        op.state = "RUNNING"
        op.fence = 1
        op.owner_id = uuid.UUID(ticket["owner_id"])
        op.lease_until = self.source.lease_until
        self.db.commit()
        old = {"id": op.id, "fence": op.fence}
        replacement = uuid.uuid4()
        self.source.fence += 1
        self.source.owner_id = replacement
        op.fence += 1
        op.owner_id = replacement
        self.db.commit()
        replay.failure(ticket, old, ValueError("controlled stale cleanup"))
        self.db.expire_all()
        self.assertEqual(self.source.owner_id, replacement)
        self.assertEqual(op.owner_id, replacement)
        self.assertEqual(op.state, "RUNNING")

    def test_historical_failure_never_drives_live_incident_conditions(self):
        from app.unified.engines import evaluate_executions

        self.enable_policy()
        event, history = self.failure()
        with patch("app.unified.engines.condition") as conditions, patch(
            "app.unified.engines.source_readiness", return_value={"ready": True}
        ):
            evaluate_executions(
                self.db,
                self.resource,
                SimpleNamespace(configuration={}),
                s.clock(self.db),
            )
        self.assertEqual(conditions.call_count, 1)
        self.assertEqual(conditions.call_args.args[2], "ETL_TELEMETRY")
        self.assertTrue(
            history.source_evidence["pentaho_historical"][
                "operational_reassessment_required"
            ]
        )
        self.assertEqual(
            history.source_evidence["pentaho_historical"]["notification_eligibility"],
            "ELIGIBLE",
        )

    def test_replay_batch_bound_resumes_cursor_without_starving_live_collection(self):
        first, _ = self.emit(self.raw(invocation="bounded-first", run="bounded-first"))
        self.emit(self.raw(invocation="bounded-second", run="bounded-second"))
        self.grant(self.user, ["etl.replay", "etl.configure", "etl.view"])
        stamp = datetime.fromisoformat(first.payload["timestamp"])
        op = s.plan_recovery(
            self.db,
            self.source,
            stamp - timedelta(seconds=1),
            stamp + timedelta(seconds=1),
            self.user.id,
            uuid.uuid4().hex,
            mode=replay.MODE,
        )
        self.db.commit()
        if op.state == "APPROVAL_REQUIRED":
            self.grant(self.reviewer, ["etl.approve_replay"])
            op.reviewer_id = self.reviewer.id
            op.state = "APPROVED"
        self.source.next_run_at = s.clock(self.db) + timedelta(minutes=1)
        self.db.commit()
        before = dict(self.source.live_checkpoint)
        ticket = s.acquire(self.db, self.source.id, uuid.uuid4())
        self.db.commit()
        self.assertEqual(replay.run_batch(self.db, self.source, op, ticket, limit=1), 1)
        self.db.commit()
        self.assertEqual(op.state, "PENDING")
        cursor = dict(op.result["reconciliation_cursor"])
        ticket = s.acquire(self.db, self.source.id, uuid.uuid4())
        self.db.commit()
        self.assertEqual(replay.run_batch(self.db, self.source, op, ticket, limit=1), 1)
        self.db.commit()
        self.assertEqual(op.state, "COMPLETE")
        self.assertEqual(op.result["processed"], 2)
        self.assertNotEqual(op.result["reconciliation_cursor"], cursor)
        self.assertEqual(self.source.live_checkpoint, before)
        self.assertEqual(
            op.result["coverage_status"], "ACCEPTED_RECORDS_ONLY_NO_GAP_CLOSURE"
        )

    def test_incomplete_poll_does_not_prove_no_run_despite_idle_health(self):
        p = self.parameters()
        self.tick(p, self.base - timedelta(seconds=20))
        self.tick(p, self.base + timedelta(seconds=10))
        stamp = self.base + timedelta(seconds=31)
        self.source.last_observed_at = stamp
        self.source.health = "IDLE"
        receipt, _ = s.operation(
            self.db,
            self.org.id,
            "ACCEPTANCE",
            "controlled-incomplete-" + uuid.uuid4().hex,
            {"generation": str(self.source.generation)},
            None,
            source_id=self.source.id,
        )
        receipt.state = "COMPLETE"
        receipt.result = {
            "complete": False,
            "accepted_at": stamp.isoformat(),
            "origin": "CONTROLLED_INCOMPLETE_POLL",
        }
        self.db.flush()
        schedule.evaluate(self.db, self.resource, p, stamp)
        self.db.commit()
        self.assertEqual(self.window().status, "INCOMPLETE")
