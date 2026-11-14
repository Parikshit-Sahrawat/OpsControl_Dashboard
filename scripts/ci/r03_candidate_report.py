"""SEC001-R03 isolated-candidate evidence; NEVER authorizes release or a waiver."""

import argparse
from collections import Counter
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import re


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assess(root, role, image_id, source, expected_upstream):
    if role not in {"postgres-gosu-r03", "otel-contrib-r03"}:
        raise ValueError("Unrecognized isolated candidate role")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id):
        raise ValueError("Docker configuration SHA-256 is missing")
    if not re.fullmatch(r"[0-9a-f]{40}", source):
        raise ValueError("Git source commit is missing")
    sbom = json.loads((root / "sbom.syft.json").read_text())
    cdx = json.loads((root / "sbom.cdx.json").read_text())
    scan = json.loads((root / "grype.json").read_text())
    db = json.loads((root / "grype-db.json").read_text())
    if (
        sbom.get("source", {}).get("metadata", {}).get("imageID") != image_id
        or scan.get("source", {}).get("target", {}).get("imageID") != image_id
        or cdx.get("bomFormat") != "CycloneDX"
        or not sbom.get("artifacts")
        or not cdx.get("components")
        or not isinstance(scan.get("matches"), list)
    ):
        raise ValueError("Missing/mismatched candidate image SBOM or Grype scan")
    if not db.get("valid") or not db.get("built"):
        raise ValueError("Invalid or missing scanner vulnerability database")
    stamp = datetime.fromisoformat(db["built"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    if stamp.tzinfo is None or stamp > now + timedelta(minutes=5) or stamp < now - timedelta(days=7):
        raise ValueError("Stale scanner vulnerability database")
    severe = [
        m
        for m in scan["matches"]
        if m.get("vulnerability", {}).get("severity", "Unknown").lower()
        in {"high", "critical", "unknown"}
    ]
    by_severity = Counter(
        m.get("vulnerability", {}).get("severity", "Unknown") for m in severe
    )
    by_package = Counter(
        (m["artifact"]["name"], m["artifact"].get("version", ""))
        for m in severe
    )
    inventory = {
        "status": "PENDING_ACCOUNTABLE_REVIEW",
        "reviewer": None,
        "components": [
            {
                "name": artifact["name"],
                "version": artifact.get("version", ""),
                "type": artifact.get("type", ""),
                "licenses": artifact.get("licenses", []),
            }
            for artifact in sbom["artifacts"]
        ],
        "scope": role,
        "image_id": image_id,
        "source_sha": source,
        "notice": "Candidate inventory only. No legal/NOTICE or source-offer approval.",
    }
    (root / "licenses.json").write_text(json.dumps(inventory, indent=2) + "\n")
    reports = ["sbom.syft.json", "sbom.cdx.json", "grype.json", "grype-db.json", "licenses.json"]
    result = {
        "schema": 1,
        "qualification": "SCANNED_NOT_APPROVED",
        "role": role,
        "source_sha": source,
        "image_config_id": image_id,
        "expected_upstream_digest": expected_upstream,
        "severe_matches": len(severe),
        "severe_by_severity": dict(by_severity),
        "largest_affected_packages": [
            {"name": pkg, "version": ver, "matches": count}
            for (pkg, ver), count in by_package.most_common(20)
        ],
        "evidence_sha256": {p: sha256(root / p) for p in reports},
        "license_status": "PENDING_ACCOUNTABLE_REVIEW",
        "db_compatibility_certified": False,
        "collector_runtime_certified": False,
        "release_eligible": False,
        "merge_authorized": False,
    }
    (root / "qualification.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", required=True)
    parser.add_argument("--image-id-file", type=Path, required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--expected-upstream", required=True)
    parser.add_argument("--directory", type=Path, required=True)
    opts = parser.parse_args()
    print(
        json.dumps(
            assess(
                opts.directory,
                opts.role,
                opts.image_id_file.read_text().strip(),
                opts.source,
                opts.expected_upstream,
            ),
            indent=2,
        )
    )
