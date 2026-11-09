"""Focused documentation validation for OC-S01-CLOSE-R02; no release promotion."""

from pathlib import Path
import collections
import csv
import hashlib
import json
import re
import subprocess

B = Path(__file__).resolve().parent
ROOT = B.parents[3]
R = B / "raw/r02"
APP = "ecfdff2cf3f9d1a7b7b284e79a7f708d1baea8ce"
CLOSE = "506d24356a205bbddb82c74924f4e84a5e54d441"
FILES = [
    "SPRINT0_FINAL_DISPOSITION.md",
    "SPRINT0_AUTHORITY_QUARANTINE.csv",
    "SPRINT1_REMAINING_CONTRACTS.md",
    "SUPPORTED_WRITER_COMPATIBILITY_MATRIX.csv",
    "DESKTOP_OWNER_ACCEPTANCE_PACKET.md",
    "INDEPENDENT_SEMANTIC_REVIEW.md",
    "HOSTED_CI_EXACT_SHA_RECONCILIATION.md",
    "INTEGRATION_READINESS_DECISION.md",
    "SPRINT2_ENTRY_DECISION_REQUEST.md",
]


def load(path):
    return json.loads(path.read_text())


def check():
    for f in FILES:
        assert (B / f).is_file(), f
    for p in B.rglob("*.json"):
        load(p)
    for p in B.glob("*.md"):
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", p.read_text()):
            if not target.startswith(("https:", "http:", "#")):
                assert (p.parent / target.split("#")[0]).exists(), (p.name, target)
    original = load(B / "SPRINT0_CLOSURE_REGISTER.json")
    final = load(B / "SPRINT0_FINAL_DISPOSITION.json")
    assert (
        final["starting_counts"]
        == original["counts"]
        == {
            "RESOLVED": 14,
            "BLOCKED": 80,
            "AWAITING_OWNER_DECISION": 39,
            "APPROVED_DEFERRED": 25,
        }
    )
    ids = lambda rows: {x["requirement_id"] for x in rows}
    assert len(final["items"]) == 158 and ids(final["items"]) == ids(
        original["requirements"]
    )
    assert sum(x["starting_disposition"] != "RESOLVED" for x in final["items"]) == 144
    fields = [
        "historical_provenance",
        "approval_status",
        "current_scope",
        "required_sprint1_acceptance",
        "required_before_sprint2_development",
        "development_sequencing",
        "independent_gates",
        "owner_decision_timing",
        "source_sha",
    ]
    assert all(
        all(str(x[k]).strip() for k in fields) and x["source_sha"] == APP
        for x in final["items"]
    )
    q = list(csv.DictReader((B / "SPRINT0_AUTHORITY_QUARANTINE.csv").open()))
    assert len(q) == len({x["item_id"] for x in q}) == 92
    assert collections.Counter(x["kind"] for x in q) == {
        "HISTORICAL_REQUIREMENT": 62,
        "INCLUDED_JOURNEY_SLOT": 30,
    }
    assert all(
        x["definition"] == "SOURCE_NOT_RECOVERED" and x["status"] == "QUARANTINED"
        for x in q
    )
    w = list(csv.DictReader((B / "SUPPORTED_WRITER_COMPATIBILITY_MATRIX.csv").open()))
    assert len(w) == len({x["id"] for x in w}) == 18
    assert all(
        all(v is not None for v in x.values()) and x["application_sha"] == APP
        for x in w
    )
    assert (
        next(x for x in w if x["id"] == "C01")["qualification"]
        == "SOURCE_DECLARED_NOT_DEPLOYMENT_QUALIFIED"
    )
    assert (
        "INDEPENDENT_REVIEW_PENDING"
        in (B / "INDEPENDENT_SEMANTIC_REVIEW.md").read_text()
    )
    for pr, sha in [(89, APP), (101, CLOSE)]:
        checks = load(R / f"pr{pr}-check-runs.json")["check_runs"]
        assert len(checks) == 33 and all(x["head_sha"] == sha for x in checks)
        assert not load(R / f"oc-close-r02-pr{pr}.json")["reviews"]
    ci = list(csv.DictReader((B / "HOSTED_CI_EXACT_SHA_RECONCILIATION.csv").open()))
    assert len(ci) == 66
    assert collections.Counter(x["conclusion"] for x in ci if x["pr"] == "89") == {
        "success": 25,
        "failure": 8,
    }
    assert collections.Counter(x["conclusion"] for x in ci if x["pr"] == "101") == {
        "success": 24,
        "failure": 8,
        "PENDING": 1,
    }
    assert all(
        x["run_url"].startswith("https://github.com/") and x["job_url"] for x in ci
    )
    old = load(B / "raw/ruleset26082467.json")
    new = load(R / "ruleset26082467.json")
    assert old["rules"] == new["rules"] and old["enforcement"] == new["enforcement"]
    baseline = load(R / "PR101_ARTIFACT_SHA256_BASELINE.json")
    for p, h in baseline.items():
        if p not in {"README.md", "CHANGED_FILES.txt"}:
            assert hashlib.sha256((B / p).read_bytes()).hexdigest() == h, p
        data = subprocess.check_output(
            ["git", "show", CLOSE + ":" + str((B / p).relative_to(ROOT))], cwd=ROOT
        )
        assert hashlib.sha256(data).hexdigest() == h, p
    authority = load(ROOT / "docs/planning/authority/AUTH-694.v1.json")
    assert (
        authority["decision_status"] == "APPROVED"
        and authority["supersession_status"] == "CURRENT"
    )
    decision = (B / "INTEGRATION_READINESS_DECISION.md").read_text()
    for status in [
        "ACCEPTABLE_BASELINE_WITH_EXPLICIT_QUARANTINE",
        "CORRECTIONS_REQUIRED",
        "CONDITIONAL_PENDING_OWNER_DECISIONS",
    ]:
        assert status in decision
    return {
        "status": "PASS_DOCUMENTATION_RECONCILIATION_ONLY",
        "baseline": CLOSE,
        "application_sha": APP,
        "registered_ids": 158,
        "unresolved_starting_rows_triaged": 144,
        "quarantined_definitions": 92,
        "supported_boundary_records": 18,
        "hosted_checks": 66,
        "required_policy": "UNCHANGED",
        "independent_review": "PENDING",
        "installed_version_roster": "NOT_ESTABLISHED;affected qualification STOPPED",
        "sprint1": "NOT COMPLETE",
        "sprint2": "NOT AUTHORIZED",
        "SECURITY": "BLOCKED",
        "CHK-001": "FAIL",
        "CHK-002": "BLOCKED",
        "RELEASE": "NO-GO",
        "collector": "0.123.0 unchanged",
    }


if __name__ == "__main__":
    print(json.dumps(check(), indent=2))
