"""Provider-neutral read-only inventory discovery, using workload identity only.

No network scanning, caller-defined provider endpoints, credential keys,
cluster-wide Kubernetes enumeration or automatic monitoring activation.
"""
import re
from datetime import datetime,timezone
from app.worker.provider_checks import ProviderCheckError,_AWS_REGION,_AWS_INSTANCE,_DNS_LABEL

def aws_ec2_candidates(config,session_factory=None,max_results=100):
    allowed={"region","account_id"}
    if not isinstance(config,dict) or set(config)-allowed:
        raise ProviderCheckError("AWS discovery requires approved region and account only")
    region=config.get("region","")
    account=config.get("account_id","")
    if not isinstance(region,str) or not _AWS_REGION.fullmatch(region):
        raise ProviderCheckError("Invalid AWS discovery region")
    if not isinstance(account,str) or not re.fullmatch(r"\d{12}",account):
        raise ProviderCheckError("AWS account ID required")
    client_options = {}
    if session_factory is None:
        try: import boto3
        except ImportError as exc: raise ProviderCheckError("Install optional boto3 SDK") from exc
        session_factory=boto3.Session
        from botocore.config import Config
        client_options['config'] = Config(connect_timeout=5, read_timeout=15, retries={'total_max_attempts': 2})
    session=session_factory(region_name=region)
    if session.client("sts", **client_options).get_caller_identity().get("Account")!=account:
        raise ProviderCheckError("AWS workload identity/account mismatch")
    client=session.client("ec2", **client_options)
    paginator=client.get_paginator("describe_instances")
    output=[]
    for page in paginator.paginate(PaginationConfig={"PageSize":50}):
        for reservation in page.get("Reservations",[]):
            for instance in reservation.get("Instances",[]):
                instance_id=instance.get("InstanceId","")
                if not isinstance(instance_id,str) or not _AWS_INSTANCE.fullmatch(instance_id):continue
                output.append({"external_id":f"aws:{account}:{region}:{instance_id}",
                    "resource_type":"EC2_INSTANCE","instance_id":instance_id,
                    "region":region,"account_id":account,
                    "state":instance.get("State",{}).get("Name","unknown")})
                if len(output)>=max_results:return output
    return output

def k8s_pod_candidates(config,client_factory=None,max_results=100):
    if not isinstance(config,dict) or set(config)-{"namespace","resource_types","approved_nodes"}:
        raise ProviderCheckError("Kubernetes discovery requires one approved namespace")
    namespace=config.get("namespace","")
    if not isinstance(namespace,str) or not _DNS_LABEL.fullmatch(namespace):
        raise ProviderCheckError("Invalid namespace")
    if client_factory is None:
        try:
            from kubernetes import client,config as kconfig
        except ImportError as exc:raise ProviderCheckError("Install optional Kubernetes SDK") from exc
        kconfig.load_incluster_config()  # cluster-scoped kubeconfig explicitly forbidden
        client_factory=client
    kinds=config.get('resource_types',['POD'])
    if not isinstance(kinds,list) or not kinds or set(kinds)-{'POD','DEPLOYMENT','NODE'}:
        raise ProviderCheckError('Choose approved Pod, Deployment or Node resource types')
    nodes=config.get('approved_nodes',[])
    if 'NODE' in kinds:
        import os
        allowed=os.getenv('OPSCONTROL_K8S_ALLOWED_NODES','').split(',')
        if not isinstance(nodes,list) or not nodes or any(n not in allowed for n in nodes):
            raise ProviderCheckError('Node discovery requires explicitly approved node names')
    # Namespace RBAC supplied by the authorized service account. The API cannot
    # escalate to cluster-wide listing or accept an arbitrary control-plane URL.
    result=client_factory.CoreV1Api().list_namespaced_pod(namespace=namespace,
        limit=min(max_results,100), _request_timeout=(5, 15)) if "POD" in kinds else type("Empty",(),{"items":[]})()
    output=[]
    for pod in result.items[:max_results]:
        if not pod.metadata or not pod.metadata.uid or not pod.metadata.name:continue
        output.append({"external_id":f"k8s:{namespace}:{pod.metadata.uid}",
            "resource_type":"K8S_POD","namespace":namespace,
            "pod_name":pod.metadata.name,"uid":str(pod.metadata.uid),
            "phase":pod.status.phase if pod.status else "Unknown"})
    if 'DEPLOYMENT' in kinds:
        deployments=client_factory.AppsV1Api().list_namespaced_deployment(namespace=namespace,limit=min(max_results,100), _request_timeout=(5, 15))
        for deployment in deployments.items:
            if len(output)>=max_results:break
            output.append({'external_id':f'k8s:{namespace}:deployment:{deployment.metadata.uid}',
                'resource_type':'K8S_DEPLOYMENT','namespace':namespace,
                'deployment_name':deployment.metadata.name,'uid':str(deployment.metadata.uid)})
    if 'NODE' in kinds:
        for name in nodes:
            if len(output)>=max_results:break
            node=client_factory.CoreV1Api().read_node(name=name, _request_timeout=(5, 15))
            output.append({'external_id':f'k8s:node:{node.metadata.uid}',
                'resource_type':'K8S_NODE','namespace':namespace,'node_name':node.metadata.name,
                'uid':str(node.metadata.uid)})
    return output
