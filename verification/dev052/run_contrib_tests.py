#!/usr/bin/env python3
"""Execute the exact two runtime gates; fail if any test is skipped or absent."""
import argparse
import json
import os
from pathlib import Path
import sys
import unittest
from provision_contrib import verify

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--binary", type=Path, required=True)
parser.add_argument("--report", type=Path, required=True)
args = parser.parse_args()
verify(args.binary)
os.environ["OPSCONTROL_OTEL_BINARY"] = str(args.binary.resolve())
root = Path(__file__).resolve().parents[2]
os.chdir(root / "backend")
sys.path.insert(0, str(root / "backend"))
names = [
    "tests.test_collection_v15.CollectionV15Tests.test_actual_contrib_accepts_five_methods",
    "tests.test_collection_v15.RealCollectionRuntimeTests.test_actual_scrape_and_log_rotation_truncation_restart",
]
result = unittest.TextTestRunner(verbosity=2).run(
    unittest.defaultTestLoader.loadTestsFromNames(names)
)
ok = result.wasSuccessful() and result.testsRun == 2 and not result.skipped
args.report.resolve().write_text(
    json.dumps(
        {
            "tests": names,
            "run": result.testsRun,
            "skipped": len(result.skipped),
            "failures": len(result.failures),
            "errors": len(result.errors),
            "status": "PASS" if ok else "FAIL",
        },
        indent=2,
    )
    + "\n"
)
sys.exit(0 if ok else 1)
