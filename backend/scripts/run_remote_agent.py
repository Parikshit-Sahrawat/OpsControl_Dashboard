"""Outbound-only remote HTTP probe runner; no shell or arbitrary scripts.

Usage (trusted host, internal-network ACL/firewall enforced):
  OPSCONTROL_SERVER_URL=https://opscontrol.example.test \
  OPSCONTROL_WORKER_TOKEN=<protected service token> \
  OPSCONTROL_ALLOWED_HOSTS=portal.example.test \
  OPSCONTROL_ALLOWED_CIDRS=10.25.1.0/24 \
    python -m scripts.run_remote_agent

Local HTTP control plane only with OPSCONTROL_ALLOW_INSECURE_CONTROL_PLANE=1
AND an explicit loopback hostname; never for real customer networks.
"""
import json
import logging
import os
import ssl
import time
import uuid
import urllib.error
import urllib.request
from datetime import datetime, timezone
from urllib.parse import urlsplit

from app.worker.egress import EgressDenied, policy_hosts, policy_cidrs, probe_https

log=logging.getLogger("opscontrol.remote.agent")

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req,fp,code,msg,headers,newurl):
        raise RuntimeError("Control plane redirects forbidden")

def config():
    base=os.environ.get("OPSCONTROL_SERVER_URL","").rstrip("/")
    token=os.environ.get("OPSCONTROL_WORKER_TOKEN","")
    parsed=urlsplit(base)
    if not base or parsed.path not in ("","/") or parsed.query or parsed.fragment or parsed.username or parsed.password:
        raise SystemExit("Invalid control-plane URL")
    insecure=os.environ.get("OPSCONTROL_ALLOW_INSECURE_CONTROL_PLANE")=="1"
    if parsed.scheme!="https" and not (insecure and parsed.scheme=="http" and parsed.hostname in {"localhost","127.0.0.1","::1"}):
        raise SystemExit("HTTPS is mandatory outside explicit local-only development")
    if len(token)<40 or len(token)>256: raise SystemExit("Valid worker credential required")
    hosts=policy_hosts([x.strip() for x in os.environ.get("OPSCONTROL_ALLOWED_HOSTS","").split(",") if x.strip()])
    cidrs=policy_cidrs([x.strip() for x in os.environ.get("OPSCONTROL_ALLOWED_CIDRS","").split(",") if x.strip()])
    return base,token,hosts,cidrs

def call(base,token,path,payload=None):
    data=json.dumps(payload,sort_keys=True).encode() if payload is not None else None
    req=urllib.request.Request(base+path,data=data,
        headers={"Authorization":"Bearer "+token,"Content-Type":"application/json"},
        method="POST" if payload is not None else "GET")
    client=urllib.request.build_opener(NoRedirect,urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    with client.open(req,timeout=15) as r:
        if r.status>=300: raise RuntimeError("Unexpected API status")
        raw=r.read(65537)
        if len(raw)>65536: raise RuntimeError("Control response too large")
        return json.loads(raw)

def execute_claim(job,hosts,cidrs):
    config=job["config"]
    server_policy=job["network_policy"]
    # The locally installed operator policy is mandatory; server cannot
    # add destinations to the agent by changing a task or worker DB policy.
    requested_hosts=policy_hosts(server_policy["allowed_hosts"])
    requested_cidrs=policy_cidrs(server_policy["allowed_cidrs"])
    if not set(requested_hosts).issubset(set(hosts)):
        raise EgressDenied("Server hostname policy exceeds local worker policy")
    # Each allowed server CIDR must be a subnet of a locally approved CIDR.
    if not all(any(net.subnet_of(local) for local in cidrs) for net in requested_cidrs):
        raise EgressDenied("Server network policy exceeds local worker policy")
    return probe_https(config,requested_hosts,server_policy["allowed_cidrs"])

def run_once(base,token,hosts,cidrs):
    claimed=call(base,token,"/api/v1/worker/claim",{})
    job=claimed.get("job")
    if not job: return False
    try:
        result=execute_claim(job,hosts,cidrs)
    except EgressDenied:
        # Do not submit a false target outage if local egress blocks a request.
        log.error("Job rejected by local agent policy; no network connection attempted")
        return True
    except ssl.SSLError:
        result={"outcome":"TLS_ERROR"}
    except (TimeoutError,socket.timeout):
        result={"outcome":"TIMEOUT"}
    except Exception:
        # Never send raw exceptions/URLs/hostnames back as evidence.
        result={"outcome":"NETWORK_ERROR"}
    evidence={"event_id":str(uuid.uuid4()),"job_id":job["job_id"],
              "lease_nonce":job["lease_nonce"],"observed_at":datetime.now(timezone.utc).isoformat(),
              **result}
    call(base,token,"/api/v1/worker/results",evidence)
    log.info("Probe result delivered: outcome=%s",result["outcome"])
    return True

def main():
    global socket
    import socket
    logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(message)s")
    base,token,hosts,cidrs=config()
    delay=5
    while True:
        try:
            busy=run_once(base,token,hosts,cidrs)
            delay=1 if busy else 5
        except KeyboardInterrupt:
            return
        except (urllib.error.HTTPError,urllib.error.URLError,RuntimeError,ValueError) as exc:
            # Avoid logging request URL or Authorization headers.
            log.warning("Control-plane request failed (%s)",type(exc).__name__)
            delay=min(delay*2,60)
        time.sleep(delay)

if __name__=="__main__":
    main()
