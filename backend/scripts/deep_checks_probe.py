"""Offline read-only Apache/Tomcat host telemetry acceptance; no real endpoints."""
import os,socket
from app.worker.deep_checks import linux_host_health,apache_status,tomcat_status,DeepCheckError

def denied(callback):
    try:callback()
    except (ValueError,DeepCheckError):return
    raise AssertionError("Dangerous collector configuration accepted")

def dns(*args,**kwargs):
    return [(socket.AF_INET,socket.SOCK_STREAM,6,"",("10.20.0.15",443))]

def main():
    host=linux_host_health({"disk_path":"/","process_pid":os.getpid()})
    assert host["outcome"]=="SUCCESS" and host["process_running"] is True
    assert 0<=host["memory_used_percent"]<=100 and host["disk_total_bytes"]>0
    missing=linux_host_health({"disk_path":"/","process_pid":2_000_000_000})
    assert missing["outcome"]=="DEGRADED" and missing["process_running"] is False
    denied(lambda:linux_host_health({"disk_path":"/etc/passwd"}))
    denied(lambda:linux_host_health({"shell":"rm -rf /"}))
    os.environ["OPSCONTROL_LOCAL_ALLOWED_HOSTS"]="portal.example.test"
    os.environ["OPSCONTROL_LOCAL_ALLOWED_CIDRS"]="10.20.0.0/16"
    cfg={"url":"https://portal.example.test","allowed_hosts":["portal.example.test"],
         "allowed_cidrs":["10.20.0.0/16"]}
    def apache_transport(host,ip,path,basic):
        assert (host,ip,path,basic)==("portal.example.test","10.20.0.15","/server-status?auto",None)
        return 200,b"Total Accesses: 521\nBusyWorkers: 3\nIdleWorkers: 17\nReqPerSec: .5\n"
    result=apache_status(cfg,transport=apache_transport,resolver=dns)
    assert result["busy_workers"]==3 and result["idle_workers"]==17
    def tomcat_transport(host,ip,path,basic):
        assert (host,ip,path,basic)==("portal.example.test","10.20.0.15","/manager/status?XML=true",None)
        return 200,b'<status><jvm><memory free="300" total="1000" max="2000"/></jvm></status>'
    jvm=tomcat_status(cfg,transport=tomcat_transport,resolver=dns)
    assert jvm["jvm_heap_used_percent"]==70
    denied(lambda:apache_status({**cfg,"allowed_hosts":["evil.example.test"]},transport=apache_transport,resolver=dns))
    denied(lambda:tomcat_status({**cfg,"url":"http://portal.example.test"},transport=tomcat_transport,resolver=dns))
    denied(lambda:tomcat_status(cfg,transport=lambda *args:(200,b'<!DOCTYPE foo><status/>'),resolver=dns))
    print("READ-ONLY LINUX HOST, APACHE, TOMCAT ADAPTER TESTS PASS")

if __name__=="__main__":main()
