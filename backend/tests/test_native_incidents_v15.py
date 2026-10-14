"""Safety tests use controlled unit inputs and make no persistent RBAC changes."""

import unittest
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import patch
from fastapi import HTTPException
from app.native_incidents.service import (
    evaluate_recovery,
    TRANSITIONS,
    transition,
    process_incidents,
)
from app.native_incidents.api import Transition, Assignment
from app.security.scope import Principal, current_principal
from pydantic import ValidationError


class NativeRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc)
        self.start = self.now - timedelta(seconds=90)
        self.org, self.user = uuid4(), uuid4()
        self.alert = SimpleNamespace(
            id=uuid4(),
            status="RESOLVED",
            resolved_at=self.start,
            last_evaluated_at=self.now,
        )
        self.condition = SimpleNamespace(
            id=uuid4(),
            active=False,
            resolved_at=self.start,
            last_observed_at=self.now,
            evidence={"sample_id": str(uuid4())},
            alert_state_id=self.alert.id,
        )
        self.principal = Principal(
            self.user,
            "operator",
            False,
            {self.org: "operator"},
            permissions=frozenset({"incidents.manage"}),
            customer_permissions={self.org: frozenset({"incidents.manage"})},
        )
        self.token = current_principal.set(self.principal)

    def tearDown(self):
        current_principal.reset(self.token)

    def test_empty_evidence_never_proves_recovery(self):
        self.assertFalse(evaluate_recovery([], [], self.start, 60, self.now)["ready"])

    def test_stable_fresh_resolved_evidence_verifies(self):
        result = evaluate_recovery(
            [self.alert], [self.condition], self.start, 60, self.now
        )
        self.assertTrue(result["ready"])
        self.assertEqual(result["evidence"]["alert_ids"], [str(self.alert.id)])

    def test_stale_alert_uses_real_fresh_condition(self):
        self.alert.last_evaluated_at = self.now - timedelta(minutes=5)
        self.assertTrue(
            evaluate_recovery([self.alert], [self.condition], self.start, 60, self.now)[
                "ready"
            ]
        )
        self.assertFalse(
            evaluate_recovery([self.alert], [], self.start, 60, self.now)["ready"]
        )

    def test_future_evidence_cannot_verify(self):
        self.alert.last_evaluated_at = self.now + timedelta(minutes=5)
        self.assertFalse(
            evaluate_recovery([self.alert], [], self.start, 60, self.now)["ready"]
        )

    def test_active_or_evidenceless_condition_blocks(self):
        self.condition.active = True
        self.assertFalse(
            evaluate_recovery([self.alert], [self.condition], self.start, 60, self.now)[
                "ready"
            ]
        )
        self.condition.active = False
        self.condition.evidence = {}
        self.assertFalse(
            evaluate_recovery([self.alert], [self.condition], self.start, 60, self.now)[
                "ready"
            ]
        )

    def test_observation_window_cannot_be_skipped(self):
        self.assertFalse(
            evaluate_recovery(
                [self.alert], [], self.now - timedelta(seconds=30), 1, self.now
            )["ready"]
        )
        self.assertFalse(
            evaluate_recovery([self.alert], [], None, 60, self.now)["ready"]
        )

    def test_open_alert_blocks(self):
        self.alert.status = "OPEN"
        self.assertFalse(
            evaluate_recovery([self.alert], [self.condition], self.start, 60, self.now)[
                "ready"
            ]
        )

    def test_state_graph_forbids_unverified_shortcuts(self):
        self.assertNotIn("RESOLVED", TRANSITIONS["OPEN"])
        self.assertNotIn("CLOSED", TRANSITIONS["INVESTIGATING"])
        self.assertEqual(TRANSITIONS["CLOSED"], {"OPEN"})

    def test_stale_revision_preserves_state(self):
        incident = SimpleNamespace(status="OPEN", organization_id=self.org)
        with patch(
            "app.native_incidents.service.details",
            return_value=SimpleNamespace(revision=2),
        ):
            with self.assertRaises(HTTPException) as error:
                transition(None, incident, "INVESTIGATING", 1, "spoofed", now=self.now)
        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(incident.status, "OPEN")

    def test_recovery_failure_preserves_state(self):
        incident = SimpleNamespace(status="MONITORING", organization_id=self.org)
        d = SimpleNamespace(revision=3)
        with patch("app.native_incidents.service.details", return_value=d), patch(
            "app.native_incidents.service.recovery",
            return_value={"ready": False, "reasons": ["No data"], "evidence": {}},
        ):
            with self.assertRaises(HTTPException) as error:
                transition(None, incident, "RESOLVED", 3, "spoofed", now=self.now)
        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(incident.status, "MONITORING")
        self.assertEqual(d.revision, 3)

    def test_service_denies_cross_customer(self):
        with self.assertRaises(HTTPException) as error:
            transition(
                None,
                SimpleNamespace(organization_id=uuid4()),
                "INVESTIGATING",
                1,
                "operator",
            )
        self.assertEqual(error.exception.status_code, 403)

    def test_service_denies_unauthenticated(self):
        token = current_principal.set(None)
        try:
            with self.assertRaises(HTTPException) as error:
                transition(
                    None,
                    SimpleNamespace(organization_id=self.org),
                    "INVESTIGATING",
                    1,
                    "operator",
                )
            self.assertEqual(error.exception.status_code, 401)
        finally:
            current_principal.reset(token)

    def test_acknowledgement_requires_exact_permission(self):
        with self.assertRaises(HTTPException) as error:
            transition(
                None,
                SimpleNamespace(organization_id=self.org),
                "ACKNOWLEDGED",
                1,
                "operator",
            )
        self.assertEqual(error.exception.status_code, 403)

    def test_mass_assignment_is_rejected(self):
        for body in (
            dict(status="OPEN", revision=1, organization_id=str(self.org)),
            dict(status="FAKE", revision=1),
        ):
            with self.assertRaises(ValidationError):
                Transition(**body)
        with self.assertRaises(ValidationError):
            Assignment(revision=1, assigned_user_id=None, platform_admin=True)

    def test_authorized_transition_uses_authenticated_actor(self):
        incident = SimpleNamespace(status="OPEN", organization_id=self.org)
        d = SimpleNamespace(revision=1)
        with patch("app.native_incidents.service.details", return_value=d), patch(
            "app.native_incidents.service.record"
        ) as audit:
            transition(
                None,
                incident,
                "INVESTIGATING",
                1,
                "spoofed",
                actor_id=uuid4(),
                now=self.now,
            )
        self.assertEqual(incident.status, "INVESTIGATING")
        self.assertEqual(d.revision, 2)
        self.assertEqual(audit.call_args.args[3], "operator")
        self.assertEqual(audit.call_args.args[-1], self.user)

    def test_pending_detail_is_reused_before_flush(self):
        from app.native_incidents.service import details

        class Pending:
            def __init__(self):
                self.new = []

            def get(self, model, identifier):
                return None

            def add(self, item):
                self.new.append(item)

        db = Pending()
        incident = SimpleNamespace(id=uuid4(), organization_id=self.org)
        first = details(db, incident)
        self.assertIs(details(db, incident), first)
        self.assertEqual(len(db.new), 1)

    def test_recovery_rejects_resolved_transient_rebreach(self):
        self._database_recovery_boundary(renewed=True)

    def test_recovery_rejects_unhealthy_sample_inside_window(self):
        self._database_recovery_boundary(window_value=95)

    def test_recovery_rejects_nan_sample(self):
        self._database_recovery_boundary(current_value=float("nan"))

    def _database_recovery_boundary(
        self, renewed=False, window_value=20, current_value=20
    ):
        from app.native_incidents.service import recovery

        self.alert.alert_rule_id = uuid4()
        self.alert.metric_definition_id = uuid4()
        incident = SimpleNamespace(id=uuid4(), organization_id=self.org)
        d = SimpleNamespace(monitoring_started_at=self.start, monitoring_seconds=60)

        class Evidence:
            def __init__(self):
                self.scalar_count = 0
                self.scalars_count = 0

            def scalar(inner, query):
                inner.scalar_count += 1
                if inner.scalar_count == 1:
                    return uuid4() if renewed else None
                if inner.scalar_count == 2:
                    return None
                return SimpleNamespace(
                    value_numeric=current_value, observed_at=self.now
                )

            def scalars(inner, query):
                inner.scalars_count += 1
                return (
                    []
                    if inner.scalars_count == 1
                    else [SimpleNamespace(value_numeric=window_value)]
                )

            def get(inner, model, identifier):
                return SimpleNamespace(operator="GT", threshold_value="80")

        with patch("app.native_incidents.service.details", return_value=d), patch(
            "app.native_incidents.service.linked_alerts", return_value=[self.alert]
        ):
            result = recovery(Evidence(), incident, self.now)
        self.assertFalse(result["ready"])
        self.assertTrue(result["reasons"])

    def test_duplicate_worker_lease_performs_no_writes(self):
        class Locked:
            def scalar(self, statement):
                return False

        self.assertEqual(
            process_incidents(Locked(), self.now), {"processed": 0, "locked": True}
        )


if __name__ == "__main__":
    unittest.main()
