"""Strictly guarded read-only AWS SDK stubs for the disposable release API.

No AWS call or credential lookup is made. Stubber validates service shapes,
request parameters and read-only call order using the existing boto3 SDK.
"""
import os
import boto3
import botocore.session
from botocore.stub import Stubber

ACCOUNT='123456789012'
REGION='ap-south-1'
CLUSTERS=['sequence-eks','sequence-eks-companion']

class FixtureSession:
    def __init__(self,region_name,cluster_names=None):
        assert region_name==REGION
        self.region=region_name; self.names=cluster_names; self.clients={}; self.stubbers=[]
    def client(self,name):
        if name in self.clients: return self.clients[name]
        assert name in {'sts','eks'}
        # Ignore even the cloud environment's deliberately unusable AWS profile;
        # this fixture must never inspect real configuration or credential files.
        core=botocore.session.Session()
        store=core.get_component('config_store')
        store.set_config_variable('profile',None)
        store.set_config_variable('config_file',os.devnull)
        store.set_config_variable('credentials_file',os.devnull)
        sdk=boto3.Session(botocore_session=core,region_name=self.region,
                          aws_access_key_id='synthetic',aws_secret_access_key='synthetic')
        client=sdk.client(name)
        stub=Stubber(client)
        if name=='sts':
            stub.add_response('get_caller_identity',{'Account':ACCOUNT,'UserId':'fictional-user',
                'Arn':f'arn:aws:iam::{ACCOUNT}:user/fictional-reader'}, {})
        else:
            names=self.names or CLUSTERS
            if self.names is None:
                stub.add_response('list_clusters',{'clusters':names},{'maxResults':50})
            for cluster in names:
                stub.add_response('describe_cluster',{'cluster':{'name':cluster,
                    'arn':f'arn:aws:eks:{REGION}:{ACCOUNT}:cluster/{cluster}',
                    'status':'ACTIVE','version':'1.32',
                    'endpoint':'https://untrusted-control-plane.example.test',
                    'certificateAuthority':{'data':'synthetic-cert-not-for-output'}}},{'name':cluster})
        stub.activate(); self.clients[name]=client; self.stubbers.append(stub)
        return client
    def assert_consumed(self):
        for stub in self.stubbers: stub.assert_no_pending_responses()

def configure():
    if os.getenv('ENVIRONMENT')!='demo' or os.getenv('OPSCONTROL_RELEASE_ACCEPTANCE')!='1':
        raise RuntimeError('AWS SDK fixture is permitted only in the explicit disposable demo lab')
    from app.api import discovery
    from app.worker.provider_discovery import aws_eks_candidates
    def candidate_fixture(config):
        sessions=[]
        def factory(region_name):
            session=FixtureSession(region_name,config.get('cluster_names')); sessions.append(session); return session
        rows=aws_eks_candidates(config,session_factory=factory)
        for session in sessions: session.assert_consumed()
        return rows
    discovery.aws_eks_candidates=candidate_fixture
