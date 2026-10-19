"""Backend OpenAPI boundaries consumed by Sprint 07; no database needed."""

import unittest
from app.main import app


class Sprint07FrontendContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = app.openapi()
        cls.paths = cls.doc["paths"]

    def schema(self, path):
        ref = self.paths[path]["post"]["requestBody"]["content"]["application/json"][
            "schema"
        ]["$ref"].split("/")[-1]
        return self.doc["components"]["schemas"][ref]

    def test_review_decision_anchors_server_candidate(self):
        s = self.schema(
            "/api/v1/unified/resources/{id}/evidence-reviews/{review_id}/decision"
        )
        self.assertEqual(
            set(s["required"]),
            {"action", "expected_revision", "idempotency_key", "reason"},
        )
        self.assertFalse(s["additionalProperties"])
        self.assertEqual(
            set(s["properties"]["action"]["enum"]),
            {"DEFER", "REJECT_CLAIM", "ACCEPT_VERIFIED_CLAIM", "ADOPT_LEGACY"},
        )

    def test_recovery_proposal_and_decision_revision_contracts(self):
        base = "/api/v1/unified/resources/{id}/executions/{history_id}/recovery-links"
        s = self.schema(base)
        self.assertEqual(
            set(s["required"]),
            {"recovery_history_id", "evidence_ids", "reason", "idempotency_key"},
        )
        self.assertEqual(s["properties"]["evidence_ids"]["minItems"], 2)
        s = self.schema(base + "/{link_id}/decision")
        self.assertIn("expected_revision", s["required"])
        self.assertEqual(s["properties"]["action"]["enum"], ["CONFIRM", "REVERSE"])

    def test_scoped_pagination_and_bounded_occurrences(self):
        for path in ["/api/v1/unified/resources", "/api/v1/native-incidents"]:
            self.assertTrue(
                {"organization_id", "environment", "limit", "offset"}
                <= {p["name"] for p in self.paths[path]["get"]["parameters"]}
            )
        names = {
            p["name"]
            for p in self.paths["/api/v1/unified/resources/{id}/schedule-windows"][
                "get"
            ]["parameters"]
        }
        self.assertIn("limit", names)
        self.assertNotIn("offset", names)

    def test_canonical_detail_evidence_routes(self):
        for path in [
            "/api/v1/unified/resources/{id}/executions/{history_id}/attempts",
            "/api/v1/native-incidents/{incident_id}/execution-failures",
            "/api/v1/native-incidents/{incident_id}/recovery-assessments",
        ]:
            self.assertTrue(
                {"limit", "offset"}
                <= {p["name"] for p in self.paths[path]["get"]["parameters"]}
            )

    def test_restoration_is_server_evaluated(self):
        s = self.schema("/api/v1/native-incidents/{incident_id}/recovery-assessments")
        self.assertEqual(set(s["required"]), {"revision", "idempotency_key"})
        self.assertNotIn("ready", s["properties"])
        self.assertFalse(s["additionalProperties"])
        s = self.schema("/api/v1/native-incidents/{incident_id}/transition")
        self.assertEqual(len(s["properties"]["status"]["enum"]), 7)
