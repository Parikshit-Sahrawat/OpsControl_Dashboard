# OpsControl Phase 2 — Architecture and Detailed Design

**Status:** DRAFT for design review | **Based on:** Phase 1 branch `docs/sdlc-phase-1` and its [evidence-backed handoff](../09-PHASE1-HANDOFF.md).

Phase 2 designs the fixes and integrations needed to turn the existing control-plane UI into safe, operational monitoring. These are **proposed interfaces and architecture decisions**, not claims of implemented code or approved production deployment.

## Design pack
- [01 — System architecture](01-ARCHITECTURE.md)
- [02 — Identity, RBAC and organization isolation](02-TENANCY-SECURITY.md)
- [03 — Template activation and monitoring runtime](03-MONITORING-ACTIVATION.md)
- [04 — Domain and database design](04-DATA-MODEL.md)
- [05 — API and event contracts](05-API-CONTRACTS.md)
- [06 — Test and verification strategy](06-VERIFICATION.md)
- [07 — Architecture decision records](07-ADRS.md)
- [08 — Implementation sequencing and exit gate](08-IMPLEMENTATION-PLAN.md)

## References
- SRS [DOC-02](../02-SRS.md) — requirements FR-001–FR-019 and NFR-001–NFR-012.
- Audit [DOC-07](../07-CODE-AUDIT.md) — static/runtime findings and verified evidence.
- [Confirmed staging execution](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/actions/runs/37987379543) — migrations, API, manual sample and 11 real browser captures.
- Issues #2, #3, #4, #5, #6, #7, #8, #9, #10, #11, #14.

## Review rules
Every proposed endpoint and entity must be mapped to an SRS requirement, migration plan, test and threat boundary. Do not implement or deploy designs as if already approved. Avoid production identifiers and secrets in this public repository.

**Phase 2 exit:** approved architecture diagrams, ERD, role-permission matrix, API contracts, collector activation contract, error/retry model, security design, test strategy, and implementation backlog with acceptance criteria.
