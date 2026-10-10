# DOC-05 — Delivery Roadmap and Review Gates
**Status:** Proposed sequence; no dates committed.

## Phase 1 — Discovery and documentation
Deliverables: charter, SRS, repository assessment, PRD, traceability and prioritized backlog.
**Exit:** approve scope and requirements; complete code/runtime audit; record unresolved risks.

## Phase 2 — Architecture and design
Deliverables: component diagrams, ERD, tenancy/RBAC design, collector protocol, scheduling and secret management, API contracts.
**Exit:** architecture review; threat model; migration and failure-mode plans.

## Phase 3 — Core application
Workstreams: organizations/tenancy, data sources, template resolution and activation, collector lifecycle, metrics/logs, UI drilldowns.
**Exit:** end-to-end source -> collector run -> evidence -> dashboard flow passes tests.

## Phase 4 — Monitoring and integration
Workstreams: Pentaho adapter first (pending decision), VM/API/SFTP/S3/database adapters, alerts and notification integrations, correlation.
**Exit:** integration contract tests, retry/idempotency checks and operational runbooks.

## Phase 5 — Verification and hardening
Workstreams: cross-tenant negative tests, performance/load, reliability, accessibility, security and regression.
**Exit:** documented test evidence and approved residual risks.

## Phase 6 — Delivery automation
Workstreams: Docker, CI, image registry, Kubernetes/EKS, Helm, GitOps, IaC and observability as justified.
**Exit:** reproducible staging deployment, rollback and secret handling verified.

## Phase 7 — Release and operations
Workstreams: release checklist, training, runbooks, SLO monitoring, incident response and feedback.
**Exit:** approved release and ownership handoff.

## Suggested priority backlog
P0: tenant isolation; reliable source-to-collector activation; secret safety; collector observability; source state semantics.
P1: Pentaho operational flow; metrics/logs/alerts; KPI drilldowns; migration and integration tests.
P2: expanded adapters; notification integrations; investigation enhancements; reports.
P3: AI assistance and controlled remediation after security review.

## Definition of Done
Documented requirement + implementation + tests + permission checks + observability + user documentation + review approval. Unverified features cannot be marked Done.
