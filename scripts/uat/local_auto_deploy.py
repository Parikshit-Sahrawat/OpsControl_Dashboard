#!/usr/bin/env python3
"""Fail-closed application-only UAT deployment. Never modifies DB, agent or volumes."""
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import time
from urllib.request import urlopen

def required(key):
    value = os.environ.get(key)
    if not value:
        raise RuntimeError(f"Missing {key}")
    return value

def run(*args, env=None, capture=False):
    return subprocess.run(args, check=True, text=True, env=env,
                          stdout=subprocess.PIPE if capture else None,
                          timeout=600).stdout

def check_url(url):
    with urlopen(url, timeout=15) as response:
        if response.status != 200:
            raise RuntimeError(f"Smoke failed: {url}")

def main():
    base = Path(required("LOCAL_UAT_BASE_COMPOSE")).resolve(strict=True)
    state = Path(required("LOCAL_UAT_STATE_DIR")).resolve(strict=True)
    project = required("LOCAL_UAT_PROJECT")
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,62}", project):
        raise RuntimeError("Invalid Compose project name")
    if state.stat().st_mode & 0o077:
        raise RuntimeError("UAT state directory must be private")
    images = (required("BACKEND_IMAGE").lower(), required("FRONTEND_IMAGE").lower())
    if not all(re.fullmatch(r"ghcr\.io/[a-z0-9_.-]+/[a-z0-9_.-]+@sha256:[a-f0-9]{64}", x) for x in images):
        raise RuntimeError("Images must be immutable GHCR digests")
    sha = required("SOURCE_SHA")
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise RuntimeError("Invalid source SHA")
    with (state / "deployment.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        overlay = Path(__file__).resolve().parents[2] / "deploy/uat/compose.images.yml"
        env = os.environ.copy()
        env.update(STAGE_B_BACKEND_IMAGE=images[0], STAGE_B_FRONTEND_IMAGE=images[1])
        compose = ("docker", "compose", "-p", project, "-f", str(base), "-f", str(overlay))
        config = json.loads(run(*compose, "config", "--format", "json", env=env, capture=True))
        services = config["services"]
        if not {"api", "worker", "frontend", "postgres", "migration"} <= services.keys():
            raise RuntimeError("Existing Compose project lacks expected services")
        if any(services[s].get("build") for s in ("api", "worker", "frontend")):
            raise RuntimeError("Build on UAT host is prohibited")
        for name, image in zip(("api", "frontend"), images):
            if services[name].get("image", "").lower() != image:
                raise RuntimeError(f"Unexpected image for {name}")
        if services["worker"].get("image", "").lower() != images[0]:
            raise RuntimeError("Unexpected worker image")
        # This operation never runs migrations, postgres or the host agent.
        run(*compose, "pull", "api", "worker", "frontend", env=env)
        run(*compose, "up", "-d", "--no-deps", "api", "worker", "frontend", env=env)
        time.sleep(5)
        check_url(required("LOCAL_UAT_API_URL").rstrip("/") + "/health/db")
        check_url(required("LOCAL_UAT_FRONTEND_URL"))
        record = {"sha": sha, "backend_image": images[0], "frontend_image": images[1],
                  "verified_at": time.time(), "result": "SMOKE_PASS"}
        tmp = state / "last-deployment.tmp"
        tmp.write_text(json.dumps(record, indent=2) + "\n")
        os.chmod(tmp, 0o600)
        tmp.replace(state / "last-deployment.json")
        print(json.dumps(record))

if __name__ == "__main__":
    main()
