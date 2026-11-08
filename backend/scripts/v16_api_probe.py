"""Actual scoped HTTP workflow in the owned lab; no vendor connection requests."""

import json, os, uuid
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from pathlib import Path
import app.main  # noqa: F401 - register existing parent models for fixture transactions
from app.db.session import SessionLocal
from sqlalchemy import select
from app.models import Organization
from app.security.models import User, OrganizationMembership
from app.security.passwords import hash_password
from app.security.permission_catalog import PROVIDER_ID
from app.data_pipelines.models import PipelineIntegration

assert (
    os.getenv("ENVIRONMENT") == "test" and os.getenv("OPSCONTROL_V16_ACCEPTANCE") == "1"
), "Owned disposable test environment required"
private = Path(os.environ["V16_PRIVATE_DIR"])
fixture = json.loads((private / "api-fixture.json").read_text())
base = os.environ["V16_API_URL"]
checks = []


def request(path, method="GET", payload=None, token=None, expected=200):
    headers = {}
    if token:
        headers["Authorization"] = "Bearer " + token
        from scripts.acceptance_scope import selection_headers
        headers.update(selection_headers(base,token))
    if method in {"POST", "PATCH", "DELETE"} and path.startswith("monitoring/data-sources/") and "/templates" in path and token and expected not in {403,404}:
        source_id = path.split("/")[2]
        head = request(f"monitoring/data-sources/{source_id}/configuration", token=token)
        headers.update({"Expected-Revision":str(head["revision"]),"Idempotency-Key":str(uuid.uuid4())})
    if method == "PATCH" and expected == 200 and token and len(path.split("/")) == 3 and path.split("/")[0] in {"monitoring", "resource-management"} and path.split("/")[1] == "data-sources":
        source_id = path.split("/")[2]
        head = request(f"monitoring/data-sources/{source_id}/configuration", token=token)
        headers.update({"Expected-Revision":str(head["revision"]),"Idempotency-Key":str(uuid.uuid4())})
    body = json.dumps(payload).encode() if payload is not None else None
    if body is not None:
        headers["Content-Type"] = "application/json"
    try:
        response = urlopen(
            Request(
                base + "/api/v1/" + path, data=body, headers=headers, method=method
            ),
            timeout=15,
        )
        status = response.status
        data = None if status == 204 else json.load(response)
    except HTTPError as error:
        status = error.code
        raw = error.read()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            if status != 500 or expected != 500:
                raise
            data = {"detail": "Expected injected server failure (non-JSON response)"}
    if status != expected:
        (private / "api-error.json").write_text(
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


def mutate(payload=None):
    return {"idempotency_key": str(uuid.uuid4()), **(payload or {})}


with SessionLocal() as db:
    a = Organization(
        name="Controlled HTTP A " + uuid.uuid4().hex,
        code="HTTP-A-" + uuid.uuid4().hex[:8],
        active=True,
    )
    b = Organization(
        name="Controlled HTTP B " + uuid.uuid4().hex,
        code="HTTP-B-" + uuid.uuid4().hex[:8],
        active=True,
    )
    admin = User(
        username="v16-api-admin",
        password_hash=hash_password(fixture["password"]),
        full_name="Controlled API Administrator",
        platform_admin=True,
        active=True,
        service_provider_id=PROVIDER_ID,
    )
    viewer = User(
        username="v16-api-viewer",
        password_hash=hash_password(fixture["viewer_password"]),
        full_name="Controlled Viewer",
        platform_admin=False,
        active=True,
        service_provider_id=PROVIDER_ID,
    )
    reviewer = User(
        username="v16-api-reviewer",
        password_hash=hash_password(fixture["viewer_password"]),
        full_name="Controlled Independent Reviewer",
        platform_admin=True,
        active=True,
        service_provider_id=PROVIDER_ID,
    )
    db.add_all([a, b, admin, viewer, reviewer])
    db.flush()
    db.add(
        OrganizationMembership(user_id=viewer.id, organization_id=a.id, role="viewer")
    )
    db.commit()
    aid = str(a.id)
    bid = str(b.id)
admin = request(
    "auth/login", "POST", {"username": "v16-api-admin", "password": fixture["password"]}
)["access_token"]
viewer = request(
    "auth/login",
    "POST",
    {"username": "v16-api-viewer", "password": fixture["viewer_password"]},
)["access_token"]
catalogue = request("data-pipelines/catalogue", token=admin)
assert len(catalogue["platforms"]) == 9
assert all(
    candidate["compatibility"] == "UNVERIFIED"
    for platform in catalogue["platforms"]
    for candidate in platform["versions"]
)
checks.append(
    "Nine platform catalogue candidates remain unverified; no runtime certification from metadata"
)
body = mutate(
    {
        "name": "Controlled multi-job integration",
        "organization_id": aid,
        "platform": "AIRFLOW",
        "environment": "TEST",
        "configuration": {"wizard_inputs": {"note": "controlled draft"}},
        "stage": 3,
    }
)
integration = request("data-pipelines/integrations", "POST", body, admin, 201)
retry = request("data-pipelines/integrations", "POST", body, admin, 201)
assert retry["id"] == integration["id"]
id = integration["id"]
checks.append(
    "Integration create/retry is idempotent and draft stage/configuration persist"
)
connection = request(
    f"data-pipelines/integrations/{id}/connections",
    "POST",
    mutate(
        {
            "configuration": {
                "base_url": "https://airflow.example.test",
                "credential_ref": "env:OPSCONTROL_PIPELINE_SECRET_"
                + uuid.UUID(aid).hex.upper()
                + "_TOKEN",
            }
        }
    ),
    admin,
    201,
)
profile = request(
    f"data-pipelines/integrations/{id}/capabilities",
    "POST",
    mutate(
        {
            "platform_version": "2.10",
            "edition": "Operator supplied",
            "deployment_type": "Self-hosted",
            "supported_methods": ["PLATFORM_API"],
        }
    ),
    admin,
    201,
)
assert (
    profile["compatibility"] == "UNVERIFIED"
    and profile["evidence_status"] != "RUNTIME_VERIFIED"
)
methods = []
for scope in ("cluster-a", "cluster-b"):
    methods.append(
        request(
            f"data-pipelines/integrations/{id}/methods",
            "POST",
            mutate(
                {
                    "name": scope,
                    "method_type": "PLATFORM_API",
                    "transport": "BACKEND",
                    "identity": {
                        "platform": "AIRFLOW",
                        "endpoint": "https://airflow.example.test",
                        "account": "controlled-account",
                        "physical_scope": scope,
                    },
                    "connection_id": connection["id"],
                    "capability_id": profile["id"],
                    "configuration": {},
                }
            ),
            admin,
            201,
        )
    )
assert methods[0]["source_id"] != methods[1]["source_id"]
checks.append(
    "Independent same-type collection methods have stable distinct physical units"
)
job = request(
    f"data-pipelines/integrations/{id}/jobs",
    "POST",
    mutate({"native_id": "dag-stable-1", "name": "Controlled DAG"}),
    admin,
    201,
)
assert not job["selected"]
selected = request(
    f'data-pipelines/jobs/{job["id"]}/selection',
    "POST",
    mutate({"selected": True, "confirmed": True, "expected_revision": job["revision"]}),
    admin,
)
assert selected["resource_id"] and selected["selected"]
association = request(
    f"data-pipelines/integrations/{id}/associations",
    "POST",
    mutate({"job_id": job["id"], "method_id": methods[0]["id"], "confirmed": True}),
    admin,
    201,
)
assert association["generation"]
checks.append(
    "Manual job requires explicit selection and confirmed generation-bound source association"
)
result = request(f"data-pipelines/integrations/{id}/validate", "POST", {}, admin)
assert not result["eligible"] and any(
    "RUNTIME_VERIFIED" in code for code in result["blockers"]
)
request(
    f"data-pipelines/integrations/{id}/activate",
    "POST",
    mutate({"confirmed": True}),
    admin,
    409,
)
request(
    f'unified/resources/{selected["resource_id"]}/activate',
    "POST",
    {"approve": True},
    admin,
    409,
)
checks.append(
    "Unverified methods blocked by V1.6 activation and legacy activation bypass"
)
request(
    f"data-pipelines/integrations/{id}/connections",
    "POST",
    mutate({"configuration": {"password": "controlled-forbidden-plaintext"}}),
    admin,
    409,
)
with SessionLocal() as db:
    wrong = PipelineIntegration(
        organization_id=uuid.UUID(bid),
        name="Other scope",
        platform="AIRFLOW",
        environment="TEST",
        owner_id=uuid.UUID(integration["owner_id"]),
        configuration={},
    )
    db.add(wrong)
    db.commit()
    wrongid = str(wrong.id)
visible = request("data-pipelines/integrations", token=viewer)
assert all(item["organization_id"] == aid for item in visible["items"])
request(f"data-pipelines/integrations/{wrongid}", token=viewer, expected=404)
request(
    "data-pipelines/integrations",
    "POST",
    mutate(
        {
            "name": "Unauthorized",
            "organization_id": bid,
            "platform": "AIRFLOW",
            "environment": "TEST",
        }
    ),
    viewer,
    403,
)
request("access/users", token=viewer, expected=403)
checks.append(
    "Customer isolation, direct RBAC denial and indirect employee access remain enforced"
)
request(
    "agent/pipeline-claim", "POST", {"source_id": methods[0]["source_id"]}, admin, 401
)
checks.append("Human session cannot impersonate source-bound Agent")
# Genuine HTTP independent review, generation fencing and full method rollback.
reviewer_token = request(
    "auth/login",
    "POST",
    {"username": "v16-api-reviewer", "password": fixture["viewer_password"]},
)["access_token"]
source_id = methods[0]["source_id"]
change = request(
    f"data-pipelines/sources/{source_id}/change-preview",
    "POST",
    mutate({"configuration": {"method_configuration": {"interval_seconds": 30}}}),
    admin,
)
request(
    f'data-pipelines/operations/{change["id"]}/approve',
    "POST",
    mutate({"confirmed": True}),
    admin,
    403,
)
request(
    f'data-pipelines/operations/{change["id"]}/approve',
    "POST",
    mutate({"confirmed": True}),
    reviewer_token,
)
applied = request(
    f'data-pipelines/operations/{change["id"]}/apply',
    "POST",
    mutate({"confirmed": True}),
    admin,
)
assert applied["state"] == "COMPLETE"
detail = request(f"data-pipelines/integrations/{id}", token=admin)
changed = next(m for m in detail["methods"] if m["id"] == methods[0]["id"])
assert changed["configuration"]["interval_seconds"] == 30
assert any(
    "JOB_SOURCE_ASSOCIATION_REQUIRED" in value
    for value in detail["activation_blockers"]
)
rollback = request(
    f'data-pipelines/operations/{change["id"]}/rollback-preview',
    "POST",
    mutate(),
    admin,
)
request(
    f'data-pipelines/operations/{rollback["id"]}/approve',
    "POST",
    mutate({"confirmed": True}),
    reviewer_token,
)
request(
    f'data-pipelines/operations/{rollback["id"]}/apply',
    "POST",
    mutate({"confirmed": True}),
    admin,
)
detail = request(f"data-pipelines/integrations/{id}", token=admin)
restored = next(m for m in detail["methods"] if m["id"] == methods[0]["id"])
assert restored["configuration"] == methods[0]["configuration"]
assert restored["validation"] == "UNVALIDATED"
assert restored["connection_id"] == methods[0]["connection_id"]
assert (
    next(x for x in detail["sources"] if x["id"] == source_id)["generation"]
    != association["generation"]
)
checks.append(
    "Independent review rejects self-approval; handoff invalidates old associations; rollback restores method configuration without fabricating eligibility"
)
# Lossless legacy transition: staged mapping has no implicit activation.
from app.models import DataSource, Collector, JobOrder
from app.unified.models import MonitoringResource
from app.registry.models import CollectorRuntimeState

with SessionLocal() as db:
    ds = DataSource(
        organization_id=uuid.UUID(aid),
        name="Controlled legacy source",
        source_type="AIRFLOW",
        enabled=True,
        connection_config={},
    )
    order = JobOrder(
        organization_id=uuid.UUID(aid),
        name="controlled-legacy-chain",
        environment="TEST",
        monitoring_enabled=True,
    )
    db.add_all([ds, order])
    db.flush()
    old_collector = Collector(
        data_source_id=ds.id,
        name="Controlled legacy collector",
        collector_type="PIPELINE_NATIVE",
        enabled=True,
        configuration={"platform": "AIRFLOW"},
        interval_seconds=60,
    )
    db.add(old_collector)
    db.flush()
    old_resource = db.get(MonitoringResource, order.id)
    if old_resource is not None:
        old_resource.name = "Controlled legacy job"
        old_resource.data_source_id = ds.id
        old_resource.primary_collector_id = old_collector.id
        old_resource.configuration = {
            "platform": "AIRFLOW",
            "jobchain": "controlled-legacy-chain",
        }
        old_resource.activation_status = "ACTIVE"
        old_resource.active = True
    else:
        old_resource = MonitoringResource(
            id=order.id,
            organization_id=uuid.UUID(aid),
            domain="ETL",
            name="Controlled legacy job",
            environment="TEST",
            job_order_id=order.id,
            data_source_id=ds.id,
            primary_collector_id=old_collector.id,
            configuration={
                "platform": "AIRFLOW",
                "jobchain": "controlled-legacy-chain",
            },
            active=True,
            activation_status="ACTIVE",
        )
    db.add_all(
        [
            old_resource,
            CollectorRuntimeState(
                collector_id=old_collector.id,
                organization_id=uuid.UUID(aid),
                checkpoint={"preserved_cursor": 73},
            ),
        ]
    )
    db.commit()
    old_resource_id, old_collector_id = str(old_resource.id), str(old_collector.id)
legacy_job = request(
    f"data-pipelines/integrations/{id}/jobs",
    "POST",
    mutate(
        {
            "native_id": "legacy-native-guid",
            "name": "Controlled legacy job",
            "resource_id": old_resource_id,
        }
    ),
    admin,
    201,
)
assert legacy_job["quarantined"] and not legacy_job["selected"]
request(
    f'data-pipelines/jobs/{legacy_job["id"]}/selection',
    "POST",
    mutate(
        {
            "selected": True,
            "confirmed": True,
            "expected_revision": legacy_job["revision"],
        }
    ),
    admin,
    409,
)
request(
    f"data-pipelines/integrations/{id}/associations",
    "POST",
    mutate(
        {"job_id": legacy_job["id"], "method_id": methods[0]["id"], "confirmed": True}
    ),
    admin,
    201,
)
transition = request(
    f"data-pipelines/sources/{source_id}/change-preview",
    "POST",
    mutate({"configuration": {"legacy_collector_id": old_collector_id}}),
    admin,
)
request(
    f'data-pipelines/operations/{transition["id"]}/approve',
    "POST",
    mutate({"confirmed": True}),
    reviewer_token,
)
request(
    f'data-pipelines/operations/{transition["id"]}/apply',
    "POST",
    mutate({"confirmed": True}),
    admin,
)
with SessionLocal() as db:
    kept = db.get(MonitoringResource, uuid.UUID(old_resource_id))
    assert (
        str(kept.id) == old_resource_id
        and str(kept.primary_collector_id) == old_collector_id
    )
    assert (
        kept.configuration["native_job_id"] == "legacy-native-guid"
        and kept.activation_status == "CONFIGURED"
    )
    assert (
        db.get(Collector, uuid.UUID(old_collector_id)).collector_type
        == "PIPELINE_V16_PROXY"
    )
    assert db.get(CollectorRuntimeState, uuid.UUID(old_collector_id)).checkpoint == {
        "preserved_cursor": 73
    }
    from app.data_pipelines.models import PipelineSource, PipelineJob

    assert db.get(PipelineSource, uuid.UUID(source_id)).live_checkpoint["jobs"][
        "legacy-native-guid"
    ] == {"preserved_cursor": 73}
    migrated = db.get(PipelineJob, uuid.UUID(legacy_job["id"]))
    assert not migrated.quarantined and not migrated.selected
    assert not db.get(JobOrder, uuid.UUID(old_resource_id)).monitoring_enabled
checks.append(
    "Reviewed legacy handoff preserves resource/collector/JobOrder UUIDs and original checkpoint; staged identity cannot activate implicitly"
)
# Sprint1 lifecycle checks use real authentication, scope hooks and PostgreSQL.
source = request("resource-management/data-sources", "POST", {"organization_id": aid, "name": "Sprint lifecycle", "source_type": "LINUX", "enabled": True}, admin, 201)
sid = source["id"]
collector = request("resource-management/collectors", "POST", {"data_source_id": sid, "name": "Sprint collector", "collector_type": "HTTP", "enabled": False, "interval_seconds": 60, "configuration": {}}, admin, 201)
request(f"resource-management/data-sources/{sid}", "PATCH", {"organization_id": bid}, admin, 422)
request(f"resource-management/data-sources/{sid}", "PATCH", {"name": "forbidden"}, viewer, 403)
request(f"resource-management/data-sources/{sid}", "PATCH", {"enabled": False}, admin)
for route in ("resource-management", "monitoring"):
    request(f"{route}/collectors/{collector['id']}", "PATCH", {"enabled": True}, admin, 409)
with SessionLocal() as db:
    from app.models import DataSource, Collector
    persisted = db.get(DataSource, uuid.UUID(sid))
    assert str(persisted.organization_id) == aid and not persisted.enabled
    assert not db.get(Collector, uuid.UUID(collector["id"])).enabled
checks.append("Sprint1: protected ownership fields, viewer denial, disabled-parent collector enable refusal on both APIs and persisted unchanged ownership")
# Template lifecycle uses the same authenticated API and immutable version rows.
applicability = {"schema_version":1,"source_types":["LINUX"],"os":["Linux"],"methods":[{"name":"Host metrics","method_type":"HOST_METRICS","configuration":{"scrapers":["cpu"],"interval_seconds":30}}],"collector_override_fields":["interval_seconds"]}
template = request("monitoring/templates", "POST", {"name":"Sprint template " + uuid.uuid4().hex, "package_config":{"applicability":applicability,"attributes":[{"key":"team","required":True}],"collector":{"type":"OTEL"}}}, admin, 201)
tid = template["id"]
request(f"monitoring/data-sources/{sid}/templates", "POST", {"template_id":tid,"template_version":1}, admin, 422)
request(f"resource-management/data-sources/{sid}", "PATCH", {"connection_config":{"opscontrol":{"attributes":{"team":"controlled"}}}}, admin)
request(f"monitoring/data-sources/{sid}/templates", "POST", {"template_id":tid,"template_version":1}, admin, 201)
request(f"monitoring/templates/{tid}", "PATCH", {"package_config":{"collector":{"type":"HTTP","interval_seconds":90}}}, admin)
effective = request(f"monitoring/data-sources/{sid}/effective-configuration", token=admin)
assert effective["templates"][0]["version"] == 1 and effective["valid"] and not effective["missing_required_attributes"]
request(f"resource-management/data-sources/{sid}", "PATCH", {"connection_config":{"opscontrol":{"attributes":{"team":"controlled"},"monitoring_overrides":{"collector":{"interval_seconds":30}}}}}, admin, 428)
request(f"monitoring/data-sources/{sid}/templates/{tid}", "PATCH", {"overrides":{"collector":{"interval_seconds":30}}}, admin)
effective = request(f"monitoring/data-sources/{sid}/effective-configuration", token=admin)
assert effective["valid"] and effective["collector"]["interval_seconds"] == 30 and effective["templates"][0]["version"] == 1
versions = request(f"monitoring/templates/{tid}/versions", token=admin)
assert {v["version"] for v in versions} == {1,2}
request("monitoring/collectors", "POST", {"data_source_id":sid,"name":"forbidden enabled legacy collector","collector_type":"HTTP","enabled":True,"interval_seconds":60,"configuration":{}},admin,409)
request(f"monitoring/data-sources/{sid}/templates/{tid}", "PATCH", {"priority":200},viewer,403)
request(f"monitoring/data-sources/{sid}/templates/{tid}", "PATCH", {"overrides":{"metrics":"invalid"}},admin,422)
request("monitoring/templates", "POST", {"name":"invalid shape","package_config":{"collector":[]}},admin,422)
other_source=request("resource-management/data-sources","POST",{"organization_id":bid,"name":"Other template scope "+uuid.uuid4().hex,"source_type":"LINUX"},admin,201)
request(f"monitoring/data-sources/{other_source['id']}/templates", "POST", {"template_id":tid,"template_version":1},viewer,403)
from concurrent.futures import ThreadPoolExecutor as TemplatePool
with TemplatePool(max_workers=2) as pool:
    jobs=[pool.submit(request,f"monitoring/templates/{tid}","PATCH",{"package_config":{"collector":{"type":"HTTP","interval_seconds":interval}}},admin) for interval in (40,50)]
    committed=[future.result()["version"] for future in jobs]
assert set(committed)=={3,4}
assert request(f"monitoring/data-sources/{sid}/effective-configuration",token=admin)["templates"][0]["version"]==1
checks.append("Template immutable v1 pin survives v2 commit; required attributes and source overrides resolve; original versions retained; viewer mutation and disabled-parent legacy creation denied")
# Role edits revoke prior sessions; stale callers cannot mutate a resource.
with SessionLocal() as db:
    user = db.scalar(select(User).where(User.username == "v16-api-viewer"))
    membership = db.scalar(select(OrganizationMembership).where(OrganizationMembership.user_id == user.id))
    membership_id = str(membership.id)
request(f"auth/memberships/{membership_id}", "PATCH", {"role":"org_admin"}, admin)
try:
    urlopen(Request(base+f"/api/v1/resource-management/data-sources/{sid}", method="PATCH",data=json.dumps({"name":"stale forbidden"}).encode(),headers={"Authorization":"Bearer "+viewer,"Content-Type":"application/json","X-OpsControl-Customers":aid}),timeout=10)
    raise AssertionError("revoked session accepted")
except HTTPError as error:
    assert error.code == 401
writer = request("auth/login", "POST", {"username":"v16-api-viewer", "password":fixture["viewer_password"]})["access_token"]
request(f"resource-management/data-sources/{sid}", "PATCH", {"description":"authorized before revocation"}, writer)
# Queue revocation before a mutation at the existing transaction-authority lock.
from app.db.session import engine
from sqlalchemy import text as sql_text
import time as race_time
from concurrent.futures import ThreadPoolExecutor as RacePool

def raw_mutation():
    try:
        with urlopen(Request(base+f"/api/v1/resource-management/data-sources/{sid}", method="PATCH",data=json.dumps({"description":"forbidden concurrent"}).encode(),headers={"Authorization":"Bearer "+writer,"Content-Type":"application/json","X-OpsControl-Customers":aid}),timeout=20) as response:
            return response.status
    except HTTPError as error:
        return error.code

def wait_authority_queue(count):
    for _ in range(500):
        with engine.connect() as poll:
            waiting=poll.scalar(sql_text("SELECT count(*) FROM pg_locks WHERE locktype='advisory' AND classid=782104 AND objid=8 AND NOT granted"))
        if waiting>=count:return
        race_time.sleep(.01)
    raise AssertionError("Expected transaction authority waiter did not reach PostgreSQL lock")

with RacePool(max_workers=2) as pool:
    with engine.begin() as blocker:
        blocker.execute(sql_text("SELECT pg_advisory_xact_lock(782104,8)"))
        revocation=pool.submit(request,f"auth/memberships/{membership_id}","PATCH",{"role":"viewer"},admin)
        wait_authority_queue(1)
        mutation=pool.submit(raw_mutation)
        wait_authority_queue(2)
    assert revocation.result()["sessions_revoked"]
    denied_status=mutation.result()
    assert denied_status in (401,403), denied_status
with SessionLocal() as db:
    assert db.get(DataSource,uuid.UUID(sid)).description=="authorized before revocation"
checks.append("Actual PostgreSQL queued revocation/update race: prior authorized writer succeeds, revocation commits first, waiting mutation401/403 with no committed partial change")

with SessionLocal() as db:
    assert db.get(DataSource,uuid.UUID(sid)).name != "stale forbidden"
checks.append("Membership role mutation revokes old session; actual stale authenticated PATCH401; no committed resource mutation; viewer role restored")
# OC-DEV-002C: real optimistic update conflict, concurrent writers and rollback.
attachment_path = f"monitoring/data-sources/{sid}/templates/{tid}"
original = request(f"monitoring/data-sources/{sid}/templates", token=admin)[0]
revision = original["updated_at"]
source_revision=request(f"monitoring/data-sources/{sid}/configuration",token=admin)["revision"]
with TemplatePool(max_workers=2) as pool:
    def edit_attachment(priority):
        try:
            headers={"Authorization":"Bearer "+admin,"Expected-Revision":str(source_revision),"Idempotency-Key":str(uuid.uuid4())}
            from scripts.acceptance_scope import selection_headers
            headers.update(selection_headers(base,admin));headers["Content-Type"]="application/json"
            with urlopen(Request(base+"/api/v1/"+attachment_path,method="PATCH",headers=headers,data=json.dumps({"expected_updated_at":revision,"priority":priority}).encode()),timeout=20) as response:
                return response.status,json.load(response)
        except HTTPError as error:
            return error.code,json.load(error)
    competing=list(pool.map(edit_attachment,(301,302)))
assert sorted(status for status,_ in competing)==[200,409],competing
winner=request(f"monitoring/data-sources/{sid}/templates",token=admin)[0]
assert winner["priority"] in (301,302) and winner["template_version"]==1
before_effective=request(f"monitoring/data-sources/{sid}/effective-configuration",token=admin)
assert request(f"monitoring/data-sources/{sid}/effective-configuration",token=admin)==before_effective
# A task-owned PostgreSQL trigger injects failure before UPDATE can commit.
from sqlalchemy import text as injected_text
with SessionLocal() as db:
    db.execute(injected_text("CREATE FUNCTION sprint_attachment_failure() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.priority=98765 THEN RAISE EXCEPTION 'controlled attachment transaction failure'; END IF; RETURN NEW; END $$"))
    db.execute(injected_text("CREATE TRIGGER sprint_attachment_failure BEFORE UPDATE ON monitoring_template_attachments FOR EACH ROW EXECUTE FUNCTION sprint_attachment_failure()"));db.commit()
try:
    request(attachment_path,"PATCH",{"priority":98765},admin,500)
    assert request(f"monitoring/data-sources/{sid}/templates",token=admin)==[winner]
    assert request(f"monitoring/data-sources/{sid}/effective-configuration",token=admin)==before_effective
finally:
    with SessionLocal() as db:
        db.execute(injected_text("DROP TRIGGER sprint_attachment_failure ON monitoring_template_attachments"))
        db.execute(injected_text("DROP FUNCTION sprint_attachment_failure()"));db.commit()
request(f"monitoring/templates/{tid}","DELETE",token=admin,expected=204)
request(attachment_path,"PATCH",{"enabled":False},admin)
request(attachment_path,"PATCH",{"enabled":True},admin,409)
request(f"monitoring/data-sources/{sid}/templates","POST",{"template_id":tid,"template_version":1},admin,409)
assert not request(f"monitoring/data-sources/{sid}/templates",token=admin)[0]["enabled"]
assert {v["version"] for v in request(f"monitoring/templates/{tid}/versions",token=admin)}=={1,2,3,4}
checks.append("002C attachment concurrent expected-revision writes produce200/409; injected PostgreSQL failure rolls back state; disabled template cannot re-enable or attach; pinned versions preserved")

# Bounded DB-ingestion load probe, not a genuine Agent/OTLP throughput certification.
import time
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select, func
from app.models import MetricDefinition, MetricSample
metric_id = uuid.uuid4()
with SessionLocal() as db:
    db.add(MetricDefinition(id=metric_id, organization_id=uuid.UUID(aid), data_source_id=uuid.UUID(sid), collector_id=uuid.UUID(collector["id"]), name="controlled-load", resource_type="VM", metric_type="gauge"))
    db.commit()
expected_ids = [uuid.uuid4() for _ in range(200)]
def write_load():
    for start in range(0, 200, 10):
        with SessionLocal() as db:
            db.add_all([MetricSample(id=identity, organization_id=uuid.UUID(aid), metric_definition_id=metric_id, collector_id=uuid.UUID(collector["id"]), observed_at=datetime.now(timezone.utc), value_numeric=1.0) for identity in expected_ids[start:start+10]])
            db.commit()
        time.sleep(0.01)
latencies = []
with ThreadPoolExecutor(max_workers=1) as pool:
    future = pool.submit(write_load)
    for _ in range(20):
        started = time.perf_counter()
        response = request("infrastructure/resources?limit=50", token=admin)
        latencies.append((time.perf_counter()-started)*1000)
        assert response["total"] >= 1
    future.result()
with SessionLocal() as db:
    actual_ids = set(db.scalars(select(MetricSample.id).where(MetricSample.metric_definition_id == metric_id)))
    physical = db.scalar(select(func.count()).select_from(MetricSample).where(MetricSample.metric_definition_id == metric_id))
assert actual_ids == set(expected_ids) and physical == 200
ordered = sorted(latencies)
Path(os.environ["V16_EVIDENCE_DIR"]).joinpath("controlled-load.json").write_text(json.dumps({"scope":"200 direct PostgreSQL sample writes concurrent with20 authenticated infrastructure reads; not full OTLP/global responsiveness reproduction", "p50_ms":ordered[9], "p95_ms":ordered[18], "max_ms":max(ordered), "latencies_ms":latencies, "expected":200, "persisted_distinct":len(actual_ids), "physical_rows":physical, "missing":0, "duplicates":0, "global_RM_DEF_036":"NOT REPRODUCED by this bounded probe; all-module representative load remains NOT TESTED"},indent=2))
checks.append("Controlled concurrent sample writes/read latency:200/200 stable IDs, zero missing/duplicates; no global performance certification")
report = {
    "status": "PASS",
    "checks": checks,
    "vendor_environments_accessed": False,
    "genuine_runtime_verification_claimed": False,
    "production_modified": False,
}
Path(os.environ["V16_EVIDENCE_DIR"]).joinpath("api.json").write_text(
    json.dumps(report, indent=2)
)
(private / "browser-fixture.json").write_text(
    json.dumps(
        {
            "base_url": base,
            "password": fixture["password"],
            "viewer_password": fixture["viewer_password"],
            "integration_id": id,
            "organization_id": aid,
            "other_organization_id": bid,
        }
    )
)
(private / "browser-fixture.json").chmod(0o600)
print(
    "V1.6 actual HTTP multi-job/draft/configuration/association/activation/RBAC workflow PASS:",
    len(checks),
    "groups",
)
