# Development Architecture and Roadmap Reconciliation v1.0

Baseline: main 65aa13114bdfe4a57e2bb3b396f822bd81090b38 (PR #41 merged). This is a planning reconciliation, not an execution certification.

## Binding approved ownership rules
- Resource Management -> Organizations means monitored external customers. Each VM/EC2 belongs to exactly one customer. Do not model one VM as shared across customer organizations.
- Access Management -> Departments/Teams means provider employees and internal operational units; never equate these to customer organizations.
- A Kubernetes cluster may be shared by explicitly authorized customers; cluster-level association does not imply every customer can see every node, namespace, workload, telemetry record, alert or incident. Enforce workload/namespace-derived tenant attribution, negative scope tests, and quarantine ambiguous evidence.
- Resource Management is the sole configuration/inventory control plane. Data Pipelines, Compute Instances and API Endpoints are operational monitoring views. Do not duplicate create/edit flows in monitoring sections.
- Pentaho and other native pipeline adapters are read-only monitoring, not execution controls. Preserve platform-native types and immutable version-aware compatibility profiles.
- Settings & Help: user profile/preference surfaces, admin-authorized platform settings, user manual, technical docs, provider SOPs/runbooks, FAQ. Restrict internal SOPs and admin mutations.
- ARCH-001: method-specific canonical collection identity, one fenced active owner per collection unit; identity conflicts quarantined; legal holds block protected permanent deletion but not safe detach/retire; shared-source suspension retains approved affected-resource preview.

## Supersession ledger
| Historical statement | Resolution | Verification obligation |
| --- | --- | --- |
| Shared VM / multi-customer VM association in Sprint 12/16/27–29 and historical P0-03 | SUPERSEDED for VM/EC2 by exclusive customer ownership; shared-resource scenarios apply to explicitly authorized Kubernetes clusters | Inspect models, constraints, API, telemetry, browser customer selection and negative tests |
| Sprint 14R unchanged 80% backend coverage versus PR #41 description lowering gate to 65% | POLICY CONFLICT; PR #41 merged but 80% was earlier approved and no new owner approval for 65% established in this conversation | Identify active CI threshold, compare original approval, obtain explicit policy decision or restore 80%; run current main coverage |
| PR #41 pending in older planning files | SUPERSEDED: merged into main 65aa13114bdfe4a57e2bb3b396f822bd81090b38 | Run current-main technical validation; do not re-merge |
| Sprint 40 formal independent UAT during development | MOVE ACCEPTANCE to Phase 2; implementation test infrastructure may be coded during Phase 1 | Separate implementation complete from independently accepted |
| Sprint 42 controlled adoption/release decision during development | MOVE RELEASE to Phase 4 | Preserve seven release gates and explicit owner authorization |
| Older sprint labels imply full feature delivery | NOT EVIDENCE OF COMPLETION | Feature-to-source/test/DB/UX traceability at exact SHA |

## Historical sprint mapping (planning only)
- Historical 12–14R: preserve delivered implementation credit, not acceptance claims.
- 15: baseline integrity and register reconciliation (DEV-01).
- 16: Kubernetes shared-cluster associations and authorization (DEV-04); exclusive VM rule retained (DEV-03).
- 17–19: certificates, durable telemetry, clocks and attribution (DEV-02/06).
- 20: notifications and escalation (DEV-05).
- 21–22: agent/collector lifecycle and real VM monitoring (DEV-02/03).
- 23: cloud/Kubernetes/private connectivity (DEV-04/06).
- 24–26: Pentaho, API/TLS and nine adapters (DEV-03).
- 27–29: scoped topology/history/scale (DEV-04).
- 30–31: SLO evidence and policy versioning (DEV-05).
- 32–33: incidents, service ownership and analytics (DEV-05).
- 34–39: DR, fleet, inventories, external clients, cost and retention (DEV-06 with DEV-02/04 dependencies).
- 40: formal independent operational UAT (Phase 2), with tooling preparation in DEV-06.
- 41: soak and self-observability (DEV-06; acceptance spans Phases 2–4).
- 42: evidence-based release decision (Phase 4).

This mapping supplements docs/verification/sprint14r/ROADMAP_RECONCILIATION.md and the detailed linked 31-sprint reference. The original full roadmap text remains incompletely recovered. Do not rewrite historical approvals as if they were always Kubernetes-only.

## Bounded delivery and gates
One active primary workstream; 2–3.5 active Codex hours per slice, not per entire feature. Implement and test each slice, capture exact SHA/paths and CI evidence, then move to next. Critical security, tenancy, deletion, legal hold, migration and data preservation changes require explicit negative tests and a preservation gate. Do not claim independent UAT or production readiness during Phase 1.

## Audit completion checklist
Expand every register row with concrete frontend/backend/model/migration/test paths and exact command evidence. Split UI-001–023, OC-IMP-001–018, AUD01–08, nine adapter profiles and approved settings/help capabilities into individual rows where exact source wording is recovered. Mark unrecovered original IMP-001–062 as SOURCE_NOT_RECOVERED rather than inventing them.
