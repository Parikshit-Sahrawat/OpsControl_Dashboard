# OPS-DEPLOY-001 — Private-Network Deployment and Connectivity

Controlled reconciliation v0.1. Status: OWNER-APPROVED DEPLOYMENT DECISIONS; IMPLEMENTATION AND CERTIFICATION INCOMPLETE. Source: Sprint 14R owner kickoff and source clarification, received 20 October 2026. Original discussion transcript, original approval date and full wording are unavailable. No canonical predecessor was found in the bounded repository/ref/issue search. This is a sourced summary, not a verbatim recovered document.

Authority: [ARCH-001 V1.6](../ARCH_001_V16.md), [ARCH-ETL-001 V1.6](ARCH_ETL_001_V16.md), [Product Alignment](PRODUCT_ALIGNMENT_ADDENDUM.md). Preserve existing identity, ownership, RBAC, source fencing and evidence rules. No production deployment exists or is authorized here.

## Approved deployment direction

Operate within a provider-controlled private VPC or equivalent private network. The provider controls ingress and egress, routing, DNS, trust stores, VPN/private connectivity and enterprise proxy configuration. Do not assume public inbound access or unrestricted outbound internet. The provider deployment team owns CA integration, agent/collector identity issuance, renewal, rotation and revocation.

Self-hosted Windows, Linux and container deployments are targets. Existing source, installers, Compose configuration or controlled Linux/container tests do not certify all target operating systems or builds. Reuse existing deployment mechanisms; no competing deployment stack is introduced in Sprint 14R.

Enterprise proxy, VPN and certificate trust must be explicitly configured and verified for the actual topology. TLS verification must stay enabled; no trust-all certificates, skipped hostname verification or embedded credentials. CrowdStrike and Zscaler are compatibility evidence requirements only: **no compatibility test or certification has been performed**. No vendor allowlist/exclusion policy is invented here.

## Boundary and evidence matrix

| Boundary | Owner / existing control | Required independent evidence / open decision |
| --- | --- | --- |
| Customer resource → Agent/collector | Provider technical team; existing collection identities, token controls and read-only adapters | Approved route, exact OS/build, least-privilege credential source and attribution policy |
| Agent/collector → ingestion API | Provider network/CA team; existing scoped authentication, TLS and method checks | Private DNS/proxy/VPN paths, actual CA chain, expiry/revocation/rotation and denied paths |
| API → workers/PostgreSQL/evidence | Provider operations; current migrations, evidence references and fencing | Segmentation, encrypted storage/backup, key custody, HA, WAL/PITR and recovery drill |
| Employee browser/API → application | Provider security; current sessions, direct/inherited roles, explicit scopes and revocation | Approved access ingress, enterprise identity integration if required, independent customer-negative UAT |
| Notifications / provider APIs / package distribution | Provider-controlled egress and destination authority | Specific destinations, proxy/no-proxy policy, restricted/offline update workflow and delivery evidence |

## Required deployment acceptance inputs

Owner must supply approved topology, addresses/routes, trust owner, supported Windows/Linux/container versions, certificate/credential providers, network security controls, external destinations and evidence policy before real connections. Never paste secrets into reports. Each live test group requires separate authorization. Controlled fixtures and local TLS are explicitly limited evidence.

Recovery targets remain configurable RPO15 minutes/RTO4 hours, daily full backup, continuous WAL/PITR where supported, operational30-day/monthly12-month retention subject to policy, monthly restore and quarterly DR drill, encryption and legal-hold precedence. These are approved targets, not achieved production guarantees; no storage/retention job is changed.

[Roadmap dependencies](../verification/sprint14r/ROADMAP_RECONCILIATION.md) and [open approvals](../verification/sprint14r/GOVERNANCE_RECONCILIATION.md) control follow-up. No production or vendor compatibility certification is implied by publishing this document.
