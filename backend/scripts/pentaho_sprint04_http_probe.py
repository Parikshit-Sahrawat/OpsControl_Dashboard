"""Authenticated real-HTTP review acceptance; native evidence is controlled."""

import os
import json
import uuid
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from sqlalchemy import select
from app.db.session import SessionLocal
from app.security.models import User, OrganizationMembership
from app.security.access_models import (
    Role,
    RolePermission,
    UserRoleAssignment,
    CustomerAccessGrant,
)
from app.security.permission_catalog import PROVIDER_ID
from app.security.passwords import hash_password
from tests.test_pentaho_review_r1 import PentahoReviewTests

assert (
    os.getenv("ENVIRONMENT") == "test" and os.getenv("OPSCONTROL_V16_ACCEPTANCE") == "1"
)
private = Path(os.environ["V16_PRIVATE_DIR"])
fixture = json.loads((private / "api-fixture.json").read_text())
base = os.environ["V16_API_URL"] + "/api/v1/"
checks = []


def request(path, method="GET", body=None, token=None, expected=200):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    try:
        with urlopen(
            Request(
                base + path,
                data=json.dumps(body).encode() if body else None,
                headers=headers,
                method=method,
            ),
            timeout=10,
        ) as response:
            status, data = response.status, json.load(response)
    except HTTPError as error:
        status, data = error.code, json.load(error)
    assert status == expected, (path, status, expected, data.get("detail"))
    return data


def login(name):
    return request(
        "auth/login", "POST", {"username": name, "password": fixture["viewer_password"]}
    )["access_token"]


lab, foreign = PentahoReviewTests(methodName="runTest"), PentahoReviewTests(
    methodName="runTest"
)
try:
    lab.setUp()
    original, _, history, row = lab.conflict()
    foreign.setUp()
    _, _, _, foreign_review = foreign.conflict()
    with SessionLocal() as db:
        role = Role(
            service_provider_id=PROVIDER_ID,
            code="controlled-review-" + uuid.uuid4().hex,
            name="Controlled review " + uuid.uuid4().hex,
        )
        db.add(role)
        db.flush()
        for key in ("etl.view", "etl.resolve_identity"):
            db.add(RolePermission(role_id=role.id, permission_key=key))
        role_id = role.id
        users = []
        for index in range(3):
            user = User(
                username="r1-review-http-" + uuid.uuid4().hex,
                full_name="Controlled scoped reviewer",
                password_hash=hash_password(fixture["viewer_password"]),
                active=True,
                platform_admin=False,
                service_provider_id=PROVIDER_ID,
            )
            db.add(user)
            db.flush()
            db.add(
                OrganizationMembership(
                    user_id=user.id,
                    organization_id=lab.org.id,
                    role="operator" if index == 1 else "viewer",
                )
            )
            if index == 0:
                db.add(
                    UserRoleAssignment(
                        service_provider_id=PROVIDER_ID,
                        user_id=user.id,
                        role_id=role.id,
                    )
                )
                db.flush()
                db.add(
                    CustomerAccessGrant(
                        service_provider_id=PROVIDER_ID,
                        user_id=user.id,
                        role_id=role.id,
                        organization_id=lab.org.id,
                    )
                )
            users.append(user.username)
        db.commit()
    reviewer, ordinary, viewer = map(login, users)
    prefix = f"unified/resources/{lab.resource.id}/evidence-reviews"
    path = prefix + f"/{row.id}/decision"
    body = {
        "action": "ACCEPT_VERIFIED_CLAIM",
        "expected_revision": 1,
        "idempotency_key": uuid.uuid4().hex,
        "reason": "Controlled independent native evidence adjudication",
    }
    request(prefix, expected=401)
    queue = request(prefix + "?status=OPEN&category=EXECUTION_OUTCOME", token=viewer)
    assert queue["total"] == 1
    assert queue["items"][0]["id"] == str(row.id)
    request(path, "POST", body, viewer, 403)
    request(path, "POST", body, ordinary, 403)
    checks.append(
        "Authenticated scoped review queue; viewer and ordinary investigator cannot adjudicate"
    )
    request(
        f"unified/resources/{foreign.resource.id}/evidence-reviews",
        token=reviewer,
        expected=404,
    )
    request(prefix + f"/{foreign_review.id}", token=reviewer, expected=404)
    request(prefix + f"/{foreign_review.id}/decision", "POST", body, reviewer, 404)
    checks.append("Cross-customer resource, review and decision IDOR denied")
    accepted = request(path, "POST", body, reviewer)
    assert accepted["status"] == "ACCEPTED" and accepted["revision"] == 2
    request(path, "POST", body, reviewer)
    timeline = request(prefix + f"/{row.id}", token=reviewer)
    assert timeline["total"] == 1
    assert timeline["decisions"][0]["projection_before"]["pentaho_outcome"] == "SUCCESS"
    assert timeline["decisions"][0]["projection_after"]["pentaho_outcome"] == "FAILED"
    request(path, "POST", {**body, "idempotency_key": uuid.uuid4().hex}, reviewer, 409)
    request(path, "POST", {**body, "action": "REJECT_CLAIM"}, reviewer, 409)
    request(path, "POST", {**body, "outcome": "SUCCESS"}, reviewer, 422)
    checks.append(
        "Explicit customer-granted reviewer corrects verified outcome; immutable before/after timeline; duplicate, stale and mass assignment checks"
    )
    issue = {
        "category": "RECOVERY_IDENTITY",
        "event_id": str(original.id),
        "expected_revision": 0,
        "idempotency_key": uuid.uuid4().hex,
        "reason": "Observed recovery identity needs independent evidence review",
    }
    request(prefix, "POST", issue, viewer, 403)
    flagged = request(prefix, "POST", issue, reviewer, 201)
    assert flagged["category"] == "RECOVERY_IDENTITY" and flagged["status"] == "OPEN"
    assert request(prefix, "POST", issue, reviewer, 201)["id"] == flagged["id"]
    request(
        prefix + f"/{flagged['id']}/decision",
        "POST",
        {
            "action": "REJECT_CLAIM",
            "expected_revision": 2,
            "idempotency_key": uuid.uuid4().hex,
            "reason": "Reviewed proposed relationship issue without changing native execution",
        },
        reviewer,
    )
    checks.append(
        "Scoped recovery identity issue opening, idempotency and audited rejection; no execution or recovery-link control"
    )
    # Effective access is recomputed for existing sessions, not cached in tokens.
    with SessionLocal() as db:
        permission = db.scalar(
            select(RolePermission).where(
                RolePermission.role_id == role_id,
                RolePermission.permission_key == "etl.resolve_identity",
            )
        )
        permission.active = False
        db.commit()
    request(path, "POST", body, reviewer, 403)
    checks.append("Permission revocation enforced in existing authenticated session")
    Path(os.environ["V16_EVIDENCE_DIR"], "pentaho-review-http.json").write_text(
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
    print(f"Pentaho Sprint 04 actual HTTP acceptance PASS: {len(checks)} groups")
finally:
    lab.doCleanups()
    foreign.doCleanups()
