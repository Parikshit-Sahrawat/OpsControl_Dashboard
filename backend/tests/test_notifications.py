"""Fail-closed configuration and untrusted provider response boundaries."""
from io import BytesIO
import json
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from app.core.config import settings
from app.worker import notifications as n

class Response(BytesIO):
    status=200

class NotificationSecurityTests(unittest.TestCase):
    def test_production_rejects_environment_servicenow_password(self):
        env={'OPSCONTROL_SERVICENOW_URL':'https://snow.example.test',
             'OPSCONTROL_SERVICENOW_CREDENTIAL_REF':'','OPSCONTROL_SERVICENOW_USERNAME':'reader',
             'OPSCONTROL_SERVICENOW_PASSWORD':'synthetic-only'}
        with patch.dict(os.environ,env), patch.object(settings,'environment','production'):
            with self.assertRaises(RuntimeError): n._servicenow_config()

    def test_fixed_https_origin_and_identifier_validation_before_credentials(self):
        env={'OPSCONTROL_SERVICENOW_CREDENTIAL_REF':'','OPSCONTROL_SERVICENOW_USERNAME':'reader',
             'OPSCONTROL_SERVICENOW_PASSWORD':'synthetic-only'}
        for url in ('http://snow.example.test','https://reader:private@snow.example.test',
                    'https://snow.example.test/path','https://snow.example.test/?query=x'):
            with self.subTest(url=url), patch.dict(os.environ,{**env,'OPSCONTROL_SERVICENOW_URL':url}):
                with self.assertRaises(RuntimeError): n._servicenow_config()
        with patch.dict(os.environ,{**env,'OPSCONTROL_SERVICENOW_URL':'https://snow.example.test',
                                   'OPSCONTROL_SERVICENOW_TABLE':'incident^ORactive=true'}):
            with self.assertRaises(RuntimeError): n._servicenow_config()

    def test_untrusted_provider_envelope_size_and_duplicate_fields(self):
        for payload in (b'not-json',b'[]',b'{}',b'{"result":[],"result":[]}',b'x'*8193):
            with self.subTest(bytes=len(payload)), patch.object(n,'_notification_open',return_value=Response(payload)):
                with self.assertRaises((RuntimeError,ValueError)):
                    n._servicenow_request('https://snow.example.test/api/now/table/incident','GET',{})
        with patch.object(n,'_notification_open',return_value=Response(b'{"result":[]}')):
            self.assertEqual(n._servicenow_request('https://snow.example.test/api/now/table/incident','GET',{}),[])

    def test_incident_reference_cannot_be_missing_number_or_path(self):
        for result in ({}, {'number':'INC001'}, {'sys_id':'../../private'}, {'sys_id':None}, []):
            with self.subTest(result=result), self.assertRaises(RuntimeError): n._servicenow_sys_id(result)
        self.assertEqual(n._servicenow_sys_id({'sys_id':'a'*32}),'a'*32)

    def test_provider_error_evidence_never_contains_body_url_or_secret(self):
        error=HTTPError('https://snow.example.test/?secret=synthetic-private',503,
                        'synthetic-private',{},BytesIO(b'synthetic-private'))
        self.assertEqual(n._safe_delivery_error(error),'Notification provider HTTP 503')
        self.assertNotIn('synthetic-private',n._safe_delivery_error(RuntimeError('synthetic-private')))
