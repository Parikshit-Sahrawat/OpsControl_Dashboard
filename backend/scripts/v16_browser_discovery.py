"""Owned-browser fixture driver: genuine worker/DB, explicitly mocked vendor inventory."""

import json
import os
import sys
import uuid
from pathlib import Path
from unittest.mock import patch

import app.main  # register existing parent models and mapper contracts
from app.core.config import settings
from app.db.session import SessionLocal
from app.data_pipelines.models import PipelineIntegration, PipelineOperation
from app.data_pipelines.runtime import run_operation


def main():
    if settings.environment != "test" or os.getenv("OPSCONTROL_V16_ACCEPTANCE") != "1":
        raise SystemExit("Owned disposable V1.6 browser lab required")
    fixture = json.loads(
        (Path(os.environ["V16_PRIVATE_DIR"]) / "browser-fixture.json").read_text()
    )
    operation_id = uuid.UUID(sys.argv[1])
    with SessionLocal() as db:
        op = db.get(PipelineOperation, operation_id)
        integration = db.get(PipelineIntegration, op.integration_id) if op else None
        if (
            not op
            or op.kind != "DISCOVERY"
            or op.state != "PENDING"
            or not integration
            or integration.platform != "AIRFLOW"
            or str(integration.organization_id) != fixture["organization_id"]
            or not integration.name.startswith("Controlled browser draft ")
        ):
            raise SystemExit("Discovery driver refused non-browser fixture")
    with patch(
        "app.data_pipelines.runtime.discover",
        return_value=(
            [
                {
                    "native_id": "browser-native-job-A",
                    "name": "Sample-labelled discovered pipeline",
                },
                {
                    "native_id": "browser-native-job-B",
                    "name": "Sample-labelled unselected pipeline",
                },
            ],
            True,
        ),
    ):
        run_operation(operation_id)
    with SessionLocal() as db:
        op = db.get(PipelineOperation, operation_id)
        if op.state != "COMPLETE":
            raise RuntimeError("Controlled discovery worker did not complete")
    print("CONTROLLED_DISCOVERY_FIXTURE: worker/DB complete; no live vendor accessed")


if __name__ == "__main__":
    main()
