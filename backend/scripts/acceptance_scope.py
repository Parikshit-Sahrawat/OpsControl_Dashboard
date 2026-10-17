"""Explicit request filters for controlled authenticated HTTP probes only."""

import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError


def selection_headers(base, token):
    root = base.split("/api/v1")[0].rstrip("/")
    with urlopen(
        Request(
            root + "/api/v1/auth/customer-scope",
            headers={"Authorization": "Bearer " + token},
        ),
        timeout=15,
    ) as response:
        ids = [r["id"] for r in json.load(response)]
    return {"X-OpsControl-Customers": ",".join(ids)}


def probe_headers(base, token, path):
    """Owned probes explicitly select the current directory snapshot, never ALL.

    Invalid-token and service-identity negative tests must reach their original
    handler. Do not turn a failed scope lookup into privileged fallback access.
    """
    if not token or path.startswith(
        ("/api/v1/auth", "/api/v1/access", "/api/v1/agent/", "/api/v1/worker/")
    ):
        return {}
    try:
        return selection_headers(base, token)
    except HTTPError as error:
        if error.code in {401, 403}:
            return {"X-OpsControl-Customers": ""}
        raise
