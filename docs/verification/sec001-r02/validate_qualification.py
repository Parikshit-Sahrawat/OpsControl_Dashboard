"""Offline documentation validation, not vulnerability clearance."""

from pathlib import Path
import csv
import hashlib
import json
import subprocess
import sys

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[2]


def validate():
    subprocess.run([sys.executable, str(BASE / "qualify.py")], check=True)
    rows = json.loads((BASE / "QUALIFICATION_MATRIX.json").read_text())
    assert len(rows) == 35 and len({r["finding_id"] for r in rows}) == 35
    assert sum(r["severity_unchanged"] == "Critical" for r in rows) == 3
    assert sum(r["severity_unchanged"] == "High" for r in rows) == 32
    assert len(list(csv.DictReader((BASE / "QUALIFICATION_MATRIX.csv").open()))) == 35
    for row in rows:
        assert row["finding_disposition"] == "UNRESOLVED" and row["reviewer"] is None
        assert row["approved_registry_manifest_digest"] is None
        assert row["installed_version"] == "go1.24.6"
        for ref in row["evidence"]:
            assert (REPO / ref.split("#")[0]).is_file(), ref
    assert (
        "VALIDSIG B42F6819007F00F88E364FD4036A9C25BF357DD4"
        in (BASE / "raw/gpg-verification.log").read_text()
    )
    assert (BASE / "raw/gpg-verification.exit").read_text().strip() == "0"
    assert len(list((BASE / "raw/go-advisories").glob("GO-*.json"))) == 35
    return {
        "status": "PASS_DOCUMENTATION_RECONCILIATION_ONLY",
        "rows": 35,
        "critical": 3,
        "high": 32,
        "findings_closed": 0,
        "reachability_inconclusive": 35,
        "genuine_runtime_tests": "NOT RUN — read-only scope",
        "security": "BLOCKED",
        "chk001": "FAIL",
        "chk002": "BLOCKED",
        "release": "NO-GO",
    }


if __name__ == "__main__":
    result = validate()
    print(json.dumps(result, indent=2))
