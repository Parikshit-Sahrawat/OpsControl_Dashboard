# OpsControl SDLC Documentation — Phase 1 Baseline
Status: **DRAFT — review required**. Date: 2026-10-10. Branch: `docs/sdlc-phase-1`.

## Lifecycle
1. Discovery and requirements (this phase)
2. Architecture and detailed design
3. Core product implementation
4. Monitoring integrations and operational workflows
5. Verification, security, and performance testing
6. Packaging and DevOps delivery
7. Release, operations, and iterative maintenance

The phases are governance gates, not a prohibition on iterative development. Work proceeds in reviewable increments with acceptance criteria and tests.

## Phase 1 artifacts
- [Project Charter](01-PROJECT-CHARTER.md)
- [Software Requirements Specification](02-SRS.md)
- [Current-State Assessment](03-CURRENT-STATE.md)
- [Product Requirements and Journeys](04-PRD.md)
- [Roadmap and Review Gates](05-ROADMAP.md)
- [Requirements Traceability](06-TRACEABILITY.md)

## Working rules
- GitHub contains versioned technical specifications and code.
- GitBook may publish approved docs; Linear may track implementation after requirements review.
- Existing documents under `docs/` are source material, not automatically proof of tested implementation.
- Avoid production credentials and customer data in public repository documents.
- No application behavior changes are included in this documentation PR.
- Do not merge until scope, priorities, acceptance criteria, and security constraints are reviewed.
