"""Integration assertions for security release hardening.

Run *after* auth_tenant_probe.py against a disposable PostgreSQL and API.
Fixtures never use real infrastructure, people or credentials.
"""
import json
import urllib.request
import urllib.error
from sqlalchemy import select, func, update
from app.db.session import SessionLocal
from app.security.models import User, OrganizationMembership, WorkerIdentity, SecurityAuditEvent
from app.models import DataSource

URL = "http://127.0.0.1:8000"
PASSWORD = "testing-only-StrongPassword-123!"

def request(method, path, token=None, payload=None):
    headers = {"Content-Type": "application/json"}
    if token: headers["Authorization"] = "Bearer " + token
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(URL + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read() or b"null") if r.status != 204 else None, {k.lower(): v for k, v in r.headers.items()}
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null"), {k.lower(): v for k, v in e.headers.items()}

def check(expected, method, path, token=None, payload=None):
    got, result, headers = request(method, path, token, payload)
    assert got == expected, (method, path, expected, got, result)
    print("PASS", expected, method, path)
    return result, headers

def login(username, password=PASSWORD):
    result, _ = check(200, "POST", "/api/v1/auth/login", payload={"username":username, "password":password})
    return result["access_token"]

def main():
    admin = login("test-admin")
    _, headers = check(200, "GET", "/api/v1/auth/me", admin)
    assert headers.get("x-content-type-options") == "nosniff", headers
    assert headers.get("x-frame-options") == "DENY", headers
    assert headers.get("cache-control") == "no-store", headers
    users,_ = check(200,"GET","/api/v1/auth/users",admin)
    north = next(u for u in users if u["username"]=="test-north")
    south = next(u for u in users if u["username"]=="test-south")
    platform = next(u for u in users if u["username"]=="test-admin")
    with SessionLocal() as db:
        memberships = db.scalars(select(OrganizationMembership)).all()
        a = next(m.organization_id for m in memberships if str(m.user_id)==north["id"])
        b = next(m.organization_id for m in memberships if str(m.user_id)==south["id"])


    # Deny embedded secrets and never echo rejected inputs in validation errors.
    unsafe={"organization_id":str(a),"name":"unsafe-source","source_type":"API",
            "connection_config":{"nested":{"password":"forbidden-plain-secret-123"}}}
    result,_=check(422,"POST","/api/v1/resource-management/data-sources",admin,unsafe)
    assert "forbidden-plain-secret-123" not in json.dumps(result)
    unsafe={"organization_id":str(a),"name":"unsafe-url","source_type":"API",
            "endpoint":"https://user:forbidden-url-secret@service.example.test"}
    result,_=check(422,"POST","/api/v1/resource-management/data-sources",admin,unsafe)
    assert "forbidden-url-secret" not in json.dumps(result)
    with SessionLocal() as db:
        existing=db.scalar(select(DataSource).where(DataSource.organization_id==a))
        existing.connection_config={"password":"legacy-private-value","credential_ref":"secret://synthetic/read-only"}
        existing.endpoint="https://user:legacy-url-private@example.test"
        db.commit()
    sources,_=check(200,"GET","/api/v1/resource-management/data-sources",admin)
    serialized_sources=json.dumps(sources)
    assert "legacy-private-value" not in serialized_sources
    assert "legacy-url-private" not in serialized_sources
    assert "[REDACTED]" in serialized_sources

    # Never allow a viewer to access the platform security administration APIs.
    viewer = login("test-reader")
    check(403,"GET","/api/v1/auth/users",viewer)
    check(403,"GET","/api/v1/auth/audit",viewer)
    check(403,"POST","/api/v1/auth/workers",viewer,{"name":"forged","organization_id":str(a)})
    check(401,"GET","/api/v1/auth/me","synthetic-wrong-token")
    check(409,"PATCH",f"/api/v1/auth/users/{platform['id']}/status",admin,{"active":False})

    # A platform admin can create, rotate credentials, and disable identities.
    user,_ = check(201,"POST","/api/v1/auth/users",admin,
                   {"username":"temporary-security-lab","password":PASSWORD,"platform_admin":False})
    uid=user["id"]
    membership,_=check(201,"POST","/api/v1/auth/memberships",admin,
                       {"user_id":uid,"organization_id":str(a),"role":"viewer"})
    user_token=login("temporary-security-lab")
    check(403,"POST","/api/v1/organizations",user_token,{"name":"forged","code":"FORGED"})
    check(200,"PATCH",f"/api/v1/auth/memberships/{membership['id']}",admin,{"role":"operator"})
    check(401,"GET","/api/v1/auth/me",user_token)
    memberships,_=check(200,"GET","/api/v1/auth/memberships",admin)
    assert any(m["id"]==membership["id"] and m["role"]=="operator" for m in memberships)
    check(204,"DELETE",f"/api/v1/auth/memberships/{membership['id']}",admin)
    check(200,"POST",f"/api/v1/auth/users/{uid}/password",admin,{"new_password":"NewSecurityOnlyPassphrase123!"})
    check(401,"POST","/api/v1/auth/login",payload={"username":"temporary-security-lab","password":PASSWORD})
    check(200,"PATCH",f"/api/v1/auth/users/{uid}/status",admin,{"active":False})
    check(401,"POST","/api/v1/auth/login",payload={"username":"temporary-security-lab","password":"NewSecurityOnlyPassphrase123!"})

    # Worker service tokens are scoped, isolated and revocable, not user tokens.
    worker,_=check(201,"POST","/api/v1/auth/workers",admin,
                   {"name":"synthetic-agent","organization_id":str(a),"expires_in_days":1})
    wk=worker["worker_token"]
    claims,_=check(200,"GET","/api/v1/worker/whoami",wk)
    assert claims["organization_id"]==str(a),claims
    check(401,"GET","/api/v1/auth/me",wk)
    check(401,"GET","/api/v1/worker/whoami",admin)
    check(204,"DELETE",f"/api/v1/auth/workers/{worker['id']}",admin)
    check(401,"GET","/api/v1/worker/whoami",wk)

    # Failed login throttling shared by all API processes via PostgreSQL.
    for index in range(10):
        check(401,"POST","/api/v1/auth/login",
              payload={"username":"unknown-lockout-lab","password":"bad-password"})
    _,hdr = check(429,"POST","/api/v1/auth/login",
                  payload={"username":"unknown-lockout-lab","password":"bad-password"})
    assert hdr.get("retry-after")=="900",hdr
    # Valid admin session is not affected by a different username bucket.
    check(200,"GET","/api/v1/auth/me",admin)

    audit,_=check(200,"GET","/api/v1/auth/audit",admin)
    kinds = {event["event_type"] for event in audit}
    assert {"LOGIN", "LOGIN_RATE_LIMIT", "USER_CREATE", "MEMBERSHIP_CREATE",
            "MEMBERSHIP_ROLE", "MEMBERSHIP_DELETE", "PASSWORD_RESET",
            "WORKER_CREATE", "WORKER_REVOKE", "HTTP_AUTH_DENIED"} <= kinds, kinds
    serialized=json.dumps(audit)
    assert PASSWORD not in serialized and wk not in serialized and "bad-password" not in serialized
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(SecurityAuditEvent)) >= len(audit)
        # Reject direct updates to protected security events.
        try:
            db.execute(update(SecurityAuditEvent).values(outcome="SUCCESS"))
            db.commit()
            raise AssertionError("Audit mutation was permitted")
        except Exception as error:
            db.rollback()
            assert "append-only" in str(error), str(error)
        assert db.scalar(select(func.count()).select_from(WorkerIdentity).where(WorkerIdentity.enabled.is_(False))) >= 1
    print("SECURITY RELEASE HARDENING NEGATIVE TESTS PASS")

if __name__=="__main__":
    main()
