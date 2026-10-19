"""Sprint 04 on real owned PostgreSQL. Authority fixtures are NOT certification."""

import os
import uuid
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from sqlalchemy import select, func, text
from sqlalchemy.exc import DBAPIError
from fastapi import HTTPException
from app.db.session import SessionLocal
from app.models import JobOrderHistory, ExecutionStatus, ExecutionType
from app.unified.models import NormalizedEvent
from app.unified.pentaho_models import (
    PentahoEvidenceReview as Review,
    PentahoEvidenceDecision as Decision,
    PentahoRevision,
    PentahoAlias,
)
from app.unified import pentaho_review as review
from app.unified.reconstruction import reduce_execution
from app.security.scope import Principal, current_principal
from app.security.access_control import request_permissions
from app.security.models import SecurityAuditEvent
from tests import test_pentaho_execution_r1 as execution


@unittest.skipUnless(
    os.getenv("OPSCONTROL_V16_ACCEPTANCE") == "1", "Owned PostgreSQL required"
)
class PentahoReviewTests(unittest.TestCase):
    setUp = execution.PentahoExecutionTests.setUp
    raw = execution.PentahoExecutionTests.raw
    emit = execution.PentahoExecutionTests.emit
    attempts = execution.PentahoExecutionTests.attempts

    @contextmanager
    def adjudicator(self, user=None):
        user = user or self.user
        principal = Principal(
            user.id,
            user.username,
            False,
            {self.org.id: "operator"},
            permissions=frozenset({"etl.resolve_identity", "etl.view"}),
            customer_permissions={
                self.org.id: frozenset({"etl.resolve_identity", "etl.view"})
            },
        )
        p = current_principal.set(principal)
        r = request_permissions.set(("etl.resolve_identity",))
        try:
            yield
        finally:
            request_permissions.reset(r)
            current_principal.reset(p)

    def conflict(self):
        original, history = self.emit(self.raw(run="review-run"))
        candidate, _ = self.emit(self.raw(outcome="FAILED", run="review-run"))
        row = self.db.scalar(select(Review).where(Review.event_id == candidate.id))
        return original, candidate, history, row

    def decide(self, row, action="REJECT_CLAIM", revision=None, key=None):
        with self.adjudicator():
            result = review.decide(
                self.db,
                self.resource,
                row.id,
                self.user.id,
                action,
                revision or row.revision,
                key or uuid.uuid4().hex,
                "Controlled native evidence adjudication",
            )
            self.db.commit()
            return result

    def test_equal_authority_conflict_pins_last_projection_and_both_evidence(self):
        original, candidate, history, row = self.conflict()
        self.assertEqual(history.pentaho_outcome, "SUCCESS")
        self.assertEqual(history.pentaho_review_state, "CONFLICTED_EVIDENCE")
        self.assertEqual(history.pentaho_identity_state, "CONFIRMED")
        self.assertEqual(candidate.processing_status, "UNRESOLVED")
        self.assertEqual(row.category, "EXECUTION_OUTCOME")
        self.assertGreaterEqual(len(row.context["prior_revision_ids"]), 2)
        self.assertTrue(row.context["verification"]["attestations"])
        self.assertEqual(row.context["verification"]["fence"], self.source.fence)
        self.assertNotEqual(row.context["occurred_at"], row.context["received_at"])
        self.assertEqual(
            self.db.scalar(
                select(func.count())
                .select_from(PentahoRevision)
                .where(PentahoRevision.history_id == history.id)
            ),
            2,
        )

    def test_weaker_outcome_cannot_override_verified_projection(self):
        _, history = self.emit(self.raw(run="weaker"))
        self.profile.definition = {
            **self.profile.definition,
            "verified_pentaho_claims": ["INVOCATION", "SCHEDULER_RETRY"],
        }
        from app.data_pipelines import service as s

        self.proof.payload = {
            **self.proof.payload,
            "reader_definition_hash": s.reader_definition(self.db, self.method),
        }
        self.db.commit()
        _, same = self.emit(self.raw(outcome="FAILED", run="weaker"))
        self.assertEqual(same.id, history.id)
        self.assertEqual(history.pentaho_outcome, "SUCCESS")
        self.assertEqual(
            self.db.scalar(
                select(func.count())
                .select_from(Review)
                .where(Review.history_id == history.id)
            ),
            0,
        )

    def test_verified_correction_is_append_only_and_idempotent(self):
        _, candidate, history, row = self.conflict()
        key = uuid.uuid4().hex
        self.decide(row, "ACCEPT_VERIFIED_CLAIM", revision=1, key=key)
        self.assertEqual(history.pentaho_outcome, "FAILED")
        self.assertEqual(history.pentaho_review_state, "CLEAR")
        self.assertEqual(candidate.processing_status, "REVIEWED")
        self.decide(row, "ACCEPT_VERIFIED_CLAIM", revision=1, key=key)
        decisions = list(
            self.db.scalars(select(Decision).where(Decision.review_id == row.id))
        )
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0].projection_before["pentaho_outcome"], "SUCCESS")
        self.assertEqual(decisions[0].projection_after["pentaho_outcome"], "FAILED")
        self.assertEqual(
            self.db.scalar(
                select(func.count())
                .select_from(PentahoRevision)
                .where(PentahoRevision.history_id == history.id)
            ),
            2,
        )
        self.assertTrue(
            self.db.scalar(
                select(SecurityAuditEvent.id).where(
                    SecurityAuditEvent.target_id == str(row.id)
                )
            )
        )

    def test_reject_preserves_outcome_and_defer_does_not_resolve(self):
        _, _, history, row = self.conflict()
        self.decide(row, "DEFER")
        self.assertEqual(row.status, "OPEN")
        self.assertEqual(row.revision, 2)
        self.assertEqual(history.pentaho_review_state, "CONFLICTED_EVIDENCE")
        self.decide(row)
        self.assertEqual(history.pentaho_outcome, "SUCCESS")
        self.assertEqual(history.pentaho_review_state, "CLEAR")
        self.assertEqual(row.status, "REJECTED")

    def test_stale_revision_and_changed_idempotency_are_rejected(self):
        _, _, _, row = self.conflict()
        key = uuid.uuid4().hex
        self.decide(row, "DEFER", key=key)
        for kwargs in ({"revision": 1}, {"key": key}):
            with self.assertRaises(HTTPException) as error:
                self.decide(row, **kwargs)
            self.assertEqual(error.exception.status_code, 409)
            self.db.rollback()

    def test_concurrent_reviewers_have_one_committed_winner(self):
        _, _, _, row = self.conflict()
        resource_id, review_id = self.resource.id, row.id

        def worker(action, user):
            with SessionLocal() as db:
                from app.unified.models import MonitoringResource

                resource = db.get(MonitoringResource, resource_id)
                try:
                    with self.adjudicator(user):
                        review.decide(
                            db,
                            resource,
                            review_id,
                            user.id,
                            action,
                            1,
                            uuid.uuid4().hex,
                            "Independent concurrent native evidence decision",
                        )
                        db.commit()
                    return "COMMITTED"
                except HTTPException as e:
                    db.rollback()
                    return e.status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            a = pool.submit(worker, "ACCEPT_VERIFIED_CLAIM", self.user)
            b = pool.submit(worker, "REJECT_CLAIM", self.reviewer)
            results = [a.result(timeout=20), b.result(timeout=20)]
        self.assertCountEqual(results, ["COMMITTED", 409])
        self.db.expire_all()
        self.assertEqual(
            self.db.scalar(
                select(func.count())
                .select_from(Decision)
                .where(Decision.review_id == review_id)
            ),
            1,
        )

    def test_alias_collision_never_reassigns_confirmed_aliases(self):
        _, original = self.emit(self.raw(run="first-run"))
        event, _ = self.emit(self.raw(run="different-run"))
        row = self.db.scalar(select(Review).where(Review.event_id == event.id))
        aliases = [
            (a.alias_key, a.history_id)
            for a in self.db.scalars(
                select(PentahoAlias).where(PentahoAlias.history_id == original.id)
            )
        ]
        with self.assertRaises(HTTPException):
            self.decide(row, "ACCEPT_VERIFIED_CLAIM")
        self.db.rollback()
        self.decide(row)
        self.assertEqual(
            aliases,
            [
                (a.alias_key, a.history_id)
                for a in self.db.scalars(
                    select(PentahoAlias).where(PentahoAlias.history_id == original.id)
                )
            ],
        )
        self.assertEqual(original.pentaho_outcome, "SUCCESS")

    def test_verified_legacy_adoption_requires_explicit_review(self):
        from app.pipeline_adapters.pentaho_observations import normalize_observation

        raw = self.raw(invocation="legacy-run")
        identity = normalize_observation(raw, self.cfg, str(self.org.id))["event"][
            "execution_id"
        ]
        legacy = JobOrderHistory(
            job_order_id=self.resource.job_order_id,
            provider_execution_id=identity,
            status=ExecutionStatus.SUCCESS,
            execution_type=ExecutionType.SCHEDULED,
        )
        self.db.add(legacy)
        self.db.commit()
        event, _ = self.emit(raw)
        row = self.db.scalar(select(Review).where(Review.event_id == event.id))
        self.assertEqual(row.category, "LEGACY_ADOPTION")
        self.assertIsNone(legacy.pentaho_resource_id)
        self.decide(row, "ADOPT_LEGACY")
        self.assertEqual(legacy.pentaho_resource_id, self.resource.id)
        self.assertEqual(legacy.pentaho_outcome, "SUCCESS")
        self.assertEqual(event.history_id, legacy.id)

    def test_retry_authority_conflict_not_resolvable_as_execution_outcome(self):
        _, history = self.emit(
            self.raw(outcome="FAILED", run="retry-review", retry="PENDING")
        )
        event, _ = self.emit(
            self.raw(outcome="FAILED", run="retry-review", retry="EXHAUSTED")
        )
        row = self.db.scalar(select(Review).where(Review.event_id == event.id))
        self.assertEqual(row.category, "RETRY_RELATIONSHIP")
        self.assertEqual(history.pentaho_lifecycle, "WAITING_FOR_RETRY")
        with self.assertRaises(HTTPException):
            self.decide(row, "ACCEPT_VERIFIED_CLAIM")
        self.db.rollback()

    def test_identity_quarantine_blocks_outcome_correction(self):
        _, _, history, row = self.conflict()
        self.emit(self.raw(run="conflicting-native-run"))
        self.assertEqual(history.pentaho_identity_state, "REVIEW_REQUIRED")
        with self.assertRaises(HTTPException) as e:
            self.decide(row, "ACCEPT_VERIFIED_CLAIM")
        self.assertEqual(e.exception.status_code, 409)
        self.db.rollback()
        self.assertEqual(history.pentaho_outcome, "SUCCESS")

    def test_ordinary_investigator_has_no_implicit_adjudication_privilege(self):
        _, _, _, row = self.conflict()
        with execution.PentahoExecutionTests.operator(self):
            with self.assertRaises(HTTPException) as error:
                review.decide(
                    self.db,
                    self.resource,
                    row.id,
                    self.user.id,
                    "REJECT_CLAIM",
                    1,
                    uuid.uuid4().hex,
                    "Unauthorized investigation must not decide identity",
                )
            self.assertEqual(error.exception.status_code, 403)

    def test_cross_customer_decision_denied_and_database_fk_rejects(self):
        _, candidate, _, row = self.conflict()
        lab = execution.PentahoExecutionTests(methodName="runTest")
        try:
            lab.setUp()
            with self.adjudicator():
                with self.assertRaises(HTTPException) as error:
                    review.decide(
                        self.db,
                        lab.resource,
                        row.id,
                        self.user.id,
                        "REJECT_CLAIM",
                        1,
                        uuid.uuid4().hex,
                        "Foreign customer reference must not be accessible",
                    )
                self.assertEqual(error.exception.status_code, 403)
            self.db.rollback()
            with self.assertRaises(DBAPIError):
                with self.db.begin_nested():
                    self.db.execute(
                        text(
                            "INSERT INTO pentaho_evidence_reviews(id,organization_id,resource_id,job_order_id,event_id,category,claim,status,revision,context,created_at) VALUES(:id,:org,:resource,:job,:event,'AMBIGUOUS_IDENTITY','IDENTITY','OPEN',1,'{}',now())"
                        ),
                        dict(
                            id=uuid.uuid4(),
                            org=lab.org.id,
                            resource=self.resource.id,
                            job=self.resource.job_order_id,
                            event=candidate.id,
                        ),
                    )
        finally:
            lab.doCleanups()

    def test_review_context_decisions_and_raw_history_are_immutable(self):
        _, _, _, row = self.conflict()
        self.decide(row, "DEFER")
        for statement in (
            "UPDATE pentaho_evidence_reviews SET context='{}' WHERE id=:id",
            "DELETE FROM pentaho_evidence_reviews WHERE id=:id",
            "UPDATE pentaho_evidence_decisions SET reason='tampered' WHERE review_id=:id",
            "DELETE FROM pentaho_evidence_decisions WHERE review_id=:id",
        ):
            with self.assertRaises(DBAPIError):
                with self.db.begin_nested():
                    self.db.execute(text(statement), {"id": row.id})

    def test_duplicate_and_late_start_do_not_clear_conflict_or_regress(self):
        raw = self.raw(run="late-review", observation_id="fixed-observation")
        _, history = self.emit(raw)
        self.emit(raw)
        self.assertEqual(len(self.attempts(history)), 1)
        candidate, _ = self.emit(self.raw(outcome="FAILED", run="late-review"))
        row = self.db.scalar(select(Review).where(Review.event_id == candidate.id))
        snapshot = review.snapshot(history)
        self.emit(self.raw(outcome="RUNNING", run="late-review"))
        self.assertEqual(review.snapshot(history), snapshot)
        self.assertEqual(
            self.db.scalar(
                select(func.count())
                .select_from(Review)
                .where(Review.event_id == candidate.id)
            ),
            1,
        )
        self.assertEqual(row.status, "OPEN")

    def test_legal_hold_pins_unverified_review_raw_without_attempt_revision(self):
        from datetime import timedelta
        from app.data_pipelines import service as s
        from app.data_pipelines.models import PipelineEvidence, PipelineHold

        self.profile.definition = {
            **self.profile.definition,
            "verified_pentaho_claims": [],
        }
        self.proof.payload = {
            **self.proof.payload,
            "reader_definition_hash": s.reader_definition(self.db, self.method),
        }
        self.db.commit()
        event, history = self.emit(self.raw())
        self.assertIsNone(history)
        row = self.db.scalar(select(Review).where(Review.event_id == event.id))
        raw = self.db.get(PipelineEvidence, row.source_evidence_id)
        raw.created_at = s.clock(self.db) - timedelta(days=40)
        self.db.add(
            PipelineHold(
                organization_id=self.org.id,
                source_id=self.source.id,
                kind="LEGAL",
                reference="controlled-review-hold",
                actor_id=self.user.id,
            )
        )
        self.db.commit()
        self.assertIsNone(
            self.db.scalar(
                select(PentahoRevision.id).where(PentahoRevision.event_id == event.id)
            )
        )
        s.cleanup(self.db)
        self.db.commit()
        self.assertIsNotNone(self.db.get(PipelineEvidence, raw.id))
        self.assertIsNotNone(self.db.get(Review, row.id))
        with self.assertRaises(HTTPException):
            self.decide(row, "ACCEPT_VERIFIED_CLAIM")
        self.db.rollback()

    def test_closed_incident_not_reopened_by_evidence_correction(self):
        from app.models import OperationalIncident
        from app.data_pipelines.service import clock

        _, _, history, row = self.conflict()
        incident = OperationalIncident(
            organization_id=self.org.id,
            episode_key="controlled-closed-" + uuid.uuid4().hex,
            source_kind="ETL",
            source_reference=str(history.id),
            history_id=history.id,
            title="Controlled historical closed incident",
            severity="CRITICAL",
            status="CLOSED",
            condition_status="RECOVERED",
            opened_at=clock(self.db),
            resolved_at=clock(self.db),
        )
        self.db.add(incident)
        self.db.commit()
        self.decide(row, "ACCEPT_VERIFIED_CLAIM")
        self.db.refresh(incident)
        self.assertEqual(incident.status, "CLOSED")
        self.assertEqual(incident.condition_status, "RECOVERED")
        self.assertEqual(row.context["incident_action"], "NONE")
        self.assertEqual(
            row.context["notification_eligibility"], "NOT_EVALUATED_SPRINT05"
        )

    def test_same_native_observation_id_with_changed_evidence_is_reviewed(self):
        _, history = self.emit(
            self.raw(run="observation-reuse", observation_id="same-native-observation")
        )
        event, _ = self.emit(
            self.raw(
                run="observation-reuse",
                observation_id="same-native-observation",
                outcome="FAILED",
            )
        )
        row = self.db.scalar(select(Review).where(Review.event_id == event.id))
        self.assertEqual(row.category, "NATIVE_ALIAS_CONFLICT")
        self.assertEqual(history.pentaho_outcome, "SUCCESS")
        self.assertEqual(
            self.db.scalar(
                select(func.count())
                .select_from(PentahoRevision)
                .where(PentahoRevision.history_id == history.id)
            ),
            1,
        )
        self.decide(row)
        self.assertEqual(history.pentaho_identity_state, "CONFIRMED")

    def test_legacy_conflicting_outcome_cannot_be_adopted(self):
        from app.pipeline_adapters.pentaho_observations import normalize_observation

        raw = self.raw(invocation="legacy-conflicting")
        identity = normalize_observation(raw, self.cfg, str(self.org.id))["event"][
            "execution_id"
        ]
        legacy = JobOrderHistory(
            job_order_id=self.resource.job_order_id,
            provider_execution_id=identity,
            status=ExecutionStatus.FAILED,
            execution_type=ExecutionType.SCHEDULED,
        )
        self.db.add(legacy)
        self.db.commit()
        event, _ = self.emit(raw)
        row = self.db.scalar(select(Review).where(Review.event_id == event.id))
        with self.assertRaises(HTTPException):
            self.decide(row, "ADOPT_LEGACY")
        self.db.rollback()
        self.assertIsNone(legacy.pentaho_resource_id)
        self.assertEqual(legacy.status, ExecutionStatus.FAILED)

    def test_batched_conflict_preserves_first_verified_projection(self):
        from unittest.mock import patch

        with patch("app.unified.reconstruction.reduce_execution", return_value=None):
            first, _ = self.emit(self.raw(run="batched-native"))
            self.emit(self.raw(run="batched-native", outcome="FAILED"))
        history = reduce_execution(
            self.db, self.resource, first.payload["execution_id"]
        )
        self.db.commit()
        self.assertEqual(history.pentaho_outcome, "SUCCESS")
        self.assertEqual(history.pentaho_review_state, "CONFLICTED_EVIDENCE")

    def test_pre_sprint04_quarantine_backfill_is_bounded_and_idempotent(self):
        event, history = self.emit(self.raw())
        legacy = NormalizedEvent(
            organization_id=self.org.id,
            resource_id=self.resource.id,
            external_key="controlled-pre-review-" + uuid.uuid4().hex,
            source_kind="PENTAHO",
            history_id=history.id,
            observed_at=event.observed_at,
            received_at=event.received_at,
            payload=event.payload,
            processing_status="UNRESOLVED",
            processing_error="PENTAHO_CONFLICT_PENDING",
        )
        self.db.add(legacy)
        self.db.commit()
        self.assertEqual(review.synchronize_reviews(self.db, self.resource, limit=1), 1)
        self.db.commit()
        self.assertEqual(review.synchronize_reviews(self.db, self.resource, limit=1), 0)
        self.assertEqual(history.pentaho_outcome, "SUCCESS")
        self.assertEqual(history.pentaho_review_state, "CONFLICTED_EVIDENCE")

    def test_later_retry_policy_cannot_silently_regress_terminal_projection(self):
        _, history = self.emit(
            self.raw(run="terminal-policy", outcome="FAILED", retry="EXHAUSTED")
        )
        event, _ = self.emit(
            self.raw(
                run="terminal-policy",
                outcome="FAILED",
                retry="PENDING",
                authority_revision=2,
            )
        )
        row = self.db.scalar(select(Review).where(Review.event_id == event.id))
        self.assertEqual(row.category, "RETRY_RELATIONSHIP")
        self.assertEqual(history.pentaho_outcome, "FAILED")
        self.assertEqual(history.pentaho_lifecycle, "TERMINAL")
        self.assertEqual(
            self.attempts(history)[0].retry_authority["retry_state"], "EXHAUSTED"
        )

    def test_reviewed_correction_cannot_automatically_drive_incident_conditions(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        from app.unified.engines import evaluate_executions
        from app.data_pipelines.service import clock

        _, _, history, row = self.conflict()
        self.decide(row, "ACCEPT_VERIFIED_CLAIM")
        with patch("app.unified.engines.condition") as conditions, patch(
            "app.unified.engines.source_readiness", return_value={"ready": True}
        ):
            evaluate_executions(
                self.db,
                self.resource,
                SimpleNamespace(configuration={}),
                clock(self.db),
            )
        self.assertEqual(conditions.call_count, 1)
        self.assertEqual(conditions.call_args.args[2], "ETL_TELEMETRY")
        self.assertTrue(
            history.source_evidence["pentaho_adjudication"][
                "operational_reassessment_required"
            ]
        )

    def test_operator_can_flag_recovery_identity_without_creating_recovery_link(self):
        event, history = self.emit(self.raw(run="observed-recovery"))
        key = uuid.uuid4().hex
        with self.adjudicator():
            row = review.flag_recovery_identity(
                self.db,
                self.resource,
                event.id,
                self.user.id,
                key,
                "Observed recovery association needs identity review",
            )
            self.db.commit()
            again = review.flag_recovery_identity(
                self.db,
                self.resource,
                event.id,
                self.user.id,
                key,
                "Observed recovery association needs identity review",
            )
            self.db.commit()
        self.assertEqual(again.id, row.id)
        self.assertEqual(row.category, "RECOVERY_IDENTITY")
        self.assertEqual(history.pentaho_identity_state, "REVIEW_REQUIRED")
        with self.assertRaises(HTTPException):
            self.decide(row, "ACCEPT_VERIFIED_CLAIM")
        self.db.rollback()
        self.decide(row, "REJECT_CLAIM")
        self.assertEqual(history.pentaho_identity_state, "CONFIRMED")
        self.assertEqual(history.pentaho_outcome, "SUCCESS")

    def test_raw_acceptance_order_survives_reverse_connector_inventory(self):
        from app.data_pipelines import service as s
        from app.unified.reconstruction import ingest_connector
        from types import SimpleNamespace

        for number, outcome in enumerate(("SUCCESS", "FAILED"), start=1):
            ticket = s.acquire(self.db, self.source.id, uuid.uuid4())
            self.db.commit()
            s.accept(
                self.db,
                ticket,
                [
                    {
                        "key": "reverse-connector-" + str(number),
                        "pentaho_observation": self.raw(
                            run="reverse-native", outcome=outcome
                        ),
                        "evidence_origin": "CONTROLLED_FIXTURE",
                    }
                ],
                {
                    "sources": {
                        "/controlled/pentaho.jsonl": {
                            "device": 1,
                            "inode": 2,
                            "offset": number * 100,
                        }
                    }
                },
                False,
            )
            self.db.commit()
        ingest_connector(
            self.db, self.resource, SimpleNamespace(configuration={}, version=1)
        )
        self.db.commit()
        events = list(
            self.db.scalars(
                select(NormalizedEvent)
                .where(NormalizedEvent.resource_id == self.resource.id)
                .order_by(NormalizedEvent.received_at, NormalizedEvent.id)
            )
        )
        self.assertEqual(
            events[0].payload["pentaho_identity"]["native_outcome"], "FAILED"
        )
        history = self.db.get(JobOrderHistory, events[0].history_id)
        self.assertEqual(history.pentaho_outcome, "SUCCESS")
        self.assertEqual(history.pentaho_review_state, "CONFLICTED_EVIDENCE")
        self.assertTrue(
            all(e.payload["pentaho_verification"]["accepted_at"] for e in events)
        )

    def test_pending_legacy_backfill_cannot_be_bypassed_by_review(self):
        original, _, history, row = self.conflict()
        pending = NormalizedEvent(
            organization_id=self.org.id,
            resource_id=self.resource.id,
            external_key="controlled-unqueued-" + uuid.uuid4().hex,
            source_kind="PENTAHO",
            history_id=history.id,
            observed_at=original.observed_at,
            received_at=original.received_at,
            payload=original.payload,
            processing_status="UNRESOLVED",
            processing_error="PENTAHO_IDENTITY_CONFLICT",
        )
        self.db.add(pending)
        self.db.commit()
        with self.assertRaises(HTTPException) as error:
            self.decide(row, "ACCEPT_VERIFIED_CLAIM")
        self.assertEqual(error.exception.status_code, 409)
        self.db.rollback()
        self.decide(row, "REJECT_CLAIM")
        self.assertEqual(history.pentaho_identity_state, "REVIEW_REQUIRED")
        self.assertEqual(history.pentaho_outcome, "SUCCESS")
