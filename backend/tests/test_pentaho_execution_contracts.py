"""Deterministic authority and lifecycle checks; not genuine native acceptance."""

import unittest
from types import SimpleNamespace as Row
from app.unified.pentaho_execution import (
    execution_state,
    identity_claim,
    proof_covers_claims,
)
from app.unified.reconstruction import logical_payload
from app.pipeline_adapters.pentaho_observations import normalize_observation
from app.security.access_control import route_permissions
from tests.test_pentaho_r1 import observation, scope, END


class PentahoExecutionContracts(unittest.TestCase):
    def test_native_lifecycle_outcome_and_completeness_are_separate(self):
        cases = [
            ("SUCCESS", {}, 1, "TERMINAL", "SUCCESS"),
            ("SUCCESS", {}, 2, "TERMINAL", "SUCCESS_AFTER_RETRY"),
            ("FAILED", {}, 1, "IDENTIFIED", None),
            ("FAILED", {"retry_state": "PENDING"}, 1, "WAITING_FOR_RETRY", None),
            ("FAILED", {"retry_state": "EXHAUSTED"}, 1, "TERMINAL", "FAILED"),
            ("RUNNING", {}, 1, "RUNNING", None),
            ("UNKNOWN", {}, 1, "IDENTIFIED", None),
            ("CANCELLED", {}, 1, "TERMINAL", "CANCELLED"),
        ]
        for outcome, retry, order, lifecycle, result in cases:
            with self.subTest(outcome=outcome, retry=retry):
                state = execution_state(
                    [
                        Row(
                            outcome=outcome,
                            retry_authority=retry,
                            attempt_order=order,
                            completeness="PARTIAL",
                        )
                    ]
                )
                self.assertEqual(state, (lifecycle, result, "PARTIAL"))

    def test_unattested_observation_never_self_certifies_identity(self):
        fact = normalize_observation(observation(), scope(), "a")
        resource = Row(
            organization_id="a",
            id="r",
            environment="TEST",
            configuration={"native_job_id": scope()["native_job_id"]},
        )
        with self.assertRaises(ValueError):
            identity_claim(fact["event"], resource)
        payload = {**fact["event"], "pentaho_verification": {"claims": ["INVOCATION"]}}
        self.assertEqual(identity_claim(payload, resource)["order"], 1)

    def test_names_and_time_matching_configuration_cannot_group_r1_invocations(self):
        payload = normalize_observation(observation(), scope(), "a")["event"]
        result = logical_payload(
            payload,
            {"duplicate_matching": {"attributes": ["jobchain", "scheduled_at"]}},
            "PENTAHO",
            "source",
        )
        self.assertEqual(result["execution_id"], payload["execution_id"])

    def test_declared_retry_authority_needs_native_scheduler_evidence(self):
        payload = normalize_observation(observation(), scope(), "a")["event"]
        self.assertFalse(
            proof_covers_claims(
                {"verified_pentaho_claims": ["INVOCATION", "SCHEDULER_RETRY"]},
                {"event": payload},
            )
        )
        self.assertTrue(
            proof_covers_claims(
                {"verified_pentaho_claims": ["INVOCATION"]}, {"event": payload}
            )
        )
        self.assertFalse(
            proof_covers_claims(
                {"verified_pentaho_claims": ["INVOCATION", "EXECUTION_OUTCOME"]},
                {"event": payload},
            )
        )
        self.assertFalse(
            proof_covers_claims(
                {"verified_pentaho_claims": ["invented-permission"]}, {"event": payload}
            )
        )

    def test_native_completion_proof_and_cancellation_are_monitoring_only(self):
        record = observation(
            state="EXECUTION_RESULT",
            result={
                "invocation_id": "native-run-1",
                "source": "NATIVE_STRUCTURED_LOG",
                "evidence_sha256": "a" * 64,
                "status": "CANCELLED",
                "ended_at": END,
            },
        )
        payload = normalize_observation(record, scope(), "a")["event"]
        self.assertEqual(payload["pentaho_identity"]["native_outcome"], "CANCELLED")
        self.assertEqual(payload["status"], "UNKNOWN")
        self.assertTrue(
            proof_covers_claims(
                {"verified_pentaho_claims": ["INVOCATION", "EXECUTION_OUTCOME"]},
                {"event": payload},
            )
        )

    def test_routes_require_view_or_investigation_not_resource_creation(self):
        path = "/api/v1/unified/resources/r/executions/e/recovery-links/l/decision"
        self.assertEqual(route_permissions("POST", path), ("etl.investigate",))
        self.assertEqual(route_permissions("GET", path), ("etl.view",))

    def test_native_cancelled_terminal_does_not_invent_sla_success_or_staleness(self):
        from datetime import datetime, timedelta
        from unittest.mock import Mock, patch
        from app.models import ExecutionStatus
        from app.unified.engines import evaluate_executions
        from tests.test_pentaho_r1 import START

        h = Row(
            id="controlled-history",
            status=ExecutionStatus.UNKNOWN,
            pentaho_lifecycle="TERMINAL",
            pentaho_outcome="CANCELLED",
            started_at=datetime.fromisoformat(START),
            ended_at=datetime.fromisoformat(END),
            monitoring_conditions={},
            source_evidence={"observed_at": END},
        )
        db = Mock()
        db.scalars.return_value.all.return_value = [h]
        resource = Row(job_order_id="controlled-job")
        parameters = Row(
            configuration={
                "long_running_seconds": 1,
                "completion_sla_seconds": 1,
                "no_response_seconds": 1,
            }
        )
        with patch(
            "app.unified.engines.source_readiness", return_value={"ready": True}
        ), patch("app.unified.engines.condition"):
            evaluate_executions(
                db,
                resource,
                parameters,
                datetime.fromisoformat(END) + timedelta(days=1),
            )
        self.assertEqual(h.sla_status, "UNKNOWN")
        self.assertFalse(h.monitoring_conditions["NO_RESPONSE"])
        self.assertFalse(h.monitoring_conditions["SLA_BREACHED"])
