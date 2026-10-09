# DOC-09 — Phase 1 Discovery Handoff and Decision Register

**Version:** 0.1 | **Date:** 2026-10-10 | **Status:** Discovery evidence substantially complete; owner sign-off and clean UI capture review pending. **Not a production approval.**

## What Phase 1 delivers
- Charter, SRS with IDs and acceptance criteria, current-state assessment, product journeys, delivery roadmap, traceability, risk register, source audit and reproducible staging verification.
- Implementation findings separated from future requirements and from independently verified runtime results.
- GitHub issues [#2–#11](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/issues) and [#14](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/issues/14) preserve reproducible defects and implementation gaps.

## Executed evidence
- [Run 37986761440](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/actions/runs/37986761440): clean migration failed with duplicate PostgreSQL `executiontype` enum; tracked as #14.
- [Run 37986901968](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/actions/runs/37986901968): after PostgreSQL ENUM fix, migrations/API passed; harness stopped on test script import path; subsequently corrected.
- [Run 37987009835](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/actions/runs/37987009835): **successful CI jobs**, including fresh PostgreSQL migration, FastAPI startup, React build, synthetic tenant probes, and manually configured API collector sampling. This proves *test execution*, not that security requirements pass.
- Corrected UI capture run and final screenshot review: **pending final review**; artifacts from 37987009835 showed browser-to-API connectivity misconfiguration, subsequently corrected on the branch.

## Verified behavior from 37987009835
| Check | Observed | Compliance |
|---|---|---|
| PostgreSQL 17 migrations | `alembic upgrade head` succeeded | PASS |
| FastAPI startup/OpenAPI | Served routes | PASS |
| React production build | Completed | PASS |
| Manual API collector -> metric sample | One successful run; one sample, value 1.0 | PASS |
| Anonymous organization list | HTTP 200 | **FAIL — required auth** |
| Anonymous Data Source list/detail/edit | HTTP 200 on all | **FAIL — required auth** |
| Cross-tenant unfiltered list | Both artificial tenant data sets exposed | **FAIL — tenant isolation** |
| Attached monitoring template | Attachment/effective config created, zero Collector / MetricDefinition rows | **FAIL — no runtime activation** |

The independent synthetic diagnostics confirm a **P0 security vulnerability**, and show that template attachment alone is not operational monitoring. Application behavior has not been modified for either issue.

## UI evidence reconciliation
Navigation: Overview, ETL Jobs, Resource Management are rendered pages; VM Health, APIs, Incidents and Reports are navigation placeholders. The previous SVG assets are illustrative drawings, not real screenshot captures. Real Playwright screenshots of seven navigation and four Resource Management views are retained in the GitHub Actions artifacts. Actual functionality beyond initial rendering remains unverified, including resource onboarding and agent installation.

## Discovery completion vs release readiness
The SDLC Discovery phase can exit when specifications are baselined, gaps are verified or explicitly marked unverified, remediation work is tracked, and design decisions are identified. **It does not require fixing all product defects during requirements gathering.** By contrast, *production readiness* is blocked until mandatory authorization, operational template activation, supported adapters, and full negative/integration tests pass.

## Proposed release-1 scope, subject to owner approval
1. Secure organization/workspace boundary and RBAC; a UI filter never grants authorization.
2. Reliable Data Source onboarding and template activation that materializes and executes operational configuration.
3. First functioning API collector as vertical slice, then read-only Pentaho monitoring and priority VM adapters.
4. Metric evidence, alert state transitions and consistent drilldowns from live KPI counts.
5. Audit trails, secrets safety, installation/operation runbooks, and regression tests.

## Decision register for Phase 2
| Decision | Proposed baseline | Approval |
|---|---|---|
| Architecture | Modular FastAPI backend + React + PostgreSQL + separate worker; avoid premature microservices | Proposed |
| Organization authorization | Server-enforced principal -> allowed org IDs, scoped DB queries, explicit role capabilities | REQUIRED |
| Templates | Pinned, declarative config with validated reconcile/activate/detach lifecycle and runtime health | REQUIRED |
| Initial integrations | Read-only API vertical slice, Pentaho as first production ETL adapter | Proposed |
| Alerts | Evaluate persisted evidence; retry/idempotency; never auto-remediate by default | Proposed |
| Retention/SLO | Define measurable targets in Phase 2 after realistic scale and compliance assumptions | Open |
| Credentials | External secret references and least privilege; never production credentials in public docs | REQUIRED |
| Logging and screenshots | Real browser captures and reproducible synthetic data; distinguish illustrations | REQUIRED |

## Phase 2 entry
**Conditionally ready for design work** based on the user's instruction to continue, with explicit unapproved decisions and product-blocking issues. Phase 2 architecture documents must say *proposed*, not *approved*, until reviewed. No merge/deployment is authorized by this handoff.

## Phase 1 review checklist
- [x] Inventory and code-based gap assessment
- [x] Requirements, charter, product journeys, traceability and prioritized issues
- [x] Disposable PostgreSQL and FastAPI smoke execution
- [x] Baseline verification of tenant exposure and template failure
- [x] Positive manual collector-to-sample test
- [x] Initial actual browser screenshots and placeholder identification
- [ ] Final corrected browser evidence and visual comparison
- [ ] Owner approval of release-1 scope, role capabilities and risk priorities
- [ ] Merge approval (separate from advancing draft design)
