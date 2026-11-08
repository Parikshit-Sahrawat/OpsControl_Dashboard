"""Synthetic owned-container backup/restore proof, never a host/UAT target."""

import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile


def normalize_schema(schema):
    """Normalize only pg_dump restrict keys and a PostgreSQL enum-array cast rewrite.

    Both cast forms convert each varchar enum literal to text. Keep all values,
    order, operators, object definitions and security constraints. No DDL omitted.
    """
    enum_array = re.compile(
        r"\(ARRAY\[((?:'[A-Z0-9_]+'::character varying)(?:, '[A-Z0-9_]+'::character varying)*)\]\)::text\[\]"
    )
    return "\n".join(
        enum_array.sub(
            lambda match: "ARRAY["
            + ", ".join("(" + value + ")::text" for value in match[1].split(", "))
            + "]",
            line,
        )
        for line in schema.splitlines()
        if not line.startswith(("\\restrict ", "\\unrestrict "))
    )


def verify(container, output):
    if not re.fullmatch(r"opscontrol-v16-[a-f0-9]{12}", container):
        raise ValueError(
            "Only an allocated disposable V1.6 PostgreSQL container is allowed"
        )

    def execute(*args, data=None):
        return subprocess.run(
            ["docker", "exec", *(["-i"] if data is not None else []), container, *args],
            input=data,
            capture_output=True,
            check=True,
            timeout=120,
        ).stdout

    def sql(database, query):
        return execute(
            "psql",
            "-X",
            "-qAt",
            "-v",
            "ON_ERROR_STOP=1",
            "-U",
            "opscontrol",
            "-d",
            database,
            "-c",
            query,
        ).decode()

    def snapshot(database):
        tables = sql(
            database,
            "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename",
        ).splitlines()
        result = {}
        for table in tables:
            quoted = '"' + table.replace('"', '""') + '"'
            rows = sql(
                database,
                "SELECT row_to_json(t)::text FROM public."
                + quoted
                + " t ORDER BY row_to_json(t)::text",
            )
            result[table] = {
                "rows": len(rows.splitlines()),
                "sha256": hashlib.sha256(rows.encode()).hexdigest(),
            }
        schema = execute(
            "pg_dump",
            "-U",
            "opscontrol",
            "--schema-only",
            "--no-owner",
            "--no-privileges",
            database,
        ).decode()
        canonical = normalize_schema(schema)
        return {
            "tables": result,
            "schema_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
        }

    version = sql("opscontrol", "SHOW server_version").strip()
    before = snapshot("opscontrol")
    with tempfile.TemporaryDirectory(prefix="oc-ci-backup-") as directory:
        Path(directory).chmod(0o700)
        dump = execute("pg_dump", "-U", "opscontrol", "-Fc", "opscontrol")
        path = Path(directory) / "synthetic.dump"
        path.write_bytes(dump)
        path.chmod(0o600)
        execute("createdb", "-U", "opscontrol", "ci_restore")
        try:
            execute(
                "pg_restore",
                "--exit-on-error",
                "-U",
                "opscontrol",
                "-d",
                "ci_restore",
                data=path.read_bytes(),
            )
            restored = snapshot("ci_restore")
            after = snapshot("opscontrol")
        finally:
            execute("dropdb", "-U", "opscontrol", "ci_restore")
        report = {
            "status": "PASS" if before == restored == after else "FAIL",
            "postgres_version": version,
            "before": before,
            "restored": restored,
            "original_after": after,
            "dump_sha256": hashlib.sha256(dump).hexdigest(),
            "dump_retention": "Synthetic credential-bearing dump erased after verification; hashes only retained",
            "isolated_restore_database_removed": True,
        }
        Path(output).write_text(json.dumps(report, indent=2) + "\n")
        if report["status"] != "PASS":
            raise ValueError("Backup/restore content or schema mismatch")
    print("Owned PostgreSQL backup/restore table and schema hashes PASS")


if __name__ == "__main__":
    import sys

    verify(sys.argv[1], sys.argv[2])
