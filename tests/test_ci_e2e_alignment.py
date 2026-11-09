"""Negative integrity fixtures, never independent workflow certification."""

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts.ci import e2e_alignment as guard


class E2EAlignmentTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        for command in (["git", "init", "-q"],):
            subprocess.run(command, cwd=self.root, check=True, capture_output=True)
        (self.root / "source.txt").write_text(
            "static unit fixture, not product evidence"
        )
        (self.root / "evidence.json").write_text('{"status":"UNIT_FIXTURE_ONLY"}')
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=Fixture",
                "-c",
                "user.email=fixture@example.invalid",
                "commit",
                "-qm",
                "unit fixture",
            ],
            cwd=self.root,
            check=True,
        )
        sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=self.root, text=True
        ).strip()
        self.data = {
            "schema": 1,
            "mode": "SPRINT1_CONTROLLED_ONLY",
            "gates": guard.GATES.copy(),
            "workflows": [],
        }
        self.evidence = {
            "path": "evidence.json",
            "commit_sha": sha,
            "sha256": hashlib.sha256(
                (self.root / "evidence.json").read_bytes()
            ).hexdigest(),
        }
        for identity in sorted(guard.IDS):
            self.data["workflows"].append(
                {
                    "workflow_id": identity,
                    "source_to_ui_journey": "unit fixture only",
                    "owner": "unit role; no signoff",
                    "environment": "unit only",
                    "source_sha": sha,
                    "source_paths": ["source.txt"],
                    "exact_test_command_job": "unit schema validation, not execution proof",
                    "certification_authority": "NONE_PENDING",
                    "provider_certification": False,
                    "status_classification": "PARTIAL",
                    "evidence_level": "IMPLEMENTED",
                    "last_result": "PARTIAL",
                    "blockers": ["No real product execution"],
                    "evidence": [],
                    "collector_required": True,
                    "verified_boundaries": [],
                }
            )

    def test_actual_repository_register(self):
        self.assertEqual(guard.validate()["workflow_rows"], 7)

    def test_pending_rows_allow_explicit_missing_evidence(self):
        self.assertEqual(guard.validate(self.data, self.root)["whole_path_verified"], 0)

    def test_missing_duplicate_and_unknown_workflows_fail(self):
        for mutate in (
            lambda d: d["workflows"].pop(),
            lambda d: d["workflows"].append(copy.deepcopy(d["workflows"][0])),
            lambda d: d["workflows"][0].update(status_classification="UNKNOWN"),
        ):
            data = copy.deepcopy(self.data)
            mutate(data)
            with self.assertRaises(ValueError):
                guard.validate(data, self.root)

    def test_verified_claim_requires_receipts_and_real_boundaries(self):
        row = self.data["workflows"][0]
        row.update(
            status_classification="CONTROLLED_E2E_VERIFIED",
            evidence_level="CONTROLLED_E2E_VERIFIED",
            last_result="PASS",
        )
        with self.assertRaises(ValueError):
            guard.validate(self.data, self.root)
        row["certification_authority"] = "CONTROLLED_ENGINEERING_ONLY"
        row["evidence"] = [self.evidence]
        row["verified_boundaries"] = [
            "authenticated_ui",
            "actual_api",
            "migrated_postgres",
            "tenant_negative",
            "failure_restart",
        ]
        with self.assertRaises(ValueError):
            guard.validate(self.data, self.root)
        row["verified_boundaries"].append("real_collector_worker")
        # This checks validator structure using labelled unit blobs; it cannot
        # qualify a product workflow or prove the declared boundaries itself.
        self.assertEqual(guard.validate(self.data, self.root)["whole_path_verified"], 1)

    def test_provider_certification_and_gate_promotion_rejected(self):
        for level in (
            "GENUINE_PROVIDER_VERIFIED",
            "INDEPENDENTLY_ACCEPTED",
            "RELEASE_ELIGIBLE",
        ):
            data = copy.deepcopy(self.data)
            data["workflows"][0]["evidence_level"] = level
            with self.assertRaises(ValueError):
                guard.validate(data, self.root)
        self.data["gates"]["RELEASE"] = "GO"
        with self.assertRaises(ValueError):
            guard.validate(self.data, self.root)

    def test_missing_tampered_and_unpinned_evidence_rejected(self):
        for key, value in (
            ("path", "missing.json"),
            ("sha256", "0" * 64),
            ("commit_sha", "main"),
            ("commit_sha", "f" * 40),
            ("path", "../escape"),
        ):
            data = copy.deepcopy(self.data)
            entry = copy.deepcopy(self.evidence)
            entry[key] = value
            data["workflows"][0]["evidence"] = [entry]
            with self.assertRaises(ValueError):
                guard.validate(data, self.root)

    def test_markdown_json_drift_rejected(self):
        path = self.root / guard.MATRIX
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(self.data))
        markdown = path.with_suffix(".md")
        markdown.write_text("unreviewed drift")
        with self.assertRaisesRegex(ValueError, "drift"):
            guard.validate(self.data, self.root)
        markdown.write_text(guard.render(self.data))
        self.assertEqual(guard.validate(self.data, self.root)["status"], "PASS")

    def test_shallow_ci_fetches_only_pinned_history_without_checkout(self):
        path = self.root / guard.MATRIX
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(self.data))
        path.with_suffix(".md").write_text(guard.render(self.data))
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=Fixture",
                "-c",
                "user.email=fixture@example.invalid",
                "commit",
                "-qm",
                "reviewed matrix",
            ],
            cwd=self.root,
            check=True,
        )
        head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=self.root, text=True
        ).strip()
        clone = self.root / "shallow"
        subprocess.run(
            ["git", "clone", "-q", "--depth=1", self.root.as_uri(), str(clone)],
            check=True,
            capture_output=True,
        )
        self.assertEqual(
            guard.prepare_history(clone), [self.data["workflows"][0]["source_sha"]]
        )
        self.assertEqual(
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=clone, text=True
            ).strip(),
            head,
        )
        self.assertEqual(guard.validate(root=clone)["status"], "PASS")
        self.assertEqual(guard.prepare_history(clone), [])
