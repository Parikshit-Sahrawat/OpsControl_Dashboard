"""Agent lifecycle tests use real private files; no production telemetry claims."""

import hashlib
import importlib.util
import json
import sys
import threading
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))
from opscontrol_agent import Agent, FILELOG_HANDOFF_MARKER, filelog_runtime_flags
from app.telemetry.api import credential_matches, utc, verify_reception


class AgentLifecycleTests(unittest.TestCase):
    def bare_agent(self, directory):
        agent = Agent.__new__(Agent)
        agent.home = Path(directory)
        agent.config = agent.home / "otel.yaml"
        agent.state = agent.home / "state.json"
        agent.runtime = "/approved/otelcol-contrib"
        agent.token = "test-only-not-a-live-token"
        agent.applied = 1
        agent.agent_configuration = {"services": []}
        agent.process = Mock()
        agent.process.poll.return_value = None
        return agent

    def version(self, text="service: {pipelines: {}}\n"):
        return {
            "runtime_version": "0.123.0",
            "revision": 2,
            "yaml_text": text,
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
            "method_snapshot": [],
            "agent_configuration": {"services": []},
        }

    def test_private_write_and_checkpoint_survives_apply(self):
        with tempfile.TemporaryDirectory() as directory:
            agent = self.bare_agent(directory)
            checkpoint = agent.home / "otel-checkpoints"
            checkpoint.mkdir()
            (checkpoint / "cursor").write_text("offset:123")
            with patch.object(agent, "stop_runtime"), patch.object(
                agent, "start_runtime"
            ), patch(
                "opscontrol_agent.subprocess.run",
                return_value=SimpleNamespace(returncode=0),
            ):
                agent.apply(self.version())
            self.assertEqual((checkpoint / "cursor").read_text(), "offset:123")
            self.assertEqual(json.loads(agent.state.read_text())["applied_revision"], 2)
            self.assertEqual(agent.state.stat().st_mode & 0o777, 0o600)

    def test_invalid_configuration_never_stops_working_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            agent = self.bare_agent(directory)
            agent.config.write_text("working")
            with patch.object(agent, "stop_runtime") as stop, patch(
                "opscontrol_agent.subprocess.run",
                return_value=SimpleNamespace(returncode=1),
            ):
                with self.assertRaisesRegex(RuntimeError, "COLLECTOR_CONFIG_INVALID"):
                    agent.apply(self.version())
                stop.assert_not_called()
            self.assertEqual(agent.config.read_text(), "working")

    def test_failed_runtime_start_restores_previous_yaml(self):
        with tempfile.TemporaryDirectory() as directory:
            agent = self.bare_agent(directory)
            agent.config.write_text("working")
            agent.process.poll.return_value = 1
            with patch.object(agent, "stop_runtime"), patch.object(
                agent, "start_runtime"
            ) as start, patch(
                "opscontrol_agent.subprocess.run",
                return_value=SimpleNamespace(returncode=0),
            ):
                with self.assertRaisesRegex(RuntimeError, "COLLECTOR_START_FAILED"):
                    agent.apply(self.version())
                self.assertEqual(start.call_count, 2)
            self.assertEqual(agent.config.read_text(), "working")
            self.assertEqual(agent.applied, 1)

    def test_runtime_launch_exception_restores_previous_yaml(self):
        with tempfile.TemporaryDirectory() as directory:
            agent = self.bare_agent(directory)
            agent.config.write_text("working")
            with patch.object(agent, "stop_runtime"), patch.object(
                agent,
                "start_runtime",
                side_effect=[OSError("launch failed"), None, None],
            ) as start, patch(
                "opscontrol_agent.subprocess.run",
                return_value=SimpleNamespace(returncode=0),
            ):
                with self.assertRaisesRegex(RuntimeError, "COLLECTOR_START_FAILED"):
                    agent.apply(self.version())
                self.assertEqual(start.call_count, 2)
                self.assertEqual(agent.config.read_text(), "working")
                self.assertEqual(agent.applied, 1)
                agent.apply(self.version())
                self.assertEqual(agent.applied, 2)
                self.assertEqual(
                    json.loads(agent.state.read_text())["applied_revision"], 2
                )

    def test_first_runtime_launch_exception_leaves_no_unapproved_config(self):
        with tempfile.TemporaryDirectory() as directory:
            agent = self.bare_agent(directory)
            agent.applied = None
            with patch.object(agent, "stop_runtime"), patch.object(
                agent, "start_runtime", side_effect=OSError("launch failed")
            ) as start, patch(
                "opscontrol_agent.subprocess.run",
                return_value=SimpleNamespace(returncode=0),
            ):
                with self.assertRaisesRegex(RuntimeError, "COLLECTOR_START_FAILED"):
                    agent.apply(self.version())
            start.assert_called_once()
            self.assertFalse(agent.config.exists())
            self.assertFalse(agent.state.exists())

    def test_missing_or_private_log_path_is_not_healthy(self):
        with tempfile.TemporaryDirectory() as directory:
            agent = self.bare_agent(directory)
            version = self.version()
            version["method_snapshot"] = [
                {
                    "enabled": True,
                    "method_type": "FILE_LOG",
                    "configuration": {
                        "source": "FILE",
                        "paths": [str(agent.home / "missing.log")],
                    },
                }
            ]
            with self.assertRaisesRegex(RuntimeError, "LOG_PATH_NOT_FOUND"):
                agent.preflight(version)
            (agent.home / "identity.json").write_text("private")
            version["method_snapshot"][0]["configuration"]["paths"] = [
                str(agent.home / "identity.json")
            ]
            with self.assertRaisesRegex(RuntimeError, "AGENT_PRIVATE_PATH_DENIED"):
                agent.preflight(version)

    def test_offline_restart_rejects_modified_local_yaml(self):
        with tempfile.TemporaryDirectory() as directory:
            agent = self.bare_agent(directory)
            agent.checksum = hashlib.sha256(b"approved").hexdigest()
            agent.config.write_text("modified")
            with patch.object(agent, "enroll"), patch.object(
                agent, "start_runtime"
            ) as start:
                with self.assertRaisesRegex(RuntimeError, "CONFIG_CHECKSUM_MISMATCH"):
                    agent.run("unused-enrollment")
                start.assert_not_called()

    def test_offline_restart_uses_validated_private_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            agent = self.bare_agent(directory)
            agent.config.write_text("approved")
            agent.checksum = hashlib.sha256(b"approved").hexdigest()
            agent.stop = threading.Event()
            agent.stop.set()
            with patch.object(agent, "enroll"), patch.object(
                agent, "start_runtime"
            ) as start, patch.object(agent, "stop_runtime"), patch(
                "opscontrol_agent.subprocess.run",
                return_value=SimpleNamespace(returncode=0),
            ) as validate:
                agent.run("unused-enrollment")
                start.assert_called_once()
                self.assertIn("validate", validate.call_args.args[0])

    def test_rotation_grace_expires(self):
        worker = SimpleNamespace(token_hash="new")
        agent = SimpleNamespace(
            previous_token_hash="old",
            previous_token_expires_at=utc() + timedelta(seconds=10),
        )
        self.assertTrue(credential_matches(agent, worker, "old"))
        agent.previous_token_expires_at = utc() - timedelta(seconds=1)
        self.assertFalse(credential_matches(agent, worker, "old"))
        self.assertTrue(credential_matches(agent, worker, "new"))

    def test_handoff_flag_follows_actual_config_for_validate_start_and_rollback(self):
        from app.telemetry.configuration import FILELOG_HANDOFF_MARKER as server_marker

        self.assertEqual(FILELOG_HANDOFF_MARKER, server_marker)
        with tempfile.TemporaryDirectory() as directory:
            agent = self.bare_agent(directory)
            agent.config.write_text("previous config\n")
            with patch.object(agent, "stop_runtime"), patch(
                "opscontrol_agent.subprocess.run",
                return_value=SimpleNamespace(returncode=0),
            ) as validate, patch("opscontrol_agent.subprocess.Popen") as launch, patch(
                "opscontrol_agent.time.sleep"
            ):
                launch.return_value.poll.return_value = None
                agent.apply(self.version(FILELOG_HANDOFF_MARKER + "service: {}\n"))
                flag = "--feature-gates=stanza.synchronousLogEmitter"
                self.assertIn(flag, validate.call_args.args[0])
                self.assertIn(flag, launch.call_args.args[0])
                agent.config.write_text("previous config\n")
                agent.start_runtime()
                self.assertNotIn(flag, launch.call_args.args[0])
                agent.config.write_text(
                    FILELOG_HANDOFF_MARKER.replace(
                        "stanza.synchronousLogEmitter", "arbitrary.gate"
                    )
                )
                self.assertEqual(filelog_runtime_flags(agent.config), [])

    def test_offline_handoff_restart_uses_same_checked_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            agent = self.bare_agent(directory)
            text = FILELOG_HANDOFF_MARKER + "service: {}\n"
            agent.config.write_text(text)
            agent.checksum = hashlib.sha256(text.encode()).hexdigest()
            agent.stop = threading.Event()
            agent.stop.set()
            with patch.object(agent, "enroll"), patch.object(
                agent, "stop_runtime"
            ), patch(
                "opscontrol_agent.subprocess.run",
                return_value=SimpleNamespace(returncode=0),
            ) as validate, patch(
                "opscontrol_agent.subprocess.Popen"
            ) as launch, patch(
                "opscontrol_agent.time.sleep"
            ):
                agent.run("unused-enrollment")
                flag = "--feature-gates=stanza.synchronousLogEmitter"
                self.assertIn(flag, validate.call_args.args[0])
                self.assertIn(flag, launch.call_args.args[0])

    def test_applied_is_not_verified_without_all_receipts(self):
        agent = SimpleNamespace(
            id="agent",
            organization_id="test-organization",
            applied_at=utc(),
            configuration_sha256="checksum",
            verified_revision=None,
        )
        version = SimpleNamespace(
            yaml_text="service: {pipelines: {logs: {}, metrics: {}}}",
            sha256="checksum",
            revision=2,
            agent_configuration={},
        )
        db = Mock()
        db.scalars.return_value.all.return_value = ["metrics"]
        self.assertFalse(verify_reception(db, agent, version))
        self.assertIsNone(agent.verified_revision)
        db.scalars.return_value.all.return_value = ["metrics", "logs"]
        db.scalars.return_value.__iter__ = lambda _: iter([])
        self.assertTrue(verify_reception(db, agent, version))
        self.assertEqual(agent.last_working_revision, 2)


if __name__ == "__main__":
    unittest.main()
