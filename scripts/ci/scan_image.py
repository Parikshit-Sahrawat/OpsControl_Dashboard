"""Generate immutable local SBOM/scan/license inventory before enforcing policy."""

import os
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]


def capture(args, path):
    p = subprocess.run(args, capture_output=True, text=True, timeout=600)
    path.write_text(p.stdout)
    path.with_suffix(path.suffix + ".stderr").write_text(p.stderr)
    if p.returncode:
        raise RuntimeError("Scanner command failed: " + args[0])


def scan(image, output, tools):
    output.mkdir(parents=True, exist_ok=True)
    # Never depend on writable HOME; keep scanner state in owned evidence.
    os.environ["GRYPE_DB_CACHE_DIR"] = str(output.resolve() / "grype-cache")
    info = json.loads(
        subprocess.check_output(["docker", "image", "inspect", image], text=True)
    )[0]
    identity = info["Id"]
    from image_coverage import contract, material

    binding_path = output / "image-binding.json"
    binding = json.loads(binding_path.read_text())
    role = os.environ["ROLE"]
    row = next(r for r in contract() if r["role"] == role)
    source_sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    if (
        binding["image_id"] != identity
        or binding["role"] != role
        or binding["source_sha"] != source_sha
        or binding["build_input"] != material(row)
    ):
        raise ValueError("Build/pull identity changed before immutable scan")
    capture(
        [
            str(tools / "syft"),
            "docker:" + identity,
            "-o",
            "cyclonedx-json=" + str(output / "sbom.cdx.json"),
            "-o",
            "syft-json=" + str(output / "sbom.syft.json"),
        ],
        output / "syft.log",
    )
    capture([str(tools / "grype"), "db", "update"], output / "grype-db-update.log")
    capture(
        [str(tools / "grype"), "db", "status", "-o", "json"],
        output / "grype-db-before.json",
    )
    capture(
        [str(tools / "grype"), "sbom:" + str(output / "sbom.syft.json"), "-o", "json"],
        output / "grype.json",
    )
    capture(
        [str(tools / "grype"), "db", "status", "-o", "json"], output / "grype-db.json"
    )
    tool_data = {
        name: subprocess.check_output(
            [str(tools / name), "version", "-o", "json"], text=True
        )
        for name in ["syft", "grype"]
    }
    (output / "tools.json").write_text(json.dumps(tool_data, indent=2))
    sbom = json.loads((output / "sbom.syft.json").read_text())
    (output / "licenses.json").write_text(
        json.dumps(
            {
                "status": "PENDING_ACCOUNTABLE_REVIEW",
                "reviewer": None,
                "components": [
                    {
                        "name": a["name"],
                        "version": a["version"],
                        "licenses": a.get("licenses", []),
                        "type": a["type"],
                    }
                    for a in sbom["artifacts"]
                ],
                "notice": "Inventory only; NOTICE/source-offer and image base obligations require review",
            },
            indent=2,
        )
    )
    files = [
        "image-binding.json",
        "sbom.cdx.json",
        "sbom.syft.json",
        "grype.json",
        "grype-db.json",
        "tools.json",
        "licenses.json",
    ]
    (output / "provenance.json").write_text(
        json.dumps(
            {
                "schema": 1,
                "scan_role": role,
                "image_id": identity,
                "architecture": info["Architecture"],
                "source_sha": subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
                ).strip(),
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "image_role": "isolated candidate; no publish/deploy",
                "sha256": {
                    f: hashlib.sha256((output / f).read_bytes()).hexdigest()
                    for f in files
                },
            },
            indent=2,
        )
    )
    # Collection/identity integrity is required for every image in PR CI.
    # The unchanged zero-severe and accountable licence policy is evaluated
    # separately across ALL eight roles by the mandatory security-sbom job.
    from security_manifest import verify_evidence

    print(json.dumps(verify_evidence(output), indent=2))


if __name__ == "__main__":
    scan(sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3]))
