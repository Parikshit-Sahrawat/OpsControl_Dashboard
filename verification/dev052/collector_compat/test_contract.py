"""Security regressions for the explicitly staged experimental contract only."""

import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "agent"))
from opscontrol_agent import Agent
from app.telemetry.configuration import RUNTIME_VERSION, validate_binary


class ExactExperimentalContractTests(unittest.TestCase):
    def test_backend_rejects_neighbor_prerelease_and_old_versions(self):
        self.assertEqual(RUNTIME_VERSION, "0.163.2")
        for version in [
            "0.163.20",
            "0.163.2-rc1",
            "0.163.2+custom",
            "0.164.0",
            "0.123.0",
        ]:
            with self.subTest(version=version), patch(
                "app.telemetry.configuration.subprocess.run",
                return_value=SimpleNamespace(
                    returncode=0, stdout="otelcol-contrib version " + version
                ),
            ) as command:
                with self.assertRaisesRegex(ValueError, "does not match"):
                    validate_binary("service: {}", "/controlled/version-stub")
                self.assertEqual(command.call_count, 1)

    def test_supervisor_rejects_neighbor_prerelease_and_old_versions(self):
        for version in [
            "0.163.20",
            "0.163.2-rc1",
            "0.163.2+custom",
            "0.164.0",
            "0.123.0",
        ]:
            with self.subTest(
                version=version
            ), tempfile.TemporaryDirectory() as home, patch(
                "opscontrol_agent.subprocess.run",
                return_value=SimpleNamespace(
                    returncode=0, stdout="otelcol-contrib version " + version
                ),
            ):
                with self.assertRaisesRegex(RuntimeError, "version mismatch"):
                    Agent(
                        home, "https://owned.example.test", "/controlled/version-stub"
                    )
