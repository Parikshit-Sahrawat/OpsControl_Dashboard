"""Policy tests with explicit negative fixtures; no live release authorization."""

import copy
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "scripts/ci" / (name + ".py")
    )
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


policy = module("policy")
release = module("release_authorization")
security = module("security_manifest")
aggregate = module("require_success")


class ResultTests(unittest.TestCase):
    def test_all_success(self):
        self.assertTrue(aggregate.validate({"a": {"result": "success"}}))

    def test_missing_failed_skipped_cancelled(self):
        for value in [
            {},
            None,
            {"a": {}},
            *[
                {"a": {"result": s}}
                for s in ["failure", "skipped", "cancelled", "pending"]
            ],
        ]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                aggregate.validate(value)


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.sha = "a" * 40
        self.record = {
            "schema": 1,
            "source_sha": self.sha,
            "phase": "SPRINT10_APPROVED",
            "gates": release.GATES.copy(),
            "operations": ["uat-publish"],
            "status": "APPROVED",
            "approval_evidence": "fixture only",
            "reviewers": {
                "product_owner": "fixture-owner",
                "security": "fixture-security",
                "migration": "fixture-dba",
            },
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        }

    def test_complete_unit_fixture_only(self):
        self.assertTrue(release.validate(self.record, self.sha, "uat-publish"))

    def test_current_gates_cannot_authorize_release(self):
        self.record["gates"] = {
            "CHK-001": "FAIL",
            "CHK-002": "BLOCKED",
            "SECURITY": "BLOCKED",
            "RELEASE": "NO-GO",
        }
        with self.assertRaises(ValueError):
            release.validate(self.record, self.sha, "uat-publish")

    def test_sha_replay_and_operation(self):
        for sha, op in [
            ("b" * 40, "uat-publish"),
            ("main", "uat-publish"),
            (self.sha, "unapproved"),
        ]:
            with self.subTest(sha=sha, op=op), self.assertRaises(ValueError):
                release.validate(self.record, sha, op)

    def test_expiry_and_reviewers(self):
        for field, value in [
            ("expires_at", "2020-01-01T00:00:00Z"),
            ("expires_at", "2030-01-01T00:00:00"),
            (
                "reviewers",
                {"product_owner": "same", "security": "same", "migration": "same"},
            ),
            ("approval_evidence", ""),
            ("phase", "SPRINT1"),
        ]:
            r = copy.deepcopy(self.record)
            r[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                release.validate(r, self.sha, "uat-publish")


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for path in [
            ".github/workflows",
            "scripts/ci",
            ".ci",
            "backend/tests",
            "tests",
            "frontend/scripts",
        ]:
            (self.root / path).mkdir(parents=True, exist_ok=True)
        for f in (ROOT / ".github/workflows").glob("*.yml"):
            shutil.copy(f, self.root / ".github/workflows" / f.name)
        shutil.copy(
            ROOT / "scripts/ci/action-lock.json",
            self.root / "scripts/ci/action-lock.json",
        )
        (self.root / ".ci/scope-manifest.json").write_text(
            json.dumps({"schema": 1, "tests": {}, "protected_assertions": {}})
        )

    def edit(self, old, new):
        f = self.root / ".github/workflows/ci-policy.yml"
        f.write_text(f.read_text().replace(old, new))

    def test_current_structure(self):
        self.assertEqual(policy.validate(self.root)["status"], "PASS")

    def test_path_filter_prohibited_for_all_prs(self):
        self.edit("  pull_request:", "  pull_request:\n    paths: [frontend/**]")
        with self.assertRaises(ValueError):
            policy.validate(self.root)

    def test_target_trigger_prohibited(self):
        self.edit("pull_request:", "pull_request_target:")
        with self.assertRaises(ValueError):
            policy.validate(self.root)

    def test_unpinned_action_rejected(self):
        self.edit(
            "actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
            "actions/checkout@v4",
        )
        with self.assertRaises(ValueError):
            policy.validate(self.root)

    def test_privileged_pr_rejected(self):
        self.edit(
            "    runs-on: ubuntu-24.04",
            "    permissions:\n      contents: write\n    runs-on: ubuntu-24.04",
        )
        with self.assertRaises(ValueError):
            policy.validate(self.root)

    def test_hidden_failure_rejected(self):
        self.edit(
            "      - run: python -m pip install",
            "      - continue-on-error: true\n        run: python -m pip install",
        )
        with self.assertRaises(ValueError):
            policy.validate(self.root)

    def test_test_omission_rejected(self):
        (self.root / "tests/test_new.py").write_text("def test_security(): pass\n")
        with self.assertRaises(ValueError):
            policy.validate(self.root)

    def test_required_context_removal_rejected(self):
        for f in (self.root / ".github/workflows").glob("*.yml"):
            f.write_text(
                f.read_text().replace("  private-https:", "  renamed-private:")
            )
        with self.assertRaises(ValueError):
            policy.validate(self.root)


class ImageEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.identity = "sha256:" + "a" * 64
        self.data = {
            "sbom.cdx.json": {
                "bomFormat": "CycloneDX",
                "components": [{"name": "unit-fixture"}],
            },
            "sbom.syft.json": {"source": {"metadata": {"imageID": self.identity}}},
            "grype.json": {
                "matches": [],
                "descriptor": {},
                "source": {"target": {"imageID": self.identity}},
            },
            "grype-db.json": {
                "built": datetime.now(timezone.utc).isoformat(),
                "valid": True,
            },
            "tools.json": {},
            "licenses.json": {
                "status": "REVIEWED",
                "reviewer": "unit fixture, not legal approval",
            },
        }
        self.write()

    def write(self):
        for f, d in self.data.items():
            (self.root / f).write_text(json.dumps(d))
        (self.root / "provenance.json").write_text(
            json.dumps(
                {
                    "image_id": self.identity,
                    "sha256": {
                        f: hashlib.sha256((self.root / f).read_bytes()).hexdigest()
                        for f in self.data
                    },
                }
            )
        )

    def test_bounded_fixture(self):
        self.assertEqual(
            security.validate(self.root)["status"], "PASS_BOUNDED_IMAGE_POLICY"
        )

    def test_tamper(self):
        (self.root / "grype.json").write_text("{}")
        with self.assertRaises(ValueError):
            security.validate(self.root)

    def test_digest_mismatch(self):
        self.data["sbom.syft.json"]["source"]["metadata"]["imageID"] = (
            "sha256:" + "b" * 64
        )
        self.write()
        with self.assertRaises(ValueError):
            security.validate(self.root)

    def test_stale_database(self):
        self.data["grype-db.json"]["built"] = "2020-01-01T00:00:00Z"
        self.write()
        with self.assertRaises(ValueError):
            security.validate(self.root)

    def test_high_critical_unknown_rejected(self):
        for severity in ["High", "Critical", "Unknown"]:
            self.data["grype.json"]["matches"] = [
                {"vulnerability": {"severity": severity}}
            ]
            self.write()
            with self.subTest(severity=severity), self.assertRaises(ValueError):
                security.validate(self.root)

    def test_inventory_is_not_legal_clearance(self):
        self.data["licenses.json"] = {
            "status": "PENDING_ACCOUNTABLE_REVIEW",
            "reviewer": None,
        }
        self.write()
        with self.assertRaises(ValueError):
            security.validate(self.root)


class BackupBoundaryTests(unittest.TestCase):
    def test_shared_or_uat_targets_rejected_before_docker_access(self):
        restore = module("postgres_restore")
        for name in [
            "postgres",
            "opscontrol-uat-db",
            "opscontrol-v16-other",
            "opscontrol-v16-" + "a" * 13,
        ]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                restore.verify(name, "/tmp/unused-ci-fixture.json")


class SchemaNormalizationTests(unittest.TestCase):
    def test_equivalent_enum_array_cast_only(self):
        normalize = module("postgres_restore").normalize_schema
        old = "CHECK (x = ANY ((ARRAY['A'::character varying, 'B'::character varying])::text[]))"
        new = "CHECK (x = ANY (ARRAY[('A'::character varying)::text, ('B'::character varying)::text]))"
        self.assertEqual(normalize(old), normalize(new))
        self.assertNotEqual(normalize(old), normalize(new.replace("'B'", "'C'")))
        self.assertNotEqual(
            normalize(old), normalize(new.replace("CHECK", "CHECK_REMOVED"))
        )

    def test_only_generated_restrict_keys_are_ignored(self):
        normalize = module("postgres_restore").normalize_schema
        self.assertEqual(
            normalize("\\restrict random1\nCREATE TABLE x();\n\\unrestrict random1"),
            "CREATE TABLE x();",
        )
        self.assertNotEqual(
            normalize("CREATE TABLE x();"), normalize("CREATE TABLE y();")
        )
