"""Schedule/transport contracts. No live Pentaho capability certification."""

import unittest
from datetime import datetime, timezone
from app.unified.calendar import occurrences
from app.unified.pentaho_schedule import native_schedule
from app.unified.schemas import Schedule, ETLParameters
from app.unified.pentaho_execution import proof_covers_claims
from app.security.permission_catalog import LEGACY_ADMIN, LEGACY_OPERATOR
from app.security.access_control import route_permissions


class HistoryContracts(unittest.TestCase):
    def test_spring_gap_skipped_and_fall_fold_is_explicit(self):
        spring = Schedule(
            frequency="DAILY", timezone="America/New_York", time="02:30"
        ).model_dump(mode="json")
        rows = list(
            occurrences(
                spring,
                datetime(2026, 3, 8, 0, tzinfo=timezone.utc),
                datetime(2026, 3, 10, 0, tzinfo=timezone.utc),
            )
        )
        self.assertEqual([r.isoformat() for r in rows], ["2026-03-09T06:30:00+00:00"])
        fold = {**spring, "time": "01:30"}
        begin = datetime(2026, 11, 1, 0, tzinfo=timezone.utc)
        end = datetime(2026, 11, 2, 0, tzinfo=timezone.utc)
        first = list(occurrences({**fold, "dst_policy": "FIRST"}, begin, end))
        second = list(occurrences({**fold, "dst_policy": "SECOND"}, begin, end))
        self.assertEqual((second[0] - first[0]).total_seconds(), 3600)

    def test_schedule_authority_not_implicitly_configured(self):
        self.assertIsNone(ETLParameters().pentaho_schedule_authority)
        self.assertEqual(
            ETLParameters(
                pentaho_schedule_authority={"mode": "MANUAL", "revision": "manual-1"}
            ).pentaho_schedule_authority.mode,
            "MANUAL",
        )

    def test_native_schedule_requires_immutable_identity_inventory_and_hash(self):
        with self.assertRaises(ValueError):
            native_schedule({"schedule": {}})
        self.assertFalse(
            proof_covers_claims(
                {"verified_pentaho_claims": ["INVOCATION", "SCHEDULE"]},
                {
                    "event": {
                        "pentaho_identity": {
                            "invocation_alias": "controlled",
                            "native_execution_id": "controlled",
                        }
                    }
                },
            )
        )

    def test_replay_privileges_not_implicitly_inherited(self):
        for keys in [LEGACY_ADMIN, LEGACY_OPERATOR]:
            self.assertNotIn("etl.replay", keys)
            self.assertNotIn("etl.approve_replay", keys)
        self.assertEqual(
            route_permissions(
                "PUT", "/api/v1/unified/resources/r/historical-notifications"
            ),
            ("templates.manage",),
        )
        self.assertEqual(
            route_permissions(
                "GET", "/api/v1/unified/resources/r/historical-notifications"
            ),
            ("alerts.view",),
        )

    def test_historical_worker_failure_does_not_prevent_live_alert_delivery(self):
        from unittest.mock import patch
        from app.worker.notifications import dispatch_pending_notifications

        calls = []

        def historical(**kwargs):
            calls.append("historical")
            raise RuntimeError("controlled local worker failure")

        with patch(
            "app.telemetry.delivery.queue_escalations",
            side_effect=lambda: calls.append("live"),
        ), patch(
            "app.worker.notifications._claim_notification", return_value=None
        ), patch(
            "app.unified.pentaho_history.dispatch_notices", side_effect=historical
        ):
            result = dispatch_pending_notifications()
        self.assertEqual(calls, ["live", "historical"])
        self.assertEqual(result["historical"]["worker_failed"], 1)
