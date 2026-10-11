"""Explicit infrastructure capabilities, safe configs and bounded evidence fields."""
import math
import ntpath
import os
import re

INFRA_TYPES={'AWS_EC2','EC2','KUBERNETES','K8S','LINUX_HOST','WINDOWS_HOST'}
ALIASES={'EC2':'AWS_EC2','K8S':'KUBERNETES'}
METRICS={
    'infrastructure_up':('AVAILABILITY',None),
    'cpu_percent':('HOST_CPU_PERCENT','percent'),
    'memory_used_percent':('HOST_MEMORY_USED_PERCENT','percent'),
    'disk_used_percent':('HOST_DISK_USED_PERCENT','percent'),
    'process_running':('HOST_PROCESS_RUNNING',None),
    'ec2_cpu_percent':('EC2_CPU_PERCENT','percent'),
    'k8s_restarts':('K8S_RESTARTS','count'),
    'k8s_available_replicas':('K8S_AVAILABLE_REPLICAS','count'),
    'k8s_node_ready':('K8S_NODE_READY',None),
}
PROVIDER_METRICS={
    'AWS_EC2':{'infrastructure_up','ec2_cpu_percent'},
    'KUBERNETES':{'infrastructure_up','k8s_restarts','k8s_available_replicas','k8s_node_ready'},
    'LINUX_HOST':{'infrastructure_up','cpu_percent','memory_used_percent','disk_used_percent','process_running'},
    'WINDOWS_HOST':{'infrastructure_up','cpu_percent','memory_used_percent','disk_used_percent','process_running'},
}
SAFE_FIELDS={'provider','outcome','instance_id','region','state','system_checks','cpu_percent',
    'resource','namespace','name','phase','ready','restarts','desired_replicas','ready_replicas',
    'available_replicas','node_ready','memory_pressure','disk_pressure','pid_pressure','unschedulable',
    'memory_total_bytes','memory_available_bytes','memory_used_percent','disk_total_bytes',
    'disk_available_bytes','disk_used_percent','load_1m','process_pid','process_running'}


def normalize(kind): return ALIASES.get(kind.upper(),kind.upper())


def validate_config(kind,cfg):
    kind=normalize(kind)
    if not isinstance(cfg,dict): raise ValueError('Infrastructure config must be an object')
    if kind=='AWS_EC2':
        if set(cfg)-{'region','account_id','instance_id'}: raise ValueError('Only approved AWS identity and instance selectors allowed')
        if not re.fullmatch(r'[a-z]{2}(?:-gov)?-[a-z]+-\d',str(cfg.get('region',''))): raise ValueError('Explicit AWS region required')
        if not re.fullmatch(r'\d{12}',str(cfg.get('account_id',''))): raise ValueError('Expected AWS account required')
        if not re.fullmatch(r'i-[0-9a-f]{8,17}',str(cfg.get('instance_id',''))): raise ValueError('Explicit EC2 instance required')
    elif kind=='KUBERNETES':
        if set(cfg)-{'namespace','pod_name','deployment_name','node_name'}: raise ValueError('Unapproved Kubernetes config key')
        names=[cfg.get(key) for key in ('pod_name','deployment_name','node_name') if cfg.get(key)]
        if len(names)!=1: raise ValueError('Choose exactly one Pod, Deployment or Node')
        label=r'[a-z0-9](?:[-a-z0-9]{0,61}[a-z0-9])?'
        namespace=cfg.get('namespace','')
        if not isinstance(namespace,str) or not re.fullmatch(label,namespace): raise ValueError('Invalid Kubernetes namespace')
        for name in names:
            if not isinstance(name,str) or len(name)>253 or not all(re.fullmatch(label,part) for part in name.split('.')): raise ValueError('Invalid Kubernetes selector')
        if cfg.get('node_name') and cfg['node_name'] not in os.getenv('OPSCONTROL_K8S_ALLOWED_NODES','').split(','):
            raise ValueError('Node is not explicitly approved for this worker')
    elif kind in {'LINUX_HOST','WINDOWS_HOST'}:
        if set(cfg)-{'disk_path','process_pid'}: raise ValueError('Only local disk and numeric process selectors allowed')
        path=cfg.get('disk_path','C:\\' if kind=='WINDOWS_HOST' else '/')
        path_module=ntpath if kind=='WINDOWS_HOST' else os.path
        default='C:\\' if kind=='WINDOWS_HOST' else '/'
        if path not in os.getenv('OPSCONTROL_HOST_ALLOWED_DISKS',default).split(',') or not path_module.isabs(path) or '..' in path.replace('\\','/').split('/'):
            raise ValueError('Local disk path not approved')
        pid=cfg.get('process_pid')
        if pid is not None and (type(pid) is not int or not 1<=pid<=2147483647): raise ValueError('Positive numeric PID required')
    else: raise ValueError('Unsupported infrastructure provider')
    return dict(cfg)


def safe_evidence(payload):
    result={}
    for key,value in (payload or {}).items():
        if key not in SAFE_FIELDS: continue
        if value is None or type(value) is bool: result[key]=value
        elif isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value): result[key]=value
        elif isinstance(value,str): result[key]=value[:253]
    return result
