# Executed bounded tests and actual result

Both commands used the repository's Python 3.12 backend virtual environment and **controlled fixtures only**; no PostgreSQL, browser, network or Pentaho host was needed. Each run completed with exit code zero.

```sh
cd backend
.venv/bin/python -m unittest tests.test_pentaho_r1 tests.test_pentaho_surface_contracts tests.test_pipeline_adapters -v
```

**55 passed, 0 failed, 0 skipped** in 0.032 s. The selected tests cover R1 CLI exit versus native result, Server authority, Carte GET path/egress/TLS, missing R1 result/error-count UNKNOWN, exact-build gating, native identity, redaction and the eight non-Pentaho adapter descriptions.

```sh
cd backend
.venv/bin/python -m unittest tests.test_pentaho_execution_contracts tests.test_pentaho_review_contracts tests.test_pentaho_history_contracts tests.test_pentaho_incident_contracts -v
```

**22 passed, 0 failed, 0 skipped** in 0.010 s. These controlled contracts cover retry outcomes, WAITING_FOR_RETRY, conflict/review boundaries, timezone/DST, incident correlation and recovery conditions. One test intentionally logs a historical-notification worker failure while asserting live alert delivery continues; the suite itself passed.

An additional read-only, in-process XML comparison called `parse_carte_status` and R1 `parse_status` with the same synthetic response lacking `nr_errors`: `legacy_missing_nr_errors: SUCCESS`; `r1_missing_nr_errors: UNKNOWN`. This demonstrates [S14-01](ADAPTER_SAFETY_AUDIT.md), not installed-build behavior. It made no HTTP request and executed no command.

No new test was added: existing focused tests already assert R1 read-only and conservative outcome boundaries. Adding a test that *expects* the located legacy unsafe result would entrench it; an authorized correction should add the regression alongside the fix. No genuine Pentaho RT-001–RT-020 case was run. Unit tests and mocks cannot certify an installed build.
