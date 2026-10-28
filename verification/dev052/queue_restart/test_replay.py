"""Offline replay safety tests; synthetic receipts here are NOT delivery evidence."""

import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

from replay import LEGACY_SHA, MAX_BYTES, prepare_replay


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.destination = self.root / "input"
        self.destination.mkdir(mode=0o700)
        self.archive = self.root / "archive"
        self.inventory = self.root / "inventory"
        self.receipts = self.root / "receipts"
        self.write(
            self.archive, b'{"event_id":"event-0000"}\n{"event_id":"event-0001"}\n'
        )
        self.write(
            self.inventory,
            {
                "scope": "synthetic",
                "expected_ids": ["event-0000", "event-0001"],
                "sealed_at_ns": 1,
                "expires_at_ns": 100,
            },
        )
        self.write(
            self.receipts,
            {
                "scope": "synthetic",
                "source": "postgresql",
                "writer_stopped": True,
                "cut_ns": 2,
                "counts_by_id": {"event-0000": 1},
            },
        )

    def write(self, path, value):
        path.write_bytes(
            value if isinstance(value, bytes) else json.dumps(value).encode()
        )
        path.chmod(0o600)

    def args(self):
        return [
            self.archive,
            self.inventory,
            self.receipts,
            dict(
                zip(
                    ["archive", "inventory", "receipts"],
                    [
                        hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in [self.archive, self.inventory, self.receipts]
                    ],
                )
            ),
            self.destination,
        ]

    def run_replay(self, **kwargs):
        return prepare_replay(
            *self.args(), scope="synthetic", binary_sha=LEGACY_SHA, now_ns=3, **kwargs
        )

    def test_missing_only_and_idempotent(self):
        first = self.run_replay()
        self.assertEqual(first["missing_ids"], ["event-0001"])
        self.assertTrue(self.run_replay()["idempotent"])
        files = list(self.destination.glob("*.log"))
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].stat().st_mode & 0o777, 0o600)
        self.assertEqual(json.loads(files[0].read_bytes())["event_id"], "event-0001")
        self.assertEqual(
            json.loads(files[0].read_bytes())["_opscontrol_replay_transaction"],
            first["transaction"],
        )

    def test_all_receipted_no_publish(self):
        d = json.loads(self.receipts.read_text())
        d["counts_by_id"]["event-0001"] = 1
        self.write(self.receipts, d)
        self.assertFalse(self.run_replay()["published"])

    def test_retention_expiry(self):
        d = json.loads(self.inventory.read_text())
        d["expires_at_ns"] = 3
        self.write(self.inventory, d)
        with self.assertRaisesRegex(ValueError, "Expired"):
            self.run_replay()

    def test_missing_archive(self):
        args = self.args()
        self.archive.unlink()
        with self.assertRaises(FileNotFoundError):
            prepare_replay(*args, scope="synthetic", binary_sha=LEGACY_SHA, now_ns=3)

    def test_partial_record(self):
        self.write(self.archive, b'{"event_id":"event-0000"}')
        with self.assertRaisesRegex(ValueError, "Partial"):
            self.run_replay()

    def test_incomplete_inventory(self):
        self.write(self.archive, b'{"event_id":"event-0000"}\n')
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            self.run_replay()

    def test_conflicting_record(self):
        self.write(
            self.archive,
            self.archive.read_bytes() + b'{"event_id":"event-0000","other":1}\n',
        )
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.run_replay()

    def test_uninventoried(self):
        self.write(
            self.archive, self.archive.read_bytes() + b'{"event_id":"event-0002"}\n'
        )
        with self.assertRaisesRegex(ValueError, "uninventoried"):
            self.run_replay()

    def test_scope_and_live_writer(self):
        d = json.loads(self.receipts.read_text())
        d["writer_stopped"] = False
        self.write(self.receipts, d)
        with self.assertRaisesRegex(ValueError, "scope mismatch"):
            self.run_replay()
        d["writer_stopped"] = True
        d["scope"] = "other"
        self.write(self.receipts, d)
        with self.assertRaisesRegex(ValueError, "scope mismatch"):
            self.run_replay()

    def test_unsupported_binary(self):
        with self.assertRaisesRegex(ValueError, "Unsupported binary"):
            prepare_replay(
                *self.args(), scope="synthetic", binary_sha="candidate", now_ns=3
            )

    def test_hash_corruption(self):
        args = self.args()
        self.write(self.archive, b"changed\n")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            prepare_replay(*args, scope="synthetic", binary_sha=LEGACY_SHA, now_ns=3)

    def test_symlink_and_hardlink(self):
        args = self.args()
        saved = self.root / "saved"
        self.archive.rename(saved)
        self.archive.symlink_to(saved)
        with self.assertRaises(OSError):
            prepare_replay(*args, scope="synthetic", binary_sha=LEGACY_SHA, now_ns=3)
        self.archive.unlink()
        os.link(saved, self.archive)
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            self.run_replay()

    def test_permissions_and_size(self):
        self.archive.chmod(0o644)
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            self.run_replay()
        self.archive.chmod(0o600)
        with self.archive.open("r+b") as f:
            f.truncate(MAX_BYTES + 1)
        with self.assertRaisesRegex(ValueError, "oversized"):
            self.run_replay()

    def test_partial_pending_refused(self):
        def fail(_):
            raise RuntimeError("injected")

        with self.assertRaises(RuntimeError):
            self.run_replay(fault=fail)
        pending = next(self.destination.glob("*.pending"))
        self.write(pending, b"partial")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            self.run_replay()
        self.assertTrue(pending.exists())
        self.assertFalse(list(self.destination.glob("*.log")))

    def test_sigkill_before_and_after_publish(self):
        for boundary in ["before_publish", "after_publish"]:
            with self.subTest(boundary=boundary):
                for p in self.destination.iterdir():
                    p.unlink()
                args = self.args()
                serial = [str(x) if isinstance(x, Path) else x for x in args]
                code = """import json,os,signal,sys
from replay import prepare_replay,LEGACY_SHA
def fault(stage):
 if stage==sys.argv[2]: os.kill(os.getpid(),signal.SIGKILL)
prepare_replay(*json.loads(sys.argv[1]),scope="synthetic",binary_sha=LEGACY_SHA,now_ns=3,fault=fault)
"""
                result = subprocess.run(
                    [sys.executable, "-c", code, json.dumps(serial), boundary],
                    cwd=Path(__file__).parent,
                )
                self.assertEqual(result.returncode, -signal.SIGKILL)
                self.assertTrue(self.run_replay()["published"])
                self.assertTrue(self.run_replay()["idempotent"])
                self.assertEqual(len(list(self.destination.glob("*.log"))), 1)

    def test_reserved_replay_field_refused(self):
        self.write(
            self.archive,
            b'{"event_id":"event-0000","_opscontrol_replay_transaction":"old"}\n',
        )
        with self.assertRaisesRegex(ValueError, "Reserved"):
            self.run_replay()

    def test_existing_destination_tamper_refused(self):
        self.run_replay()
        self.write(next(self.destination.glob("*.log")), b"tamper")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            self.run_replay()


if __name__ == "__main__":
    unittest.main()
