"""Owned PostgreSQL execution/attempt acceptance, with explicit controlled proofs.

No fixture constitutes installed Pentaho acceptance or runtime certification.
"""

import os
import uuid
import unittest
from types import SimpleNamespace
from contextlib import contextmanager
from datetime import timedelta
from sqlalchemy import select, func, text
from sqlalchemy.exc import DBAPIError
from fastapi import HTTPException
import app.main  # noqa: F401
from app.models import JobOrderHistory
from app.security.models import User, SecurityAuditEvent
from app.security.permission_catalog import PROVIDER_ID
from app.security.scope import Principal, current_principal
from app.security.passwords import hash_password
from app.data_pipelines import service as s
from app.data_pipelines.models import (
    PipelineJob,
    PipelineAssociation,
    PipelineEvidence,
    PipelineHold,
)
from app.data_pipelines.bridge import create_job_resource
from app.unified.models import NormalizedEvent
from app.unified.pentaho_models import (
    PentahoAttempt,
    PentahoAlias,
    PentahoRevision,
    PentahoRecoveryDecision,
)
from app.unified.reconstruction import ingest_connector
from app.unified import pentaho_recovery as recovery
from tests import test_pipeline_ownership_v16 as ownership
from tests.test_pentaho_r1 import observation, END


@unittest.skipUnless(
    os.getenv("OPSCONTROL_V16_ACCEPTANCE") == "1",
    "Owned disposable PostgreSQL required",
)
class PentahoExecutionTests(unittest.TestCase):
    def setUp(self):
        ownership.OwnershipTests.setUp(self)
        self.cfg, _, _ = ownership.OwnershipTests._pentaho_r1_fixture(
            self,
            surface=getattr(self, "surface", "KITCHEN_PAN"),
            workload_kind=getattr(self, "workload_kind", "JOB"),
        )
        self.job = PipelineJob(
            organization_id=self.org.id,
            integration_id=self.integration.id,
            native_id=self.cfg["native_job_id"],
            name="Controlled native execution",
            origin="MANUAL",
            selected=True,
        )
        self.db.add(self.job)
        self.db.flush()
        self.db.info["pipeline_initial_job_binding"] = self.job.id
        self.resource = create_job_resource(self.db, self.integration, self.job)
        self.job.resource_id = self.resource.id
        self.db.add(
            PipelineAssociation(
                organization_id=self.org.id,
                method_id=self.method.id,
                job_id=self.job.id,
                generation=self.source.generation,
                confirmed_by=self.user.id,
            )
        )
        self.profile.evidence_status = "RUNTIME_VERIFIED"
        self.profile.definition = {
            "supported_methods": [self.source.method_type],
            "verified_pentaho_claims": [
                "INVOCATION",
                "EXECUTION_OUTCOME",
                "SCHEDULER_RETRY",
            ],
        }
        self.proof.payload = {
            "runtime_origin": "AUTHENTICATED_RUNTIME",
            "fixture_state": "CONTROLLED_PREVERIFIED_NATIVE_AUTHORITY",
            "reader_definition_hash": s.reader_definition(self.db, self.method),
            "evidence": {
                "surface": self.cfg["surface"],
                "exact_build": self.cfg["exact_build"],
            },
        }
        self.reviewer = User(
            username="controlled-review-" + uuid.uuid4().hex,
            full_name="Controlled reviewer",
            password_hash=hash_password(uuid.uuid4().hex),
            active=True,
            service_provider_id=PROVIDER_ID,
        )
        self.db.add(self.reviewer)
        self.db.commit()
        self.counter = 0

    def raw(
        self,
        invocation="invocation-1",
        outcome="SUCCESS",
        run=None,
        order=1,
        retry="EXHAUSTED",
        authority_revision=1,
        **changes
    ):
        kwargs = {
            "native_execution_id": invocation,
            "invocation_id": invocation,
            "observation_id": str(uuid.uuid4()),
        }
        if outcome in {"RUNNING", "EXITED"}:
            kwargs.update(
                state="PROCESS_STARTED" if outcome == "RUNNING" else "PROCESS_EXITED",
                exit_code=0,
            )
        else:
            kwargs.update(
                state="EXECUTION_RESULT",
                result={
                    "invocation_id": invocation,
                    "source": "NATIVE_STRUCTURED_LOG",
                    "evidence_sha256": "a" * 64,
                    "status": outcome,
                    "ended_at": END,
                },
            )
        if run:
            kwargs["scheduler_identity"] = {
                "authority_id": "controlled-scheduler",
                "native_run_id": run,
                "native_attempt_id": "attempt-" + str(order),
                "attempt_order": order,
                "retry_state": retry,
                "authority_revision": authority_revision,
                "authority_evidence_sha256": "b" * 64,
                **(
                    {"previous_attempt_id": "attempt-" + str(order - 1)}
                    if order > 1
                    else {}
                ),
            }
        return observation(self.cfg, **{**kwargs, **changes})

    def emit(self, raw):
        self.counter += 1
        key = "controlled-offset-" + str(self.counter)
        checkpoint = {
            "sources": {
                "/controlled/pentaho.jsonl": {
                    "device": 1,
                    "inode": 2,
                    "offset": self.counter * 100,
                }
            }
        }
        ticket = s.acquire(self.db, self.source.id, uuid.uuid4())
        self.db.commit()
        s.accept(
            self.db,
            ticket,
            [
                {
                    "key": key,
                    "pentaho_observation": raw,
                    "evidence_origin": "CONTROLLED_FIXTURE",
                }
            ],
            checkpoint,
            False,
        )
        self.db.commit()
        evidence = self.db.scalar(
            select(PipelineEvidence).where(
                PipelineEvidence.source_id == self.source.id,
                PipelineEvidence.external_key == key,
            )
        )
        ingest_connector(
            self.db, self.resource, SimpleNamespace(configuration={}, version=1)
        )
        self.db.commit()
        event = self.db.scalar(
            select(NormalizedEvent).where(
                NormalizedEvent.resource_id == self.resource.id,
                NormalizedEvent.external_key == "v16:" + str(evidence.id),
            )
        )
        return event, (
            self.db.get(JobOrderHistory, event.history_id) if event.history_id else None
        )

    def attempts(self, history):
        return list(
            self.db.scalars(
                select(PentahoAttempt)
                .where(PentahoAttempt.history_id == history.id)
                .order_by(PentahoAttempt.attempt_order)
            )
        )

    @contextmanager
    def operator(self, user=None, roles=None):
        user = user or self.user
        principal = Principal(
            user.id,
            user.username,
            False,
            roles if roles is not None else {self.org.id: "operator"},
        )
        token = current_principal.set(principal)
        try:
            yield
        finally:
            current_principal.reset(token)

    def failed_and_recovery(self):
        a, failed = self.emit(self.raw("failed-native", "FAILED", run="failed-logical"))
        b, restored = self.emit(
            self.raw("manual-native", "SUCCESS", execution_origin="MANUAL")
        )
        return a, failed, b, restored

    def test_single_success_has_canonical_history_attempt_and_aliases(self):
        event, h = self.emit(self.raw())
        self.assertEqual(
            (h.pentaho_lifecycle, h.pentaho_outcome), ("TERMINAL", "SUCCESS")
        )
        self.assertEqual(h.status.value, "SUCCESS")
        self.assertEqual(len(self.attempts(h)), 1)
        self.assertEqual(h.job_order_id, self.resource.job_order_id)
        self.assertEqual(event.processing_status, "PROCESSED")
        self.assertEqual(
            self.db.scalar(
                select(func.count())
                .select_from(PentahoAlias)
                .where(PentahoAlias.history_id == h.id)
            ),
            1,
        )

    def test_verified_failed_attempt_pending_then_success_after_retry(self):
        _, h = self.emit(self.raw("try-1", "FAILED", run="run-1", retry="PENDING"))
        self.assertEqual(
            (h.pentaho_lifecycle, h.pentaho_outcome), ("WAITING_FOR_RETRY", None)
        )
        _, next_h = self.emit(self.raw("try-2", "SUCCESS", run="run-1", order=2))
        self.assertEqual(h.id, next_h.id)
        self.assertEqual(h.pentaho_outcome, "SUCCESS_AFTER_RETRY")
        self.assertEqual([a.outcome for a in self.attempts(h)], ["FAILED", "SUCCESS"])

    def test_verified_final_failure_exhausted_is_terminal(self):
        _, h = self.emit(self.raw(outcome="FAILED", run="run-final"))
        self.assertEqual(
            (h.pentaho_lifecycle, h.pentaho_outcome), ("TERMINAL", "FAILED")
        )

    def test_missing_retry_authority_never_implies_exhaustion(self):
        _, h = self.emit(self.raw(outcome="FAILED"))
        self.assertEqual(self.attempts(h)[0].outcome, "FAILED")
        self.assertEqual(h.pentaho_lifecycle, "IDENTIFIED")
        self.assertIsNone(h.pentaho_outcome)
        self.assertEqual(h.status.value, "UNKNOWN")

    def test_process_exit_alone_unknown_and_scheduler_alone_not_success(self):
        _, h = self.emit(self.raw(outcome="EXITED", run="scheduler-exit"))
        self.assertIsNone(h.pentaho_outcome)
        self.assertEqual(self.attempts(h)[0].outcome, "UNKNOWN")
        self.assertIsNone(h.ended_at)

    def test_duplicate_observations_keep_raw_records_but_not_duplicate_attempts_revisions(
        self,
    ):
        raw = self.raw()
        first, h = self.emit(raw)
        second, other = self.emit(raw)
        self.assertNotEqual(first.id, second.id)
        self.assertEqual(h.id, other.id)
        self.assertEqual(len(self.attempts(h)), 1)
        self.assertEqual(
            self.db.scalar(
                select(func.count())
                .select_from(PentahoRevision)
                .where(PentahoRevision.history_id == h.id)
            ),
            1,
        )

    def test_out_of_order_start_and_earlier_retry_do_not_regress_success(self):
        _, h = self.emit(self.raw("try-2", "SUCCESS", run="out-of-order", order=2))
        _, same = self.emit(
            self.raw("try-1", "FAILED", run="out-of-order", retry="PENDING")
        )
        _, again = self.emit(
            self.raw("try-2", "RUNNING", run="out-of-order", order=2, retry="UNKNOWN")
        )
        self.assertEqual(h.id, same.id)
        self.assertEqual(again.pentaho_outcome, "SUCCESS_AFTER_RETRY")
        self.assertEqual(len(self.attempts(h)), 2)

    def test_unverified_retry_proposal_remains_separate_and_quarantined(self):
        self.profile.definition = {
            "supported_methods": ["FILE_LOG"],
            "verified_pentaho_claims": ["INVOCATION", "EXECUTION_OUTCOME"],
        }
        self.db.commit()
        a, h = self.emit(
            self.raw("independent-1", "FAILED", run="claimed-run", retry="PENDING")
        )
        b, other = self.emit(
            self.raw("independent-2", "SUCCESS", run="claimed-run", order=2)
        )
        self.assertNotEqual(h.id, other.id)
        self.assertEqual(a.processing_status, "UNRESOLVED")
        self.assertEqual(b.processing_status, "UNRESOLVED")
        self.assertTrue(self.job.selected)
        self.assertEqual(self.job.native_id, self.cfg["native_job_id"])

    def test_conflicting_native_alias_does_not_retarget_confirmed_run(self):
        _, h = self.emit(
            self.raw("same-native", "RUNNING", run="original-run", retry="PENDING")
        )
        ids = {
            a.id
            for a in self.db.scalars(
                select(PentahoAlias).where(PentahoAlias.history_id == h.id)
            )
        }
        event, _ = self.emit(self.raw("same-native", "SUCCESS", run="different-run"))
        self.assertEqual(event.processing_status, "UNRESOLVED")
        self.assertEqual(
            ids,
            {
                a.id
                for a in self.db.scalars(
                    select(PentahoAlias).where(PentahoAlias.history_id == h.id)
                )
            },
        )
        self.assertTrue(self.job.selected)

    def test_native_retry_revision_advances_without_rewriting_prior_evidence(self):
        _, h = self.emit(
            self.raw(outcome="FAILED", run="policy-change", retry="PENDING")
        )
        _, same = self.emit(
            self.raw(outcome="FAILED", run="policy-change", authority_revision=2)
        )
        self.assertEqual(h.id, same.id)
        self.assertEqual(h.pentaho_outcome, "FAILED")
        revisions = list(
            self.db.scalars(
                select(PentahoRevision)
                .where(PentahoRevision.history_id == h.id)
                .order_by(PentahoRevision.revision)
            )
        )
        self.assertEqual(len(revisions), 2)
        self.assertEqual(
            revisions[0].payload["identity"]["scheduler"]["retry_state"], "PENDING"
        )

    def test_manual_recovery_keeps_failed_original_and_distinct_identity(self):
        a, failed, b, restored = self.failed_and_recovery()
        self.assertNotEqual(failed.id, restored.id)
        self.assertEqual(restored.execution_type.value, "MANUAL")
        with self.operator():
            link = recovery.propose(
                self.db,
                failed,
                restored.id,
                self.user.id,
                uuid.uuid4().hex,
                "Controlled operator association with native evidence",
                [a.id, b.id],
            )
            self.db.commit()
        with self.operator(self.reviewer):
            recovery.review(
                self.db,
                failed,
                link.id,
                self.reviewer.id,
                uuid.uuid4().hex,
                "Independent evidence review confirms association",
                "CONFIRM",
                1,
            )
            self.db.commit()
        self.assertEqual(link.status, "CONFIRMED")
        self.assertEqual(failed.pentaho_outcome, "FAILED")
        self.assertEqual(restored.pentaho_outcome, "SUCCESS")

    def test_many_to_many_recovery_links_and_reversal_are_append_only(self):
        a, failed, b, restored = self.failed_and_recovery()
        c, failed2 = self.emit(self.raw("failed-2", "FAILED", run="failed-logical-2"))
        d, restored2 = self.emit(
            self.raw("manual-2", "SUCCESS", execution_origin="MANUAL")
        )
        with self.operator():
            links = [
                recovery.propose(
                    self.db,
                    x,
                    y.id,
                    self.user.id,
                    uuid.uuid4().hex,
                    "Controlled native identity relationship evidence",
                    [ex.id, ey.id],
                )
                for ex, x, ey, y in [
                    (a, failed, b, restored),
                    (c, failed2, b, restored),
                    (a, failed, d, restored2),
                ]
            ]
            self.db.commit()
        with self.operator(self.reviewer):
            for link in links:
                original = self.db.get(JobOrderHistory, link.failed_history_id)
                recovery.review(
                    self.db,
                    original,
                    link.id,
                    self.reviewer.id,
                    uuid.uuid4().hex,
                    "Independent association evidence confirmed",
                    "CONFIRM",
                    1,
                )
            self.db.commit()
            recovery.review(
                self.db,
                failed,
                links[0].id,
                self.reviewer.id,
                uuid.uuid4().hex,
                "Observed relationship reversed after operator review",
                "REVERSE",
                2,
            )
            self.db.commit()
        self.assertEqual(links[0].status, "REVERSED")
        self.assertEqual(
            self.db.scalar(
                select(func.count())
                .select_from(PentahoRecoveryDecision)
                .where(PentahoRecoveryDecision.link_id == links[0].id)
            ),
            3,
        )
        self.assertEqual(failed.pentaho_outcome, "FAILED")
        self.assertEqual(
            self.db.scalar(
                select(func.count())
                .select_from(SecurityAuditEvent)
                .where(SecurityAuditEvent.target_id == str(links[0].id))
            ),
            3,
        )

    def test_recovery_self_confirmation_and_viewer_mutation_are_denied(self):
        a, failed, b, restored = self.failed_and_recovery()
        with self.operator():
            link = recovery.propose(
                self.db,
                failed,
                restored.id,
                self.user.id,
                uuid.uuid4().hex,
                "Controlled evidence relationship proposal",
                [a.id, b.id],
            )
            self.db.commit()
            with self.assertRaises(HTTPException):
                recovery.review(
                    self.db,
                    failed,
                    link.id,
                    self.user.id,
                    uuid.uuid4().hex,
                    "Self approval must be blocked",
                    "CONFIRM",
                    1,
                )
            self.db.rollback()
        with self.operator(roles={self.org.id: "viewer"}):
            with self.assertRaises(HTTPException) as caught:
                recovery.propose(
                    self.db,
                    failed,
                    restored.id,
                    self.user.id,
                    uuid.uuid4().hex,
                    "Viewer cannot change relationship",
                    [a.id, b.id],
                )
            self.assertEqual(caught.exception.status_code, 403)

    def test_cross_customer_history_and_relation_are_rejected(self):
        _, h = self.emit(self.raw())
        with self.operator(roles={}):
            with self.assertRaises(HTTPException):
                recovery.history(self.db, self.resource, h.id)
        with self.operator():
            with self.assertRaises(HTTPException):
                recovery.history(self.db, self.resource, uuid.uuid4())
        # Composite FK rejects a customer/resource different from the parent history.
        attempt = self.attempts(h)[0]
        self.db.add(
            PentahoAlias(
                organization_id=self.org.id,
                resource_id=uuid.uuid4(),
                history_id=h.id,
                attempt_id=attempt.id,
                alias_key="cross-scope",
                kind="INVOCATION",
                native_identity={},
            )
        )
        with self.assertRaises(DBAPIError):
            self.db.commit()
        self.db.rollback()

    def test_identity_quarantine_blocks_recovery_confirmation(self):
        a, failed, b, restored = self.failed_and_recovery()
        with self.operator():
            link = recovery.propose(
                self.db,
                failed,
                restored.id,
                self.user.id,
                uuid.uuid4().hex,
                "Evidence association before identity issue",
                [a.id, b.id],
            )
            self.db.commit()
        restored.pentaho_identity_state = "REVIEW_REQUIRED"
        self.db.commit()
        with self.operator(self.reviewer), self.assertRaises(HTTPException):
            recovery.review(
                self.db,
                failed,
                link.id,
                self.reviewer.id,
                uuid.uuid4().hex,
                "Cannot override identity quarantine",
                "CONFIRM",
                1,
            )
        self.db.rollback()

    def test_revision_and_alias_mutations_and_history_deletion_rejected(self):
        _, h = self.emit(self.raw())
        for sql in (
            "UPDATE pentaho_attempt_revisions SET disposition='CHANGED' WHERE history_id=:id",
            "DELETE FROM pentaho_native_aliases WHERE history_id=:id",
            "DELETE FROM job_order_histories WHERE id=:id",
        ):
            with self.assertRaises(DBAPIError):
                self.db.execute(text(sql), {"id": h.id})
                self.db.commit()
            self.db.rollback()

    def test_legal_hold_and_referenced_raw_history_survive_cleanup(self):
        _, h = self.emit(self.raw())
        revision = self.db.scalar(
            select(PentahoRevision).where(PentahoRevision.history_id == h.id)
        )
        raw = self.db.get(PipelineEvidence, revision.source_evidence_id)
        raw.created_at = s.clock(self.db) - timedelta(days=40)
        self.db.add(
            PipelineHold(
                organization_id=self.org.id,
                source_id=self.source.id,
                kind="LEGAL",
                reference="controlled-hold",
                actor_id=self.user.id,
            )
        )
        self.db.commit()
        s.cleanup(self.db)
        self.db.commit()
        self.assertIsNotNone(self.db.get(PipelineEvidence, raw.id))
        self.assertIsNotNone(self.db.get(PentahoRevision, revision.id))
        self.assertIsNotNone(self.db.get(JobOrderHistory, h.id))

    def test_stale_source_generation_does_not_accept_attempt_or_advance_checkpoint(
        self,
    ):
        previous = self.source.live_checkpoint
        ticket = s.acquire(self.db, self.source.id, uuid.uuid4())
        self.db.commit()
        self.source.generation = uuid.uuid4()
        self.db.commit()
        with self.assertRaises(s.PipelineError):
            s.accept(
                self.db,
                ticket,
                [{"key": "stale", "pentaho_observation": self.raw()}],
                {"sources": {}},
                False,
            )
        self.db.rollback()
        self.assertEqual(self.source.live_checkpoint, previous)
        self.assertIsNone(
            self.db.scalar(
                select(PipelineEvidence.id).where(
                    PipelineEvidence.source_id == self.source.id,
                    PipelineEvidence.external_key == "stale",
                )
            )
        )

    def test_cancelled_is_native_outcome_without_execution_controls(self):
        _, h = self.emit(self.raw(outcome="CANCELLED"))
        self.assertEqual(
            (h.pentaho_lifecycle, h.pentaho_outcome), ("TERMINAL", "CANCELLED")
        )
        self.assertEqual(h.status.value, "UNKNOWN")  # compatible legacy status

    def test_known_retry_predecessor_cannot_point_back_from_an_earlier_attempt(self):
        _, h = self.emit(
            self.raw("try-3", "RUNNING", run="native-order", order=3, retry="UNKNOWN")
        )
        raw = self.raw("try-2", "FAILED", run="native-order", order=2, retry="PENDING")
        raw["scheduler_identity"]["previous_attempt_id"] = "attempt-3"
        event, _ = self.emit(raw)
        self.assertEqual(event.processing_status, "UNRESOLVED")
        self.assertEqual(event.processing_error, "PENTAHO_RETRY_PREDECESSOR_CONFLICT")
        self.assertEqual(len(self.attempts(h)), 1)
        self.assertEqual(h.pentaho_identity_state, "REVIEW_REQUIRED")
