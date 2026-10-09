"""Disposable-database Phase 1 verification probes.

Run only in an isolated CI/local staging environment; creates demo tenant data.
Records behavior as evidence. Known security/template failures are NOT counted as passes.
"""
import asyncio
import json
import os
import urllib.error
import urllib.request
import uuid
from pathlib import Path

BASE = os.getenv("OPSCONTROL_TEST_API", "http://127.0.0.1:8000")
RESULT = {"environment": "disposable CI database", "checks": {}, "release_blockers": []}


def request(method, path, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"} if data is not None else {}
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        return exc.code, json.loads(raw) if raw else None


def created(path, obj):
    status, result = request("POST", path, obj)
    assert status == 201, f"POST {path}: {status} {result}"
    return result


def get(path):
    status, result = request("GET", path)
    assert status == 200, f"GET {path}: {status} {result}"
    return result


def record(label, observed, expected, compliant):
    RESULT["checks"][label] = {"observed": observed, "expected": expected,
                                "compliant": compliant}
    if not compliant:
        RESULT["release_blockers"].append(label)


def main():
    key = str(uuid.uuid4())[:8]
    org_a = created("/api/v1/organizations", {"name": f"Audit Tenant A {key}", "code": f"A{key}", "active": True})
    org_b = created("/api/v1/organizations", {"name": f"Audit Tenant B {key}", "code": f"B{key}", "active": True})
    source_a = created("/api/v1/resource-management/data-sources", {
        "organization_id": org_a["id"], "name": f"Staging API {key}",
        "source_type": "API", "endpoint": BASE + "/health", "auth_type": "BASIC", "enabled": True
    })
    source_b = created("/api/v1/resource-management/data-sources", {
        "organization_id": org_b["id"], "name": f"Other Tenant API {key}",
        "source_type": "API", "endpoint": BASE + "/health", "enabled": True
    })

    # Anonymous access already invalidates authenticated organization isolation.
    anon_org_status, anon_orgs = request("GET", "/api/v1/organizations")
    anon_list_status, anon_sources = request("GET", "/api/v1/resource-management/data-sources")
    anon_b_status, _ = request("GET", f"/api/v1/monitoring/data-sources/{source_b['id']}")
    anon_edit_status, _ = request("PATCH", f"/api/v1/resource-management/data-sources/{source_b['id']}",
                                  {"description": "Unauthorized anonymous update in isolated CI"})
    record("organization_read_requires_auth", anon_org_status, "401 or 403", anon_org_status in (401, 403))
    record("source_list_requires_auth", anon_list_status, "401 or 403", anon_list_status in (401, 403))
    record("source_detail_requires_auth", anon_b_status, "401 or 403", anon_b_status in (401, 403))
    record("source_edit_requires_auth", anon_edit_status, "401 or 403", anon_edit_status in (401, 403))
    RESULT["checks"]["cross_tenant_data_exposed_anonymously"] = {
        "observed": anon_list_status == 200 and {source_a["id"], source_b["id"]}.issubset(
            {s["id"] for s in anon_sources}),
        "expected": False, "compliant": anon_list_status in (401, 403)
    }

    template = created("/api/v1/monitoring/templates", {
        "name": f"Audit template {key}", "scope": "API",
        "package_config": {
            "collector": {"type": "API", "interval_seconds": 30},
            "metrics": [{"name": "Availability", "metric": "availability",
                         "method": "HTTP", "extract": "AVAILABILITY"}],
            "alerts": [], "logs": [], "attributes": []
        }
    })
    attachment = created(f"/api/v1/monitoring/data-sources/{source_a['id']}/templates", {
        "template_id": template["id"], "template_version": 1
    })
    effective = get(f"/api/v1/monitoring/data-sources/{source_a['id']}/effective-configuration")
    auto_collectors = get(f"/api/v1/monitoring/collectors?data_source_id={source_a['id']}")
    auto_metrics = get(f"/api/v1/monitoring/metrics?data_source_id={source_a['id']}")
    auto_ok = bool(attachment and effective.get("valid") and auto_collectors and auto_metrics)
    record("template_materializes_monitoring", {
        "attachment_created": bool(attachment),
        "effective_collector": effective.get("collector", {}).get("type"),
        "provisioned_collectors": len(auto_collectors),
        "provisioned_metrics": len(auto_metrics)
    }, "at least one live Collector + MetricDefinition", auto_ok)

    # Positive control: existing manually configured HTTP collector -> run -> metric sample.
    collector = created("/api/v1/monitoring/collectors", {
        "data_source_id": source_a["id"], "name": f"manual-api-{key}",
        "collector_type": "API", "enabled": True, "interval_seconds": 30,
        "configuration": {"url": BASE + "/health", "credential_ref": "STAGING",
                          "auth_type": "BASIC", "expected_status": 200}
    })
    metric = created("/api/v1/monitoring/metrics", {
        "organization_id": org_a["id"], "data_source_id": source_a["id"],
        "collector_id": collector["id"], "name": f"availability-{key}",
        "resource_type": "API", "metric_type": "GAUGE",
        "query_config": {"extract": "AVAILABILITY"}, "unit": "bool"
    })
    from app.worker.collector_runtime import execute_collector
    asyncio.run(execute_collector(uuid.UUID(collector["id"])))
    runs = get(f"/api/v1/monitoring/collectors/{collector['id']}/runs")
    samples = get(f"/api/v1/monitoring/metrics/{metric['id']}/samples")
    run_ok = bool(runs and runs[0]["status"] == "SUCCESS"
                  and samples and samples[0]["value_numeric"] == 1.0)
    record("manually_configured_api_collector_to_sample", {
        "collector_runs": len(runs), "last_run_status": runs[0]["status"] if runs else None,
        "metric_samples": len(samples), "latest_value": samples[0]["value_numeric"] if samples else None
    }, "successful CollectorRun and availability sample=1.0", run_ok)
    if not run_ok:
        raise AssertionError("Manual collector-to-sample control failed")

    RESULT["known_release_blockers"] = len(RESULT["release_blockers"])
    output = Path("phase1-staging-evidence.json")
    output.write_text(json.dumps(RESULT, indent=2) + "\n")
    print(json.dumps(RESULT, indent=2))
    print("NOTE: release_blockers are findings, not test passes; Phase 1 product approval is blocked.")


if __name__ == "__main__":
    try:
        main()
    except BaseException:
        Path("phase1-staging-evidence-error.txt").write_text("Staging probe failed; inspect CI job logs.\n")
        raise
