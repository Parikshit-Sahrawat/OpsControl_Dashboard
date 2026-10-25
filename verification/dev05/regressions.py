"""Run only related existing contract tests and retain exact counts/outcomes."""

import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, "/app")
modules = [
    "tests.test_api_monitoring_config",
    "tests.test_api_worker_v2",
    "tests.test_remote_auth",
    "tests.test_infrastructure_health_projection",
    "tests.test_api_service_health_projection",
    "tests.test_collection_v15",
    "tests.test_pentaho_carte_compat",
    "tests.test_pentaho_execution_contracts",
    "tests.test_pentaho_history_contracts",
    "tests.test_pentaho_review_contracts",
]
suite = unittest.defaultTestLoader.loadTestsFromNames(modules)
result = unittest.TextTestRunner(verbosity=2).run(suite)
report = {
    "modules": modules,
    "total": result.testsRun,
    "passed": result.testsRun
    - len(result.skipped)
    - len(result.errors)
    - len(result.failures)
    - len(result.expectedFailures),
    "skipped": [
        {"test": str(test), "reason": reason} for test, reason in result.skipped
    ],
    "failures": [str(test) for test, _ in result.failures],
    "errors": [str(test) for test, _ in result.errors],
    "expected_failures": len(result.expectedFailures),
    "unexpected_successes": len(result.unexpectedSuccesses),
    "scope": "Existing synthetic/unit contracts; no real-provider acceptance implied",
}
Path("/golden/evidence/regressions.json").write_text(
    json.dumps(report, indent=2) + "\n"
)
sys.exit(0 if result.wasSuccessful() and result.testsRun > 0 else 1)
