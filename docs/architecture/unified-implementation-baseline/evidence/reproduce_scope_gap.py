"""Run from backend: .venv/bin/python ../docs/architecture/unified-implementation-baseline/evidence/reproduce_scope_gap.py. No DB I/O."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from uuid import uuid4
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.entities import ETLWorkflow, ETLWorkflowDependency
from app.security.scope import Principal, enforce_writes, _PATHS
org = uuid4()
principal = Principal(uuid4(), "synthetic-admin", True, {}, customer_directory_ids=frozenset([org]))
observations = []
for obj in [ETLWorkflow(organization_id=org, name="synthetic", environment="DEV", schedule={}, active=True), ETLWorkflowDependency(workflow_id=uuid4(), predecessor_job_id=uuid4(), successor_job_id=uuid4())]:
    with Session() as db:
        db.info["opscontrol_principal"] = principal
        db.add(obj)
        try:
            enforce_writes(db, None, None)
            observation = {"result": "NO_DENIAL"}
        except HTTPException as exc:
            observation = {"result": "DENIED", "http_status": exc.status_code, "detail": exc.detail}
        observations.append({"model": type(obj).__name__, "registered_for_scope": type(obj).__name__ in _PATHS, **observation})
print(json.dumps(observations, indent=2))
