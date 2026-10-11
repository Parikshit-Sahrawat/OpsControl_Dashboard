"""Read-only Linux host/process and Apache/Tomcat status collectors.

No remote command execution, unrestricted URLs, JMX invocation or filesystem
reads other than the explicit Linux /proc and configured disk mount.
Services are polled through pinned TLS with independent local egress limits.
"""
import os
import re
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET
from app.worker.egress import check_target,resolve_target,policy_hosts,policy_cidrs
from app.worker.pentaho_status import _transport
from app.worker.credentials import resolve_basic_auth
import base64

class DeepCheckError(ValueError):pass

def linux_host_health(cfg):
    if not isinstance(cfg,dict) or set(cfg)-{"disk_path","process_pid"}:
        raise DeepCheckError("Only disk_path and process_pid are permitted")
    path=cfg.get("disk_path","/")
    approved={p.strip() for p in os.getenv("OPSCONTROL_HOST_ALLOWED_DISKS","/").split(",")}
    if path not in approved or not os.path.isabs(path) or ".." in path.split("/"):
        raise DeepCheckError("Disk path is not approved for this local agent")
    import time
    def cpu_ticks():
        with open('/proc/stat',encoding='ascii') as stat:
            values=[int(v) for v in stat.readline().split()[1:9]]
        return sum(values),values[3]+values[4]
    first=cpu_ticks();time.sleep(0.2);second=cpu_ticks()
    elapsed=second[0]-first[0]
    cpu_percent=round(100*(1-(second[1]-first[1])/elapsed),2) if elapsed>0 else None
    with open("/proc/meminfo",encoding="ascii") as mem:
        values={}
        for line in mem:
            match=re.match(r"^(MemTotal|MemAvailable):\s+(\d+) kB$",line.strip())
            if match:values[match.group(1)]=int(match.group(2))
    total=values.get("MemTotal",0);available=values.get("MemAvailable",0)
    if not total:raise DeepCheckError("Linux memory metrics unavailable")
    disk=os.statvfs(path)
    disk_total=disk.f_blocks*disk.f_frsize
    disk_available=disk.f_bavail*disk.f_frsize
    result={"provider":"LINUX_HOST","outcome":"SUCCESS","disk_path":path,"cpu_percent":cpu_percent,
            "memory_total_bytes":total*1024,"memory_available_bytes":available*1024,
            "memory_used_percent":round(100*(1-available/total),2),
            "disk_total_bytes":disk_total,"disk_available_bytes":disk_available,
            "disk_used_percent":round(100*(1-disk_available/disk_total),2) if disk_total else None,
            "load_1m":os.getloadavg()[0]}
    pid=cfg.get("process_pid")
    if pid is not None:
        if type(pid) is not int or not 1<=pid<=2_147_483_647:
            raise DeepCheckError("Only a positive numeric process PID is allowed")
        result["process_pid"]=pid
        try:os.kill(pid,0);result["process_running"]=True
        except ProcessLookupError:result["process_running"]=False
        except PermissionError:
            # Insufficient permission is UNKNOWN, not process DOWN.
            result["process_running"]=None
        if result["process_running"] is False:result["outcome"]="DEGRADED"
    return result

def _local_policy(cfg):
    if set(cfg)-{"url","allowed_hosts","allowed_cidrs","credential_ref"}:
        raise DeepCheckError("Unsupported status collector configuration")
    hosts=policy_hosts(cfg.get("allowed_hosts",[]))
    nets=policy_cidrs(cfg.get("allowed_cidrs",[]))
    local_hosts=policy_hosts([x.strip() for x in os.getenv("OPSCONTROL_LOCAL_ALLOWED_HOSTS","").split(",") if x.strip()])
    local_nets=policy_cidrs([x.strip() for x in os.getenv("OPSCONTROL_LOCAL_ALLOWED_CIDRS","").split(",") if x.strip()])
    if not set(hosts).issubset(local_hosts) or not all(
        any(net.subnet_of(local) for local in local_nets) for net in nets):
        raise DeepCheckError("Collector egress exceeds agent-local policy")
    parts,approved=check_target(cfg.get("url"),hosts,cfg.get("allowed_cidrs",[]))
    if parts.path not in ("","/"):
        raise DeepCheckError("Only the approved server root can be monitored")
    return parts,approved

def _fetch_status(cfg,path,transport=_transport,resolver=None,credential_resolver=resolve_basic_auth):
    parts,approved=_local_policy(cfg)
    ip=resolve_target(parts.hostname,approved,resolver) if resolver else resolve_target(parts.hostname,approved)
    basic=None
    if cfg.get("credential_ref"):
        username,password=credential_resolver(cfg["credential_ref"])
        basic=base64.b64encode((username+":"+password).encode()).decode()
    status,body=transport(parts.hostname,ip,path,basic)
    if status!=200:raise DeepCheckError("Read-only status endpoint unavailable")
    if len(body)>65536:raise DeepCheckError("Status result exceeds 64 KiB")
    return body

def apache_status(cfg,transport=_transport,resolver=None,credential_resolver=resolve_basic_auth):
    body=_fetch_status(cfg,"/server-status?auto",transport,resolver,credential_resolver)
    values={}
    approved={"Total Accesses":"total_accesses","BusyWorkers":"busy_workers",
              "IdleWorkers":"idle_workers","ReqPerSec":"requests_per_second"}
    for line in body.decode("ascii","replace").splitlines():
        if ":" not in line:continue
        key,value=(p.strip() for p in line.split(":",1))
        if key not in approved:continue
        try:values[approved[key]]=float(value)
        except ValueError:raise DeepCheckError("Invalid Apache numeric status")
    if not {"busy_workers","idle_workers"}<=values.keys():
        raise DeepCheckError("Apache mod_status lacks worker counters")
    return {"provider":"APACHE","outcome":"SUCCESS",**values}

def tomcat_status(cfg,transport=_transport,resolver=None,credential_resolver=resolve_basic_auth):
    body=_fetch_status(cfg,"/manager/status?XML=true",transport,resolver,credential_resolver)
    if b"<!DOCTYPE" in body.upper() or b"<!ENTITY" in body.upper():
        raise DeepCheckError("Unsafe Tomcat XML document")
    try:root=ET.fromstring(body)
    except ET.ParseError as exc:raise DeepCheckError("Malformed Tomcat status XML") from exc
    if root.tag!="status":raise DeepCheckError("Unexpected Tomcat status root")
    memory=root.find("./jvm/memory")
    if memory is None:raise DeepCheckError("Tomcat JVM memory unavailable")
    try:
        free=int(memory.attrib["free"]);total=int(memory.attrib["total"])
        if total<=0 or free<0 or free>total:raise ValueError()
    except (KeyError,ValueError) as exc:raise DeepCheckError("Invalid JVM memory metrics") from exc
    return {"provider":"TOMCAT","outcome":"SUCCESS",
            "jvm_heap_total_bytes":total,"jvm_heap_free_bytes":free,
            "jvm_heap_used_percent":round((total-free)*100/total,2)}


def windows_host_health(cfg, *, metrics=None, system=None):
    """Local Windows APIs via psutil; no WinRM, remote shell or arbitrary code."""
    import platform
    from app.worker.infrastructure import validate_config
    validate_config('WINDOWS_HOST',cfg)
    if (system or platform.system())!='Windows':
        raise DeepCheckError('Windows host telemetry requires a native Windows worker')
    if metrics is None:
        try: import psutil as metrics
        except ImportError as exc: raise DeepCheckError('Install optional host SDK requirements') from exc
    memory=metrics.virtual_memory()
    disk=metrics.disk_usage(cfg.get('disk_path','C:\\'))
    cpu=metrics.cpu_percent(interval=0.2)
    result={'provider':'WINDOWS_HOST','outcome':'SUCCESS','cpu_percent':cpu,
        'memory_total_bytes':memory.total,'memory_available_bytes':memory.available,
        'memory_used_percent':memory.percent,'disk_total_bytes':disk.total,
        'disk_available_bytes':disk.free,'disk_used_percent':disk.percent}
    pid=cfg.get('process_pid')
    if pid is not None:
        result['process_pid']=pid
        result['process_running']=metrics.pid_exists(pid)
        if not result['process_running']: result['outcome']='DEGRADED'
    return result
