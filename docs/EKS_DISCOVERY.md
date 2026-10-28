> **Scope correction — OC-SCOPE-REM-001 (2026-10-28):** Kubernetes, EKS, AKS, GKE, OpenShift and other Kubernetes distributions are REMOVED_FROM_SCOPE. Any cluster setup, monitoring, discovery or customer-association instructions below are superseded historical context and must not be used. VM/EC2, application, API and read-only Pentaho support remains in scope. See `docs/verification/scope-removal/kubernetes-platforms/REQUIREMENT_SCOPE_RECONCILIATION.md`.

# Read-only EKS inventory discovery

`AWS_EKS` discovery uses the existing optional boto3 SDK and workload identity. A platform administrator configures an enabled discovery Data Source with explicit `region`, 12-digit expected `account_id`, and optionally 1–50 exact `cluster_names`. Static credentials, role/profile switches, endpoint overrides and scanning arbitrary URLs are rejected.

The adapter checks STS caller account before EKS calls. With explicit cluster names it describes only those clusters; otherwise it lists with bounded pagination then describes at most 100 clusters. The ARN/name must match the expected AWS partition/account/region. Returned facts are cluster identity, control-plane status and Kubernetes version. Endpoint, certificate authority and tags are not returned or used to connect to Kubernetes.

Required read-only IAM: `eks:ListClusters` for unfiltered discovery and `eks:DescribeCluster` for approved cluster ARNs; expected identity is verified with `sts:GetCallerIdentity`. Use resource/region conditions and scoped workload identity appropriate to the approved sandbox. No Create/Update/Delete EKS actions are performed. Individual SDK connect/read/retry limits are bounded; sustained load, overall multi-call deadlines and real account IAM still require acceptance.

## API and approval flow

1. As platform admin, POST `/api/v1/resource-management/data-sources` with `source_type=AWS_EKS` and approved connection config.
2. POST `/api/v1/resource-discovery/sources/{source_id}/scan` to obtain candidates. Scan does not import or activate anything.
3. POST `/api/v1/resource-discovery/sources/{source_id}/import` with `approved_external_ids` and `dry_run=true`; verify no DB inventory change.
4. Repeat with `dry_run=false` only for approved identifiers. Import creates an organization-scoped AWS_EKS source with stable external identity and status UNKNOWN, **without a collector**. Repeated import returns ALREADY_IMPORTED and preserves ID.
5. Resource Management shows the imported cluster in both themes as **Discovery only**. Its generic VM/agent editor and Monitoring Setup activation are disabled. API activation also rejects EKS inventory with an actionable message.

Control-plane ACTIVE is not a workload health measurement. Pod/Deployment/Node health continues through an explicitly deployed namespace-scoped Kubernetes service-account collector. Discovery does not create a kubeconfig, use the described endpoint/certificate, or imply connectivity to the cluster.

## Controlled verification

```bash
(cd backend && .venv/bin/python -m unittest discover -s tests -v)
RELEASE_BROWSER_ACCEPTANCE=1 PLAYWRIGHT_MODULE=/absolute/path/playwright/index.mjs \
RELEASE_EVIDENCE_DIR=/tmp/eks-review backend/.venv/bin/python scripts/release-acceptance.py
```

The release API's fixture startup is guarded by `ENVIRONMENT=demo` and `OPSCONTROL_RELEASE_ACCEPTANCE=1`; ordinary/prod API startup never installs the fixture. Actual boto3/botocore Stubber clients validate service response shapes, read-only request order and parameters. They explicitly ignore external AWS profiles/configuration and use only synthetic credentials; no AWS packet or real credential lookup is made. The HTTP API, database, dry run/import, tenant denial and browser screens are real. [Backend ledger](acceptance/operational-sequence/sprint5-eks.json), [browser ledger](acceptance/operational-sequence/sprint5-eks-browser.json), [light](acceptance/operational-sequence/eks-light.png), [dark](acceptance/operational-sequence/eks-dark.png).

Live AWS/Agent Toolkit setup remains paused. Genuine EKS account/region/IAM and customer-cluster service-account/network compatibility have not been accepted. This is controlled inventory acceptance, not production EKS health certification.
