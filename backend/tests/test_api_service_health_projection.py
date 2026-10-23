"""Recent HTTP probe success does not override current collector state."""

import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.api.operations import service_snapshot


class ApiServiceHealthProjectionTests(unittest.TestCase):
    def test_stopped_probe_with_recent_success_is_not_healthy(self):
        source = SimpleNamespace(
            id=uuid4(), organization_id=uuid4(), name="customer-api", enabled=True
        )
        collector = SimpleNamespace(
            id=uuid4(),
            name="api-probe",
            enabled=True,
            status="STOPPED",
            interval_seconds=60,
        )
        run = SimpleNamespace(
            id=uuid4(),
            collector_id=collector.id,
            started_at=datetime.now(timezone.utc),
            ended_at=datetime.now(timezone.utc),
            status="SUCCESS",
            outcome="SUCCESS",
            http_status=200,
            response_time_ms=12.0,
        )
        for status, expected in (
            ("STOPPED", "UNKNOWN"),
            ("RUNNING", "UNKNOWN"),
            ("ERROR", "CRITICAL"),
            ("HEALTHY", "HEALTHY"),
            ("SUCCESS", "HEALTHY"),  # authenticated remote probe completion
        ):
            with self.subTest(status=status):
                collector.status = status
                result = service_snapshot(
                    source,
                    None,
                    {
                        "collectors": [collector],
                        "runs": {collector.id: run},
                        "alerts": [],
                        "open_count": 0,
                    },
                )
                self.assertEqual(result["collectors"][0]["status"], status)
                self.assertEqual(result["collectors"][0]["freshness"], "CURRENT")
                self.assertEqual(result["health"], expected)

        collector.status = "HEALTHY"
        run.started_at -= timedelta(minutes=10)
        stale = service_snapshot(
            source,
            None,
            {
                "collectors": [collector],
                "runs": {collector.id: run},
                "alerts": [],
                "open_count": 0,
            },
        )
        self.assertEqual(stale["collectors"][0]["freshness"], "STALE")
        self.assertEqual(stale["health"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
