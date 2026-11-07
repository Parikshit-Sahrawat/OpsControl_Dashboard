#!/usr/bin/env python3
"""No provider/DNS/DB connections or subprocesses; bounded synthetic contracts."""
import json
import os
from pathlib import Path
import socket
import platform
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch
from sqlalchemy.engine import Engine

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ["DATABASE_URL"] = "postgresql+psycopg://offline:offline@127.0.0.1:1/offline"
os.environ["ENVIRONMENT"] = "test"
os.environ["ENV"] = "test"
blocked = []


def deny(*args, **kwargs):
    blocked.append("forbidden network/database/process operation")
    raise AssertionError(
        "OC-ETL-008A is offline: network, DNS and subprocess execution forbidden"
    )


if __name__ == "__main__":
    targets = [
        "tests.test_pentaho_qualification_offline",
        "tests.test_pentaho_surface_contracts",
        "tests.test_pentaho_r1",
        "tests.test_pentaho_carte_compat",
        "tests.test_etl_authority_writer.AuthorityEnvelopePolicyTests",
    ]
    # croniter probes ELF width using `file`; supply actual interpreter pointer width without spawning it.
    with patch.object(Engine, "connect", deny), patch.object(
        platform,
        "architecture",
        return_value=(str(struct.calcsize("P") * 8) + "bit", ""),
    ), patch.object(socket.socket, "connect", deny), patch.object(
        socket.socket, "connect_ex", deny
    ), patch.object(
        socket, "getaddrinfo", deny
    ), patch.object(
        socket, "gethostbyname", deny
    ), patch.object(
        subprocess, "Popen", deny
    ):
        suite = unittest.defaultTestLoader.loadTestsFromNames(targets)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(
        json.dumps(
            {
                "run": result.testsRun,
                "failures": len(result.failures),
                "errors": len(result.errors),
                "skipped": len(result.skipped),
                "blocked_io_attempts": len(blocked),
                "provider_qualification": "NOT RUN / BLOCKED",
                "database_connections": (
                    0 if not blocked else "forbidden attempts recorded"
                ),
                "subprocesses": 0 if not blocked else "forbidden attempts recorded",
            }
        )
    )
    sys.exit(0 if result.wasSuccessful() and not blocked else 1)
