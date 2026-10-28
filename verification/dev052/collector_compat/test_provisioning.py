"""Candidate pin failures must occur before executing any binary or staging source."""

import importlib.util
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "collector_overlay_prepare", Path(__file__).with_name("prepare.py")
)
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


class CandidatePinTests(unittest.TestCase):
    def test_offline_provisioner_rejects_wrong_hash_before_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binary = root / "untrusted"
            binary.write_bytes(b"untrusted executable fixture")
            output = root / "output" / "otelcol-contrib"
            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).with_name("provision.py")),
                    "--output",
                    str(output),
                    "--offline-artifact",
                    str(binary),
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Contrib SHA-256 mismatch", result.stderr)
            self.assertFalse(output.exists())
            self.assertFalse(output.with_suffix(".provenance.json").exists())

    def test_mismatched_binary_is_never_executed_or_staged(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            binary = root / "untrusted"
            binary.write_bytes(b"untrusted binary fixture")
            with patch.object(prepare.subprocess, "check_output") as command:
                with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                    prepare.prepare(root / "stage", binary)
                command.assert_not_called()
            self.assertFalse((root / "stage").exists())
