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
