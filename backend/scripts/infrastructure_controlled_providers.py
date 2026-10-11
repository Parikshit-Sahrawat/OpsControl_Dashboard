"""Explicit acceptance-only adapters: SDK stub EC2, TLS fixture K8s, Windows fake.

Application code never enables these automatically. Installed only in the
controlled sprint acceptance process, with evidence origin clearly recorded.
"""
import os
from datetime import datetime,timezone
from pathlib import Path
from types import SimpleNamespace as NS
import boto3
from botocore.stub import Stubber,ANY
from kubernetes import client
from app.worker.provider_checks import ec2_health,kubernetes_health
from app.worker.deep_checks import windows_host_health
from app.worker.collector_runtime import CollectorAdapter,CollectionResult


def aws_session(region_name):
    session=boto3.Session(region_name=region_name,aws_access_key_id='controlled-fixture',aws_secret_access_key='controlled-fixture')
    clients={}
    phase=Path(os.environ['INFRA_PRIVATE_DIR'],'phase').read_text().strip()
    for name in ('sts','ec2','cloudwatch'):
        sdk=session.client(name);stub=Stubber(sdk)
        if name=='sts':stub.add_response('get_caller_identity',{'Account':'123456789012','Arn':'arn:aws:iam::123456789012:role/controlled-fixture','UserId':'fixture-reader'})
        if name=='ec2':
            stub.add_response('describe_instances',{'Reservations':[{'Instances':[{'InstanceId':'i-0123456789abcdef0','State':{'Name':'running'}}]}]})
            stub.add_response('describe_instance_status',{'InstanceStatuses':[{'InstanceId':'i-0123456789abcdef0','SystemStatus':{'Status':'ok'},'InstanceStatus':{'Status':'ok'}}]})
        if name=='cloudwatch':stub.add_response('get_metric_statistics',{'Datapoints':[{'Timestamp':datetime.now(timezone.utc),'Average':95.0 if phase=='failed' else 19.75}]},
            {'Namespace':'AWS/EC2','MetricName':'CPUUtilization','Dimensions':[{'Name':'InstanceId','Value':'i-0123456789abcdef0'}],'StartTime':ANY,'EndTime':ANY,'Period':300,'Statistics':['Average']})
        stub.activate();clients[name]=sdk
    return NS(client=lambda name:clients[name])


def kube_client():
    root=Path(os.environ['INFRA_PRIVATE_DIR'])
    configuration=client.Configuration();configuration.host='https://127.0.0.1:18443'
    configuration.ssl_ca_cert=str(root/'tls.crt');configuration.verify_ssl=True
    configuration.api_key={'authorization':'Bearer '+(root/'kube-token').read_text().strip()}
    configuration.proxy=None
    api=client.ApiClient(configuration)
    return NS(CoreV1Api=lambda:client.CoreV1Api(api),AppsV1Api=lambda:client.AppsV1Api(api))

class EC2Controlled(CollectorAdapter):
    async def collect(self,collector):
        payload=ec2_health(collector.configuration,aws_session)
        return CollectionResult(payload['outcome']=='SUCCESS','Controlled EC2 SDK evidence',payload)
class K8sControlled(CollectorAdapter):
    async def collect(self,collector):
        payload=kubernetes_health(collector.configuration,kube_client())
        return CollectionResult(payload['outcome']=='SUCCESS','Controlled TLS Kubernetes evidence',payload)
class WindowsControlled(CollectorAdapter):
    async def collect(self,collector):
        failed=Path(os.environ['INFRA_PRIVATE_DIR'],'phase').read_text().strip()=='failed'
        metrics=NS(virtual_memory=lambda:NS(total=16000000000,available=8000000000,percent=50.0),
            disk_usage=lambda path:NS(total=100000000000,free=75000000000,percent=25.0),
            cpu_percent=lambda interval:20.0,pid_exists=lambda pid:not failed)
        previous=os.environ.get('OPSCONTROL_HOST_ALLOWED_DISKS')
        os.environ['OPSCONTROL_HOST_ALLOWED_DISKS']='C:\\'
        try:payload=windows_host_health(collector.configuration,metrics=metrics,system='Windows')
        finally:
            if previous is None:os.environ.pop('OPSCONTROL_HOST_ALLOWED_DISKS',None)
            else:os.environ['OPSCONTROL_HOST_ALLOWED_DISKS']=previous
        return CollectionResult(payload['outcome']=='SUCCESS','Controlled Windows SDK evidence',payload)
