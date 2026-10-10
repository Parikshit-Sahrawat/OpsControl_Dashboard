"""Read-only AWS EC2 acceptance using ONLY AWS workload-identity credentials.

Run against an authorized disposable EC2 sandbox. Do not provision instances,
write IAM policies, modify security groups, or assume alternative roles here.
"""
import argparse
import os
from app.worker.provider_checks import ec2_health

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--region",required=True)
    p.add_argument("--account",required=True)
    p.add_argument("--instance-id",required=True)
    args=p.parse_args()
    # Disable ambient static credentials: GitHub OIDC action should provide
    # short-lived STS session credentials in the environment.
    if not os.getenv("AWS_SESSION_TOKEN"):
        raise SystemExit("Temporary AWS STS credentials required; static credentials are not accepted")
    result=ec2_health({"region":args.region,"account_id":args.account,"instance_id":args.instance_id})
    assert result["instance_id"]==args.instance_id and result["region"]==args.region
    assert result["state"] in {"pending","running","stopping","stopped","shutting-down","terminated"}
    assert result["system_checks"] in {"ok","impaired","unknown"}
    if result["state"]=="running" and result["system_checks"]=="ok":
        assert result["outcome"]=="SUCCESS"
    print("REAL AWS READ-ONLY EC2 ACCEPTANCE:",{
        "instance_id":result["instance_id"],"region":result["region"],
        "state":result["state"],"checks":result["system_checks"],
        "has_cpu_metric":result["cpu_percent"] is not None,
        "outcome":result["outcome"]})
if __name__=="__main__":main()
