#!/usr/bin/env python3
"""Fail-closed Stage B UAT preflight, migration gate and deployment driver.

This trusted script runs from reviewed main on a dedicated UAT runner. Feature
source is built on a separate hosted runner; it is never executed on this host.
"""

import argparse
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.request import Request, urlopen

from stage_b_state import locked, transition, save, validate_sha, validate_branch

IMAGE = re.compile(r"ghcr\.io/[a-z0-9_.-]+/[a-z0-9_.-]+@sha256:[0-9a-f]{64}\Z")
ROOT = Path(__file__).resolve().parents[2]
OVERLAY = ROOT / "deploy/uat/compose.images.yml"


def run(*argv, env=None, capture=False):
    return (
        subprocess.run(
            argv,
            check=True,
            text=True,
            env=env,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture else None,
            timeout=1800,
        ).stdout
        if capture
        else None
    )


def check_backup(archive, backup_root):
    if Path(archive).is_symlink() or Path(backup_root).is_symlink():
        raise ValueError("Backup paths cannot be symlinks")
    archive, backup_root = Path(archive).resolve(strict=True), Path(
        backup_root
    ).resolve(strict=True)
    if backup_root not in archive.parents or archive.is_symlink():
        raise ValueError(
            "Backup must be a regular file in the UAT-owned backup directory"
        )
    if archive.stat().st_mode & 0o077 or backup_root.stat().st_mode & 0o077:
        raise ValueError("Backup and backup directory must be private")
    manifest_path = Path(str(archive) + ".json")
    if manifest_path.is_symlink():
        raise ValueError("Backup manifest cannot be a symlink")
    manifest = json.loads(manifest_path.read_text())
    created = datetime.fromisoformat(manifest["created_at"])
    if created.tzinfo is None or not datetime.now(timezone.utc) - timedelta(
        hours=24
    ) <= created <= datetime.now(timezone.utc):
        raise ValueError("Verified backup must be less than 24 hours old")
    digest = hashlib.sha256()
    with archive.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    if (
        manifest.get("format") != "postgresql-custom"
        or digest.hexdigest() != manifest.get("sha256")
        or archive.stat().st_size == 0
    ):
        raise ValueError("Backup checksum, format or size failed verification")
    run("pg_restore", "--list", str(archive), capture=True)
    return manifest["sha256"]


def migration_gate(
    current, target_hash, *, backup, backup_root, review_ref, approver, actor
):
    """Return whether the separately approved one-shot migration must run."""
    needed = current is None or current.get("migration_hash") != target_hash
    if not needed:
        return False, None
    if not (backup and backup_root and review_ref and approver):
        raise ValueError("Migration requires backup, independent review and approval")
    if approver == actor:
        raise ValueError(
            "Migration reviewer must be independent of initiating operator"
        )
    return True, check_backup(backup, backup_root)


def checked_compose(base, project, env):
    base = Path(base).resolve(strict=True)
    if ROOT in base.parents or base == ROOT:
        raise ValueError(
            "Use operator-owned persistent UAT Compose, not repository demo Compose"
        )
    if not re.fullmatch(r"opscontrol-feature-uat-[a-z0-9-]+", project):
        raise ValueError("Refusing non-UAT Compose project")
    base_args = ["docker", "compose", "--project-name", project, "--file", str(base)]
    existing_config = json.loads(
        run(*base_args, "config", "--format", "json", env=env, capture=True)
    )
    if not {"api", "worker", "migration", "frontend", "postgres"} <= set(
        existing_config["services"]
    ):
        raise ValueError("Operator-owned base Compose lacks required services")
    if not existing_config["services"]["worker"].get("command"):
        raise ValueError("Existing UAT worker must have its explicit worker command")
    if existing_config["services"]["migration"].get("ports"):
        raise ValueError("One-shot migration service must not publish ports")
    for name in ("api", "worker", "migration", "frontend"):
        for volume in existing_config["services"][name].get("volumes", []):
            target = (
                volume.get("target", "")
                if isinstance(volume, dict)
                else str(volume).split(":")[-1]
            )
            if (
                target == "/app"
                or target.startswith("/app/app")
                or target.startswith("/app/migrations")
                or target.startswith("/usr/share/nginx/html")
            ):
                raise ValueError(
                    "UAT volume may not override immutable application source"
                )
    args = [*base_args, "--file", str(OVERLAY)]
    config = json.loads(run(*args, "config", "--format", "json", env=env, capture=True))
    required = {"api", "worker", "migration", "frontend", "postgres"}
    if not required <= set(config["services"]):
        raise ValueError("Existing UAT Compose lacks required services")
    for name in ("api", "worker", "migration", "frontend"):
        if "build" in config["services"][name]:
            raise ValueError("UAT runtime may use only prebuilt immutable images")
    if config["services"]["postgres"].get("build"):
        raise ValueError("Unexpected PostgreSQL build")
    # Refuse a fresh project or database; never initialize/reset someone else's DB.
    existing = json.loads(
        run(*base_args, "ps", "--format", "json", env=env, capture=True) or "[]"
    )
    if not any(
        item.get("Service") == "postgres" and item.get("State") == "running"
        for item in existing
    ):
        raise ValueError(
            "Existing owned UAT PostgreSQL container must already be running"
        )
    return args


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "deploy",
            "record-main",
            "release",
            "feature-mode",
            "maintenance",
            "recover",
            "status",
        ),
    )
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--project")
    parser.add_argument("--base-compose", type=Path)
    parser.add_argument("--branch")
    parser.add_argument("--sha")
    parser.add_argument("--backend-image")
    parser.add_argument("--frontend-image")
    parser.add_argument("--migration-hash")
    parser.add_argument("--backup", type=Path)
    parser.add_argument("--backup-root", type=Path)
    parser.add_argument("--migration-review-ref")
    parser.add_argument("--migration-approver")
    parser.add_argument("--approval-ref")
    parser.add_argument("--request")
    parser.add_argument("--api-url")
    parser.add_argument("--frontend-url")
    args = parser.parse_args()
    if args.action == "status":
        with locked(args.state_dir) as (state, _):
            print(json.dumps(state, sort_keys=True))
        return
    if not args.approval_ref or not args.request:
        raise ValueError("Approved operator request and unique run ID required")
    if args.action != "deploy":
        if args.action == "record-main":
            validate_sha(args.sha)
            repository = os.environ.get("GITHUB_REPOSITORY")
            if not repository or not re.fullmatch(
                r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository
            ):
                raise ValueError("GitHub repository identity required")
            remote = run(
                "gh",
                "api",
                f"repos/{repository}/branches/main",
                "--jq",
                ".commit.sha",
                capture=True,
            ).strip()
            if remote != args.sha:
                raise ValueError("Only latest verified origin/main may be recorded")
        if args.action == "recover":
            raise ValueError(
                "Recovery requires manual service and data verification; see runbook"
            )
        with locked(args.state_dir) as (state, root):
            transition(state, args.action, sha=args.sha)
            save(
                state,
                root,
                {
                    "action": args.action,
                    "approval_ref": args.approval_ref,
                    "request": args.request,
                    "sha": args.sha,
                },
            )
        return
    validate_sha(args.sha)
    if args.branch != "main":
        validate_branch(args.branch)
    for image in (args.backend_image, args.frontend_image):
        if not IMAGE.fullmatch(image or ""):
            raise ValueError("Both images must be immutable GHCR digest references")
    if not re.fullmatch(r"[0-9a-f]{64}", args.migration_hash or ""):
        raise ValueError("Migration tree digest required")
    if not args.project or not args.base_compose:
        raise ValueError("Existing UAT project and Compose file required")
    env = os.environ.copy()
    env["STAGE_B_BACKEND_IMAGE"] = args.backend_image
    env["STAGE_B_FRONTEND_IMAGE"] = args.frontend_image
    compose = checked_compose(args.base_compose, args.project, env)
    with locked(args.state_dir) as (state, root):
        transition(
            state,
            "begin",
            sha=args.sha,
            branch=args.branch,
            request=args.request,
            migration_hash=args.migration_hash,
        )
        migration_needed, backup_digest = migration_gate(
            state["current"],
            args.migration_hash,
            backup=args.backup,
            backup_root=args.backup_root,
            review_ref=args.migration_review_ref,
            approver=args.migration_approver,
            actor=os.environ.get("GITHUB_ACTOR"),
        )
        save(
            state,
            root,
            {
                "action": "begin",
                "sha": args.sha,
                "request": args.request,
                "migration_review_ref": args.migration_review_ref,
                "backup_sha256": backup_digest,
                "approval_ref": args.approval_ref,
            },
        )
    try:
        run(*compose, "pull", "api", "worker", "frontend", "migration", env=env)
        if migration_needed:
            run(*compose, "run", "--rm", "--no-deps", "migration", env=env)
        run(*compose, "up", "-d", "--no-deps", "api", "worker", "frontend", env=env)
        run(*compose, "ps", env=env)
        if not args.api_url or not args.frontend_url:
            raise ValueError("Smoke URLs required")
        for url in (args.api_url.rstrip("/") + "/health/db", args.frontend_url):
            with urlopen(
                Request(url, headers={"User-Agent": "OpsControl-Stage-B-Smoke"}),
                timeout=15,
            ) as response:
                if response.status != 200:
                    raise ValueError("HTTP smoke failed")
        # Full authenticated/negative-authorization monitoring smoke is trusted
        # main source; no success is recorded without it.
        smoke = os.environ.get("STAGE_B_AUTH_SMOKE")
        trusted_smoke = ROOT / "scripts/uat/stage_b_smoke.py"
        if (
            not smoke
            or Path(smoke).resolve() != trusted_smoke.resolve()
            or not trusted_smoke.is_file()
            or not os.access(trusted_smoke, os.X_OK)
        ):
            raise ValueError(
                "Trusted authenticated RBAC/monitoring smoke executable required"
            )
        run(str(trusted_smoke))
        with locked(args.state_dir) as (state, root):
            transition(state, "complete", request=args.request)
            save(
                state,
                root,
                {
                    "action": "complete",
                    "request": args.request,
                    "sha": args.sha,
                    "approval_ref": args.approval_ref,
                },
            )
    except BaseException:
        with locked(args.state_dir) as (state, root):
            transition(state, "fail", request=args.request)
            save(
                state,
                root,
                {
                    "action": "fail",
                    "request": args.request,
                    "sha": args.sha,
                    "approval_ref": args.approval_ref,
                },
            )
        raise


if __name__ == "__main__":
    main()
