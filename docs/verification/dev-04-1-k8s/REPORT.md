# DEV-04.1 — K8S-01 bounded implementation evidence

Base: `origin/main` `422b8cbb7551104aae34293000cef33e28d916dd`. The owner explicitly ratified the four ADR-K8S-001 contracts on 2026-10-23 for K8S-01 implementation. This does not approve OC-IMP-017 in full. The [canonical register](../../planning/DEVELOPMENT_COMPLETION_REGISTER.md) and [bounded backlog](../issue-47/BACKLOG.md) are the requirement sources.

## Reproduced gap and correction

At the base revision, EKS discovery imports one customer-owned `DataSource` per Organization, but there is no canonical Kubernetes cluster entity or explicit cluster-customer association. Source inspection confirmed the missing model and route; the new regression was not executed against a separate baseline checkout. Existing `DataSource.organization_id` and VM/EC2 ownership are unchanged.

For EKS responses that contain a provider-issued cluster ID as well as an account/region/name-verified ARN, approved imports now converge on one canonical cluster row. The customer-owned sources remain separate. Each explicit import creates one audited association; a repeated import is idempotent and cannot reactivate a revoked association. Association changes use a row lock, expected revision and immutable decision record. The only exposed mutation is revocation; a fresh-evidence regrant workflow is deliberately absent.

Customer cluster list/detail projections intersect customer selection, effective `resources.view`, active association and applicable LIMIT/DENY resource boundaries before counts and pagination. Unknown cluster IDs return 404. Cluster-level inventory is `UNKNOWN`, with empty namespace and workload scopes; no telemetry, topology or health is inferred. No Kubernetes write or workload-control endpoint was added.

An EKS ARN alone is not enough to distinguish a recreated physical cluster. If the authenticated provider response lacks its cluster ID, the existing customer-owned discovery import remains available but no shared-cluster association is granted (`cluster_identity_status=UNVERIFIED`). A changed provider ID for the same ARN returns 409 for identity review; no automatic merge occurs. Other Kubernetes discovery methods lack this verified cluster identity path and remain outside this increment.

## Controlled verification

Environment: new, disposable PostgreSQL 17.11 Docker container, with separate fresh and populated-upgrade databases. No existing volume was mounted or reset. Synthetic EKS provider responses were used; no live AWS/Kubernetes access occurred.

- Baseline source inspection: no `KubernetesCluster` model and no `/kubernetes-clusters` resource-management route at `422b8cbb`.
- Fresh Alembic upgrade to `0038_k8s_cluster_associations`: PASS.
- Populated `0037_access_boundaries` → `0038_k8s_cluster_associations`: PASS. The synthetic Organization and EKS `DataSource` retained exact IDs, ownership and discovery identity. No association was fabricated for the historical source.
- `OPSCONTROL_V16_ACCEPTANCE=1 python -m pytest -q tests/test_kubernetes_cluster_associations.py tests/test_eks_discovery.py tests/test_sprint12_shared_trust.py tests/test_access_control.py`: **21 passed, 0 failed, 0 skipped** in disposable PostgreSQL (plus 280 unittest subtests). Tests cover same physical ID across A/B, distinct customer sources, scope denial, forged customer selection, resource-boundary denial, revision conflict, immutable history and identity, no silent regrant, missing provider ID, and changed physical ID quarantine.
- `python -m alembic check`: PASS; no new upgrade operations detected.
- Python compilation, targeted Ruff fatal-error check, Black check on new files, and `git diff --check`: PASS.

The exact final test count and commit are recorded in the draft PR. Controlled fixtures are developer evidence only; independent UAT, genuine EKS/native acceptance and production readiness remain open.

## Bounded limitations

- Standard EKS installations whose provider response lacks a stable cluster ID receive no shared-cluster association. An authorized, independently verifiable physical identity method is needed before this path can be extended.
- Namespace/workload UID attribution, scoped telemetry, topology edges, caches, exports and incident projection are not implemented by this cluster-inventory increment. They must continue to deny by default; do not interpret cluster visibility as workload permission.
- Revocation removes the new canonical cluster projection immediately. The customer-owned `DataSource` configuration remains retained under its existing ownership contract; it is not a grant to cluster telemetry or workload data. Any future EKS telemetry path must check the current association revision before release.
- No browser UI was added. The Resource Management API is the controlled inventory projection; current customer-owned discovery UI remains separate.
- Revoked associations and their immutable audit history remain stored. Regrant requires a separately reviewed fresh-evidence workflow; the revocation route cannot reactivate from stale proof.
- Real provider compatibility, independent UAT and deployment were NOT RUN.
