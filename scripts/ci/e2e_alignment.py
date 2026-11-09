"""Integrity of the bounded Sprint 1 E2E register; not a certification engine."""

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
MATRIX = "docs/verification/sprint1-integration/E2E_WORKFLOW_MATRIX.json"
GATES = {
    "CHK-001": "FAIL",
    "CHK-002": "BLOCKED",
    "SECURITY": "BLOCKED",
    "RELEASE": "NO-GO",
}
IDS = {f"S1-E2E-{number:02}" for number in range(1, 8)}
LEVELS = {
    "DESIGNED",
    "IMPLEMENTED",
    "CONTROLLED_E2E_VERIFIED",
    "GENUINE_PROVIDER_VERIFIED",
    "INDEPENDENTLY_ACCEPTED",
    "RELEASE_ELIGIBLE",
}
STATUSES = {
    "PARTIAL",
    "NOT_IMPLEMENTED",
    "BLOCKED",
    "IMPLEMENTED",
    "CONTROLLED_E2E_VERIFIED",
}


def pinned_file(root, path, commit):
    relative = Path(path)
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or not (root / relative).resolve().is_relative_to(root.resolve())
    ):
        raise ValueError("Unsafe source/evidence path")
    if not (root / relative).is_file() or not re.fullmatch(r"[a-f0-9]{40}", commit):
        raise ValueError("Missing file or immutable commit")
    result = subprocess.run(
        ["git", "show", commit + ":" + path], cwd=root, capture_output=True
    )
    if result.returncode:
        raise ValueError("File absent at declared commit: " + path)
    return result.stdout


def prepare_history(root=ROOT):
    """Explicit CI preparation for checkout's shallow history; never in tests.

    Fetch only full commit IDs declared by this reviewed local register. No
    branch advancement, checkout, implicit provenance fallback or code execution.
    """
    data = json.loads((root / MATRIX).read_text())
    commits = {row["source_sha"] for row in data["workflows"]}
    commits.update(
        e["commit_sha"] for row in data["workflows"] for e in row.get("evidence", [])
    )
    if not all(re.fullmatch(r"[a-f0-9]{40}", value) for value in commits):
        raise ValueError("Full immutable provenance IDs required before fetch")
    missing = [
        sha
        for sha in sorted(commits)
        if subprocess.run(
            ["git", "cat-file", "-e", sha + "^{commit}"], cwd=root, capture_output=True
        ).returncode
    ]
    if missing:
        subprocess.run(
            ["git", "fetch", "--no-tags", "--depth=1", "origin", *missing],
            cwd=root,
            check=True,
            timeout=120,
        )
    return missing


def render(data):
    columns = [
        "workflow_id",
        "source_to_ui_journey",
        "owner",
        "environment",
        "source_sha",
        "exact_test_command_job",
        "actual_evidence_path",
        "last_result",
        "status_classification",
        "certification_authority",
        "blockers",
    ]
    text = "# Sprint 1 bounded E2E workflow matrix\n\n"
    text += "Issue95 authorizes this register and its guard only. Evidence levels are defined in [the architecture alignment](../../architecture/SPRINT1_E2E_ALIGNMENT.md). Source and evidence commits differ deliberately; JSON retains exact hashes. Owner roles below are responsibilities, not fabricated named signoffs. No row asserts genuine-provider certification or release eligibility.\n\n"
    text += (
        "| " + " | ".join(columns) + " |\n|" + "|".join(["---"] * len(columns)) + "|\n"
    )
    for row in data["workflows"]:
        display = dict(row)
        display["actual_evidence_path"] = (
            "; ".join(f"`{e['path']}` @ `{e['commit_sha']}`" for e in row["evidence"])
            or "MISSING — see blockers"
        )
        display["blockers"] = (
            "; ".join(row["blockers"]) or "None within declared boundary"
        )
        text += (
            "| "
            + " | ".join(
                str(display[column]).replace("|", "\\|").replace("\n", " ")
                for column in columns
            )
            + " |\n"
        )
    text += "\nHistorical/subpath PASS evidence does not change a row's PARTIAL/BLOCKED whole-path disposition. CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.\n"
    return text


def validate(data=None, root=ROOT):
    data = json.loads((root / MATRIX).read_text()) if data is None else data
    if (
        data.get("schema") != 1
        or data.get("gates") != GATES
        or data.get("mode") != "SPRINT1_CONTROLLED_ONLY"
    ):
        raise ValueError("Scope or independent gates changed")
    rows = data["workflows"]
    if len(rows) != len(IDS) or {row["workflow_id"] for row in rows} != IDS:
        raise ValueError("Missing or duplicate required workflow")
    for row in rows:
        for key in (
            "source_to_ui_journey",
            "owner",
            "environment",
            "source_sha",
            "exact_test_command_job",
            "certification_authority",
        ):
            if not isinstance(row.get(key), str) or not row[key].strip():
                raise ValueError("Missing workflow field: " + key)
        if (
            row.get("status_classification") not in STATUSES
            or row.get("evidence_level") not in LEVELS
        ):
            raise ValueError("Unknown workflow status or evidence level")
        # This authorization cannot establish live provider, independent owner,
        # security/legal approval or release eligibility from controlled tests.
        if (
            row["evidence_level"]
            in {
                "GENUINE_PROVIDER_VERIFIED",
                "INDEPENDENTLY_ACCEPTED",
                "RELEASE_ELIGIBLE",
            }
            or row.get("provider_certification") is not False
        ):
            raise ValueError(
                "Provider/independent/release certification not authorized by this register"
            )
        if not row.get("source_paths"):
            raise ValueError("Missing implementation traceability")
        for path in row["source_paths"]:
            pinned_file(root, path, row["source_sha"])
        if row.get("certification_authority") not in {
            "CONTROLLED_ENGINEERING_ONLY",
            "NONE_PENDING",
        } or not isinstance(row.get("collector_required"), bool):
            raise ValueError("Unknown certification authority or collector boundary")
        verified = row["status_classification"] == "CONTROLLED_E2E_VERIFIED"
        if verified != (row["evidence_level"] == "CONTROLLED_E2E_VERIFIED"):
            raise ValueError("Contradictory verification classification")
        if row.get("last_result") not in {
            "PASS",
            "FAIL",
            "PARTIAL",
            "BLOCKED",
            "NOT_RUN",
        }:
            raise ValueError("Unknown execution result")
        if (row["last_result"] == "PASS") != verified:
            raise ValueError("Whole-path PASS requires controlled verification")
        if not verified and not row.get("blockers"):
            raise ValueError("Incomplete workflow needs exact blockers")
        if row["status_classification"] == "BLOCKED" and row["last_result"] not in {
            "BLOCKED",
            "NOT_RUN",
        }:
            raise ValueError("Contradictory blocked result")
        if verified:
            if row["certification_authority"] != "CONTROLLED_ENGINEERING_ONLY":
                raise ValueError(
                    "Controlled result needs a bounded engineering authority"
                )
            needed = {
                "authenticated_ui",
                "actual_api",
                "migrated_postgres",
                "tenant_negative",
                "failure_restart",
            }
            if row.get("collector_required"):
                needed.add("real_collector_worker")
            if not needed.issubset(row.get("verified_boundaries", [])) or not row.get(
                "evidence"
            ):
                raise ValueError(
                    "Missing real-component verification boundary/evidence"
                )
        for evidence in row.get("evidence", []):
            content = pinned_file(root, evidence["path"], evidence["commit_sha"])
            if (
                hashlib.sha256(content).hexdigest() != evidence["sha256"]
                or (root / evidence["path"]).read_bytes() != content
            ):
                raise ValueError("Evidence checksum/provenance mismatch")
    if (root / MATRIX).is_file():
        markdown = root / MATRIX.replace(".json", ".md")
        if not markdown.is_file() or markdown.read_text() != render(data):
            raise ValueError("Markdown/JSON workflow matrix drift")
    return {
        "status": "PASS",
        "workflow_rows": len(rows),
        "whole_path_verified": sum(
            r["status_classification"] == "CONTROLLED_E2E_VERIFIED" for r in rows
        ),
        "meaning": "register integrity only; not certification",
    }


if __name__ == "__main__":
    if sys.argv[1:] == ["--prepare-history"]:
        prepare_history()
    elif sys.argv[1:]:
        raise SystemExit("Only --prepare-history is supported")
    print(json.dumps(validate(), indent=2))
