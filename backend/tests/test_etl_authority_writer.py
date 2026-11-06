"""Real PostgreSQL/mixed binaries. Crypto probes never qualify a provider."""

import base64
import hashlib
import io
import json
import os
import socket
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from fastapi import HTTPException
from sqlalchemy import select, text, func, create_engine, inspect
from sqlalchemy.exc import DBAPIError
from sqlalchemy.engine import make_url
from urllib.request import urlopen, Request
from urllib.error import HTTPError
from app.db.session import SessionLocal, engine
from app.etl_bindings.authority import (
    Envelope,
    verify_signature,
    signed_bytes,
)
from app.etl_bindings.models import (
    ETLNativeBinding,
    ETLNativeAttestation,
    ETLBindingQualification,
)
from app.etl_bindings.writer import mark
from app.models import JobOrderHistory, ExecutionStatus, ExecutionType
from app.data_pipelines.models import PipelineSource, PipelineEvidence
from app.security.models import User
from app.security.passwords import hash_password
from tests import test_etl_binding_lifecycle as fixtures

ROOT = Path(__file__).resolve().parents[2]
OLD_SHAS = [
    "a915322b5c5c80b0d37dea71f6b7f70237082340",
    "a061bdbabe7e250fe7141861c193ca837ef14dbe",
]


def sign(private, body):
    parsed = Envelope.model_fields["body"].annotation.model_validate(body)
    raw = parsed.model_dump(mode="json")
    return {
        "issuer_key_id": "contract-only",
        "body": raw,
        "signature": base64.b64encode(private.sign(signed_bytes(raw))).decode(),
    }


def store_for(private):
    return {
        "version": 1,
        "issuers": {
            "contract-only": {
                "public_key_base64": base64.b64encode(
                    private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
                ).decode(),
                "assurance": "CONTRACT_TEST_ONLY",
                "revoked": False,
                "targets": {},
            }
        },
    }


@unittest.skipUnless(
    os.getenv("OPSCONTROL_ETL_SCOPE_ACCEPTANCE") == "1",
    "Owned migrated PostgreSQL/HTTP required",
)
class AuthorityWriterTests(unittest.TestCase):
    seed = fixtures.BindingLifecycleTests.seed
    req = fixtures.BindingLifecycleTests.req
    payload = fixtures.BindingLifecycleTests.payload
    stage = fixtures.BindingLifecycleTests.stage
    tearDown = fixtures.BindingLifecycleTests.tearDown

    def setUp(self):
        fixtures.BindingLifecycleTests.setUp(self)
        self.private = Ed25519PrivateKey.generate()
        self.store_path = Path(os.environ["OPSCONTROL_ETL_AUTHORITY_TRUST_STORE"])
        self.write_store(store_for(self.private))

    def write_store(self, store):
        temp = self.store_path.with_suffix(".next")
        temp.write_text(json.dumps(store))
        temp.chmod(0o600)
        temp.replace(self.store_path)

    def envelope(self, binding, **changes):
        now = datetime.now(timezone.utc)
        body = {
            "schema_version": 1,
            "assurance": "CONTRACT_TEST_ONLY",
            "organization_id": str(self.a),
            "environment": "PROD",
            "platform": "PENTAHO",
            "binding_id": binding["id"],
            "native_job_id": self.n,
            "observed_native_id": self.native,
            "canonical_authority_id": "CONTRACT-FIXTURE-NOT-PROVIDER",
            "authority_aliases": [self.namespace],
            "canonical_object_key": "contract-object-" + self.native,
            "object_kind": "JOB",
            "issued_at": now,
            "not_before": now - timedelta(seconds=1),
            "expires_at": now + timedelta(minutes=15),
            "methods": [
                {
                    "method_id": m["method_id"],
                    "source_id": m["source_id"],
                    "generation": m["generation"],
                    "revision": m["revision"],
                    "reader_definition_hash": m["reader_definition_hash"],
                    "evidence_id": str(uuid4()),
                    "payload_sha256": "0" * 64,
                    "exact_build": "CONTRACT_FIXTURE_NOT_AN_INSTALLED_PROVIDER_BUILD",
                }
                for m in binding["method_snapshot"]
            ],
        }
        body.update(changes)
        return sign(self.private, body)

    def test_signed_contract_preview_cannot_persist_or_confirm_provider_authority(self):
        first = self.stage()
        envelope = self.envelope(first)
        data = self.req(
            "etl/native-authority/validate-envelope", "POST", {"envelope": envelope}
        )
        self.assertEqual(data["status"], "CONTRACT_VALID_NOT_QUALIFIED")
        self.assertFalse(data["qualified"])
        self.assertFalse(data["persisted"])
        self.assertEqual(data["monitoring_activation"], "BLOCKED")
        with SessionLocal() as db:
            reviewer = User(
                username="authority-reviewer-" + uuid4().hex,
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
        self.req(
            "etl/native-authority/attestations",
            "POST",
            {"envelope": envelope},
            409,
            token,
        )
        forged = self.envelope(first, assurance="PROVIDER_QUALIFIED")
        self.req(
            "etl/native-authority/validate-envelope", "POST", {"envelope": forged}, 409
        )
        self.req(self.base, "POST", self.payload("CONFIRM", first), 403)
        with SessionLocal() as db:
            self.assertEqual(
                db.scalar(select(func.count()).select_from(ETLNativeAttestation)), 0
            )
            self.assertEqual(
                db.scalar(select(func.count()).select_from(ETLBindingQualification)), 0
            )
        output = {
            "status": "PASS_CONTRACT_VALIDATION_ONLY",
            "provider_qualified": False,
            "preview": data,
            "contract_test_envelope": envelope,
            "contract_test_public_trust": store_for(self.private),
            "genuine_provider_positive": "BLOCKED / NOT RUN",
        }
        (
            Path(os.environ["ETL_SCOPE_EVIDENCE_DIR"])
            / "authority-envelope-results.json"
        ).write_text(json.dumps(output, indent=2))

    def test_aliases_have_one_canonical_key_but_operator_changes_cannot_claim_authority(
        self,
    ):
        first = self.stage()
        one = self.envelope(first)
        two = self.envelope(
            first, authority_aliases=[self.namespace, "signed-other-alias"]
        )
        a = verify_signature(Envelope.model_validate(one), store_for(self.private))
        b = verify_signature(Envelope.model_validate(two), store_for(self.private))
        self.assertEqual(a["target_key"], b["target_key"])
        self.assertFalse(a["qualified"])
        self.assertFalse(b["qualified"])
        bad = self.envelope(first, authority_aliases=["operator-unrelated-namespace"])
        self.req(
            "etl/native-authority/validate-envelope", "POST", {"envelope": bad}, 409
        )
        foreign = self.envelope(first, organization_id=str(self.b))
        self.req(
            "etl/native-authority/validate-envelope", "POST", {"envelope": foreign}, 409
        )
        changed = self.envelope(first)
        changed["body"]["methods"][0]["generation"] = str(uuid4())
        changed = sign(self.private, changed["body"])
        self.req(
            "etl/native-authority/validate-envelope", "POST", {"envelope": changed}, 409
        )

    def test_expiry_signature_and_live_issuer_revocation_are_rejected(self):
        first = self.stage()
        expired = self.envelope(
            first, expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)
        )
        self.req(
            "etl/native-authority/validate-envelope", "POST", {"envelope": expired}, 409
        )
        tampered = self.envelope(first)
        tampered["body"]["canonical_object_key"] = "tampered"
        self.req(
            "etl/native-authority/validate-envelope",
            "POST",
            {"envelope": tampered},
            409,
        )
        envelope = self.envelope(first)
        store = store_for(self.private)
        store["issuers"]["contract-only"]["revoked"] = True
        self.write_store(store)
        self.req(
            "etl/native-authority/validate-envelope",
            "POST",
            {"envelope": envelope},
            409,
        )
        self.assertEqual(len(self.req(self.base)["versions"]), 1)

    def test_transaction_local_writer_marker_cannot_leak_to_old_requests(self):
        first = self.stage()
        with engine.connect() as c:
            c.execute(
                text("SELECT set_config('opscontrol.etl_writer_protocol','1',true)")
            )
            c.commit()
            self.assertNotEqual(
                c.scalar(
                    text(
                        "SELECT current_setting('opscontrol.etl_writer_protocol',true)"
                    )
                ),
                "1",
            )
            c.rollback()
            with self.assertRaises(DBAPIError):
                c.execute(
                    text("UPDATE job_orders SET name='old-writer' WHERE id=:id"),
                    {"id": self.j1},
                )
                c.commit()
            c.rollback()
        self.req(
            f"etl/workflows/{self.wa}/jobs/{self.j1}",
            "PATCH",
            {"name": "current-authorized-configuration"},
        )
        self.assertEqual(self.req(self.base)["versions"][0]["id"], first["id"])

    def test_old_sql_bypasses_and_checkpoint_batch_are_rolled_back(self):
        self.stage()
        source_id = UUID(self.methods[0]["source_id"])
        statements = [
            ("UPDATE job_orders SET name='old-bypass' WHERE id=:id", {"id": self.j1}),
            (
                "UPDATE monitoring_resources SET activation_status='ACTIVE' WHERE job_order_id=:id",
                {"id": self.j1},
            ),
            ("UPDATE pipeline_jobs SET selected=true WHERE id=:id", {"id": self.n}),
            (
                "UPDATE pipeline_methods SET revision=revision+1 WHERE id=:id",
                {"id": self.methods[0]["id"]},
            ),
            (
                "UPDATE pipeline_sources SET generation=:g WHERE id=:id",
                {"id": source_id, "g": uuid4()},
            ),
        ]
        with SessionLocal() as db:
            before = db.get(PipelineSource, source_id).live_checkpoint
        for sql, params in statements:
            with SessionLocal() as db:
                with self.assertRaises(DBAPIError) as e:
                    db.execute(text(sql), params)
                    db.commit()
                self.assertIn("OC_ETL_WRITER_VERSION_REQUIRED", str(e.exception.orig))
                db.rollback()
        with SessionLocal() as db:
            source = db.get(PipelineSource, source_id)
            source.live_checkpoint = {"old_should_rollback": True}
            evidence = PipelineEvidence(
                organization_id=self.a,
                source_id=source_id,
                generation=source.generation,
                external_key="old-fenced-" + uuid4().hex,
                native_job_id=self.native,
                payload={"fixture": True},
                outcome="ACCEPTED",
                observed_at=datetime.now(timezone.utc),
            )
            db.add(evidence)
            with self.assertRaises(DBAPIError):
                db.commit()
            db.rollback()
        with SessionLocal() as db:
            self.assertEqual(db.get(PipelineSource, source_id).live_checkpoint, before)
            self.assertEqual(
                db.scalar(
                    select(func.count())
                    .select_from(PipelineEvidence)
                    .where(PipelineEvidence.source_id == source_id)
                ),
                0,
            )
        # Current writer may retain a quarantined raw receipt; no projection or
        # authority is invented and the deduplication identity is unchanged.
        with SessionLocal() as db:
            mark(db)
            source = db.get(PipelineSource, source_id)
            db.add(
                PipelineEvidence(
                    organization_id=self.a,
                    source_id=source_id,
                    generation=source.generation,
                    external_key="current-quarantine",
                    native_job_id=self.native,
                    payload={"fixture": True},
                    outcome="QUARANTINED_IDENTITY",
                    observed_at=datetime.now(timezone.utc),
                )
            )
            db.commit()

    def test_legacy_write_before_optin_commits_before_the_binding(self):
        event_id = uuid4()
        with SessionLocal() as old:
            old.add(
                JobOrderHistory(
                    id=event_id,
                    job_order_id=self.j1,
                    execution_type=ExecutionType.SCHEDULED,
                    status=ExecutionStatus.FAILED,
                    source_result="before-optin-stable-id",
                )
            )
            old.flush()
            with ThreadPoolExecutor(1) as pool:
                pending = pool.submit(self.stage)
                time.sleep(0.2)
                self.assertFalse(pending.done())
                old.commit()
                binding = pending.result(timeout=15)
        with SessionLocal() as db:
            event = db.get(JobOrderHistory, event_id)
            version = db.get(ETLNativeBinding, UUID(binding["id"]))
            self.assertIsNotNone(event)
            self.assertLessEqual(
                event.created_at.replace(tzinfo=timezone.utc), version.valid_from
            )
            self.assertEqual(event.source_result, "before-optin-stable-id")
        # The opposite order is explicitly refused, not silently attributed.
        self.req(
            f"etl/job-orders/{self.j1}/executions",
            "POST",
            {
                "execution_type": "SCHEDULED",
                "status": "SUCCESS",
                "source_result": "after-optin-rejected",
            },
            409,
        )

    def old_denial(self, path, method, payload, status, base_url):
        try:
            with urlopen(
                Request(
                    base_url + "/api/v1/" + path,
                    method=method,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": "Bearer " + self.token,
                        "X-OpsControl-Customers": str(self.a),
                    },
                    data=json.dumps(payload).encode(),
                ),
                timeout=20,
            ) as response:
                actual = response.status
                body = response.read().decode()
        except HTTPError as error:
            actual = error.code
            body = error.read().decode()
        self.assertEqual(actual, status)
        self.assertEqual(body, "Internal Server Error")
        self.checks.append(
            {
                "method": method,
                "path": path,
                "expected": status,
                "actual": actual,
                "body_sha256": hashlib.sha256(body.encode()).hexdigest(),
                "older_unmodified_handler": True,
            }
        )

    def start_old(self, sha, private, log):
        archive = subprocess.check_output(
            ["git", "archive", sha, "backend/app"], cwd=ROOT
        )
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(private, filter="data")
        backend = Path(private) / "backend"
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--app-dir",
                str(backend),
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--no-access-log",
            ],
            cwd=backend,
            env=os.environ.copy(),
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        base = f"http://127.0.0.1:{port}"
        for _ in range(100):
            if process.poll() is not None:
                raise AssertionError("Exact older API exited before readiness")
            try:
                with urlopen(base + "/health", timeout=1) as r:
                    if r.status == 200:
                        return process, base, hashlib.sha256(archive).hexdigest()
            except OSError:
                time.sleep(0.1)
        process.kill()
        process.wait(timeout=10)
        raise AssertionError("Older API readiness timeout")

    def test_exact_older_binaries_read_but_cannot_write_opted_in_jobs_after_restart(
        self,
    ):
        binding = self.stage()
        out = Path(os.environ["ETL_SCOPE_EVIDENCE_DIR"])
        results = []
        for sha in OLD_SHAS:
            process = None
            with tempfile.TemporaryDirectory(prefix="etl007-old-api-") as private, (
                out / ("old-api-" + sha[:7] + ".log")
            ).open("w") as log:
                try:
                    process, base, archive_hash = self.start_old(sha, private, log)
                    self.req(f"etl/workflows/{self.wa}/monitoring", base_url=base)
                    self.req(
                        f"etl/job-orders/{self.j2}/executions",
                        "POST",
                        {
                            "execution_type": "SCHEDULED",
                            "status": "FAILED",
                            "source_result": "legacy-safe-" + sha,
                        },
                        201,
                        base_url=base,
                    )
                    for _ in range(2):
                        self.old_denial(
                            f"etl/job-orders/{self.j1}/executions",
                            "POST",
                            {
                                "execution_type": "SCHEDULED",
                                "status": "SUCCESS",
                                "source_result": "old-blocked-" + sha,
                            },
                            500,
                            base_url=base,
                        )
                    process.kill()
                    process.wait(timeout=10)
                    # The fence survives a whole old-process restart, not a session flag.
                    process, base, _ = self.start_old(sha, private, log)
                    self.old_denial(
                        f"etl/job-orders/{self.j1}/executions",
                        "POST",
                        {"execution_type": "SCHEDULED", "status": "SUCCESS"},
                        500,
                        base_url=base,
                    )
                    results.append(
                        {
                            "source_sha": sha,
                            "archive_sha256": archive_hash,
                            "legacy_unaffected_http": 201,
                            "opted_in_http": [500, 500, 500],
                            "meaning": "DB refusal under unchanged older handler; old health/read200 is not safe writer readiness",
                        }
                    )
                finally:
                    if process and process.poll() is None:
                        process.terminate()
                        try:
                            process.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait(timeout=10)
        with SessionLocal() as db:
            self.assertEqual(
                db.scalar(
                    select(func.count())
                    .select_from(JobOrderHistory)
                    .where(JobOrderHistory.job_order_id == self.j1)
                ),
                0,
            )
            self.assertEqual(
                db.scalar(
                    select(func.count())
                    .select_from(JobOrderHistory)
                    .where(JobOrderHistory.job_order_id == self.j2)
                ),
                2,
            )
            self.assertEqual(
                db.get(ETLNativeBinding, UUID(binding["id"])).state, "STAGED"
            )
        for sha in OLD_SHAS:
            self.assertGreaterEqual(
                (out / ("old-api-" + sha[:7] + ".log"))
                .read_text()
                .count("OC_ETL_WRITER_VERSION_REQUIRED"),
                3,
            )
        (out / "older-writer-results.json").write_text(
            json.dumps(
                {
                    "status": "PASS_FENCE_ENFORCEMENT_ONLY",
                    "older_full_writer_compatibility": "BLOCKED",
                    "binaries": results,
                    "opted_in_persisted": 0,
                    "unaffected_legacy_persisted": 2,
                },
                indent=2,
            )
        )

    def test_writer_fence_survives_restore_and_unsafe_downgrade_refuses(self):
        self.stage()
        out = Path(os.environ["ETL_SCOPE_EVIDENCE_DIR"])
        url = make_url(os.environ["DATABASE_URL"])

        def snapshot(e):
            with e.connect() as c:
                i = inspect(c)
                result = {}
                for name in sorted(i.get_table_names()):
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
                            for x in i.get_columns(name)
                        ],
                        "foreign_keys": i.get_foreign_keys(name),
                    }
                return result

        before = snapshot(engine)
        refused = subprocess.run(
            [sys.executable, "-m", "alembic", "downgrade", "0040_etl_native_bindings"],
            cwd=ROOT / "backend",
            capture_output=True,
            text=True,
            timeout=60,
        )
        (out / "writer-fence-downgrade-refusal.log").write_text(
            (refused.stdout + refused.stderr).replace(url.password, "[REDACTED]")
        )
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn(
            "Unsafe populated ETL downgrade blocked before DDL", refused.stderr
        )
        self.assertEqual(snapshot(engine), before)
        docker = [
            "docker",
            "--host=unix:///var/run/docker.sock",
            "exec",
            "-i",
            os.environ["ETL_SCOPE_CONTAINER"],
        ]
        dump = subprocess.run(
            [*docker, "pg_dump", "-U", "postgres", "-Fc", url.database],
            capture_output=True,
            timeout=90,
        )
        self.assertEqual(dump.returncode, 0)
        (out / "synthetic-authority-writer-backup.dump").write_bytes(dump.stdout)
        restored = "writer_restore_" + uuid4().hex[:10]
        try:
            subprocess.run(
                [*docker, "createdb", "-U", "postgres", restored],
                check=True,
                capture_output=True,
                timeout=30,
            )
            result = subprocess.run(
                [*docker, "pg_restore", "-U", "postgres", "--no-owner", "-d", restored],
                input=dump.stdout,
                capture_output=True,
                timeout=90,
            )
            self.assertEqual(result.returncode, 0, result.stderr.decode()[-1200:])
            e = create_engine(url.set(database=restored))
            try:
                self.assertEqual(snapshot(e), before)
                with e.begin() as c:
                    with self.assertRaises(DBAPIError) as error:
                        c.execute(
                            text(
                                "UPDATE job_orders SET name='old-restored-bypass' WHERE id=:id"
                            ),
                            {"id": self.j1},
                        )
                    self.assertIn(
                        "OC_ETL_WRITER_VERSION_REQUIRED", str(error.exception.orig)
                    )
            finally:
                e.dispose()
        finally:
            subprocess.run(
                [*docker, "dropdb", "-U", "postgres", restored],
                check=True,
                capture_output=True,
                timeout=30,
            )
        with SessionLocal() as db:
            inventory = {
                "scope": "isolated synthetic fixture database only; not owner UAT/production",
                "provider_qualified_attestations": db.scalar(
                    select(func.count()).select_from(ETLNativeAttestation)
                ),
                "claims": [
                    {
                        "binding_id": str(b.id),
                        "state": b.state,
                        "identity_claim": b.identity_snapshot,
                        "methods": b.method_snapshot,
                        "qualified": False,
                    }
                    for b in db.scalars(select(ETLNativeBinding)).all()
                ],
            }
        (out / "native-authority-inventory.json").write_text(
            json.dumps(inventory, indent=2)
        )
        (out / "writer-restore-results.json").write_text(
            json.dumps(
                {
                    "status": "PASS_FENCE_AND_RESTORE_ONLY",
                    "downgrade_exit": refused.returncode,
                    "source": before,
                    "restored": before,
                    "archive_sha256": hashlib.sha256(dump.stdout).hexdigest(),
                    "restored_old_writer_refused": True,
                },
                indent=2,
            )
        )

    @unittest.skipUnless(
        os.getenv("ETL_WORKFLOW_UI_ACCEPTANCE") == "1", "Owned browser required"
    )
    def test_browser_contract_preview_never_qualifies_or_activates(self):
        first = self.stage()
        fixture = {
            "a": str(self.a),
            "username": self.username,
            "password": self.password,
            "token": self.token,
            "envelope": self.envelope(first),
        }
        with tempfile.TemporaryDirectory(prefix="etl007-browser-private-") as private:
            path = Path(private) / "fixture.json"
            path.write_text(json.dumps(fixture))
            path.chmod(0o600)
            env = {**os.environ, "ETL_AUTHORITY_BROWSER_FIXTURE": str(path)}
            result = subprocess.run(
                ["node", "frontend/scripts/native_authority_acceptance.mjs"],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=120,
            )
        (
            Path(os.environ["ETL_SCOPE_EVIDENCE_DIR"]) / "authority-browser.log"
        ).write_text(
            (result.stdout + result.stderr)
            .replace(self.password, "[REDACTED]")
            .replace(self.token, "[REDACTED]")
        )
        self.assertEqual(result.returncode, 0, "See redacted authority-browser.log")


class AuthorityEnvelopePolicyTests(unittest.TestCase):
    def fixture(self):
        key = Ed25519PrivateKey.generate()
        now = datetime.now(timezone.utc)
        body = {
            "schema_version": 1,
            "assurance": "CONTRACT_TEST_ONLY",
            "organization_id": str(uuid4()),
            "environment": "TEST",
            "platform": "PENTAHO",
            "binding_id": str(uuid4()),
            "native_job_id": str(uuid4()),
            "observed_native_id": "opaque-test-id",
            "canonical_authority_id": "CONTRACT_ONLY",
            "authority_aliases": ["contract-alias"],
            "canonical_object_key": "opaque-test-object",
            "object_kind": "JOB",
            "issued_at": now,
            "not_before": now - timedelta(seconds=1),
            "expires_at": now + timedelta(minutes=10),
            "methods": [
                {
                    "method_id": str(uuid4()),
                    "source_id": str(uuid4()),
                    "generation": str(uuid4()),
                    "revision": 1,
                    "reader_definition_hash": "0" * 64,
                    "evidence_id": str(uuid4()),
                    "payload_sha256": "0" * 64,
                    "exact_build": "CONTRACT_ONLY",
                }
            ],
        }
        return key, body

    def test_valid_signature_is_not_provider_qualification(self):
        key, body = self.fixture()
        result = verify_signature(
            Envelope.model_validate(sign(key, body)), store_for(key)
        )
        self.assertEqual(result["status"], "CONTRACT_VALID_NOT_QUALIFIED")
        self.assertFalse(result["qualified"])
        body["assurance"] = "PROVIDER_QUALIFIED"
        with self.assertRaises(HTTPException) as e:
            verify_signature(Envelope.model_validate(sign(key, body)), store_for(key))
        self.assertEqual(e.exception.detail, "TEST_ISSUER_CANNOT_QUALIFY_PROVIDER")

    def test_expired_future_unbounded_duplicate_and_tampered_contracts_refuse(self):
        key, body = self.fixture()
        now = datetime.now(timezone.utc)
        cases = [
            {**body, "expires_at": now - timedelta(seconds=1)},
            {**body, "issued_at": now + timedelta(hours=1)},
            {**body, "expires_at": now + timedelta(days=2)},
            {**body, "authority_aliases": ["duplicate", "duplicate"]},
        ]
        for candidate in cases:
            with self.assertRaises(HTTPException):
                verify_signature(
                    Envelope.model_validate(sign(key, candidate)), store_for(key)
                )
        envelope = sign(key, body)
        envelope["body"]["canonical_object_key"] = "changed"
        with self.assertRaises(HTTPException):
            verify_signature(Envelope.model_validate(envelope), store_for(key))
