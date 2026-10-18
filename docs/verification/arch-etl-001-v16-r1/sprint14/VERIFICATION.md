# Sprint 14 verification record

## Baseline and scope

Repository `/workspace/OpsControl_Dashboard`, branch `feat/arch-etl-001-v16-r1`. Before edits, local HEAD and fetched `origin/feat/arch-etl-001-v16-r1` both equaled required Sprint 13 baseline `2479846805e4f4755a2c37898a154b1f95074603`; working tree was clean. Sprint 13 report, Sprint 10–12 readiness evidence, architecture §11, Pentaho adapter paths and relevant tests were inspected. Changes are confined to the ten Sprint 14 Markdown files. No executable code, migration, deployment configuration or approved architecture was edited.

## Actual checks

| Check | Exact command or method | Result |
|---|---|---|
| Adapter, R1 safety and registry tests | `cd backend && .venv/bin/python -m unittest tests.test_pentaho_r1 tests.test_pentaho_surface_contracts tests.test_pipeline_adapters -v` | PASS: 55 tests, 0 failures, 0 skips, 0.032 s. |
| Execution, review, history and incident contracts | `cd backend && .venv/bin/python -m unittest tests.test_pentaho_execution_contracts tests.test_pentaho_review_contracts tests.test_pentaho_history_contracts tests.test_pentaho_incident_contracts -v` | PASS: 22 tests, 0 failures, 0 skips, 0.010 s. |
| Legacy/R1 conservative result comparison | In-process synthetic `<jobstatus><id>r1</id><status_desc>Finished</status_desc></jobstatus>` passed to `parse_carte_status` and R1 `parse_status` | FINDING: legacy `SUCCESS`, R1 `UNKNOWN`; no network/process launch. See [S14-01](ADAPTER_SAFETY_AUDIT.md). |
| Documentation completeness, links, case coverage, unchanged protected paths | Local Python and Git checks below | See final result recorded below. |

The first backend invocation used a mistaken `backend/.venv/bin/python` path while already in `backend` and exited 127; the corrected command above is the executed passing run. No result was suppressed. Existing fixtures already exercise R1 conservative outcomes and read-only boundaries; no duplicate assertion was added to enshrine unsafe legacy behavior.

## Documentation validation

The read-only `python - <<'PY' ... PY` validation at delivery checked the exact set of ten required Markdown files, every local Markdown link, exactly one row for each RT-001–RT-020, exact architecture §11 tab-separated coverage strings, every row's NOT RUN status, all 16 P0–P2 gap IDs, AUD-01–AUD-08 continuity and IMP/OC-IMP status markers. **PASS.** An initial version of the validator incorrectly expected the architecture's coverage index to use Markdown table delimiters; it failed on RT-001. The corrected check uses the source's tab-separated format and passed. This was a validation-script formatting error, not a case-content mismatch. `git diff --check` and protected-path checks are part of the final Git gate.

## Evidence boundary

Installed-build tests: **0 run; RT-001–RT-020 NOT RUN — REAL INSTALLED-BUILD ACCEPTANCE OUTSTANDING.** PostgreSQL, browser, real agent/collector, Pentaho Server, Carte and Kitchen/Pan were not used in this sprint. No test here demonstrates real-runtime compatibility, native success, production CA/private route, workload safety on an installed build, RPO/RTO or production readiness. An independent, separately authorized witness is required before any RT status changes.
