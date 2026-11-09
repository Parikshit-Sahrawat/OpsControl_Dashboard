"""Actual HTTP transactions, deterministically queued on PostgreSQL row locks."""

import json
import os
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from uuid import uuid4
from sqlalchemy import select, text
from app.db.session import SessionLocal
from app.models import ETLWorkflow, ETLWorkflowDependency, JobOrder
from tests import test_etl_workflow_scope as scope_tests


@unittest.skipUnless(
    os.getenv("OPSCONTROL_ETL_SCOPE_ACCEPTANCE") == "1",
    "Owned PostgreSQL/HTTP required",
)
class WorkflowDAGConcurrency(unittest.TestCase):
    setUp = scope_tests.WorkflowScopeTests.setUp

    def request(self, method, path, payload=None, token=None):
        headers = {
            "Content-Type": "application/json",
            "X-OpsControl-Customers": f"{self.a},{self.b}",
        }
        if token:
            headers["Authorization"] = "Bearer " + token
        request = Request(
            os.environ["ETL_SCOPE_API_URL"] + "/api/v1/" + path,
            headers=headers,
            method=method,
            data=json.dumps(payload).encode() if payload is not None else None,
        )
        try:
            with urlopen(request, timeout=15) as response:
                return response.status, json.load(response)
        except HTTPError as exc:
            return exc.code, json.load(exc)

    def token(self):
        status, body = self.request(
            "POST", "auth/login", {"username": self.username, "password": self.password}
        )
        self.assertEqual(status, 200)
        return body["access_token"]

    def add_job(self, workflow, org):
        with SessionLocal() as db:
            job = JobOrder(
                organization_id=org,
                workflow_id=workflow,
                name="extra-" + uuid4().hex,
                environment="PROD",
            )
            db.add(job)
            db.commit()
            return job.id

    def send(self, token, workflow, edge):
        return self.request(
            "POST",
            f"etl/workflows/{workflow}/dependencies",
            {"predecessor_job_id": str(edge[0]), "successor_job_id": str(edge[1])},
            token,
        )

    def wait_blocked(self, count):
        deadline = time.monotonic() + 3
        with SessionLocal() as db:
            while time.monotonic() < deadline:
                db.execute(text("SELECT pg_stat_clear_snapshot()"))
                rows = db.execute(
                    text(
                        "SELECT pid, wait_event FROM pg_stat_activity WHERE datname=current_database() AND wait_event_type='Lock' AND query ILIKE '%FOR UPDATE%'"
                    )
                ).all()
                if len(rows) >= count:
                    return [{"pid": r.pid, "wait_event": r.wait_event} for r in rows]
                time.sleep(0.02)
        self.fail(f"{count} actual API transactions did not reach the workflow lock")

    def race(self, edges, expected):
        token = self.token()
        with SessionLocal() as gate, ThreadPoolExecutor(max_workers=2) as pool:
            gate.scalar(
                select(ETLWorkflow).where(ETLWorkflow.id == self.wa).with_for_update()
            )
            futures = [pool.submit(self.send, token, self.wa, edge) for edge in edges]
            try:
                blocked = self.wait_blocked(2)
            finally:
                gate.rollback()
            outcomes = [f.result(timeout=15) for f in futures]
        self.assertEqual(sorted(x[0] for x in outcomes), expected)
        with SessionLocal() as db:
            actual = db.execute(
                select(
                    ETLWorkflowDependency.predecessor_job_id,
                    ETLWorkflowDependency.successor_job_id,
                ).where(ETLWorkflowDependency.workflow_id == self.wa)
            ).all()
        graph = {}
        for a, b in actual:
            graph.setdefault(str(a), set()).add(str(b))

        def visit(node, active, done):
            self.assertNotIn(node, active, "Persisted graph contains a cycle")
            if node in done:
                return
            active.add(node)
            for child in graph.get(node, set()):
                visit(child, active, done)
            active.remove(node)
            done.add(node)

        done = set()
        for node in graph:
            visit(node, set(), done)
        Path(
            os.environ["ETL_SCOPE_EVIDENCE_DIR"], self._testMethodName + ".json"
        ).write_text(
            json.dumps(
                {
                    "blocked_postgresql_sessions": blocked,
                    "http_results": [
                        {"status": status, "detail": body.get("detail")}
                        for status, body in outcomes
                    ],
                    "persisted_edges": [[str(a), str(b)] for a, b in actual],
                    "acyclic": True,
                },
                indent=2,
            )
            + "\n"
        )
        return actual, outcomes

    def test_concurrent_opposite_edges_cannot_both_commit(self):
        actual, outcomes = self.race(
            [(self.j1, self.j2), (self.j2, self.j1)], [201, 409]
        )
        self.assertEqual(len(actual), 1)
        self.assertEqual(
            [body["detail"] for status, body in outcomes if status == 409],
            ["Workflow dependency cycle"],
        )

    def test_concurrent_long_cycle_uses_entire_persisted_graph(self):
        j3 = self.add_job(self.wa, self.a)
        j4 = self.add_job(self.wa, self.a)
        with SessionLocal() as db:
            db.add_all(
                [
                    ETLWorkflowDependency(
                        workflow_id=self.wa,
                        predecessor_job_id=self.j1,
                        successor_job_id=self.j2,
                    ),
                    ETLWorkflowDependency(
                        workflow_id=self.wa, predecessor_job_id=j3, successor_job_id=j4
                    ),
                ]
            )
            db.commit()
        actual, _ = self.race([(self.j2, j3), (j4, self.j1)], [201, 409])
        self.assertEqual(len(actual), 3)

    def test_concurrent_nonconflicting_edges_both_commit(self):
        j3 = self.add_job(self.wa, self.a)
        actual, _ = self.race([(self.j1, self.j2), (self.j1, j3)], [201, 201])
        self.assertEqual(len(actual), 2)

    def test_concurrent_duplicate_has_one_commit_and_clean_rollback(self):
        actual, outcomes = self.race(
            [(self.j1, self.j2), (self.j1, self.j2)], [201, 409]
        )
        self.assertEqual(len(actual), 1)
        self.assertEqual(
            [body["detail"] for status, body in outcomes if status == 409],
            ["Dependency already exists"],
        )
        j3 = self.add_job(self.wa, self.a)
        self.assertEqual(self.send(self.token(), self.wa, (self.j2, j3))[0], 201)

    def test_workflow_lock_does_not_serialize_other_workflows(self):
        jb2 = self.add_job(self.wb, self.b)
        token = self.token()
        with SessionLocal() as gate, ThreadPoolExecutor(max_workers=2) as pool:
            gate.scalar(
                select(ETLWorkflow).where(ETLWorkflow.id == self.wa).with_for_update()
            )
            blocked = pool.submit(self.send, token, self.wa, (self.j1, self.j2))
            try:
                self.wait_blocked(1)
                independent = pool.submit(self.send, token, self.wb, (self.jb, jb2))
                self.assertEqual(independent.result(timeout=3)[0], 201)
                self.assertFalse(blocked.done())
            finally:
                gate.rollback()
            self.assertEqual(blocked.result(timeout=15)[0], 201)

    def test_busy_workflow_returns_actionable_error_without_mutation(self):
        token = self.token()
        with SessionLocal() as gate, ThreadPoolExecutor(max_workers=1) as pool:
            gate.scalar(
                select(ETLWorkflow).where(ETLWorkflow.id == self.wa).with_for_update()
            )
            future = pool.submit(self.send, token, self.wa, (self.j1, self.j2))
            try:
                status, body = future.result(timeout=9)
            finally:
                gate.rollback()
        self.assertEqual(status, 409)
        self.assertIn("configuration is busy", body["detail"])
        with SessionLocal() as db:
            self.assertEqual(
                db.scalars(
                    select(ETLWorkflowDependency).where(
                        ETLWorkflowDependency.workflow_id == self.wa
                    )
                ).all(),
                [],
            )
        self.assertEqual(self.send(token, self.wa, (self.j1, self.j2))[0], 201)

    def test_authorization_mutation_excludes_dependency_writes(self):
        token = self.token()
        with SessionLocal() as gate, ThreadPoolExecutor(max_workers=1) as pool:
            gate.execute(text("SELECT pg_advisory_xact_lock(782104, 8)"))
            future = pool.submit(self.send, token, self.wa, (self.j1, self.j2))
            try:
                deadline = time.monotonic() + 3
                observed = False
                with SessionLocal() as monitor:
                    while time.monotonic() < deadline:
                        monitor.execute(text("SELECT pg_stat_clear_snapshot()"))
                        observed = bool(
                            monitor.scalar(
                                text(
                                    "SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND wait_event_type='Lock' AND query LIKE 'SELECT pg_advisory_xact_lock_shared%'"
                                )
                            )
                        )
                        if observed:
                            break
                        time.sleep(0.02)
                    self.assertTrue(
                        observed,
                        "Dependency request must wait for exclusive authorization transaction",
                    )
                    self.assertFalse(future.done())
                    self.assertEqual(
                        monitor.scalars(
                            select(ETLWorkflowDependency).where(
                                ETLWorkflowDependency.workflow_id == self.wa
                            )
                        ).all(),
                        [],
                    )
            finally:
                gate.rollback()
            self.assertEqual(future.result(timeout=15)[0], 201)
