> Closure update: see [FINAL_ACCEPTANCE_MATRIX.md](FINAL_ACCEPTANCE_MATRIX.md). Earlier results/limitations below are historical snapshots, not the final closure verdict.

# Source change report — 2026-10-28

Baseline `09a578f70282c7889a515c332c948f1940ae6719`. Initial removal `274175850c8553ecbf27d8cb0e7a2d9f5136a9da`; residual product/UI and regression correction `679ed2887a53eec4fe226876cd945fdd373fbe46`; synthetic preservation probe `c08be56909caee686eac5107846bdacea5d26346`; final fixture/guide removal `2e544d0f5cbfccaaebe7c71cf479813e464a17ab`.

See [inventory](REMOVAL_INVENTORY.md) and [results](REGRESSION_TEST_RESULTS.md). Dedicated cluster operational routes, adapters, discovery imports, SDK dependency, UI drawer and rendering branches, metric extraction, fixtures and cluster-only provisioning CI are removed. Excluded DataSource/Collector type input is rejected. General VM/EC2, API, read-only Pentaho and telemetry infrastructure remain in scope.

No schema migration or production collector change. Full PostgreSQL-backed regression: 538 passed, 2 skipped at `679ed2887a53eec4fe226876cd945fdd373fbe46`. Subsequent changes are test-only fixtures, a preservation probe and documentation; no later product behavior change. Historical test import failures were retained, then reconciled without removing retained-data security checks. This is a reviewable bounded removal, not completed browser/provider acceptance or release approval.

CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO

## Latest-main integration

PR 69 and PR 70 were merged externally during execution. Latest verified main `62a4eb4643c09594569aa61f0a60ae64035e6ede` is integrated at `5c0c5074f959bc47c3e2bb1591c2b421ad46b164`. The only conflict was the deleted dedicated Kubernetes verification script, resolved by keeping its removal. No changes relative to that main affect DEV-05.0/05.1/05.2 evidence, collector telemetry code or applied migrations. Final regression results below supersede initial baseline-only results for integration readiness; all earlier logs are retained.
