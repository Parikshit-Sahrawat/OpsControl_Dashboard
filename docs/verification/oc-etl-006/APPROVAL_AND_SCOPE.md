# OC-ETL-006 authority and implementation boundary

2026-11-06 UTC. Product baseline `a915322b5c5c80b0d37dea71f6b7f70237082340`, existing draft PR80, branch `dev/post-pr78-architecture-closure-20261105`.

## Owner authority

Source: the project owner's OC-ETL-006 task in this project conversation, supplied after OC-ETL-005 closure. Exact approval: “The product owner has explicitly approved D01–D06 for design, implementation, additive database migrations and controlled non-production deployment.” This supersedes the earlier pending **product-owner** design/implementation authorization for D01–D06. It does not invent named independent security, DBA, provider, UAT or release signatures. No external approval URL was supplied. The owner is the user issuing that task; an independent identity or review is not inferred.

Selected approved direction: additive immutable binding versions (D01 option B), one current owner/target with multiple explicit method snapshots and no reparenting (D02); separate backend readiness dimensions and no green-on-save (D03); retain existing etl.configure/etl.view permissions and revocation boundary, distinct reviewer for confirmation (D04); expose contextual freshness with a version/evaluation clock (D05); append-only temporal provenance, RESTRICT and refused populated downgrade (D06). No provider execution or new permission catalog is authorized.

## Scope implemented and remaining blockers

This increment implements a **temporal native identity claim registry**, staged same-target reader replacement/retirement, history UI, receipt constraints and fail-closed routing, and six backend dimensions. It does not call an operator-entered namespace a verified native authority. The `NATIVE_AUTHORITY_CLAIM_V1` tuple includes platform, environment, explicit authority claim, object kind JOB and the persisted PipelineJob.native_id. Display names are never keys. Hash and tuple unique indexes reserve current claims. Two aliases for an unknown external namespace cannot be proven to denote one provider object without D09 evidence. Thus *qualified cross-surface native ownership is not certified*.

Current capability proofs establish reader/source evidence, not a generic attestation of the new cross-method authority namespace. No authoritative provider-to-namespace mapping or approved target proof was supplied/recovered. Confirmation checks separation of duty and current runtime eligibility, then refuses missing D09 certification. There is no producer/client verified flag or successful confirmation route until that prerequisite has a reviewed implementation. Real verified binding confirmation, active-reader cutover, positive binding-receipt routing and aggregate activation remain BLOCKED / NOT TESTED. Their reserved schema is not a claim of implementation completeness. Existing approved source handoff remains the required path for active readers; no alternate cutover is enabled.

The source/reader replacement implemented here changes **STAGED configuration only**, with no selected/enabled integration, enabled legacy collector, in-flight source lease, or legal/manual/continuity hold. Same-target identity and immutable parents are preserved. Active-native changes refuse and require separately reviewed handoff. This is a deliberate bounded subset, not a claim that D01–D06 Definition of Done is fully satisfied.

D07 recurrence/calendar and D08 long-running threshold remain unresolved. D09 genuine-provider proof and independent UAT remain separate. D10 gates remain CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.
