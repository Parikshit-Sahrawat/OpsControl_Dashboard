# Executed development verification

Use [commands](COMMANDS.json), [baselines](BASELINES.json) and raw `evidence/` files. Different suites overlap: do not add browser/API groups to unit counts or count repeated runs as new unique coverage.

| Boundary | Exact execution | Outcome |
|---|---|---|
| Broad PostgreSQL-backed backend discovery | 57 modules, source95b4ab6; `evidence/final/ownership.txt` | 564 run: **562 PASS, 0 FAIL, 2 SKIP** |
| Final resource-focused backend | sourceba80b49, `evidence/final-workspace/ownership.txt` | **12 PASS, 0 FAIL/SKIP**; overlap with broad run |
| Expanded migration/Pentaho foundation | sourcefcd385a, `evidence/final-visual/ownership.txt` | **68 PASS, 0 FAIL/SKIP**; overlap with broad run |
| Frontend Node helpers | sourceba80b49, `evidence/frontend-final-workspace-tests.log` | **44 PASS, 0 FAIL/SKIP** |
| Frontend ESLint / Vite production build | sourceba80b49, corresponding final logs | **PASS**, exits0 |
| Actual authenticated resource/template API | final workspace `api.json` | **15 PASS groups** including stale/session/scope/CAS/commit-failure/concurrent revocation negatives |
| Resource/template browser security | final workspace `resource-security.json` | **7 PASS groups** |
| New shared-workspace browser | final workspace `workspace-ui.json` | **9 PASS groups**, real backend; desktop/tablet/mobile/dark screenshots |
| Retained pipeline browser | final workspace `browser.json` | **PASS**, existing eight-step configuration/activation contract; synthetic provider fixtures |
| Retained RBAC | final-visual `sprint08-http.json`, `sprint08-browser.json` | **14 HTTP + 5 browser PASS groups** |
| Retained Pentaho browser | final-visual `sprint07-browser.json` | **17 PASS groups**, excluded incident UI not exposed; retained background identity checked through actual API |
| Retained Pentaho HTTP | final-visual Pentaho/review/history/incident JSON | **4 / 5 / 4 / 5 PASS groups**, synthetic monitoring evidence; no provider certification |
| Disposable release harness | source95b4ab6, `evidence/release/report.json` | **13 PASS groups** incl TLS/authorization/audit/notification/retention/fault/restore; not release clearance |
| Authority documentation validator | `evidence/static/authority.json`, `authority-tests.log` | Validator PASS + **9 PASS tests**; no authority/UAT promotion |
| Focused Python lint | `evidence/static/new-python-lint.log`, `ci-python-lint.log` | New Python files + configured fatal-error subset PASS |
| Unrestricted Python lint | `evidence/static/ruff-*.json` | **FAIL**: existing touched files20 baseline/19 candidate; zero new signatures; initial broader diagnostic also included unrelated sprint08 test formatting |
| Dependency audits | `evidence/security/commands.json` | Both exit1; Python10 advisory records in3 installed toolchain packages, npm4 moderate entries |
| Image SBOM/scans, dedicated secrets scanner, actionlint | Tools unavailable / no final release image candidate | **BLOCKED / NOT TESTED**; YAML + embedded Bash syntax checked independently |

The two skips are `test_actual_contrib_accepts_five_methods` and `test_actual_scrape_and_log_rotation_truncation_restart`: pinned Contrib binary not configured. They are NOT TESTED, not runtime PASS. Production pin is unchanged. Fixtures do not certify genuine Windows/Linux/EC2/Pentaho providers.

## Data preservation and fault boundaries

No applied migration or schema changed. Real PostgreSQL17.11/imageID `sha256:ab20e934b27ba3ff927c1b4c9ff8cf6c32f315f743efe68dd3441182a87fb085`, running on task-owned loopback-published tmpfs containers. FastAPI/React/Vite and headless Chromium/Playwright exercised real authenticated HTTP; synthetic data only.

- Broad run: **100 tables / 14,522 rows / 237 foreign keys** compared across source and restored database, including column metadata and canonical content hashes (`evidence/final/restore.json`). Source unchanged after restore. Expanded fixture and final-workspace counts are separately retained, not conflated.
- Release harness independent restore: **100 tables / 1,197 rows / 499 constraints**, audit trigger + migration head preserved. Corrupt checksum, backup overwrite and nonempty restore target refused. This small dataset is not production RTO/RPO certification.
- Fresh/populated upgrade and Alembic drift checks passed. Supported empty downgrade/upgrade passed; populated downgrade refused. Separate staging-preservation rerun includes `existing_database_upgrade_probe` and real pipeline ownership fixtures.
- Actual HTTP commit failure injection verifies rollback; CAS collision produces200/409; disabled parent/collector checks, revoked session401 and viewer403 remain real backend assertions. Browser interception delayed an actual fetched response (no fabricated body) to verify tenant switching; stale response cannot repopulate old inventory. Unsaved override draft survives conflict.
- No queue/spool crash certification or live collector installation is claimed. The retained 200 direct-SQL-sample/20-HTTP-read probe is explicitly **not OTLP**, no global responsiveness fix or performance SLO is inferred. RM-DEF-036 remains NOT REPRODUCED by that bounded probe.
- Only exact allocated containers/processes/private directories were cleaned. Per-run cleanup JSON and immutable image identities are retained. Synthetic backup archives were used for actual restore then removed because they contain synthetic authentication records; hashes/content comparisons retained. No broad Docker prune, customer volumes or shared UAT accessed.

## Preserved failures

1. Development attempt1: browser390px page overflow. Screenshot/raw AssertionError retained. Fixed button/chip sizing and mobile header layout.
2. Attempt2: Enter selection focused trigger and reopened global search, blocking subsequent click. Screenshot/timeout retained. Fixed default key activation, added dialog-close assertion and portaled dialog.
3. Staging-focused attempt: chose only lifecycle unit tests, which populate no protected pipeline tables; the harness's final *populated* downgrade assertion therefore failed. No production guard changed. Reran with actual pipeline ownership fixtures:56 PASS and populated refusal/restore passed. The earlier failure remains recorded.
4. Documentation validation initially rejected `evidence/release/eks.json`: the unchanged upstream harness writes JSON plus appended output into that file. Raw bytes retained as `eks.json.raw.txt`, not rewritten into an invented JSON result. Strict JSON validation is applied to actual JSON files.
5. Both audit failures and unrestricted lint findings remain unresolved, not hidden by passing behavioral tests.

Backend application source is byte-identical after95b4ab6; later commits adjust UI labels/layout, browser scope assertions and add a CI job. Expanded browser results belong to fcd385a; final workspace screenshots/results to ba80b49. Documentation-only final HEAD does not retroactively rename these tested SHAs.
