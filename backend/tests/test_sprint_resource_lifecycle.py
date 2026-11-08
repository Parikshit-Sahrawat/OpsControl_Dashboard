"""Lifecycle negative contracts; existing owned HTTP/RBAC tests run separately."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4
import app.main  # noqa: F401
from fastapi import HTTPException
from pydantic import ValidationError
from app.api import resource_management, monitoring
from app.schemas.monitoring import DataSourceUpdate, CollectorUpdate
from app.services.collector_lifecycle import require_enabled_parent


class ResourceLifecycleTests(unittest.TestCase):
    def test_ownership_and_unknown_patch_fields_are_rejected(self):
        for model, field in [
            (DataSourceUpdate, "organization_id"),
            (CollectorUpdate, "data_source_id"),
        ]:
            with self.subTest(model=model), self.assertRaises(ValidationError):
                model.model_validate({field: str(uuid4())})

    def test_configuration_does_not_assert_health(self):
        with self.assertRaises(ValidationError):
            CollectorUpdate.model_validate({"status": "HEALTHY"})

    def test_both_patch_routes_refuse_disabled_parent_without_commit(self):
        for handler in [
            resource_management.update_scoped_collector,
            monitoring.update_collector,
        ]:
            db = Mock()
            collector = SimpleNamespace(
                data_source_id=uuid4(),
                enabled=False,
                collector_type="HTTP",
                configuration={},
            )
            db.get.side_effect = [
                collector,
                SimpleNamespace(
                    enabled=False, source_type="LINUX", connection_config={}
                ),
                SimpleNamespace(enabled=False),
            ]
            with self.subTest(route=handler.__name__), self.assertRaises(
                HTTPException
            ) as error:
                handler(uuid4(), CollectorUpdate(enabled=True), db)
            self.assertEqual(error.exception.status_code, 409)
            db.commit.assert_not_called()
            self.assertFalse(collector.enabled)

    def test_disabling_and_enabled_parent_are_supported(self):
        require_enabled_parent(SimpleNamespace(enabled=False), False)
        require_enabled_parent(SimpleNamespace(enabled=True), True)

    def test_unreviewed_release_mapping_fails_before_network(self):
        import importlib.util
        from pathlib import Path
        from unittest.mock import patch

        file = Path(__file__).resolve().parents[2] / "scripts/uat/pull_release.py"
        spec = importlib.util.spec_from_file_location("sprint_publish_policy", file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch.object(module, "api") as api:
            with self.assertRaisesRegex(module.Rejected, "Trusted workflow mapping"):
                module.check_ci("f" * 40)
            api.assert_not_called()
