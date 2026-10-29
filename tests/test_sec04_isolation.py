import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "entry", Path(__file__).resolve().parents[1] / "scripts/uat/service_entry.py"
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class IsolationTests(unittest.TestCase):
    def test_untrusted_owner_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(RuntimeError, "Untrusted"):
                m.protected(td)

    def test_root_execution_rejected(self):
        with patch.object(m.os, "geteuid", return_value=0):
            with self.assertRaisesRegex(RuntimeError, "dedicated"):
                m.main()

    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "link"
            p.symlink_to("/etc")
            with self.assertRaisesRegex(RuntimeError, "Untrusted"):
                m.protected(p)
