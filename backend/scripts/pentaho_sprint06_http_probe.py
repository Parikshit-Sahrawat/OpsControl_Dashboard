"""Authenticated HTTP acceptance using controlled native fixtures only."""

import os, json, uuid
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from app.security.passwords import hash_password
from tests.test_pentaho_incident_r1 import PentahoIncidentTests

assert (
    os.getenv("ENVIRONMENT") == "test" and os.getenv("OPSCONTROL_V16_ACCEPTANCE") == "1"
)
fixture = json.loads(
    (Path(os.environ["V16_PRIVATE_DIR"]) / "api-fixture.json").read_text()
)
base = os.environ["V16_API_URL"] + "/api/v1/"
checks = []


def request(path, method="GET", body=None, token=None, expected=200):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    try:
        with urlopen(
            Request(
                (
                    (os.environ["V16_API_URL"] + path)
                    if path.startswith("/")
                    else base + path
                ),
                data=json.dumps(body).encode() if body is not None else None,
                headers=headers,
                method=method,
            ),
            timeout=15,
        ) as response:
            status, data = response.status, json.load(response)
    except HTTPError as e:
        status, data = e.code, json.load(e)
    assert status == expected, (path, status, expected, data.get("detail"))
    return data


lab = PentahoIncidentTests(methodName="runTest")
foreign = PentahoIncidentTests(methodName="runTest")
try:
    lab.setUp()
    _, _, incident, _ = lab.recovered()
    foreign.setUp()
    _, _, other = foreign.failure()
    for user in (lab.user, lab.reviewer):
        user.password_hash = hash_password(fixture["viewer_password"])
    lab.db.commit()
    lab.grant(lab.user, ["incidents.view", "incidents.manage"])
    lab.grant(lab.reviewer, ["incidents.view"])

    def login(user):
        return request(
            "auth/login",
            "POST",
            {"username": user.username, "password": fixture["viewer_password"]},
        )["access_token"]

    editor, viewer = login(lab.user), login(lab.reviewer)
    path = "native-incidents/" + str(incident.id)
    request(path, expected=401)
    request("native-incidents/" + str(other.incident_id), token=editor, expected=404)
    visible = request(path, token=viewer)
    inventory = request("native-incidents?environment=TEST", token=viewer)
    assert str(incident.id) in {r["id"] for r in inventory["items"]}
    assert request("native-incidents?environment=PROD", token=viewer)["total"] == 0
    assert len(visible["execution_failures"]) == 1
    page = request(path + "/execution-failures?limit=1", token=viewer)
    assert page["total"] == 1 and len(page["items"]) == 1
    assert (
        visible["execution_failures"][0]["reassessment"]["action"]
        == "PRESERVE_ASSOCIATION_NO_REOPEN"
    )
    checks.append(
        "Authenticated customer scope, viewer detail, failure evidence and historical reassessment"
    )
    body = {
        "revision": visible["details"]["revision"],
        "idempotency_key": uuid.uuid4().hex,
        "observation_seconds": 60,
    }
    request(path + "/recovery-assessments", "POST", body, viewer, 403)
    saved = request(path + "/recovery-assessments", "POST", body, editor)
    assert saved["result"] == "VALIDATION_FAILED"
    assert (
        request(path + "/recovery-assessments", "POST", body, editor)["id"]
        == saved["id"]
    )
    request(
        path + "/recovery-assessments",
        "POST",
        {**body, "idempotency_key": uuid.uuid4().hex},
        editor,
        409,
    )
    request(
        path + "/recovery-assessments", "POST", {**body, "ready": True}, editor, 422
    )
    checks.append(
        "Explicit mutation permission, revision, idempotency and mass-assignment rejection"
    )
    proof = request(path + "/recovery-preview", token=viewer)
    assert not proof["ready"] and proof["evidence"]["candidates"]
    current = request(path, token=editor)
    request(
        path + "/transition",
        "POST",
        {"revision": current["details"]["revision"], "status": "RESOLVED"},
        editor,
        409,
    )
    assert len(current["recovery_assessments"]) == 1
    assert request(path + "/recovery-assessments?offset=1", token=viewer)["items"] == []
    assert any(a["event_type"] == "RECOVERY_ASSESSED" for a in current["activities"])
    checks.append(
        "Isolated successful execution cannot restore service; assessment audit persisted"
    )
    request(
        path + "/transition",
        "POST",
        {"revision": 1, "status": "INVESTIGATING"},
        editor,
        409,
    )
    request(
        path + "/transition",
        "POST",
        {"revision": current["details"]["revision"], "status": "INVESTIGATING"},
        viewer,
        403,
    )
    checks.append("Stale and unauthorized lifecycle mutations denied")
    doc = request("/openapi.json", token=editor)
    routes = [r for r in doc["paths"] if "native-incidents" in r]
    assert not any(
        any(control in r for control in ("/run", "/restart", "/cancel", "/execute"))
        for r in routes
    )
    checks.append("Native incident extension exposes no ETL workload controls")
    Path(os.environ["V16_EVIDENCE_DIR"], "pentaho-incident-http.json").write_text(
        json.dumps(
            {
                "status": "PASS",
                "checks": checks,
                "native_authority": "CONTROLLED_FIXTURE",
                "genuine_runtime_acceptance": False,
            },
            indent=2,
        )
    )
    print(f"Pentaho Sprint 06 actual HTTP acceptance PASS: {len(checks)} groups")
finally:
    lab.doCleanups()
    foreign.doCleanups()
