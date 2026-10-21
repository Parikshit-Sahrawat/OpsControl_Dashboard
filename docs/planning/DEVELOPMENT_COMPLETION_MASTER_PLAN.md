# OpsControl Phase 1 Development Completion Master Plan v1.0

Status: OWNER-APPROVED OPERATING MODEL; PROVISIONAL IMPLEMENTATION PLAN. Repository baseline main 4ebd8d8a64dff75ef7577c169c76e651e435dcc7. See DEVELOPMENT_COMPLETION_REGISTER.md.

## Four phases
1. Development: complete all approved functional coding, with unit/integration/security/customer-isolation/CI/migration preservation checks on every bounded increment.
2. Manual and Automated Testing: comprehensive end-to-end independent acceptance, real provider runtime tests, assistive technology and environment provenance.
3. Improvements and Bug Fixes: stabilize, optimize and close defects based on evidence.
4. Deployment and Release: seven release gates, controlled adoption, measured recovery and owner authorization.

## Solo-developer rules
- One primary development workstream active at a time; no six parallel feature branches.
- Prefer 2–3.5 hours active coding per bounded Codex slice; checkpoint before five hours. Avoid redundant context and full suite reruns when a focused failure can be diagnosed first.
- Automate lint/build/test/coverage/security/migration evidence; do not replace full final acceptance with targeted checks.
- Maintain one canonical requirement register (DEVELOPMENT_COMPLETION_REGISTER.md), one development backlog (this plan), one defect register (link to existing improvement/UAT registers), one release-readiness record (docs/verification/sprint14r/PRODUCTION_READINESS.md).
- Risk-based review: customer isolation, security, schema migration, legal holds, deletion and credential changes require negative tests and preservation checks.
- AI and owner testing is not independent third-party certification; label evidence accurately.
- Codex coding policy: prefer dedicated tools over shell; rg for search; inspect before editing; preserve dirty worktrees; never destructive git resets; conform to design system; root-cause fixes and real verification. Tool-specific guidance (such as multi_tool_use.parallel) applies only where actually available. Never identify as a different model as an operational policy.
- PR #33 protected. No production deploy without explicit owner approval.

## First integration gate: PR #41
PR #41 at c98809e7de630ed9fbb04178acc7e58dd76ba434 is unmerged as of this record. Its current-head workflows include failures in Synthetic operational dashboard acceptance and ARCH-001 V1.5 continuous quality, despite many green checks. The PR description says the coverage floor was changed from 80% to 65%, and preceding-head CI measured 66.32%; this is a policy discrepancy requiring explicit reconciliation before merge certification. Preserve all completed UI work and Stage B safeguards. Do not merge until mandatory required checks pass on final immutable head and scope/coverage policy is resolved. Recheck main SHA, then verify resulting merged main. PR #33 untouched.

## Sequential packages
| Package | Workstream | Target bounded slice | Dependency | Developer-level exit |
| --- | --- | --- | --- | --- |
| P1-00 | DEV-01 | PR #41 gate remediation and exact main reconciliation | CI and coverage policy | All required checks pass on final SHA, safe merge and post-merge verification |
| P1-01 | DEV-01 | Recover UI-001–023 and source-path inventory; complete customer/employee workflows | P1-00 | All registered actions wired; RBAC negatives, browser tests |
| P1-02 | DEV-01 | Profile and Help/SOP/FAQ UI and docs | P1-01 | Authenticated profile, permissions and responsive help navigation |
| P1-03 | DEV-06 | Admin application settings API/persistence/security | P1-01 | Audited authorized changes; denied users cannot mutate |
| P1-04 | DEV-02 | Agent enrollment and collector multi-method lifecycle | P1-03 | Repeatable controlled Windows/Linux enrollment and method identity |
| P1-05 | DEV-02 | Logs/metrics/traces, durable replay, clocks and coverage | P1-04 | Scoped accepted/rejected/lost evidence under failure |
| P1-06 | DEV-03 | Compute VM/EC2 and real host monitoring | P1-05 | One-customer ownership and native state evidence |
| P1-07 | DEV-03 | Pentaho native read-only monitoring and nine adapters | P1-05 | Version-specific compatibility and execution/health separation |
| P1-08 | DEV-03 | API/TLS and synthetic journeys | P1-05 | Scoped read-only outcomes, synthetic labeled explicitly |
| P1-09 | DEV-04 | Shared Kubernetes cluster design, discovery and attribution | P1-01, P1-05 | Same cluster authorized across customers, no cross-tenant workload leakage |
| P1-10 | DEV-04 | Topology, history and freshness | P1-09 | Scoped versioned relationships and forged-ID negatives |
| P1-11 | DEV-05 | Notifications, incidents, ownership and escalation | P1-05 | Correct recipients, no wrong-customer delivery |
| P1-12 | DEV-05 | SLOs, reports, self-monitoring and verified recovery | P1-10, P1-11 | Reproducible SLO/recovery evidence, stale and unknown distinguished |
| P1-13 | DEV-06 | Identity, certificate, network, fleet and retention hardening | P1-04 | Denied trust and rollback tests; holds preserved |
| P1-14 | DEV-06 | Recovery/DR, scale and Feature UAT infrastructure readiness | P1-13 | Technical code/tests complete; independent DR/UAT remains Phase 2/4 |

Estimates: each package is decomposed into 2–3.5 hour active Codex slices after actual source inventory. Do not treat one package as a 2–3.5 hour promise. External infrastructure time and real-provider acceptance are separate.

## Historical roadmap reconciliation
Sprint 12–14/14R credit preserved. Sprint 15 baseline; 16 shared-resource design (correct to Kubernetes shared cluster, not VM); 17–19 identity/telemetry; 20 notifications; 21–22 agent/compute; 23 Kubernetes/cloud; 24–26 integrations; 27–29 topology; 30–31 SLO; 32–33 incident/analytics; 34–39 recovery/scale/lifecycle; 40 comprehensive UAT (Phase 2); 41 resilience and self-monitoring; 42 release decision (Phase 4). Sprint numbers do not establish code completeness. The original roadmap wording is not fully recovered; do not claim verbatim reconciliation.

## Phase 1 definition of done
Every approved feature mapped to code and tests, frontend/backend/database integrated, security and customer-isolation negatives passing, critical coverage/CI policy met, populated-data preservation verified, documentation updated, final main SHA reconciled. Independent UAT and production certification remain distinct and unclaimed.

## Audit backlog
Full main source-level and execution audit still required. This register is a documented starting inventory, not proof that every approved feature is enumerated. Codex should enrich exact source/test paths and provide actual run logs before reporting completion percentage.
