# Production readiness — NOT READY

Approval, implementation, controlled verification, independent UAT and certification remain separate. All seven release gates remain mandatory: functional UAT; security/customer isolation; real integration acceptance; telemetry reliability; performance/capacity; recovery/operations; independent evidence-backed sign-off. Initial inventory p95<500ms is an engineering target subject to approved representative workload, not a promise.

| Gap | Evidence credited /14R change | Remaining exit / owner dependency |
| --- | --- | --- |
| P0-01 Genuine Pentaho runtime | Existing native artifacts and correctness regression retained | RT001–020 NOT RUN; real build, authorized read-only credentials and witness; native child identity UNVERIFIED |
| P0-02 Telemetry continuity | Existing fenced ingestion/partial-evidence corrections reused | Whole-path durability/backpressure/loss accounting and representative sustained sources |
| P0-03 Shared infrastructure | Existing customer-negative controls retained | One canonical VM in both authorized customer views remains unsupported; explicit association/attribution design approval first |
| P0-04 Recovery/resilience | Existing REC01–06/populated migrations reused and applicable gate rerun | Encrypted/offsite/WAL-PITR/key custody/failure-domain drill; actual RPO/RTO, not targets |
| P0-05 Credentials/certificates | Existing token/identity checks retained | Provider CA and real OS issuance/expiry/renewal/revocation/rotation |
| P0-06 Network trust | New controlled deployment decision record; existing local TLS evidence | Private VPC/DNS/ingress/egress/proxy/VPN/CA tests; no CrowdStrike/Zscaler certification |
| P1-01 Fleet RBAC/query scale | Existing multi-customer/deny/revocation regression reused | Representative measured fleet/query/authority-lock workload; local API p95 812ms exceeds500ms engineering target despite passing existing2000ms runtime gate |
| P1-02 External-client scope | Existing explicit owned clients retained | Third-party migration and acknowledgment, no insecure omitted-scope fallback |
| P1-03 Large inventories | Existing scoped505/505/75 pagination cases reused | Snapshot semantics during concurrent mutation, graph/aggregate bounds and representative benchmarks |
| P1-04 Topology integrity | Existing scoped FK/cycle/history checks retained | Shared-resource design and authorized version/freshness/as-of provenance |
| P1-05 SLO correctness | Existing reporting is not a complete SLO engine | Approved denominator/policy/version/provenance and repeatable evidence; original IMP059/060 source absent |
| P1-06 Fleet lifecycle | Existing multiple-method/configuration/fence behavior retained | Real Windows/Linux/container canary/install/upgrade/rollback |
| P1-07 Notification delivery | Existing scoped delivery/retry/idempotency checks retained | Real provider sandbox, authorized escalation/support-window acceptance |
| P1-08 Platform acceptance | Existing nine-platform classifications/contracts retained | Exact provider/build/method acceptance; no fixture-based certification |
| P2-01 Operational usability |14R fixes720px offset and adds focus/contrast/tables/light-dark browser checks | Independent exact-revision UAT, assistive technology and shift workflows |
| P2-02 Efficiency/cost | Existing bounded intake/holds retained | Cardinality/storage/residency budgets, Agent log rotation and aggregate profiling |

AUD01 bounded history was corrected before14R; AUD02 aggregate materialization, AUD03 browser enrichment and AUD04 authority lock remain measured-performance follow-ups. AUD05 full data-path readiness, AUD06 legacy method attribution policy, AUD07 original source/SLO governance and AUD08 deployment/DR certification remain tracked in the unchanged [audit evidence](../arch-etl-001-v16-r1/sprint10/CODE_AUDIT_FINDINGS.md). Neither missing certification nor future implementation is reclassified as a new Sprint14 defect.

[18 requirement declarations](IMPROVEMENT_REGISTER.md), [source/approval gaps](GOVERNANCE_RECONCILIATION.md) and [roadmap](ROADMAP_RECONCILIATION.md) remain explicit. No production deployment/database/source exists or was touched by this work.
