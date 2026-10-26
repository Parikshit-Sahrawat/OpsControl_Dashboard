"""Experimental, offline finite source replay; NOT a queue/checkpoint repair tool.

Caller must stop the collector, seal the complete producer inventory/archive and
obtain an independent, quiescent PostgreSQL receipt snapshot for the same scope.
Only the exact legacy binary is supported. No automatic production invocation.
"""

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time

LEGACY_SHA = "6bca4ddd928b4b0880f7ec6c16511922f740c497b4efa4b33915b2d54a729213"
MAX_BYTES = 16 * 1024 * 1024
MAX_IDS = 10000


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_sealed(path, sha):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or info.st_uid != os.getuid()
            or info.st_mode & 0o077
            or info.st_size > MAX_BYTES
        ):
            raise ValueError("Unsafe or oversized sealed input")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            data = stream.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES or digest(data) != sha:
            raise ValueError("Sealed input hash mismatch")
        return data
    finally:
        os.close(fd)


def prepare_replay(
    archive,
    inventory,
    receipts,
    seals,
    destination,
    *,
    scope,
    binary_sha,
    now_ns=None,
    fault=None
):
    """Publish missing-only JSONL atomically in an already-approved filelog glob.

    Receipt snapshots are operator-trusted inputs, not self-authenticating proofs.
    The lab exports them directly from PG. A stale snapshot may cause duplicates.
    Deterministic publication is idempotent; it is not exactly-once delivery.
    All paths/parents must be in an exclusively owned stopped-writer workspace.
    """
    if binary_sha != LEGACY_SHA:
        raise ValueError("Unsupported binary; no version transition authorized")
    destination = Path(destination)
    info = destination.lstat()
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.getuid()
        or info.st_mode & 0o077
    ):
        raise ValueError("Replay directory must be owned private non-symlink directory")
    raw = read_sealed(archive, seals["archive"])
    manifest = json.loads(read_sealed(inventory, seals["inventory"]))
    receipt = json.loads(read_sealed(receipts, seals["receipts"]))
    now_ns = time.time_ns() if now_ns is None else now_ns
    if (
        manifest["scope"] != scope
        or receipt["scope"] != scope
        or receipt["source"] != "postgresql"
        or not receipt["writer_stopped"]
    ):
        raise ValueError("Independent stopped-writer receipt scope mismatch")
    if (
        not manifest["sealed_at_ns"]
        <= receipt["cut_ns"]
        <= now_ns
        < manifest["expires_at_ns"]
    ):
        raise ValueError("Expired retention or invalid receipt time boundary")
    expected = manifest["expected_ids"]
    if (
        not expected
        or len(expected) > MAX_IDS
        or len(set(expected)) != len(expected)
        or any(not re.fullmatch(r"event-[0-9]{4}", e) for e in expected)
    ):
        raise ValueError("Invalid bounded independent ID inventory")
    records = {}
    if not raw.endswith(b"\n"):
        raise ValueError("Partial archive record")
    for line in raw.splitlines(keepends=True):
        row = json.loads(line)
        if "_opscontrol_replay_transaction" in row:
            raise ValueError("Reserved replay field already present")
        eid = row["event_id"]
        if eid in records or eid not in expected:
            raise ValueError("Duplicate/conflicting or uninventoried archive record")
        records[eid] = line
    if set(records) != set(expected):
        raise ValueError("Incomplete independent archive coverage")
    counts = receipt["counts_by_id"]
    if set(counts) - set(expected) or any(
        type(v) is not int or v < 0 for v in counts.values()
    ):
        raise ValueError("Invalid receipt inventory")
    missing = sorted(e for e in expected if not counts.get(e, 0))
    transaction = digest(
        json.dumps(
            {"seals": seals, "scope": scope, "binary": binary_sha}, sort_keys=True
        ).encode()
    )
    # A missing prefix can fingerprint-identify as the old, already-checkpointed
    # source. Put an explicit transaction marker first, preserving every original
    # field and stable event ID. Never rewind or delete the old checkpoint.
    payload = b"".join(
        (
            json.dumps(
                {
                    "_opscontrol_replay_transaction": transaction,
                    **json.loads(records[e]),
                },
                separators=(",", ":"),
            )
            + "\n"
        ).encode()
        for e in missing
    )
    output = destination / ("replay-" + transaction + ".log")
    if not missing:
        return {"missing_ids": [], "published": False, "transaction": transaction}
    if output.exists() or output.is_symlink():
        read_sealed(output, digest(payload))
        return {
            "missing_ids": missing,
            "published": True,
            "idempotent": True,
            "transaction": transaction,
            "sha256": digest(payload),
        }
    staging = destination / (".replay-" + transaction + ".pending")
    try:
        fd = os.open(
            staging, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
        )
    except FileExistsError:
        # An incomplete prior write is never silently discarded or overwritten.
        read_sealed(staging, digest(payload))
    else:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    if fault:
        fault("before_publish")
    # Owned, offline workspace precondition; refuse destination replacement.
    if output.exists() or output.is_symlink():
        raise ValueError("Concurrent publication; stop and inspect")
    os.rename(staging, output)
    fd = os.open(destination, os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    if fault:
        fault("after_publish")
    return {
        "missing_ids": missing,
        "published": True,
        "idempotent": False,
        "transaction": transaction,
        "sha256": digest(payload),
    }
