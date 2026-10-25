import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import recovery as r


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.state = self.root / "state"
        self.state.mkdir(mode=0o700)
        self.vault = self.root / "vault"
        self.vault.mkdir(mode=0o700)
        self.logs = self.root / "logs"
        self.logs.mkdir(mode=0o700)
        for name in ["filelog", "queue"]:
            r.atomic(self.state / name, ("legacy-" + name).encode())
        self.config = self.root / "config.yaml"
        r.atomic(self.config, b"fixed config")
        self.backup = self.vault / "backup"
        r.snapshot(self.state, self.backup, self.config)
        self.expected = ["event-1", "event-2"]
        r.atomic(
            self.logs / "source.log",
            b'{"event_id":"event-1"}\n{"event_id":"event-2"}\n',
        )
        self.archive = self.vault / "archive"
        r.seal_archive([self.logs / "source.log"], self.expected, self.archive)
        for name in ["filelog", "queue"]:
            r.atomic(self.state / name, ("candidate-protobuf-" + name).encode())
        self.failed_state = r.tree(self.state)

    def recover(self, fault=None):
        return r.recover(
            self.state,
            self.backup,
            self.archive,
            self.config,
            self.vault,
            self.logs,
            "job-1",
            fault,
        )

    def test_replay_collision_refused_before_state_mutation(self):
        r.atomic(self.logs / "recovery-job-1.log", b"unrelated retained input")
        with self.assertRaisesRegex(ValueError, "collision"):
            self.recover()
        self.assertEqual(r.tree(self.state), self.failed_state)
        self.assertFalse((self.vault / "job-1.json").exists())

    def test_empty_partial_staging_resumes(self):
        (self.root / ".state.exchange-job-1").mkdir(mode=0o700)
        result = self.recover()
        self.assertEqual(result["phase"], "COMPLETED")
        self.assertEqual(r.tree(Path(result["preserved_candidate"])), self.failed_state)

    def test_empty_independent_inventory_refused(self):
        with self.assertRaisesRegex(ValueError, "Nonempty"):
            r.seal_archive([], [], self.vault / "empty-archive")

    def test_backup_cut_cannot_be_overwritten(self):
        digest = r.sha(self.backup / "manifest.json")
        with self.assertRaisesRegex(ValueError, "already exists"):
            r.snapshot(self.state, self.backup, self.config)
        self.assertEqual(r.sha(self.backup / "manifest.json"), digest)

    def test_conflicting_stable_ids_refused(self):
        r.atomic(
            self.logs / "conflict.log",
            b'{"event_id":"event-1","payload":"conflicting"}\n',
        )
        with self.assertRaisesRegex(ValueError, "Conflicting"):
            r.seal_archive(
                list(self.logs.glob("*.log")), self.expected, self.vault / "conflict"
            )

    def test_pending_restore_has_no_partial_replay_file(self):
        with self.assertRaisesRegex(RuntimeError, "before-replay"):
            self.recover("before-replay")
        self.assertFalse((self.logs / "recovery-job-1.log").exists())
        with self.assertRaisesRegex(ValueError, "Pending"):
            r.assert_startable(self.vault)
        self.assertEqual(self.recover()["phase"], "COMPLETED")

    def test_atomic_restore_preserves_failed_tree_and_idempotence(self):
        record = self.recover()
        self.assertEqual(r.tree(Path(record["preserved_candidate"])), self.failed_state)
        self.assertEqual(
            r.tree(self.state), r.verify_backup(self.backup, self.config)["files"]
        )
        self.assertTrue(self.recover()["idempotent_noop"])
        r.assert_startable(self.vault)
        self.assertEqual(
            (self.logs / "recovery-job-1.log").stat().st_mode & 0o777, 0o600
        )

    def test_partial_staging_never_changes_live_state(self):
        with self.assertRaisesRegex(RuntimeError, "partial-copy"):
            self.recover("partial-copy")
        self.assertEqual(r.tree(self.state), self.failed_state)
        with self.assertRaisesRegex(ValueError, "Pending"):
            r.assert_startable(self.vault)
        self.assertEqual(self.recover()["phase"], "COMPLETED")
        self.assertTrue(list(self.root.glob(".state.exchange-job-1.incomplete-*")))

    def test_each_durable_boundary_resumes_without_reexchange(self):
        for fault in ["before-exchange", "after-exchange", "before-replay"]:
            with self.subTest(fault=fault):
                # Separate fresh fixture per boundary.
                case = RecoveryTests()
                case.setUp()
                try:
                    with self.assertRaises(RuntimeError):
                        case.recover(fault)
                    result = case.recover()
                    self.assertEqual(
                        r.tree(Path(result["preserved_candidate"])), case.failed_state
                    )
                finally:
                    case.doCleanups()

    def test_actual_process_death_after_exchange_resumes(self):
        command = [
            sys.executable,
            str(Path(r.__file__)),
            "recover",
            "--state",
            str(self.state),
            "--backup",
            str(self.backup),
            "--archive",
            str(self.archive),
            "--config",
            str(self.config),
            "--vault",
            str(self.vault),
            "--replay-root",
            str(self.logs),
            "--transaction",
            "job-1",
            "--inject-failure",
            "kill-after-exchange",
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 86)
        self.assertEqual(self.recover()["phase"], "COMPLETED")

    def test_corrupt_backup_and_config_are_refused(self):
        r.atomic(self.backup / "state/filelog", b"corrupt")
        with self.assertRaisesRegex(ValueError, "integrity"):
            self.recover()
        self.assertEqual(r.tree(self.state), self.failed_state)

    def test_changed_config_refused(self):
        r.atomic(self.config, b"another configuration")
        with self.assertRaisesRegex(ValueError, "integrity"):
            self.recover()

    def test_incomplete_archive_is_blocked(self):
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            r.seal_archive(
                [self.logs / "source.log"],
                self.expected + ["lost-event"],
                self.vault / "missing",
            )

    def test_tampered_archive_is_blocked(self):
        r.atomic(self.archive / "records.jsonl", b"bad archive")
        with self.assertRaisesRegex(ValueError, "integrity"):
            self.recover()

    def test_active_writer_lock_is_refused(self):
        with (self.state / "filelog").open("r+b") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(ValueError, "writer active"):
                self.recover()

    def test_links_permissions_and_post_completion_rewind_refused(self):
        os.chmod(self.state / "filelog", 0o644)
        with self.assertRaises(ValueError):
            self.recover()
        os.chmod(self.state / "filelog", 0o600)
        (self.state / "link").symlink_to(self.state / "queue")
        with self.assertRaises(ValueError):
            self.recover()
        (self.state / "link").unlink()
        self.recover()
        r.atomic(self.state / "filelog", b"collector advanced")
        with self.assertRaisesRegex(ValueError, "advanced"):
            self.recover()
