# OpsControl living implementation roadmap

Last reconciled 2026-10-11. Main baseline `fbe83badb47ee61b81fe60f23dde48c37b1ee1d0` includes PR #23 (ETL), #24 (operational dashboards) and #25 (approved modern dual-theme UI). All sixteen PR #25 checks passed at its feature head; post-merge [Validation](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/actions/runs/38165657701) passed. GitHub API/PR creation and merge are operational. Historical Forbidden and pending development merge claims are superseded.

Implementation, controlled evidence, remote CI, human review, merge and production acceptance are separate states. Owner-approved development merges do not certify independent security review. AWS Toolkit/live AWS setup remains paused.

## P0 customer / internal access correction

Dedicated unmerged feature branch `feature/customer-department-rbac` implements provider-owned departments, employee identity metadata, roles/permissions and paired customer grants with customer resources unchanged. Local PostgreSQL, browser, Docker, worker/tenant, ETL/incident and populated restore regressions are documented in the [implementation report](architecture/ACCESS_IMPLEMENTATION_REPORT.md). Remote CI and independent review are separate PR gates. No production deployment or live AWS setup is authorized by these results. Full Alembic comparison reports 32 pre-existing non-access drift groups; new access tables/user metadata match the migration.

## Current development stage

| Workstream | Verified state | Next gate |
|---|---|---|
| Resource/rule management | Scoped sources, versioned independent rules, HTTP/infrastructure activation and collectors implemented and controlled-tested | Real provider/operator UAT and concurrency review |
| Sprint 1 HTTP | Actual synthetic HTTPS health→failure→recovery; DB/audit/tenant and browser evidence; merged/CI tested | Target deployment egress, CA rotation and UAT |
| Sprint 2 infrastructure | AWS SDK controlled collection, TLS K8s fixture, native Linux and controlled Windows; data-backed VM view; merged/CI tested | Genuine AWS/CloudWatch, native Windows, customer K8s acceptance |
| Sprint 3 Pentaho | Read-only Carte-shaped lifecycle, No Run/Long Running/SLA/history/logs/host correlation; PR #23 merged | Genuine Carte compatibility/read-only acceptance |
| Sprint 4 NOC | All primary tabs data-backed; incident/investigation/report/scope journeys; PR #24 merged | Fleet scale and operator UAT |
| UI Test 1 | Persistent dark/light themes, responsive navigation/bento layout, actual browser regression; approved PR #25 merged | Preserve appearance/accessibility during reliability work |
| Sprint 5 reliability | P0/P1 corrections and controlled populated restore/retention/TLS/resilience gate on separate feature branch | Exact-head CI/review, deployment-scale evidence and formal release acceptance |

## Implementation priorities

The canonical [P0–P3 matrix](RELEASE_RELIABILITY.md) records root causes, impact, implemented source paths and remaining acceptance. Resolve P0 safety/recovery/deployment gates before calling this a release candidate; continue P1 load, scale and onboarding validation without waiting for live providers.

- P0: reconciled evidence, independent authorization/security review, populated restore/retention, restricted runtime roles and TLS/proxy/SPA headers.
- P1: bounded concurrent collection/recovery, dashboard inventory/query scale, clean Docker upgrade/rollback/operator UAT; genuine provider work deferred.
- P2: real Apache/Tomcat, external incident delivery and duration-weighted SLO; dependency/archive scale follow-ups.
- P3: operator-driven visual/usability improvements.

## Acceptance references

[HTTP](HTTP_GOLDEN_PATH.md), [Infrastructure](INFRASTRUCTURE_MONITORING.md), [Pentaho](PENTAHO_ETL_MONITORING.md), [Operational UI](OPERATIONAL_DASHBOARDS.md), [Sprint reassessment](SPRINT_REASSESSMENT.md), [security checklist](SECURITY_RELEASE_CHECKLIST.md), [field evidence](PHASE2_FIELD_ACCEPTANCE.md).

Every new PR records exact head checks, artifacts, reviewer decision and merge separately. Preserve negative tests and real evidence; mocks are identified explicitly. Production rollout remains conditional on independent security/deployment review, target-volume recovery/resilience, operator UAT and formal acceptance.

## 2026-10-12 ordered implementation sequence

Main now includes approved reliability PR #26 at `277ec2c` with seventeen green head checks and green post-merge Validation. [The requested stabilization → activation → telemetry → alerts/ServiceNow → EKS/deployment sequence](OPERATIONAL_RELEASE_SEQUENCE.md) fixes remaining registration/transport/delivery gaps and captures controlled evidence merged into main through PR #27. [Architecture](OPERATIONAL_ARCHITECTURE.md), [OWASP checklist](security/OWASP_API_2023_CHECKLIST.md), [ServiceNow](SERVICENOW_INTEGRATION.md), [EKS](EKS_DISCOVERY.md) and [UAT/rollback](DEPLOYMENT_UAT.md) document exact boundaries. PR #27 subsequently passed all 17 exact-head checks at `c3250e0` and merged with owner approval as `2b33b9f`. No PR remains open at this reconciliation; genuine providers, independent security review and formal production acceptance remain separate gates.
