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
source = ROOT / "current.log"
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


def start(root, config, version, trace_target=None):
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
            "inject=pwrite64:delay_enter=2s",
        ] + command
        mark(
            "syscall_fault",
            target=str(trace_target),
            delay_enter="2s",
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
                "paths": ["/fixture/current.log"],
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
    cases = (
        ["batch_checkpoint_gap"]
        if plan.get("durability_suite") == "baseline"
        else [
            "before_read",
            "after_checkpoint_before_commit",
            "after_commit_before_ack",
            "after_ack",
            "unavailable_api",
            "queue_saturation",
            "repeated_crashes",
            "retained_source_before_read",
            "expired_source_before_read",
            "permanent_rejection",
        ]
    )
    cases = plan.get("durability_cases", cases)
    versions = plan.get("durability_versions", ["0.163.2"])
    for runtime in versions:
        for scenario in cases:
            current = {
                "name": runtime + "-" + scenario,
                "scenario": scenario,
                "runtime": runtime,
                "status": "FAIL",
                "expected_ids": [],
                "timeline": [],
                "snapshots": [],
            }
            report["cases"].append(current)
            root = ROOT / current["name"]
            root.mkdir(mode=0o700)
            (root / "otel-checkpoints").mkdir(mode=0o700)
            source.unlink(missing_ok=True)
            source.touch(mode=0o600)
            text = generated
            if scenario == "queue_saturation":
                assert text.count("queue_size: 256") == 1
                text = text.replace(
                    "queue_size: 256", "queue_size: 2\n      num_consumers: 1"
                )
                current["test_overlay"] = (
                    "queue_size=2,num_consumers=1; production size remains256"
                )
            config = root / "otel.yaml"
            atomic(config, text.encode())
            current["config_sha256"] = hashlib.sha256(text.encode()).hexdigest()
            try:
                gate("pass")
                start(root, config, runtime)
                if scenario in {"before_enqueue", "after_enqueue_before_checkpoint"}:
                    # Warm empty stores, then delay only writes to the selected
                    # bbolt file. All other security/resource constraints persist.
                    stop()
                    pattern = (
                        "exporter_*"
                        if scenario == "before_enqueue"
                        else "receiver_filelog*"
                    )
                    target = next((root / "otel-checkpoints").glob(pattern))
                    gate("hold_before_commit")
                    start(root, config, runtime, trace_target=target)
                    emit()
                    deadline = time.monotonic() + 35
                    while True:
                        snap = snapshot(root, "delayed-write-boundary", retain=False)
                        ids = set(current["expected_ids"])
                        pending = queued_ids(snap)
                        trace = (root / "syscalls.log").read_text()
                        if scenario == "after_enqueue_before_checkpoint":
                            reached = (
                                ids <= pending
                                and max(offsets(snap) or [0]) < source.stat().st_size
                            )
                        else:
                            # Source descriptor at EOF proves the file was read;
                            # intercepted queue write and absent queue/receipt IDs
                            # bound the handoff before its durable commit.
                            pid = collector_pid()
                            fd_eof = False
                            for fd in Path(f"/proc/{pid}/fd").iterdir():
                                try:
                                    if os.readlink(fd) == str(source):
                                        info = Path(
                                            f"/proc/{pid}/fdinfo/{fd.name}"
                                        ).read_text()
                                        pos = int(
                                            next(
                                                line.split()[1]
                                                for line in info.splitlines()
                                                if line.startswith("pos:")
                                            )
                                        )
                                        fd_eof = pos >= source.stat().st_size
                                except FileNotFoundError:
                                    pass
                            reached = (
                                fd_eof
                                and not pending
                                and "pwrite64(" in trace
                                and not ids & set(ledger("received"))
                            )
                        if reached:
                            break
                        assert (
                            time.monotonic() < deadline
                        ), "Exact syscall boundary not observed"
                        time.sleep(0.1)
                    held = snapshot(root, "held-exact-kill-boundary", keep_stopped=True)
                    if scenario == "after_enqueue_before_checkpoint":
                        assert (
                            ids <= queued_ids(held)
                            and max(offsets(held) or [0]) < source.stat().st_size
                        )
                    else:
                        assert not queued_ids(held) and not ids & set(
                            ledger("received")
                        )
                    current["boundary_observed"] = scenario
                    stop(kill=True)
                    gate("pass")
                    start(root, config, runtime)
                elif scenario in {
                    "before_read",
                    "retained_source_before_read",
                    "expired_source_before_read",
                }:
                    os.kill(process.pid, signal.SIGSTOP)
                    wait(
                        lambda: "\nState:\tT"
                        in Path(f"/proc/{process.pid}/status").read_text(),
                        2,
                    )
                    emit()
                    stop(kill=True)
                    if scenario == "expired_source_before_read":
                        mark(
                            "source_retention_expired",
                            source_sha256=hashlib.sha256(
                                source.read_bytes()
                            ).hexdigest(),
                        )
                        source.unlink()
                    start(root, config, runtime)
                elif scenario == "batch_checkpoint_gap":
                    emit(16)
                    deadline = time.monotonic() + 2
                    while True:
                        snap = snapshot(root, "batch-window")
                        if max(offsets(snap) or [0]) == source.stat().st_size:
                            break
                        assert (
                            time.monotonic() < deadline
                        ), "Checkpoint window not reached"
                        time.sleep(0.03)
                    assert not queued_ids(snap) and not set(
                        current["expected_ids"]
                    ) & set(ledger("received"))
                    current["confirmed_window"] = (
                        "checkpoint EOF; queue has no IDs; API received none; before 5s batch flush"
                    )
                    metrics("before-kill")
                    stop(kill=True)
                    start(root, config, runtime)
                elif scenario == "after_ack":
                    emit()
                    wait(lambda: set(current["expected_ids"]) <= set(ledger()))
                    time.sleep(0.25)
                    snap = snapshot(root, "after-ack-queue-deletion")
                    assert not queued_ids(snap)
                    metrics("after-ack")
                    stop(kill=True)
                    start(root, config, runtime)
                elif scenario == "unavailable_api":
                    second_outage = (ROOT / "api-restored").exists()
                    if second_outage:
                        gate("unavailable")
                    else:
                        (ROOT / "request-api-outage").touch()
                        wait(lambda: (ROOT / "api-down").exists(), 10)
                    emit()
                    time.sleep(0.8)
                    snapshot(root, "api-tcp-unavailable")
                    stop(kill=True)
                    if second_outage:
                        time.sleep(5)
                        gate("pass")
                    else:
                        wait(lambda: (ROOT / "api-restored").exists(), 15)
                    current["outage_mode"] = (
                        "HTTP503"
                        if second_outage
                        else "API process stopped/TCP unavailable"
                    )
                    start(root, config, runtime)
                elif scenario == "permanent_rejection":
                    gate("permanent_rejection")
                    emit()
                    wait(
                        lambda: set(current["expected_ids"])
                        <= set(ledger("injected_rejection"))
                    )
                    time.sleep(0.3)
                    snapshot(root, "permanent-rejection")
                    stop(kill=True)
                    gate("pass")
                    start(root, config, runtime)
                else:
                    mode = (
                        "hold_after_commit"
                        if scenario == "after_commit_before_ack"
                        else "hold_before_commit"
                    )
                    gate(mode)
                    emit(
                        1
                        if scenario
                        in {
                            "queue_saturation",
                            "production_queue_saturation",
                            "staggered_production_saturation",
                        }
                        else 4
                    )
                    wait(
                        lambda: set(current["expected_ids"])
                        <= set(
                            ledger(
                                "held_after_commit"
                                if mode == "hold_after_commit"
                                else "held_before_commit"
                            )
                        )
                    )
                    time.sleep(0.3)
                    snap = snapshot(root, "queue-and-checkpoint-before-kill")
                    assert set(current["expected_ids"]) <= queued_ids(
                        snap
                    ), "Durable queue lacks in-flight IDs"
                    assert (
                        max(offsets(snap) or [0]) == source.stat().st_size
                    ), "Checkpoint not at EOF"
                    metrics("before-kill")
                    if scenario in {
                        "queue_saturation",
                        "production_queue_saturation",
                        "staggered_production_saturation",
                    }:
                        if scenario == "staggered_production_saturation":
                            # Each previous ID has a persisted EOF checkpoint before
                            # the next write: archive rereading cannot mask a queue
                            # recovery deletion of an already-checkpointed ID.
                            progressed = []
                            for _ in range(270):
                                new = emit(1)
                                deadline = time.monotonic() + 2
                                while True:
                                    cut = snapshot(
                                        root, "staggered-checkpoint", retain=False
                                    )
                                    if (
                                        max(offsets(cut) or [0])
                                        == source.stat().st_size
                                    ):
                                        progressed.extend(new)
                                        break
                                    if time.monotonic() > deadline:
                                        break
                                    time.sleep(0.1)
                                if time.monotonic() > deadline:
                                    break
                            current["checkpointed_before_next_write_ids"] = progressed
                        elif scenario == "production_queue_saturation":
                            emit(270)
                            time.sleep(2)
                        else:
                            for _ in range(9):
                                emit(1)
                                time.sleep(0.25)
                        time.sleep(0.5)
                        snap = snapshot(root, "queue-saturation")
                        current["backpressure_observed"] = (
                            max(offsets(snap) or [0]) < source.stat().st_size
                        )
                        if not current["backpressure_observed"]:
                            current["unsafe_checkpoint_advance"] = True
                    if scenario == "repeated_crashes":
                        for _ in range(3):
                            stop(kill=True)
                            gate("hold_before_commit")
                            start(root, config, runtime)
                            time.sleep(0.3)
                            assert set(current["expected_ids"]) <= queued_ids(
                                snapshot(root, "repeated-crash")
                            )
                    stop(kill=True)
                    gate("pass")
                    start(root, config, runtime)
                known_loss = scenario in {
                    "batch_checkpoint_gap",
                    "expired_source_before_read",
                    "permanent_rejection",
                }
                try:
                    wait(
                        lambda: set(current["expected_ids"]) <= set(ledger()),
                        8 if known_loss else 25,
                    )
                except AssertionError:
                    if not known_loss:
                        raise
                metrics("final")
                snapshot(root, "final")
                stop()
                got = ledger()
                current["accepted_attempt_counts"] = {
                    e: got[e] for e in current["expected_ids"]
                }
                current["missing_ids"] = sorted(set(current["expected_ids"]) - set(got))
                current["status"] = (
                    "FAIL"
                    if current["missing_ids"]
                    or current.get("unsafe_checkpoint_advance")
                    else "PASS"
                )
                current["detected_loss"] = bool(current["missing_ids"])
                if known_loss and not current["missing_ids"]:
                    current["error"] = "Expected negative failure did not reproduce"
                    current["status"] = "FAIL"
            except Exception as err:
                if process is not None and process.poll() is None:
                    try:
                        snapshot(root, "failure-cut")
                        metrics("failure-cut")
                    except Exception as observe:
                        current["observation_error"] = str(observe)
                current["error"] = type(err).__name__ + ": " + str(err)
                current["missing_ids"] = sorted(
                    set(current["expected_ids"]) - set(ledger())
                )
            finally:
                stop(kill=True)
                gate("pass")
                if source.exists():
                    atomic(root / "source.jsonl", source.read_bytes())
                atomic(ROOT / "e2e.json", report)
                print(
                    current["name"]
                    + ": "
                    + current["status"]
                    + " "
                    + current.get("error", ""),
                    flush=True,
                )
    report["status"] = (
        "FAIL" if any(c["status"] != "PASS" for c in report["cases"]) else "PASS"
    )
except Exception as err:
    report["error"] = type(err).__name__ + ": " + str(err)
    raise
finally:
    stop(kill=True)
    atomic(ROOT / "e2e.json", report)
if report["status"] != "PASS":
    raise SystemExit(1)
