"""Owned local browser fixtures. No vendor runtime or real workloads."""

import json, os, uuid
from datetime import timedelta
from pathlib import Path
from sqlalchemy import select
from app.models import JobStepExecution
from app.security.passwords import hash_password
from app.security.models import User
from app.security.permission_catalog import PROVIDER_ID
from app.data_pipelines.models import PipelineIntegration, PipelineJob
from app.data_pipelines.bridge import create_job_resource
from app.unified.pentaho_models import PentahoEvidenceReview
from tests.test_pentaho_incident_r1 import PentahoIncidentTests
from tests.test_pentaho_history_r1 import PentahoHistoryTests

assert (
    os.environ.get("OPSCONTROL_V16_ACCEPTANCE") == "1"
    and os.environ.get("ENVIRONMENT") == "test"
)
private = Path(os.environ["V16_PRIVATE_DIR"])
password = json.loads((private / "api-fixture.json").read_text())["viewer_password"]
lab = PentahoIncidentTests(methodName="runTest")
lab.setUp()
foreign = PentahoIncidentTests(methodName="runTest")
foreign.setUp()
native = PentahoHistoryTests(methodName="runTest")
native.setUp()
try:
    lab.org.name = "Sprint 07 Alpha"
    lab.resource.name = "Orders Pentaho"
    lab.db.commit()
    foreign.org.name = "Sprint 07 Beta"
    foreign.resource.name = "Beta isolated pipeline"
    foreign.db.commit()
    original_event, original, failure = lab.failure("original-failure")
    _, waiting = lab.emit(
        lab.raw(
            invocation="retry-wait", outcome="FAILED", run="retry-wait", retry="PENDING"
        )
    )
    lab.emit(
        lab.raw(
            invocation="retry-1", outcome="FAILED", run="retry-success", retry="PENDING"
        )
    )
    _, retried = lab.emit(
        lab.raw(invocation="retry-2", outcome="SUCCESS", run="retry-success", order=2)
    )
    recovery_event, recovered = lab.emit(
        lab.raw(invocation="manual-recovery", outcome="SUCCESS")
    )
    lab.emit(lab.raw(invocation="conflict", outcome="FAILED", run="conflict"))
    lab.emit(lab.raw(invocation="conflict", outcome="SUCCESS", run="conflict"))
    _, incomplete = lab.emit(lab.raw(invocation="exit-only", outcome="EXITED"))
    review = lab.db.scalar(
        select(PentahoEvidenceReview).where(
            PentahoEvidenceReview.resource_id == lab.resource.id
        )
    )
    p = PentahoHistoryTests.parameters(lab)
    PentahoHistoryTests.tick(lab, p, lab.base - timedelta(seconds=20))
    PentahoHistoryTests.tick(lab, p, lab.base + timedelta(seconds=31), healthy=False)
    native.test_verified_native_schedule_and_freshness()
    native.resource.name = "Verified native scheduler fixture"
    native.org.name = "Sprint 07 Native"
    native.db.commit()
    viewer = User(
        username="sprint07-viewer-" + uuid.uuid4().hex,
        full_name="Controlled read-only operator",
        password_hash=hash_password(password),
        active=True,
        service_provider_id=PROVIDER_ID,
    )
    restricted = User(
        username="sprint07-etl-only-" + uuid.uuid4().hex,
        full_name="Controlled catalog-restricted reader",
        password_hash=hash_password(password),
        active=True,
        service_provider_id=PROVIDER_ID,
    )
    lab.db.add_all([viewer, restricted])
    for u in [lab.user, lab.reviewer]:
        u.password_hash = hash_password(password)
    lab.db.commit()
    keys = [
        "etl.view",
        "etl.investigate",
        "etl.resolve_identity",
        "incidents.view",
        "incidents.manage",
        "incidents.acknowledge",
        "resources.view",
        "access.view",
    ]
    lab.grant(lab.user, keys)
    lab.grant(lab.reviewer, keys)
    lab.grant(viewer, ["etl.view", "incidents.view", "resources.view"])
    lab.grant(restricted, ["etl.view"])
    foreign.grant(lab.user, keys)
    native.grant(lab.user, keys)
    for index in range(22):
        platform = ["AIRFLOW", "NIFI", "ADF", "SSIS"][index % 4]
        integration = PipelineIntegration(
            organization_id=lab.org.id,
            name="Browser " + platform,
            platform=platform,
            environment="TEST",
            owner_id=lab.user.id,
            configuration={},
            enabled=False,
        )
        lab.db.add(integration)
        lab.db.flush()
        job = PipelineJob(
            organization_id=lab.org.id,
            integration_id=integration.id,
            native_id="controlled-" + str(index),
            name=f"{platform} compatible {index:02d}",
            origin="MANUAL",
            selected=True,
        )
        lab.db.add(job)
        lab.db.flush()
        lab.db.info["pipeline_initial_job_binding"] = job.id
        resource = create_job_resource(lab.db, integration, job)
        job.resource_id = resource.id
    # Deliberately synthetic UI-only counter states; not observed native child
    # invocations. Native parser/persistence evidence is tested separately.
    for copy, status, errors, read, written in [
        ("0", "SUCCESS", 0, 0, 4),
        ("1", "UNKNOWN", None, None, None),
    ]:
        lab.db.add(
            JobStepExecution(
                history_id=retried.id,
                name="Synthetic repeated step",
                external_step_id="controlled-ui-step-" + copy,
                attempt=2,
                status=status,
                step_type="CONTROLLED_UI_FIXTURE",
                records_read=read,
                records_written=written,
                source_evidence={
                    "fixture_state": "CONTROLLED_UI_COUNTER_VALUES",
                    "native_copy": copy,
                    "nr_errors": errors,
                    "native_status_description": "Finished" if copy == "0" else None,
                    "native_metrics": {
                        "errors": errors,
                        "linesRead": read,
                        "linesWritten": written,
                        "linesInput": read,
                        "linesOutput": written,
                    },
                },
            )
        )
    lab.db.commit()
    data = {
        "password": password,
        "operator": lab.user.username,
        "reviewer": lab.reviewer.username,
        "viewer": viewer.username,
        "restricted": restricted.username,
        "organization": str(lab.org.id),
        "foreignOrganization": str(foreign.org.id),
        "nativeOrganization": str(native.org.id),
        "resource": str(lab.resource.id),
        "foreignResource": str(foreign.resource.id),
        "nativeResource": str(native.resource.id),
        "original": str(original.id),
        "recovered": str(recovered.id),
        "retried": str(retried.id),
        "waiting": str(waiting.id),
        "incomplete": str(incomplete.id),
        "originalEvent": str(original_event.id),
        "recoveryEvent": str(recovery_event.id),
        "review": str(review.id),
        "incident": str(failure.incident_id),
    }
    target = private / "sprint07-fixture.json"
    target.write_text(json.dumps(data))
    target.chmod(0o600)
    print("Sprint 07 controlled fixtures ready; no vendor runtime accessed")
finally:
    lab.doCleanups()
    foreign.doCleanups()
    native.doCleanups()
