"""Read-only EKS selectors, expected identity and untrusted response projection."""
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from app.worker.provider_checks import ProviderCheckError
from app.worker.provider_discovery import aws_eks_candidates
from scripts.eks_acceptance_fixture import FixtureSession,ACCOUNT,REGION

class EksDiscoveryTests(unittest.TestCase):
    def test_actual_sdk_stubbed_list_describe_and_safe_projection(self):
        sessions=[]
        def factory(region_name):
            session=FixtureSession(region_name); sessions.append(session); return session
        rows=aws_eks_candidates({'region':REGION,'account_id':ACCOUNT},factory)
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[0]['resource_type'],'EKS_CLUSTER')
        self.assertEqual(rows[0]['provider_status'],'ACTIVE')
        self.assertNotIn('endpoint',str(rows)); self.assertNotIn('certificate',str(rows))
        for session in sessions: session.assert_consumed()

    def test_approved_selectors_describe_without_enumeration(self):
        session=FixtureSession(REGION,['sequence-eks'])
        rows=aws_eks_candidates({'region':REGION,'account_id':ACCOUNT,'cluster_names':['sequence-eks']},
            lambda region_name:session)
        self.assertEqual(len(rows),1); session.assert_consumed()

    def test_endpoint_credentials_bad_selectors_and_limit_fail_before_sdk(self):
        base={'region':REGION,'account_id':ACCOUNT}; factory=Mock()
        for extra in ({'endpoint_url':'https://unapproved.example.test'},{'access_key_id':'synthetic'},
                      {'cluster_names':['../private']},{'cluster_names':[]},{'cluster_names':['dup','dup']},
                      {'cluster_names':'sequence-eks'},{'account_id':'bad'},{'region':'invalid'}):
            with self.subTest(extra=extra), self.assertRaises(ProviderCheckError):
                aws_eks_candidates({**base,**extra},factory)
        for limit in (0,101,True):
            with self.assertRaises(ProviderCheckError): aws_eks_candidates(base,factory,max_results=limit)
        factory.assert_not_called()

    def test_workload_account_mismatch_prevents_eks_calls(self):
        eks=Mock()
        session=SimpleNamespace(client=lambda name:SimpleNamespace(get_caller_identity=lambda:{'Account':'111111111111'}) if name=='sts' else eks)
        with self.assertRaises(ProviderCheckError):
            aws_eks_candidates({'region':REGION,'account_id':ACCOUNT},lambda region_name:session)
        eks.describe_cluster.assert_not_called(); eks.get_paginator.assert_not_called()

    def test_foreign_cluster_arn_is_rejected(self):
        client=SimpleNamespace(describe_cluster=lambda **kw:{'cluster':{'name':'sequence-eks',
            'arn':f'arn:aws:eks:{REGION}:111111111111:cluster/sequence-eks','status':'ACTIVE','version':'1.32'}})
        session=SimpleNamespace(client=lambda name:SimpleNamespace(get_caller_identity=lambda:{'Account':ACCOUNT}) if name=='sts' else client)
        with self.assertRaises(ProviderCheckError):
            aws_eks_candidates({'region':REGION,'account_id':ACCOUNT,'cluster_names':['sequence-eks']},lambda region_name:session)

    def test_provider_cluster_id_is_projected_only_when_supplied_and_valid(self):
        def candidate(value):
            client=SimpleNamespace(describe_cluster=lambda **kw:{'cluster':{'name':'sequence-eks',
                'arn':f'arn:aws:eks:{REGION}:{ACCOUNT}:cluster/sequence-eks',
                'id':value,'status':'ACTIVE','version':'1.32'}})
            session=SimpleNamespace(client=lambda name:SimpleNamespace(get_caller_identity=lambda:{'Account':ACCOUNT}) if name=='sts' else client)
            return aws_eks_candidates({'region':REGION,'account_id':ACCOUNT,
                'cluster_names':['sequence-eks']},lambda region_name:session)
        self.assertEqual(candidate('provider-cluster-1')[0]['provider_cluster_id'],
                         'provider-cluster-1')
        with self.assertRaises(ProviderCheckError): candidate('../unverified')
