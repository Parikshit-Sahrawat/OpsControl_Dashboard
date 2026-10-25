import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    "provision", Path(__file__).with_name("provision_contrib.py")
)
provision = importlib.util.module_from_spec(spec)
spec.loader.exec_module(provision)


class ProvisionTests(unittest.TestCase):
    def test_mismatch_is_rejected_before_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "bad"
            artifact.write_bytes(b"untrusted executable")
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                provision.verify(artifact)
