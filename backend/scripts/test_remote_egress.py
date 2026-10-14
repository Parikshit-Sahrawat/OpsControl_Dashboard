"""Network policy unit tests; never sends a network packet."""
import socket
from app.worker.egress import EgressDenied, check_target, resolve_target, validate_ip, policy_cidrs, policy_hosts

def denied(fn):
    try: fn()
    except EgressDenied: return
    raise AssertionError("Expected network egress denial")

def fake(addresses):
    return lambda *args, **kwargs: [(socket.AF_INET,socket.SOCK_STREAM,6,"",(addr,443)) for addr in addresses]

def main():
    hosts=["portal.example.test"]
    cidrs=["10.20.0.0/16"]
    assert check_target("https://portal.example.test/ready",hosts,cidrs)[0].path=="/ready"
    denied(lambda:check_target("http://portal.example.test/ready",hosts,cidrs))
    denied(lambda:check_target("https://evil.example.test/",hosts,cidrs))
    denied(lambda:check_target("https://user:password@portal.example.test/",hosts,cidrs))
    denied(lambda:check_target("https://portal.example.test:8080/",hosts,cidrs))
    denied(lambda:check_target("https://portal.example.test/ready?token=abc",hosts,cidrs))
    denied(lambda:check_target("https://portal.example.test/\r\nHost:evil",hosts,cidrs))
    denied(lambda:policy_hosts(["*.example.test"]))
    denied(lambda:policy_cidrs(["0.0.0.0/0"]))
    denied(lambda:policy_cidrs(["::/0"]))
    denied(lambda:policy_cidrs(["127.0.0.0/8"]))
    denied(lambda:policy_cidrs(["169.254.0.0/16"]))
    permitted=policy_cidrs(cidrs)
    assert resolve_target("portal.example.test",permitted,fake(["10.20.12.4"]))=="10.20.12.4"
    denied(lambda:resolve_target("portal.example.test",permitted,fake(["10.20.12.4","8.8.8.8"])))
    denied(lambda:resolve_target("portal.example.test",permitted,fake(["169.254.169.254"])))
    denied(lambda:resolve_target("portal.example.test",permitted,fake(["127.0.0.1"])))
    denied(lambda:resolve_target("portal.example.test",permitted,fake(["::ffff:127.0.0.1"])))
    denied(lambda:validate_ip("100.100.100.200",policy_cidrs(["100.64.0.0/10"])))
    # Remote control-plane cannot widen the locally approved worker policy.
    from scripts import run_remote_agent as agent
    job={"config":{"url":"https://portal.example.test/ready"},
         "network_policy":{"allowed_hosts":["evil.example.test"],
                           "allowed_cidrs":["10.20.0.0/16"]}}
    denied(lambda:agent.execute_claim(job,hosts,permitted))
    job["network_policy"]["allowed_hosts"]=["portal.example.test"]
    job["network_policy"]["allowed_cidrs"]=["10.0.0.0/8"]
    denied(lambda:agent.execute_claim(job,hosts,permitted))
    job["network_policy"]["allowed_cidrs"]=["10.20.0.0/16"]
    original=agent.probe_https
    agent.probe_https=lambda cfg,allowed_hosts,allowed_cidrs: {
        "outcome":"SUCCESS","http_status":200,"response_time_ms":1,"response_size_bytes":0}
    try:
        assert agent.execute_claim(job,hosts,permitted)["outcome"]=="SUCCESS"
    finally:
        agent.probe_https=original
    print("REMOTE EGRESS NEGATIVE TESTS PASS")

if __name__=="__main__": main()
