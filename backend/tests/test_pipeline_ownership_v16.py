"""Actual PostgreSQL fencing/durability tests; preverified states are controlled fixtures."""

import os, uuid, unittest
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select, func, delete
from sqlalchemy.exc import IntegrityError
import app.main  # register all parent FK targets and scope guards
from app.db.session import SessionLocal
from app.models import Organization
from app.security.models import User
from app.security.passwords import hash_password
from app.security.permission_catalog import PROVIDER_ID
from app.data_pipelines.models import *
from app.data_pipelines import service as s


@unittest.skipUnless(
    os.getenv("OPSCONTROL_V16_ACCEPTANCE") == "1", "Owned PostgreSQL fixture required"
)
class OwnershipTests(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        self.addCleanup(self.db.close)
        self.org = Organization(
            name="Controlled V16 " + str(uuid.uuid4()),
            code="V16-" + uuid.uuid4().hex[:12],
            active=True,
        )
        self.user = User(
            username="v16-" + uuid.uuid4().hex,
            password_hash=hash_password(uuid.uuid4().hex),
            full_name="Controlled Operator",
            active=True,
            platform_admin=False,
            service_provider_id=PROVIDER_ID,
        )
        self.db.add_all([self.org, self.user])
        self.db.flush()
        self.integration = PipelineIntegration(
            organization_id=self.org.id,
            name="Controlled Integration",
            platform="AIRFLOW",
            environment="TEST",
            owner_id=self.user.id,
            configuration={},
            enabled=True,
        )
        self.source = PipelineSource(
            organization_id=self.org.id,
            method_type="PLATFORM_API",
            canonical_key=uuid.uuid4().hex.ljust(64, "0"),
            identity={"physical_scope": "controlled"},
            continuity_validated=True,
            live_checkpoint={"cursor": 0},
            fence=40,
        )
        self.db.add_all([self.integration, self.source])
        self.db.flush()
        self.proof = PipelineEvidence(
            organization_id=self.org.id,
            source_id=self.source.id,
            generation=self.source.generation,
            external_key="controlled-preverified-state",
            native_job_id="dag-1",
            payload={
                "runtime_origin": "AUTHENTICATED_RUNTIME",
                "fixture_state": "HYPOTHETICAL_PREVERIFIED_PROFILE",
            },
            outcome="ACCEPTED",
            observed_at=s.clock(self.db),
        )
        self.connection = PipelineConnection(
            organization_id=self.org.id,
            integration_id=self.integration.id,
            version=1,
            configuration={},
            checksum="a" * 64,
            active=True,
        )
        self.db.add_all([self.proof, self.connection])
        self.db.flush()
        self.profile = PipelineCapability(
            organization_id=self.org.id,
            integration_id=self.integration.id,
            platform_version="2.10",
            edition="Controlled",
            deployment_type="TEST",
            definition={"supported_methods": ["PLATFORM_API"]},
            compatibility="SUPPORTED",
            evidence_status="RUNTIME_VERIFIED",
            verification_evidence_id=self.proof.id,
        )
        self.db.add(self.profile)
        self.db.flush()
        self.method = PipelineMethod(
            organization_id=self.org.id,
            integration_id=self.integration.id,
            source_id=self.source.id,
            connection_id=self.connection.id,
            capability_id=self.profile.id,
            name="API",
            transport="BACKEND",
            configuration={"method_type": "PLATFORM_API"},
            enabled=True,
            validation="VALID",
        )
        self.db.add(self.method)
        self.db.flush()
        self.proof.payload = {
            **self.proof.payload,
            "reader_definition_hash": s.reader_definition(self.db, self.method),
        }
        self.db.commit()

    def fact(self, key="record-1", native="not-selected"):
        stamp = s.clock(self.db).isoformat()
        return {
            "key": key,
            "native_job_id": native,
            "observed_at": stamp,
            "event": {
                "execution_id": "run-1",
                "jobchain": "provider-name",
                "timestamp": stamp,
                "status": "RUNNING",
                "event_type": "START",
            },
        }

    def test_token_41_expires_token_42_commits_then_delayed_41_rejected(self):
        a = s.acquire(self.db, self.source.id, uuid.uuid4())
        self.assertEqual(a["fence"], 41)
        self.db.commit()
        self.source.lease_until = s.clock(self.db) - timedelta(seconds=1)
        self.db.commit()
        b = s.acquire(self.db, self.source.id, uuid.uuid4())
        self.assertEqual(b["fence"], 42)
        self.db.commit()
        result = s.accept(self.db, b, [self.fact()], {"cursor": 42}, True)
        self.db.commit()
        self.assertEqual(result["accepted"], 1)
        before = self.db.scalar(
            select(func.count())
            .select_from(PipelineEvidence)
            .where(PipelineEvidence.source_id == self.source.id)
        )
        with self.assertRaises(s.PipelineError) as rejected:
            s.accept(self.db, a, [self.fact("delayed")], {"cursor": 41}, True)
        self.assertEqual(rejected.exception.code, "STALE_OWNER_OR_GENERATION")
        self.db.rollback()
        self.assertEqual(
            self.db.get(PipelineSource, self.source.id).live_checkpoint, {"cursor": 42}
        )
        self.assertEqual(
            self.db.scalar(
                select(func.count())
                .select_from(PipelineEvidence)
                .where(PipelineEvidence.source_id == self.source.id)
            ),
            before,
        )

    def test_evidence_constraint_failure_rolls_back_checkpoint_and_receipt(self):
        ticket = s.acquire(self.db, self.source.id, uuid.uuid4())
        self.db.commit()
        fact = self.fact()
        bad = self.fact("invalid")
        bad["event"] = {}
        bad["observed_at"] = "invalid"
        with self.assertRaises(s.PipelineError):
            s.accept(self.db, ticket, [fact, bad], {"cursor": 100}, True)
        self.db.rollback()
        self.assertEqual(
            self.db.get(PipelineSource, self.source.id).live_checkpoint, {"cursor": 0}
        )
        self.assertFalse(
            self.db.scalar(
                select(PipelineEvidence.id).where(
                    PipelineEvidence.external_key == fact["key"],
                    PipelineEvidence.source_id == self.source.id,
                )
            )
        )

    def test_generation_change_rejects_old_ticket(self):
        ticket = s.acquire(self.db, self.source.id, uuid.uuid4())
        self.db.commit()
        self.source.generation = uuid.uuid4()
        self.db.commit()
        with self.assertRaises(s.PipelineError):
            s.accept(self.db, ticket, [self.fact()], {}, True)
        self.db.rollback()

    def test_shared_integration_pause_and_composed_manual_hold(self):
        other = PipelineIntegration(
            organization_id=self.org.id,
            name="Shared",
            platform="AIRFLOW",
            environment="TEST",
            owner_id=self.user.id,
            configuration={},
            enabled=True,
        )
        self.db.add(other)
        self.db.flush()
        connection = PipelineConnection(
            organization_id=self.org.id,
            integration_id=other.id,
            version=1,
            configuration={},
            checksum="b" * 64,
            active=True,
        )
        profile = PipelineCapability(
            organization_id=self.org.id,
            integration_id=other.id,
            platform_version="2.10",
            edition="Controlled",
            deployment_type="TEST",
            definition={"supported_methods": ["PLATFORM_API"]},
            compatibility="SUPPORTED",
            evidence_status="RUNTIME_VERIFIED",
            verification_evidence_id=self.proof.id,
        )
        self.db.add_all([connection, profile])
        self.db.flush()
        self.db.add(
            PipelineMethod(
                organization_id=self.org.id,
                integration_id=other.id,
                source_id=self.source.id,
                connection_id=connection.id,
                capability_id=profile.id,
                name="Shared reference",
                transport="BACKEND",
                configuration={"method_type": "PLATFORM_API"},
                enabled=True,
                validation="VALID",
            )
        )
        self.db.commit()
        ticket = s.acquire(self.db, self.source.id, uuid.uuid4())
        self.db.commit()
        s.pause(self.db, other, self.user.id)
        manual = s.hold(self.db, self.source.id, "MANUAL", "operator", self.user.id)
        self.db.commit()
        with self.assertRaises(s.PipelineError):
            s.accept(self.db, ticket, [self.fact()], {}, True)
        self.db.rollback()
        self.assertTrue(s.suspended(self.db, self.source))
        with self.assertRaises(s.PipelineError):
            s.release_hold(self.db, manual.id, self.user.id)
        self.db.rollback()
        self.assertFalse(self.source.continuity_validated)

    def test_reference_hold_reconciliation_does_not_churn_fence(self):
        s.hold(self.db, self.source.id, "MANUAL", "stable", self.user.id)
        self.db.commit()
        fence = self.source.fence
        s.hold(self.db, self.source.id, "MANUAL", "stable", self.user.id)
        self.db.commit()
        self.assertEqual(self.source.fence, fence)

    def test_unverified_profile_blocks_acquisition(self):
        self.profile.evidence_status = "DOCUMENTED"
        self.db.commit()
        with self.assertRaises(s.PipelineError) as result:
            s.acquire(self.db, self.source.id, uuid.uuid4())
        self.assertEqual(result.exception.code, "CAPABILITY_NOT_RUNTIME_VERIFIED")
        self.db.rollback()

    def test_no_selection_or_name_based_routing(self):
        ticket = s.acquire(self.db, self.source.id, uuid.uuid4())
        self.db.commit()
        result = s.accept(
            self.db,
            ticket,
            [self.fact(native="unregistered-name")],
            {"cursor": 1},
            True,
        )
        self.db.commit()
        self.assertEqual(result["quarantined"], 1)
        evidence = self.db.scalar(
            select(PipelineEvidence).where(
                PipelineEvidence.source_id == self.source.id,
                PipelineEvidence.external_key == "record-1",
            )
        )
        self.assertEqual(evidence.outcome, "QUARANTINED_IDENTITY")

    def test_discovery_rename_and_incomplete_absence_preserve_identity(self):
        s.reconcile_discovery(
            self.db,
            self.integration,
            [{"native_id": "stable", "name": "Before"}],
            True,
            True,
        )
        self.db.commit()
        job = self.db.scalar(
            select(PipelineJob).where(PipelineJob.integration_id == self.integration.id)
        )
        id = job.id
        s.reconcile_discovery(
            self.db,
            self.integration,
            [{"native_id": "stable", "name": "After"}],
            True,
            True,
        )
        self.db.commit()
        self.assertEqual(job.id, id)
        self.assertEqual(job.name, "After")
        self.assertFalse(job.selected)
        s.reconcile_discovery(self.db, self.integration, [], False, True)
        self.db.commit()
        self.assertIsNone(job.stale_since)
        with self.assertRaises(s.PipelineError):
            s.reconcile_discovery(self.db, self.integration, [], True, False)
        self.db.rollback()
        self.assertIsNone(job.stale_since)

    def test_manual_discovery_match_requires_confirmation(self):
        job = PipelineJob(
            organization_id=self.org.id,
            integration_id=self.integration.id,
            native_id="manual",
            name="Manual",
            origin="MANUAL",
            selected=False,
        )
        self.db.add(job)
        self.db.commit()
        s.reconcile_discovery(
            self.db,
            self.integration,
            [{"native_id": "manual", "name": "Discovered"}],
            True,
            True,
        )
        self.db.commit()
        self.assertTrue(job.quarantined)
        self.assertEqual(job.origin, "MANUAL")
        s.reconcile_discovery(
            self.db,
            self.integration,
            [{"native_id": "manual", "name": "Discovered"}],
            True,
            True,
            confirm_manual_ids=("manual",),
        )
        self.db.commit()
        self.assertFalse(job.quarantined)
        self.assertEqual(job.origin, "CONFIRMED_MERGE")

    def test_recovery_bounds_and_live_cursor_separation(self):
        now = s.clock(self.db)
        within = s.plan_recovery(
            self.db, self.source, now - timedelta(hours=1), now, self.user.id, "within"
        )
        beyond = s.plan_recovery(
            self.db, self.source, now - timedelta(days=2), now, self.user.id, "beyond"
        )
        self.db.commit()
        self.assertEqual(within.state, "PENDING")
        self.assertEqual(beyond.state, "APPROVAL_REQUIRED")
        self.assertEqual(self.source.recovery_checkpoint, {})
        self.assertEqual(self.source.live_checkpoint, {"cursor": 0})

    def test_legal_hold_release_requires_independent_actor(self):
        hold = s.hold(self.db, self.source.id, "LEGAL", "case-1", self.user.id)
        self.db.commit()
        with self.assertRaises(s.PipelineError):
            s.release_hold(self.db, hold.id, self.user.id)
        self.db.rollback()
        self.assertIsNone(hold.released_at)

    def test_optimistic_operation_idempotency_mismatch_rejected(self):
        a, new = s.operation(
            self.db, self.org.id, "CONFIG", "stable", {"value": 1}, self.user.id
        )
        self.db.commit()
        b, new = s.operation(
            self.db, self.org.id, "CONFIG", "stable", {"value": 1}, self.user.id
        )
        self.assertFalse(new)
        self.assertEqual(a.id, b.id)
        with self.assertRaises(s.PipelineError):
            s.operation(
                self.db, self.org.id, "CONFIG", "stable", {"value": 2}, self.user.id
            )
        self.db.rollback()

    def test_postgres_rejects_cross_customer_method_fk(self):
        other = Organization(
            name="Other controlled", code="OTHER-" + uuid.uuid4().hex[:12], active=True
        )
        self.db.add(other)
        self.db.flush()
        self.db.add(
            PipelineJob(
                organization_id=other.id,
                integration_id=self.integration.id,
                native_id="evil",
                name="Cross scope",
                origin="MANUAL",
                selected=False,
            )
        )
        with self.assertRaises(IntegrityError):
            self.db.flush()
        self.db.rollback()

    def test_fence_itself_rejects_same_owner_with_live_lease(self):
        owner = uuid.uuid4()
        old = s.acquire(self.db, self.source.id, owner)
        self.source.fence += 1
        self.source.lease_until = s.clock(self.db) + timedelta(seconds=60)
        self.db.commit()
        with self.assertRaises(s.PipelineError):
            s.accept(self.db, old, [self.fact()], {"cursor": 999}, True)
        self.db.rollback()
        self.assertEqual(
            self.db.get(PipelineSource, self.source.id).live_checkpoint, {"cursor": 0}
        )

    def test_retention_respects_legal_hold_and_selected_stale_jobs(self):
        old = s.clock(self.db) - timedelta(days=40)
        self.proof.created_at = old
        job = PipelineJob(
            organization_id=self.org.id,
            integration_id=self.integration.id,
            native_id="protected-native",
            name="Selected stale job",
            origin="MANUAL",
            selected=True,
            stale_since=old,
        )
        self.db.add(job)
        s.hold(self.db, self.source.id, "LEGAL", "controlled-legal", self.user.id)
        self.db.commit()
        s.cleanup(self.db)
        self.db.commit()
        self.assertIsNotNone(self.db.get(PipelineJob, job.id))
        self.assertFalse(
            self.db.get(PipelineEvidence, self.proof.id).payload.get(
                "raw_retired", False
            )
        )

    def test_expired_runtime_proof_retains_only_safe_attestation_metadata(self):
        self.proof.created_at = s.clock(self.db) - timedelta(days=40)
        self.db.commit()
        s.cleanup(self.db)
        self.db.commit()
        proof = self.db.get(PipelineEvidence, self.proof.id)
        self.assertTrue(proof.payload["raw_retired"])
        self.assertNotIn("fixture_state", proof.payload)
        self.assertTrue(s.eligible(self.db, self.method))

    def test_control_plane_tick_is_durable_and_does_not_read_providers(self):
        from app.data_pipelines.runtime import tick

        work = tick(dispatch=False)
        self.assertIn(self.source.id, work["sources"])
        self.assertIn("operations", work)

    def test_native_job_projection_preserves_v15_identity_and_provider_evidence(self):
        from app.data_pipelines.bridge import create_job_resource
        from app.models import CollectorRun
        from app.unified.models import MonitoringResource

        job = PipelineJob(
            organization_id=self.org.id,
            integration_id=self.integration.id,
            native_id="actual-native-guid",
            name="Same display name",
            origin="MANUAL",
            selected=True,
        )
        self.db.add(job)
        self.db.flush()
        resource_id = create_job_resource(self.db, self.integration, job).id
        self.db.info["pipeline_initial_job_binding"] = job.id
        job.resource_id = resource_id
        self.db.add(
            PipelineAssociation(
                organization_id=self.org.id,
                method_id=self.method.id,
                job_id=job.id,
                generation=self.source.generation,
                confirmed_by=self.user.id,
            )
        )
        self.db.commit()
        ticket = s.acquire(self.db, self.source.id, uuid.uuid4())
        self.db.commit()
        raw = self.fact(native=job.native_id)
        raw["evidence"] = {
            "semantics": "EXECUTION",
            "raw_record": {"message": "controlled raw evidence"},
        }
        result = s.accept(self.db, ticket, [raw], {"cursor": 1}, True)
        self.db.commit()
        self.assertEqual(result["quarantined"], 0)
        resource = self.db.get(MonitoringResource, resource_id)
        run = self.db.scalar(
            select(CollectorRun).where(
                CollectorRun.collector_id == resource.primary_collector_id
            )
        )
        fact = run.source_metadata["execution_records"][0]
        self.assertEqual(fact["event"]["jobchain"], resource.configuration["jobchain"])
        self.assertEqual(fact["event"]["provider_jobchain"], "provider-name")
        self.assertEqual(fact["native_job_id"], job.native_id)
        self.assertNotIn("raw_record", fact["evidence"])
        stored = self.db.get(
            PipelineEvidence, uuid.UUID(fact["evidence"]["v16_evidence_id"])
        )
        self.assertEqual(
            stored.payload["evidence"]["raw_record"]["message"],
            "controlled raw evidence",
        )
        from app.unified.reconstruction import ingest_connector
        from types import SimpleNamespace

        version = SimpleNamespace(configuration={}, version=1)
        self.assertEqual(ingest_connector(self.db, resource, version), 1)
        self.db.commit()
        self.assertEqual(ingest_connector(self.db, resource, version), 0)
        self.db.commit()

    def test_stale_observation_stops_claiming_receiving_without_fabricated_data(self):
        from app.data_pipelines.runtime import tick

        self.source.health = "RECEIVING"
        self.source.last_observed_at = s.clock(self.db) - timedelta(minutes=10)
        self.db.commit()
        cursor = dict(self.source.live_checkpoint)
        tick(dispatch=False)
        self.db.expire_all()
        self.assertEqual(self.db.get(PipelineSource, self.source.id).health, "NO_DATA")
        self.assertEqual(
            self.db.get(PipelineSource, self.source.id).live_checkpoint, cursor
        )

    def test_two_actual_database_sessions_cannot_both_own_source(self):
        sid = self.source.id

        def attempt(_):
            with SessionLocal() as db:
                try:
                    ticket = s.acquire(db, sid, uuid.uuid4())
                    db.commit()
                    return ticket["fence"]
                except s.PipelineError as error:
                    db.rollback()
                    return error.code

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, range(2)))
        self.assertEqual(sum(isinstance(x, int) for x in results), 1)
        self.assertIn("SOURCE_ALREADY_OWNED", results)
