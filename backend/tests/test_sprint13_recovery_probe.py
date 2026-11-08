"""Preservation-gate checks for the owned, disposable restore probe."""

import subprocess
import unittest

from scripts.sprint13_recovery_probe import assert_preserved_downgrade


class PreservedDowngradeTests(unittest.TestCase):
    def test_kubernetes_history_guard_keeps_current_revision(self):
        downgrade = subprocess.CompletedProcess(
            args=["alembic", "downgrade"],
            returncode=1,
            stderr=(
                "RuntimeError: Canonical cluster or association evidence exists; "
                "restore a verified backup"
            ),
        )
        assert_preserved_downgrade(
            downgrade,
            "0038_k8s_cluster_associations",
            "0038_k8s_cluster_associations",
        )

    def test_earlier_guard_rolls_back_the_whole_downgrade(self):
        downgrade = subprocess.CompletedProcess(
            args=["alembic", "downgrade"],
            returncode=1,
            stderr="RuntimeError: Access boundaries or decisions exist",
        )
        assert_preserved_downgrade(
            downgrade,
            "0038_k8s_cluster_associations",
            "0038_k8s_cluster_associations",
        )

    def test_central_guard_requires_recovery_guidance(self):
        message = "Unsafe populated ETL downgrade blocked before DDL: workflows. Take a verified full backup and rehearse isolated restoration"
        assert_preserved_downgrade(
            subprocess.CompletedProcess([], 1, stderr=message), "0039", "0039"
        )
        for error, revision in (
            (message, "0038"),
            ("Unsafe populated ETL downgrade blocked before DDL", "0039"),
        ):
            with self.subTest(error=error, revision=revision):
                with self.assertRaises(AssertionError):
                    assert_preserved_downgrade(
                        subprocess.CompletedProcess([], 1, stderr=error),
                        "0039",
                        revision,
                    )

    def test_unknown_failure_or_changed_revision_is_not_preservation(self):
        for returncode, stderr, after in (
            (0, "", "0031_in_app_notifications"),
            (
                1,
                "OperationalError: connection refused",
                "0038_k8s_cluster_associations",
            ),
            (1, "Access boundaries or decisions exist", "0037_access_boundaries"),
        ):
            with self.subTest(returncode=returncode, stderr=stderr, after=after):
                with self.assertRaises(AssertionError):
                    assert_preserved_downgrade(
                        subprocess.CompletedProcess(
                            args=["alembic", "downgrade"],
                            returncode=returncode,
                            stderr=stderr,
                        ),
                        "0038_k8s_cluster_associations",
                        after,
                    )


if __name__ == "__main__":
    unittest.main()
