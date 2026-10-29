> **Scope correction — OC-SCOPE-REM-001 (2026-10-28):** Kubernetes, EKS, AKS, GKE, OpenShift and other Kubernetes distributions are REMOVED_FROM_SCOPE. Any cluster setup, monitoring, discovery or customer-association instructions below are superseded historical context and must not be used. VM/EC2, application, API and read-only Pentaho support remains in scope. See `docs/verification/scope-removal/kubernetes-platforms/REQUIREMENT_SCOPE_RECONCILIATION.md`.

> Current stage (2026-10-13): existing PRs #30/#31 are merged. `feature/consolidated-manual-uat` implements managed OTel telemetry, organization tables, single-department onboarding and independent alert/notification delivery; its dedicated PR follows owner-authorized merge after automated validation. See [UAT implementation and exact verification](CONSOLIDATED_UAT.md). Historical rows below record earlier milestones; incident/ServiceNow features are retired rather than planned release dependencies.

# OpsControl living implementation roadmap

Last reconciled 2026-10-13. Main baseline `e5f51181754324b1c274b2ad0128d951e62bd5a5` includes approved PRs #30 and #31, plus PR #23 (ETL), #24 (operational dashboards) and #25 (approved modern dual-theme UI). All sixteen PR #25 checks passed at its feature head; post-merge [Validation](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/actions/runs/38165657701) passed. GitHub API/PR creation and merge are operational. Historical Forbidden and pending development merge claims are superseded.

Implementation, controlled evidence, remote CI, human review, merge and production acceptance are separate states. Owner-approved development merges do not certify independent security review. AWS Toolkit/live AWS setup remains paused.

## P0 customer / internal access correction

Merged PR #31 (`feature/customer-department-rbac`) implements provider-owned departments, employee identity metadata, roles/permissions and paired customer grants with customer resources unchanged. Local PostgreSQL, browser, Docker, worker/tenant, ETL/incident and populated restore regressions are documented in the [implementation report](architecture/ACCESS_IMPLEMENTATION_REPORT.md). All 18 PR #31 checks passed before its approved merge; independent owner review remains distinct from automated checks. All 32 pre-existing non-access drift groups are [resolved without schema/data changes](architecture/SCHEMA_MODEL_RECONCILIATION.md); the full Alembic comparison passes and is enforced in CI. The owner accepts single-provider runtime and is conducting independent security review/UAT locally. This correction needs no production deployment or production data modification. Live AWS setup remains paused.

## Current development stage

| Workstream | Verified state | Next gate |
|---|---|---|
| Resource/rule management | Scoped sources, versioned independent rules, HTTP/infrastructure activation and collectors implemented and controlled-tested | Real provider/operator UAT and concurrency review |
| Sprint 1 HTTP | Actual synthetic HTTPS health→failure→recovery; DB/audit/tenant and browser evidence; merged/CI tested | Target deployment egress, CA rotation and UAT |
| Sprint 2 infrastructure | AWS SDK controlled collection, TLS K8s fixture, native Linux and controlled Windows; data-backed VM view; merged/CI tested | Genuine AWS/CloudWatch, native Windows, customer K8s acceptance |
| Sprint 3 Pentaho | Read-only Carte-shaped lifecycle, No Run/Long Running/SLA/history/logs/host correlation; PR #23 merged | Genuine Carte compatibility/read-only acceptance |
| Sprint 4 NOC | Data-backed tabs and investigation/report/scope journeys; PR #24 merged; consolidated UAT replaces incident workflows with monitoring Alerts | Fleet scale and operator UAT |
| UI Test 1 | Persistent dark/light themes, responsive navigation/bento layout, actual browser regression; approved PR #25 merged | Preserve appearance/accessibility during reliability work |
| Sprint 5 reliability | Approved reliability corrections merged via PR #26; retained restore/retention/TLS/resilience regression passes on the UAT branch | Exact-head CI/review, deployment-scale evidence and formal release acceptance |

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
