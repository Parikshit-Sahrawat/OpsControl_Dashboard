import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    "bootstrap", Path(__file__).resolve().parents[1] / "bootstrap_pip.py"
)
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


class BootstrapTests(unittest.TestCase):
    def test_bad_wheel_is_rejected_before_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "bad.whl"
            p.write_bytes(b"untrusted")
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                bootstrap.verify(p, "0" * 64)
