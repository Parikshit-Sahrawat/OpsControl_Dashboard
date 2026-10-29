"""Infrastructure selector, native platform and evidence boundaries."""
import os,math
from types import SimpleNamespace as NS
from app.worker.infrastructure import validate_config,safe_evidence
from app.worker.deep_checks import windows_host_health,DeepCheckError
from app.worker.collector_runtime import _extract_metric_value,CollectionResult

def denied(fn,exception=ValueError):
    try:fn()
    except exception:return
    raise AssertionError('Unsafe selector accepted')

def main():
    denied(lambda:validate_config('KUBERNETES',{'namespace':'demo','node_name':'unapproved'}))
    denied(lambda:validate_config('KUBERNETES',{'namespace':'demo..x','pod_name':'web'}))
    denied(lambda:validate_config('LINUX_HOST',{'disk_path':'/etc','process_pid':12}))
    denied(lambda:validate_config('LINUX_HOST',{'process_pid':True}))
    denied(lambda:validate_config('AWS_EC2',{'region':'ap-south-1','account_id':'123456789012','instance_id':'i-0123456789abcdef0','endpoint_url':'https://other'}))
    denied(lambda:windows_host_health({'disk_path':'C:\\'},system='Linux'),DeepCheckError)
    assert safe_evidence({'outcome':'SUCCESS','password':'hidden','token':'hidden','cpu_percent':math.nan})=={'outcome':'SUCCESS'}
    assert _extract_metric_value(NS(query_config={'extract':'HOST_CPU_PERCENT'}),CollectionResult(True,'sample',{'cpu_percent':math.inf})) is None
    print('Infrastructure selector, excluded orchestration, native Windows refusal and finite sanitized evidence PASS')
if __name__=='__main__':main()
