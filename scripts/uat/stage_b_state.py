#!/usr/bin/env python3
"""Persistent, serialized Stage B UAT deployment state. No Docker operations here."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import tempfile

SHA = re.compile(r"[0-9a-f]{40}\Z")
BRANCH = re.compile(r"(?!.*(?:\.\.|//|@\{|\\))[A-Za-z0-9][A-Za-z0-9._/-]{0,127}\Z")
MODES = {"FEATURE_UAT", "MAIN", "MAINTENANCE"}


def validate_sha(value):
    if not SHA.fullmatch(value or ""):
        raise ValueError("An immutable 40-character lowercase commit SHA is required")
    return value


def validate_branch(value):
    if not BRANCH.fullmatch(value or "") or value.endswith(("/", ".", ".lock")):
        raise ValueError("Invalid branch name")
    return value


def now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def locked(root):
    root = Path(root)
    if root.is_symlink():
        raise ValueError("State directory cannot be a symlink")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if root.stat().st_mode & 0o077:
        raise ValueError("State directory must be private (0700)")
    with (root / "lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = root / "state.json"
        if path.is_symlink():
            raise ValueError("State file cannot be a symlink")
        state = (
            json.loads(path.read_text())
            if path.exists()
            else {
                "version": 1,
                "mode": "FEATURE_UAT",
                "current": None,
                "pending_main": None,
                "inflight": None,
                "needs_recovery": False,
                "revision": 0,
            }
        )
        if state.get("version") != 1 or state.get("mode") not in MODES:
            raise ValueError("Unsupported or corrupt deployment state")
        yield state, root


def save(state, root, event):
    state["revision"] += 1
    state["updated_at"] = now()
    data = (json.dumps(state, sort_keys=True, indent=2) + "\n").encode()
    fd, name = tempfile.mkstemp(prefix=".stage-b-", dir=root)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, root / "state.json")
        with (root / "events.jsonl").open("a") as stream:
            stream.write(
                json.dumps({"at": now(), "revision": state["revision"], **event}) + "\n"
            )
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(root / "events.jsonl", 0o600)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def transition(
    state, command, *, sha=None, branch=None, request=None, migration_hash=None
):
    """Pure transition rules, shared by CLI and tests. Mutations require the lock."""
    if command == "record-main":
        validate_sha(sha)
        # Caller must independently verify this is the current origin/main tip.
        state["pending_main"] = sha
    elif command == "begin":
        if state["inflight"] or state["needs_recovery"]:
            raise ValueError(
                "Another deployment or unresolved failure blocks this operation"
            )
        if not request:
            raise ValueError("Unique request ID required")
        if branch == "main":
            if state["mode"] != "MAIN" or state["pending_main"] != validate_sha(sha):
                raise ValueError(
                    "MAIN deployment requires released mode and latest pending main SHA"
                )
        else:
            validate_branch(branch)
            validate_sha(sha)
            if state["mode"] != "FEATURE_UAT":
                raise ValueError("Feature deployment requires FEATURE_UAT mode")
        state["inflight"] = {
            "request": request,
            "branch": branch,
            "sha": sha,
            "migration_hash": migration_hash,
            "started_at": now(),
        }
    elif command == "complete":
        if not state["inflight"] or state["inflight"]["request"] != request:
            raise ValueError("No matching deployment in progress")
        item = state["inflight"]
        state["current"] = {
            key: item[key] for key in ("branch", "sha", "migration_hash")
        }
        state["current"]["verified_at"] = now()
        if item["branch"] == "main" and state["pending_main"] == item["sha"]:
            state["pending_main"] = None
        state["inflight"] = None
    elif command == "fail":
        if not state["inflight"] or state["inflight"]["request"] != request:
            raise ValueError("No matching deployment in progress")
        state["failed_attempt"] = state["inflight"]
        state["inflight"] = None
        state["needs_recovery"] = True
        state["mode"] = "MAINTENANCE"
    elif command == "release":
        if state["inflight"] or state["needs_recovery"]:
            raise ValueError("Deployment or unresolved failure blocks release")
        if state["mode"] != "FEATURE_UAT" or not state["pending_main"]:
            raise ValueError("Release requires FEATURE_UAT and a pending main commit")
        state["mode"] = "MAIN"
    elif command == "feature-mode":
        if state["inflight"] or state["needs_recovery"]:
            raise ValueError("Deployment or unresolved failure blocks mode switch")
        state["mode"] = "FEATURE_UAT"
    elif command == "maintenance":
        if state["inflight"]:
            raise ValueError("Deployment in progress")
        state["mode"] = "MAINTENANCE"
    elif command == "recover":
        if state["inflight"] or not state["needs_recovery"]:
            raise ValueError("No failed deployment requiring recovery")
        # Operator must verify actual services before clearing the failure.
        state["needs_recovery"] = False
        state["mode"] = "FEATURE_UAT"
    else:
        raise ValueError("Unknown transition")
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=(
            "status",
            "record-main",
            "begin",
            "complete",
            "fail",
            "release",
            "feature-mode",
            "maintenance",
            "recover",
        ),
    )
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--sha")
    parser.add_argument("--branch")
    parser.add_argument("--request")
    parser.add_argument("--migration-hash")
    parser.add_argument("--approval-ref")
    args = parser.parse_args()
    with locked(args.state_dir) as (state, root):
        if args.command != "status":
            if (
                args.command not in ("record-main", "complete", "fail")
                and not args.approval_ref
            ):
                raise ValueError("Operator approval reference required")
            transition(
                state,
                args.command,
                sha=args.sha,
                branch=args.branch,
                request=args.request,
                migration_hash=args.migration_hash,
            )
            save(
                state,
                root,
                {
                    "command": args.command,
                    "request": args.request,
                    "approval_ref": args.approval_ref,
                    "sha": args.sha,
                },
            )
        print(json.dumps(state, sort_keys=True))


if __name__ == "__main__":
    main()
