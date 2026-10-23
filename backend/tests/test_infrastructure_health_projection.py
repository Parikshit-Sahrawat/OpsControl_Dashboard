"""A recent observation must not hide the current collector state."""

import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from app.api.infrastructure import snapshot


class InfrastructureHealthProjectionTests(unittest.TestCase):
    def test_stopped_collector_with_recent_success_is_not_healthy(self):
        source = SimpleNamespace(
            id=uuid4(),
            organization_id=uuid4(),
            name="customer-vm",
            enabled=True,
            source_type="LINUX",
        )
        collector = SimpleNamespace(
            id=uuid4(),
            name="vm-collector",
            collector_type="LINUX_HOST",
            enabled=True,
            status="STOPPED",
            interval_seconds=60,
            last_error=None,
            last_run_at=None,
        )
        evidence = SimpleNamespace(
            id=uuid4(),
            observed_at=datetime.now(timezone.utc),
            payload={"outcome": "SUCCESS"},
        )
        for status, expected in (
            ("STOPPED", "UNKNOWN"),
            ("RUNNING", "UNKNOWN"),
            ("ERROR", "WARNING"),
            ("HEALTHY", "HEALTHY"),
        ):
            with self.subTest(status=status):
                collector.status = status
                db = Mock()
                db.scalars.return_value.all.side_effect = [[collector], [], []]
                db.scalar.return_value = evidence
                result = snapshot(source, db)
                self.assertEqual(result["collectors"][0]["status"], status)
                self.assertEqual(result["collectors"][0]["freshness"], "CURRENT")
                self.assertEqual(result["health"], expected)


if __name__ == "__main__":
    unittest.main()
