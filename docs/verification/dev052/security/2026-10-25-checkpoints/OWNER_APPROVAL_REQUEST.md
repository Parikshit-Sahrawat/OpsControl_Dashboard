# Accountable checkpoint recovery review request

**Status: PENDING. No signatures, risk acceptance or production approval.**
Review code commits `9f10022e79e0a5f5f3e492fde5045d3cd004292f` and
`5c7f1b519076784924b071222a511ec179390a1b`, the operator runbook and final
`lab-attempt-4/` evidence. Automated technical review by Codex is not owner signoff.

| Accountable owner | Concrete decision / evidence needed | Status |
|---|---|---|
| Collector/runtime owner | Review complete-state backup, format boundaries, atomic exchange/journal resume, live-writer refusal, direct-runtime fixture limits and unresolved CHK-001/CHK-002. Decide whether this narrowly bounded recovery design is supportable. | UNASSIGNED / PENDING |
| Data/operations owner | Attest independent ID inventory and retention completeness through the maintenance cut; confirm legacy-cut provenance, sensitive-backup custody, unchanged config/method/source paths and service UID. Approve measured duplicate/downstream effects or block replay. | UNASSIGNED / PENDING |
| Storage/platform owner | Qualify actual local filesystem, flock/rename-exchange/fsync behavior, available capacity and service stop/pre-start procedures. Physical power-loss, other filesystems/OSes and large/other-signal states are not certified. | UNASSIGNED / PENDING |
| Security/release owner | Review the 16-ID interrupted-upgrade delivery gap, finite 44-ID recovery with 56 duplicate rows, and pending-journal service integration. Require remaining transition/rollback criteria before any separate version-guard/pin change. Existing strict release gates stay blocking. | UNASSIGNED / PENDING |

Requested approval is for a clearly scoped maintenance/recovery procedure **only
after review**. This document requests no vulnerability waiver, unrelated
remediation, final image publication or DEV-05.2B transition. Until accountable
decisions and unresolved tests are addressed: default 0.123.0, promotion/security
BLOCKED and release NO-GO.
