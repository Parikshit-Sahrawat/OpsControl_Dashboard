"""Recipient security and preferences; durable queue behavior has API/PG acceptance."""

import unittest
from types import SimpleNamespace as Row
from unittest.mock import Mock, patch
from uuid import uuid4
from fastapi import HTTPException
from pydantic import ValidationError
from app.telemetry.delivery import validate_destination
from app.telemetry.inbox import validate_targets, audience, Preference, persist


class RecipientTests(unittest.TestCase):
    def test_malformed_or_unbounded_targets_fail_validation(self):
        for ids in (
            [{}],
            [1],
            ["not-a-uuid"],
            [str(uuid4())] * 2,
            "anyone",
            [str(uuid4()) for _ in range(101)],
        ):
            with self.subTest(ids=type(ids).__name__), self.assertRaises(
                (ValueError, TypeError)
            ):
                validate_destination("IN_APP", {"user_ids": ids})
        validate_destination(
            "IN_APP", {"user_ids": [str(uuid4())], "department_ids": []}
        )

    def test_plain_credentials_and_unknown_settings_rejected(self):
        with self.assertRaises(ValueError):
            validate_destination("IN_APP", {"password": "secret"})
        with self.assertRaises(ValidationError):
            Preference(in_app=True, user_id=str(uuid4()))

    def test_inactive_foreign_provider_or_customer_denied(self):
        user, provider, org = uuid4(), uuid4(), uuid4()
        for row, allowed in (
            (None, True),
            (Row(active=False, service_provider_id=provider), True),
            (Row(active=True, service_provider_id=uuid4()), True),
            (Row(active=True, service_provider_id=provider), False),
        ):
            db = Mock()
            db.get.return_value = row
            with patch(
                "app.telemetry.inbox.resolve_access",
                return_value=Row(allows=lambda *args: allowed),
            ):
                with self.assertRaises(HTTPException) as e:
                    validate_targets(db, {"user_ids": [str(user)]}, org, provider)
                self.assertEqual(e.exception.status_code, 422)

    def test_authorized_active_recipient_accepted(self):
        provider = uuid4()
        db = Mock()
        db.get.return_value = Row(active=True, service_provider_id=provider)
        with patch(
            "app.telemetry.inbox.resolve_access",
            return_value=Row(allows=lambda *args: True),
        ):
            validate_targets(db, {"user_ids": [str(uuid4())]}, uuid4(), provider)

    def test_audience_respects_opt_out_and_current_customer_permission(self):
        users = [
            Row(notification_preferences={}),
            Row(notification_preferences={"in_app": False}),
            Row(notification_preferences={}),
        ]
        db = Mock()
        db.scalars.return_value.all.return_value = users
        with patch(
            "app.telemetry.inbox.resolve_access",
            side_effect=[
                Row(allows=lambda *args: True),
                Row(allows=lambda *args: False),
            ],
        ):
            self.assertEqual(audience(db, {}, uuid4()), [users[0]])

    def test_fanout_is_bounded_and_mismatched_evidence_rejected(self):
        db = Mock()
        db.scalars.return_value.all.return_value = [Row()] * 1001
        with self.assertRaises(RuntimeError):
            audience(db, {}, uuid4())
        with self.assertRaises(RuntimeError):
            persist(Row(alert_state_id=uuid4()), Row(id=uuid4()))
