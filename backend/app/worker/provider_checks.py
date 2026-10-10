"""Read-only, provider-neutral cloud/K8s/ETL health collectors.

No static cloud credentials, AssumeRole, arbitrary kubeconfig, arbitrary HTTP
methods or private endpoint overrides. SDK credentials come from workload
identity (IAM role/service account) in approved deployments.
"""
import re
from datetime import datetime,timedelta,timezone

class ProviderCheckError(ValueError): pass

_AWS_REGION=re.compile(r"^[a-z]{2}(?:-gov)?-[a-z]+-\d$")
_AWS_INSTANCE=re.compile(r"^i-[0-9a-f]{8,17}$")
_DNS_LABEL=re.compile(r"^[a-z0-9](?:[-a-z0-9]{0,61}[a-z0-9])?$")

def ec2_health(config,session_factory=None):
    if not isinstance(config,dict): raise ProviderCheckError("EC2 configuration must be an object")
    if set(config)-{"region","instance_id","account_id"}:
        raise ProviderCheckError("Unapproved EC2 configuration key")
    region=config.get("region","")
    instance=config.get("instance_id","")
    account=config.get("account_id","")
    if not isinstance(region,str) or not _AWS_REGION.fullmatch(region):
        raise ProviderCheckError("AWS region must be explicitly configured")
    if not isinstance(instance,str) or not _AWS_INSTANCE.fullmatch(instance):
        raise ProviderCheckError("Valid EC2 instance ID required")
    if not isinstance(account,str) or not re.fullmatch(r"\d{12}",account):
        raise ProviderCheckError("12-digit expected AWS account ID required")
    if session_factory is None:
        try: import boto3
        except ImportError as exc:
            raise ProviderCheckError("Install optional provider SDK requirements") from exc
        session_factory=boto3.Session
    # Never permit a caller-provided endpoint, access key, profile or role ARN.
    session=session_factory(region_name=region)
    sts=session.client("sts")
    if sts.get_caller_identity().get("Account")!=account:
        raise ProviderCheckError("Workload identity does not match approved AWS account")
    ec2=session.client("ec2")
    describe=ec2.describe_instances(InstanceIds=[instance])
    rows=[entry for reservation in describe.get("Reservations",[])
          for entry in reservation.get("Instances",[])
          if entry.get("InstanceId")==instance]
    if len(rows)!=1: raise ProviderCheckError("EC2 instance not returned")
    state=rows[0].get("State",{}).get("Name","unknown")
    # API status-check evidence is separate from lifecycle state.
    checks=ec2.describe_instance_status(InstanceIds=[instance],IncludeAllInstances=True)
    statuses=checks.get("InstanceStatuses",[])
    check_value="unknown"
    if statuses:
        record=statuses[0]
        if record.get("InstanceId")==instance:
            system=record.get("SystemStatus",{}).get("Status","unknown")
            instance_status=record.get("InstanceStatus",{}).get("Status","unknown")
            check_value="ok" if system==instance_status=="ok" else "impaired" if "impaired" in (system,instance_status) else "unknown"
    cloudwatch=session.client("cloudwatch")
    now=datetime.now(timezone.utc)
    metric=cloudwatch.get_metric_statistics(
        Namespace="AWS/EC2",MetricName="CPUUtilization",
        Dimensions=[{"Name":"InstanceId","Value":instance}],
        StartTime=now-timedelta(minutes=10),EndTime=now,Period=300,Statistics=["Average"])
    candidates=sorted(metric.get("Datapoints",[]),key=lambda x:x["Timestamp"],reverse=True)
    cpu=float(candidates[0]["Average"]) if candidates else None
    return {"provider":"AWS_EC2","instance_id":instance,"region":region,
            "state":state,"system_checks":check_value,"cpu_percent":cpu,
            "outcome":"SUCCESS" if state=="running" and check_value=="ok" else
                      "DEGRADED" if state=="running" else "UNAVAILABLE"}

def kubernetes_health(config,client_factory=None):
    if not isinstance(config,dict): raise ProviderCheckError("Kubernetes config must be JSON")
    if set(config)-{"namespace","pod_name","deployment_name"}:
        raise ProviderCheckError("Unapproved Kubernetes configuration key")
    namespace=config.get("namespace","")
    pod=config.get("pod_name")
    deployment=config.get("deployment_name")
    if not isinstance(namespace,str) or not _DNS_LABEL.fullmatch(namespace):
        raise ProviderCheckError("Namespace must be explicit")
    if bool(pod)==bool(deployment):
        raise ProviderCheckError("Choose exactly one Pod or Deployment")
    name=pod or deployment
    if not isinstance(name,str) or not _DNS_LABEL.fullmatch(name):
        raise ProviderCheckError("Invalid Pod/Deployment name")
    if client_factory is None:
        try:
            from kubernetes import client
        except ImportError as exc:
            raise ProviderCheckError("Install optional Kubernetes client") from exc
        from kubernetes import config as kconfig
        kconfig.load_incluster_config()  # service-account only; no arbitrary kubeconfig
        client_factory=client
    if pod:
        obj=client_factory.CoreV1Api().read_namespaced_pod(name=name,namespace=namespace)
        status=obj.status
        phase=status.phase or "Unknown"
        ready=any(c.type=="Ready" and c.status=="True" for c in (status.conditions or []))
        restarts=sum(c.restart_count or 0 for c in (status.container_statuses or []))
        waiting=[c.state.waiting.reason for c in (status.container_statuses or [])
                 if c.state and c.state.waiting and c.state.waiting.reason]
        outcome="SUCCESS" if phase=="Running" and ready else "DEGRADED"
        return {"provider":"KUBERNETES","resource":"POD","namespace":namespace,
                "name":name,"phase":phase,"ready":ready,"restarts":restarts,
                "waiting_reasons":waiting[:10],"outcome":outcome}
    obj=client_factory.AppsV1Api().read_namespaced_deployment(name=name,namespace=namespace)
    status=obj.status
    desired=int(obj.spec.replicas or 0)
    ready=int(status.ready_replicas or 0)
    available=int(status.available_replicas or 0)
    return {"provider":"KUBERNETES","resource":"DEPLOYMENT","namespace":namespace,
            "name":name,"desired_replicas":desired,"ready_replicas":ready,
            "available_replicas":available,
            "outcome":"SUCCESS" if desired>0 and available>=desired else "DEGRADED"}
