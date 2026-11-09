import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest


class EvidenceIntegrityTests(unittest.TestCase):
    def test_tampering_and_traversal_cannot_pass_evidence_gate(self):
        path = Path(__file__).resolve().parents[1] / "docs/verification/sprint1-integration/validate_evidence.py"
        spec = importlib.util.spec_from_file_location("sprint1_evidence", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            (root / "result.txt").write_text("actual controlled result")
            manifest = {"schema":1,"files":{"result.txt":hashlib.sha256((root/"result.txt").read_bytes()).hexdigest()}}
            module.verify_artifacts(root, manifest)
            (root / "result.txt").write_text("forged PASS")
            with self.assertRaises(ValueError):
                module.verify_artifacts(root, manifest)
            with self.assertRaises(ValueError):
                module.verify_artifacts(root, {"schema":1,"files":{"../result.txt":"0"*64}})
