"""Real authenticated local HTTP; controlled native fixtures, no vendor access."""

import os, json, uuid
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from app.unified.schemas import ETLParameters, Schedule
from app.unified import pentaho_history as h
from app.security.passwords import hash_password
from app.data_pipelines.service import clock
from datetime import timedelta
from tests.test_pentaho_history_r1 import PentahoHistoryTests

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
        from scripts.acceptance_scope import selection_headers
        headers.update(selection_headers(base,token))
    try:
        with urlopen(
            Request(
                base + path,
                data=json.dumps(body).encode() if body is not None else None,
                headers=headers,
                method=method,
            ),
            timeout=10,
        ) as response:
            status, data = response.status, json.load(response)
    except HTTPError as e:
        status, data = e.code, json.load(e)
    assert status == expected, (path, status, expected, data.get("detail"))
    return data


def login(name):
    return request(
        "auth/login", "POST", {"username": name, "password": fixture["viewer_password"]}
    )["access_token"]


lab = PentahoHistoryTests(methodName="runTest")
foreign = PentahoHistoryTests(methodName="runTest")
try:
    lab.setUp()
    lab.enable_policy()
    event, history = lab.failure()
    foreign.setUp()
    lab.user.password_hash = hash_password(fixture["viewer_password"])
    lab.reviewer.password_hash = hash_password(fixture["viewer_password"])
    lab.db.commit()
    lab.grant(
        lab.user,
        [
            "etl.view",
            "etl.configure",
            "etl.replay",
            "templates.view",
            "templates.manage",
            "alerts.view",
            "resources.view",
        ],
    )
    lab.grant(
        lab.reviewer, ["etl.view", "etl.configure", "templates.view", "alerts.view"]
    )
    editor = login(lab.user.username)
    reviewer = login(lab.reviewer.username)
    prefix = f"unified/resources/{lab.resource.id}"
    request(prefix + "/historical-notifications", expected=401)
    body = {
        "enabled": True,
        "destination_ids": [str(lab.destination.id)],
        "historical_after_seconds": 60,
        "expected_revision": lab.resource.revision,
        "idempotency_key": uuid.uuid4().hex,
    }
    request(prefix + "/historical-notifications", "PUT", body, reviewer, 403)
    saved = request(prefix + "/historical-notifications", "PUT", body, editor)
    assert (
        request(prefix + "/historical-notifications", "PUT", body, editor)["revision"]
        == saved["revision"]
    )
    request(
        prefix + "/historical-notifications",
        "PUT",
        {**body, "idempotency_key": uuid.uuid4().hex},
        editor,
        409,
    )
    request(
        f"unified/resources/{foreign.resource.id}/historical-notifications",
        token=editor,
        expected=404,
    )
    checks.append(
        "Scoped policy save, existing-role denial, optimistic revision and idempotency; foreign resource denied"
    )
    cfg = ETLParameters(
        schedule=Schedule(frequency="DAILY", timezone="UTC", time="02:00"),
        pentaho_schedule_authority={
            "mode": "MONITORING_EXPECTATION",
            "revision": "configured-1",
        },
    ).model_dump(mode="json")
    parameter = {"configuration": cfg, "expected_resource_revision": saved["revision"]}
    request(f"unified/parameters/{lab.resource.id}", "POST", parameter, editor, 201)
    bad = {
        **cfg,
        "pentaho_schedule_authority": {
            "mode": "VERIFIED_SCHEDULER",
            "revision": "forged",
            "authority_id": "unverified",
            "evidence_id": str(lab.proof.id),
            "capability_id": str(lab.profile.id),
        },
    }
    request(
        f"unified/parameters/{lab.resource.id}/preview",
        "POST",
        {"configuration": bad, "expected_resource_revision": saved["revision"]},
        editor,
        409,
    )
    checks.append(
        "Monitoring expectation saves as a version; unverified native schedule proof cannot masquerade as scheduler authority"
    )
    now = clock(lab.db)
    recovery = {
        "start": (now - timedelta(hours=7)).isoformat(),
        "end": (now - timedelta(seconds=1)).isoformat(),
        "mode": "ACCEPTED_PENTAHO_EVIDENCE",
        "idempotency_key": uuid.uuid4().hex,
    }
    path = f"data-pipelines/sources/{lab.source.id}/recovery"
    request(path, "POST", recovery, reviewer, 403)
    plan = request(path, "POST", recovery, editor)
    assert plan["state"] == "APPROVAL_REQUIRED"
    approve = f'data-pipelines/operations/{plan["id"]}/approve'
    action = {"confirmed": True, "idempotency_key": uuid.uuid4().hex}
    request(approve, "POST", action, editor, 403)
    request(approve, "POST", action, reviewer, 403)
    lab.grant(lab.reviewer, ["etl.approve_replay"])
    assert request(approve, "POST", action, reviewer)["state"] == "APPROVED"
    provider = request(
        path,
        "POST",
        {
            k: v
            for k, v in {**recovery, "idempotency_key": uuid.uuid4().hex}.items()
            if k != "mode"
        },
        editor,
    )
    assert provider["state"] == "UNSUPPORTED"
    checks.append(
        "Bounded accepted-evidence replay needs explicit grant; beyond-bound independent approval; provider replay remains unsupported"
    )
    # Execute only the approved retained-evidence worker in this owned lab;
    # no provider/source collection or workload execution occurs.
    from app.unified.pentaho_replay import run
    from app.data_pipelines.models import PipelineOperation

    lab.db.expire_all()
    lab.source.next_run_at = clock(lab.db) + timedelta(minutes=1)
    before_checkpoint = dict(lab.source.live_checkpoint)
    lab.db.commit()
    run(uuid.UUID(plan["id"]))
    lab.db.expire_all()
    completed = lab.db.get(PipelineOperation, uuid.UUID(plan["id"]))
    assert completed.state == "COMPLETE" and completed.result["processed"] >= 1
    assert lab.source.live_checkpoint == before_checkpoint
    lab.db.expire_all()
    h.reconcile(lab.db, lab.resource)
    lab.db.commit()
    assert h.dispatch_notices(limit=1, organization_id=lab.org.id)["sent"] == 1
    notices = request(prefix + "/historical-notifications", token=editor)
    assert notices["total"] == 1 and notices["items"][0]["status"] == "SENT"
    inbox = request("notifications", token=editor)
    historical = [
        v for v in inbox["items"] if v.get("classification") == "HISTORICAL_FAILURE"
    ]
    assert len(historical) == 1 and historical[0]["alert_state_id"] is None
    assert (
        historical[0]["historical_evidence"]["occurred_at"]
        != historical[0]["historical_evidence"]["discovered_at"]
    )
    other = request("notifications", token=reviewer)
    assert not any(
        v.get("classification") == "HISTORICAL_FAILURE" for v in other["items"]
    )
    checks.append(
        "Durable historical inbox delivery, distinct occurrence/discovery, no fake live AlertState, recipient isolation"
    )
    Path(os.environ["V16_EVIDENCE_DIR"], "pentaho-history-http.json").write_text(
        json.dumps(
            {
                "status": "PASS",
                "checks": checks,
                "native_authority": "CONTROLLED_FIXTURE",
                "external_messages_sent": False,
                "genuine_runtime_acceptance": False,
            },
            indent=2,
        )
    )
    print(f"Pentaho Sprint 05 actual HTTP acceptance PASS: {len(checks)} groups")
finally:
    lab.doCleanups()
    foreign.doCleanups()
