"""Owned API SIGKILL/restart contract; private state is never an evidence artifact."""

import json
import os
import signal
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4
from sqlalchemy import select, text
from app.db.session import SessionLocal
from app.models import DataSource, MonitoringTemplateAttachment
from app.models.entities import SourceConfigurationRevision
from tests.test_source_configuration_contract import SourceConfigurationContract

phase, filename = sys.argv[1:3]
private = Path(filename)
f = SourceConfigurationContract("test_attach_reload_history_rollback_and_detach")
if phase == "interrupt":
    f.setUp()
    state = {
        key: getattr(f, key) for key in ("org", "sid", "tid", "admin", "member", "base")
    }
    state["key"] = str(uuid4())
    private.write_text(json.dumps(state))
    private.chmod(0o600)
else:
    state = json.loads(private.read_text())
    for key in ("org", "sid", "tid", "admin", "member", "base"):
        setattr(f, key, state[key])

payload = dict(expected_revision=0, attachments=[f.member])


def admitted():
    return f.call("POST", f.base + "/commands", payload, key=state["key"])


if phase == "interrupt":
    pid = int(sys.argv[3])
    # Validate against the task-owned API command before signalling any process.
    command = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
    assert b"uvicorn" in command and b"app.main:app" in command
    with SessionLocal() as owner:
        owner.execute(
            text(
                "CREATE FUNCTION s01_pause_revision() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.data_source_id::text='"
                + f.sid
                + "' THEN PERFORM pg_advisory_xact_lock(782104,118); END IF; RETURN NEW; END $$"
            )
        )
        owner.execute(
            text(
                "CREATE TRIGGER s01_pause_revision BEFORE INSERT ON source_configuration_revisions FOR EACH ROW EXECUTE FUNCTION s01_pause_revision()"
            )
        )
        owner.commit()
        owner.execute(text("SELECT pg_advisory_xact_lock(782104,118)"))
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(admitted)
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    owner.execute(text("SELECT pg_stat_clear_snapshot()"))
                    waiting = owner.scalar(
                        text(
                            "SELECT EXISTS(SELECT 1 FROM pg_locks WHERE locktype='advisory' AND classid=782104 AND objid=118 AND NOT granted)"
                        )
                    )
                    if waiting:
                        break
                    time.sleep(0.05)
                assert waiting, "API did not reach the instrumented pre-ledger boundary"
                os.kill(pid, signal.SIGKILL)
                owner.rollback()
                try:
                    result = future.result(timeout=15)
                    assert result[0] >= 500, result[0]
                except (ConnectionError, OSError) as exc:
                    result = type(exc).__name__
        finally:
            owner.rollback()
            owner.execute(
                text(
                    "DROP TRIGGER s01_pause_revision ON source_configuration_revisions"
                )
            )
            owner.execute(text("DROP FUNCTION s01_pause_revision()"))
            owner.commit()
    with SessionLocal() as db:
        assert db.get(DataSource, f.sid).configuration_revision == 0
        assert not list(
            db.scalars(
                select(SourceConfigurationRevision).where(
                    SourceConfigurationRevision.data_source_id == f.sid
                )
            )
        )
        assert not list(
            db.scalars(
                select(MonitoringTemplateAttachment).where(
                    MonitoringTemplateAttachment.data_source_id == f.sid
                )
            )
        )
    print(
        json.dumps(
            {
                "case": "SIGKILL_API_BEFORE_LEDGER_PERSISTENCE",
                "status": "PASS",
                "head": 0,
                "history_rows": 0,
                "projection_rows": 0,
                "source_id": f.sid,
                "at": time.time(),
            }
        )
    )
elif phase in ("recover", "replay"):
    code, value = admitted()
    assert code == 201, (code, value)
    assert value["revision"] == 1
    assert value["replayed"] == (phase == "replay")
    with SessionLocal() as db:
        head = db.get(DataSource, f.sid).configuration_revision
        history = list(
            db.scalars(
                select(SourceConfigurationRevision).where(
                    SourceConfigurationRevision.data_source_id == f.sid
                )
            )
        )
        projection = list(
            db.scalars(
                select(MonitoringTemplateAttachment).where(
                    MonitoringTemplateAttachment.data_source_id == f.sid
                )
            )
        )
        assert head == 1 and len(history) == len(projection) == 1
    print(
        json.dumps(
            {
                "case": phase,
                "status": "PASS",
                "head": head,
                "history_rows": len(history),
                "projection_rows": len(projection),
                "replayed": value["replayed"],
                "source_id": f.sid,
                "at": time.time(),
            }
        )
    )
else:
    raise ValueError("Unknown owned test phase")
