"""Authorized activation metadata stays narrow; collector configuration uses existing redaction."""

import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4
from fastapi import HTTPException
from app.api.activation import activation_state


class ActivationHydrationTests(unittest.TestCase):
    def test_persisted_selection_metadata_excludes_configuration_and_secrets(self):
        record = SimpleNamespace(
            status="ACTIVE",
            version=2,
            collector_id=uuid4(),
            applied_at=datetime.now(timezone.utc),
            details={
                "generated": [],
                "include_templates": True,
                "plan": {
                    "rules": [
                        {"version_id": "rule-v1", "definition": {"secret": "canary"}},
                        {"version_id": None, "source": "TEMPLATE"},
                    ],
                    "collector": {"configuration": {"Authorization": "canary"}},
                },
            },
        )
        db = Mock()
        db.scalar.return_value = record
        source_id = uuid4()
        with patch("app.api.activation.can_manage") as authorize:
            result = activation_state(source_id, db)
        authorize.assert_called_once_with(db, source_id, "collectors.view")
        self.assertEqual(result["rule_version_ids"], ["rule-v1"])
        self.assertTrue(result["include_templates"])
        self.assertNotIn("canary", str(result))

    def test_missing_activation_returns_not_configured(self):
        db = Mock()
        db.scalar.return_value = None
        with patch("app.api.activation.can_manage"):
            self.assertEqual(activation_state(uuid4(), db)["status"], "NOT_CONFIGURED")

    def test_unauthorized_source_cannot_read_activation_metadata(self):
        db = Mock()
        db.get.return_value = SimpleNamespace(organization_id=uuid4())
        with patch("app.api.activation.current_principal") as principal:
            principal.get.return_value = None
            with self.assertRaises(HTTPException) as error:
                activation_state(uuid4(), db)
        self.assertEqual(error.exception.status_code, 403)
        db.scalar.assert_not_called()

    def test_legacy_activation_infers_template_selection_from_persisted_plan(self):
        db = Mock()
        db.scalar.return_value = SimpleNamespace(
            status="ACTIVE",
            version=1,
            collector_id=None,
            applied_at=datetime.now(timezone.utc),
            details={"plan": {"rules": [{"source": "TEMPLATE"}]}},
        )
        with patch("app.api.activation.can_manage"):
            self.assertTrue(activation_state(uuid4(), db)["include_templates"])
