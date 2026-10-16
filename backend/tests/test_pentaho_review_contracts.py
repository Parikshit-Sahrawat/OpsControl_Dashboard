"""Pure review contracts, no native runtime certification."""

import unittest
from types import SimpleNamespace
from app.security.permission_catalog import (
    PERMISSIONS,
    LEGACY_ADMIN,
    LEGACY_OPERATOR,
    ROLE_SPECS,
)
from app.security.access_control import route_permissions
from app.unified.pentaho_review import category
from app.unified.pentaho_execution import project_history
from app.unified.api import PentahoEvidenceReviewDecision
from pydantic import ValidationError


class ReviewContracts(unittest.TestCase):
    def test_claim_categories_do_not_mix_identity_outcomes_and_recovery(self):
        for error, expected in {
            "PENTAHO_NATIVE_IDENTITY_UNVERIFIED": "AMBIGUOUS_IDENTITY",
            "PENTAHO_IDENTITY_CONFLICT": "NATIVE_ALIAS_CONFLICT",
            "PENTAHO_RETRY_AUTHORITY_CONFLICT": "RETRY_RELATIONSHIP",
            "PENTAHO_CONFLICT_PENDING": "EXECUTION_OUTCOME",
            "PENTAHO_LEGACY_IDENTITY_REVIEW_REQUIRED": "LEGACY_ADOPTION",
            "PENTAHO_RECOVERY_IDENTITY": "RECOVERY_IDENTITY",
        }.items():
            self.assertEqual(category(error), expected)

    def test_granular_permission_not_granted_to_existing_investigators(self):
        self.assertIn("etl.resolve_identity", PERMISSIONS)
        for keys in (
            LEGACY_ADMIN,
            LEGACY_OPERATOR,
            ROLE_SPECS["noc-operator"][1],
            ROLE_SPECS["access-administrator"][1],
        ):
            self.assertNotIn("etl.resolve_identity", keys)
        path = "/api/v1/unified/resources/r/evidence-reviews/q/decision"
        self.assertEqual(route_permissions("POST", path), ("etl.resolve_identity",))
        self.assertEqual(route_permissions("GET", path), ("etl.view",))

    def test_conflict_projection_guard_does_not_query_or_modify_outcome(self):
        history = SimpleNamespace(
            pentaho_review_state="CONFLICTED_EVIDENCE", pentaho_outcome="SUCCESS"
        )
        project_history(None, history)
        self.assertEqual(history.pentaho_outcome, "SUCCESS")

    def test_review_input_no_override_fields_or_workload_actions(self):
        body = dict(
            action="REJECT_CLAIM",
            expected_revision=1,
            idempotency_key="controlled",
            reason="Valid reviewed rejection",
        )
        PentahoEvidenceReviewDecision(**body)
        for extra in (
            {"outcome": "SUCCESS"},
            {"alias_key": "replacement"},
            {"action": "RERUN"},
            {"expected_revision": 0},
        ):
            with self.assertRaises(ValidationError):
                PentahoEvidenceReviewDecision(**{**body, **extra})

    def test_authority_integrity_snapshot_required_for_reviewed_correction(self):
        from unittest.mock import Mock
        from copy import deepcopy
        from app.unified.pentaho_review import verified_candidate
        from app.unified.pentaho_execution import digest
        from app.pipeline_adapters.pentaho_observations import normalize_observation
        from tests.test_pentaho_r1 import scope, observation
        from uuid import uuid4
        from fastapi import HTTPException

        org, source, generation, evidence_id = uuid4(), uuid4(), uuid4(), uuid4()
        cfg = scope()
        payload = normalize_observation(observation(cfg), cfg, str(org))["event"]
        raw = SimpleNamespace(
            organization_id=org,
            source_id=source,
            generation=generation,
            payload={"controlled": True},
        )
        payload["pentaho_verification"] = {
            "claims": ["INVOCATION"],
            "evidence_id": str(evidence_id),
            "source_id": str(source),
            "generation": str(generation),
            "fence": 41,
            "evidence_sha256": digest(raw.payload),
            "attestations": [
                {
                    "platform_version": "controlled-build",
                    "verification_evidence_id": str(uuid4()),
                    "reader_definition_hash": "a" * 64,
                    "connection_id": str(uuid4()),
                    "claims": ["INVOCATION"],
                }
            ],
        }
        resource = SimpleNamespace(
            id=uuid4(),
            organization_id=org,
            environment="TEST",
            configuration={"native_job_id": cfg["native_job_id"]},
        )
        db = Mock()
        db.get.return_value = raw
        verified_candidate(db, resource, SimpleNamespace(payload=payload))
        for broken in (
            {"attestations": []},
            {"evidence_sha256": "0" * 64},
            {"generation": str(uuid4())},
            {"fence": 0},
            {"claims": ["INVOCATION", "EXECUTION_OUTCOME"]},
        ):
            candidate = deepcopy(payload)
            candidate["pentaho_verification"].update(broken)
            with self.assertRaises(HTTPException):
                verified_candidate(db, resource, SimpleNamespace(payload=candidate))
