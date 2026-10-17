"""Explicit request filters for controlled authenticated HTTP probes only."""

import json
from urllib.request import Request, urlopen


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
