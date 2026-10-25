"""Direct pinned runtime checkpoint benchmark; no Agent version-guard bypass.

Legacy API identity authorizes the owned synthetic OTLP producer. Direct binary
processes isolate state formats; they do not advertise a promoted Agent runtime.
"""

import collections
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import recovery as r

sys.path.insert(0, "/work/backend/scripts")
from acceptance_scope import probe_headers

assert os.environ["ENVIRONMENT"] == "test" and os.environ["DEV052A3_LAB"] == "1"
ROOT = Path("/fixture")
fixture = json.loads((ROOT / "fixture.json").read_text())
report = {
    "status": "FAIL",
    "checks": [],
    "failed_cases": [],
    "phases": [],
    "scope": "synthetic checkpoint-only direct-runtime benchmark; not supported Agent transition",
}
process = None
logs = ROOT / "logs"
logs.mkdir(mode=0o700)
retention = ROOT / "retention"
retention.mkdir(mode=0o700)
home = ROOT / "checkpoint-home"
home.mkdir(mode=0o700)
vault = ROOT / "vault"
vault.mkdir(mode=0o700)
state = home / "otel-checkpoints"
state.mkdir(mode=0o700)
source = logs / "app.log"
expected = []
api = os.environ["ARCH001_API_URL"]


def call(path, method="GET", body=None, token=None, expected=200):
    request = Request(
        api + path,
        method=method,
        headers={
            "Content-Type": "application/json",
            **({"Authorization": "Bearer " + token} if token else {}),
            **probe_headers(api, token, path),
        },
        data=None if body is None else json.dumps(body).encode(),
    )
    try:
        with urlopen(request, timeout=15) as response:
            code, raw = response.status, response.read()
    except HTTPError as error:
        code, raw = error.code, error.read()
    assert code == expected, (path, code, expected)
    return json.loads(raw) if raw else None


def passed(name):
    report["checks"].append(name)
    print(name + ": PASS", flush=True)


def counts():
    with sqlite3.connect(
        "file:/fixture/api-ledger.sqlite?mode=ro", uri=True, timeout=15
    ) as db:
        return collections.Counter(
            event
            for row in db.execute("SELECT event_ids FROM attempts WHERE status=200")
            for event in json.loads(row[0])
        )


def phase(name):
    actual = counts()
    report["phases"].append(
        {
            "name": name,
            "cut_utc": datetime.now(timezone.utc).isoformat(),
            "expected": list(expected),
            "accepted_attempt_counts": dict(actual),
            "missing": sorted(set(expected) - set(actual)),
            "duplicate_attempts": sum(max(n - 1, 0) for n in actual.values()),
        }
    )


def wait(predicate, label, timeout=65):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            passed(label)
            return
        if process is not None:
            assert process.poll() is None, "Runtime exited: " + label
        time.sleep(0.25)
    raise AssertionError("Timeout: " + label)


def emit(first, last, truncate=False):
    ids = [f"event-{i:04d}" for i in range(first, last)]
    expected.extend(ids)
    r.atomic(
        ROOT / "expected-ids.json", json.dumps(expected).encode()
    )  # Independent durable producer inventory first.
    payload = b"".join(
        (
            json.dumps(
                {
                    "event_id": event,
                    "sequence": int(event.split("-")[1]),
                    "message": "controlled event",
                    "padding": event * 120,
                },
                sort_keys=True,
            )
            + "\n"
        ).encode()
        for event in ids
    )
    with source.open("wb" if truncate else "ab") as stream:
        os.chmod(source, 0o600)
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def stop(kill=False):
    global process
    if process is not None and process.poll() is None:
        process.kill() if kill else process.terminate()
        process.wait(timeout=20)
    process = None


def start(version, legacy_encoding=False, root=home):
    global process
    r.assert_startable(vault)
    binary = (
        "/runtime/otelcol-contrib-0.123.0"
        if version == "0.123.0"
        else "/runtime/otelcol-contrib"
    )
    command = [binary]
    if legacy_encoding:
        command.append("--feature-gates=-filelog.protobufCheckpointEncoding")
    output = (ROOT / "runtime.log").open("ab")
    process = subprocess.Popen(
        command + ["--config", str(config)],
        env={
            **os.environ,
            "OPSCONTROL_AGENT_TOKEN": credential,
            "OPSCONTROL_AGENT_STATE_DIR": str(root),
        },
        stdout=output,
        stderr=subprocess.STDOUT,
    )
    output.close()
    time.sleep(0.7)
    assert process.poll() is None


try:
    token = call(
        "/api/v1/auth/login",
        "POST",
        {"username": "arch001-admin", "password": fixture["password"]},
    )["access_token"]
    vm = call(
        "/api/v1/unified/resources/vm",
        "POST",
        {
            "name": "Checkpoint migration fixture",
            "hostname": socket.gethostname(),
            "address": socket.gethostname(),
            "environment": "SANDBOX",
            "os_type": "Linux",
            "organization_id": fixture["org"],
            "native_os_metrics": False,
        },
        token,
        201,
    )
    prefix = "/api/v1/agent-control/collectors/" + vm["primary_collector_id"]
    for method in call(prefix, token=token)["methods"]:
        call(prefix + "/methods/" + method["id"], "DELETE", token=token, expected=204)
    method = call(
        prefix + "/methods",
        "POST",
        {
            "name": "Checkpoint ID stream",
            "method_type": "FILE_LOG",
            "configuration": {
                "paths": ["/fixture/logs/*.log"],
                "format": "JSON",
                "start_at": "beginning",
            },
        },
        token,
        201,
    )
    version = call(prefix + "/versions", "POST", token=token, expected=201)
    assert (
        version["validation_status"] == "VALIDATED"
        and version["runtime_version"] == "0.123.0"
    )
    config = home / "otel.yaml"
    r.atomic(config, version["yaml_text"].encode())
    enrollment = call(prefix + "/registration", "POST", token=token, expected=201)
    identity = call(
        "/api/v1/agent/register",
        "POST",
        {
            "enrollment_token": enrollment["enrollment_token"],
            "hostname": socket.gethostname(),
            "os_type": "Linux",
            "version": "1.5.0",
            "runtime_version": "0.123.0",
        },
        expected=201,
    )
    credential = identity["access_token"]
    r.atomic(home / "identity.json", json.dumps(identity).encode())
    call(
        prefix + "/apply",
        "POST",
        {"revision": version["revision"], "approve": True},
        token,
    )
    report.update(
        collector_id=vm["primary_collector_id"],
        agent_id=identity["agent_id"],
        method_id=method["id"],
        config_sha256=r.sha(config),
    )
    emit(0, 8)
    start("0.123.0")
    call(
        "/api/v1/agent/heartbeat",
        "POST",
        {
            "version": "1.5.0",
            "runtime_version": "0.123.0",
            "health": "RUNNING",
            "applied_revision": version["revision"],
            "configuration_sha256": version["sha256"],
        },
        credential,
    )
    wait(lambda: set(expected) <= set(counts()), "legacy IDs persisted before backup")
    stop()
    phase("legacy-cut")
    backup = vault / "legacy-cut"
    backup_manifest = r.snapshot(state, backup, config)
    report["legacy_backup"] = backup_manifest
    report["legacy_manifest_sha256"] = r.sha(backup / "manifest.json")
    start("0.163.2", legacy_encoding=True)
    emit(8, 16)
    wait(
        lambda: set(expected) <= set(counts()),
        "populated JSON state upgrades to compatible candidate",
    )
    stop()
    for i in range(2):
        before = counts()
        start("0.163.2", legacy_encoding=True)
        time.sleep(6)
        stop()
        assert counts() == before, "Unexpected replay after compatible restart"
    passed("repeated candidate restarts preserve consumed offsets")
    start("0.163.2", legacy_encoding=True)
    source.rename(logs / "app.1.log")
    emit(16, 24)
    wait(lambda: set(expected) <= set(counts()), "rotated input IDs persisted")
    shutil.copyfile(source, retention / "pretruncate.jsonl")
    os.chmod(retention / "pretruncate.jsonl", 0o600)
    emit(24, 28, truncate=True)
    wait(
        lambda: set(expected) <= set(counts()),
        "copy-truncate with retained archive persists IDs",
    )
    stop()
    phase("compatible-upgrade-rotation-truncation")
    start("0.163.2")  # Default encoding intentionally reproduces the dangerous path.
    emit(28, 44)
    time.sleep(0.4)
    stop(kill=True)
    phase("interrupted-default-upgrade")
    r.copy_tree(state, vault / "crash-forensic")
    start("0.163.2")
    try:
        wait(
            lambda: set(expected) <= set(counts()),
            "interrupted default upgrade restarts and delivers retained IDs",
        )
    except AssertionError as error:
        report["failed_cases"].append(
            {
                "case": "unclean default upgrade delivery",
                "status": "FAIL",
                "error": str(error),
                "missing_ids": sorted(set(expected) - set(counts())),
            }
        )
        print(
            "unclean default upgrade delivery: FAIL (preserved; testing independent archive recovery)",
            flush=True,
        )
    stop()
    phase("default-protobuf-after-restart")
    original_failed = r.tree(state)
    r.copy_tree(state, vault / "protobuf-forensic")
    probe = ROOT / "probe-home"
    probe.mkdir(mode=0o700)
    r.copy_tree(state, probe / "otel-checkpoints")
    with (ROOT / "downgrade-failure.log").open("w") as output:
        failed = subprocess.run(
            ["/runtime/otelcol-contrib-0.123.0", "--config", str(config)],
            env={
                **os.environ,
                "OPSCONTROL_AGENT_TOKEN": credential,
                "OPSCONTROL_AGENT_STATE_DIR": str(probe),
            },
            stdout=output,
            stderr=subprocess.STDOUT,
            timeout=20,
        )
    assert (
        failed.returncode != 0
        and "decoding file count" in (ROOT / "downgrade-failure.log").read_text()
    )
    assert r.tree(state) == original_failed
    report["default_downgrade"] = {
        "result": "FAIL as reproduced",
        "exit_code": failed.returncode,
        "original_state_unchanged": True,
    }
    passed("default protobuf downgrade failure reproduced on disposable clone")
    all_files = list(logs.glob("*.log")) + list(retention.glob("*.jsonl"))
    try:
        r.seal_archive(
            all_files, expected + ["missing-source-event"], vault / "incomplete-archive"
        )
    except ValueError:
        passed("incomplete source archive blocked")
    else:
        raise AssertionError("Incomplete archive accepted")
    archive = vault / "sealed-archive"
    r.seal_archive(all_files, expected, archive)
    start("0.163.2")
    try:
        r.recover(state, backup, archive, config, vault, logs, "active-writer")
    except ValueError as error:
        assert "writer active" in str(error)
        passed("live collector state lock blocks recovery")
    else:
        raise AssertionError("Live state recovery accepted")
    stop()
    failed_before_recovery = r.tree(state)
    try:
        r.recover(
            state, backup, archive, config, vault, logs, "rollback-1", "partial-copy"
        )
    except RuntimeError:
        pass
    else:
        raise AssertionError("Partial staging fault not injected")
    assert r.tree(state) == failed_before_recovery
    try:
        r.assert_startable(vault)
    except ValueError:
        passed("partial recovery refuses service restart")
    else:
        raise AssertionError("Pending recovery start allowed")
    command = [
        sys.executable,
        "/verification/recovery.py",
        "recover",
        "--state",
        str(state),
        "--backup",
        str(backup),
        "--archive",
        str(archive),
        "--config",
        str(config),
        "--vault",
        str(vault),
        "--replay-root",
        str(logs),
        "--transaction",
        "rollback-1",
        "--inject-failure",
        "kill-after-exchange",
    ]
    crashed = subprocess.run(command, capture_output=True, text=True)
    assert crashed.returncode == 86, crashed.stderr
    result = r.recover(state, backup, archive, config, vault, logs, "rollback-1")
    assert r.tree(Path(result["preserved_candidate"])) == failed_before_recovery
    assert r.recover(state, backup, archive, config, vault, logs, "rollback-1")[
        "idempotent_noop"
    ]
    assert r.sha(backup / "manifest.json") == report["legacy_manifest_sha256"]
    report["recovery"] = result
    passed(
        "interrupted atomic exchange resumes idempotently and preserves failed state"
    )
    before_replay = counts()
    start("0.123.0")
    wait(
        lambda: all(counts()[event] >= before_replay[event] + 1 for event in expected),
        "bounded replay of every stable ID acknowledged by actual API",
    )
    stop()
    phase("legacy-recovery-replay")
    for i in range(3):
        before = counts()
        start("0.123.0")
        time.sleep(6)
        stop()
        assert counts() == before, "Unexpected delivery after repeated rollback restart"
    passed("repeated rollback restarts do not replay already-consumed recovery file")
    try:
        r.recover(state, backup, archive, config, vault, logs, "rollback-1")
    except ValueError as error:
        assert "advanced" in str(error)
        passed("completed recovery refuses a second rewind after state advances")
    else:
        raise AssertionError("Advanced state rewound")
    phase("final")
    report["expected_ids"] = expected
    report["recovery_completed"] = True
    report["status"] = "FAIL" if report["failed_cases"] else "PASS"
except Exception as error:
    report["error"] = type(error).__name__ + ": " + str(error)
    raise
finally:
    stop()
    (ROOT / "e2e.json").write_text(json.dumps(report, indent=2) + "\n")

if report["status"] != "PASS":
    raise SystemExit(1)
