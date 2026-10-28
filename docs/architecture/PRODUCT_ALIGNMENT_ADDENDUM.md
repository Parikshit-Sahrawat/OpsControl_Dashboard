> OC-SCOPE-REM-001 (2026-10-28): Kubernetes, EKS, AKS, GKE, OpenShift and other Kubernetes distributions are REMOVED_FROM_SCOPE. This owner decision supersedes earlier supported-cluster descriptions below. Historical text is retained for audit; VM/EC2 exclusive customer ownership is unchanged.

# Product Alignment Addendum — controlled reconciliation v0.1

Status: OWNER-APPROVED DECISIONS, RECONCILED SUMMARY. Approval provenance: owner Sprint 14R kickoff and subsequent source-clarification messages received 20 October 2026. The original planning discussion, its approval date and verbatim wording have not been recovered. This document records the decisions supplied in this session; it does not claim to reproduce an original specification. Broader wording requires owner review in the [decision register](../verification/sprint14r/GOVERNANCE_RECONCILIATION.md).

[ARCH-001 V1.6](../ARCH_001_V16.md) and [ARCH-ETL-001 V1.6](ARCH_ETL_001_V16.md) remain controlling. This addendum does not change their canonical models, identities, permissions, migrations or execution semantics.

## Approved product boundaries

OpsControl is an industry-neutral observability platform for data pipelines, compute, APIs and distributed applications. One provider operates the installation for monitored customer organizations. Access Management departments are the provider's internal workforce teams; they are not customer organizations.

Resource Management owns canonical inventory, onboarding and collection configuration. Data Pipelines, Compute Instances and API Endpoints are operational monitoring views. Reuse existing APIs and stores; navigation must not create a second configuration control plane.

Maintain explicit customer scopes and backend effective authorization. Selecting a customer or ALL listed customers never grants authority. A shared resource target retains one canonical identity with explicit authorized associations and attributable evidence. **The positive many-customer resource model is not implemented or authorized by Sprint 14R.** Its schema, API, revocation and derived-visibility design still require separate approval.

Preserve native platform types, collection-method identity, one fenced active owner, immutable execution/evidence history, retries, reviewed recovery links, legal holds and all existing adapters. OpsControl must not start, stop, rerun, repair or cancel ETL workloads. Separate execution outcome, monitoring health and evidence completeness; incomplete evidence cannot certify success or NO_RUN.

## UI direction approved for bounded Sprint 14R work

Extend the existing semantic light/dark design system with deliberate typography, compact tables, restrained glass treatment on appropriate shell surfaces, visible focus and reduced-motion support. Preserve grouped/collapsible navigation, mobile access, permissions, routes, customer-scope clearing, collector multiple-method workflows and all six Data Pipeline pages. Keep functional interfaces and existing terminology; no static replacement screens or new framework/dependencies.

Independent UAT remains required. Automated Chromium and contrast checks are development evidence, not accessibility certification. Production remains NOT READY. [Deployment decisions](OPS_DEPLOY_001.md) and the [seven release gates](../verification/sprint14r/PRODUCTION_READINESS.md) remain separate from product approval.
