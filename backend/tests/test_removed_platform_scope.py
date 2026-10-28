import unittest
from uuid import uuid4
from pydantic import ValidationError
from app.schemas.monitoring import DataSourceCreate, CollectorCreate
from app.api.resource_management import router
from app.api.discovery import capabilities
from app.worker.collector_runtime import ADAPTERS

class RemovedPlatformTests(unittest.TestCase):
    def test_no_cluster_routes_or_capabilities(self):
        self.assertFalse(any('kubernetes' in r.path for r in router.routes))
        self.assertFalse({'KUBERNETES', 'K8S', 'AWS_EKS'} & set(ADAPTERS))
        self.assertEqual({v['provider'] for v in capabilities()}, {'AWS_EC2','HTTP','PENTAHO'})
    def test_removed_source_inputs_rejected(self):
        for provider in ['KUBERNETES','K8S','AWS_EKS','AZURE_AKS','GKE','OPENSHIFT']:
            with self.subTest(provider=provider), self.assertRaises(ValidationError):
                DataSourceCreate(name='synthetic',organization_id=uuid4(),source_type=provider)
    def test_supported_source_inputs_preserved(self):
        for provider in ['AWS_EC2','LINUX_HOST','WINDOWS_HOST','HTTP','PENTAHO']:
            self.assertEqual(DataSourceCreate(name='synthetic',organization_id=uuid4(),source_type=provider).source_type,provider)
