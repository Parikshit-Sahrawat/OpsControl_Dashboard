import copy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from stage_b_state import locked, save, transition
from stage_b_deploy import check_backup, checked_compose, migration_gate

A = "a" * 40
B = "b" * 40
H = "c" * 64


class StateTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name) / "state"

    def state(self):
        with locked(self.root) as (state, _):
            return copy.deepcopy(state)

    def mutate(self, command, **kw):
        with locked(self.root) as (state, root):
            transition(state, command, **kw)
            save(state, root, {"test": command})

    def test_default_feature_and_main_cannot_overwrite(self):
        self.assertEqual(self.state()["mode"], "FEATURE_UAT")
        self.mutate("record-main", sha=A)
        with self.assertRaisesRegex(ValueError, "MAIN deployment"):
            self.mutate(
                "begin", branch="main", sha=A, request="main-1", migration_hash=H
            )
        self.mutate(
            "begin", branch="feat/sprint", sha=B, request="feature-1", migration_hash=H
        )
        self.mutate("complete", request="feature-1")
        self.assertEqual(self.state()["current"]["sha"], B)
        self.assertEqual(self.state()["pending_main"], A)

    def test_latest_pending_main_and_release(self):
        self.mutate("record-main", sha=A)
        self.mutate("record-main", sha=B)
        self.mutate("release")
        with self.assertRaises(ValueError):
            self.mutate("begin", branch="main", sha=A, request="old")
        self.mutate("begin", branch="main", sha=B, request="new", migration_hash=H)
        self.mutate("complete", request="new")
        self.assertEqual(self.state()["mode"], "MAIN")
        self.assertIsNone(self.state()["pending_main"])

    def test_inflight_lock_and_failure_recovery_gate(self):
        self.mutate("begin", branch="feature/x", sha=A, request="one")
        with self.assertRaises(ValueError):
            self.mutate("begin", branch="feature/y", sha=B, request="two")
        self.mutate("fail", request="one")
        self.assertEqual(self.state()["mode"], "MAINTENANCE")
        with self.assertRaises(ValueError):
            self.mutate("feature-mode")
        self.mutate("recover")
        self.assertEqual(self.state()["mode"], "FEATURE_UAT")

    def test_private_atomic_state_and_bad_identity(self):
        with self.assertRaises(ValueError):
            self.mutate("begin", branch="feat/../../oops", sha=A, request="x")
        self.mutate("record-main", sha=A)
        self.assertEqual((self.root / "state.json").stat().st_mode & 0o077, 0)
        self.assertEqual(len((self.root / "events.jsonl").read_text().splitlines()), 1)

    def test_record_main_keeps_feature_current(self):
        self.mutate("begin", branch="feat/a", sha=A, request="x")
        self.mutate("complete", request="x")
        self.mutate("record-main", sha=B)
        self.assertEqual(self.state()["current"]["sha"], A)
        self.assertEqual(self.state()["pending_main"], B)

    def test_file_lock_serializes_independent_processes(self):
        with locked(self.root):
            process = subprocess.Popen(
                [
                    sys.executable,
                    str(Path(__file__).with_name("stage_b_state.py")),
                    "status",
                    "--state-dir",
                    str(self.root),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            time.sleep(0.1)
            self.assertIsNone(process.poll())
        stdout, stderr = process.communicate(timeout=3)
        self.assertEqual(process.returncode, 0, stderr)
        self.assertEqual(json.loads(stdout)["mode"], "FEATURE_UAT")


class BackupGateTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name) / "backups"
        self.root.mkdir(mode=0o700)
        self.archive = self.root / "uat.dump"
        self.archive.write_bytes(b"archive")
        self.archive.chmod(0o600)
        self.manifest = Path(str(self.archive) + ".json")
        self.data = {
            "format": "postgresql-custom",
            "sha256": hashlib.sha256(b"archive").hexdigest(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    def write(self):
        self.manifest.write_text(json.dumps(self.data))
        self.manifest.chmod(0o600)

    @patch("stage_b_deploy.run", return_value="valid toc")
    def test_verified_backup(self, runner):
        self.write()
        self.assertEqual(check_backup(self.archive, self.root), self.data["sha256"])
        runner.assert_called_once()

    @patch("stage_b_deploy.run", return_value="valid toc")
    def test_stale_or_corrupt_backup_rejected(self, _runner):
        self.data["created_at"] = (
            datetime.now(timezone.utc) - timedelta(days=2)
        ).isoformat()
        self.write()
        with self.assertRaises(ValueError):
            check_backup(self.archive, self.root)
        self.data["created_at"] = datetime.now(timezone.utc).isoformat()
        self.data["sha256"] = "0" * 64
        self.write()
        with self.assertRaises(ValueError):
            check_backup(self.archive, self.root)

    @patch("stage_b_deploy.check_backup", return_value="verified-digest")
    def test_migration_requires_independent_review_and_backup(self, checker):
        with self.assertRaisesRegex(ValueError, "Migration requires"):
            migration_gate(
                None,
                H,
                backup=None,
                backup_root=None,
                review_ref=None,
                approver=None,
                actor="operator",
            )
        with self.assertRaisesRegex(ValueError, "independent"):
            migration_gate(
                None,
                H,
                backup=self.archive,
                backup_root=self.root,
                review_ref="review-1",
                approver="operator",
                actor="operator",
            )
        self.assertEqual(
            migration_gate(
                None,
                H,
                backup=self.archive,
                backup_root=self.root,
                review_ref="review-1",
                approver="reviewer",
                actor="operator",
            ),
            (True, "verified-digest"),
        )
        self.assertEqual(
            migration_gate(
                {"migration_hash": H},
                H,
                backup=None,
                backup_root=None,
                review_ref=None,
                approver=None,
                actor="operator",
            ),
            (False, None),
        )
        checker.assert_called_once()


class ComposeBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.base = Path(self.directory.name) / "uat-owned.yml"
        self.base.write_text("services: {}\n")

    @patch("stage_b_deploy.run")
    def test_requires_existing_database_and_migration_service(self, command):
        command.return_value = json.dumps(
            {"services": {"api": {}, "worker": {}, "frontend": {}, "postgres": {}}}
        )
        with self.assertRaisesRegex(ValueError, "lacks required services"):
            checked_compose(self.base, "opscontrol-feature-uat-test", {})

    @patch("stage_b_deploy.run")
    def test_rejects_new_project_or_build_from_feature_source(self, command):
        services = {
            name: {} for name in ("api", "worker", "frontend", "postgres", "migration")
        }
        services["worker"] = {
            "command": ["python", "-m", "scripts.run_collector_worker"]
        }
        command.side_effect = [
            json.dumps({"services": services}),
            json.dumps({"services": {**services, "api": {"build": "."}}}),
        ]
        with self.assertRaisesRegex(ValueError, "prebuilt immutable"):
            checked_compose(self.base, "opscontrol-feature-uat-test", {})
        with self.assertRaisesRegex(ValueError, "non-UAT"):
            checked_compose(self.base, "demo", {})

    @patch("stage_b_deploy.run")
    def test_requires_running_owned_postgres(self, command):
        services = {
            name: {} for name in ("api", "worker", "frontend", "postgres", "migration")
        }
        services["worker"] = {
            "command": ["python", "-m", "scripts.run_collector_worker"]
        }
        command.side_effect = [
            json.dumps({"services": services}),
            json.dumps({"services": services}),
            "[]",
        ]
        with self.assertRaisesRegex(ValueError, "already be running"):
            checked_compose(self.base, "opscontrol-feature-uat-test", {})


if __name__ == "__main__":
    unittest.main()
