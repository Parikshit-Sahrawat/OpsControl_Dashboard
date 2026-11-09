"""Command contract; actual BuildKit proof is recorded separately."""

import json
import tempfile
import unittest
from pathlib import Path

from scripts.ci.compose_build import build_with_trust


class ComposeBuildTests(unittest.TestCase):
    def test_exact_validated_file_entitlement_and_compose_plan(self):
        calls = []
        plan = {
            "target": {"api": {"tags": ["owned-api"]}},
            "group": {"default": {"targets": ["api"]}},
        }

        def run(command):
            calls.append(command)
            return json.dumps(plan) if command[-1] == "--print" else "built"

        with tempfile.TemporaryDirectory() as private:
            ca = Path("/etc/ssl/certs/ca-certificates.crt").resolve()
            self.assertEqual(
                build_with_trust(
                    ["docker", "compose", "-p", "owned"], ca, private, run
                ),
                "built",
            )
            self.assertEqual(
                calls[0], ["docker", "compose", "-p", "owned", "build", "--print"]
            )
            self.assertEqual(calls[1][-2:], ["--allow=fs.read=" + str(ca), "--load"])
            self.assertEqual(
                json.loads((Path(private) / "compose-bake.json").read_text()), plan
            )
            self.assertEqual(
                (Path(private) / "compose-bake.json").stat().st_mode & 0o777, 0o600
            )

    def test_invalid_or_missing_ca_fails_before_build(self):
        with tempfile.TemporaryDirectory() as private:
            ca = Path(private) / "invalid-ca"
            ca.write_text("not a certificate")
            for path in (ca, Path(private) / "missing"):
                with self.assertRaises((ValueError, OSError)):
                    build_with_trust(
                        [], path, private, lambda _: self.fail("must not build")
                    )

    def test_empty_compose_plan_fails_closed(self):
        with tempfile.TemporaryDirectory() as private:
            with self.assertRaisesRegex(ValueError, "no build targets"):
                build_with_trust(
                    [], "/etc/ssl/certs/ca-certificates.crt", private, lambda _: "{}"
                )
