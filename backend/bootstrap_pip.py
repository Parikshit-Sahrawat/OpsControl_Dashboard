"""Install the pinned pip wheel without executing the old installed pip.

Uses only stdlib HTTPS/hash verification before loading the verified wheel.
No network package resolution occurs during installation. Offline input must
match the same reviewed hash. Python/OS startup remains part of the trust base.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import ssl
import subprocess
import sys
import tempfile
import urllib.request


def verify(path, expected):
    with path.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != expected:
        raise ValueError("pip bootstrap checksum mismatch; refusing execution")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline-wheel", type=Path)
    args = parser.parse_args()
    pin = json.loads(Path(__file__).with_name("pip-bootstrap.json").read_text())
    with tempfile.TemporaryDirectory(prefix="opscontrol-pip-bootstrap-") as directory:
        wheel = Path(directory) / pin["filename"]
        if args.offline_wheel:
            wheel.write_bytes(args.offline_wheel.read_bytes())
        else:
            ca = os.getenv("PIP_CERT") or os.getenv("SSL_CERT_FILE")
            context = ssl.create_default_context(cafile=ca)
            with urllib.request.urlopen(
                pin["url"], context=context, timeout=60
            ) as response:
                data = response.read(16 * 1024 * 1024 + 1)
            if len(data) > 16 * 1024 * 1024:
                raise ValueError("pip wheel exceeds size limit")
            wheel.write_bytes(data)
        verify(wheel, pin["sha256"])
        # -I ignores injected PYTHONPATH. The verified wheel precedes site-packages;
        # no old pip installer is invoked and no index is contacted by pip.
        program = 'import runpy,sys;sys.path.insert(0,sys.argv[1]);sys.argv=["pip","install","--isolated","--no-index","--no-deps","--no-cache-dir","--upgrade",sys.argv[1]];runpy.run_module("pip",run_name="__main__")'
        subprocess.run([sys.executable, "-I", "-c", program, str(wheel)], check=True)
        version = subprocess.check_output(
            [sys.executable, "-I", "-m", "pip", "--version"], text=True
        )
        if not version.startswith("pip " + pin["version"] + " "):
            raise RuntimeError("Installed pip version mismatch")
        print(
            json.dumps(
                {
                    "version": pin["version"],
                    "wheel_sha256": pin["sha256"],
                    "old_pip_executed": False,
                    "installation_index_access": False,
                }
            )
        )


if __name__ == "__main__":
    main()
