"""Run INSIDE a Docker internal network (never connects to real infrastructure)."""
import sys
from app.worker.egress import probe_https,EgressDenied
conf={"url":"https://portal.example.test/ready","expected_status":200,"timeout_seconds":4}
policy_hosts=["portal.example.test"]
policy_cidrs=["172.28.77.0/24"]
result=probe_https(conf,policy_hosts,policy_cidrs)
expected=sys.argv[1]
assert result["outcome"]==expected,(expected,result)
assert result["http_status"]==(200 if expected=="SUCCESS" else 503),result
assert result["response_time_ms"]>=0
print("PRIVATE HTTPS LIVE PROBE PASS:",result)
