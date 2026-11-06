"""Real migrated PostgreSQL and authenticated HTTP; fixtures never certify providers."""

import json
import os
import hashlib
import unittest
from pathlib import Path
from datetime import datetime, timezone, timedelta
from uuid import uuid4, UUID
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from sqlalchemy import select, text, func
from sqlalchemy.exc import DBAPIError
from app.db.session import SessionLocal
from app.unified.models import MonitoringResource
from app.data_pipelines.models import (
    PipelineIntegration,
    PipelineConnection,
    PipelineCapability,
    PipelineSource,
    PipelineMethod,
    PipelineJob,
    PipelineHold,
    PipelineOperation,
)
from app.etl_bindings.models import ETLNativeBinding, ETLBindingReceipt
from app.etl_bindings import service
from app.models import JobOrder
from app.security.models import User, SecurityAuditEvent
from app.security.passwords import hash_password
from app.security.access_models import (
    Role,
    RolePermission,
    UserRoleAssignment,
    CustomerAccessGrant,
)
from tests import test_etl_workflow_scope as scopes


@unittest.skipUnless(
    os.getenv("OPSCONTROL_ETL_SCOPE_ACCEPTANCE") == "1",
    "Owned PostgreSQL/HTTP required",
)
class BindingLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.assertEqual(os.environ.get("ENVIRONMENT"), "test")
        self.assertTrue(
            os.environ.get("ETL_SCOPE_CONTAINER", "").startswith("oc-etl002-")
        )
        scopes.WorkflowScopeTests.setUp(self)
        self.checks = []
        self.native = "native-" + uuid4().hex
        self.namespace = "server-" + uuid4().hex
        self.n, self.methods = self.seed(self.j1, self.native)
        self.token = self.req(
            "auth/login",
            "POST",
            {"username": self.username, "password": self.password},
            token="",
        )["access_token"]
        self.base = f"etl/workflows/{self.wa}/jobs/{self.j1}/native-bindings"

    def tearDown(self):
        out = Path(os.environ["ETL_SCOPE_EVIDENCE_DIR"])
        (out / (self._testMethodName + ".json")).write_text(
            json.dumps({"checks": self.checks}, indent=2)
        )

    def seed(self, job_id, native, environment="PROD"):
        with SessionLocal() as db:
            job = db.get(JobOrder, job_id)
            resource = db.scalar(
                select(MonitoringResource).where(
                    MonitoringResource.job_order_id == job_id
                )
            )
            i = PipelineIntegration(
                organization_id=job.organization_id,
                name="Synthetic binding",
                platform="PENTAHO",
                environment=environment,
                owner_id=self.uid,
            )
            db.add(i)
            db.flush()
            c = PipelineConnection(
                organization_id=job.organization_id,
                integration_id=i.id,
                version=1,
                configuration={"url": "https://synthetic.invalid"},
                checksum="0" * 64,
                active=False,
            )
            p = PipelineCapability(
                organization_id=job.organization_id,
                integration_id=i.id,
                platform_version="UNVERIFIED",
                edition="fixture",
                deployment_type="test",
                definition={"supported_methods": ["PLATFORM_API"]},
            )
            db.add_all([c, p])
            db.flush()
            methods = []
            for idx in range(2):
                source = PipelineSource(
                    organization_id=job.organization_id,
                    method_type="PLATFORM_API",
                    canonical_key=hashlib.sha256(uuid4().bytes).hexdigest(),
                    identity={
                        "platform": "PENTAHO",
                        "endpoint": "https://synthetic.invalid/" + uuid4().hex,
                        "account": "synthetic",
                        "physical_scope": "fixture",
                    },
                )
                db.add(source)
                db.flush()
                m = PipelineMethod(
                    organization_id=job.organization_id,
                    integration_id=i.id,
                    source_id=source.id,
                    connection_id=c.id,
                    capability_id=p.id,
                    name=f"Synthetic method {idx}",
                    transport="BACKEND",
                    configuration={
                        "method_type": "PLATFORM_API",
                        "interval_seconds": 60,
                    },
                )
                db.add(m)
                db.flush()
                methods.append(
                    {
                        "id": str(m.id),
                        "source_id": str(source.id),
                        "generation": str(source.generation),
                    }
                )
            n = PipelineJob(
                organization_id=job.organization_id,
                integration_id=i.id,
                native_id=native,
                name="Not a durable display identity",
                origin="LEGACY_PENDING",
                resource_id=resource.id,
                quarantined=True,
            )
            db.add(n)
            db.commit()
            return str(n.id), methods

    def req(self, path, method="GET", body=None, status=200, token=None, customer=None):
        headers = {
            "Content-Type": "application/json",
            "X-OpsControl-Customers": str(customer or self.a),
        }
        credential = getattr(self, "token", "") if token is None else token
        if credential:
            headers["Authorization"] = "Bearer " + credential
        try:
            with urlopen(
                Request(
                    (base_url or os.environ["ETL_SCOPE_API_URL"]) + "/api/v1/" + path,
                    method=method,
                    headers=headers,
                    data=json.dumps(body).encode() if body is not None else None,
                ),
                timeout=20,
            ) as r:
                actual = r.status
                data = json.load(r)
        except HTTPError as e:
            actual = e.code
            data = json.load(e)
        self.checks.append(
            {
                "method": method,
                "path": path,
                "expected": status,
                "actual": actual,
                "detail": data.get("detail") if isinstance(data, dict) else None,
            }
        )
        self.assertEqual(actual, status, self.checks[-1])
        return data

    def payload(self, command="STAGE", current=None, methods=None):
        methods = methods or self.methods
        return {
            "command": command,
            "idempotency_key": uuid4().hex,
            "current_binding_id": current["id"] if current else None,
            "expected_revision": current["revision"] if current else None,
            "native_job_id": self.n,
            "authority_claim": self.namespace,
            "method_ids": [m["id"] for m in methods],
            "expected_sources": {m["source_id"]: m["generation"] for m in methods},
            "reason": "Synthetic controlled configuration",
            "confirmed": True,
        }

    def stage(self):
        return self.req(self.base, "POST", self.payload(), 201)

    def test_stage_replace_retire_idempotency_and_immutable_history(self):
        p = self.payload()
        first = self.req(self.base, "POST", p, 201)
        self.assertEqual(self.req(self.base, "POST", p, 201)["id"], first["id"])
        second = self.req(
            self.base, "POST", self.payload("REPLACE", first, [self.methods[1]]), 201
        )
        self.assertEqual(second["previous_id"], first["id"])
        retired = self.req(
            self.base, "POST", self.payload("RETIRE", second, [self.methods[1]]), 201
        )
        self.assertEqual(retired["state"], "RETIRED")
        versions = self.req(self.base)["versions"]
        self.assertEqual(len(versions), 3)
        self.assertEqual(versions[0]["valid_until"], versions[1]["valid_from"])
        self.assertEqual(versions[1]["valid_until"], versions[2]["valid_from"])
        self.assertEqual(
            versions[0]["identity_snapshot"], versions[2]["identity_snapshot"]
        )
        self.req(self.base, "POST", self.payload("REPLACE", retired), 409)
        with SessionLocal() as db:
            audit = db.scalar(
                select(func.count())
                .select_from(SecurityAuditEvent)
                .where(SecurityAuditEvent.target_type == "ETLNativeBinding")
            )
            self.assertGreaterEqual(audit, 3)
            self.assertEqual(
                db.get(PipelineJob, UUID(self.n)).resource_id,
                UUID(first["resource_id"]),
            )

    def test_duplicate_conflict_and_failed_transaction_leave_no_operation(self):
        old = self.stage()
        p = self.payload()
        key = p["idempotency_key"]
        self.req(self.base, "POST", p, 409)
        changed = self.payload("REPLACE", old)
        changed["authority_claim"] = "other-native-authority"
        self.req(self.base, "POST", changed, 409)
        with SessionLocal() as db:
            self.assertIsNone(
                db.scalar(
                    select(PipelineOperation.id).where(
                        PipelineOperation.idempotency_key == key
                    )
                )
            )
            self.assertIsNone(db.get(ETLNativeBinding, UUID(old["id"])).valid_until)

    def test_concurrent_same_job_one_commit_and_other_refresh(self):
        gate = Barrier(2)

        def submit(_):
            p = self.payload()
            gate.wait()
            try:
                with urlopen(
                    Request(
                        os.environ["ETL_SCOPE_API_URL"] + "/api/v1/" + self.base,
                        method="POST",
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": "Bearer " + self.token,
                            "X-OpsControl-Customers": str(self.a),
                        },
                        data=json.dumps(p).encode(),
                    ),
                    timeout=20,
                ) as r:
                    return r.status
            except HTTPError as e:
                return e.code

        with ThreadPoolExecutor(2) as pool:
            result = sorted(pool.map(submit, range(2)))
        self.assertEqual(result, [201, 409])
        self.checks.append({"concurrent_statuses": result})
        self.assertEqual(len(self.req(self.base)["versions"]), 1)

    def test_same_qualified_claim_cannot_get_two_job_owners(self):
        self.stage()
        n, methods = self.seed(self.j2, self.native)
        p = self.payload(methods=methods)
        p["native_job_id"] = n
        self.req(
            f"etl/workflows/{self.wa}/jobs/{self.j2}/native-bindings", "POST", p, 409
        )

    def test_stale_generation_inflight_and_retention_holds(self):
        old = self.stage()
        with SessionLocal() as db:
            source = db.get(PipelineSource, UUID(self.methods[0]["source_id"]))
            source.lease_until = datetime.now(timezone.utc) + timedelta(minutes=2)
            db.commit()
        self.req(self.base, "POST", self.payload("REPLACE", old), 409)
        with SessionLocal() as db:
            source = db.get(PipelineSource, UUID(self.methods[0]["source_id"]))
            source.lease_until = None
            hold = PipelineHold(
                organization_id=self.a,
                source_id=source.id,
                kind="LEGAL",
                reference="synthetic-preserve",
                actor_id=self.uid,
            )
            db.add(hold)
            db.commit()
            holdid = hold.id
        self.req(self.base, "POST", self.payload("RETIRE", old), 409)
        with SessionLocal() as db:
            db.get(PipelineHold, holdid).released_at = datetime.now(timezone.utc)
            db.get(PipelineSource, UUID(self.methods[0]["source_id"])).generation = (
                uuid4()
            )
            db.commit()
        self.req(self.base, "POST", self.payload("REPLACE", old), 409)
        ready = self.req(f"etl/workflows/{self.wa}/readiness")
        item = next(j for j in ready["jobs"] if j["job_id"] == str(self.j1))
        self.assertEqual(item["binding_validity"]["state"], "STALE")
        self.assertEqual(item["monitoring_activation"]["state"], "BLOCKED")

    def test_confirmation_requires_independent_reviewer_and_real_native_authority(self):
        first = self.stage()
        self.req(self.base, "POST", self.payload("CONFIRM", first), 403)
        with SessionLocal() as db:
            reviewer = User(
                username="reviewer-" + uuid4().hex,
                password_hash=hash_password(self.password),
                platform_admin=True,
            )
            db.add(reviewer)
            db.commit()
            name = reviewer.username
        token = self.req(
            "auth/login",
            "POST",
            {"username": name, "password": self.password},
            token="",
        )["access_token"]
        self.req(self.base, "POST", self.payload("CONFIRM", first), 409, token)
        self.assertEqual(len(self.req(self.base)["versions"]), 1)

    def test_tenant_environment_invalid_payload_and_unauthenticated_denials(self):
        self.req(
            f"etl/workflows/{self.wb}/jobs/{self.jb}/native-bindings",
            "POST",
            self.payload(),
            404,
        )
        self.req(self.base, "POST", self.payload(), 401, "")
        p = self.payload()
        p["run_job"] = True
        self.req(self.base, "POST", p, 422)
        p = self.payload()
        p["method_ids"] *= 2
        self.req(self.base, "POST", p, 422)
        p = self.payload()
        p["expected_sources"] = {}
        self.req(self.base, "POST", p, 409)
        wrong, m = self.seed(self.j1, "other-env", environment="DEV")
        p = self.payload(methods=m)
        p["native_job_id"] = wrong
        self.req(self.base, "POST", p, 409)

    def test_role_revocation_and_view_only_denial(self):
        with SessionLocal() as db:
            user = User(
                username="binding-editor-" + uuid4().hex,
                password_hash=hash_password(self.password),
            )
            role = Role(code="binding-" + uuid4().hex, name="Binding controlled role")
            db.add_all([user, role])
            db.flush()
            db.add_all(
                [
                    RolePermission(role_id=role.id, permission_key=k)
                    for k in ["etl.view", "etl.configure"]
                ]
            )
            db.add(UserRoleAssignment(user_id=user.id, role_id=role.id))
            db.flush()
            db.add(
                CustomerAccessGrant(
                    user_id=user.id, role_id=role.id, organization_id=self.a
                )
            )
            db.commit()
            name = user.username
            role_id = str(role.id)
        token = self.req(
            "auth/login",
            "POST",
            {"username": name, "password": self.password},
            token="",
        )["access_token"]
        old = self.req(self.base, "POST", self.payload(), 201, token)
        role = next(row for row in self.req("access/roles") if row["id"] == role_id)
        self.req(
            "access/roles/" + role_id,
            "PATCH",
            {
                "name": role["name"],
                "expected_revision": role["authorization_revision"],
                "permissions": ["etl.view"],
            },
        )
        self.req(self.base, "POST", self.payload("REPLACE", old), 403, token)
        self.req(self.base, token=token)

    def test_database_immutability_and_interrupted_closure_rollback(self):
        old = self.stage()
        for sql in [
            "DELETE FROM etl_native_bindings WHERE id=:id",
            "UPDATE etl_native_bindings SET reason='overwrite' WHERE id=:id",
            "UPDATE etl_native_bindings SET valid_until=now() WHERE id=:id",
        ]:
            with SessionLocal() as db:
                with self.assertRaises(DBAPIError):
                    db.execute(text(sql), {"id": old["id"]})
                    db.commit()
                db.rollback()
        with SessionLocal() as db:
            pid = db.scalar(text("SELECT pg_backend_pid()"))
            db.execute(
                text("UPDATE etl_native_bindings SET valid_until=now() WHERE id=:id"),
                {"id": old["id"]},
            )
            with SessionLocal() as killer:
                self.assertTrue(
                    killer.scalar(
                        text("SELECT pg_terminate_backend(:pid)"), {"pid": pid}
                    )
                )
                killer.commit()
            with self.assertRaises(DBAPIError):
                db.commit()
        with SessionLocal() as db:
            self.assertIsNone(db.get(ETLNativeBinding, UUID(old["id"])).valid_until)
            self.assertEqual(
                db.scalar(select(func.count()).select_from(ETLBindingReceipt)), 0
            )

    def test_readiness_version_evaluation_and_legacy_history_not_inferred(self):
        before = self.req(f"etl/workflows/{self.wa}/readiness")
        self.stage()
        after = self.req(f"etl/workflows/{self.wa}/readiness")
        self.assertEqual(before["freshness_policy"], "ETL_SOURCE_RECEIPT_V1")
        self.assertGreaterEqual(after["evaluated_at"], before["evaluated_at"])
        item = next(j for j in after["jobs"] if j["job_id"] == str(self.j1))
        self.assertEqual(item["binding_validity"]["state"], "STAGED")
        self.assertEqual(item["source_connectivity"]["state"], "UNVERIFIED")
        self.assertEqual(item["evidence_freshness"]["state"], "MISSING")
        self.assertEqual(item["operational_health"]["state"], "UNVERIFIED")
        self.assertEqual(item["evidence_freshness"]["threshold_seconds"], 180)
        with SessionLocal() as db:
            n = db.get(PipelineJob, UUID(self.n))
            m = db.get(PipelineMethod, UUID(self.methods[0]["id"]))
            s = db.get(PipelineSource, m.source_id)
            self.assertEqual(service.routing_binding(db, n, s, m), (False, None))

    @unittest.skipUnless(
        os.getenv("ETL_WORKFLOW_UI_ACCEPTANCE") == "1", "Owned browser required"
    )
    def test_native_binding_authenticated_browser(self):
        import tempfile
        import subprocess

        with SessionLocal() as db:
            viewer = User(
                username="binding-viewer-" + uuid4().hex,
                password_hash=hash_password(self.password),
            )
            role = Role(code="binding-viewer-" + uuid4().hex, name="Binding viewer")
            db.add_all([viewer, role])
            db.flush()
            db.add_all(
                [
                    RolePermission(role_id=role.id, permission_key=k)
                    for k in ["etl.view", "resources.view", "customers.view"]
                ]
            )
            db.add(UserRoleAssignment(user_id=viewer.id, role_id=role.id))
            db.flush()
            db.add(
                CustomerAccessGrant(
                    user_id=viewer.id, role_id=role.id, organization_id=self.a
                )
            )
            db.commit()
            fixture = {
                "a": str(self.a),
                "b": str(self.b),
                "wa": str(self.wa),
                "username": self.username,
                "password": self.password,
                "viewer": viewer.username,
                "native_job": self.n,
                "authority": self.namespace,
            }
        with tempfile.TemporaryDirectory(prefix="etl006-private-") as private:
            file = Path(private) / "fixture.json"
            file.write_text(json.dumps(fixture))
            file.chmod(0o600)
            env = {**os.environ, "ETL_BINDING_FIXTURE": str(file)}
            result = subprocess.run(
                ["node", "frontend/scripts/native_binding_acceptance.mjs"],
                cwd=Path(__file__).resolve().parents[2],
                env=env,
                capture_output=True,
                text=True,
                timeout=120,
            )
        (
            Path(os.environ["ETL_SCOPE_EVIDENCE_DIR"]) / "native-binding-browser.log"
        ).write_text(
            (result.stdout + result.stderr).replace(self.password, "[REDACTED]")
        )
        self.assertEqual(result.returncode, 0, result.stderr[-1500:])
        with SessionLocal() as db:
            rows = db.scalars(
                select(ETLNativeBinding)
                .where(ETLNativeBinding.job_order_id == self.j1)
                .order_by(ETLNativeBinding.valid_from)
            ).all()
            self.assertEqual([r.state for r in rows], ["STAGED", "STAGED", "RETIRED"])
            self.assertEqual(rows[0].valid_until, rows[1].valid_from)
            self.assertFalse(db.get(PipelineJob, UUID(self.n)).selected)

    def test_populated_binding_downgrade_refused_and_full_restore_preserves_history(
        self,
    ):
        import subprocess
        import sys
        from sqlalchemy.engine import make_url
        from sqlalchemy import create_engine, inspect

        first = self.stage()
        second = self.req(self.base, "POST", self.payload("REPLACE", first), 201)
        url = make_url(os.environ["DATABASE_URL"])
        out = Path(os.environ["ETL_SCOPE_EVIDENCE_DIR"])

        def snapshot(engine):
            with engine.connect() as c:
                inspector = inspect(c)
                result = {}
                for name in sorted(inspector.get_table_names()):
                    rows = c.scalars(
                        text(
                            f'SELECT to_jsonb(t)::text FROM "{name}" t ORDER BY to_jsonb(t)::text'
                        )
                    ).all()
                    result[name] = {
                        "count": len(rows),
                        "sha256": hashlib.sha256(json.dumps(rows).encode()).hexdigest(),
                        "columns": [
                            (x["name"], str(x["type"]), x["nullable"])
                            for x in inspector.get_columns(name)
                        ],
                        "foreign_keys": inspector.get_foreign_keys(name),
                    }
                return result

        from app.db.session import engine

        before = snapshot(engine)
        r = subprocess.run(
            [
                sys.executable,
                "-m",
                "alembic",
                "downgrade",
                "0039_etl_workflow_foundation",
            ],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True,
            text=True,
            timeout=60,
        )
        (out / "binding-populated-downgrade-refusal.log").write_text(
            (r.stdout + r.stderr).replace(url.password, "[REDACTED]")
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Unsafe populated ETL downgrade blocked before DDL", r.stderr)
        self.assertIn("etl_native_bindings", r.stderr)
        self.assertEqual(snapshot(engine), before)
        docker = [
            "docker",
            "--host=unix:///var/run/docker.sock",
            "exec",
            "-i",
            os.environ["ETL_SCOPE_CONTAINER"],
        ]
        archive = subprocess.run(
            [*docker, "pg_dump", "-U", "postgres", "-Fc", url.database],
            capture_output=True,
            timeout=90,
        )
        self.assertEqual(archive.returncode, 0)
        (out / "synthetic-temporal-backup.dump").write_bytes(archive.stdout)
        restore = "binding_restore_" + uuid4().hex[:12]
        try:
            subprocess.run(
                [*docker, "createdb", "-U", "postgres", restore],
                check=True,
                capture_output=True,
                timeout=30,
            )
            restored = subprocess.run(
                [*docker, "pg_restore", "-U", "postgres", "--no-owner", "-d", restore],
                input=archive.stdout,
                capture_output=True,
                timeout=90,
            )
            self.assertEqual(restored.returncode, 0, restored.stderr.decode()[-2000:])
            restored_engine = create_engine(url.set(database=restore))
            try:
                self.assertEqual(snapshot(restored_engine), before)
            finally:
                restored_engine.dispose()
        finally:
            subprocess.run(
                [*docker, "dropdb", "-U", "postgres", restore],
                check=True,
                capture_output=True,
                timeout=30,
            )
        with SessionLocal() as db:
            self.assertEqual(service.current(db, self.j1).id, UUID(second["id"]))
        (out / "temporal-preservation-results.json").write_text(
            json.dumps(
                {
                    "status": "PASS",
                    "downgrade_exit": r.returncode,
                    "source_hashes": before,
                    "restored_hashes": before,
                    "archive_sha256": hashlib.sha256(archive.stdout).hexdigest(),
                    "comparison": "Actual restored database hashes equal source snapshot; empty owned restore database removed",
                },
                indent=2,
            )
        )

    def test_receipt_cannot_claim_unconfirmed_historical_binding(self):
        from app.data_pipelines.models import PipelineEvidence

        first = self.stage()
        with SessionLocal() as db:
            evidence = PipelineEvidence(
                organization_id=self.a,
                source_id=UUID(self.methods[0]["source_id"]),
                generation=UUID(self.methods[0]["generation"]),
                external_key="synthetic-no-projection-" + uuid4().hex,
                native_job_id=self.native,
                payload={"synthetic": True},
                outcome="ACCEPTED",
                observed_at=datetime.now(timezone.utc),
            )
            db.add(evidence)
            db.commit()
            eid = evidence.id
        with SessionLocal() as db:
            db.add(
                ETLBindingReceipt(
                    organization_id=self.a,
                    binding_id=UUID(first["id"]),
                    evidence_id=eid,
                    payload_sha256="0" * 64,
                )
            )
            with self.assertRaises(DBAPIError):
                db.commit()
            db.rollback()
        with SessionLocal() as db:
            self.assertIsNotNone(db.get(PipelineEvidence, eid))
            self.assertIsNone(
                db.scalar(
                    select(ETLBindingReceipt.id).where(
                        ETLBindingReceipt.evidence_id == eid
                    )
                )
            )
        state = self.req(f"etl/workflows/{self.wa}/readiness")
        item = next(j for j in state["jobs"] if j["job_id"] == str(self.j1))
        self.assertEqual(item["evidence_freshness"]["state"], "MISSING")
        self.assertEqual(item["operational_health"]["state"], "UNVERIFIED")

    def test_fence_advance_without_generation_change_is_not_a_rebind(self):
        first = self.stage()
        with SessionLocal() as db:
            source = db.get(PipelineSource, UUID(self.methods[0]["source_id"]))
            source.fence += 1
            db.commit()
        state = self.req(f"etl/workflows/{self.wa}/readiness")
        item = next(j for j in state["jobs"] if j["job_id"] == str(self.j1))
        self.assertEqual(item["binding_validity"]["state"], "STAGED")
        self.req(self.base, "POST", self.payload("REPLACE", first), 201)

    def test_concurrent_target_ownership_and_nonconflicting_targets(self):
        n, methods = self.seed(self.j2, self.native)
        path = f"etl/workflows/{self.wa}/jobs/{self.j2}/native-bindings"
        p = self.payload(methods=methods)
        p["native_job_id"] = n

        def race(pairs):
            gate = Barrier(2)

            def run(pair):
                path, payload = pair
                gate.wait()
                try:
                    with urlopen(
                        Request(
                            os.environ["ETL_SCOPE_API_URL"] + "/api/v1/" + path,
                            method="POST",
                            headers={
                                "Content-Type": "application/json",
                                "Authorization": "Bearer " + self.token,
                                "X-OpsControl-Customers": str(self.a),
                            },
                            data=json.dumps(payload).encode(),
                        ),
                        timeout=20,
                    ) as r:
                        return r.status
                except HTTPError as e:
                    return e.code

            with ThreadPoolExecutor(2) as pool:
                return sorted(pool.map(run, pairs))

        outcome = race([(self.base, self.payload()), (path, p)])
        self.assertEqual(outcome, [201, 409])
        self.checks.append({"same_target_different_jobs": outcome})
        # Separate new Jobs/targets exercise concurrency without a global graph lock.
        from app.models import ETLWorkflow

        with SessionLocal() as db:
            w = db.get(ETLWorkflow, self.wc)
            extra = JobOrder(
                organization_id=self.a,
                workflow_id=w.id,
                environment="PROD",
                name="concurrent-independent-" + uuid4().hex,
            )
            db.add(extra)
            db.commit()
            jid = extra.id
        n1, m1 = self.seed(self.jc, "independent-" + uuid4().hex)
        n2, m2 = self.seed(jid, "independent-" + uuid4().hex)
        pairs = []
        for job, native, refs in [(self.jc, n1, m1), (jid, n2, m2)]:
            payload = self.payload(methods=refs)
            payload["native_job_id"] = native
            pairs.append(
                (f"etl/workflows/{self.wc}/jobs/{job}/native-bindings", payload)
            )
        outcome = race(pairs)
        self.assertEqual(outcome, [201, 201])
        self.checks.append({"independent_targets": outcome})

    def test_committed_binding_survives_owned_api_sigkill_and_restart(self):
        import socket
        import subprocess
        import sys
        import time
        from urllib.request import urlopen

        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        base = f"http://127.0.0.1:{port}"
        out = Path(os.environ["ETL_SCOPE_EVIDENCE_DIR"])
        process = None
        with (out / "binding-api-restart.log").open("w") as log:

            def start():
                process = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "uvicorn",
                        "app.main:app",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        str(port),
                        "--no-access-log",
                    ],
                    cwd=Path(__file__).resolve().parents[1],
                    env=os.environ.copy(),
                    stdout=log,
                    stderr=subprocess.STDOUT,
                )
                for _ in range(100):
                    if process.poll() is not None:
                        raise AssertionError(
                            "Owned restart API exited before readiness"
                        )
                    try:
                        with urlopen(base + "/health", timeout=1) as r:
                            if r.status == 200:
                                return process
                    except OSError:
                        time.sleep(0.1)
                process.kill()
                process.wait(timeout=10)
                raise AssertionError("Owned restart API readiness timeout")

            try:
                process = start()
                first = self.req(self.base, "POST", self.payload(), 201, base_url=base)
                killed = process.pid
                process.kill()
                process.wait(timeout=10)
                self.assertEqual(process.returncode, -9)
                process = start()
                versions = self.req(self.base, base_url=base)["versions"]
                self.assertEqual([row["id"] for row in versions], [first["id"]])
                self.assertEqual(
                    versions[0]["identity_snapshot"], first["identity_snapshot"]
                )
                self.assertEqual(versions[0]["state"], "STAGED")
                (out / "binding-api-restart-results.json").write_text(
                    json.dumps(
                        {
                            "status": "PASS",
                            "killed_owned_api_pid": killed,
                            "replacement_owned_api_pid": process.pid,
                            "binding_id": first["id"],
                            "version_count": len(versions),
                            "boundary": "after acknowledged commit; same-version API restart; not collector durability or old-binary rollback",
                        },
                        indent=2,
                    )
                )
            finally:
                if process is not None and process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=10)
        self.assertIsNotNone(process.returncode)


class FreshnessPolicyTests(unittest.TestCase):
    def test_observed_and_committed_clocks_and_boundary(self):
        now = datetime.now(timezone.utc)
        self.assertEqual(service.receipt_freshness(now, now, now, 180), "FRESH")
        self.assertEqual(
            service.receipt_freshness(now, now - timedelta(seconds=180), now, 180),
            "FRESH",
        )
        self.assertEqual(
            service.receipt_freshness(now, now - timedelta(seconds=181), now, 180),
            "STALE",
        )
        self.assertEqual(
            service.receipt_freshness(now, now, now - timedelta(seconds=181), 180),
            "STALE",
        )
        self.assertEqual(
            service.receipt_freshness(now, now + timedelta(seconds=1), now, 180),
            "CLOCK_UNCERTAIN",
        )
        self.assertEqual(
            service.receipt_freshness(now, now, now + timedelta(seconds=1), 180),
            "CLOCK_UNCERTAIN",
        )
