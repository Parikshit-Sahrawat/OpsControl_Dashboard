"""Controlled fixture bindings, isolated from production application startup."""
import os
if os.getenv('ENVIRONMENT')!='demo' or os.getenv('OPSCONTROL_INFRA_ACCEPTANCE')!='1':
    raise SystemExit('Only allowed inside disposable Sprint 2 acceptance')
from app.main import app
from app.api import discovery
from app.worker.provider_discovery import aws_ec2_candidates
from scripts.infrastructure_controlled_providers import aws_session
import uvicorn
# Actual boto3 models; never enabled by app.main.
discovery.aws_ec2_candidates=lambda cfg:aws_ec2_candidates(cfg,aws_session)
uvicorn.run(app,host='127.0.0.1',port=18000,access_log=False)
