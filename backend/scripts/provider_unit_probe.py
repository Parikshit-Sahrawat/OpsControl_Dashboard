"""Offline unit tests: no credentials, AWS calls or Kubernetes cluster needed."""
import os
from datetime import datetime,timezone
from types import SimpleNamespace as NS
from unittest.mock import Mock
from app.worker.provider_checks import ec2_health,kubernetes_health,ProviderCheckError
from app.worker.pentaho_status import get_job_status,parse_carte_status,PentahoStatusError

def denied(fn,exception=ValueError):
    try: fn()
    except exception: return
    raise AssertionError("Unsafe or invalid provider config accepted")

def aws_session(region_name):
    assert region_name=="ap-south-1"
    def client(name):
        if name=="sts": return NS(get_caller_identity=lambda:{"Account":"123456789012"})
        if name=="ec2":
            return NS(describe_instances=lambda **kw:{"Reservations":[{"Instances":[
                {"InstanceId":"i-0123456789abcdef0","State":{"Name":"running"}}]}]},
                describe_instance_status=lambda **kw:{"InstanceStatuses":[{
                    "InstanceId":"i-0123456789abcdef0",
                    "SystemStatus":{"Status":"ok"},"InstanceStatus":{"Status":"ok"}}]})
        if name=="cloudwatch":
            return NS(get_metric_statistics=lambda **kw:{"Datapoints":[{
                "Timestamp":datetime.now(timezone.utc),"Average":19.75}]})
        raise AssertionError("Unexpected cloud SDK")
    return NS(client=client)

def test_aws():
    config={"region":"ap-south-1","instance_id":"i-0123456789abcdef0","account_id":"123456789012"}
    status=ec2_health(config,aws_session)
    assert status["outcome"]=="SUCCESS" and status["cpu_percent"]==19.75
    denied(lambda:ec2_health({**config,"region":"unsafe.invalid"},aws_session),ProviderCheckError)
    denied(lambda:ec2_health({**config,"endpoint_url":"http://169.254.169.254"},aws_session),ProviderCheckError)
    denied(lambda:ec2_health({**config,"access_key_id":"secret"},aws_session),ProviderCheckError)
    denied(lambda:ec2_health({**config,"account_id":"111111111111"},aws_session),ProviderCheckError)

def test_k8s():
    pod=NS(status=NS(phase="Running",conditions=[NS(type="Ready",status="True")],
                     container_statuses=[NS(restart_count=3,state=NS(waiting=None))]))
    dep=NS(spec=NS(replicas=3),status=NS(ready_replicas=2,available_replicas=2))
    api=NS(CoreV1Api=lambda:NS(read_namespaced_pod=lambda **kwargs:pod),
           AppsV1Api=lambda:NS(read_namespaced_deployment=lambda **kwargs:dep))
    result=kubernetes_health({"namespace":"demo","pod_name":"web-0"},api)
    assert result["outcome"]=="SUCCESS" and result["restarts"]==3
    degraded=kubernetes_health({"namespace":"demo","deployment_name":"frontend"},api)
    assert degraded["outcome"]=="DEGRADED" and degraded["available_replicas"]==2
    denied(lambda:kubernetes_health({"namespace":"../secrets","pod_name":"web-0"},api),ProviderCheckError)
    denied(lambda:kubernetes_health({"namespace":"demo","pod_name":"web-0","server":"https://elsewhere"},api),ProviderCheckError)
    denied(lambda:kubernetes_health({"namespace":"demo","pod_name":"web-0","deployment_name":"frontend"},api),ProviderCheckError)

def test_pentaho():
    sample=b"<job_status><id>execution-0001</id><status_desc>Finished</status_desc><result><nr_errors>0</nr_errors></result></job_status>"
    parsed=parse_carte_status(sample)
    assert parsed["execution_status"]=="SUCCESS" and parsed["nr_errors"]==0
    fail=parse_carte_status(sample.replace(b"<nr_errors>0",b"<nr_errors>2"))
    assert fail["execution_status"]=="FAILED"
    denied(lambda:parse_carte_status(b'<!DOCTYPE foo [ <!ENTITY x "y"> ]><job_status/>'),PentahoStatusError)
    os.environ["OPSCONTROL_LOCAL_ALLOWED_HOSTS"]="carte.example.test"
    os.environ["OPSCONTROL_LOCAL_ALLOWED_CIDRS"]="10.20.0.0/16"
    cfg={"url":"https://carte.example.test","job_name":"Hourly ETL","execution_id":"execution-0001",
         "allowed_hosts":["carte.example.test"],"allowed_cidrs":["10.20.0.0/16"]}
    def fake_transport(host,ip,path,authorization):
        assert host=="carte.example.test" and ip=="10.20.1.4"
        assert path.startswith("/kettle/jobStatus/?name=Hourly%20ETL")
        assert "xml=Y" in path
        assert authorization is None
        return 200,sample
    def fake_dns(*args,**kw):
        import socket
        return [(socket.AF_INET,socket.SOCK_STREAM,6,"",("10.20.1.4",443))]
    result=get_job_status(cfg,transport=fake_transport,resolver=fake_dns)
    assert result["execution_status"]=="SUCCESS"
    denied(lambda:get_job_status({**cfg,"allowed_hosts":["evil.example.test"]},
        transport=fake_transport,resolver=fake_dns),PentahoStatusError)
    denied(lambda:get_job_status({**cfg,"url":"http://carte.example.test"},
        transport=fake_transport,resolver=fake_dns),ValueError)

if __name__=="__main__":
    test_aws();test_k8s();test_pentaho()
    print("EC2 / KUBERNETES / PENTAHO READ-ONLY PROVIDER UNIT TESTS PASS")
