"""Explicit re-enrollment preserves identity/checkpoints and protected backups."""

import json, tempfile, threading, unittest
from pathlib import Path
from unittest.mock import Mock
from uuid import uuid4
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "agent"))
from opscontrol_agent import Agent


class ReenrollmentTests(unittest.TestCase):
    def make(self, root):
        agent = Agent.__new__(Agent)
        agent.home = Path(root)
        agent.credentials = agent.home / "identity.json"
        agent.token = "controlled-old-token"
        self.id = str(uuid4())
        self.original = {"agent_id": self.id, "access_token": agent.token}
        agent.credentials.write_text(json.dumps(self.original))
        agent.credentials.chmod(0o600)
        agent.request = Mock(
            return_value={"agent_id": self.id, "access_token": "controlled-new-token"}
        )
        file = agent.home / "enrollment"
        file.write_text("controlled-one-use")
        file.chmod(0o600)
        (agent.home / "checkpoint").write_text("preserve-offset")
        return agent, file

    def test_same_identity_force_keeps_checkpoint_and_private_backup(self):
        with tempfile.TemporaryDirectory() as root:
            agent, file = self.make(root)
            agent.enroll(file, force=True)
            self.assertEqual(
                json.loads(agent.credentials.read_text())["agent_id"], self.id
            )
            self.assertEqual((agent.home / "checkpoint").read_text(), "preserve-offset")
            backups = list(agent.home.glob("identity.before-reenrollment.*.json"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(json.loads(backups[0].read_text()), self.original)
            self.assertEqual(backups[0].stat().st_mode & 0o777, 0o600)
            self.assertFalse(file.exists())

    def test_normal_restart_does_not_consume_new_enrollment(self):
        with tempfile.TemporaryDirectory() as root:
            agent, file = self.make(root)
            agent.enroll(file)
            agent.request.assert_not_called()
            self.assertTrue(file.exists())

    def test_different_resource_never_overwrites_existing_identity(self):
        with tempfile.TemporaryDirectory() as root:
            agent, file = self.make(root)
            agent.request.return_value["agent_id"] = str(uuid4())
            with self.assertRaisesRegex(RuntimeError, "RESOURCE_MISMATCH"):
                agent.enroll(file, force=True)
            self.assertEqual(json.loads(agent.credentials.read_text()), self.original)
            self.assertTrue(file.exists())
            self.assertEqual((agent.home / "checkpoint").read_text(), "preserve-offset")
