"""Notification transport safety contracts; no external messages are sent."""

import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from urllib.parse import urlsplit
from uuid import uuid4
from app.telemetry import delivery as module


class NotificationTransportTests(unittest.TestCase):
    def invoke(self, channel, config, response_status=202, response_body=b"ok"):
        self.state = SimpleNamespace(
            organization_id=uuid4(),
            severity="CRITICAL",
            message="CPU high\r\ncontrolled evidence",
        )
        self.delivery = SimpleNamespace(
            channel="DEST:" + str(uuid4()),
            id=uuid4(),
            event_type="TRIGGERED",
            payload={"message": "controlled"},
        )
        session = Mock()
        session.__enter__ = Mock(return_value=session)
        session.__exit__ = Mock(return_value=False)
        session.scalar.return_value = SimpleNamespace(
            channel=channel, configuration=config
        )
        self.socket = Mock()
        self.tls = Mock()
        self.client = Mock()
        self.client.getresponse.return_value = SimpleNamespace(
            status=response_status, read=lambda count: response_body
        )
        with patch.object(module, "SessionLocal", return_value=session), patch.object(
            module,
            "target",
            return_value=(urlsplit("https://notify.example.test/hooks"), "192.0.2.10"),
        ), patch.object(
            module.socket, "create_connection", return_value=self.socket
        ), patch.object(
            module.ssl, "create_default_context", return_value=self.tls
        ), patch.object(
            module.http.client, "HTTPSConnection", return_value=self.client
        ):
            return module.send_destination(self.delivery, self.state)

    def test_webhook_verifies_dns_identity_and_has_retry_idempotency_key(self):
        result = self.invoke("WEBHOOK", {"url": "https://notify.example.test/hooks"})
        self.assertEqual(result, "webhook:" + str(self.delivery.id))
        self.tls.wrap_socket.assert_called_once_with(
            self.socket, server_hostname="notify.example.test"
        )
        method, path, body, headers = self.client.request.call_args.args
        self.assertEqual((method, path), ("POST", "/hooks"))
        self.assertEqual(headers["Idempotency-Key"], str(self.delivery.id))
        self.assertEqual(json.loads(body)["delivery_id"], str(self.delivery.id))
        self.client.close.assert_called_once()
        self.socket.close.assert_called_once()

    def test_webhook_rejected_or_oversized_response_never_reports_success(self):
        for status, body in ((503, b"unavailable"), (202, b"x" * 8193)):
            with self.subTest(status=status), self.assertRaises(RuntimeError):
                self.invoke(
                    "WEBHOOK",
                    {"url": "https://notify.example.test/hooks"},
                    status,
                    body,
                )
            self.client.close.assert_called_once()
            self.socket.close.assert_called_once()

    def test_webhook_managed_authentication_and_header_injection_rejection(self):
        with patch.object(module, "secret", return_value="controlled-key"):
            self.invoke(
                "WEBHOOK",
                {
                    "url": "https://notify.example.test/hooks",
                    "credential_ref": "env:WEBHOOK_TEST_KEY",
                },
            )
            self.assertEqual(
                self.client.request.call_args.args[3]["Authorization"],
                "Bearer controlled-key",
            )
        with patch.object(
            module, "secret", return_value="bad\r\nInjected: value"
        ), self.assertRaisesRegex(RuntimeError, "authentication"):
            self.invoke(
                "WEBHOOK",
                {
                    "url": "https://notify.example.test/hooks",
                    "credential_ref": "env:WEBHOOK_TEST_KEY",
                },
            )
        self.client.request.assert_not_called()
        self.socket.close.assert_called_once()

    def test_smtp_tls_authentication_message_identity_and_header_sanitization(self):
        for port in (465, 587):
            with self.subTest(port=port):
                smtp = Mock()
                socket = Mock()
                context = Mock()

                class FakeSMTP:
                    def __init__(inner, host, port, timeout=10, context=None):
                        inner.context = context
                        inner._get_socket(host, port, timeout)

                    def __enter__(inner):
                        return smtp

                    def __exit__(inner, *args):
                        return False

                state = SimpleNamespace(
                    organization_id=uuid4(),
                    severity="CRITICAL",
                    message="CPU high\r\nno extra header",
                )
                delivery = SimpleNamespace(channel="DEST:" + str(uuid4()), id=uuid4())
                row = SimpleNamespace(
                    channel="SMTP",
                    configuration={
                        "host": "smtp.example.test",
                        "port": port,
                        "sender": "ops@example.test",
                        "recipients": ["sre@example.test"],
                        "credential_ref": "env:SMTP_TEST_AUTH",
                    },
                )
                session = Mock()
                session.__enter__ = Mock(return_value=session)
                session.__exit__ = Mock(return_value=False)
                session.scalar.return_value = row
                with patch.object(
                    module, "SessionLocal", return_value=session
                ), patch.object(
                    module, "target", return_value=(None, "192.0.2.20")
                ), patch.object(
                    module.smtplib, "SMTP", FakeSMTP
                ), patch.object(
                    module.smtplib, "SMTP_SSL", FakeSMTP
                ), patch.object(
                    module.socket, "create_connection", return_value=socket
                ) as connect, patch.object(
                    module.ssl, "create_default_context", return_value=context
                ), patch.object(
                    module,
                    "secret",
                    return_value=json.dumps(
                        {"username": "controlled", "password": "test-only"}
                    ),
                ):
                    result = module.send_destination(delivery, state)
                self.assertEqual(result, "smtp:" + str(delivery.id))
                connect.assert_called_once_with(("192.0.2.20", port), 10)
                smtp.login.assert_called_once_with("controlled", "test-only")
                if port == 587:
                    smtp.starttls.assert_called_once_with(context=context)
                else:
                    context.wrap_socket.assert_called_once_with(
                        socket, server_hostname="smtp.example.test"
                    )
                    smtp.starttls.assert_not_called()
                message = smtp.send_message.call_args.args[0]
                self.assertEqual(
                    message["Message-ID"],
                    "<opscontrol-" + str(delivery.id) + "@opscontrol.local>",
                )
                self.assertNotIn("\n", message["Subject"])
                self.assertEqual(message["To"], "sre@example.test")

    def test_destination_revocation_prevents_delivery(self):
        session = Mock()
        session.__enter__ = Mock(return_value=session)
        session.__exit__ = Mock(return_value=False)
        session.scalar.return_value = None
        with patch.object(module, "SessionLocal", return_value=session), patch.object(
            module.socket, "create_connection"
        ) as connection, self.assertRaisesRegex(RuntimeError, "disabled"):
            module.send_destination(
                SimpleNamespace(channel="DEST:" + str(uuid4())),
                SimpleNamespace(organization_id=uuid4()),
            )
        connection.assert_not_called()
