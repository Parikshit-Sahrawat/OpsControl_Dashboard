"""Private subprocess failures must remain reviewable without leaking credentials."""

import json
import tempfile
import unittest
from pathlib import Path

from scripts.acceptance_diagnostics import export_logs


class AcceptanceDiagnosticsTests(unittest.TestCase):
    def test_failure_assertion_survives_with_secrets_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            private = Path(directory) / "private"
            private.mkdir()
            output = Path(directory) / "export"
            (private / "fixture.json").write_text(
                json.dumps(
                    {
                        "password": "fixture-password",
                        "nested": {"access_token": "fixture-token"},
                    }
                )
            )
            (private / "failure.log").write_text(
                "AssertionError: invalid field\nfixture-password fixture-token db-password env-secret Bearer opaque-token eyJabc.def.ghi"
            )
            exported = export_logs(
                private, output, {"APP_SECRET": "env-secret"}, ["db-password"]
            )
            self.assertEqual(exported, ["failure.log"])
            text = (output / "failure.log").read_text()
            self.assertIn("AssertionError: invalid field", text)
            for secret in (
                "fixture-password",
                "fixture-token",
                "db-password",
                "env-secret",
                "opaque-token",
                "eyJabc.def.ghi",
            ):
                self.assertNotIn(secret, text)

    def test_dump_keys_and_fixture_are_never_exported(self):
        with tempfile.TemporaryDirectory() as directory:
            private = Path(directory) / "private"
            private.mkdir()
            output = Path(directory) / "export"
            for name in ("database.dump", "key.pem", "session.json"):
                (private / name).write_text("private")
            self.assertEqual(export_logs(private, output, {}), [])
            self.assertEqual(list(output.iterdir()), [])
