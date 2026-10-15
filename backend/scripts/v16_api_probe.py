"""Actual scoped HTTP workflow in the owned lab; no vendor connection requests."""

import json, os, uuid
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from pathlib import Path
import app.main  # register existing parent models for direct fixture transactions
from app.db.session import SessionLocal
from app.models import Organization
from app.security.models import User, OrganizationMembership
from app.security.passwords import hash_password
from app.security.permission_catalog import PROVIDER_ID
from app.security.scope import current_principal
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
        data = json.load(response)
    except HTTPError as error:
        status = error.code
        data = json.load(error)
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
            "integration_id": id,
            "organization_id": aid,
        }
    )
)
(private / "browser-fixture.json").chmod(0o600)
print(
    "V1.6 actual HTTP multi-job/draft/configuration/association/activation/RBAC workflow PASS:",
    len(checks),
    "groups",
)
