"""Real Session checkpoint transactions around the actual async provider bridge.

SQLite stores only runtime-state/evidence tables here; PostgreSQL migration and
referential-integrity acceptance belong to the dedicated disposable PG harness.
"""

import asyncio
import json
import unittest
from types import SimpleNamespace as S
from uuid import uuid4
from unittest.mock import patch
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from app.registry.models import CollectorRuntimeState
from app.registry.runtime import collect_pipeline
from app.pipeline_adapters import Adapter, AdapterError, Batch
from app.pipeline_adapters.core import execution, step_event

START = "2026-01-01T00:00:00+00:00"
END = "2026-01-01T00:01:00+00:00"


class PipelineRuntimeV15Tests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        self.addCleanup(self.engine.dispose)
        with self.engine.begin() as db:
            db.execute(
                text(
                    "CREATE TABLE collector_runtime_states(collector_id CHAR(32) PRIMARY KEY,organization_id CHAR(32) NOT NULL,checkpoint JSON NOT NULL,revision INTEGER NOT NULL,last_error VARCHAR(80),updated_at TIMESTAMP NOT NULL)"
                )
            )
            db.execute(
                text(
                    "CREATE TABLE acceptance_evidence(id INTEGER PRIMARY KEY,payload TEXT NOT NULL)"
                )
            )
        self.db = Session(self.engine)
        self.addCleanup(self.db.close)
        self.org = uuid4()
        self.collector = S(
            id=uuid4(),
            configuration={
                "platform": "CONTROLLED",
                "jobchain": "resource-job",
                "resource_id": str(uuid4()),
                "integration_configuration": {},
            },
        )
        self.source = S(organization_id=self.org)

    def run_bridge(self, batch, checkpoint=None, adapter_class=None):
        class Controlled(Adapter):
            platform = "CONTROLLED"

            def collect(self, cp):
                if checkpoint is not None:
                    self_case.assertEqual(cp, checkpoint)
                return batch

        self_case = self
        with patch.dict(
            "app.registry.runtime.PLATFORM_ADAPTERS",
            {"CONTROLLED": adapter_class or Controlled},
        ):
            return asyncio.run(collect_pipeline(self.db, self.collector, self.source))

    def fact(self, status="SUCCESS", ended=END):
        return execution("CONTROLLED", "provider-job", "run", status, START, ended)

    def test_cursor_and_evidence_commit_together_and_resume(self):
        batch = Batch(
            [self.fact()], {"origin": "CONTROLLED_PROVIDER_FIXTURE"}, {"offset": 1}
        )
        result = self.run_bridge(batch, checkpoint={})
        self.assertTrue(result.success)
        self.db.execute(
            text("INSERT INTO acceptance_evidence(payload) VALUES(:p)"),
            {"p": json.dumps(result.payload)},
        )
        self.db.commit()
        self.db.expire_all()
        state = self.db.get(CollectorRuntimeState, self.collector.id)
        self.assertEqual(state.checkpoint, {"offset": 1})
        self.assertEqual(state.revision, 1)
        self.assertEqual(
            self.db.scalar(text("SELECT count(*) FROM acceptance_evidence")), 1
        )
        self.run_bridge(
            Batch([self.fact()], checkpoint={"offset": 2}), checkpoint={"offset": 1}
        )
        self.db.commit()
        self.assertEqual(state.revision, 2)

    def test_evidence_failure_rolls_back_cursor_progress(self):
        self.run_bridge(Batch([self.fact()], checkpoint={"offset": 1}))
        self.db.commit()
        result = self.run_bridge(Batch([self.fact()], checkpoint={"offset": 2}))
        self.assertTrue(result.success)
        self.db.flush()
        self.db.rollback()
        self.db.expire_all()
        state = self.db.get(CollectorRuntimeState, self.collector.id)
        self.assertEqual(state.checkpoint, {"offset": 1})
        self.assertEqual(state.revision, 1)
        self.assertEqual(
            self.db.scalar(text("SELECT count(*) FROM acceptance_evidence")), 0
        )

    def test_failed_partial_mutation_does_not_advance_checkpoint(self):
        self.run_bridge(Batch([self.fact()], checkpoint={"nested": {"offset": 1}}))
        self.db.commit()

        class MutatingFailure(Adapter):
            def collect(self, cp):
                cp["nested"]["offset"] = 999
                raise AdapterError("AUTHENTICATION", "Do not expose provider token")

        result = self.run_bridge(None, adapter_class=MutatingFailure)
        self.assertFalse(result.success)
        self.assertNotIn("token", result.message)
        self.db.commit()
        self.db.expire_all()
        state = self.db.get(CollectorRuntimeState, self.collector.id)
        self.assertEqual(state.checkpoint, {"nested": {"offset": 1}})
        self.assertEqual(state.last_error, "AUTHENTICATION")

    def test_scope_mismatch_stops_before_provider_read(self):
        self.db.add(
            CollectorRuntimeState(
                collector_id=self.collector.id,
                organization_id=uuid4(),
                checkpoint={"opaque": "foreign"},
                revision=1,
            )
        )
        self.db.commit()

        class Forbidden(Adapter):
            def collect(self, cp):
                raise AssertionError("Provider must not be called")

        result = self.run_bridge(None, adapter_class=Forbidden)
        self.assertFalse(result.success)
        self.assertEqual(result.payload["outcome"], "CONFIGURATION_ERROR")
        self.assertNotIn("foreign", json.dumps(result.payload))

    def test_step_times_do_not_create_parent_start(self):
        parent = self.fact()
        fact = step_event(
            "CONTROLLED",
            parent,
            {"task_id": "task"},
            "task",
            "Task",
            "SUCCESS",
            START,
            END,
            2,
        )
        result = self.run_bridge(Batch([fact], checkpoint={"step_queue": []}))
        events = [x["event"] for x in result.payload["execution_records"]]
        self.assertEqual([x["event_type"] for x in events], ["STEP_END", "STEP_START"])
        self.assertNotIn("START", [x["event_type"] for x in events])
        begin = events[1]
        self.assertIsNone(begin["ended_at"])
        self.assertFalse(begin["terminal_status_observed"])
        self.assertEqual(begin["step_id"], "task")
        self.assertEqual(begin["attempt"], 2)

    def test_terminal_without_end_preserved_and_no_fabricated_time(self):
        result = self.run_bridge(Batch([self.fact("FAILED", None)], checkpoint={}))
        records = result.payload["execution_records"]
        terminal = records[0]["event"]
        self.assertIsNone(terminal["ended_at"])
        self.assertTrue(terminal["terminal_status_observed"])
        self.assertEqual(records[1]["event"]["event_type"], "START")
        self.assertIsNone(records[1]["event"]["ended_at"])
        self.assertFalse(records[1]["event"]["terminal_status_observed"])

    def test_running_snapshot_uses_received_clock_without_changing_source_start(self):
        result = self.run_bridge(Batch([self.fact("RUNNING", None)], checkpoint={}))
        records = result.payload["execution_records"]
        snapshot = next(r for r in records if r["event"]["event_type"] == "STATUS")
        self.assertTrue(snapshot["event"]["observed_provider_status"])
        self.assertEqual(snapshot["event"]["started_at"], START)
        self.assertNotEqual(snapshot["event"]["timestamp"], START)
        self.assertIsNone(snapshot["event"]["ended_at"])
        self.assertEqual(snapshot["event"]["jobchain"], "resource-job")
        self.assertEqual(snapshot["event"]["provider_jobchain"], "provider-job")

    def test_invalid_payload_checkpoint_never_persists_progress(self):
        for batch in [
            Batch([{"event": {}}], checkpoint={"offset": 2}),
            Batch([self.fact()], checkpoint={"cursor": "x" * 65537}),
        ]:
            with self.subTest(batch_size=len(batch.events)):
                result = self.run_bridge(batch)
                self.assertFalse(result.success)
                self.assertIsNone(self.db.get(CollectorRuntimeState, self.collector.id))

    def test_retry_reads_keep_original_checkpoint_then_persist_success(self):
        calls = []

        class Retry(Adapter):
            def collect(self, cp):
                calls.append(dict(cp))
                if len(calls) < 2:
                    raise AdapterError("THROTTLED", "Rate limited")
                return Batch(
                    [execution("CONTROLLED", "j", "r", "SUCCESS", START, END)],
                    checkpoint={"offset": 1},
                )

            def collect_with_retry(self, cp):
                return super().collect_with_retry(cp, sleep=lambda delay: None)

        result = self.run_bridge(None, adapter_class=Retry)
        self.assertTrue(result.success)
        self.assertEqual(calls, [{}, {}])
        self.db.commit()
        self.assertEqual(
            self.db.get(CollectorRuntimeState, self.collector.id).checkpoint,
            {"offset": 1},
        )

    def test_provider_raw_evidence_is_recursively_secret_redacted(self):
        from app.pipeline_adapters.http import IICS

        record = {
            "runId": "r",
            "taskName": "task",
            "state": 1,
            "startTime": START,
            "endTime": END,
            "parameters": {
                "password": "never-store-this",
                "access_token": "never-store-token",
                "nested": ['{"api_key":"never-store-key"}'],
            },
        }
        adapter = IICS({"base_url": "https://provider.test", "task_id": "task"})
        batch = adapter.batch([record], {})
        result = self.run_bridge(batch)
        payload = json.dumps(result.payload)
        self.assertNotIn("never-store", payload)
        self.assertIn("[REDACTED]", payload)
