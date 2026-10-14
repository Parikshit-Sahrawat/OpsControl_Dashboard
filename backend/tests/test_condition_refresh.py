"""An ongoing condition refreshes authorized alerts, without implicit rule activation."""

import unittest
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace as Row
from unittest.mock import Mock, patch
from uuid import uuid4
from app.unified.engines import condition


class ConditionRefreshTests(unittest.TestCase):
    def test_existing_active_condition_reenables_only_explicitly_approved_rule(self):
        now = datetime.now(timezone.utc)
        alert = uuid4()
        row = Row(
            active=True,
            severity="CRITICAL",
            last_observed_at=now - timedelta(seconds=30),
            alert_state_id=alert,
            evidence={},
        )
        resource = Row(
            id=uuid4(),
            organization_id=uuid4(),
            domain="VM",
            name="Controlled VM",
            configuration={
                "alert_setup": {
                    "enabled": True,
                    "parameter_version": 2,
                    "severities": ["CRITICAL"],
                    "in_app": False,
                    "destinations": [],
                }
            },
        )
        metric = Row(id=uuid4())
        rule = Row(enabled=False, severity="WARNING", notification_channels=["IN_APP"])
        db = Mock()
        db.scalar.side_effect = [row, Row(version=2), metric, rule]
        with patch(
            "app.unified.engines.evaluate_metric_sample", return_value=Row(id=alert)
        ) as evaluate:
            self.assertIs(
                condition(
                    db,
                    resource,
                    "CPU",
                    "CPU",
                    True,
                    "CRITICAL",
                    "Observed breach",
                    {"sample_id": str(uuid4())},
                    now,
                ),
                row,
            )
            evaluate.assert_called_once()
            self.assertTrue(rule.enabled)
            self.assertEqual(rule.notification_channels, [])
            self.assertEqual(row.last_observed_at, now)

    def test_disabled_setup_cannot_open_or_reenable_alert(self):
        now = datetime.now(timezone.utc)
        resource = Row(
            id=uuid4(),
            organization_id=uuid4(),
            domain="VM",
            name="Controlled VM",
            configuration={},
        )
        db = Mock()
        db.scalar.side_effect = [None, None]
        with patch("app.unified.engines.evaluate_metric_sample") as evaluate:
            condition(
                db, resource, "CPU", "CPU", True, "CRITICAL", "Observed breach", {}, now
            )
            evaluate.assert_not_called()
