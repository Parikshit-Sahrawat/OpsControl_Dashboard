"""Retired ITSM paths and baseline notification boundaries."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch
from app.telemetry.delivery import validate_destination, secret, send_destination
from app.worker import notifications as n


class NotificationSecurityTests(unittest.TestCase):
    def test_retired_itsm_cannot_deliver(self):
        self.assertFalse(hasattr(n, "send_servicenow"))
        for channel in ("SERVICENOW", "PAGERDUTY"):
            with self.assertRaises(RuntimeError):
                n.deliver(SimpleNamespace(channel=channel), None)

    def test_only_secure_webhooks(self):
        for url in (
            "http://example.test",
            "https://user:secret@example.test",
            "https://example.test:8000",
            "https://example.test/?secret=1",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_destination("WEBHOOK", {"url": url})
        validate_destination(
            "WEBHOOK",
            {
                "url": "https://notify.example.test/alerts",
                "credential_ref": "env:NOTIFY_KEY",
            },
        )

    def test_email_recipient_and_secret_boundaries(self):
        for recipients in ([], ["bad"], ["a@example.test\r\nBCC:x@example.test"]):
            with self.assertRaises(ValueError):
                validate_destination(
                    "SMTP",
                    {
                        "host": "smtp.example.test",
                        "sender": "s@example.test",
                        "recipients": recipients,
                    },
                )
        with self.assertRaises(ValueError):
            validate_destination("IN_APP", {"password": "bad"})
        with self.assertRaises(ValueError):
            secret("plaintext")

    def test_valid_smtp_configuration_accepts_real_address_syntax(self):
        validate_destination(
            "SMTP",
            {
                "host": "smtp.example.test",
                "sender": "service@example.test",
                "recipients": ["sre@example.test"],
                "port": 587,
                "credential_ref": "env:SMTP_AUTH",
            },
        )

    def test_idempotent_in_app_reference(self):
        d = SimpleNamespace(channel="IN_APP", id="stable-uuid")
        self.assertEqual(n.deliver(d, None), "in-app:stable-uuid")

    def test_provider_error_never_contains_secrets(self):
        self.assertNotIn("private", n._safe_delivery_error(RuntimeError("private")))
