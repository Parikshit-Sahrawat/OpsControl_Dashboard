#!/usr/bin/env python3
"""Sprint0 real application baseline. No product mutation or shared environments."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get("OC_COMP_BASELINE_EVIDENCE", "/tmp/opscontrol-development-baseline"))
OUT.mkdir(parents=True, exist_ok=True)
PYTHON = ROOT / "backend/.venv/bin/python"
modules = ["tests." + p.stem for p in sorted((ROOT / "backend/tests").glob("test_*.py"))]
COMMON = {**os.environ, "AWS_EC2_METADATA_DISABLED": "true"}
sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
steps = [
    ("frontend", ["npm", "test", "--prefix", "frontend"], {}),
    ("lint", ["npm", "run", "lint", "--prefix", "frontend"], {}),
    ("build", ["npm", "run", "build", "--prefix", "frontend"], {}),
    ("postgres-http-browser", [str(PYTHON), "scripts/v16-acceptance.py"], {
        "V16_TEST_TARGETS": ",".join(modules), "V16_STAGING_PRESERVATION": "1",
        "V16_API_ACCEPTANCE": "1", "V16_BROWSER_ACCEPTANCE": "1",
        "V16_SPRINT08_ACCEPTANCE": "1", "V16_EVIDENCE_DIR": str(OUT / "postgres-http-browser"),
    }),
    ("security-restore-faults", [str(PYTHON), "scripts/release-acceptance.py"], {
        "RELEASE_BROWSER_ACCEPTANCE": "1", "RELEASE_EVIDENCE_DIR": str(OUT / "security-restore-faults"),
    }),
]
results = []
for name, command, flags in steps:
    with (OUT / (name + ".log")).open("w") as log:
        run = subprocess.run(command, cwd=ROOT, env={**COMMON, **flags}, stdout=log, stderr=subprocess.STDOUT)
    results.append({"name": name, "command": command, "flags": flags, "source_sha": sha, "exit": run.returncode})
    (OUT / "commands.json").write_text(json.dumps(results, indent=2) + "\n")
    print(name, "exit", run.returncode, flush=True)
# Failed independent suites do not suppress the other evidence. Nonzero remains failure.
sys.exit(1 if any(r["exit"] for r in results) else 0)
