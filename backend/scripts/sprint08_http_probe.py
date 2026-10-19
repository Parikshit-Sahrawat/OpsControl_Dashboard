"""Actual authenticated route decisions on an owned local PostgreSQL instance."""

import json, os, uuid
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from sqlalchemy import select, func
from app.db.session import SessionLocal
from app.security.models import (
    User,
)
from app.security.access_models import (
    UserRoleAssignment,
    AccessBoundaryDecision,
)
from app.security.passwords import hash_password
from tests.test_pentaho_incident_r1 import PentahoIncidentTests

assert (
    os.environ.get("OPSCONTROL_V16_ACCEPTANCE") == "1"
    and os.environ.get("ENVIRONMENT") == "test"
)
private = Path(os.environ["V16_PRIVATE_DIR"])
out = Path(os.environ["V16_EVIDENCE_DIR"])
base = os.environ["V16_API_URL"]
f = json.loads((private / "api-fixture.json").read_text())
password = f["viewer_password"]
checks = []


def req(path, method="GET", body=None, token=None, scope=None, expected=200):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    if scope is not None:
        headers["X-OpsControl-Customers"] = (
            ",".join(str(v) for v in scope) if isinstance(scope, list) else scope
        )
    try:
        with urlopen(
            Request(
                base + "/api/v1/" + path,
                data=json.dumps(body).encode() if body is not None else None,
                headers=headers,
                method=method,
            ),
            timeout=20,
        ) as r:
            status = r.status
            raw = r.read()
            data = json.loads(raw) if raw else None
    except HTTPError as e:
        status = e.code
        raw = e.read()
        data = json.loads(raw) if raw else None
    assert status in (expected if isinstance(expected, tuple) else (expected,)), (
        path,
        status,
        expected,
        data,
    )
    return data


def login(u):
    return req("auth/login", "POST", {"username": u.username, "password": password})[
        "access_token"
    ]


def boundary(admin, subject, kind, spec, revision=None, id=None, key=None):
    return req(
        "access/boundaries" + ("/" + id if id else ""),
        "PATCH" if id else "POST",
        {
            "user_id": str(subject),
            "kind": kind,
            "specification": {
                k: (
                    [str(x) for x in v]
                    if isinstance(v, list)
                    else str(v) if isinstance(v, uuid.UUID) else v
                )
                for k, v in spec.items()
            },
            "active": True,
            "expected_revision": revision,
            "idempotency_key": key or uuid.uuid4().hex,
            "reason": "Controlled security boundary decision",
        },
        admin,
        expected=200 if id else 201,
    )


lab = PentahoIncidentTests(methodName="runTest")
other = PentahoIncidentTests(methodName="runTest")
lab.setUp()
other.setUp()
try:
    lab.org.name = "Sprint 08 scoped customer"
    lab.resource.name = "Sprint 08 secured Pentaho"
    for u in [lab.user, lab.reviewer]:
        u.password_hash = hash_password(password)
    lab.db.commit()
    lab.grant(
        lab.user,
        [
            "resources.view",
            "etl.view",
            "etl.investigate",
            "incidents.view",
            "incidents.manage",
            "etl.resolve_identity",
            "etl.configure",
            "etl.replay",
            "etl.approve_replay",
        ],
    )
    lab.grant(lab.reviewer, ["resources.view", "etl.view"])
    editor, viewer = login(lab.user), login(lab.reviewer)
    admin = req(
        "auth/login", "POST", {"username": "v16-api-admin", "password": f["password"]}
    )["access_token"]
    a = str(lab.org.id)
    b = str(other.org.id)
    r = str(lab.resource.id)
    assert req("unified/resources?domain=ETL", token=editor)["total"] == 0
    assert req("unified/resources?domain=ETL", token=editor, scope=[a])["total"] == 1
    req("unified/resources/" + r, token=editor, expected=(403, 404))
    req("unified/resources", token=editor, scope="ALL", expected=403)
    req("unified/resources", token=editor, scope="*", expected=422)
    assert (
        req("unified/resources?organization_id=" + b, token=editor, scope=[a])["total"]
        == 0
    )
    req(
        "unified/resources/" + str(other.resource.id),
        token=editor,
        scope=[a, b],
        expected=(403, 404),
    )
    checks.append(
        "Explicit one-customer scope; omitted/empty/ALL/wildcard/foreign query and detail isolation"
    )
    other.grant(lab.user, ["resources.view", "etl.view"])
    assert req("unified/resources?domain=ETL", token=editor, scope=[a, b])["total"] == 2
    assert (
        req("unified/resources?domain=ETL&offset=1&limit=1", token=editor, scope=[a])[
            "items"
        ]
        == []
    )
    checks.append(
        "Several explicit customers and scoped pagination cannot widen authority"
    )
    denied = boundary(
        admin,
        lab.user.id,
        "LIMIT",
        {
            "permissions": ["resources.view", "etl.view", "incidents.view"],
            "customers": [a],
            "environments": ["PROD"],
        },
    )
    assert req("unified/resources?domain=ETL", token=editor, scope=[a])["total"] == 0
    req("unified/resources/" + r + "/executions", token=editor, scope=[a], expected=404)
    doc = req("auth/me", token=editor)
    assert doc["access_boundaries"][0]["kind"] == "LIMIT"
    boundary(
        admin,
        lab.user.id,
        "LIMIT",
        {
            "permissions": ["resources.view", "etl.view", "incidents.view"],
            "customers": [a],
            "resources": [r],
        },
        revision=denied["revision"],
        id=denied["id"],
    )
    assert req("unified/resources?domain=ETL", token=editor, scope=[a])["total"] == 1
    checks.append(
        "Environment/resource restrictions enforced in inventory, execution detail and effective projection"
    )
    # Real native evidence routes still enforce their own granular decisions.
    _, original, failure = lab.failure("s08-failed")
    lab.emit(lab.raw(invocation="s08-conflict", outcome="FAILED", run="s08-conflict"))
    lab.emit(lab.raw(invocation="s08-conflict", outcome="SUCCESS", run="s08-conflict"))
    reviews = req(
        "unified/resources/" + r + "/evidence-reviews", token=editor, scope=[a]
    )
    review = reviews["items"][0]
    decision = {
        "action": "DEFER",
        "expected_revision": review["revision"],
        "reason": "Controlled authorized review decision",
        "idempotency_key": uuid.uuid4().hex,
    }
    path = "unified/resources/" + r + "/evidence-reviews/" + review["id"] + "/decision"
    req(path, "POST", decision, viewer, [a], 403)
    req(path, "POST", decision, editor, [a])
    req(path, "POST", decision, editor, [a])
    req(
        path,
        "POST",
        {**decision, "idempotency_key": uuid.uuid4().hex},
        editor,
        [a],
        409,
    )
    req(path, "POST", {**decision, "actor_id": str(lab.reviewer.id)}, editor, [a], 422)
    req("native-incidents/" + str(failure.incident_id), token=editor, scope=[a])
    req(
        "native-incidents/" + str(failure.incident_id),
        token=editor,
        scope=[b],
        expected=(403, 404),
    )
    req(
        "unified/resources/" + r + "/historical-notifications",
        "PUT",
        {},
        viewer,
        [a],
        403,
    )
    checks.append(
        "Evidence adjudication authorization, revision/idempotency, forged actor rejection, incident and notification isolation"
    )
    admin_id = req("auth/me", token=admin)["id"]
    lab.grant(lab.user, ["incidents.acknowledge"])
    boundary(
        admin,
        lab.user.id,
        "DENY",
        {"permissions": ["incidents.acknowledge"], "customers": [a]},
    )
    incident_path = "native-incidents/" + str(failure.incident_id)
    current = req(incident_path, token=editor, scope=[a])
    req(
        incident_path + "/transition",
        "POST",
        {"revision": current["details"]["revision"], "status": "ACKNOWLEDGED"},
        editor,
        [a],
        (403, 404),
    )
    req(
        incident_path + "/transition",
        "POST",
        {"revision": current["details"]["revision"], "status": "INVESTIGATING"},
        editor,
        [a],
    )
    checks.append(
        "Exact incident action scope cannot borrow the alternative middleware permission"
    )
    # Migration/ownership fixtures may contain additional break-glass users.
    # Temporarily model the last-admin state in this owned database, restoring
    # every original flag even if an assertion fails. No session or history is deleted.
    with SessionLocal() as db:
        previous_admins = list(
            db.scalars(select(User.id).where(User.platform_admin.is_(True)))
        )
        for u in db.scalars(
            select(User).where(
                User.id.in_(previous_admins), User.id != uuid.UUID(admin_id)
            )
        ):
            u.platform_admin = False
        db.commit()
    try:
        req(
            "access/employees/" + admin_id,
            "PATCH",
            {"platform_admin": False},
            admin,
            expected=409,
        )
        req(
            "auth/users/" + admin_id + "/status",
            "PATCH",
            {"active": False},
            admin,
            expected=409,
        )
    finally:
        with SessionLocal() as db:
            for u in db.scalars(select(User).where(User.id.in_(previous_admins))):
                u.platform_admin = True
            db.commit()
    checks.append(
        "Last effective platform administrator protected on canonical and legacy routes"
    )
    # Existing IT permissions alone never imply a delegation budget.
    lab.grant(
        lab.reviewer,
        [
            "access.view",
            "access.manage_users",
            "access.manage_departments",
            "access.manage_roles",
            "access.manage_permissions",
        ],
    )
    dept = req(
        "access/departments",
        "POST",
        {"name": "Managed " + uuid.uuid4().hex, "code": uuid.uuid4().hex[:12]},
        admin,
        expected=201,
    )
    body = {
        "username": "s08-new-" + uuid.uuid4().hex,
        "full_name": "Controlled new employee",
        "password": password,
        "department_id": dept["id"],
    }
    req("access/employees", "POST", body, viewer, expected=(403, 404))
    delegation = boundary(
        admin,
        lab.reviewer.id,
        "DELEGATE",
        {
            "permissions": ["etl.view", "resources.view"],
            "customers": [a],
            "departments": [dept["id"]],
            "create_departments": True,
        },
    )
    new = req("access/employees", "POST", body, viewer, expected=201)
    assert len(new["departments"]) == 1
    req(
        "access/employees",
        "POST",
        {**body, "username": "bad-" + uuid.uuid4().hex, "department_id": None},
        viewer,
        expected=422,
    )
    req(
        "access/employees",
        "POST",
        {**body, "username": "bad-" + uuid.uuid4().hex, "platform_admin": True},
        viewer,
        expected=403,
    )
    extra = req(
        "access/departments",
        "POST",
        {"name": "Empty delegated " + uuid.uuid4().hex},
        viewer,
        expected=201,
    )
    req(
        "access/departments/" + extra["id"] + "/members",
        "POST",
        {"user_id": new["id"]},
        viewer,
        expected=409,
    )
    checks.append(
        "Explicit delegated employee/department creation, exactly one department, no break-glass or implicit access"
    )
    good = req(
        "access/roles",
        "POST",
        {
            "name": "Budget " + uuid.uuid4().hex,
            "permissions": ["etl.view", "resources.view"],
        },
        viewer,
        expected=201,
    )
    role_snapshot = next(
        row for row in req("access/roles", token=viewer) if row["id"] == good["id"]
    )
    revised = {
        "name": "Reviewed budget " + uuid.uuid4().hex,
        "permissions": ["etl.view", "resources.view"],
        "expected_revision": role_snapshot["authorization_revision"],
    }
    req("access/roles/" + good["id"], "PATCH", revised, viewer)
    req("access/roles/" + good["id"], "PATCH", revised, viewer, expected=409)
    checks.append(
        "Delegated role permission edits require a current authorization revision"
    )
    req(
        "access/roles",
        "POST",
        {
            "name": "Escalation " + uuid.uuid4().hex,
            "permissions": ["etl.resolve_identity"],
        },
        viewer,
        expected=403,
    )
    req(
        "access/employees/" + new["id"] + "/roles",
        "POST",
        {"role_id": good["id"]},
        viewer,
        expected=201,
    )
    grant = {"user_id": new["id"], "organization_id": a, "role_id": good["id"]}
    saved = req("access/customer-grants", "POST", grant, viewer, expected=201)
    req(
        "access/customer-grants",
        "POST",
        {**grant, "organization_id": b},
        viewer,
        expected=403,
    )
    req(
        "access/employees/" + str(lab.reviewer.id) + "/roles",
        "POST",
        {"role_id": good["id"]},
        viewer,
        expected=403,
    )
    req(
        "access/boundaries",
        "POST",
        {
            "user_id": new["id"],
            "kind": "ALL_CUSTOMERS",
            "specification": {
                "role_id": good["id"],
                "permissions": ["etl.view"],
                "include_future": True,
            },
            "reason": "Forbidden escalation attempt",
            "idempotency_key": uuid.uuid4().hex,
        },
        viewer,
        expected=403,
    )
    checks.append(
        "Delegated role/customer budgets, self-elevation and ALL escalation denied"
    )
    # Idempotent policy retry preserves exactly one audit decision; stale edit fails.
    key = uuid.uuid4().hex
    spec = {"permissions": ["etl.view"], "customers": [a], "resources": [r]}
    first = boundary(admin, uuid.UUID(new["id"]), "LIMIT", spec, key=key)
    again = boundary(admin, uuid.UUID(new["id"]), "LIMIT", spec, key=key)
    assert first["id"] == again["id"]
    boundary(admin, uuid.UUID(new["id"]), "LIMIT", spec, revision=1, id=first["id"])
    req(
        "access/boundaries/" + first["id"],
        "PATCH",
        {
            "user_id": new["id"],
            "kind": "LIMIT",
            "specification": spec,
            "active": True,
            "expected_revision": 1,
            "idempotency_key": uuid.uuid4().hex,
            "reason": "Controlled stale revision check",
        },
        admin,
        expected=409,
    )
    with SessionLocal() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(AccessBoundaryDecision)
                .where(AccessBoundaryDecision.request_key == key)
            )
            == 1
        )
    checks.append("Policy idempotency, immutable decision audit and stale revisions")
    from concurrent.futures import ThreadPoolExecutor

    competing = {
        "user_id": new["id"],
        "kind": "LIMIT",
        "specification": spec,
        "active": True,
        "expected_revision": 2,
        "reason": "Controlled concurrent policy revision",
    }

    def competing_save(_):
        return req(
            "access/boundaries/" + first["id"],
            "PATCH",
            {**competing, "idempotency_key": uuid.uuid4().hex},
            admin,
            expected=(200, 409),
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(competing_save, range(2)))
    assert (
        sum(r.get("revision") == 3 for r in results) == 1
        and sum("detail" in r for r in results) == 1
    )
    checks.append(
        "Concurrent authenticated boundary edits serialize; one wins and one receives stale revision"
    )

    # Persist existing-session grant revocation; token is not a permission cache.
    new_token = req(
        "auth/login", "POST", {"username": body["username"], "password": password}
    )["access_token"]
    assert req("unified/resources?domain=ETL", token=new_token, scope=[a])["total"] == 1
    req("access/customer-grants/" + saved["id"], "DELETE", token=admin, expected=204)
    req("unified/resources?domain=ETL", token=new_token, scope=[a], expected=403)
    checks.append("Customer grant revocation takes effect for an existing session")
    req(
        "access/employees/" + str(lab.user.id) + "/roles",
        "POST",
        {"role_id": good["id"]},
        admin,
        expected=201,
    )
    req(
        "access/roles/" + good["id"],
        "PATCH",
        {
            "name": "No shared-role escalation",
            "permissions": ["etl.view", "resources.view"],
        },
        viewer,
        expected=403,
    )
    checks.append(
        "A shared role assigned outside delegation cannot be edited through a filtered administrative session"
    )

    # Explicit ALL assigned to an existing role; future authority is separately decided.
    with SessionLocal() as db:
        role = db.scalar(
            select(UserRoleAssignment.role_id).where(
                UserRoleAssignment.user_id == lab.user.id
            )
        )
    allrow = boundary(
        admin,
        lab.user.id,
        "ALL_CUSTOMERS",
        {
            "role_id": role,
            "permissions": ["resources.view", "etl.view"],
            "include_future": True,
        },
    )
    assert req("auth/me", token=editor)["all_customers_authorized"]
    assert req("unified/resources?domain=ETL", token=editor, scope="ALL")["total"] >= 2
    checks.append(
        "Explicit ALL authority and independently controlled future-customer semantics"
    )
    (private / "sprint08-fixture.json").write_text(
        json.dumps(
            {
                "password": password,
                "operator": lab.user.username,
                "delegate": lab.reviewer.username,
                "organization": a,
                "other": b,
                "resource": r,
                "managedDepartment": dept["id"],
                "employee": new["id"],
                "allBoundary": allrow["id"],
            }
        )
    )
    (private / "sprint08-fixture.json").chmod(0o600)
    (out / "sprint08-http.json").write_text(
        json.dumps(
            {"status": "PASS", "checks": checks, "genuine_runtime_acceptance": False},
            indent=2,
        )
    )
    print(
        "Sprint 08 real authenticated HTTP authorization PASS: "
        + str(len(checks))
        + " groups"
    )
finally:
    lab.doCleanups()
    other.doCleanups()
