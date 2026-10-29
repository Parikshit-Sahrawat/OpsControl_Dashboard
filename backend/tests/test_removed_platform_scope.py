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

class OperationalConfigurationTests(unittest.TestCase):
    def test_nested_operational_aliases_rejected_without_erasing_generic_labels(self):
        from app.services.excluded_platforms import require_supported_configuration
        for kind in ('EKS', 'AmazonElasticKubernetesService', 'AzureKubernetesService',
                     'GoogleKubernetesEngine', 'microk8s', 'K3S', 'RedHatOpenShift', 'awsEks', 'azureAks', 'gcpGke'):
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                require_supported_configuration({'wrapper':[{'collector':{'type':kind}}]})
        generic={'namespace':'payments','workload':'batch','cluster':'postgres-ha',
                 'attributes':{'k8s.namespace.name':'historical-label'}}
        self.assertEqual(require_supported_configuration(generic),generic)

    def test_legacy_source_cannot_be_relabelled_by_collector(self):
        from app.services.excluded_platforms import require_supported_collector
        from fastapi import HTTPException
        from types import SimpleNamespace
        with self.assertRaises(HTTPException) as denied:
            require_supported_collector(SimpleNamespace(collector_type='HTTP',configuration={}),
                SimpleNamespace(source_type='AWS_EKS',connection_config={}))
        self.assertEqual(denied.exception.status_code,422)

    def test_nested_source_template_and_collector_configs_are_rejected(self):
        from app.schemas.monitoring import MonitoringTemplateCreate, CollectorCreate, DataSourceUpdate
        factories=(lambda:MonitoringTemplateCreate(name='nested',package_config={'collector':{'type':'GKE'}}),
                   lambda:CollectorCreate(name='nested',collector_type='HTTP',data_source_id=uuid4(),configuration={'nested':{'provider':'AKS'}}),
                   lambda:DataSourceUpdate(connection_config={'opscontrol':{'monitoring_overrides':{'collector':{'type':'K8S'}}}}))
        for factory in factories:
            with self.assertRaises(ValidationError):factory()

    def test_configuration_depth_is_bounded(self):
        from app.services.excluded_platforms import require_supported_configuration
        value={}
        for _ in range(22):value={'nested':value}
        with self.assertRaises(ValueError):require_supported_configuration(value)
