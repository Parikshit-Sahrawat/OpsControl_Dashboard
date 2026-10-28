"""Stage an explicit experimental contract in a new private source directory.

Never mutates the checkout or changes a default provisioning/runtime pin.
The candidate binary must match the reviewed pin before staging/execution.
"""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def prepare(stage, binary):
    pin = json.loads((HERE / "candidate.json").read_text())
    with binary.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != pin["binary_sha256"]:
            raise ValueError("Candidate checksum mismatch; refusing execution")
    version = subprocess.check_output([str(binary), "--version"], text=True).strip()
    if version != "otelcol-contrib version " + pin["version"]:
        raise ValueError("Candidate version mismatch")
    stage.mkdir(mode=0o700, parents=True, exist_ok=False)
    archive = stage / "source.tar"
    with archive.open("wb") as target:
        subprocess.run(
            [
                "git",
                "archive",
                "HEAD",
                "backend/app",
                "backend/tests",
                "backend/scripts",
                "backend/migrations",
                "backend/alembic.ini",
                "agent",
            ],
            cwd=ROOT,
            stdout=target,
            check=True,
        )
    source_sha = hashlib.sha256(archive.read_bytes()).hexdigest()
    with tarfile.open(archive) as tar:
        tar.extractall(stage, filter="data")
    archive.unlink()
    patch = HERE / "experimental-0.163.2.patch"
    subprocess.run(["git", "apply", "--check", str(patch)], cwd=stage, check=True)
    subprocess.run(["git", "apply", str(patch)], cwd=stage, check=True)
    # Fixture inputs follow the deliberately staged contract. Assertions and
    # unknown-version rejection cases are untouched.
    fixtures = [
        "backend/tests/test_agent_v15.py",
        "backend/scripts/agent_v15_acceptance_probe.py",
    ]
    for name in fixtures:
        path = stage / name
        path.write_text(path.read_text().replace('"0.123.0"', '"0.163.2"'))
    record = {
        **pin,
        "source_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "source_archive_sha256": source_sha,
        "experimental_patch_sha256": hashlib.sha256(patch.read_bytes()).hexdigest(),
        "fixture_literal_updates": fixtures,
        "stage": str(stage),
        "production_guard_modified": False,
    }
    (stage / "overlay-provenance.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.stage.resolve(), args.binary.resolve()), indent=2))
