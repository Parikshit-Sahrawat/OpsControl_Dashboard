"""Timed owned-PostgreSQL scenarios, not vendor/runtime throughput certification."""

import json
import os
import time
import unittest
from pathlib import Path
from tests.test_pipeline_ownership_v16 import OwnershipTests
from tests.test_pentaho_execution_r1 import PentahoExecutionTests
from tests.test_sprint09_hardening import Sprint09Hardening

assert (
    os.getenv("OPSCONTROL_V16_ACCEPTANCE") == "1" and os.getenv("ENVIRONMENT") == "test"
)
results = []
for cls, method, concurrency, dataset in (
    (
        OwnershipTests,
        "test_two_actual_database_sessions_cannot_both_own_source",
        2,
        "one source; two competing PostgreSQL sessions",
    ),
    (
        PentahoExecutionTests,
        "test_duplicate_observations_keep_raw_records_but_not_duplicate_attempts_revisions",
        1,
        "one source; repeated accepted native observation",
    ),
    (
        Sprint09Hardening,
        "test_worker_restart_resumes_retained_recovery_without_reprocessing",
        1,
        "two retained events; two fresh worker sessions; one-row recovery batches",
    ),
):
    samples = []
    for _ in range(3):
        result = unittest.TestResult()
        case = cls(method)
        started = time.perf_counter()
        case.run(result)
        elapsed = time.perf_counter() - started
        assert result.wasSuccessful() and not result.skipped, (
            method,
            result.errors,
            result.failures,
            result.skipped,
        )
        samples.append(elapsed)
    ordered = sorted(samples)
    results.append(
        {
            "scenario": method,
            "dataset": dataset,
            "iterations": 3,
            "internal_concurrency": concurrency,
            "duration_seconds": round(sum(samples), 4),
            "throughput_scenarios_per_second": round(3 / sum(samples), 3),
            "p50_ms": round(ordered[1] * 1000, 3),
            "p95_ms": round(ordered[-1] * 1000, 3),
            "p99_ms": round(ordered[-1] * 1000, 3),
            "failures": 0,
            "skips": 0,
        }
    )
Path(os.environ["V16_EVIDENCE_DIR"], "sprint09-resilience.json").write_text(
    json.dumps(
        {
            "status": "PASS",
            "measurements": results,
            "limits": "Three samples per scenario include fixture setup; p95/p99 reported as observed maximum. No OS crash, remote failover or genuine runtime certification.",
            "production_scale_certification": False,
            "genuine_runtime_acceptance": False,
        },
        indent=2,
    )
)
print(
    "Sprint 09 measured PostgreSQL ownership/duplicate/restart resilience PASS: 9 scenarios"
)
