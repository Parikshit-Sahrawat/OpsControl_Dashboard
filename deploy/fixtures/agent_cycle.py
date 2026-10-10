"""Single remote agent claim+execution in dual, isolated Docker networks."""
import os
from app.worker.egress import policy_cidrs,policy_hosts
from scripts.run_remote_agent import run_once
token=os.environ["OPSCONTROL_WORKER_TOKEN"]
hosts=policy_hosts(["portal.example.test"])
cidrs=policy_cidrs(["172.28.77.0/24"])
assert run_once("http://opscontrol-control:8000",token,hosts,cidrs), "No leased job was available"
print("Remote agent accepted real TLS evidence and submitted sanitized result")
