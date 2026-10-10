# OpsControl — Living Implementation Roadmap

**Last reconciled:** 2026-10-10  
**Current development head:** `feat/secure-remote-collector-protocol` (draft PR [#20](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/pull/20))  
**Scope:** General-purpose, vendor-neutral open-source monitoring and observability. No organization-specific source data, private hostnames, business processes or customer credentials.

> **Progress accounting:** "Implemented" means committed code exists on a branch; "CI verified" means specified automated checks passed on that branch; "Production ready" requires external security review, installation/deployment and user acceptance. No draft PR in this roadmap is merged into `main`. Do not claim implementation is production-ready merely because tests pass.

## Live priorities

| Priority | Feature | Verified implementation status | Immediate next step | Evidence / dependencies |
|---|---|---|---|---|
| **P0** | Authentication and organization isolation | **Implemented + CI verified** on feature/security branches; not merged or externally approved | Independent authorization review, nonempty DB upgrade, deployment hardening; merge only with approval | [PR #17](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/pull/17), [PR #19](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/pull/19), [security checklist](SECURITY_RELEASE_CHECKLIST.md) |
| **P0** | Template activation and collector provisioning | **Not implemented end-to-end**; existing template attachment, effective-config resolution and manual collectors do not constitute automatic monitoring | Build preview → validate → idempotent reconciliation → collector/metric/log/alert provisioning → activation state → deactivation/rollback | [Phase 2 monitoring activation specification](sdlc/phase2/README.md); depend on organization RBAC and rule catalogs |
| **P0** | Authenticated remote job dispatch and evidence ingestion | **HTTP MVP implemented + CI verified**: scoped workers, assignment, scheduled/leased jobs, nonce fencing, deduplicated evidence, CollectorRun, metric samples, native alert evaluation | Deployment threat-model review, HA/load/retention and integration with activation engine | [PR #20](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/pull/20), [agent quickstart](REMOTE_AGENT_QUICKSTART.md) |
| **P0** | Private-network egress protection | **Application controls implemented + CI verified**: HTTPS GET/443, exact host + CIDR, DNS pinning, redirect deny, metadata/loopback deny, local agent allowlist | Verify external firewall/CNI enforcement, private CA/TLS and egress restrictions against real isolated test network | [PR #20](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/pull/20), [example NetworkPolicy](../deploy/examples/remote-agent-networkpolicy.yaml); not production approved |
| **P1** | Independent Metric, Log and Alert Rule catalogs | **Architecture defined**; existing metric definitions/log sources/alerts do not equal reusable rule-version catalogs | Build catalog models, versioning, RBAC, rule compatibility/preview, bindings and template bundles | [Phase 2 rule catalog design](sdlc/phase2/09-RULE-CATALOG-DESIGN.md) |
| **P1** | Live homepage world clock | **Implemented + Playwright browser verified** in foundation branch; no need to wait for backend polling | Preserve time-zone selection, DST correctness and UI refresh separation; UX polish only | [PR #16](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/pull/16), staging CI |
| **P1** | HTTP / Internal Application Health | **Remote HTTPS availability/status MVP implemented**; rich assertions, credential-based journeys, full onboarding and synthetic browser tests pending | Onboarding UI → checks/metrics/rules → activation → real local synthetic end-to-end test | [Remote agent quickstart](REMOTE_AGENT_QUICKSTART.md), [internal UI specification](sdlc/phase2/13-INTERNAL-APPLICATION-UI-MONITORING.md) |
| **P1** | AWS EC2 discovery/monitoring | **Architecture only**; no production-ready EC2 collector | Read-only discovery, manual import review, CloudWatch/status metrics, least-privilege IAM, mocked tests | [Resource Discovery specification](sdlc/phase2/14-RESOURCE-DISCOVERY-INFRASTRUCTURE-MONITORING.md) |
| **P1** | Kubernetes Pod/Deployment discovery | **Architecture only**; no operational Kubernetes adapter | Namespace-limited inventory, Pod Ready/restarts and Deployment availability, optional metrics-server, fake-K8s tests | [Resource Discovery specification](sdlc/phase2/14-RESOURCE-DISCOVERY-INFRASTRUCTURE-MONITORING.md) |
| **P1** | Generic sample data and developer onboarding | **Quickstart/documentation started**; public-ready one-command demo and reproducible screenshots not complete | Synthetic-only fixture pack, bootstrap admin, Docker Compose local profile, scripted smoke and real UI screenshots | [Beginner Quickstart](QUICKSTART.md), README |
| **P1 — parallel** | Pentaho and generic ETL job monitoring | **ETL data model, screens and investigation workflows exist; real Pentaho collector is a stub** | Read-only Pentaho execution adapter, schedules/no-run/SLA semantics, evidence ingestion, end-to-end fake adapter test | Independent workstream: must not depend on cloud monitoring implementation |
| **P2** | Apache/Tomcat deep monitoring, Linux/Windows process telemetry | **Architecture only** | Secure host-level agent metrics, Apache status / Tomcat JMX under explicit RBAC/egress policy | Starts after HTTP → EC2 → Kubernetes foundational slices |
| **P2** | Enterprise security & deployment | **Security design/implementation underway**; **production release blocked** | External review, secret vault, retention, TLS/ingress, audit management, DR, multi-tenant load testing | [Issue #18](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/issues/18), [SECURITY.md](../SECURITY.md) |

## Delivery order and verification gates

| Stage | Deliverable | Done means |
|---|---|---|
| **0 — Security acceptance** | Authenticate all human/worker entry points; enforce tenant isolation and least privilege | Two-org negative tests; authorization/DB upgrade/security review complete; no unauthorized source access |
| **1 — Rule catalogs** | Versioned, independently attachable Metric/Log/Alert Rules | Create, pin versions, list/filter, edit new version, compatibility errors, audit, cross-org negatives |
| **2 — Activation engine** | Operational monitoring config from chosen rules/template | Preview → preflight → activate → real evidence → metric/log/alert → deactivation. Reapply is idempotent and rollback auditable |
| **3 — HTTP golden path** | A new self-hoster monitors one synthetic local/private HTTPS service | No hardcoded provider specifics; documented first-run with screenshots and real detection/recovery |
| **4 — EC2** | AWS resource discovery + read-only health | Candidate import and drift, denied-region/IAM tests, CloudWatch metric validation |
| **5 — Kubernetes** | Namespace-scoped Pod/Deployment health | Fake/disposable cluster fixtures; watch reconnect; unavailable metrics API handled |
| **6 — Apache/Tomcat** | Server and JVM/service health | Test containers, credentials/transport security and independent app-versus-host health |
| **Parallel — ETL** | Production-like job runs, No Run and SLA evaluation | Fictional Pentaho fixture with read-only adapter; no AWS/K8s dependency |

## Updating this roadmap after every stage

For every significant implementation or validation:
1. Update the affected row's **exact verified status** and next action; never promote "design" to "done" without runtime evidence.
2. Link the branch/PR, migration, test suite and latest successful CI run (or mark pending/failed).
3. Keep these states distinct: **Designed**, **Code committed**, **Automated tests passing**, **Reviewed**, **Merged**, **Release verified**.
4. Prefer one manageable vertical slice with negative auth/network tests and a working local synthetic fixture.
5. Keep the table synchronized with README and Quickstart. Do **not** silently merge draft PRs, deploy publicly or introduce employer/customer-specific artifacts.

## Recent milestones

- **Phase 2 foundation** — PR #16: homepage world clock and non-placeholder overview status, browser tests.
- **Auth/tenancy** — PR #17: user sessions, memberships, backend organization isolation.
- **Security hardening** — PR #19: rate limiting, audit, revocation, admin UI, vulnerability/secret scans.
- **Remote HTTP collector** — PR #20: scoped private agent, scheduled leases, strict outbound policy and safe evidence ingestion.
- **Next proposed implementation** — rule catalogs followed immediately by template/rule activation. Review approval required for merges or any production deployment.
