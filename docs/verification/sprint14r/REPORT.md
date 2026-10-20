# Sprint14R — remediation verification, governance and UI foundations

Status: LOCAL ACCEPTANCE PASS; REMOTE CI/INTEGRATION PENDING. Production remains NOT READY. Baseline `origin/main@59344c97401340e222627063f7c89bb5e2e89ead`, isolated branch `feat/sprint14r-foundations`. No concurrent work was overwritten. Full original ENG-001/roadmap compliance is UNVERIFIED; the owner explicitly permits bounded work under existing repository requirements while controlled wording is reconciled.

The existing main P0/P1 remediation is reused and regression-tested: conservative Carte outcomes, partial observations, native nullable fields/step copies, monitoring-health separation, authorized inline onboarding and scoped stable pagination. There is no duplicate engine, model or historical branch merge. [Dispositions and changed components](IMPLEMENTATION.md).

New UI work extends existing semantic tokens and light/dark themes, fixes the reproduced720px collapsed-sidebar content offset, adds keyboard skip/mobile focus navigation, canonical breadcrumbs, compact keyboard-scrollable inventory tables and restrained shell glass with high-contrast/reduced-motion support. Existing routes, grouped/collapsed/mobile navigation, six pipeline pages, multiple collector methods, customer/internal-department separation and backend RBAC remain intact.

[Product Alignment](../../architecture/PRODUCT_ALIGNMENT_ADDENDUM.md), [OPS-DEPLOY-001](../../architecture/OPS_DEPLOY_001.md) and [ENG-001 reconciliation](../../engineering/ENG_001.md) now record supplied decisions with explicit owner-message provenance. They are summaries, not recovered verbatim originals. Private VPC/provider-controlled ingress-egress/proxy-VPN-CA and self-hosted Windows/Linux/container targets are recorded; no deployment/vendor compatibility is certified. [Owner decisions and unresolved wording](GOVERNANCE_RECONCILIATION.md).

## Evidence and limits

[Verification](VERIFICATION.md) records exact commands, failures, skip counts and actual controlled PostgreSQL/API/Chromium scope. New browser82 checks and preserved UI recovery52 pass;503 owned PostgreSQL/backend executions and92 native compatibility cases pass. Initial runtime API p95 exceeded its existing limit while other workloads overlapped; failure is retained; isolated rerun passed at812ms API/178ms ingestion. Critical coverage82.68% passed unchanged80%. No threshold, assertion or80% coverage requirement changed.

Representative actual synthetic screenshots: [baseline720px](evidence/baseline-720-collapsed.png), [light desktop](evidence/browser-paint/light-1366-inventory.png), [dark mobile](evidence/browser-paint/dark-390-inventory.png), [corrected720px](evidence/browser-paint/dark-720-inventory.png), [forced colors](evidence/browser-paint/forced-colors-navigation.png). They show test fixtures, not live infrastructure. [Independent manual UAT checklist](MANUAL_UAT_CHECKLIST.md) remains pending.

## Remaining dependencies

All [sixP0/eightP1/twoP2 readiness gaps](PRODUCTION_READINESS.md), AUD01–08 and [18 OC-IMP entries](IMPROVEMENT_REGISTER.md) remain traceable. Original62 IMP definitions remain SOURCE_NOT_RECOVERED. Shared canonical multi-customer resource design/runtime is unsupported and separately approval-blocked; no new schema or runtime implementation is authorized here. Full ENG wording, individual requirement revision confirmation, deployment topology/trust, genuine provider acceptance and independent UAT remain open.

The [reconciled12–42 planning framework](ROADMAP_RECONCILIATION.md) credits existing corrections and assigns deployment/network/certification dependencies. It adds14R as the current bounded correction; no future sprint starts. Recommended next increment is independent UAT and separately approved shared-resource design preparation, not another parser/navigation rewrite. No guarantee of production certification by42.

RT-001–RT-020: **NOT RUN**. Native repeated child execution identity: **UNVERIFIED**. No ETL workload, real source, production configuration, deployment, PR creation or protected PR33 modification occurred. Main integration remains conditional on all mandatory current gates and remote recheck; see [integration ledger](INTEGRATION.md).
