#!/usr/bin/env python3
"""Verify the experimental Linux amd64 candidate; no production guard/pin transition."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import uuid

PIN = json.loads(Path(__file__).with_name("candidate.json").read_text())
VERSION, IMAGE, SHA256 = PIN["version"], PIN["image"], PIN["binary_sha256"]
DOCKER = ["docker", "--host=unix:///var/run/docker.sock"]


def verify(path):
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != SHA256:
        raise ValueError("Contrib SHA-256 mismatch; artifact must not be executed")
    return digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--offline-artifact", type=Path)
    args = parser.parse_args()
    if platform.system() != "Linux" or platform.machine() not in ("x86_64", "amd64"):
        raise SystemExit(
            "Only pinned Linux amd64 is supported; do not substitute another platform"
        )
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        verify(output)
    else:
        with tempfile.TemporaryDirectory(
            prefix="dev052a3-artifact-", dir=output.parent
        ) as directory:
            candidate = Path(directory) / "otelcol-contrib"
            if args.offline_artifact:
                shutil.copyfile(args.offline_artifact, candidate)
            else:
                subprocess.run(
                    [*DOCKER, "pull", "--platform", "linux/amd64", IMAGE], check=True
                )
                observed = subprocess.check_output(
                    [*DOCKER, "image", "inspect", "--format", "{{.Id}}", IMAGE],
                    text=True,
                ).strip()
                if observed != PIN["image_config_digest"]:
                    raise ValueError("Candidate image identity mismatch")
                container = None
                try:
                    container = subprocess.check_output(
                        [
                            *DOCKER,
                            "create",
                            "--platform",
                            "linux/amd64",
                            "--name",
                            "dev052a3-artifact-" + uuid.uuid4().hex,
                            "--network",
                            "none",
                            IMAGE,
                        ],
                        text=True,
                    ).strip()
                    subprocess.run(
                        [
                            *DOCKER,
                            "cp",
                            container + ":/otelcol-contrib",
                            str(candidate),
                        ],
                        check=True,
                    )
                finally:
                    if container:
                        subprocess.run([*DOCKER, "rm", container], check=True)
            verify(candidate)
            candidate.chmod(0o755)
            os.replace(candidate, output)
    version = subprocess.check_output([str(output), "--version"], text=True).strip()
    if version != "otelcol-contrib version " + VERSION:
        raise RuntimeError("Verified runtime version mismatch")
    record = {
        "release_approved": False,
        "guard_transition": "BLOCKED; explicit review and complete promotion gates required",
        "image_config_digest": PIN["image_config_digest"],
        "version": VERSION,
        "platform": "linux/amd64",
        "image": IMAGE,
        "binary_sha256": SHA256,
        "trust": "Binary extracted from scope-approved digest-pinned evaluation image; Docker verifies content digests. Binary hash pinned from that trusted extraction.",
        "license": "Apache-2.0 (upstream distribution); transitive notice review remains a release gate",
        "upstream_license": "https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/v0.163.0/LICENSE",
        "redistribution": "No binary committed or repackaged; retain upstream licenses/notices when distributing.",
        "mode": "offline" if args.offline_artifact else "digest-pinned-image",
        "observed_version": version,
    }
    output.with_suffix(".provenance.json").write_text(
        json.dumps(record, indent=2) + "\n"
    )
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
