# Removal inventory — 2026-10-28

Baseline `09a578f70282c7889a515c332c948f1940ae6719`; final source/fixture revision `2e544d0f5cbfccaaebe7c71cf479813e464a17ab`. Raw complete tracked searches: [before](inventory-before.txt), [after](inventory-after.txt). [Per-file categories](inventory.json) classify locations; generic substring matches (deployment, namespace, pod, cluster) are not sufficient grounds for deletion. Semantic reconciliation of every historical planning match remains incomplete.

| Dependency chain | Disposition |
|---|---|
| `backend/app/api/resource_management.py` cluster list/detail/revoke routes and ClusterAssociationChange | Removed; historical models retained |
| `backend/app/api/discovery.py` → provider_discovery EKS/Kubernetes readers → Kubernetes SDK | Removed; EC2 workload identity and authorization retained |
| `backend/app/worker/collector_runtime.py` adapter → provider_checks Kubernetes health | Removed, including Kubernetes metric extraction |
| `backend/app/worker/infrastructure.py` Kubernetes config/metric family | Removed; historical safe evidence fields retained |
| `frontend/src/pages/UnifiedResourceManagement.jsx` → ImportedDiscoveryInventory | Drawer/component removed |
| ResourceManagementV2 and MonitoringSetup | Excluded sources filtered; EKS rendering branches removed |
| monitoring create/update schemas → activation engine | Removed platform types rejected; persisted legacy collectors retired by existing worker fences |
| requirements-providers.txt | Kubernetes SDK removed; EC2 SDK retained |
| `.github/workflows/kubernetes-cni-acceptance.yml` → verify-kubernetes-provider.sh | Dedicated cluster provisioning/verification removed; shared Docker and other CI preserved |
| Controlled Kubernetes HTTPS fixture, EKS discovery fixture, EKS browser inventory acceptance | Removed; shared EC2/Windows/Pentaho probes retained |
| release-acceptance.py → EKS fixture monkeypatch | Removed; rejection probe seeds historical data directly and rejects new EKS creation |

Retained by design: entities.py cluster/association/decision ORM metadata and exports; scope.py/resource_scope.py customer fences; migration 0038 and all applied migrations; immutable records, historical evidence and Git history. Shared container infrastructure and generic cloud metric Namespace fields are not Kubernetes support. Exclusion strings and negative tests are intentional references. No AKS/GKE/OpenShift-specific adapter was found in the application search; these aliases are rejected as excluded source types.

Old positive API tests have been replaced with removal/rejection contracts and direct legacy-data security tests, including tenant fences, DENY/LIMIT boundaries, foreign writes, immutable history, immutable identity and invalid revision/deletion. Prior failed import results remain in backend-full.log. Historical evidence outside this package is unchanged.

## Latest-main integration

PR 69 and PR 70 were merged externally during execution. Latest verified main `62a4eb4643c09594569aa61f0a60ae64035e6ede` is integrated at `5c0c5074f959bc47c3e2bb1591c2b421ad46b164`. The only conflict was the deleted dedicated Kubernetes verification script, resolved by keeping its removal. No changes relative to that main affect DEV-05.0/05.1/05.2 evidence, collector telemetry code or applied migrations. Final regression results below supersede initial baseline-only results for integration readiness; all earlier logs are retained.
