"""One actual TLS probe, reading its ephemeral worker token without logging it."""
import json
from pathlib import Path
from app.worker.egress import policy_cidrs, policy_hosts
from scripts.run_remote_agent import run_once
state=json.loads(Path('/golden/private/session.json').read_text())
assert run_once('http://opscontrol-control:8000', state['worker_token'],
    policy_hosts(['portal.example.test']), policy_cidrs(['172.28.77.0/24']))
print('Real TLS probe delivered sanitized evidence')
