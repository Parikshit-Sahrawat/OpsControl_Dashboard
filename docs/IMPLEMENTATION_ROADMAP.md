# OpsControl — Living Implementation Roadmap

**Last reconciled:** 2026-10-10  
**Development baseline:** `main`, consolidated through [PR #22](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/pull/22) and its dependency PRs.
**Scope:** General-purpose, vendor-neutral open-source monitoring and observability. No organization-specific source data, private hostnames, business processes or customer credentials.

> **Progress accounting:** "Implemented" means committed code exists on a branch; "CI verified" means specified automated checks passed on that branch; "Production ready" requires external security review, installation/deployment and user acceptance. The owner approved development consolidation into `main` on 2026-10-10 with live AWS and genuine Carte acceptance deferred. These remain follow-up acceptance tasks, not passed checks. See the [merge decision and evidence](PHASE2_FIELD_ACCEPTANCE.md). Do not claim implementation is production-ready merely because tests pass.

## Live priorities

| Priority | Feature | Verified implementation status | Immediate next step | Evidence / dependencies |
|---|---|---|---|---|
| **P0** | Authentication and organization isolation | **Implemented + CI verified** in the development baseline; external review pending | Independent authorization review, real deployed-data upgrade and deployment hardening; disposable upgrade preservation passed | [PR #17](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/pull/17), [PR #19](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/pull/19), [security checklist](SECURITY_RELEASE_CHECKLIST.md) |
| **P0** | Template activation and collector provisioning | **HTTP vertical slice implemented + disposable PostgreSQL CI verified**: preview, pinned rule/template resolution, idempotent remote HTTP collector, metric/log/alert provisioning, disable and preserved history; non-HTTP activation pending | Private HTTPS end-to-end acceptance passed in disposable Docker CI; browser-synthetic assertions and non-HTTP activation still pending | [Phase 2 monitoring activation specification](sdlc/phase2/README.md); depend on organization RBAC and rule catalogs |
| **P0** | Authenticated remote job dispatch and evidence ingestion | **HTTP MVP implemented + CI verified**: scoped workers, assignment, scheduled/leased jobs, nonce fencing, deduplicated evidence, CollectorRun, metric samples, native alert evaluation | Deployment threat-model review, HA/load/retention and integration with activation engine | [PR #20](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/pull/20), [agent quickstart](REMOTE_AGENT_QUICKSTART.md) |
| **P0** | Private-network egress protection | **Python egress guards + real Docker internal-network firewall test CI passed**; deployable Kubernetes NetworkPolicy and live CNI test script created, **disposable kind+Calico CNI acceptance passed** | kind+Calico test now runs in CI; verify deployment-specific CNI/firewall and real reverse proxy | [PR #20](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/pull/20), [example NetworkPolicy](../deploy/examples/remote-agent-networkpolicy.yaml); not production approved |
| **P1** | Independent Metric, Log and Alert Rule catalogs | **Independent METRIC/LOG/ALERT catalogs implemented + staging CI verified**: immutable versions, org RBAC, pinned bindings and validation | Immutable rule-version editor implemented; compatibility for non-HTTP providers and real-user acceptance remain | [Phase 2 rule catalog design](sdlc/phase2/09-RULE-CATALOG-DESIGN.md) |
| **P1** | Live homepage world clock | **Implemented + Playwright browser verified** in foundation branch; no need to wait for backend polling | Preserve time-zone selection, DST correctness and UI refresh separation; UX polish only | [PR #16](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/pull/16), staging CI |
| **P1** | HTTP / Internal Application Health | **HTTP onboarding UI + backend activation implemented** with worker enrollment, versioned rules and operational evidence; browser-synthetic journeys not yet implemented | Disposable private TLS evidence→alert OPEN→RESOLVED passed; richer assertions, live private CA and operator UAT remain | [Remote agent quickstart](REMOTE_AGENT_QUICKSTART.md), [internal UI specification](sdlc/phase2/13-INTERNAL-APPLICATION-UI-MONITORING.md) |
| **P1** | AWS EC2 discovery/monitoring | **Read-only EC2 adapter/discovery/import implemented; offline mocks CI verified; no real AWS account tested** | OIDC-only read-only AWS field-test workflow added; NOT RUN without approved sandbox account, IAM role and instance | [Resource Discovery specification](sdlc/phase2/14-RESOURCE-DISCOVERY-INFRASTRUCTURE-MONITORING.md) |
| **P1** | Kubernetes Pod/Deployment discovery | **Pod/Deployment read-only adapter plus namespace-scoped Pod discovery/import implemented; offline mocks and disposable kind cluster CI verified** | Deployment-specific cluster acceptance and remaining capability gaps | [Resource Discovery specification](sdlc/phase2/14-RESOURCE-DISCOVERY-INFRASTRUCTURE-MONITORING.md) |
| **P1** | Generic sample data and developer onboarding | **One-command localhost Docker demo implemented and CI verified** with random local admin secret, fictional seed, PostgreSQL/FastAPI/React, protected ports; UI screenshot smoke added | Add turnkey synthetic HTTPS probe lab, onboarding tutorial screenshots and broader beginner docs | [Beginner Quickstart](QUICKSTART.md), README |
| **P1 — parallel** | Pentaho and generic ETL job monitoring | **Read-only pinned-TLS Pentaho Carte adapter and idempotent JobOrderHistory persistence implemented; offline XML and DB tests in CI; not tested on live Carte** | Synthetic pinned TLS Carte lifecycle test and Secrets Manager credential-ref code added; genuine Carte authorization/execution and No Run/SLA remain | Independent workstream: must not depend on cloud monitoring implementation |
| **P2** | Apache/Tomcat deep monitoring, Linux/Windows process telemetry | **Read-only Linux host/process, Apache mod_status, Tomcat JVM parsers implemented with offline safety tests**; live service validation pending | Harden agent boundaries and test actual Apache/Tomcat fixtures | Starts after HTTP → EC2 → Kubernetes foundational slices |
| **P2** | Enterprise security & deployment | **Security design/implementation underway**; **production release blocked** | External review, real Secrets Manager role, retention, TLS/ingress, audit management, DR and tenant load testing | [Issue #18](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/issues/18), [SECURITY.md](../SECURITY.md) |

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

## Field acceptance and testing evidence

See [Phase 2 Field Acceptance](PHASE2_FIELD_ACCEPTANCE.md) for precisely which real and synthetic environments were exercised; mark provider-specific claims as *pending* until their dedicated field tests pass. Do not infer production readiness from mock fixtures.

## Recent milestones

- **Phase 2 foundation** — PR #16: homepage world clock and non-placeholder overview status, browser tests.
- **Auth/tenancy** — PR #17: user sessions, memberships, backend organization isolation.
- **Security hardening** — PR #19: rate limiting, audit, revocation, admin UI, vulnerability/secret scans.
- **Remote HTTP collector** — PR #20: scoped private agent, scheduled leases, strict outbound policy and safe evidence ingestion.
- **Phase 2 integrations** — PR #21: versioned independent Metric/Log/Alert catalogs; HTTP activation/reconciliation, UI onboarding, EC2/K8s read-only adapters and discovery, Carte ETL status persistence, one-command fictional Docker demo and network-isolation CI.
- **Field acceptance PR #22** — isolated real TLS probe and PostgreSQL alert/recovery test passed in disposable CI, diagnostics and immutable rule editor added, kind+Calico/RBAC, upgrade preservation, optional OIDC AWS field gate, scoped secret resolution and host/Apache/Tomcat read-only prototypes. See [Phase 2 field acceptance ledger](PHASE2_FIELD_ACCEPTANCE.md). Genuine AWS and Carte installations have **not** been validated. Development merge approved with real-provider tests deferred; production approval remains outstanding.
