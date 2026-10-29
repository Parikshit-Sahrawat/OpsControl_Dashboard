#!/usr/bin/env python3
"""Real Docker readiness fault/recovery fixture; never mounts application volumes.

This is a component acceptance check, not full release/backup acceptance.
"""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import uuid

sys.path.insert(0, str(Path(__file__).parent))
from local_auto_deploy import check_worker


def main():
    project = "opscontrol-accept-" + uuid.uuid4().hex[:12]
    docker = ("docker", "--host=unix:///var/run/docker.sock", "compose", "-p", project)
    with tempfile.TemporaryDirectory() as td:
        fixture = Path(td) / "compose.json"
        fixture.write_text(
            json.dumps(
                {
                    "services": {
                        "worker": {
                            "image": "opscontrol-uat-api:latest",
                            "network_mode": "none",
                            "read_only": True,
                            "tmpfs": ["/tmp"],
                            "entrypoint": ["python", "-c"],
                            "command": [
                                "import time,pathlib; p=pathlib.Path('/tmp/opscontrol-worker-heartbeat'); p.write_text(str(time.time())); time.sleep(300)"
                            ],
                        }
                    }
                }
            )
        )
        compose = (*docker, "-f", str(fixture))

        def run(*args):
            subprocess.run(
                (*compose, *args), check=True, timeout=60, capture_output=True
            )

        def rejected():
            try:
                check_worker(compose, None, started)
            except subprocess.CalledProcessError:
                return
            raise AssertionError("Unhealthy worker accepted")

        started = time.time()
        try:
            run("up", "-d", "--no-build", "--pull", "never")
            check_worker(compose, None, started)
            print("PASS healthy worker")
            run(
                "exec",
                "-T",
                "worker",
                "python",
                "-c",
                "from pathlib import Path; Path('/tmp/opscontrol-worker-heartbeat').write_text('1')",
            )
            rejected()
            print("PASS stale heartbeat rejected")
            run("stop", "worker")
            rejected()
            print("PASS stopped worker rejected")
            run("up", "-d", "--force-recreate", "--no-build", "--pull", "never")
            check_worker(compose, None, started)
            print("PASS worker recovery")
        finally:
            # No volumes are created or deleted; only this UUID fixture is removed.
            run("down")


if __name__ == "__main__":
    main()
