"""Fail-closed coverage fixtures; not real image/security acceptance."""

import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/ci"))
import image_security_gate as gate
spec = importlib.util.spec_from_file_location(
    "image_coverage", ROOT / "scripts/ci/image_coverage.py"
)
coverage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coverage)
spec = importlib.util.spec_from_file_location(
    "image_policy", ROOT / "scripts/ci/security_manifest.py"
)
security = importlib.util.module_from_spec(spec)
spec.loader.exec_module(security)


class ImageCoverageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in [
            ".ci/image-coverage.json",
            ".github/workflows/security-artifacts.yml",
            "deploy/release/image-policy.json",
        ]:
            (self.root / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / name, self.root / name)
        rows = json.loads((ROOT / ".ci/image-coverage.json").read_text())["roles"]
        for row in rows:
            if row.get("file"):
                (self.root / row["file"]).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(ROOT / row["file"], self.root / row["file"])
        self.source = "1" * 40
        self.images = self.root / "artifacts"
        self.images.mkdir()
        for index, row in enumerate(coverage.contract(self.root)):
            directory = self.images / ("image-evidence-" + row["role"])
            directory.mkdir()
            identity = "sha256:" + str(index) * 64
            data = {
                "image-binding.json": {
                    "role": row["role"],
                    "image_id": identity,
                    "source_sha": self.source,
                    "architecture": "amd64",
                    "identity_kind": "docker-image-config-sha256",
                    "build_input": coverage.material(row, self.root),
                    "repo_digests": [row["image"]] if row.get("image") else [],
                },
                "sbom.cdx.json": {
                    "bomFormat": "CycloneDX",
                    "components": [{"name": "unit-only"}],
                    "metadata": {
                        "component": {"version": identity.removeprefix("sha256:")}
                    },
                },
                "sbom.syft.json": {
                    "source": {"metadata": {"imageID": identity}},
                    "artifacts": [{"name": "unit-only"}],
                },
                "grype.json": {
                    "source": {"target": {"imageID": identity}},
                    "descriptor": {},
                    "matches": [{"vulnerability": {"severity": "High"}}],
                },
                "licenses.json": {
                    "status": "PENDING_ACCOUNTABLE_REVIEW",
                    "reviewer": None,
                    "components": [{"name": "unit-only"}],
                },
                "grype-db.json": {
                    "valid": True,
                    "built": datetime.now(timezone.utc).isoformat(),
                },
                "tools.json": {},
            }
            for name, value in data.items():
                (directory / name).write_text(json.dumps(value))
            (directory / "provenance.json").write_text(
                json.dumps(
                    {
                        "image_id": identity,
                        "source_sha": self.source,
                        "architecture": "amd64",
                        "scan_role": row["role"],
                        "sha256": {
                            name: coverage.sha(directory / name) for name in data
                        },
                    }
                )
            )

    def mutate(self, name, change):
        directory = self.images / "image-evidence-backend-runtime"
        path = directory / name
        data = json.loads(path.read_text())
        change(data)
        path.write_text(json.dumps(data))
        if name != "provenance.json":
            p = json.loads((directory / "provenance.json").read_text())
            p["sha256"][name] = coverage.sha(path)
            (directory / "provenance.json").write_text(json.dumps(p))

    def test_repository_workflow_has_all_six_production_and_seven_legacy_roles(self):
        self.assertEqual(len(coverage.contract()), 8)

    def test_complete_fixture_coverage_does_not_clear_vulnerability_or_legal_gates(
        self,
    ):
        result = coverage.coverage(self.images, self.source, self.root)
        self.assertEqual(len(result["images"]), 8)
        self.assertFalse(result["release_eligible"])
        # Per-image evidence integrity must PASS without pretending security approval.
        image_path = self.images / "image-evidence-backend-runtime"
        self.assertEqual(
            security.verify_evidence(image_path)["status"],
            "PASS_BOUNDED_IMAGE_EVIDENCE",
        )
        # Mandatory centralized security evaluation sees EVERY failing role.
        verdict = gate.evaluate(self.images, self.source, self.root)
        self.assertEqual(verdict["status"], "BLOCKED")
        self.assertEqual(verdict["blocked_roles"], 8)
        self.assertFalse(verdict["release_approved"])
        with self.assertRaisesRegex(ValueError, "Unresolved High"):
            security.validate(image_path)
        # Even a clean vulnerability scan cannot manufacture legal approval.
        self.mutate("grype.json", lambda x: x.update(matches=[]))
        self.assertEqual(
            security.verify_evidence(image_path)["status"],
            "PASS_BOUNDED_IMAGE_EVIDENCE",
        )
        with self.assertRaisesRegex(ValueError, "License/NOTICE review pending"):
            security.validate(image_path)
        # Regression guard: the workflow must keep the central policy gate
        # mandatory, independent of successful per-image evidence collection.
        workflow = (self.root / ".github/workflows/security-artifacts.yml").read_text()
        self.assertIn("scripts/ci/image_security_gate.py", workflow)
        self.assertIn("name: image-security-policy", workflow)

    def test_missing_production_image_is_failure(self):
        shutil.rmtree(self.images / "image-evidence-production-frontend")
        with self.assertRaisesRegex(ValueError, "production-frontend"):
            coverage.coverage(self.images, self.source, self.root)

    def test_swapped_role_artifact_is_failure_even_if_hashes_are_consistent(self):
        self.mutate("image-binding.json", lambda x: x.update(role="frontend"))
        with self.assertRaises(ValueError):
            coverage.coverage(self.images, self.source, self.root)

    def test_each_sbom_or_scan_digest_mismatch_is_failure(self):
        for name in ["sbom.cdx.json", "sbom.syft.json", "grype.json"]:
            original = (
                self.images / "image-evidence-backend-runtime" / name
            ).read_text()
            self.mutate(
                name,
                lambda x: (
                    x.update(metadata={"component": {"version": "f" * 64}})
                    if name.endswith("cdx.json")
                    else x.update(
                        source={
                            "metadata": {"imageID": "bad"},
                            "target": {"imageID": "bad"},
                        }
                    )
                ),
            )
            with self.assertRaises(ValueError):
                coverage.coverage(self.images, self.source, self.root)
            self.mutate(name, lambda x: (x.clear(), x.update(json.loads(original))))

    def test_stale_source_commit_is_failure(self):
        with self.assertRaisesRegex(ValueError, "source commit"):
            coverage.coverage(self.images, "2" * 40, self.root)

    def test_wrong_build_target_is_failure(self):
        self.mutate(
            "image-binding.json", lambda x: x["build_input"].update(target="migration")
        )
        with self.assertRaisesRegex(ValueError, "build inputs"):
            coverage.coverage(self.images, self.source, self.root)

    def test_tampered_or_missing_binding_is_failure(self):
        path = self.images / "image-evidence-backend-runtime/image-binding.json"
        path.write_text("{}")
        with self.assertRaises((ValueError, KeyError)):
            coverage.coverage(self.images, self.source, self.root)
        path.unlink()
        with self.assertRaises(FileNotFoundError):
            coverage.coverage(self.images, self.source, self.root)

    def test_workflow_matrix_drift_is_failure(self):
        path = self.root / ".github/workflows/security-artifacts.yml"
        path.write_text(path.read_text().replace("target: runtime", "target: wrong"))
        with self.assertRaisesRegex(ValueError, "coverage drift"):
            coverage.contract(self.root)

    def test_missing_required_scan_report_is_failure(self):
        (self.images / "image-evidence-backend-runtime/grype.json").unlink()
        with self.assertRaises(FileNotFoundError):
            coverage.coverage(self.images, self.source, self.root)

    def test_empty_catalog_cannot_satisfy_coverage(self):
        self.mutate("sbom.syft.json", lambda x: x.update(artifacts=[]))
        with self.assertRaisesRegex(ValueError, "Empty/invalid"):
            coverage.coverage(self.images, self.source, self.root)
