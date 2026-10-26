"""Finite-ID SIGKILL probes. Real binaries/API/Postgres; no promotion or recovery edits."""

import collections
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import sqlite3
import subprocess
import sys
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from state_view import inspect
from replay import prepare_replay

sys.path.insert(0, "/work/agent")
try:
    from opscontrol_agent import filelog_runtime_flags
except ImportError:

    def filelog_runtime_flags(config):
        assert (
            not Path(config)
            .read_text()
            .startswith("# opscontrol-filelog-durable-handoff-v1:")
        )
        return []


sys.path.insert(0, "/work/backend/scripts")
from acceptance_scope import probe_headers

assert os.environ["ENVIRONMENT"] == "test" and os.environ["DEV052A3_LAB"] == "1"
ROOT = Path("/fixture")
fixture = json.loads((ROOT / "fixture.json").read_text())
plan = json.loads(Path("/work/overlay-provenance.json").read_text())
api = os.environ["ARCH001_API_URL"]
process = None
report = {
    "status": "FAIL",
    "cases": [],
    "scope": "finite synthetic filelog delivery; SIGKILL, not power failure; no exactly-once guarantee",
}
source = ROOT / "input" / "current.log"
source.parent.mkdir(mode=0o700, exist_ok=True)
next_id = 0
current = None


def atomic(path, value):
    data = (
        json.dumps(value, indent=2).encode() if not isinstance(value, bytes) else value
    )
    temp = path.with_name(path.name + ".tmp")
    with temp.open("wb") as f:
        os.chmod(temp, 0o600)
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)
    fd = os.open(path.parent, os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def mark(stage, **fields):
    entry = {"time_ns": time.time_ns(), "stage": stage, **fields}
    with (ROOT / "controller.log").open("a") as f:
        f.write(json.dumps(entry) + "\n")
        f.flush()
        os.fsync(f.fileno())
    if current is not None:
        current["timeline"].append(entry)


def gate(mode):
    atomic(ROOT / "api-mode.json", {"mode": mode, "generation": time.time_ns()})
    mark("api_gate", mode=mode)


def call(path, method="GET", body=None, token=None, expected=200):
    req = Request(
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
        with urlopen(req, timeout=15) as res:
            status, raw = res.status, res.read()
    except HTTPError as err:
        status, raw = err.code, err.read()
    assert status == expected, (path, status, expected)
    return json.loads(raw) if raw else None


def ledger(stage="api_committed"):
    with sqlite3.connect(
        "file:/fixture/api-ledger.sqlite?mode=ro", uri=True, timeout=15
    ) as db:
        return collections.Counter(
            e
            for (raw,) in db.execute(
                "SELECT event_ids FROM timeline WHERE stage=?", (stage,)
            )
            for e in json.loads(raw)
        )


def wait(predicate, seconds=15):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        if predicate():
            return
        if process is not None:
            assert process.poll() is None, "Collector exited"
        time.sleep(0.03)
    raise AssertionError("Timed out waiting for observed boundary")


def stop(kill=False):
    global process
    if process is not None and process.poll() is None:
        mark("SIGKILL" if kill else "SIGTERM", pid=process.pid)
        os.killpg(process.pid, signal.SIGKILL if kill else signal.SIGTERM)
        process.wait(timeout=15)
    process = None


def collector_pid():
    if current and current.get("traced"):
        children = []
        for item in Path("/proc").iterdir():
            if not item.name.isdigit():
                continue
            try:
                status = (item / "status").read_text()
                parent = int(
                    next(
                        line.split()[1]
                        for line in status.splitlines()
                        if line.startswith("PPid:")
                    )
                )
                if parent == process.pid:
                    children.append(item.name)
            except (FileNotFoundError, ProcessLookupError):
                pass
        assert len(children) == 1, "Expected one owned traced collector child"
        return int(children[0])
    return process.pid


def start(root, config, version, trace_target=None, injection="delay_enter=300ms"):
    global process
    binary = (
        "/runtime/otelcol-contrib-0.123.0"
        if version == "0.123.0"
        else "/runtime/otelcol-contrib"
    )
    command = [binary, "--config", str(config)] + filelog_runtime_flags(config)
    current["traced"] = bool(trace_target)
    if trace_target:
        command = [
            "/fixture/tools/ld-linux-x86-64.so.2",
            "--library-path",
            "/fixture/tools",
            "/fixture/tools/strace",
            "-f",
            "-ttt",
            "-yy",
            "-o",
            str(root / "syscalls.log"),
            "-e",
            "trace=pwrite64,fsync,fdatasync",
            "-e",
            "raw=pwrite64",
            "-P",
            str(trace_target),
            "-e",
            "inject=pwrite64:" + injection,
        ] + command
        mark(
            "syscall_fault",
            target=str(trace_target),
            injection=injection,
            syscall="pwrite64",
        )
    with (ROOT / "runtime.log").open("ab") as log:
        process = subprocess.Popen(
            command,
            env={
                **os.environ,
                "OPSCONTROL_AGENT_TOKEN": credential,
                "OPSCONTROL_AGENT_STATE_DIR": str(root),
            },
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    mark("collector_start", version=version, pid=process.pid)
    time.sleep(0.45)
    assert process.poll() is None, "Collector startup failed"


def emit(count=4):
    global next_id
    ids = [f"event-{i:04d}" for i in range(next_id, next_id + count)]
    next_id += count
    current["expected_ids"].extend(ids)
    atomic(
        ROOT / "expected.json", {c["name"]: c["expected_ids"] for c in report["cases"]}
    )
    payload = b"".join(
        (
            json.dumps(
                {
                    "event_id": e,
                    "message": "owned synthetic durability probe",
                    "padding": e * 120,
                }
            )
            + "\n"
        ).encode()
        for e in ids
    )
    with source.open("ab") as f:
        os.chmod(source, 0o600)
        f.write(payload)
        f.flush()
        os.fsync(f.fileno())
    mark(
        "source_fsynced",
        ids=ids,
        bytes=source.stat().st_size,
        sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    )
    return ids


def snapshot(root, label, keep_stopped=False, retain=True):
    pid = collector_pid()
    os.kill(pid, signal.SIGSTOP)
    # Verify kernel stop before inspecting committed bbolt pages.
    wait(
        lambda: any(
            "\nState:\t" + v in Path(f"/proc/{pid}/status").read_text()
            for v in ["T", "t"]
        ),
        2,
    )
    state = inspect(root / "otel-checkpoints")
    metrics = ""
    try:
        # Collector is paused: metrics must be fetched before/after separately.
        pass
    finally:
        if not keep_stopped:
            os.kill(pid, signal.SIGCONT)
    data = {
        "time_ns": time.time_ns(),
        "label": label,
        "source_bytes": source.stat().st_size if source.exists() else None,
        "state": state,
    }
    if retain:
        current["snapshots"].append(data)
    mark("snapshot", label=label)
    return data


def metrics(label):
    try:
        with urlopen("http://127.0.0.1:8888/metrics", timeout=2) as res:
            text = res.read().decode()
        (ROOT / (current["name"] + "-" + label + "-metrics.log")).write_text(text)
    except OSError as e:
        mark("metrics_unavailable", label=label, error=type(e).__name__)


def queued_ids(snap):
    return {
        e
        for name, f in snap["state"].items()
        if name.startswith("exporter_")
        for row in f["entries"]
        for e in row["event_ids"]
    }


def offsets(snap):
    values = []

    def walk(value):
        if isinstance(value, dict):
            for k, v in value.items():
                if k.lower() == "offset" and isinstance(v, int):
                    values.append(v)
                else:
                    walk(v)
        elif isinstance(value, list):
            for v in value:
                walk(v)

    for name, f in snap["state"].items():
        if name.startswith("receiver_filelog"):
            walk(f)
    return values


try:
    assert os.getuid() != 0
    token = call(
        "/api/v1/auth/login",
        "POST",
        {"username": "arch001-admin", "password": fixture["password"]},
    )["access_token"]
    vm = call(
        "/api/v1/unified/resources/vm",
        "POST",
        {
            "name": "CHK001 durability fixture",
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
    for m in call(prefix, token=token)["methods"]:
        call(prefix + "/methods/" + m["id"], "DELETE", token=token, expected=204)
    method = call(
        prefix + "/methods",
        "POST",
        {
            "name": "Durability ID stream",
            "method_type": "FILE_LOG",
            "configuration": {
                "paths": ["/fixture/input/*.log"],
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
    generated = version["yaml_text"]
    atomic(ROOT / "generated.yaml", generated.encode())
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
    atomic(ROOT / "identity.json", identity)
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
        generated_sha256=hashlib.sha256(generated.encode()).hexdigest(),
    )
    import shutil
    from replay import LEGACY_SHA, digest

    def receipt_cut(root, label):
        assert process is None, "Stop writer before independent DB cut"
        time.sleep(0.25)
        atomic(ROOT / "receipt-request.json", {
            "case": current["name"], "label": label,
            "collector_id": report["collector_id"],
            "expected_ids": current["expected_ids"], "writer_stopped": True,
        })
        call("/health")
        path = root / label
        assert path.exists()
        data = json.loads(path.read_text())
        counts = data["counts_by_id"]
        expected = set(current["expected_ids"])
        got = ledger()
        phase = {
            "label": label, "time_ns": data["cut_ns"],
            "expected_distinct": len(expected),
            "persisted_distinct": len(expected & set(counts)),
            "missing_ids": sorted(expected - set(counts)),
            "api_accepted_attempts": sum(got[e] for e in expected),
            "physical_rows": sum(counts.values()),
            "physical_duplicate_rows": sum(counts.values()) - len(counts),
        }
        current.setdefault("phases", []).append(phase)
        return path, phase

    def seal(root):
        atomic(root / "archive.jsonl", source.read_bytes())
        atomic(root / "inventory.json", {
            "scope": report["collector_id"],
            "expected_ids": current["expected_ids"],
            "sealed_at_ns": time.time_ns(),
            "expires_at_ns": time.time_ns() + 600 * 10**9,
        })

    def replay(root, receipt, fault=None):
        paths = [root / "archive.jsonl", root / "inventory.json", receipt]
        seals = dict(zip(["archive", "inventory", "receipts"],
                         [digest(p.read_bytes()) for p in paths]))
        result = prepare_replay(*paths, seals, source.parent,
                                scope=report["collector_id"], binary_sha=LEGACY_SHA,
                                fault=fault)
        atomic(root / "replay-plan.json", {"seals": seals, **result})
        mark("bounded_replay_published", **result)
        return result

    def checkpoint_eof(root, seconds=2):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            cut = snapshot(root, "staggered-checkpoint", retain=False)
            if max(offsets(cut) or [0]) == source.stat().st_size:
                return True
            time.sleep(0.03)
        return False

    def fill(root, config):
        gate("hold_before_commit")
        start(root, config, "0.123.0")
        for _ in range(267):
            emit(1)
            if not checkpoint_eof(root):
                break
        snap = snapshot(root, "full-queue-before-restart")
        assert len(current["expected_ids"]) == 267, "Default-size staggered saturation not reproduced"
        assert len(queued_ids(snap)) == 266
        assert max(offsets(snap) or [0]) < source.stat().st_size
        assert set(current["expected_ids"][:10]) <= queued_ids(snap)
        seal(root)
        stop(kill=True)

    def drain(root, config, runtime, seconds=6):
        gate("pass")
        start(root, config, runtime)
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if set(current["expected_ids"]) <= set(ledger()):
                break
            assert process.poll() is None
            time.sleep(0.1)
        snapshot(root, "after-drain")
        stop()

    cases = plan.get("queue_cases", ["legacy_full_replay", "replacement_full"])
    for scenario in cases:
        current = {"name": scenario, "scenario": scenario, "runtime": "0.123.0",
                   "status": "FAIL", "expected_ids": [], "timeline": [], "snapshots": []}
        report["cases"].append(current)
        root = ROOT / scenario
        root.mkdir(mode=0o700)
        (root / "otel-checkpoints").mkdir(mode=0o700)
        for old in source.parent.iterdir():
            old.unlink()
        source.touch(mode=0o600)
        # Fixture timing only: queue remains 256 requests, ten default consumers.
        text = generated.replace("    start_at: beginning", "    poll_interval: 20ms\n    start_at: beginning")
        assert text.count("queue_size: 256") == 1 and "num_consumers:" not in text
        current["test_overlay"] = "filelog poll_interval=20ms; include owned replay glob; queue256/default10consumers unchanged"
        config = root / "otel.yaml"
        atomic(config, text.encode())
        current["config_sha256"] = digest(text.encode())
        try:
            if scenario.startswith(("legacy", "replacement", "boundary", "repeated", "enospc", "corrupt", "retention_expiry")):
                fill(root, config)
                runtime = "0.163.2" if scenario.startswith("replacement") or "replacement" in scenario else "0.123.0"
                current["runtime"] = runtime
                target = next((root / "otel-checkpoints").glob("exporter_*"))
                if scenario.startswith("boundary"):
                    # Delay each actual queue pwrite, then inspect committed pages.
                    start(root, config, runtime, trace_target=target)
                    original = set(current["expected_ids"][:10])
                    deadline = time.monotonic() + 45
                    while True:
                        snap = snapshot(root, "transaction-poll", retain=False)
                        retained = original & queued_ids(snap)
                        trace = (root / "syscalls.log").read_text()
                        if "after_reenqueue" in scenario:
                            moved = {e for name, data in snap["state"].items()
                                     if name.startswith("exporter_")
                                     for row in data["entries"]
                                     if row["key"][-1].isdigit() and int(row["key"][-1]) >= 266
                                     for e in row["event_ids"]}
                            reached = original <= moved
                        elif "before_delete" in scenario:
                            reached = retained == original and "pwrite64(" in trace
                        elif "after_delete" in scenario:
                            reached = not retained
                        else:
                            reached = 0 < len(retained) < 10
                        if reached:
                            held = snapshot(root, "held-transaction-kill", keep_stopped=True)
                            assert retained == original & queued_ids(held)
                            current["boundary_retained_inflight_ids"] = sorted(retained)
                            current["boundary_observed"] = True
                            stop(kill=True)
                            atomic(root / "queue-at-kill.bin", target.read_bytes())
                            break
                        assert time.monotonic() < deadline, "Transaction boundary not observed"
                        time.sleep(0.03)
                elif scenario == "repeated_crashes":
                    for _ in range(3):
                        start(root, config, runtime)
                        time.sleep(0.4)
                        snapshot(root, "repeated-full-restart")
                        stop(kill=True)
                elif scenario == "enospc":
                    current["fault"] = "queue-only pwrite64 ENOSPC when=1, not host disk fill"
                    try:
                        start(root, config, runtime, trace_target=target,
                              injection="error=ENOSPC:when=1")
                        time.sleep(1)
                    except AssertionError as err:
                        current["injected_startup_error"] = str(err)
                    stop(kill=True)
                elif scenario == "corrupt":
                    original = target.read_bytes()
                    atomic(root / "queue-before-corruption.bin", original)
                    data = bytearray(original)
                    size = int.from_bytes(data[24:28], "little")
                    for index in [16, size + 16]:
                        data[index:index+4] = b"BAD!"
                    atomic(target, bytes(data))
                    current["corruption"] = {"backup_sha256": digest(original), "corrupt_sha256": digest(data)}
                    try:
                        start(root, config, runtime)
                        time.sleep(1)
                        current["corrupt_process_exit"] = process.poll()
                    except AssertionError as err:
                        current["corrupt_startup_error"] = str(err)
                    stop(kill=True)
                    gate("pass")
                    _, native = receipt_cut(root, "native-pg.json")
                    current["native_status"] = "FAIL"
                    current["recovery_status"] = "BLOCKED: queue corruption; no checkpoint/queue repair permitted"
                    continue
                drain(root, config, runtime)
            else:
                gate("permanent_rejection" if scenario == "permanent_rejection" else "unavailable")
                start(root, config, "0.123.0")
                emit(4)
                assert checkpoint_eof(root)
                seal(root)
                if scenario == "api_outage":
                    (ROOT / "request-api-outage").touch()
                    wait(lambda: (ROOT / "api-restored").exists(), 20)
                time.sleep(1)
                stop(kill=True)
                if scenario == "permanent_rejection":
                    # Keep the permanent rejection across restart and attempted replay.
                    start(root, config, "0.123.0")
                    time.sleep(1)
                    stop(kill=True)
                else:
                    drain(root, config, "0.123.0")
            receipt, native = receipt_cut(root, "native-pg.json")
            current["native_status"] = "FAIL" if native["missing_ids"] else "PASS"
            current["status"] = current["native_status"]
            if scenario in {"legacy_full_replay", "repeated_crashes", "enospc", "permanent_rejection", "retention_expiry"}:
                if scenario == "retention_expiry":
                    # If normal retry delivered everything this is only a refusal test.
                    inventory = json.loads((root / "inventory.json").read_text())
                    inventory["expires_at_ns"] = time.time_ns() - 1
                    atomic(root / "inventory.json", inventory)
                    try:
                        replay(root, receipt)
                    except ValueError as err:
                        current["recovery_status"] = "BLOCKED: " + str(err)
                    else:
                        raise AssertionError("Expired retention accepted")
                else:
                    replay(root, receipt)
                    if scenario != "permanent_rejection":
                        drain(root, config, "0.123.0", 15)
                    else:
                        start(root, config, "0.123.0")
                        time.sleep(2)
                        stop(kill=True)
                    _, recovered = receipt_cut(root, "recovered-pg.json")
                    current["recovery_status"] = "FAIL" if recovered["missing_ids"] else "PASS"
                    # Preserve native FAIL even if bounded recovery succeeds.
                    for _ in range(2):
                        if scenario != "permanent_rejection":
                            drain(root, config, "0.123.0", 2)
                    receipt_cut(root, "final-pg.json")
        except Exception as err:
            current["error"] = type(err).__name__ + ": " + str(err)
            current["status"] = "FAIL"
            stop(kill=True)
            gate("pass")
            try:
                receipt_cut(root, "failure-pg.json")
            except Exception as observe:
                current["observation_error"] = str(observe)
        finally:
            stop(kill=True)
            gate("pass")
            atomic(root / "source.jsonl", source.read_bytes())
            for replay_file in source.parent.glob("replay-*.log"):
                atomic(root / replay_file.name, replay_file.read_bytes())
            atomic(ROOT / "e2e.json", report)
            print(scenario + ": " + current["status"] + " " + current.get("error", ""), flush=True)
    report["status"] = "FAIL" if any(c["status"] != "PASS" for c in report["cases"]) else "PASS"
except Exception as err:
    report["error"] = type(err).__name__ + ": " + str(err)
    raise
finally:
    stop(kill=True)
    atomic(ROOT / "e2e.json", report)
if report["status"] != "PASS":
    raise SystemExit(1)
