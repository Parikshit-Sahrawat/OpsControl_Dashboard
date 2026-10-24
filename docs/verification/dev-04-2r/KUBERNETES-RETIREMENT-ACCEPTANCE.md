# DEV-04.2R — Kubernetes monitoring retirement acceptance

## Scope and protected functionality
Retire **Kubernetes/EKS cluster and workload monitoring** only. Do not retire Kubernetes as a deployment platform, CNI enforcement tests, VM/EC2 monitoring, Linux/Windows monitoring, ETL/Pentaho, HTTP/API monitoring, shared topology, or unrelated RBAC. Preserve legacy Kubernetes cluster identities, customer associations, association decisions, collector history, monitoring evidence, and revocation APIs. No destructive schema migration is authorized.

## Implemented in PR #63
- New EKS/Kubernetes/K8S discovery scans and imports are rejected; EC2 discovery remains operational.
- New Kubernetes activation plans are rejected and the activation selector hides retired providers.
- Local execution prevents provider calls and disables encountered legacy collectors; the local due sweep disables enabled local Kubernetes collectors.
- Remote scheduler disables enabled Kubernetes collectors regardless of due time and cancels their QUEUED/LEASED jobs, clearing lease nonce hashes; records remain for historical inspection.
- Obsolete Kubernetes live-discovery acceptance expectations are replaced with negative retirement tests. Historical cluster-association tests retain revocation, tenant isolation and immutability checks through a test-only legacy import fixture.

## Verification and outstanding operational gates
- CI success is required **for the final head SHA**. Earlier 18/18 green result was for e8b1492, before the remote scheduler update; it cannot validate later changes.
- Confirm cancellation of queued and leased Kubernetes jobs in a disposable PostgreSQL environment, including jobs whose collector is already disabled. Confirm a worker cannot lease or submit a cancelled job; an already executing worker may require a separate drain/quiescence procedure.
- Confirm local and remote collectors of all three retired provider aliases stop, including not-yet-due collectors, and no new provider requests are made.
- Verify preserved cluster identities, association revisions, immutable decisions, historical evidence, and explicit revocation continue to function.
- Verify protected EC2/Linux/Windows, ETL/Pentaho, HTTP/API, shared topology and security workflows.
- Audit the final PR diff and obtain reviewer approval before merge. No claim of completed deployment-wide retirement until production inventory and active-worker drain have been verified.

## Deployment checklist
1. Inventory existing Kubernetes collector IDs, remote jobs (QUEUED/LEASED), and running workers; record counts and baseline evidence.
2. Quiesce Kubernetes-targeted remote workers or drain active leases before retirement to avoid an in-flight provider call.
3. Deploy the approved retirement changes and run the local and remote scheduler passes.
4. Check all retired collector types are disabled/STOPPED, no Kubernetes QUEUED/LEASED jobs remain, and preserved history/association decisions are queryable.
5. Run the protected-domain smoke tests, retain audit output and sign off explicitly.

**Status:** CI and operational acceptance pending for the latest retirement changes. PR #63 remains draft and unmerged.
