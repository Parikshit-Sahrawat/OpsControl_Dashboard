"""Exact candidate image coverage. This does not waive vulnerability/licence gates."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import yaml

ROOT = Path(__file__).resolve().parents[2]
FIELDS = ("context", "file", "target", "image")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contract(root=ROOT):
    data = json.loads((root / ".ci/image-coverage.json").read_text())
    rows = data["roles"]
    if data["schema"] != 1 or len({r["role"] for r in rows}) != len(rows):
        raise ValueError("Invalid/duplicate image role contract")
    old = {
        "backend-runtime",
        "backend-migration",
        "uat-backend",
        "frontend",
        "postgres",
        "ingestion-gateway",
        "otel-contrib",
    }
    if not old <= {r["role"] for r in rows}:
        raise ValueError("Historical seven scan roles cannot be removed")
    production = {
        r["role"]
        for r in json.loads((root / "deploy/release/image-policy.json").read_text())[
            "roles"
        ]
    }
    mapped = [r["production_role"] for r in rows if r.get("production_role")]
    if set(mapped) != production or len(mapped) != len(production):
        raise ValueError("Missing/ambiguous production role coverage")
    expected = {r["role"]: {k: r.get(k, "") for k in FIELDS} for r in rows}
    workflow = yaml.load(
        (root / ".github/workflows/security-artifacts.yml").read_text(),
        Loader=yaml.BaseLoader,
    )
    matrix = workflow["jobs"]["image-evidence"]["strategy"]["matrix"]["include"]
    if (
        len(matrix) != len(rows)
        or {r["role"]: {k: r.get(k, "") for k in FIELDS} for r in matrix} != expected
    ):
        raise ValueError("Workflow/build-input coverage drift")
    if expected["frontend"]["file"] != "frontend/Dockerfile.demo" or not any(
        r.get("production_role") == "frontend"
        and r.get("file") == "frontend/Dockerfile.runtime"
        for r in rows
    ):
        raise ValueError("Production frontend must not be replaced by demo coverage")
    if (
        expected["otel-contrib"]["image"]
        != "otel/opentelemetry-collector-contrib:0.123.0@sha256:e39311df1f3d941923c00da79ac7ba6269124a870ee87e3c3ad24d60f8aee4d2"
    ):
        raise ValueError("Collector runtime pin changed")
    return rows


def material(row, root=ROOT):
    result = {k: row.get(k, "") for k in FIELDS}
    if row.get("file"):
        if not (root / row["file"]).resolve().is_relative_to(root.resolve()):
            raise ValueError("Unsafe build input path")
        result["dockerfile_sha256"] = sha(root / row["file"])
    return result


def bind(role, image, iid_file, output, root=ROOT):
    row = next(r for r in contract(root) if r["role"] == role)
    if subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=root, text=True
    ).strip():
        raise ValueError("Clean committed checkout required for image binding")
    info = json.loads(
        subprocess.check_output(["docker", "image", "inspect", image], text=True)
    )[0]
    identity = iid_file.read_text().strip()
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", identity) or info["Id"] != identity:
        raise ValueError("Build/pull result and tagged scan image differ")
    repo_digests = info.get("RepoDigests", [])
    if row.get("image") and not any(
        x.endswith("@" + row["image"].split("@", 1)[1]) for x in repo_digests
    ):
        raise ValueError("Pulled image does not match pinned upstream digest")
    output.mkdir(parents=True, exist_ok=True)
    data = {
        "schema": 1,
        "role": role,
        "image_id": identity,
        "identity_kind": "docker-image-config-sha256",
        "architecture": info["Architecture"],
        "source_sha": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip(),
        "build_input": material(row, root),
        "repo_digests": repo_digests,
        "registry_release_approved": False,
    }
    (output / "image-binding.json").write_text(json.dumps(data, indent=2) + "\n")
    return data


def verify(directory, row, source, root=ROOT):
    binding = json.loads((directory / "image-binding.json").read_text())
    provenance = json.loads((directory / "provenance.json").read_text())
    identity = binding["image_id"]
    if (
        not re.fullmatch(r"sha256:[a-f0-9]{64}", identity)
        or binding["role"] != row["role"]
        or provenance.get("scan_role") != row["role"]
    ):
        raise ValueError("Wrong role or immutable image identity")
    if (
        not re.fullmatch(r"[a-f0-9]{40}", source)
        or binding["source_sha"] != source
        or provenance["source_sha"] != source
    ):
        raise ValueError("Wrong source commit")
    if (
        binding["build_input"] != material(row, root)
        or binding["identity_kind"] != "docker-image-config-sha256"
    ):
        raise ValueError("Wrong intended build inputs/digest kind")
    required = {
        "image-binding.json",
        "sbom.cdx.json",
        "sbom.syft.json",
        "grype.json",
        "licenses.json",
        "tools.json",
        "grype-db.json",
    }
    if not required <= provenance["sha256"].keys():
        raise ValueError("Incomplete scan/binding artifact coverage")
    for name, digest in provenance["sha256"].items():
        if Path(name).name != name or sha(directory / name) != digest:
            raise ValueError("Artifact checksum/path mismatch")
    syft = json.loads((directory / "sbom.syft.json").read_text())
    scan = json.loads((directory / "grype.json").read_text())
    cdx = json.loads((directory / "sbom.cdx.json").read_text())
    if (
        cdx.get("bomFormat") != "CycloneDX"
        or not cdx.get("components")
        or not syft.get("artifacts")
        or not isinstance(scan.get("matches"), list)
    ):
        raise ValueError("Empty/invalid image SBOM or scan")
    if not json.loads((directory / "licenses.json").read_text()).get("components"):
        raise ValueError("Missing component licence inventory")
    component = cdx.get("metadata", {}).get("component", {})
    cdx_identity = component.get("version", "")
    if cdx_identity and not cdx_identity.startswith("sha256:"):
        cdx_identity = "sha256:" + cdx_identity
    if (
        provenance["image_id"] != identity
        or syft["source"]["metadata"]["imageID"] != identity
        or scan["source"]["target"]["imageID"] != identity
        or cdx_identity != identity
    ):
        raise ValueError("SBOM/scan/binding image digest mismatch")
    if (
        binding["architecture"] != provenance["architecture"]
        or binding["architecture"] != "amd64"
    ):
        raise ValueError("Unqualified or mismatched image architecture")
    if row.get("image") and not any(
        x.endswith("@" + row["image"].split("@", 1)[1]) for x in binding["repo_digests"]
    ):
        raise ValueError("Upstream immutable image reference mismatch")
    return {
        "role": row["role"],
        "image_id": identity,
        "source_sha": source,
        "matches": len(scan["matches"]),
        "license_status": json.loads((directory / "licenses.json").read_text())[
            "status"
        ],
        "coverage": "PASS_EXACT_CANDIDATE_ONLY",
        "release_eligible": False,
    }


def coverage(directory, source, root=ROOT):
    rows = contract(root)
    expected = {"image-evidence-" + r["role"] for r in rows}
    actual = {
        p.name
        for p in directory.iterdir()
        if p.is_dir() and p.name.startswith("image-evidence-")
    }
    if actual != expected:
        raise ValueError(
            f"Missing/unexpected image artifacts: missing={sorted(expected-actual)} unexpected={sorted(actual-expected)}"
        )
    return {
        "coverage": "PASS_EXACT_CANDIDATES_ONLY",
        "images": [
            verify(directory / ("image-evidence-" + r["role"]), r, source, root)
            for r in rows
        ],
        "release_eligible": False,
        "final_registry_manifest_approval": "BLOCKED_NOT_PROVIDED",
        "vulnerability_license_gates": "SEPARATELY_ENFORCED_UNCHANGED",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["bind", "validate"])
    parser.add_argument("--role")
    parser.add_argument("--image")
    parser.add_argument("--iid-file", type=Path)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--source")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = (
            bind(args.role, args.image, args.iid_file, args.directory)
            if args.mode == "bind"
            else coverage(args.directory, args.source)
        )
    except Exception as error:
        if args.output:
            args.output.write_text(
                json.dumps(
                    {
                        "coverage": "FAIL",
                        "error": str(error),
                        "release_eligible": False,
                    },
                    indent=2,
                )
                + "\n"
            )
        raise
    if args.output:
        args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
