# 07 — Architecture Decision Records (Proposals)

All entries are **PROPOSED**, not final approvals.

## ADR-001 — Modular monolith first
**Context:** The current project has FastAPI modules plus a standalone worker and one PostgreSQL. Premature microservices would add deployment, distributed state and operational complexity before integration contracts are tested.
**Decision:** Keep one backend repository with strict modules (`identity`, `resources`, `templates/activation`, `collection`, `evidence`, `alerts`, `correlation`) and separate API/worker processes. Extract services only when load/security/ownership warrants.
**Consequences:** Easier local end-to-end testing and consistent data transactions; module boundaries require discipline.

## ADR-002 — Native OpsControl telemetry control plane
**Context:** Product direction is a custom monitoring console rather than requiring Prometheus/Grafana as the core product.
**Decision:** PostgreSQL owns operational configuration, selected metric samples, logs, alert states and evidence. Collector worker owns read-only collection. Future Prometheus/OpenTelemetry integration may expose operational telemetry without defining the primary product data contract.
**Consequences:** Implement retention, cardinality and query/load policies explicitly. Avoid making PostgreSQL a boundless raw telemetry warehouse.

## ADR-003 — Declarative template activation
**Context:** Current attachment + effective configuration is only a package resolution; runtime objects do not appear.
**Decision:** Separate attachment, effective preview, validated activation, generated configuration provenance and observed runtime health. Materialization is idempotent and reversible by deactivation, with evidence history retained.
**Consequences:** Requires activation tables/service, runtime health tracking and concurrency tests.

## ADR-004 — Mandatory server-side tenancy
**Context:** Verified anonymous GET/PATCH across synthetic organizations. UI multi-org selector is not security.
**Decision:** Authenticated principal and memberships enforce all org-scoped operations. UI selection may only narrow authorized scope. Negative authorization tests are release blockers.
**Consequences:** Add identity/RBAC data, cross-tenant constraints, audit trails and comprehensive API changes before production.

## ADR-005 — Collector registration is not agent installation
**Context:** UI stores an OTEL collector and `PENDING_INSTALL`, while runtime lacks OTEL adapter.
**Decision:** Distinguish agent registration and deployment status from supported polling/ingestion adapters. A collector cannot report `HEALTHY` without actual supported transport and recent evidence.
**Consequences:** Separate agent protocol/receiver decision and accurate UI states.

## ADR-006 — Configuration and evidence must not depend on notification delivery
**Context:** External email/PagerDuty/ServiceNow providers can be unavailable.
**Decision:** Persist alert transitions and outbound delivery records transactionally; dispatch with bounded retries, idempotent provider references and explicit error histories. No retry of a failed notification mutates ETL job state.
**Consequences:** Reliable alerts with independent provider diagnostics; operational ownership for dead-letter/retry.

## ADR-007 — Risk-gated DevOps sequencing
**Context:** Deploying an unauthenticated operational control plane would amplify a known vulnerability.
**Decision:** Validate functionality and security with local/ephemeral tests first. Containerize later; deploy with least-privilege credentials, managed data stores and network restrictions after quality gates; then Jenkins/ECR/Kubernetes/Helm/ArgoCD/Terraform as justified.
**Consequences:** CI now, Kubernetes later; no premature public staging of sensitive endpoints.

## Decision sign-off
Record owner, date, alternatives considered, tradeoffs and links to relevant issues before marking `ACCEPTED`. Especially confirm identity provider, retention, role boundaries and Pentaho source contract.
