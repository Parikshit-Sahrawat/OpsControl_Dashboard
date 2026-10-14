"""Read-only Carte status over real TLS in the isolated Docker test network."""
import os
import sys
from app.worker.pentaho_status import get_job_status
os.environ["OPSCONTROL_LOCAL_ALLOWED_HOSTS"]="portal.example.test"
os.environ["OPSCONTROL_LOCAL_ALLOWED_CIDRS"]="172.28.77.0/24"
config={
    "url":"https://portal.example.test",
    "job_name":"Fictional Daily Job",
    "execution_id":"test-execution-001",
    "allowed_hosts":["portal.example.test"],
    "allowed_cidrs":["172.28.77.0/24"]
}
result=get_job_status(config)
assert result["execution_status"]==sys.argv[1],result
assert result["execution_id"]=="test-execution-001",result
print("CARTE TLS READ-ONLY STATUS PASS",result)
