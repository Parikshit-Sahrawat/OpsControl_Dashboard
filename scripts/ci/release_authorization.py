"""Fail-closed release record validation. No records are supplied/enabled by CI."""

import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
GATES = {"CHK-001": "PASS", "CHK-002": "PASS", "SECURITY": "PASS", "RELEASE": "GO"}


def validate(record, sha, operation):
    if not re.fullmatch(r"[a-f0-9]{40}", sha):
        raise ValueError("Exact lowercase source SHA required")
    if record.get("schema") != 1 or record.get("source_sha") != sha:
        raise ValueError("Authorization schema or SHA mismatch")
    if record.get("phase") != "SPRINT10_APPROVED" or record.get("gates") != GATES:
        raise ValueError("Independent release gates and Sprint10 approval required")
    if operation not in record.get("operations", []):
        raise ValueError("Operation not authorized")
    if record.get("status") != "APPROVED" or not record.get("approval_evidence"):
        raise ValueError("Accountable approval evidence required")
    reviewers = record.get("reviewers", {})
    required = ("product_owner", "security", "migration")
    if any(
        not isinstance(reviewers.get(k), str) or not reviewers[k].strip()
        for k in required
    ):
        raise ValueError("Named independent reviewers required")
    if len(set(reviewers[k].casefold() for k in required)) != len(required):
        raise ValueError("Independent reviewers must be distinct")
    if record.get("expires_at") is None:
        raise ValueError("Bounded authorization expiry required")
    from datetime import datetime, timezone

    expires = datetime.fromisoformat(record["expires_at"].replace("Z", "+00:00"))
    if expires.tzinfo is None or expires <= datetime.now(timezone.utc):
        raise ValueError("Authorization expired or timezone missing")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sha", required=True)
    parser.add_argument("--record", required=True)
    parser.add_argument("--operation", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,79}", args.record):
        raise ValueError("Invalid authorization record ID")
    directory = ROOT / "docs/releases/authorizations"
    path = directory / (args.record + ".json")
    if (
        path.is_symlink()
        or not path.is_file()
        or path.resolve().parent != directory.resolve()
    ):
        raise ValueError("Committed authorization record unavailable")
    # Reviewed-main checkout is required by workflows; check the record is tracked.
    import subprocess

    subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(path.relative_to(ROOT))],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    validate(json.loads(path.read_text()), args.sha, args.operation)
    print(
        "Release record validated; independent trusted check/protection verification still required"
    )


if __name__ == "__main__":
    main()
