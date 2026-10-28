# Results at implementation `274175850c8553ecbf27d8cb0e7a2d9f5136a9da`

All execution used development checkout; no customer/provider targets. Backend DATABASE_URL was explicitly set to `sqlite:////tmp/opscontrol-scope-removal-unit.db`.

| Command | Actual result |
|---|---|
| backend: DATABASE_URL=sqlite:////tmp/opscontrol-scope-removal-unit.db .venv/bin/python -m unittest discover -s tests -v | FAIL:536 total,317 passed,217 skipped,2 import errors |
| npm test --prefix frontend | PASS:36 tests,0 failures,0 skips |
| npm run lint --prefix frontend | PASS |
| npm run build --prefix frontend | PASS, bundle-size warning retained |

Failures: test_eks_discovery imports removed aws_eks_candidates; test_kubernetes_cluster_associations imports removed ClusterAssociationChange. These require scope-correct replacement tests preserving tenant/authorization/history protections. They are not suppressed. Full logs retained. The earlier focused67-test command passed before the final retirement-fence changes; it is not substituted for exact-commit full-suite results.

Fresh/populated PostgreSQL migration, actual VM registration, collector activation integration, ETL/Pentaho provider integration, full HTTP route-denial matrix, Docker acceptance and hosted mandatory CI: NOT RUN/NOT ESTABLISHED here. SQLite/unit passes cannot establish those gates. Backend static/lint gate not fully assessed. Removal is INCOMPLETE, NOT READY for owner acceptance.
