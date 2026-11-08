"""Install official scanners after verifying locked archive SHA256, no curl pipe."""

import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[2]


def install(destination):
    destination.mkdir(parents=True, exist_ok=True)
    lock = json.loads((ROOT / "scripts/ci/tool-lock.json").read_text())
    for name, tool in lock.items():
        data = urllib.request.urlopen(tool["url"], timeout=90).read()
        if hashlib.sha256(data).hexdigest() != tool["sha256"]:
            raise ValueError("Scanner archive checksum mismatch")
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
            member = archive.getmember(name)
            if not member.isfile() or member.size > 300_000_000:
                raise ValueError("Unsafe scanner archive member")
            output = destination / name
            output.write_bytes(archive.extractfile(member).read())
            output.chmod(0o755)
    (destination / "tool-lock.json").write_text(json.dumps(lock, indent=2))


if __name__ == "__main__":
    install(Path(sys.argv[1]))
