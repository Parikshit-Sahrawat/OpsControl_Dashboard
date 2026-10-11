"""Infrastructure selector, native platform and evidence boundaries."""
import os,math
from types import SimpleNamespace as NS
from app.worker.infrastructure import validate_config,safe_evidence
from app.worker.deep_checks import windows_host_health,DeepCheckError
from app.worker.provider_checks import kubernetes_health,ProviderCheckError
from app.worker.collector_runtime import _extract_metric_value,CollectionResult

def denied(fn,exception=ValueError):
    try:fn()
    except exception:return
    raise AssertionError('Unsafe selector accepted')

def main():
    os.environ['OPSCONTROL_K8S_ALLOWED_NODES']='approved-node'
    denied(lambda:validate_config('KUBERNETES',{'namespace':'demo','node_name':'unapproved'}))
    denied(lambda:validate_config('KUBERNETES',{'namespace':'demo..x','pod_name':'web'}))
    denied(lambda:validate_config('LINUX_HOST',{'disk_path':'/etc','process_pid':12}))
    denied(lambda:validate_config('LINUX_HOST',{'process_pid':True}))
    denied(lambda:validate_config('AWS_EC2',{'region':'ap-south-1','account_id':'123456789012','instance_id':'i-0123456789abcdef0','endpoint_url':'https://other'}))
    denied(lambda:windows_host_health({'disk_path':'C:\\'},system='Linux'),DeepCheckError)
    node=NS(spec=NS(unschedulable=False),status=NS(conditions=[NS(type='Ready',status='True'),NS(type='MemoryPressure',status='False')]))
    client=NS(CoreV1Api=lambda:NS(read_node=lambda **kw:node))
    cfg={'namespace':'demo','node_name':'approved-node'}
    assert kubernetes_health(cfg,client)['outcome']=='SUCCESS'
    node.status.conditions[1].status='True'
    assert kubernetes_health(cfg,client)['outcome']=='DEGRADED'
    denied(lambda:kubernetes_health({**cfg,'node_name':'other'},client),ProviderCheckError)
    assert safe_evidence({'outcome':'SUCCESS','password':'hidden','token':'hidden','cpu_percent':math.nan})=={'outcome':'SUCCESS'}
    assert _extract_metric_value(NS(query_config={'extract':'HOST_CPU_PERCENT'}),CollectionResult(True,'sample',{'cpu_percent':math.inf})) is None
    print('Infrastructure selector, Node health, native Windows refusal and finite sanitized evidence PASS')
if __name__=='__main__':main()
