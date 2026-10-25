#!/usr/bin/env python3
"""Verify the approved Linux amd64 Contrib runtime before use; never trust latest."""
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

VERSION = "0.123.0"
IMAGE = "otel/opentelemetry-collector-contrib:0.123.0@sha256:e39311df1f3d941923c00da79ac7ba6269124a870ee87e3c3ad24d60f8aee4d2"
SHA256 = "6bca4ddd928b4b0880f7ec6c16511922f740c497b4efa4b33915b2d54a729213"


def verify(path):
    digest = hashlib.file_digest(path.open("rb"), "sha256").hexdigest()
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
            prefix="dev052-artifact-", dir=output.parent
        ) as directory:
            candidate = Path(directory) / "otelcol-contrib"
            if args.offline_artifact:
                shutil.copyfile(args.offline_artifact, candidate)
            else:
                subprocess.run(
                    ["docker", "pull", "--platform", "linux/amd64", IMAGE], check=True
                )
                container = None
                try:
                    container = subprocess.check_output(
                        [
                            "docker",
                            "create",
                            "--platform",
                            "linux/amd64",
                            "--name",
                            "dev052-artifact-" + uuid.uuid4().hex,
                            "--network",
                            "none",
                            IMAGE,
                        ],
                        text=True,
                    ).strip()
                    subprocess.run(
                        [
                            "docker",
                            "cp",
                            container + ":/otelcol-contrib",
                            str(candidate),
                        ],
                        check=True,
                    )
                finally:
                    if container:
                        subprocess.run(["docker", "rm", container], check=True)
            verify(candidate)
            candidate.chmod(0o755)
            os.replace(candidate, output)
    version = subprocess.check_output([str(output), "--version"], text=True).strip()
    if version != "otelcol-contrib version " + VERSION:
        raise RuntimeError("Verified runtime version mismatch")
    record = {
        "version": VERSION,
        "platform": "linux/amd64",
        "image": IMAGE,
        "binary_sha256": SHA256,
        "trust": "Binary extracted from repository-approved digest-pinned upstream image; Docker verifies content digests. Binary hash pinned from that trusted extraction.",
        "license": "Apache-2.0 (upstream distribution); transitive notice review remains a release gate",
        "upstream_license": "https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/v0.123.0/LICENSE",
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
