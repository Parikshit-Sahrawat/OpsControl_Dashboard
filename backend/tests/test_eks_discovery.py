"""Retired EKS discovery must reject before any provider access.

Positive EKS projection/identity contracts were removed by OC-SCOPE-REM-001.
EC2 identity/endpoint controls remain covered by provider regressions.
"""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4
from fastapi import HTTPException
from app.api.discovery import source_access, capabilities
from app.security.scope import current_principal
from app.worker import provider_discovery

class EksDiscoveryTests(unittest.TestCase):
    def test_removed_provider_adapter_and_capability(self):
        self.assertFalse(hasattr(provider_discovery, 'aws_eks_candidates'))
        self.assertFalse(any(x['provider'] == 'AWS_EKS' for x in capabilities()))

    def test_even_platform_admin_cannot_discover_removed_platform(self):
        token = current_principal.set(SimpleNamespace(platform_admin=True))
        self.addCleanup(current_principal.reset, token)
        for kind in ('AWS_EKS', 'K8S', 'KUBERNETES', 'AZURE_AKS', 'GOOGLE_GKE', 'OPENSHIFT'):
            with self.subTest(kind=kind):
                db = Mock()
                db.get.return_value = SimpleNamespace(source_type=kind, enabled=True)
                with self.assertRaises(HTTPException) as denied:
                    source_access(db, uuid4())
                self.assertEqual(denied.exception.status_code, 422)

    def test_customer_admin_still_cannot_use_deployment_identity(self):
        token = current_principal.set(SimpleNamespace(platform_admin=False))
        self.addCleanup(current_principal.reset, token)
        db = Mock()
        db.get.return_value = SimpleNamespace(source_type='AWS_EC2', enabled=True)
        with self.assertRaises(HTTPException) as denied:
            source_access(db, uuid4())
        self.assertEqual(denied.exception.status_code, 403)
