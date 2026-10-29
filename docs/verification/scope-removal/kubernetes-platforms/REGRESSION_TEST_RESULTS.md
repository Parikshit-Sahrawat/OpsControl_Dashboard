> Closure update: see [FINAL_ACCEPTANCE_MATRIX.md](FINAL_ACCEPTANCE_MATRIX.md). Earlier results/limitations below are historical snapshots, not the final closure verdict.

# Regression results — 2026-10-28

| SHA / check | Command and evidence | Result |
|---|---|---|
| 2741758 full SQLite discovery | `python -m unittest discover -s tests -v`; backend-full.log | 317 PASS / 217 SKIP / 2 import ERROR (preserved failed attempt) |
| `679ed2887a53eec4fe226876cd945fdd373fbe46` PostgreSQL full suite | `OPSCONTROL_V16_ACCEPTANCE=1 .venv/bin/python -m unittest discover -s tests -v`; backend-postgresql-679ed28.log | 538 PASS / 2 SKIP / 0 FAIL / 0 ERROR; 540 total |
| `679ed2887a53eec4fe226876cd945fdd373fbe46` frontend | `npm test --prefix frontend`; frontend-tests-679ed28.log | 36 PASS / 0 FAIL |
| `679ed2887a53eec4fe226876cd945fdd373fbe46` frontend static/build | `npm run lint --prefix frontend`; `npm run build --prefix frontend` | PASS; >500KB bundle warning retained |
| Unchanged migrations, same hashes as baseline | `.venv/bin/alembic upgrade head`; migration-fresh.log | PASS fresh PostgreSQL; first loopback attempt FAIL retained |
| c08be56909caee686eac5107846bdacea5d26346 | `OPSCONTROL_SCOPE_REMOVAL_FIXTURE=1 .venv/bin/python -m scripts.scope_removal_preservation_probe` | PASS; 100 tables matched for populated no-op upgrade and restoration |
| `2e544d0f5cbfccaaebe7c71cf479813e464a17ab` provider probes | `python -m scripts.provider_unit_probe`; `python -m scripts.infrastructure_unit_probe` | PASS, synthetic EC2/Pentaho, selectors, Windows platform refusal, sanitization |

Backend commands run from backend with the explicit task-owned DATABASE_URL; never default application/UAT DB. Actual isolated PostgreSQL URL target was 172.18.0.2:5432/scope_removal. It is ephemeral and must not be reused without verifying new fixture identity. Fixture is now removed. Probe source enforces task label, bridge IP and database name.

Full-suite names in the raw log cover tenant/RBAC/access boundaries, VM resource identity, collector activation/hydration, API/TLS/remote authorization, Pentaho/pipeline semantics, alerts/incidents and migrations. The two skips are `test_actual_contrib_accepts_five_methods` and `test_actual_scrape_and_log_rotation_truncation_restart`: pinned Contrib binary not configured. No collector qualification attempted. No passing test implies genuine-provider certification.

NOT RUN: new browser end-to-end unavailable-UI acceptance; hosted CI workflows; genuine Windows/Linux/cloud/Pentaho provider tests; full live HTTP release-acceptance harness after fixture reconciliation. No UAT or production access. Backend global lint is not claimed; Python compileall and diff whitespace checks passed. Security/durability gates remain unchanged.

## Final integrated revision

At `5c0c5074f959bc47c3e2bb1591c2b421ad46b164` incorporating current main `62a4eb4643c09594569aa61f0a60ae64035e6ede`:

- Full backend PostgreSQL suite, same command/environment: **545 total, 543 PASS, 2 SKIP, 0 FAIL/ERROR** (`final-backend-5c0c507.log`). The same two pinned-binary checks remain skipped.
- Frontend: **36 PASS**, lint PASS, build PASS (`final-frontend-5c0c507.log`, `final-lint-5c0c507.log`, `final-build-5c0c507.log`). Bundle-size warning remains.
- Fresh PostgreSQL migrations PASS (`final-migration-5c0c507.log`). Populated upgrade/restore PASS for all 100 tables (`final-preservation-5c0c507.json`); one synthetic cluster, two associations, one immutable decision retained. No new migration or destructive operation.
- Second owned fixture container/network removed after validation. No named volume or unrelated Docker cleanup.

No acceptance gaps above are silently closed by these reruns. Full browser/HTTP harness and genuine providers remain NOT TESTED.
