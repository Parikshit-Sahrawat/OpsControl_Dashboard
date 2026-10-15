"""Actual PostgreSQL fencing/durability tests; preverified states are controlled fixtures."""

import os, uuid, unittest
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
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

    def read_only_operation(self, kind="DISCOVERY"):
        self.user.platform_admin = True
        self.profile.evidence_status = "DOCUMENTED"
        self.connection.configuration = {
            "base_url": "https://inventory.example.test",
            "auth_type": "NONE",
        }
        self.connection.checksum = s.digest(self.connection.configuration)
        self.integration.enabled = False  # a saved draft, not activated collection
        op, _ = s.operation(
            self.db,
            self.org.id,
            kind,
            uuid.uuid4().hex,
            {},
            self.user.id,
            integration_id=self.integration.id,
        )
        self.db.commit()
        return op

    def test_review_discovery_unverified_draft_succeeds_activation_stays_blocked(self):
        from app.data_pipelines.runtime import run_operation

        op = self.read_only_operation()
        # Mock only the read-only provider boundary; actual worker and DB run.
        with patch(
            "app.data_pipelines.runtime.discover",
            return_value=(
                [{"native_id": "discovered-dag", "name": "Discovered DAG"}],
                True,
            ),
        ) as provider:
            run_operation(op.id)
        self.db.expire_all()
        self.assertEqual(self.db.get(PipelineOperation, op.id).state, "COMPLETE")
        provider.assert_called_once()
        job = self.db.scalar(
            select(PipelineJob).where(
                PipelineJob.integration_id == self.integration.id,
                PipelineJob.native_id == "discovered-dag",
            )
        )
        self.assertFalse(job.selected)
        self.assertFalse(s.eligible(self.db, self.method))
        self.assertTrue(
            any(
                "METHOD_NOT_RUNTIME_VERIFIED" in x
                for x in s.blockers(self.db, self.integration)
            )
        )

    def test_review_unauthorized_discovery_never_reads_or_stales(self):
        from app.data_pipelines.runtime import run_operation

        op = self.read_only_operation()
        self.user.platform_admin = False  # no customer grants
        self.db.commit()
        with patch("app.data_pipelines.runtime.discover") as provider:
            run_operation(op.id)
        self.db.expire_all()
        current = self.db.get(PipelineOperation, op.id)
        self.assertEqual(current.state, "BLOCKED")
        self.assertEqual(current.result["code"], "DISCOVERY_NOT_AUTHORIZED")
        provider.assert_not_called()

    def test_review_incomplete_discovery_does_not_stale_or_delete(self):
        from app.data_pipelines.runtime import run_operation

        op = self.read_only_operation()
        job = PipelineJob(
            organization_id=self.org.id,
            integration_id=self.integration.id,
            native_id="missing",
            name="Keep missing inventory",
            origin="DISCOVERED",
            selected=False,
            quarantined=False,
        )
        self.db.add(job)
        self.db.commit()
        job_id = job.id
        with patch("app.data_pipelines.runtime.discover", return_value=([], False)):
            run_operation(op.id)
        self.db.expire_all()
        self.assertEqual(self.db.get(PipelineOperation, op.id).state, "INCOMPLETE")
        self.assertIsNone(self.db.get(PipelineJob, job_id).stale_since)

    def test_review_redetection_does_not_require_runtime_eligibility(self):
        from app.data_pipelines.runtime import run_operation

        op = self.read_only_operation("REDETECTION")
        run_operation(op.id)
        self.db.expire_all()
        result = self.db.get(PipelineOperation, op.id)
        self.assertEqual(result.state, "COMPLETE")
        self.assertFalse(result.result["runtime_verified"])
        self.assertIn("executions", result.result["capabilities"]["supported"])
        self.assertFalse(s.eligible(self.db, self.method))

    def shared_reader(
        self,
        configuration=None,
        connection_configuration=None,
        transport="BACKEND",
        enabled=True,
    ):
        integration = PipelineIntegration(
            organization_id=self.org.id,
            name="Shared review",
            platform="AIRFLOW",
            environment="TEST",
            owner_id=self.user.id,
            enabled=True,
            configuration={},
        )
        self.db.add(integration)
        self.db.flush()
        connection = PipelineConnection(
            organization_id=self.org.id,
            integration_id=integration.id,
            version=1,
            active=True,
            configuration=connection_configuration or {},
            checksum="b" * 64,
        )
        profile = PipelineCapability(
            organization_id=self.org.id,
            integration_id=integration.id,
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
        method = PipelineMethod(
            organization_id=self.org.id,
            integration_id=integration.id,
            source_id=self.source.id,
            connection_id=connection.id,
            capability_id=profile.id,
            name="Shared review reader",
            enabled=enabled,
            transport=transport,
            validation="VALID",
            configuration=configuration or {"method_type": "PLATFORM_API"},
        )
        self.db.add(method)
        self.db.commit()
        return method

    def test_review_equivalent_readers_share_one_unit_and_one_fenced_owner(self):
        shared = self.shared_reader()
        self.assertEqual(shared.source_id, self.method.source_id)
        s.reader_equivalence(
            self.db, s.locked_source(self.db, self.source.id), persist=True
        )
        ticket = s.acquire(self.db, self.source.id, uuid.uuid4())
        self.db.commit()
        self.assertEqual(ticket["fence"], 41)
        with self.assertRaises(s.PipelineError) as denied:
            s.acquire(self.db, self.source.id, uuid.uuid4())
        self.assertEqual(denied.exception.code, "SOURCE_ALREADY_OWNED")
        self.db.rollback()
        self.assertEqual(
            self.db.scalar(
                select(func.count())
                .select_from(PipelineOperation)
                .where(
                    PipelineOperation.source_id == self.source.id,
                    PipelineOperation.kind == "READER_CONTRACT",
                )
            ),
            1,
        )

    def test_review_different_credentials_cannot_share(self):
        self.shared_reader(
            connection_configuration={
                "credential_ref": "env:OPSCONTROL_PIPELINE_SECRET_"
                + self.org.id.hex.upper()
                + "_OTHER"
            }
        )
        with self.assertRaises(s.PipelineError) as denied:
            s.acquire(self.db, self.source.id, uuid.uuid4())
        self.assertEqual(
            denied.exception.detail, {"code": "SHARED_SOURCE_READER_CONFLICT"}
        )
        self.db.rollback()
        self.assertEqual(self.source.fence, 40)

    def test_review_different_queries_and_checkpoint_interpretation_cannot_share(self):
        shared = self.shared_reader(
            configuration={
                "method_type": "PLATFORM_API",
                "adapter_overrides": {"dag_id": "different-dag"},
            }
        )
        for cfg in (
            shared.configuration,
            {"method_type": "PLATFORM_API", "native_identity_field": "different_id"},
            {"method_type": "PLATFORM_API", "checkpoint_schema": "different-v2"},
        ):
            shared.configuration = cfg
            self.db.commit()
            with self.assertRaises(s.PipelineError) as denied:
                s.acquire(self.db, self.source.id, uuid.uuid4())
            self.assertEqual(denied.exception.code, "SHARED_SOURCE_READER_CONFLICT")
            self.db.rollback()

    def test_review_durable_contract_rejects_single_reader_change_without_handoff(self):
        s.reader_equivalence(
            self.db, s.locked_source(self.db, self.source.id), persist=True
        )
        self.db.commit()
        self.method.configuration = {
            **self.method.configuration,
            "native_identity_field": "unsafe_changed_cursor",
        }
        self.db.commit()
        with self.assertRaises(s.PipelineError) as denied:
            s.acquire(self.db, self.source.id, uuid.uuid4())
        self.assertEqual(denied.exception.code, "SHARED_SOURCE_READER_CONFLICT")
        self.db.rollback()
        self.assertEqual(self.source.live_checkpoint, {"cursor": 0})

    def test_review_enabling_incompatible_binding_is_rejected_by_api(self):
        from app.data_pipelines.api import edit_method, MethodEdit
        from app.security.scope import Principal, current_principal

        shared = self.shared_reader(
            configuration={
                "method_type": "PLATFORM_API",
                "adapter_overrides": {"dag_id": "other"},
            },
            enabled=False,
        )
        token = current_principal.set(
            Principal(self.user.id, self.user.username, True, {})
        )
        try:
            with self.assertRaises(s.PipelineError) as denied:
                edit_method(
                    shared.id,
                    MethodEdit(
                        name=shared.name,
                        enabled=True,
                        expected_revision=shared.revision,
                        idempotency_key=uuid.uuid4().hex,
                    ),
                    self.db,
                )
            self.assertEqual(denied.exception.code, "SHARED_SOURCE_READER_CONFLICT")
            self.db.rollback()
            self.assertFalse(self.db.get(PipelineMethod, shared.id).enabled)
        finally:
            current_principal.reset(token)

    def latest_failure(self):
        self.db.expire_all()
        return self.db.scalar(
            select(PipelineOperation)
            .where(
                PipelineOperation.source_id == self.source.id,
                PipelineOperation.kind == "COLLECTION_FAILURE",
            )
            .order_by(PipelineOperation.created_at.desc())
        )

    def test_review_preparation_exception_rolls_back_and_releases_owned_lease(self):
        from app.data_pipelines.runtime import run_source

        with patch(
            "sqlalchemy.orm.Session.expunge",
            side_effect=ValueError("private diagnostic"),
        ), patch("app.data_pipelines.runtime.collect_method") as provider:
            run_source(self.source.id)
        failure = self.latest_failure()
        self.assertEqual(
            failure.result, {"error_code": "RUNTIME_ERROR", "ownership_released": True}
        )
        source = self.db.get(PipelineSource, self.source.id)
        self.assertIsNone(source.owner_id)
        self.assertIsNone(source.lease_until)
        self.assertEqual(source.live_checkpoint, {"cursor": 0})
        provider.assert_not_called()

    def test_review_invalid_recovery_operation_cannot_become_live_collection(self):
        from app.data_pipelines.runtime import run_source

        with patch("app.data_pipelines.runtime.collect_method") as provider:
            run_source(self.source.id, uuid.uuid4())
        failure = self.latest_failure()
        self.assertEqual(failure.result["error_code"], "RECOVERY_NOT_ELIGIBLE")
        provider.assert_not_called()
        self.assertEqual(
            self.db.get(PipelineSource, self.source.id).live_checkpoint, {"cursor": 0}
        )

    def test_review_expired_worker_never_commits_checkpoint_or_cleans_new_owner(self):
        from app.data_pipelines.runtime import run_source

        def expire(*args, **kwargs):
            with SessionLocal() as db:
                source = s.locked_source(db, self.source.id)
                source.lease_until = s.clock(db) - timedelta(seconds=1)
                db.commit()
            return [self.fact("late-expired")], {"cursor": 100}, True

        with patch("app.data_pipelines.runtime.collect_method", side_effect=expire):
            run_source(self.source.id)
        failure = self.latest_failure()
        self.assertFalse(failure.result["ownership_released"])
        self.assertEqual(self.source.live_checkpoint, {"cursor": 0})
        self.assertEqual(
            self.db.scalar(
                select(func.count())
                .select_from(PipelineEvidence)
                .where(PipelineEvidence.source_id == self.source.id)
            ),
            1,
        )

    def test_review_replacement_commit_survives_stale_worker_cleanup(self):
        from app.data_pipelines.runtime import run_source

        replacement = uuid.uuid4()

        def replace(*args, **kwargs):
            with SessionLocal() as db:
                source = s.locked_source(db, self.source.id)
                source.lease_until = s.clock(db) - timedelta(seconds=1)
                db.commit()
                ticket = s.acquire(db, source.id, replacement)
                db.commit()
                s.accept(db, ticket, [self.fact("replacement")], {"cursor": 42}, True)
                db.commit()
            return [self.fact("stale")], {"cursor": 41}, True

        with patch("app.data_pipelines.runtime.collect_method", side_effect=replace):
            run_source(self.source.id)
        failure = self.latest_failure()
        self.assertFalse(failure.result["ownership_released"])
        self.assertEqual(self.source.owner_id, replacement)
        self.assertEqual(self.source.fence, 42)
        self.assertEqual(self.source.live_checkpoint, {"cursor": 42})
        self.assertNotEqual(self.source.health, "ERROR")
        self.assertFalse(
            self.db.scalar(
                select(PipelineEvidence.id).where(
                    PipelineEvidence.source_id == self.source.id,
                    PipelineEvidence.external_key == "stale",
                )
            )
        )

    def test_review_recovery_failure_preserves_live_and_recovery_cursors(self):
        from app.data_pipelines.runtime import run_source

        self.source.next_run_at = s.clock(self.db) + timedelta(minutes=1)
        self.source.recovery_checkpoint = {"cursor": 7}
        op, _ = s.operation(
            self.db,
            self.org.id,
            "RECOVERY",
            uuid.uuid4().hex,
            {
                "generation": str(self.source.generation),
                "start": s.clock(self.db).isoformat(),
                "end": s.clock(self.db).isoformat(),
            },
            self.user.id,
            source_id=self.source.id,
        )
        self.db.commit()
        run_source(self.source.id, op.id)
        self.db.expire_all()
        self.assertEqual(self.db.get(PipelineOperation, op.id).state, "UNRECOVERABLE")
        self.assertEqual(self.source.live_checkpoint, {"cursor": 0})
        self.assertEqual(self.source.recovery_checkpoint, {"cursor": 7})

    def test_review_verification_failure_is_structured_and_does_not_advance(self):
        from app.data_pipelines.runtime import run_source

        op, _ = s.operation(
            self.db,
            self.org.id,
            "VERIFY",
            uuid.uuid4().hex,
            {"generation": str(self.source.generation)},
            self.user.id,
            source_id=self.source.id,
        )
        op.state = "RUNNING"
        op.lease_until = s.clock(self.db) + timedelta(minutes=5)
        self.profile.evidence_status = "DOCUMENTED"
        self.db.commit()
        with patch.dict(
            os.environ, {"OPSCONTROL_PIPELINE_RUNTIME_ACCEPTANCE": "1"}
        ), patch(
            "app.data_pipelines.runtime.collect_method",
            side_effect=ValueError("sensitive provider detail"),
        ):
            run_source(self.source.id, verification=True)
        self.db.expire_all()
        self.assertEqual(self.db.get(PipelineOperation, op.id).state, "FAILED")
        self.assertEqual(self.source.live_checkpoint, {"cursor": 0})
        self.assertEqual(self.latest_failure().result["error_code"], "RUNTIME_ERROR")

    def test_review_replacement_active_lease_is_never_released_by_stale_cleanup(self):
        from app.data_pipelines.runtime import run_source

        replacement = uuid.uuid4()
        lease = []

        def replace(*args, **kwargs):
            with SessionLocal() as db:
                source = s.locked_source(db, self.source.id)
                source.lease_until = s.clock(db) - timedelta(seconds=1)
                db.commit()
                ticket = s.acquire(db, source.id, replacement)
                lease.append(ticket["lease_until"])
                db.commit()
            return [], {"cursor": 100}, True

        with patch("app.data_pipelines.runtime.collect_method", side_effect=replace):
            run_source(self.source.id)
        self.assertFalse(self.latest_failure().result["ownership_released"])
        self.assertEqual(self.source.owner_id, replacement)
        self.assertEqual(self.source.lease_until.isoformat(), lease[0])
        self.assertEqual(self.source.live_checkpoint, {"cursor": 0})

    def test_review_adding_incompatible_binding_is_rejected_by_api(self):
        from app.data_pipelines.api import add_method, MethodInput
        from app.security.scope import Principal, current_principal

        identity, key = s.canonical(
            "PLATFORM_API",
            {
                "platform": "AIRFLOW",
                "endpoint": "https://inventory.example.test",
                "account": "controlled",
                "physical_scope": "all-dags",
            },
        )
        self.source.identity, self.source.canonical_key = identity, key
        self.connection.configuration = {
            "base_url": identity["endpoint"],
            "auth_type": "NONE",
        }
        self.db.commit()
        shared = self.shared_reader(
            connection_configuration={
                "base_url": identity["endpoint"],
                "auth_type": "NONE",
                "dag_id": "different-scope",
            }
        )
        other_id, conn_id, cap_id = (
            shared.integration_id,
            shared.connection_id,
            shared.capability_id,
        )
        self.db.delete(shared)
        self.db.commit()
        token = current_principal.set(
            Principal(self.user.id, self.user.username, True, {})
        )
        try:
            with self.assertRaises(s.PipelineError) as denied:
                add_method(
                    other_id,
                    MethodInput(
                        name="Reject conflicting query",
                        method_type="PLATFORM_API",
                        transport="BACKEND",
                        identity=identity,
                        connection_id=conn_id,
                        capability_id=cap_id,
                        configuration={},
                        enabled=True,
                        idempotency_key=uuid.uuid4().hex,
                    ),
                    self.db,
                )
            self.assertEqual(denied.exception.code, "SHARED_SOURCE_READER_CONFLICT")
            self.db.rollback()
            self.assertIsNone(
                self.db.scalar(
                    select(PipelineMethod.id).where(
                        PipelineMethod.integration_id == other_id
                    )
                )
            )
        finally:
            current_principal.reset(token)

    def test_review_failed_database_preparation_is_rolled_back_before_cleanup(self):
        from app.data_pipelines.runtime import run_source
        from sqlalchemy import text

        def invalid_transaction(db, obj):
            db.execute(text("SELECT 1/0"))

        with patch("sqlalchemy.orm.Session.expunge", new=invalid_transaction):
            run_source(self.source.id)
        self.assertTrue(self.latest_failure().result["ownership_released"])
        self.assertEqual(self.source.live_checkpoint, {"cursor": 0})
        self.assertIsNone(self.source.lease_until)

    def test_review_expired_recovery_claim_is_requeued_and_refenced(self):
        from app.data_pipelines.runtime import run_source, tick

        current = s.clock(self.db)
        self.source.next_run_at = current + timedelta(minutes=1)
        op, _ = s.operation(
            self.db,
            self.org.id,
            "RECOVERY",
            uuid.uuid4().hex,
            {
                "generation": str(self.source.generation),
                "start": current.isoformat(),
                "end": current.isoformat(),
            },
            self.user.id,
            source_id=self.source.id,
        )
        op.state, op.fence, op.owner_id = "RUNNING", 7, uuid.uuid4()
        op.lease_until = current - timedelta(seconds=1)
        self.db.commit()
        self.assertIn(op.id, tick(False)["recoveries"])
        run_source(self.source.id, op.id)
        self.db.expire_all()
        current_op = self.db.get(PipelineOperation, op.id)
        self.assertEqual(current_op.fence, 8)
        self.assertEqual(
            current_op.state, "UNRECOVERABLE"
        )  # unsupported provider replay, not fabricated recovery
        self.assertEqual(
            current_op.result["error_code"], "BOUNDED_PROVIDER_REPLAY_NOT_SUPPORTED"
        )
        self.assertEqual(self.source.live_checkpoint, {"cursor": 0})
