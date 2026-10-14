"""Provider failures remain typed and never expose provider-secret diagnostics."""

import unittest
from botocore.exceptions import ClientError, NoCredentialsError, EndpointConnectionError
from app.pipeline_adapters.core import provider_error


class ProviderFailureTests(unittest.TestCase):
    def test_official_sdk_error_categories_and_redacted_messages(self):
        cases = {
            "AccessDeniedException": "AUTHENTICATION",
            "ExpiredTokenException": "AUTHENTICATION",
            "ThrottlingException": "THROTTLED",
            "TooManyRequestsException": "THROTTLED",
            "EntityNotFoundException": "CONFIGURATION",
            "InvalidInputException": "CONFIGURATION",
            "InternalServiceException": "PROVIDER",
        }
        for code, expected in cases.items():
            with self.subTest(code=code):
                error = ClientError(
                    {"Error": {"Code": code, "Message": "provider-private-diagnostic"}},
                    "GetJobRuns",
                )
                result = provider_error(error)
                self.assertEqual(result.kind, expected)
                self.assertNotIn("provider-private-diagnostic", str(result))

    def test_missing_identity_and_connection_failures_are_distinct(self):
        for error, expected in (
            (NoCredentialsError(), "AUTHENTICATION"),
            (
                EndpointConnectionError(endpoint_url="https://private-provider.test"),
                "NETWORK",
            ),
            (Exception("28000", "credential-private-diagnostic"), "AUTHENTICATION"),
            (Exception("08001", "connection-private-diagnostic"), "NETWORK"),
            (Exception("unknown-private-diagnostic"), "PROVIDER"),
        ):
            with self.subTest(expected=expected):
                result = provider_error(error)
                self.assertEqual(result.kind, expected)
                self.assertNotIn("private-diagnostic", str(result))
