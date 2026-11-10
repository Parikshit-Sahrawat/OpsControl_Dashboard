"""Validate navigation evidence identities; not owner acceptance/release clearance."""

from pathlib import Path
import hashlib
import json
import re
import struct
import subprocess

B = Path(__file__).resolve().parent
ROOT = B.parents[2]


def check():
    for p in B.rglob("*.json"):
        json.loads(p.read_text())
    for p in B.glob("*.md"):
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", p.read_text()):
            if not target.startswith(("https:", "http:", "#")):
                assert (p.parent / target.split("#")[0]).exists(), (p, target)
    results = json.loads((B / "TEST_RESULTS.json").read_text())
    assert results["frontend"] == {
        "tests": 57,
        "passed": 57,
        "failed": 0,
        "skipped": 0,
        "new": 2,
        "retained": 55,
    }
    assert results["postgresql_unique_test_ids"] == 102
    nav = json.loads((B / "after/resource-navigation.json").read_text())
    assert nav["status"] == "PASS" and len(nav["checks"]) == 10
    assert len(nav["screenshots"]) == 18
    for role in ["admin", "operator"]:
        for width, height in [(1920, 1080), (1440, 900), (1366, 768)]:
            for domain in ["VM", "ETL", "API"]:
                path = B / "after" / f"navigation-{role}-{domain}-{width}x{height}.png"
                data = path.read_bytes()
                assert data[:8] == b"\x89PNG\r\n\x1a\n"
                assert struct.unpack(">II", data[16:24]) == (width, height)
            assert (B / "before" / f"{role}-desktop-{width}x{height}.png").is_file()
    for path, digest in json.loads((B / "SOURCE_SHA256.json").read_text()).items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path
    baseline = json.loads((B / "BASELINE.json").read_text())
    assert baseline["application_tree_unchanged_after_tested_commit"]
    paths = subprocess.check_output(
        [
            "git",
            "diff",
            "--name-only",
            baseline["pr89"],
            "HEAD",
            "--",
            "backend",
            "agent",
            "deploy",
        ],
        cwd=ROOT,
        text=True,
    )
    assert not paths.strip()
    cleanup = json.loads((B / "CLEANUP.json").read_text())
    assert (
        cleanup["remaining_task_containers"] == 0
        and len(cleanup["fixture_cleanup"]) == 4
    )
    assert all(row["independently_absent"] for row in cleanup["fixture_cleanup"])
    workflow = (ROOT / ".github/workflows/resource-workspace.yml").read_text()
    assert "RESOURCE_NAV_ACCEPTANCE: '1'" in workflow
    assert "INCLUDED_POSITIVE" in (ROOT / ".ci/scope-manifest.json").read_text()
    return {
        "status": "PASS_EVIDENCE_CONSISTENCY_ONLY",
        "frontend": 57,
        "postgres_unique": 102,
        "navigation_browser_groups": 10,
        "before_desktop_screenshots": 6,
        "after_domain_desktop_screenshots": 18,
        "remaining_task_containers": 0,
        "owner_acceptance": "PENDING",
        "SECURITY": "BLOCKED",
        "CHK-001": "FAIL",
        "CHK-002": "BLOCKED",
        "RELEASE": "NO-GO",
        "collector": "0.123.0 unchanged",
    }


if __name__ == "__main__":
    print(json.dumps(check(), indent=2))
