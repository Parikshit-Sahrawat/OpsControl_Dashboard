"""Disposable PostgreSQL/real authenticated handlers; never native certification."""

import os
import secrets
import unittest
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from types import SimpleNamespace
from sqlalchemy import select, func
import json
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import app.main
from app.db.session import SessionLocal
from app.models import (
    Organization,
    VM,
    JobOrder,
    DataSource,
    Collector,
    JobOrderHistory,
    JobStepExecution,
)
from app.security.models import User
from app.security.passwords import hash_password
from app.security.permission_catalog import PROVIDER_ID
from app.unified.models import NormalizedEvent, MonitoringResource, ResourceDependency
from app.worker.pentaho_status import parse_carte_status
from app.services.etl_monitoring import ingest_snapshot

NATIVE = Path(__file__).resolve().parents[2] / "tests/fixtures/pentaho/native-evidence"


@unittest.skipUnless(
    os.getenv("OPSCONTROL_V16_ACCEPTANCE") == "1",
    "Owned disposable PostgreSQL required",
)
class AuditRemediation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.private = tempfile.TemporaryDirectory(prefix="opscontrol-remediation-http-")
        cls.addClassCleanup(cls.private.cleanup)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        cls.base = "http://127.0.0.1:" + str(port)
        log = open(Path(cls.private.name) / "api.log", "w")
        cls.addClassCleanup(log.close)
        proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            stdout=log,
            stderr=log,
        )

        def stop():
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()

        cls.addClassCleanup(stop)
        for _ in range(100):
            try:
                with urlopen(cls.base + "/health", timeout=1) as response:
                    if response.status == 200:
                        break
            except OSError:
                time.sleep(0.1)
        else:
            raise RuntimeError("Disposable HTTP service did not start")

    def setUp(self):
        self.db = SessionLocal()
        self.addCleanup(self.db.close)
        self.org = Organization(
            name="Remediation " + uuid.uuid4().hex, code=uuid.uuid4().hex[:12]
        )
        self.foreign = Organization(
            name="Other " + uuid.uuid4().hex, code=uuid.uuid4().hex[:12]
        )
        self.db.add_all([self.org, self.foreign])
        self.db.flush()
        self.vm = VM(
            organization_id=self.org.id,
            hostname=uuid.uuid4().hex + ".invalid",
            environment="TEST",
            os="Linux",
        )
        self.db.add(self.vm)
        self.db.flush()
        self.job = JobOrder(
            organization_id=self.org.id,
            vm_id=self.vm.id,
            name="Native fixture replay",
            environment="TEST",
            active=True,
            monitoring_enabled=True,
        )
        self.source = DataSource(
            organization_id=self.org.id,
            name="Disabled fixture source",
            source_type="PENTAHO",
            enabled=False,
        )
        self.db.add_all([self.job, self.source])
        self.db.flush()
        self.collector = Collector(
            data_source_id=self.source.id,
            name="Disabled fixture collector",
            collector_type="PENTAHO",
            enabled=False,
            configuration={"job_order_id": str(self.job.id)},
        )
        self.password = secrets.token_urlsafe(24)
        self.user = User(
            username="remed-" + uuid.uuid4().hex,
            full_name="Synthetic administrator",
            password_hash=hash_password(self.password),
            active=True,
            platform_admin=True,
            service_provider_id=PROVIDER_ID,
        )
        self.db.add_all([self.collector, self.user])
        self.db.commit()
        base = self.base

        class OwnedHttp:
            def call(self, path, method="GET", json=None, headers=None):
                body = None if json is None else __import__("json").dumps(json).encode()
                request = Request(
                    base + path,
                    data=body,
                    method=method,
                    headers={"Content-Type": "application/json", **(headers or {})},
                )
                try:
                    response = urlopen(request, timeout=15)
                except HTTPError as error:
                    response = error
                with response:
                    text = response.read().decode()
                    return SimpleNamespace(
                        status_code=response.status,
                        text=text,
                        json=lambda: __import__("json").loads(text),
                    )

            def get(self, path, **kw):
                return self.call(path, **kw)

            def post(self, path, **kw):
                return self.call(path, method="POST", **kw)

        self.client = OwnedHttp()
        login = self.client.post(
            "/api/v1/auth/login",
            json={"username": self.user.username, "password": self.password},
        )
        self.assertEqual(login.status_code, 200)
        self.headers = {
            "Authorization": "Bearer " + login.json()["access_token"],
            "X-OpsControl-Customers": str(self.org.id),
        }
        self.now = datetime.now(timezone.utc)

    def ingest(self, records, observed=None):
        ingest_snapshot(
            self.collector,
            SimpleNamespace(
                payload={
                    "provider": "PENTAHO",
                    "inventory_complete": False,
                    "executions": records,
                }
            ),
            observed or self.now,
            self.db,
        )
        self.db.commit()

    def history(self, identity):
        return self.db.scalar(
            select(JobOrderHistory).where(
                JobOrderHistory.job_order_id == self.job.id,
                JobOrderHistory.provider_execution_id == identity,
            )
        )

    def test_native_partial_three_of_three_idempotent_and_empty_preserves(self):
        rows = [
            parse_carte_status((NATIVE / name).read_bytes(), True)
            for name in (
                "RT-LAB-010O-final-job-status.xml",
                "RT-LAB-010D-job-status.xml",
                "RT-LAB-010H-final-job-status.xml",
            )
        ]
        self.ingest(rows)
        histories = self.db.scalars(
            select(JobOrderHistory).where(JobOrderHistory.job_order_id == self.job.id)
        ).all()
        self.assertEqual(len(histories), 3)
        self.assertEqual(
            {h.provider_execution_id for h in histories},
            {r["execution_id"] for r in rows},
        )
        self.assertEqual(
            sorted(h.status.value for h in histories), ["FAILED", "FAILED", "SUCCESS"]
        )
        events = self.db.scalar(
            select(func.count())
            .select_from(NormalizedEvent)
            .where(NormalizedEvent.organization_id == self.org.id)
        )
        self.assertEqual(events, 3)
        self.ingest(rows)
        self.ingest([])
        self.assertEqual(
            self.db.scalar(
                select(func.count())
                .select_from(JobOrderHistory)
                .where(JobOrderHistory.job_order_id == self.job.id)
            ),
            3,
        )
        self.assertEqual(
            self.db.scalar(
                select(func.count())
                .select_from(NormalizedEvent)
                .where(NormalizedEvent.organization_id == self.org.id)
            ),
            3,
        )
        for row in rows:
            h = self.history(row["execution_id"])
            response = self.client.get(
                "/api/v1/etl/executions/" + str(h.id), headers=self.headers
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.json()["source_evidence"]["native_result"],
                row["native_result"],
            )
            denied = self.client.get(
                "/api/v1/etl/executions/" + str(h.id),
                headers={
                    **self.headers,
                    "X-OpsControl-Customers": str(self.foreign.id),
                },
            )
            self.assertEqual(denied.status_code, 404)
        self.assertFalse(any(h.status.value == "NO_RUN" for h in histories))

    def test_conflicting_and_out_of_order_claims_preserve_projection_and_raw_evidence(
        self,
    ):
        native = parse_carte_status(
            (NATIVE / "RT-LAB-010O-final-job-status.xml").read_bytes()
        )
        self.ingest([native])
        h = self.history(native["execution_id"])
        original = dict(h.source_evidence)
        conflict = {
            **native,
            "execution_status": "FAILED",
            "native_result": "N",
            "nr_errors": 1,
        }
        self.ingest([conflict], self.now + timedelta(seconds=1))
        self.db.refresh(h)
        self.assertEqual(h.status.value, "SUCCESS")
        self.assertEqual(h.source_evidence, original)
        self.assertTrue(h.monitoring_conditions["CONFLICTING_TERMINAL_EVIDENCE"])
        event = self.db.scalar(
            select(NormalizedEvent).where(
                NormalizedEvent.organization_id == self.org.id,
                NormalizedEvent.processing_status == "QUARANTINED",
            )
        )
        self.assertEqual(event.payload["native_observation"]["native_result"], "N")
        self.ingest([conflict], self.now + timedelta(seconds=2))
        self.assertEqual(
            self.db.scalar(
                select(func.count())
                .select_from(NormalizedEvent)
                .where(NormalizedEvent.organization_id == self.org.id)
            ),
            2,
        )
        self.ingest(
            [{**native, "execution_status": "RUNNING", "native_result": None}],
            self.now - timedelta(seconds=20),
        )
        self.db.refresh(h)
        self.assertEqual(h.status.value, "SUCCESS")
        self.assertEqual(h.source_evidence, original)
        self.assertEqual(
            self.db.scalar(
                select(func.count())
                .select_from(NormalizedEvent)
                .where(NormalizedEvent.organization_id == self.org.id)
            ),
            3,
        )

    def test_reordered_native_step_copies_and_nullable_metrics_survive_api(self):
        native = parse_carte_status(
            (NATIVE / "RT-LAB-005B-execution-status.xml").read_bytes(),
            workload_kind="TRANSFORMATION",
        )
        # Explicit synthetic duplicate/reordered rows, not native child UUID proof.
        first = {**native["steps"][0], "name": "same", "copy": "0"}
        second = {
            **first,
            "copy": "1",
            "nr_errors": None,
            "metrics": {
                "linesRead": None,
                "linesWritten": 0,
                "linesInput": None,
                "linesOutput": None,
                "errors": None,
            },
        }
        native = {**native, "steps": [first, second]}
        self.ingest([native])
        h = self.history(native["execution_id"])
        before = {
            s.source_evidence["native_copy"]: s.id
            for s in self.db.scalars(
                select(JobStepExecution).where(JobStepExecution.history_id == h.id)
            )
        }
        self.ingest(
            [{**native, "steps": [second, first]}], self.now + timedelta(seconds=1)
        )
        self.db.expire_all()
        after = {
            s.source_evidence["native_copy"]: s.id
            for s in self.db.scalars(
                select(JobStepExecution).where(JobStepExecution.history_id == h.id)
            )
        }
        self.assertEqual(before, after)
        self.assertEqual(len(after), 2)
        response = self.client.get(
            "/api/v1/etl/executions/" + str(h.id), headers=self.headers
        )
        self.assertEqual(response.status_code, 200)
        rows = response.json()["steps"]
        self.assertEqual(len(rows), 2)
        missing = next(r for r in rows if r["source_evidence"]["native_copy"] == "1")
        self.assertIsNone(missing["records_read"])
        self.assertEqual(missing["records_written"], 0)
        self.assertIsNone(missing["source_evidence"]["native_metrics"]["linesInput"])

    def test_unknown_observation_never_resolves_verified_failure(self):
        from app.models import AlertIncidentEvent

        failed = parse_carte_status(
            (NATIVE / "RT-LAB-010D-job-status.xml").read_bytes()
        )
        self.ingest([failed])
        before = self.db.scalar(
            select(func.count())
            .select_from(AlertIncidentEvent)
            .join(JobOrderHistory)
            .where(
                JobOrderHistory.job_order_id == self.job.id,
                AlertIncidentEvent.event_type == "JOB_FAILED_RESOLVED",
            )
        )
        self.ingest(
            [
                {
                    "execution_id": "missing-proof",
                    "execution_status": "UNKNOWN",
                    "nr_errors": None,
                }
            ],
            self.now + timedelta(seconds=1),
        )
        self.assertEqual(
            self.db.scalar(
                select(func.count())
                .select_from(AlertIncidentEvent)
                .join(JobOrderHistory)
                .where(
                    JobOrderHistory.job_order_id == self.job.id,
                    AlertIncidentEvent.event_type == "JOB_FAILED_RESOLVED",
                )
            ),
            before,
        )

    def test_paged_sources_collectors_scoped_totals_and_legacy_shape(self):
        sources = [
            DataSource(
                organization_id=self.org.id,
                name=f"Page {i:04}",
                source_type="HTTP",
                enabled=False,
            )
            for i in range(505)
        ]
        self.db.add_all(sources)
        self.db.flush()
        foreign = DataSource(
            organization_id=self.foreign.id,
            name="Page foreign",
            source_type="HTTP",
            enabled=False,
        )
        self.db.add(foreign)
        self.db.flush()
        cs = [
            Collector(
                data_source_id=sources[0].id,
                name=f"Page {i:04}",
                collector_type="HTTP",
                enabled=False,
            )
            for i in range(505)
        ]
        self.db.add_all(cs)
        self.db.commit()
        for path, extra in [
            ("/api/v1/resource-management/data-sources", "search=Page"),
            (
                "/api/v1/resource-management/collectors",
                "search=Page&data_source_id=" + str(sources[0].id),
            ),
        ]:
            ids = []
            for offset in range(0, 505, 200):
                r = self.client.get(
                    path
                    + "?paginated=true&limit=200&offset="
                    + str(offset)
                    + "&"
                    + extra,
                    headers=self.headers,
                )
                self.assertEqual(r.status_code, 200)
                body = r.json()
                self.assertEqual(body["total"], 505)
                self.assertEqual(body["has_more"], offset + len(body["items"]) < 505)
                ids.extend(x["id"] for x in body["items"])
            self.assertEqual(len(ids), 505)
            self.assertEqual(len(set(ids)), 505)
            legacy = self.client.get(path + "?limit=1&" + extra, headers=self.headers)
            self.assertIsInstance(legacy.json(), list)
            self.assertEqual(len(legacy.json()), 1)
        r = self.client.get(
            "/api/v1/resource-management/data-sources?paginated=true&search=Page&organization_id="
            + str(self.foreign.id),
            headers=self.headers,
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["total"], 0)
        no_selection = self.client.get(
            "/api/v1/resource-management/data-sources?paginated=true",
            headers={**self.headers, "X-OpsControl-Customers": ""},
        )
        self.assertEqual(no_selection.status_code, 200)
        self.assertEqual(no_selection.json()["total"], 0)

    def test_dependency_preview_and_pages_preserve_full_scoped_history(self):
        root = self.db.scalar(
            select(MonitoringResource).where(
                MonitoringResource.job_order_id == self.job.id
            )
        )
        host = self.db.scalar(
            select(MonitoringResource).where(
                MonitoringResource.vm_id == self.vm.id,
                MonitoringResource.domain == "VM",
            )
        )
        self.db.add_all(
            [
                ResourceDependency(
                    organization_id=self.org.id,
                    resource_id=root.id,
                    depends_on_id=host.id,
                    relationship_type="DEPENDS_ON",
                    service_identity="controlled-" + str(i),
                    valid_from=self.now - timedelta(hours=i + 1),
                    valid_to=self.now - timedelta(hours=i + 1) + timedelta(minutes=10),
                )
                for i in range(75)
            ]
        )
        self.db.commit()
        detail = self.client.get(
            "/api/v1/unified/resources/" + str(root.id), headers=self.headers
        )
        self.assertEqual(detail.status_code, 200)
        value = detail.json()
        self.assertEqual(len(value["dependencies"]), 50)
        self.assertTrue(value["dependency_has_more"])
        self.assertGreaterEqual(value["dependency_total"], 75)
        ids = []
        for offset in range(0, value["dependency_total"], 20):
            result = self.client.get(
                "/api/v1/unified/resources/"
                + str(root.id)
                + "/dependencies?limit=20&offset="
                + str(offset),
                headers=self.headers,
            )
            self.assertEqual(result.status_code, 200)
            page = result.json()
            self.assertEqual(page["total"], value["dependency_total"])
            ids.extend(r["id"] for r in page["items"])
        self.assertEqual(len(ids), value["dependency_total"])
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(ids[:50], [r["id"] for r in value["dependencies"]])
        denied = self.client.get(
            "/api/v1/unified/resources/" + str(root.id) + "/dependencies",
            headers={**self.headers, "X-OpsControl-Customers": str(self.foreign.id)},
        )
        self.assertEqual(denied.status_code, 404)

    def test_inline_platform_creation_is_atomic_and_does_not_change_other_scope(self):
        body = {
            "name": "Inline VM",
            "hostname": uuid.uuid4().hex + ".invalid",
            "address": "192.0.2.30",
            "environment": "TEST",
            "os_type": "Linux",
            "new_customer": {
                "name": "Inline " + uuid.uuid4().hex,
                "code": uuid.uuid4().hex[:12],
            },
        }
        created = self.client.post(
            "/api/v1/unified/resources/vm", json=body, headers=self.headers
        )
        self.assertEqual(created.status_code, 201, created.text)
        org = created.json()["organization_id"]
        self.assertNotEqual(org, str(self.org.id))
        old_scope = self.client.get(
            "/api/v1/unified/resources/" + created.json()["id"], headers=self.headers
        )
        self.assertEqual(old_scope.status_code, 404)
        new_scope = self.client.get(
            "/api/v1/unified/resources/" + created.json()["id"],
            headers={**self.headers, "X-OpsControl-Customers": org},
        )
        self.assertEqual(new_scope.status_code, 200)
        ambiguous = self.client.post(
            "/api/v1/unified/resources/vm",
            json={**body, "organization_id": str(self.org.id)},
            headers=self.headers,
        )
        self.assertEqual(ambiguous.status_code, 422)
        rollback_name = "Rollback " + uuid.uuid4().hex
        invalid = self.client.post(
            "/api/v1/unified/resources/api",
            json={
                "name": "Rollback API",
                "dns": "api.invalid",
                "environment": "TEST",
                "linked_vm_resource_id": str(self.vm.id),
                "new_customer": {"name": rollback_name, "code": uuid.uuid4().hex[:12]},
            },
            headers=self.headers,
        )
        self.assertEqual(invalid.status_code, 422)
        self.assertIsNone(
            self.db.scalar(
                select(Organization).where(Organization.name == rollback_name)
            )
        )
        # Existing authoritative endpoints still reject a non-platform actor.
        self.user.platform_admin = False
        self.db.commit()
        denied = self.client.post(
            "/api/v1/unified/resources/vm",
            json={
                **body,
                "hostname": uuid.uuid4().hex + ".invalid",
                "new_customer": {
                    "name": "Denied " + uuid.uuid4().hex,
                    "code": uuid.uuid4().hex[:12],
                },
            },
            headers=self.headers,
        )
        self.assertEqual(denied.status_code, 403)


@unittest.skipUnless(
    os.getenv("OPSCONTROL_V16_ACCEPTANCE") == "1",
    "Owned disposable PostgreSQL required",
)
class CanonicalCarteProjection(unittest.TestCase):
    from tests.test_pentaho_execution_r1 import PentahoExecutionTests as _base

    setUp = _base.setUp

    def emit(self, raw):
        from app.data_pipelines import service as service
        from app.data_pipelines.models import PipelineEvidence
        from app.pipeline_adapters.pentaho_observations import normalize_observation
        from app.unified.reconstruction import ingest_connector

        self.counter += 1
        fact = normalize_observation(raw, self.cfg, str(self.org.id))
        fact["evidence_origin"] = "CONTROLLED_FIXTURE"
        ticket = service.acquire(self.db, self.source.id, uuid.uuid4())
        self.db.commit()
        service.accept(
            self.db, ticket, [fact], {"controlled_observation": self.counter}, False
        )
        self.db.commit()
        evidence = self.db.scalar(
            select(PipelineEvidence).where(
                PipelineEvidence.source_id == self.source.id,
                PipelineEvidence.external_key == fact["key"],
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

    surface = "CARTE"
    workload_kind = "TRANSFORMATION"

    def test_native_xml_fenced_source_to_attempt_steps_and_projection(self):
        from app.pipeline_adapters.pentaho_carte import parse_status
        from app.models import JobStepExecution

        body = (NATIVE / "RT-LAB-005B-execution-status.xml").read_bytes()
        raw = parse_status(
            body,
            self.cfg,
            "a5a594c6-8ad7-4b3f-b518-22157f0eba68",
            datetime.now(timezone.utc).isoformat(),
        )
        # Hypothetical preverified source authority is an isolated fixture, not
        # an installed-build certification or a real collector connection.
        event, history = self.emit(raw)
        self.assertIsNotNone(history)
        self.assertEqual(history.source_evidence["native_result"], "Y")
        steps = self.db.scalars(
            select(JobStepExecution).where(JobStepExecution.history_id == history.id)
        ).all()
        self.assertEqual(len(steps), len(raw["native_steps"]))
        before = {s.external_step_id: s.id for s in steps}
        repeated = {
            **raw,
            "observation_id": uuid.uuid4().hex,
            "native_steps": list(reversed(raw["native_steps"])),
        }
        self.emit(repeated)
        steps = self.db.scalars(
            select(JobStepExecution).where(JobStepExecution.history_id == history.id)
        ).all()
        self.assertEqual({s.external_step_id: s.id for s in steps}, before)
        for step in steps:
            original = next(
                r
                for r in raw["native_steps"]
                if r["name"] == step.name
                and r.get("copy") == step.source_evidence["native_copy"]
            )
            self.assertEqual(step.records_read, original["metrics"]["linesRead"])
            self.assertEqual(
                step.source_evidence["native_metrics"], original["metrics"]
            )
        self.assertEqual(
            event.payload["pentaho_identity"]["native_execution_id"],
            "a5a594c6-8ad7-4b3f-b518-22157f0eba68",
        )
        disputed = parse_status(
            body.replace(b"<nr_errors>0</nr_errors>", b"<nr_errors>1</nr_errors>"),
            self.cfg,
            "a5a594c6-8ad7-4b3f-b518-22157f0eba68",
            datetime.now(timezone.utc).isoformat(),
        )
        self.assertEqual(disputed["status"], "UNKNOWN")
        conflict, frozen = self.emit(disputed)
        self.assertEqual(conflict.processing_status, "UNRESOLVED")
        self.assertEqual(frozen.pentaho_review_state, "CONFLICTED_EVIDENCE")
        self.assertEqual(frozen.pentaho_outcome, "SUCCESS")
        self.assertEqual(frozen.source_evidence["nr_errors"], 0)
