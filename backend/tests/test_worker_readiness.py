import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from app.worker import collector_runtime as runtime


class WorkerReadinessTests(unittest.TestCase):
    def test_database_success_writes_heartbeat(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "heartbeat"
            with patch.dict(
                os.environ, {"OPSCONTROL_WORKER_HEARTBEAT": str(path)}
            ), patch.object(runtime, "engine") as engine:
                runtime._write_worker_heartbeat()
            self.assertGreater(float(path.read_text()), 0)
            engine.connect.return_value.__enter__.return_value.execute.assert_called_once()

    def test_database_failure_does_not_refresh_heartbeat(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "heartbeat"
            path.write_text("1")
            with patch.dict(
                os.environ, {"OPSCONTROL_WORKER_HEARTBEAT": str(path)}
            ), patch.object(
                runtime.engine, "connect", side_effect=RuntimeError("unavailable")
            ):
                with self.assertRaises(RuntimeError):
                    runtime._write_worker_heartbeat()
            self.assertEqual(path.read_text(), "1")

    def test_disabled_heartbeat_does_not_open_database(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(
            runtime, "engine"
        ) as engine:
            runtime._write_worker_heartbeat()
        engine.connect.assert_not_called()
