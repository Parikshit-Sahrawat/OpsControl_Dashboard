# Measured queue matrix — 2026-10-26

Native delivery: **4 PASS, 13 FAIL** across 17 selected cases. All 18 attempts, including the superseded unmarked-replay failure: **4 PASS, 14 FAIL**. Run-local IDs must not be deduplicated across labs. Native FAIL is preserved after replay.

| Run / case | Runtime | Native | Expected | PG native | Missing native | Final PG | Accepted / rows / duplicates final | Recovery |
|---|---|---|---:|---:|---:|---:|---|---|
| guarded-baseline/0.123.0-staggered_production_saturation | 0.123.0 | FAIL | 267 | 257 | 10 | 257 | 257 / 257 / 0 | NOT TESTED |
| replay-attempt1/replacement_full | 0.163.2 | PASS | 267 | 267 | 0 | 267 | 267 / 267 / 0 | NOT TESTED |
| boundaries-attempt1/boundary_before_delete_1 | 0.123.0 | FAIL | 267 | 257 | 10 | 257 | 257 / 257 / 0 | NOT TESTED |
| boundaries-attempt1/boundary_after_delete_1 | 0.123.0 | FAIL | 267 | 257 | 10 | 257 | 257 / 257 / 0 | NOT TESTED |
| boundaries-attempt1/boundary_partial_replacement_1 | 0.163.2 | FAIL | 267 | 258 | 9 | 258 | 258 / 258 / 0 | NOT TESTED |
| replay-marker/legacy_full_replay | 0.123.0 | FAIL | 267 | 257 | 10 | 267 | 267 / 267 / 0 | PASS |
| replay-marker/repeated_crashes | 0.123.0 | FAIL | 267 | 257 | 10 | 267 | 267 / 267 / 0 | PASS |
| replay-marker/retention_expiry | 0.123.0 | FAIL | 267 | 257 | 10 | 257 | 257 / 257 / 0 | BLOCKED: Expired retention or invalid receipt time boundary |
| boundaries-repeat/boundary_before_delete_2 | 0.123.0 | FAIL | 267 | 257 | 10 | 257 | 257 / 257 / 0 | NOT TESTED |
| boundaries-repeat/boundary_after_delete_2 | 0.123.0 | FAIL | 267 | 257 | 10 | 257 | 257 / 257 / 0 | NOT TESTED |
| boundaries-repeat/boundary_partial_replacement_2 | 0.163.2 | FAIL | 267 | 258 | 9 | 258 | 258 / 258 / 0 | NOT TESTED |
| boundaries-repeat/boundary_after_reenqueue_replacement_1 | 0.163.2 | PASS | 267 | 267 | 0 | 267 | 267 / 267 / 0 | NOT TESTED |
| faults-attempt1/boundary_after_reenqueue_replacement_2 | 0.163.2 | PASS | 267 | 267 | 0 | 267 | 267 / 267 / 0 | NOT TESTED |
| faults-attempt1/enospc | 0.123.0 | FAIL | 267 | 257 | 10 | 267 | 267 / 267 / 0 | PASS |
| faults-attempt1/corrupt | 0.123.0 | FAIL | 267 | 0 | 267 | 0 | 0 / 0 / 0 | BLOCKED: queue corruption; no checkpoint/queue repair permitted |
| faults-attempt1/api_outage | 0.123.0 | PASS | 4 | 4 | 0 | 4 | 4 / 4 / 0 | NOT TESTED |
| faults-attempt1/permanent_rejection | 0.123.0 | FAIL | 4 | 0 | 4 | 0 | 0 / 0 / 0 | FAIL |

Final receipt reconciliation over the selected run-local sets: 4013 expected, 3664 persisted distinct, 349 missing, 3664 accepted record attempts, 3664 physical rows, 0 physical duplicates. These totals include deliberate corruption/permanent rejection and repeated tests; they are not a production loss rate.
