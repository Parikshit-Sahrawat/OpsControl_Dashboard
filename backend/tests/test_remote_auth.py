"""Approved reference boundaries for remote HTTPS Basic authentication."""
import base64
import os
import unittest
from unittest.mock import patch
from app.worker import egress
from app.worker.credentials import validate_credential_reference, CredentialProviderError

class RemoteBasicAuthTests(unittest.TestCase):
    def test_unapproved_reference_is_denied_before_secret_retrieval_and_transport(self):
        with patch.dict(os.environ, {'OPSCONTROL_ALLOWED_CREDENTIAL_REFS': ''}), \
             patch.object(egress, 'resolve_target', return_value='10.20.1.4'), \
             patch('app.worker.credentials.resolve_basic_auth') as secret, \
             patch.object(egress, '_pinned_https') as transport:
            with self.assertRaises(egress.EgressDenied):
                egress.probe_https({'url': 'https://portal.example.test/ready', 'credential_ref': 'fixture'},
                    ['portal.example.test'], ['10.20.0.0/16'])
            secret.assert_not_called(); transport.assert_not_called()

    def test_approved_reference_sends_basic_only_to_pinned_verified_transport(self):
        with patch.dict(os.environ, {'OPSCONTROL_ALLOWED_CREDENTIAL_REFS': 'fixture'}), \
             patch.object(egress, 'resolve_target', return_value='10.20.1.4'), \
             patch('app.worker.credentials.resolve_basic_auth', return_value=('reader', 'synthetic-only')), \
             patch.object(egress, '_pinned_https', return_value=(200, 12)) as transport:
            result = egress.probe_https({'url': 'https://portal.example.test/ready', 'credential_ref': 'fixture'},
                ['portal.example.test'], ['10.20.0.0/16'])
            expected = 'Basic ' + base64.b64encode(b'reader:synthetic-only').decode()
            transport.assert_called_once_with('portal.example.test', '10.20.1.4', '/ready', 8, expected)
            self.assertEqual(result['outcome'], 'SUCCESS')
            self.assertNotIn('synthetic-only', str(result))

    def test_colon_account_rejected_before_transport(self):
        with patch.dict(os.environ, {'OPSCONTROL_ALLOWED_CREDENTIAL_REFS': 'fixture'}), \
             patch.object(egress, 'resolve_target', return_value='10.20.1.4'), \
             patch('app.worker.credentials.resolve_basic_auth', return_value=('bad:reader', 'synthetic-only')), \
             patch.object(egress, '_pinned_https') as transport:
            with self.assertRaises(egress.EgressDenied):
                egress.probe_https({'url': 'https://portal.example.test/ready', 'credential_ref': 'fixture'},
                    ['portal.example.test'], ['10.20.0.0/16'])
            transport.assert_not_called()

    def test_reference_validation_never_resolves_credentials(self):
        self.assertEqual(validate_credential_reference('fixture'), 'fixture')
        arn = 'aws-secretsmanager://ap-south-1/arn:aws:secretsmanager:ap-south-1:123456789012:secret:demo'
        self.assertEqual(validate_credential_reference(arn), arn)
        for invalid in ('', 'https://metadata.invalid/', arn.replace('ap-south-1/arn', 'us-east-1/arn'), None):
            with self.subTest(reference=invalid), self.assertRaises(CredentialProviderError):
                validate_credential_reference(invalid)
