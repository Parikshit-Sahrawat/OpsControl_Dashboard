"""Offline Linux checkpoint backup + bounded archive replay, not a BoltDB converter.

Requires an operator-confirmed stopped collector, confirmed healthy legacy cut,
unchanged config and independently complete stable-ID source archive. Never edits
BoltDB internals, deletes failed state, or promises exactly-once delivery.
"""

import contextlib
import ctypes
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import uuid


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def private(path):
    path = Path(path)
    if path.is_symlink():
        raise ValueError("Symlink refused")
    info = path.stat()
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.getuid()
        or info.st_mode & 0o077
    ):
        raise ValueError("Owned private 0700 directory required")
    return path


def sync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic(path, data):
    path = Path(path)
    private(path.parent)
    temporary = path.with_name("." + path.name + ".tmp-" + uuid.uuid4().hex)
    fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        sync_dir(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def write_json(path, value):
    atomic(path, (json.dumps(value, sort_keys=True, indent=2) + "\n").encode())


def tree(path):
    path = private(path)
    result = {}
    for file in sorted(path.rglob("*")):
        if file.is_symlink():
            raise ValueError("Symlink in checkpoint tree")
        info = file.stat()
        if file.is_dir():
            private(file)
            continue
        if (
            not file.is_file()
            or info.st_nlink != 1
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o600
        ):
            raise ValueError("Only owned, nonlinked 0600 regular state files supported")
        result[str(file.relative_to(path))] = {
            "sha256": sha(file),
            "size": info.st_size,
            "mode": "0600",
        }
    if not result:
        raise ValueError("Populated checkpoint state required")
    return result


@contextlib.contextmanager
def locked(path):
    before = tree(path)
    descriptors = []
    try:
        for name in before:
            fd = os.open(Path(path) / name, os.O_RDWR | os.O_NOFOLLOW)
            descriptors.append(fd)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ValueError(
                    "Collector/state writer active; stop it first"
                ) from None
        if tree(path) != before:
            raise ValueError("State changed while acquiring locks")
        yield before
    finally:
        for fd in descriptors:
            os.close(fd)


def copy_tree(source, destination, fault=None):
    destination.mkdir(mode=0o700)
    for index, name in enumerate(tree(source)):
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        atomic(target, (Path(source) / name).read_bytes())
        if fault == "partial-copy" and index == 0:
            raise RuntimeError("INJECTED partial-copy")
    sync_dir(destination)


def snapshot(state, backup, config):
    """Caller must prove this cut was produced by healthy pinned 0.123.0."""
    state, backup, config = Path(state), Path(backup), Path(config)
    private(backup.parent)
    if backup.exists():
        raise ValueError("Backup already exists; immutable cut cannot be overwritten")
    partial = backup.with_name(backup.name + ".partial-" + uuid.uuid4().hex)
    partial.mkdir(mode=0o700)
    with locked(state) as inventory:
        copy_tree(state, partial / "state")
        if tree(partial / "state") != inventory:
            raise ValueError("Backup integrity mismatch")
        write_json(
            partial / "manifest.json",
            {
                "version": 1,
                "scope": "operator-confirmed legacy cut",
                "config_sha256": sha(config),
                "files": inventory,
            },
        )
        atomic(partial / "SEALED", sha(partial / "manifest.json").encode())
    os.rename(partial, backup)
    sync_dir(backup.parent)
    return verify_backup(backup, config)


def verify_backup(backup, config):
    backup = private(backup)
    if (backup / "SEALED").is_symlink() or (backup / "manifest.json").is_symlink():
        raise ValueError("Linked backup metadata refused")
    if (backup / "SEALED").read_text() != sha(backup / "manifest.json"):
        raise ValueError("Backup manifest hash mismatch")
    manifest = json.loads((backup / "manifest.json").read_text())
    if manifest["config_sha256"] != sha(config) or manifest["files"] != tree(
        backup / "state"
    ):
        raise ValueError("Backup/config integrity mismatch")
    return manifest


def seal_archive(files, expected_ids, output):
    """Complete external ID inventory is mandatory; missing source data blocks."""
    output = Path(output)
    private(output.parent)
    if not isinstance(expected_ids, list) or not expected_ids:
        raise ValueError("Nonempty independent event inventory required")
    if output.exists():
        raise ValueError("Archive exists")
    records = {}
    sources = []
    for file in files:
        file = Path(file)
        if file.is_symlink() or not file.is_file() or file.stat().st_nlink != 1:
            raise ValueError("Unsafe log archive source")
        sources.append(
            {"name": file.name, "sha256": sha(file), "size": file.stat().st_size}
        )
        for line in file.read_text().splitlines():
            record = json.loads(line)
            event_id = record.get("event_id")
            if event_id is None:
                continue
            if not isinstance(event_id, str) or not re.fullmatch(
                r"[A-Za-z0-9_.:-]{1,120}", event_id
            ):
                raise ValueError("Stable event ID required")
            if event_id in records and records[event_id] != record:
                raise ValueError("Conflicting event ID bodies")
            records[event_id] = record
    if len(set(expected_ids)) != len(expected_ids) or set(expected_ids) != set(records):
        raise ValueError(
            "Incomplete/conflicting archive versus independent event inventory"
        )
    partial = output.with_name(output.name + ".partial-" + uuid.uuid4().hex)
    partial.mkdir(mode=0o700)
    atomic(
        partial / "records.jsonl",
        b"".join(
            (json.dumps(records[k], sort_keys=True) + "\n").encode()
            for k in sorted(records)
        ),
    )
    write_json(
        partial / "manifest.json",
        {
            "version": 1,
            "event_ids": sorted(records),
            "sources": sources,
            "records_sha256": sha(partial / "records.jsonl"),
        },
    )
    atomic(partial / "SEALED", sha(partial / "manifest.json").encode())
    os.rename(partial, output)
    sync_dir(output.parent)
    return json.loads((output / "manifest.json").read_text())


def verify_archive(archive):
    archive = private(archive)
    for name in ["SEALED", "manifest.json", "records.jsonl"]:
        path = archive / name
        if (
            path.is_symlink()
            or not path.is_file()
            or path.stat().st_nlink != 1
            or stat.S_IMODE(path.stat().st_mode) != 0o600
        ):
            raise ValueError("Unsafe archive file")
    manifest = json.loads((archive / "manifest.json").read_text())
    if (archive / "SEALED").read_text() != sha(archive / "manifest.json") or manifest[
        "records_sha256"
    ] != sha(archive / "records.jsonl"):
        raise ValueError("Archive integrity mismatch")
    records = [
        json.loads(line)
        for line in (archive / "records.jsonl").read_text().splitlines()
    ]
    if [r["event_id"] for r in records] != manifest["event_ids"]:
        raise ValueError("Archive event inventory mismatch")
    return manifest


def exchange(a, b):
    """Atomic whole-directory exchange. No non-atomic fallback is permitted."""
    if Path(a).stat().st_dev != Path(b).stat().st_dev:
        raise ValueError("Same filesystem required")
    libc = ctypes.CDLL(None, use_errno=True)
    function = getattr(libc, "renameat2", None)
    if function is None:
        raise RuntimeError("BLOCKED: Linux atomic renameat2 exchange unavailable")
    function.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    function.restype = ctypes.c_int
    if function(-100, os.fsencode(a), -100, os.fsencode(b), 2) != 0:
        raise OSError(ctypes.get_errno(), "Atomic checkpoint exchange failed")
    sync_dir(Path(a).parent)


def recover(
    state, backup, archive, config, vault, replay_root, transaction, fault=None
):
    state, backup, archive, config, vault, replay_root = map(
        Path, [state, backup, archive, config, vault, replay_root]
    )
    private(state.parent)
    private(vault)
    private(replay_root)
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,60}", transaction):
        raise ValueError("Safe explicit transaction ID required")
    manifest = verify_backup(backup, config)
    archive_manifest = verify_archive(archive)
    journal = vault / (transaction + ".json")
    stage = state.with_name("." + state.name + ".exchange-" + transaction)
    replay = replay_root / ("recovery-" + transaction + ".log")
    # A unique first fingerprint makes this a new input; all source IDs remain
    # unchanged. The explicit control marker is excluded from source-ID counts.
    payload = (
        json.dumps(
            {
                "recovery_generation": transaction,
                "control": "bounded replay",
                "padding": "-" * 1100,
            }
        )
        + "\n"
    ).encode() + (archive / "records.jsonl").read_bytes()
    request = {
        "state": str(state.resolve()),
        "backup_sha256": sha(backup / "manifest.json"),
        "archive_sha256": sha(archive / "manifest.json"),
        "config_sha256": sha(config),
        "replay_sha256": hashlib.sha256(payload).hexdigest(),
    }
    if replay.is_symlink() or (
        replay.exists()
        and (
            not replay.is_file()
            or replay.stat().st_nlink != 1
            or stat.S_IMODE(replay.stat().st_mode) != 0o600
            or sha(replay) != request["replay_sha256"]
        )
    ):
        raise ValueError("Replay path collision; refusing mutation")
    lockfd = os.open(
        vault / ".operator.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600
    )
    try:
        fcntl.flock(lockfd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with locked(state) as current:
            if journal.exists():
                if journal.is_symlink():
                    raise ValueError("Journal symlink refused")
                record = json.loads(journal.read_text())
                if record["request"] != request:
                    raise ValueError(
                        "Transaction cannot be reused for different inputs"
                    )
                if record["phase"] == "COMPLETED":
                    if (
                        current != manifest["files"]
                        or not replay.exists()
                        or sha(replay) != request["replay_sha256"]
                    ):
                        raise ValueError(
                            "Completed state advanced or replay changed; refusing another rewind"
                        )
                    return {**record, "idempotent_noop": True}
            else:
                record = {"request": request, "before": current, "phase": "PREPARED"}
                write_json(journal, record)
            if current == record["before"]:
                stage_inventory = None
                if stage.exists():
                    private(stage)
                    stage_inventory = tree(stage) if any(stage.iterdir()) else {}
                if stage.exists() and stage_inventory != manifest["files"]:
                    os.rename(
                        stage,
                        stage.with_name(stage.name + ".incomplete-" + uuid.uuid4().hex),
                    )
                if not stage.exists():
                    copy_tree(backup / "state", stage, fault=fault)
                if tree(stage) != manifest["files"]:
                    raise ValueError("Staged restoration failed hash verification")
                record["phase"] = "STAGED"
                write_json(journal, record)
                if fault == "before-exchange":
                    raise RuntimeError("INJECTED before-exchange")
                exchange(state, stage)
                if fault == "kill-after-exchange":
                    os._exit(86)  # Explicit test-only crash; durable journal resumes.
                if fault == "after-exchange":
                    raise RuntimeError("INJECTED after-exchange")
            elif (
                current != manifest["files"]
                or not stage.exists()
                or tree(stage) != record["before"]
            ):
                raise ValueError(
                    "Unknown mixed/modified state; manual recovery required"
                )
            # stage now preserves the entire failed candidate tree, not deleted.
            record["phase"] = "RESTORED"
            write_json(journal, record)
            if fault == "before-replay":
                raise RuntimeError("INJECTED before-replay")
            if replay.exists():
                if replay.is_symlink() or sha(replay) != request["replay_sha256"]:
                    raise ValueError("Replay path collision; refusing overwrite")
            else:
                atomic(replay, payload)
            record.update(
                phase="COMPLETED",
                replay_event_ids=archive_manifest["event_ids"],
                preserved_candidate=str(stage),
                idempotent_noop=False,
            )
            write_json(journal, record)
            return record
    finally:
        os.close(lockfd)


def assert_startable(vault):
    for path in private(vault).glob("*.json"):
        if json.loads(path.read_text()).get("phase") != "COMPLETED":
            raise ValueError(
                "Pending recovery journal; resume or investigate before start"
            )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    backup = commands.add_parser("backup")
    for name in ["state", "backup", "config"]:
        backup.add_argument("--" + name, type=Path, required=True)
    archive = commands.add_parser("archive")
    archive.add_argument("--expected-ids", type=Path, required=True)
    archive.add_argument("--output", type=Path, required=True)
    archive.add_argument("files", nargs="+", type=Path)
    restore = commands.add_parser("recover")
    for name in ["state", "backup", "archive", "config", "vault", "replay-root"]:
        restore.add_argument("--" + name, type=Path, required=True)
    restore.add_argument("--transaction", required=True)
    restore.add_argument(
        "--inject-failure",
        choices=[
            "partial-copy",
            "before-exchange",
            "after-exchange",
            "before-replay",
            "kill-after-exchange",
        ],
    )
    start = commands.add_parser("check-start")
    start.add_argument("--vault", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "backup":
        result = snapshot(args.state, args.backup, args.config)
    elif args.command == "archive":
        result = seal_archive(
            args.files, json.loads(args.expected_ids.read_text()), args.output
        )
    elif args.command == "check-start":
        assert_startable(args.vault)
        result = {"start_permitted": True}
    else:
        result = recover(
            args.state,
            args.backup,
            args.archive,
            args.config,
            args.vault,
            args.replay_root,
            args.transaction,
            args.inject_failure,
        )
    print(json.dumps(result, indent=2))
