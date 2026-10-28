"""Inventory legal-file presence from immutable images, never execute entrypoints."""

import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import uuid

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "docs/verification/dev052/security/2026-10-25-followup"
rows = []
for image in json.loads((OUT / "image-inventory.json").read_text()):
    container = None
    try:
        container = subprocess.check_output(
            [
                "docker",
                "create",
                "--network",
                "none",
                "--name",
                "dev052a2-license-" + uuid.uuid4().hex,
                image["id"],
            ],
            text=True,
        ).strip()
        process = subprocess.Popen(
            ["docker", "export", container], stdout=subprocess.PIPE
        )
        files = []
        with tarfile.open(fileobj=process.stdout, mode="r|") as archive:
            for member in archive:
                base = Path(member.name).name.lower()
                if (
                    member.isfile()
                    and member.size <= 2_000_000
                    and (
                        base.startswith(("license", "licence", "notice", "copying"))
                        or base == "copyright"
                    )
                ):
                    data = archive.extractfile(member).read()
                    files.append(
                        {
                            "path": member.name,
                            "bytes": len(data),
                            "sha256": hashlib.sha256(data).hexdigest(),
                        }
                    )
        if process.wait() != 0:
            raise RuntimeError("Image export failed")
        rows.append(
            {
                "image": image["name"],
                "id": image["id"],
                "legal_files": files,
                "review": "Presence/hash only, not component-obligation fulfillment or signoff",
            }
        )
        print(image["name"], len(files), flush=True)
    finally:
        # create has no user mounts; -v removes only its own anonymous volumes.
        if container:
            subprocess.run(
                ["docker", "rm", "-v", container], check=True, stdout=subprocess.DEVNULL
            )
    (OUT / "legal-file-presence.json").write_text(json.dumps(rows, indent=2) + "\n")
