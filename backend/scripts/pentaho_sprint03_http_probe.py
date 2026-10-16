"""Real HTTP extension checks in the owned lab; native authority is a fixture."""

import json
import os
import uuid
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from sqlalchemy import select
from app.db.session import SessionLocal
from app.security.models import User, OrganizationMembership
from tests.test_pentaho_execution_r1 import PentahoExecutionTests

assert (
    os.getenv("ENVIRONMENT") == "test" and os.getenv("OPSCONTROL_V16_ACCEPTANCE") == "1"
)
private = Path(os.environ["V16_PRIVATE_DIR"])
fixture = json.loads((private / "api-fixture.json").read_text())
base = os.environ["V16_API_URL"] + "/api/v1/"
checks = []


def request(path, method="GET", payload=None, token=None, expected=200):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    body = json.dumps(payload).encode() if payload is not None else None
    try:
        with urlopen(
            Request(
                (
                    os.environ["V16_API_URL"] + path
                    if path.startswith("/")
                    else base + path
                ),
                data=body,
                method=method,
                headers=headers,
            ),
            timeout=15,
        ) as response:
            status, data = response.status, json.load(response)
    except HTTPError as error:
        status, data = error.code, json.load(error)
    if status != expected:
        (private / "r1-http-error.json").write_text(
            json.dumps(
                {
                    "path": path,
                    "status": status,
                    "expected": expected,
                    "detail": data.get("detail"),
                }
            )
        )
    assert status == expected, (path, status, expected)
    return data


lab = PentahoExecutionTests(methodName="runTest")
foreign = PentahoExecutionTests(methodName="runTest")
try:
    lab.setUp()
    a, failed, b, restored = lab.failed_and_recovery()
    foreign.setUp()
    _, foreign_run = foreign.emit(foreign.raw())
    with SessionLocal() as db:
        viewer = db.scalar(select(User).where(User.username == "v16-api-viewer"))
        db.add(
            OrganizationMembership(
                user_id=viewer.id,
                organization_id=lab.org.id,
                role="viewer",
            )
        )
        operators = []
        from app.security.passwords import hash_password
        from app.security.permission_catalog import PROVIDER_ID

        for _ in range(2):
            operator = User(
                username="r1-http-operator-" + uuid.uuid4().hex,
                full_name="Controlled scoped investigator",
                password_hash=hash_password(fixture["viewer_password"]),
                active=True,
                platform_admin=False,
                service_provider_id=PROVIDER_ID,
            )
            db.add(operator)
            db.flush()
            db.add(
                OrganizationMembership(
                    user_id=operator.id, organization_id=lab.org.id, role="operator"
                )
            )
            operators.append(operator.username)
        db.commit()
    admin = request(
        "auth/login",
        "POST",
        {"username": "v16-api-admin", "password": fixture["password"]},
    )["access_token"]
    viewer = request(
        "auth/login",
        "POST",
        {"username": "v16-api-viewer", "password": fixture["viewer_password"]},
    )["access_token"]
    investigator = request(
        "auth/login",
        "POST",
        {"username": operators[0], "password": fixture["viewer_password"]},
    )["access_token"]
    reviewer = request(
        "auth/login",
        "POST",
        {"username": operators[1], "password": fixture["viewer_password"]},
    )["access_token"]
    prefix = f"unified/resources/{lab.resource.id}/executions/{failed.id}"
    request(prefix + "/attempts", expected=401)
    detail = request(prefix + "/attempts", token=viewer)
    assert detail["total"] == 1 and detail["execution"]["pentaho_outcome"] == "FAILED"
    assert detail["items"][0]["revisions"]
    request(
        f"unified/resources/{foreign.resource.id}/executions/{foreign_run.id}/attempts",
        token=viewer,
        expected=404,
    )
    request(
        f"unified/resources/{lab.resource.id}/executions/{foreign_run.id}/attempts",
        token=admin,
        expected=404,
    )
    checks.append(
        "Authenticated scoped attempts/revisions read; cross-customer resource and nested execution IDOR denied"
    )
    proposal = {
        "recovery_history_id": str(restored.id),
        "evidence_ids": [str(a.id), str(b.id)],
        "reason": "Controlled evidence association for HTTP acceptance",
        "idempotency_key": uuid.uuid4().hex,
    }
    request(prefix + "/recovery-links", "POST", proposal, viewer, 403)
    link = request(prefix + "/recovery-links", "POST", proposal, investigator, 201)
    repeated = request(prefix + "/recovery-links", "POST", proposal, investigator, 201)
    assert repeated["id"] == link["id"]
    decision_path = prefix + "/recovery-links/" + link["id"] + "/decision"
    body = {
        "action": "CONFIRM",
        "expected_revision": 1,
        "reason": "Independent evidence review confirms relation",
        "idempotency_key": uuid.uuid4().hex,
    }
    request(decision_path, "POST", body, investigator, 409)
    confirmed = request(decision_path, "POST", body, reviewer)
    assert confirmed["status"] == "CONFIRMED"
    checks.append(
        "Viewer mutation denied; customer-scoped non-admin investigators propose/confirm; proposal idempotent; self-confirmation denied"
    )
    request(
        decision_path,
        "POST",
        {
            "action": "REVERSE",
            "expected_revision": 1,
            "reason": "Stale revision cannot reverse relationship",
            "idempotency_key": uuid.uuid4().hex,
        },
        reviewer,
        409,
    )
    reverse = {
        "action": "REVERSE",
        "expected_revision": 2,
        "reason": "Operator review reverses monitoring relationship",
        "idempotency_key": uuid.uuid4().hex,
    }
    assert request(decision_path, "POST", reverse, reviewer)["status"] == "REVERSED"
    request(decision_path, "POST", reverse, reviewer)
    timeline = request(prefix + "/recovery-links", token=viewer)
    assert len(timeline["items"][0]["decisions"]) == 3
    assert (
        request(prefix + "/attempts", token=viewer)["execution"]["pentaho_outcome"]
        == "FAILED"
    )
    checks.append(
        "Revision conflict denied; reversal idempotent and append-only; original failure remains FAILED"
    )
    # Read-only monitoring extension exposes no launch/cancel/restart/rerun operation.
    schema = request("/openapi.json", token=admin)
    paths = [p for p in schema["paths"] if "/executions/" in p]
    assert paths and all(
        not any(
            word in p.lower()
            for word in ("rerun", "restart", "cancel", "launch", "repair")
        )
        for p in paths
    )
    checks.append("Monitoring-only execution routes; no workload controls")
    Path(os.environ["V16_EVIDENCE_DIR"], "pentaho-http.json").write_text(
        json.dumps(
            {
                "status": "PASS",
                "checks": checks,
                "native_authority": "CONTROLLED_FIXTURE",
                "genuine_runtime_acceptance": False,
                "production_modified": False,
            },
            indent=2,
        )
    )
    print(f"Pentaho Sprint 03 actual HTTP acceptance PASS: {len(checks)} groups")
finally:
    lab.doCleanups()
    foreign.doCleanups()
