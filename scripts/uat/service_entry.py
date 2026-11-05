"""Root-owned entrypoint for the dedicated outbound deployment identity."""

import os
from pathlib import Path
import stat


def protected(path):
    path = Path(path)
    for item in (path, *path.parents):
        info = item.lstat()
        if stat.S_ISLNK(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise RuntimeError(f"Untrusted deployment configuration: {item}")
    return path


def main():
    if os.geteuid() == 0:
        raise RuntimeError("Run as dedicated opscontrol-deploy user")
    code = protected(Path(__file__).parent)
    configuration = protected("/etc/opscontrol-uat/controller.json")
    import json

    config = json.loads(configuration.read_text())
    allowed = {
        "LOCAL_UAT_BASE_COMPOSE",
        "LOCAL_UAT_OVERRIDE_COMPOSE",
        "LOCAL_UAT_PROJECT",
        "LOCAL_UAT_API_URL",
        "LOCAL_UAT_FRONTEND_URL",
    }
    if set(config) != allowed:
        raise RuntimeError("Unexpected controller configuration keys")
    for name in ("LOCAL_UAT_BASE_COMPOSE", "LOCAL_UAT_OVERRIDE_COMPOSE"):
        protected(config[name])
    for source in code.glob("*.py"):
        protected(source)
    token = Path(os.environ["CREDENTIALS_DIRECTORY"]) / "github-token"
    os.environ["GH_TOKEN"] = token.read_text().strip()
    os.environ.update(config)
    os.execv(
        "/usr/bin/python3",
        [
            "/usr/bin/python3",
            str(code / "pull_release.py"),
            "--state-dir",
            "/var/lib/opscontrol-uat-deploy",
        ],
    )


if __name__ == "__main__":
    main()
