"""Deterministic cause authority and independent assessment state contracts."""

import unittest
from types import SimpleNamespace
from uuid import uuid4
from pydantic import ValidationError
from app.native_incidents.pentaho import cause_reference, root_key, assessment_result
from app.native_incidents.api import AssessmentRequest


class IncidentContracts(unittest.TestCase):
    def test_cause_requires_occurrence_authority_and_hash(self):
        for value in (
            {"job_name": "same"},
            {},
            None,
            {"authority_id": "a", "occurrence_id": "b", "evidence_sha256": "bad"},
        ):
            with self.assertRaises(ValueError):
                cause_reference(value)

    def test_unverified_cause_cannot_correlate(self):
        r = SimpleNamespace(organization_id=uuid4(), environment="TEST")
        self.assertIsNone(
            root_key(r, {"claims": {"INVOCATION"}, "native": {"failure_cause": {}}})
        )

    def test_root_scope_and_proof_are_exact(self):
        r = SimpleNamespace(organization_id=uuid4(), environment="TEST")
        c = {
            "claims": {"FAILURE_CAUSE"},
            "native": {
                "failure_cause": {
                    "authority_id": "scheduler",
                    "occurrence_id": "outage-1",
                    "evidence_sha256": "a" * 64,
                }
            },
        }
        key = root_key(r, c)
        r.environment = "PROD"
        self.assertNotEqual(key, root_key(r, c))
        r.environment = "TEST"
        c["native"]["failure_cause"]["evidence_sha256"] = "b" * 64
        self.assertNotEqual(key, root_key(r, c))

    def test_assessment_results_are_independent(self):
        cases = [
            ((["conflict"], [], [], True, True), "VALIDATION_FAILED"),
            (([], ["proof"], [], False, False), "INSUFFICIENT_EVIDENCE"),
            (([], ["proof"], [], True, False), "VALIDATION_PENDING"),
            (([], [], ["window"], True, False), "RECOVERY_CANDIDATE"),
            (([], [], ["window"], True, True), "VALIDATION_PENDING"),
            (([], [], [], True, True), "VALIDATED_RECOVERY"),
        ]
        for args, expected in cases:
            self.assertEqual(assessment_result(*args), expected)

    def test_assessment_input_requires_revision_key_and_bounded_period(self):
        for body in (
            {"revision": 1},
            {"revision": 1, "idempotency_key": "x", "observation_seconds": 0},
            {"revision": 1, "idempotency_key": "x", "ready": True},
        ):
            with self.assertRaises(ValidationError):
                AssessmentRequest(**body)
