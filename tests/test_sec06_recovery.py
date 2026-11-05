import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
from test_local_auto_deploy import m, B, F


class RecoveryTests(unittest.TestCase):
    def exercise(self, outcomes):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td)
            base = state / "compose.yml"
            base.write_text("services: {}")
            previous = {"sha": "b" * 40, "backend_image": B, "frontend_image": F}
            m.atomic(state / "last-deployment.json", previous)
            env = {
                "LOCAL_UAT_STATE_DIR": td,
                "LOCAL_UAT_PULL_ENABLED": "true",
                "LOCAL_UAT_BASE_COMPOSE": str(base),
                "LOCAL_UAT_OVERRIDE_COMPOSE": str(base),
                "LOCAL_UAT_PROJECT": "disposable",
                "LOCAL_UAT_API_URL": "http://localhost",
                "LOCAL_UAT_FRONTEND_URL": "http://localhost",
            }
            handoff = types.SimpleNamespace(
                read_fd=lambda state: {
                    "sha": "a" * 40,
                    "images": {"backend": B, "frontend": F},
                }
            )
            with patch.dict(os.environ, env, clear=True), patch.dict(
                sys.modules, {"release_handoff": handoff}
            ), patch.object(m, "deploy_images", side_effect=outcomes) as deploy:
                try:
                    m.main()
                except RuntimeError:
                    pass
            return (
                json.loads((state / "last-deployment.json").read_text()),
                json.loads((state / "deploy-audit.jsonl").read_text()),
                deploy.call_count,
            )

    def test_failure_rolls_back_and_preserves_baseline(self):
        last, audit, calls = self.exercise([RuntimeError("bad worker"), None])
        self.assertEqual(last["sha"], "b" * 40)
        self.assertEqual(audit["rollback"], "PASS")
        self.assertEqual(calls, 2)

    def test_failed_rollback_preserves_baseline(self):
        last, audit, calls = self.exercise(
            [RuntimeError("bad"), RuntimeError("bad rollback")]
        )
        self.assertEqual(last["sha"], "b" * 40)
        self.assertEqual(audit["rollback"], "FAIL")
        self.assertEqual(calls, 2)

    def test_recovery_records_new_baseline(self):
        last, audit, calls = self.exercise([None])
        self.assertEqual(last["sha"], "a" * 40)
        self.assertEqual(audit["outcome"], "DEPLOYED")
        self.assertEqual(calls, 1)
