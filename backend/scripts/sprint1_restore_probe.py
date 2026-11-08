"""Hash-compare a complete synthetic database restore inside the owned container."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
from sqlalchemy import create_engine, inspect, text
from app.db.session import engine

assert os.environ.get("OPSCONTROL_V16_ACCEPTANCE") == "1"
container = os.environ["V16_OWNED_CONTAINER"]
assert container.startswith("opscontrol-v16-")
out = Path(os.environ["V16_EVIDENCE_DIR"])


def snapshot(connection_engine):
    result = {}
    with connection_engine.connect() as db:
        inspector = inspect(db)
        for table in inspector.get_table_names():
            quoted = db.dialect.identifier_preparer.quote(table)
            rows = list(
                db.scalars(
                    text(
                        f"SELECT to_jsonb(t)::text FROM {quoted} t ORDER BY to_jsonb(t)::text"
                    )
                )
            )
            result[table] = {
                "count": len(rows),
                "sha256": hashlib.sha256(json.dumps(rows).encode()).hexdigest(),
                "columns": [
                    (c["name"], str(c["type"]), c["nullable"])
                    for c in inspector.get_columns(table)
                ],
                "foreign_keys": inspector.get_foreign_keys(table),
            }
    return result


before = snapshot(engine)
archive = subprocess.check_output(
    [
        "docker",
        "exec",
        container,
        "pg_dump",
        "-U",
        "opscontrol",
        "-d",
        "opscontrol",
        "-Fc",
    ]
)
(out / "synthetic-backup.dump").write_bytes(archive)
subprocess.run(
    ["docker", "exec", container, "createdb", "-U", "opscontrol", "sprint_restore"],
    check=True,
)
subprocess.run(
    [
        "docker",
        "exec",
        "-i",
        container,
        "pg_restore",
        "-U",
        "opscontrol",
        "-d",
        "sprint_restore",
        "--no-owner",
        "--no-privileges",
    ],
    input=archive,
    check=True,
)
restored_engine = create_engine(engine.url.set(database="sprint_restore"))
try:
    restored = snapshot(restored_engine)
    assert before == restored and before == snapshot(engine)
finally:
    restored_engine.dispose()
    subprocess.run(
        ["docker", "exec", container, "dropdb", "-U", "opscontrol", "sprint_restore"],
        check=True,
    )
(out / "restore.json").write_text(
    json.dumps(
        {
            "status": "PASS",
            "tables_compared": len(before),
            "backup_sha256": hashlib.sha256(archive).hexdigest(),
            "snapshots": before,
            "source_unchanged": True,
            "temporary_archive_disposition": "Removed after verified restoration; hash retained; contains synthetic auth records",
            "restored_schema_data_fk_equal": True,
        },
        indent=2,
    )
)
(out / "synthetic-backup.dump").unlink()
print("Synthetic full backup/restore PASS:", len(before), "tables; temporary archive removed after verified restore")
