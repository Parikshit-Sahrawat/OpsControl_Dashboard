"""Quiet readable sources never fabricate incoming telemetry or bypass freshness."""

import unittest
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace as Row
from uuid import uuid4
from app.unified.engines import readable_idle_file


class QuietReadinessTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.id = str(uuid4())
        self.method = {
            "id": self.id,
            "method_type": "FILE_LOG",
            "configuration": {"source": "FILE"},
        }
        self.config = Row(revision=2, sha256="f" * 64)
        self.observation = {
            "observed_at": self.now.isoformat(),
            "applied_revision": 2,
            "state": "IDLE",
            "sources_found": 2,
            "sources_readable": 2,
            "error_code": None,
        }
        self.agent = Row(
            configuration_sha256=self.config.sha256,
            method_health={self.id: self.observation},
        )

    def test_quiet_readable_files_are_idle_availability_only(self):
        self.assertTrue(
            readable_idle_file(self.method, self.agent, self.config, self.now)
        )
        self.assertNotIn("last_received_at", self.observation)

    def test_wrong_revision_or_checksum_does_not_activate(self):
        self.observation["applied_revision"] = 1
        self.assertFalse(
            readable_idle_file(self.method, self.agent, self.config, self.now)
        )
        self.observation["applied_revision"] = 2
        self.agent.configuration_sha256 = "e" * 64
        self.assertFalse(
            readable_idle_file(self.method, self.agent, self.config, self.now)
        )

    def test_no_file_permission_error_or_partial_reads_are_not_ready(self):
        for change in (
            {"sources_found": 0, "sources_readable": 0},
            {"sources_readable": 1},
            {"state": "ERROR"},
            {"error_code": "PATH_PERMISSION"},
        ):
            original = dict(self.observation)
            self.observation.update(change)
            self.assertFalse(
                readable_idle_file(self.method, self.agent, self.config, self.now)
            )
            self.observation.clear()
            self.observation.update(original)

    def test_future_stale_and_unaware_observations_rejected(self):
        for timestamp in (
            (self.now + timedelta(seconds=1)).isoformat(),
            (self.now - timedelta(seconds=91)).isoformat(),
            self.now.replace(tzinfo=None).isoformat(),
            "invalid",
        ):
            self.observation["observed_at"] = timestamp
            self.assertFalse(
                readable_idle_file(self.method, self.agent, self.config, self.now)
            )

    def test_non_file_sources_need_independent_reception(self):
        self.method["configuration"]["source"] = "JOURNALD"
        self.assertFalse(
            readable_idle_file(self.method, self.agent, self.config, self.now)
        )
        self.method["method_type"] = "SYSLOG_RECEIVER"
        self.assertFalse(
            readable_idle_file(self.method, self.agent, self.config, self.now)
        )
