"""Enforce digest-bound local image evidence; no publication or risk waivers."""

import hashlib
import json
import re
from pathlib import Path
from datetime import datetime, timezone, timedelta


def verify_evidence(directory):
    record = json.loads((directory / "provenance.json").read_text())
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", record["image_id"]):
        raise ValueError("Immutable image ID required")
    for path, sha in record["sha256"].items():
        p = (directory / path).resolve()
        if (
            p.parent != directory.resolve()
            or hashlib.sha256(p.read_bytes()).hexdigest() != sha
        ):
            raise ValueError("Evidence checksum or path mismatch")
    required = {
        "sbom.cdx.json",
        "sbom.syft.json",
        "grype.json",
        "grype-db.json",
        "tools.json",
        "licenses.json",
    }
    if not required <= record["sha256"].keys():
        raise ValueError("Incomplete image evidence")
    cdx = json.loads((directory / "sbom.cdx.json").read_text())
    if cdx.get("bomFormat") != "CycloneDX" or not cdx.get("components"):
        raise ValueError("Missing CycloneDX components")
    syft = json.loads((directory / "sbom.syft.json").read_text())
    if syft.get("source", {}).get("metadata", {}).get("imageID") != record["image_id"]:
        raise ValueError("SBOM image identity mismatch")
    scan = json.loads((directory / "grype.json").read_text())
    if "matches" not in scan or "descriptor" not in scan:
        raise ValueError("Invalid scanner output")
    if scan.get("source", {}).get("target", {}).get("imageID") != record["image_id"]:
        raise ValueError("Scan image identity mismatch")
    db = json.loads((directory / "grype-db.json").read_text())
    if db.get("valid") is not True:
        raise ValueError("Scanner database is not valid")
    built = db.get("built") or db.get("status", {}).get("built")
    if not built:
        raise ValueError("Scanner DB timestamp missing")
    stamp = datetime.fromisoformat(built.replace("Z", "+00:00"))
    if (
        stamp.tzinfo is None
        or stamp > datetime.now(timezone.utc) + timedelta(minutes=5)
        or stamp < datetime.now(timezone.utc) - timedelta(days=7)
    ):
        raise ValueError("Scanner database stale or invalid")
    return {
        "status": "PASS_BOUNDED_IMAGE_EVIDENCE",
        "image_id": record["image_id"],
        "not_security_approval": True,
        "not_release_clearance": True,
    }


def validate(directory):
    """Mandatory existing zero-severe plus accountable License/NOTICE gate."""
    evidence = verify_evidence(directory)
    scan = json.loads((directory / "grype.json").read_text())
    bad = [
        m
        for m in scan["matches"]
        if m.get("vulnerability", {}).get("severity", "Unknown").lower()
        in ("high", "critical", "unknown")
    ]
    if bad:
        raise ValueError(
            f"Unresolved High/Critical/unknown severity matches: {len(bad)}"
        )
    license_review = json.loads((directory / "licenses.json").read_text())
    if license_review.get("status") != "REVIEWED" or not license_review.get("reviewer"):
        raise ValueError(
            "License/NOTICE review pending; inventory is not legal approval"
        )
    return {
        "status": "PASS_BOUNDED_IMAGE_POLICY",
        "image_id": evidence["image_id"],
        "not_release_clearance": True,
    }


if __name__ == "__main__":
    import sys

    print(json.dumps(validate(Path(sys.argv[1])), indent=2))
