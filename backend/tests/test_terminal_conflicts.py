"""Conflicting incomplete provider evidence cannot be silently declared successful."""

import unittest
from types import SimpleNamespace as Row
from unittest.mock import Mock
from uuid import uuid4
from app.unified.reconstruction import terminal_fact
from app.models import ExecutionStatus


class TerminalConflictTests(unittest.TestCase):
    def setUp(self):
        self.resource = Row(id=uuid4())
        self.db = Mock()
        self.db.scalar.return_value = None
        self.failure = Row(
            payload={"status": "FAILED", "error": "Actual failure"}, source_kind="LOG"
        )
        self.success = Row(payload={"status": "SUCCESS"}, source_kind="CONNECTOR")

    def test_conflict_preserves_unknown_without_explicit_precedence(self):
        status, chosen, conflict = terminal_fact(
            self.db, self.resource, [self.failure, self.success]
        )
        self.assertEqual(status, ExecutionStatus.UNKNOWN)
        self.assertTrue(conflict)

    def test_explicit_precedence_preserves_selected_failure_evidence(self):
        self.db.scalar.return_value = Row(
            configuration={
                "duplicate_matching": {
                    "conflict_resolution": "PREFER_CONFIGURED_SOURCE",
                    "source_precedence": ["LOG"],
                }
            }
        )
        status, chosen, conflict = terminal_fact(
            self.db, self.resource, [self.failure, self.success]
        )
        self.assertEqual(status, ExecutionStatus.FAILED)
        self.assertEqual(chosen.payload["error"], "Actual failure")
        self.assertTrue(conflict)

    def test_unmatched_preference_does_not_silently_allow_success(self):
        self.db.scalar.return_value = Row(
            configuration={
                "duplicate_matching": {
                    "conflict_resolution": "PREFER_CONFIGURED_SOURCE",
                    "source_precedence": ["UNAVAILABLE"],
                }
            }
        )
        self.assertEqual(
            terminal_fact(self.db, self.resource, [self.failure, self.success])[0],
            ExecutionStatus.UNKNOWN,
        )

    def test_consistent_terminal_evidence_needs_no_policy_override(self):
        status, chosen, conflict = terminal_fact(
            self.db, self.resource, [self.success, self.success]
        )
        self.assertEqual(status, ExecutionStatus.SUCCESS)
        self.assertFalse(conflict)
        self.db.scalar.assert_not_called()
