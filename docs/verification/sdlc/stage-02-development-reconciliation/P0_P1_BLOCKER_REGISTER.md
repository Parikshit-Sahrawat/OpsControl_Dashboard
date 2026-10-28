# Dependency and blocker register

Severity denotes gate impact, not proof of a newly reproduced defect. No owner UAT results supplied; no UAT defect invented. Historical AUD findings require disposition review, not automatic reopening.

| ID | Requirements | Responsible canonical workstream | Gate / condition | Resolution prerequisite and acceptance |
|---|---|---|---|---|
| P0-01 | TEL-03 | DEV-02; DEV-05 hardening | Native persistent queue loss | Upstream support, transaction invariant, approved candidate; N1–N4 zero missing admitted IDs with independent receipts |
| P0-02 | TEL-01/TEL-03 | DEV-02; DEV-05 hardening | CHK-002 rollback | Depends on supported binary/schema; populated queue and checkpoint rollback separately proven |
| P0-03 | PLT-01 | DEV-06 | Migration preservation evidence | Historical disposable preservation credited; require current0038 populated upgrade/downgrade evidence, no blanket historical defect reopening |
| P0-04 | AM-01/CMP-02/K8S-01 | DEV-01/03/04 | Isolation/security gate | Current scoped association/fencing negatives and independent reviewer; no confirmed new leak asserted |
| P0-05 | PLT-03 | DEV-06 | Independent security certification | Issue18 and draft69 security findings; exact images/scans/licenses and accountable review |
| P0-06 | PLT-02 | DEV-06 | Mandatory CI tracking | Latest captured main green; preserve required checks; no current red defect established |
| P1-01 | RM-02/UI-007/UI-023 | DEV-01 | Activation/workflow verification | Reproduce exact-source draft/template activation before fixes; DEV05-001 already fixed |
| P1-02 | RM-05/TEL-02 | DEV-02 | Scheduling/concurrency/receipt completeness | Approved attribution contract; concurrent ownership and restart evidence |
| P1-03 | DP-01/DP-02/CMP-01/API-01 | DEV-03 | Genuine provider readiness/freshness | Authorized Windows/Linux/Pentaho builds and independent evidence; synthetic fixtures insufficient |
| P1-04 | OPS-01/OPS-02/OPS-04 | DEV-05 | Alert/incident/integration contract | Owner-approved escalation/SLO semantics; delivery and correlation negatives |
| P1-05 | RM-03/AM-02/AM-03/HELP-01/SET-01 | DEV-01 | UI/profile/help evidence | Exact-SHA independent UAT; no anticipated defect creation |

CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO
