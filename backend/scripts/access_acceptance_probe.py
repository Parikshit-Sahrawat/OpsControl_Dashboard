"""Real HTTP + PostgreSQL assertions in the owned access fixture only."""

from scripts.acceptance_scope import probe_headers
import json, os, uuid
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, DBAPIError
from app.db.session import SessionLocal
from app.models import (
    Organization,
)  # register customer FK targets in this standalone probe
from app.security.models import User, OrganizationMembership
from app.security.access_models import (
    Department,
    DepartmentMembership,
    ServiceProvider,
    CustomerAccessGrant,
    UserRoleAssignment,
)
from app.security.permission_catalog import PROVIDER_ID
from app.security.passwords import hash_password

BASE = os.environ["TEST_API_BASE"]
PRIVATE = Path(os.environ["ACCESS_PRIVATE_DIR"])
OUT = Path(os.environ["ACCESS_EVIDENCE_DIR"])
f = json.loads((PRIVATE / "fixture.json").read_text())
checks = []
fixture_department = None


def request(path, method="GET", body=None, token=None, expected=200):
    global fixture_department
    if (
        expected in (201, 403, 409, 422)
        and method == "POST"
        and path == "/api/v1/access/employees"
        and body
        and not body.get("department_id")
    ):
        body = {**body, "department_id": fixture_department}
    if (
        expected == 403
        and method == "POST"
        and path == "/api/v1/access/employees"
        and body
        and not body.get("department_id")
    ):
        body = {**body, "department_id": fixture_department}
    if (
        expected == 201
        and method == "POST"
        and path.startswith("/api/v1/access/departments/")
        and path.endswith("/members")
    ):
        department_id = path.split("/")[-2]
        return request(
            "/api/v1/access/employees/" + body["user_id"] + "/department",
            "PUT",
            {"department_id": department_id},
            token,
            200,
        )
    if expected == 204 and method == "DELETE" and "/members/" in path:
        return request(
            "/api/v1/access/employees/" + path.rsplit("/", 1)[1] + "/department",
            "PUT",
            {"department_id": fixture_department},
            token,
            200,
        )
    if (
        expected == 201
        and method == "POST"
        and path == "/api/v1/auth/users"
        and body
        and not body.get("platform_admin")
        and not body.get("department_id")
    ):
        body = {**body, "department_id": fixture_department}
    req = Request(
        BASE + path,
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
        headers={
            "Content-Type": "application/json",
            **({"Authorization": "Bearer " + token} if token else {}),
            **probe_headers(BASE, token, path),
        },
    )
    try:
        with urlopen(req, timeout=20) as r:
            status = r.status
            data = r.read()
    except HTTPError as e:
        status = e.code
        data = e.read()
    assert status in (expected if isinstance(expected, tuple) else (expected,)), (
        method,
        path,
        status,
        expected,
    )
    return json.loads(data) if data else None


def record(name):
    checks.append(name)


def main():
    if (
        os.getenv("OPSCONTROL_ACCESS_ACCEPTANCE") != "1"
        or os.getenv("ENVIRONMENT") != "test"
        or not BASE.startswith("http://127.0.0.1:")
    ):
        raise RuntimeError("Owned local access fixture required")
    admin = request(
        "/api/v1/auth/login",
        "POST",
        {"username": "access-fixture-admin", "password": f["admin_password"]},
    )["access_token"]
    legacy = request("/api/v1/auth/me", token=f["old_viewer_token"])
    assert legacy["id"] == f["viewer_id"]
    assert "access.view" not in legacy["permissions"]
    assert [
        x["id"] for x in request("/api/v1/organizations", token=f["old_viewer_token"])
    ] == [f["customer_a"]]
    record(
        "Existing users, hashes, sessions and exact legacy customer viewer scope survive migration"
    )
    before_revision = request("/api/v1/auth/me", token=admin)["authorization_revision"]
    request(
        "/api/v1/organizations/" + f["customer_a"],
        "PATCH",
        {"name": "Customer A renamed (synthetic)"},
        admin,
    )
    assert (
        request("/api/v1/auth/me", token=admin)["authorization_revision"]
        != before_revision
    )
    assert any(
        row["name"] == "Customer A renamed (synthetic)"
        for row in request("/api/v1/auth/customer-scope", token=f["old_viewer_token"])
    )
    request(
        "/api/v1/organizations/" + f["customer_a"],
        "PATCH",
        {"name": "Customer A (synthetic)"},
        admin,
    )
    record(
        "Customer directory changes invalidate authorization revision and refresh authorized selector metadata"
    )
    roles = request("/api/v1/access/roles", token=admin)
    rid = {r["code"]: r["id"] for r in roles}

    def employee(name, platform=False):
        return request(
            "/api/v1/access/employees",
            "POST",
            {
                "username": name,
                "full_name": name + " Employee",
                "employee_id": "EMP-" + name,
                "work_email": name + "@example.test",
                "password": f["admin_password"],
                "platform_admin": platform,
            },
            admin,
            201,
        )

    def login(name):
        return request(
            "/api/v1/auth/login",
            "POST",
            {"username": name, "password": f["admin_password"]},
        )["access_token"]

    def dept(name):
        return request(
            "/api/v1/access/departments",
            "POST",
            {
                "name": name,
                "code": name,
                "description": "Synthetic provider department",
            },
            admin,
            201,
        )

    def delegate_identity_view(subject, departments):
        # Explicit fixture-only Sprint08 administration boundary. A delegation
        # budget grants no operational/customer permission by itself.
        return request(
            "/api/v1/access/boundaries",
            "POST",
            {
                "user_id": subject["id"],
                "kind": "DELEGATE",
                "specification": {
                    "departments": departments,
                    "customers": [],
                    "permissions": ["resources.view"],
                },
                "active": True,
                "idempotency_key": uuid.uuid4().hex,
                "reason": "Controlled explicit administrative view fixture",
            },
            admin,
            201,
        )

    global fixture_department
    fixture_department = dept("Controlled Unassigned Team")["id"]
    one = dept("NOC")
    two = dept("Systems")
    assert one["id"] != two["id"] and not {one["id"], two["id"]} & {
        f["customer_a"],
        f["customer_b"],
    }
    member = employee("access-noc")
    manager = employee("access-manager")
    other = employee("access-other")
    for d in (one, two):
        request(
            "/api/v1/access/departments/" + d["id"] + "/roles",
            "POST",
            {"role_id": rid["read-only-viewer"]},
            admin,
            201,
        )
    for d, c in ((one, f["customer_a"]), (two, f["customer_b"])):
        request(
            "/api/v1/access/customer-grants",
            "POST",
            {
                "department_id": d["id"],
                "organization_id": c,
                "role_id": rid["read-only-viewer"],
            },
            admin,
            201,
        )
    request(
        "/api/v1/access/departments/" + one["id"] + "/members",
        "POST",
        {"user_id": member["id"]},
        admin,
        201,
    )
    request(
        "/api/v1/access/departments/" + two["id"] + "/members",
        "POST",
        {"user_id": other["id"]},
        admin,
        201,
    )
    noc = login("access-noc")
    south = login("access-other")
    assert [x["id"] for x in request("/api/v1/organizations", token=noc)] == [
        f["customer_a"]
    ]
    assert [x["id"] for x in request("/api/v1/organizations", token=south)] == [
        f["customer_b"]
    ]
    record(
        "Customers and internal departments are independent UUID entities; same department role has separate customer scopes"
    )
    for path in [
        "/api/v1/access/employees",
        "/api/v1/access/departments",
        "/api/v1/access/roles",
        "/api/v1/access/permissions",
        "/api/v1/access/customer-directory",
        "/api/v1/auth/users",
        "/api/v1/auth/memberships",
        "/api/v1/access/employees/" + other["id"] + "/effective-permissions",
    ]:
        request(path, token=noc, expected=403)
    request("/api/v1/access/employees", expected=401)
    record(
        "No access.view means 403 for direct or indirect identity/department/permission APIs; anonymous receives 401"
    )
    request(
        "/api/v1/access/departments/" + two["id"] + "/members",
        "POST",
        {"user_id": member["id"]},
        admin,
        409,
    )
    request(
        "/api/v1/access/employees/" + member["id"] + "/department",
        "PUT",
        {"department_id": two["id"]},
        admin,
    )
    assert set(request("/api/v1/auth/me", token=noc)["customer_permissions"]) == {
        f["customer_b"]
    }
    request(
        "/api/v1/access/employees/" + member["id"] + "/department",
        "PUT",
        {"department_id": one["id"]},
        admin,
    )
    assert set(request("/api/v1/auth/me", token=noc)["customer_permissions"]) == {
        f["customer_a"]
    }
    record(
        "Single department creation enforcement and explicit transfer immediately update existing sessions"
    )
    request(
        "/api/v1/access/employees/" + manager["id"] + "/roles",
        "POST",
        {"role_id": rid["access-administrator"]},
        admin,
        201,
    )
    delegate_identity_view(manager, [fixture_department, one["id"], two["id"]])
    access = login("access-manager")
    assert "access.view" in request("/api/v1/auth/me", token=access)["permissions"]
    for path in [
        "/api/v1/organizations",
        "/api/v1/resource-management/data-sources",
        "/api/v1/etl/executions",
        "/api/v1/operations/services",
    ]:
        request(path, token=access, expected=403)
    request(
        "/api/v1/access/employees",
        "POST",
        {
            "username": "escalation",
            "full_name": "Escalation",
            "password": f["admin_password"],
            "platform_admin": True,
        },
        access,
        403,
    )
    request(
        "/api/v1/access/employees/" + manager["id"] + "/roles",
        "POST",
        {"role_id": rid["resource-administrator"]},
        access,
        403,
    )
    request(
        "/api/v1/access/roles",
        "POST",
        {"name": "Escalating Role", "permissions": ["access.manage_users"]},
        access,
        403,
    )
    request(
        "/api/v1/access/employees/" + f["admin_id"],
        "PATCH",
        {"platform_admin": False},
        access,
        404,  # Protected employees are intentionally non-discoverable to delegation.
    )
    unchanged = request("/api/v1/access/employees/" + f["admin_id"], token=admin)
    assert unchanged["platform_admin"] is True and unchanged["active"] is True
    request(
        "/api/v1/access/employees",
        "POST",
        {
            "username": "massassignment",
            "full_name": "Mass Assignment",
            "password": f["admin_password"],
            "id": f["customer_a"],
        },
        admin,
        422,
    )
    record(
        "Access administrators manage identities but gain no monitoring/customer access and cannot escalate/self-grant/mass-assign"
    )
    request(
        "/api/v1/access/employees/" + f["admin_id"],
        "PATCH",
        {"active": False},
        admin,
        409,
    )
    request(
        "/api/v1/access/employees/" + f["admin_id"],
        "PATCH",
        {"platform_admin": False},
        admin,
        409,
    )
    record(
        "Last active break-glass administrator is protected from disable or demotion"
    )
    for c in (f["customer_a"], f["customer_b"]):
        request(
            "/api/v1/resource-management/data-sources",
            "POST",
            {"organization_id": c, "name": "Scoped " + c, "source_type": "API"},
            admin,
            201,
        )
    rows = request("/api/v1/resource-management/data-sources", token=noc)
    assert all(r["organization_id"] == f["customer_a"] for r in rows)
    source_b = next(
        r
        for r in request("/api/v1/resource-management/data-sources", token=admin)
        if r["organization_id"] == f["customer_b"]
    )
    request(
        "/api/v1/monitoring/data-sources/" + source_b["id"], token=noc, expected=404
    )
    assert (
        request(
            "/api/v1/resource-management/data-sources?organization_id="
            + f["customer_b"],
            token=noc,
        )
        == []
    )
    request(
        "/api/v1/resource-management/data-sources",
        "POST",
        {"organization_id": f["customer_b"], "name": "forged", "source_type": "API"},
        noc,
        403,
    )
    record(
        "Customer lists/details/mutations independently reject or hide the other customer"
    )
    grant = request(
        "/api/v1/access/customer-grants",
        "POST",
        {"user_id": member["id"], "organization_id": f["customer_a"], "effect": "DENY"},
        admin,
        201,
    )
    assert request("/api/v1/auth/me", token=noc)["customer_permissions"] == {}
    request("/api/v1/resource-management/data-sources", token=noc, expected=403)
    request(
        "/api/v1/access/customer-grants/" + grant["id"],
        "DELETE",
        token=admin,
        expected=204,
    )
    assert (
        f["customer_a"] in request("/api/v1/auth/me", token=noc)["customer_permissions"]
    )
    record(
        "Explicit employee customer deny wins over inherited scope; removal restores only valid inheritance"
    )
    request(
        "/api/v1/access/departments/" + one["id"],
        "PATCH",
        {
            "name": "NOC renamed",
            "code": "NOC",
            "description": "changed",
            "active": False,
        },
        admin,
    )
    assert request("/api/v1/auth/me", token=noc)["customer_permissions"] == {}
    request(
        "/api/v1/access/departments/" + one["id"],
        "PATCH",
        {
            "name": "NOC renamed",
            "code": "NOC",
            "description": "changed",
            "active": True,
        },
        admin,
    )
    assert {one["id"], two["id"]}.issubset(
        {d["id"] for d in request("/api/v1/access/departments", token=admin)["items"]}
    )
    request(
        "/api/v1/access/departments/" + one["id"], "DELETE", token=admin, expected=409
    )
    record(
        "Department UUID remains stable across edit/deactivation; soft deactivation removes inherited access and deletion is refused"
    )
    with SessionLocal() as db:
        try:
            db.add(
                DepartmentMembership(
                    user_id=uuid.uuid4(),
                    department_id=uuid.UUID(one["id"]),
                    service_provider_id=PROVIDER_ID,
                )
            )
            db.commit()
            raise AssertionError("Invalid FK accepted")
        except IntegrityError:
            db.rollback()
        try:
            db.execute(
                text("UPDATE departments SET id=:new WHERE id=:id"),
                {"new": uuid.uuid4(), "id": one["id"]},
            )
            db.commit()
            raise AssertionError("Mutable UUID accepted")
        except DBAPIError:
            db.rollback()

        try:
            db.add(
                UserRoleAssignment(
                    user_id=uuid.UUID(member["id"]),
                    role_id=uuid.UUID(rid["read-only-viewer"]),
                    service_provider_id=PROVIDER_ID,
                    effect="BAD",
                )
            )
            db.commit()
            raise AssertionError("Invalid assignment effect accepted")
        except IntegrityError:
            db.rollback()
    record("PostgreSQL rejects invalid memberships, role effects and UUID mutation")
    # The preview executes the real save constraints, but rolls back all grants.
    preview_user = employee("access-preview")
    request(
        "/api/v1/access/employees/" + preview_user["id"] + "/roles",
        "POST",
        {"role_id": rid["read-only-viewer"]},
        admin,
        201,
    )
    body = {
        "user_id": preview_user["id"],
        "organization_id": f["customer_b"],
        "role_id": rid["read-only-viewer"],
    }
    proposal = request("/api/v1/access/customer-grants/preview", "POST", body, admin)
    assert (
        not proposal["saved"]
        and f["customer_b"] in proposal["effective"]["customer_permissions"]
    )
    assert (
        request(
            "/api/v1/access/customer-grants?user_id=" + preview_user["id"], token=admin
        )["total"]
        == 0
    )
    assert (
        request(
            "/api/v1/access/employees/" + preview_user["id"] + "/effective-permissions",
            token=admin,
        )["customer_permissions"]
        == {}
    )
    record("Server-validated effective preview leaves no persisted grant or privilege")
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    barrier = Barrier(2)

    def concurrent_grant(effect):
        barrier.wait(timeout=5)
        return request(
            "/api/v1/access/customer-grants",
            "POST",
            (
                body
                if effect == "ALLOW"
                else {
                    "user_id": preview_user["id"],
                    "organization_id": f["customer_b"],
                    "effect": "DENY",
                }
            ),
            admin,
            (201, 409),
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(concurrent_grant, ("ALLOW", "DENY")))
    assert sum("id" in result for result in results) == 1
    persisted = request(
        "/api/v1/access/customer-grants?user_id=" + preview_user["id"], token=admin
    )
    assert persisted["total"] == 1
    request(
        "/api/v1/access/customer-grants/" + persisted["items"][0]["id"],
        "DELETE",
        token=admin,
        expected=204,
    )
    record(
        "Concurrent ALLOW/DENY attempts serialize per employee; exactly one grant survives and contradictory request is 409"
    )
    # Different roles must remain paired with their own department/customer.
    scoped = employee("access-paired")
    custom = request(
        "/api/v1/access/roles",
        "POST",
        {"name": "Paired Resource Read", "permissions": ["resources.view"]},
        admin,
        201,
    )
    limited = dept("Limited")
    request(
        "/api/v1/access/departments/" + limited["id"] + "/roles",
        "POST",
        {"role_id": custom["id"]},
        admin,
        201,
    )
    request(
        "/api/v1/access/customer-grants",
        "POST",
        {
            "department_id": limited["id"],
            "organization_id": f["customer_b"],
            "role_id": custom["id"],
        },
        admin,
        201,
    )
    for d in (one, limited):
        request(
            "/api/v1/access/departments/" + d["id"] + "/members",
            "POST",
            {"user_id": scoped["id"]},
            admin,
            201,
        )
    paired = login("access-paired")
    perms = request("/api/v1/auth/me", token=paired)["customer_permissions"]
    assert f["customer_a"] not in perms and perms[f["customer_b"]] == ["resources.view"]
    role_snapshot = next(
        r
        for r in request("/api/v1/access/roles", token=admin)
        if r["id"] == custom["id"]
    )
    request(
        "/api/v1/access/roles/" + custom["id"],
        "PATCH",
        {
            "name": "Paired Resource Read",
            "permissions": ["alerts.view"],
            "expected_revision": role_snapshot["authorization_revision"],
        },
        admin,
    )
    perms = request("/api/v1/auth/me", token=paired)["customer_permissions"]
    assert perms[f["customer_b"]] == ["alerts.view"]
    request(
        "/api/v1/resource-management/data-sources?organization_id=" + f["customer_b"],
        token=paired,
        expected=403,
    )
    record(
        "No role/customer cross-product; custom role permission replacement applies immediately to the same session"
    )
    denial = request(
        "/api/v1/access/employees/" + member["id"] + "/roles",
        "POST",
        {"role_id": rid["read-only-viewer"], "effect": "DENY"},
        admin,
        201,
    )
    assert (
        request("/api/v1/auth/me", token=noc)["customer_permissions"][f["customer_a"]]
        == []
    )
    request(
        "/api/v1/access/employees/" + member["id"] + "/roles/" + denial["id"],
        "DELETE",
        token=admin,
        expected=204,
    )
    assert (
        "resources.view"
        in request("/api/v1/auth/me", token=noc)["customer_permissions"][
            f["customer_a"]
        ]
    )
    record(
        "Employee-specific permission restriction narrows inherited roles; revocation restores only paired access"
    )
    other_provider = uuid.uuid4()
    outsider = uuid.uuid4()
    with SessionLocal() as db:
        db.add(
            ServiceProvider(
                id=other_provider,
                name="Other synthetic provider",
                code="OTHER",
                active=True,
            )
        )
        db.flush()
        db.add(
            User(
                id=outsider,
                service_provider_id=other_provider,
                username="access-outsider",
                full_name="Other Provider Employee",
                password_hash=hash_password(f["admin_password"]),
            )
        )
        db.commit()
        try:
            db.add(
                DepartmentMembership(
                    user_id=outsider,
                    department_id=uuid.UUID(one["id"]),
                    service_provider_id=PROVIDER_ID,
                )
            )
            db.commit()
            raise AssertionError("Cross-provider membership accepted")
        except IntegrityError:
            db.rollback()
    request("/api/v1/access/employees/" + str(outsider), token=admin, expected=404)
    assert str(outsider) not in {
        u["id"] for u in request("/api/v1/auth/users", token=admin)
    }
    request(
        "/api/v1/access/departments/" + one["id"] + "/members",
        "POST",
        {"user_id": str(outsider)},
        admin,
        404,
    )
    request(
        "/api/v1/auth/login",
        "POST",
        {"username": "access-outsider", "password": f["admin_password"]},
        expected=401,
    )
    record(
        "Provider-owned identity queries and composite foreign keys reject another provider employee"
    )
    # Department-only administrator cannot use identity or platform escalation APIs.
    limited_admin = employee("access-department-admin")
    admin_role = request(
        "/api/v1/access/roles",
        "POST",
        {
            "name": "Department Administrator",
            "permissions": ["access.view", "access.manage_departments"],
        },
        admin,
        201,
    )
    request(
        "/api/v1/access/employees/" + limited_admin["id"] + "/roles",
        "POST",
        {"role_id": admin_role["id"]},
        admin,
        201,
    )
    delegate_identity_view(limited_admin, [fixture_department, one["id"], two["id"]])
    department_admin = login("access-department-admin")
    request(
        "/api/v1/access/employees/" + limited_admin["id"],
        "PATCH",
        {"platform_admin": True},
        department_admin,
        403,
    )
    request(
        "/api/v1/access/employees/" + limited_admin["id"] + "/roles",
        "POST",
        {"role_id": rid["platform-administrator"]},
        department_admin,
        403,
    )
    request(
        "/api/v1/access/employees/" + limited_admin["id"] + "/effective-permissions",
        token=department_admin,
    )
    record(
        "Department-only administration cannot modify identity roles or protected platform capability"
    )
    restricted = request(
        "/api/v1/access/roles",
        "POST",
        {"name": "Self Restriction", "permissions": ["resources.view"]},
        admin,
        201,
    )
    request(
        "/api/v1/access/employees/" + manager["id"] + "/roles",
        "POST",
        {"role_id": restricted["id"], "effect": "DENY"},
        admin,
        201,
    )
    request(
        "/api/v1/access/roles/" + restricted["id"],
        "PATCH",
        {"name": "Self Restriction", "permissions": []},
        access,
        403,
    )
    inactive = request(
        "/api/v1/access/roles",
        "POST",
        {
            "name": "Inactive Own Role",
            "permissions": ["resources.update"],
            "active": False,
        },
        admin,
        201,
    )
    request(
        "/api/v1/access/employees/" + manager["id"] + "/roles",
        "POST",
        {"role_id": inactive["id"]},
        admin,
        201,
    )
    request(
        "/api/v1/access/roles/" + inactive["id"],
        "PATCH",
        {
            "name": "Inactive Own Role",
            "permissions": ["resources.update"],
            "active": True,
        },
        access,
        403,
    )
    protected_department = request(
        "/api/v1/access/departments",
        "POST",
        {"name": "Protected Inactive Department", "active": False},
        admin,
        201,
    )
    delegate_identity_view(limited_admin, [protected_department["id"]])
    request(
        "/api/v1/access/departments/" + protected_department["id"] + "/roles",
        "POST",
        {"role_id": rid["access-administrator"]},
        admin,
        201,
    )
    request(
        "/api/v1/access/departments/" + protected_department["id"],
        "PATCH",
        {"name": "Protected Inactive Department", "active": True},
        department_admin,
        403,
    )
    record(
        "DENY/inactive own roles cannot be edited to self-escalate; department reactivation checks protected delegation"
    )
    request(
        "/api/v1/access/departments",
        "POST",
        {"name": "Different Name", "code": "NOC"},
        admin,
        409,
    )
    request(
        "/api/v1/access/employees",
        "POST",
        {
            "username": "duplicate-employee-id",
            "full_name": "Duplicate",
            "employee_id": member["employee_id"],
            "password": f["admin_password"],
        },
        admin,
        409,
    )
    with SessionLocal() as db:
        try:
            db.execute(
                text("UPDATE users SET id=:new WHERE id=:id"),
                {"new": uuid.uuid4(), "id": member["id"]},
            )
            db.commit()
            raise AssertionError("Mutable employee UUID accepted")
        except DBAPIError:
            db.rollback()
    record(
        "Department codes/employee IDs are unique; both employee and department UUIDs are immutable"
    )
    request(
        "/api/v1/access/employees/" + other["id"], "PATCH", {"active": False}, admin
    )
    request("/api/v1/auth/me", token=south, expected=401)
    request(
        "/api/v1/auth/login",
        "POST",
        {"username": "access-other", "password": f["admin_password"]},
        expected=401,
    )
    record("Disabled employees cannot authenticate and prior sessions are unusable")
    worker = request(
        "/api/v1/auth/workers",
        "POST",
        {
            "organization_id": f["customer_a"],
            "name": "Access worker",
            "expires_in_days": 1,
        },
        admin,
        201,
    )
    request("/api/v1/access/employees", token=worker["worker_token"], expected=401)
    assert (
        request("/api/v1/worker/whoami", token=worker["worker_token"])[
            "organization_id"
        ]
        == f["customer_a"]
    )
    record(
        "Service identities retain exact customer identity and cannot retrieve internal employee APIs"
    )
    peer = employee("access-peer-administrator")
    request(
        "/api/v1/access/employees/" + peer["id"] + "/roles",
        "POST",
        {"role_id": rid["access-administrator"]},
        admin,
        201,
    )
    request(
        "/api/v1/access/employees/" + peer["id"] + "/password",
        "POST",
        {"new_password": f["admin_password"] + "-new"},
        access,
        403,
    )
    request(
        "/api/v1/access/employees/" + peer["id"],
        "PATCH",
        {"active": False},
        access,
        403,
    )
    request(
        "/api/v1/access/employees/" + peer["id"],
        "PATCH",
        {"full_name": "Altered administrative identity"},
        access,
        403,
    )
    request(
        "/api/v1/access/employees/" + peer["id"] + "/roles",
        "POST",
        {"role_id": rid["read-only-viewer"]},
        access,
        403,
    )
    assert request("/api/v1/access/employees/" + peer["id"], token=access)[
        "protected_administration"
    ]
    request(
        "/api/v1/access/departments/" + protected_department["id"],
        "PATCH",
        {"name": "Protected Inactive Department", "active": True},
        admin,
    )
    request(
        "/api/v1/access/departments/" + protected_department["id"],
        "PATCH",
        {"name": "Protected Inactive Department", "active": False},
        department_admin,
        403,
    )
    request(
        "/api/v1/access/departments/" + protected_department["id"],
        "PATCH",
        {"name": "Protected Inactive Department", "active": False},
        admin,
    )
    record(
        "Reserved administration credentials/account lifecycle and protected-department deactivation cannot bypass delegation authority"
    )
    reset_target = employee("access-password-reset")
    old_reset_token = login("access-password-reset")
    result = request(
        "/api/v1/access/employees/" + reset_target["id"] + "/password",
        "POST",
        {"new_password": f["admin_password"] + "-rotated"},
        access,
    )
    assert result["sessions_revoked"]
    request("/api/v1/auth/me", token=old_reset_token, expected=401)
    request(
        "/api/v1/auth/login",
        "POST",
        {"username": "access-password-reset", "password": f["admin_password"]},
        expected=401,
    )
    request(
        "/api/v1/auth/login",
        "POST",
        {
            "username": "access-password-reset",
            "password": f["admin_password"] + "-rotated",
        },
    )
    record(
        "Authorized ordinary employee password reset works, revokes all old sessions and rejects the prior password"
    )
    compatibility = employee("access-legacy-new")
    with SessionLocal() as db:
        legacy_row = OrganizationMembership(
            user_id=uuid.UUID(compatibility["id"]),
            organization_id=uuid.UUID(f["customer_b"]),
            role="viewer",
        )
        db.add(legacy_row)
        db.flush()
        legacy_id = str(legacy_row.id)
        db.commit()
    compatibility_token = login("access-legacy-new")
    listing = request(
        "/api/v1/access/customer-grants?user_id=" + compatibility["id"], token=admin
    )
    assert (
        listing["total"] == 1
        and listing["items"][0]["id"] == legacy_id
        and listing["items"][0]["source"] == "legacy_customer_membership"
    )
    assert (
        f["customer_b"]
        in request("/api/v1/auth/me", token=compatibility_token)["customer_permissions"]
    )
    request(
        "/api/v1/access/customer-grants/" + legacy_id,
        "DELETE",
        token=admin,
        expected=204,
    )
    assert (
        request("/api/v1/auth/me", token=compatibility_token)["customer_permissions"]
        == {}
    )
    record(
        "Post-migration legacy API/CLI memberships remain visible as customer grants and explicit revocation removes the authoritative source"
    )
    audit = request("/api/v1/access/audit?limit=200", token=admin)["items"]
    assert any(
        e["outcome"] == "DENIED" and e["actor_id"] == member["id"] for e in audit
    )
    assert all(
        e["actor_id"] and e["target_id"] and e["action"] and e["timestamp"]
        for e in audit
    )
    serialized = json.dumps(request("/api/v1/access/employees?limit=200", token=admin))
    assert "password_hash" not in serialized and f["admin_password"] not in serialized
    record(
        "Administrative audit records actor/target/action/outcome/time without credentials"
    )
    f.update(
        noc_id=member["id"],
        access_id=manager["id"],
        department_a=one["id"],
        department_b=two["id"],
        viewer_role=rid["read-only-viewer"],
        noc_username="access-noc",
        access_username="access-manager",
    )
    (PRIVATE / "fixture.json").write_text(json.dumps(f))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "security.json").write_text(
        json.dumps(
            {
                "status": "PASS",
                "checks": checks,
                "customer_resource_relationships_preserved": True,
                "legacy_source": "organization_memberships remains customer grant compatibility, never a department",
            },
            indent=2,
        )
    )
    print(
        "ACCESS MIGRATION / PROVIDER / DEPARTMENT / CUSTOMER RBAC SECURITY PASS ("
        + str(len(checks))
        + " check groups)"
    )


if __name__ == "__main__":
    main()
