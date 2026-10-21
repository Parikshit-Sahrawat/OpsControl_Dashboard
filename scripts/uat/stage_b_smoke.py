#!/usr/bin/env python3
"""Authenticated UAT-only smoke. Private config contains synthetic test accounts."""

import json
import os
from pathlib import Path
import stat
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def request(base, path, token=None, payload=None, customers=None):
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    if customers is not None:
        headers["X-OpsControl-Customers"] = customers
    if payload is not None:
        headers["Content-Type"] = "application/json"
    req = Request(
        base.rstrip("/") + path,
        json.dumps(payload).encode() if payload is not None else None,
        headers,
    )
    try:
        with urlopen(req, timeout=15) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        return error.code, None


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    path = Path(os.environ["STAGE_B_SMOKE_CONFIG"])
    if (
        not path.is_file()
        or path.is_symlink()
        or stat.S_IMODE(path.stat().st_mode) & 0o077
    ):
        raise ValueError("Private synthetic UAT smoke configuration required (0600)")
    config = json.loads(path.read_text())
    base = config["api_url"]
    viewer = config["viewer"]
    other = config["other_customer_id"]
    own = config["viewer_customer_id"]
    status, _ = request(base, "/api/v1/auth/me")
    require(status == 401, "Anonymous auth boundary failed")
    status, login = request(
        base,
        "/api/v1/auth/login",
        payload={"username": viewer["username"], "password": viewer["password"]},
    )
    require(status == 200 and login.get("access_token"), "Authentication failed")
    token = login["access_token"]
    status, me = request(base, "/api/v1/auth/me", token)
    require(
        status == 200 and me["username"] == viewer["username"],
        "Session projection failed",
    )
    status, customers = request(base, "/api/v1/auth/customer-scope", token)
    require(
        status == 200
        and own in {row["id"] for row in customers}
        and other not in {row["id"] for row in customers},
        "Customer scope failed",
    )
    status, resources = request(
        base,
        "/api/v1/unified/resources?limit=10&organization_id=" + own,
        token,
        customers=own,
    )
    require(
        status == 200
        and all(row["organization_id"] == own for row in resources["items"]),
        "Scoped inventory failed",
    )
    status, forged = request(
        base,
        "/api/v1/unified/resources?limit=10&organization_id=" + other,
        token,
        customers=other,
    )
    require(
        status in (200, 403, 404) and (status != 200 or not forged["items"]),
        "Forged customer leaked data",
    )
    status, _ = request(
        base, "/api/v1/operations/services?organization_id=" + own, token, customers=own
    )
    require(status == 200, "Monitoring projection failed")
    status, _ = request(base, "/api/v1/monitoring/organizations", token, customers=own)
    require(status in (200, 403), "Unexpected inventory response")
    status, _ = request(base, "/api/v1/organizations", token, payload={}, customers=own)
    require(status == 403, "Read-only employee reached customer mutation contract")
    print(
        "PASS: API, authentication, session, customer isolation, RBAC and monitoring smoke"
    )


if __name__ == "__main__":
    main()
