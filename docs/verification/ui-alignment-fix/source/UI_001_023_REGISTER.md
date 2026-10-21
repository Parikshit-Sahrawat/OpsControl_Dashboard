# OpsControl Dashboard — UI Alignment Fix Register (UI-001–UI-023)

Status: Approved by user on 2026-10-20. Reconstructed from approved project discussion; not asserted to be an existing repository file.

| ID | Requirement | Priority |
|---|---|---|
| UI-001 | Expandable/collapsible sidebar navigation groups, active routes, keyboard/mobile support, and preference persistence | P1 |
| UI-002 | Replace Resource Management horizontal tabs with a clearly grouped component selector/dropdown | P1 |
| UI-003 | Replace Compute Instance onboarding modal with a full-page configuration workspace | P0 |
| UI-004 | Provide a vertical desktop stepper for the 10-step Compute onboarding journey and compact mobile navigation | P1 |
| UI-005 | Eliminate overlaps, clipping, inconsistent spacing, and misaligned form controls | P1 |
| UI-006 | Standardize Previous, Continue, Save Draft, validation, and primary actions; remove duplicate Next buttons | P0 |
| UI-007 | Investigate and resolve `Data source not found` / `Not Found` onboarding errors without masking backend failures | P0 |
| UI-008 | Support independently configured collection methods for one VM-associated OpsControl Agent | P1 |
| UI-009 | Implement meaningful backend-confirmed readiness validation before monitoring activation | P0 |
| UI-010 | Preserve distinction between monitored customer organizations and internal employee departments | P0 |
| UI-011 | Preserve Resource Management as configuration/inventory and Operations as monitoring/investigation | P0 |
| UI-012 | Verify desktop, tablet, mobile, light theme, and dark theme | P1 |
| UI-013 | Correct Data Pipeline/Pentaho configuration layout, labels, credential references, responsive fields, and stepper | P1 |
| UI-014 | Correct Access Management explicit access-boundary form layout and scope/permission grouping | P1 |
| UI-015 | Improve Department → Employee → Permissions workflow and effective-permission readability without changing RBAC | P1 |
| UI-016 | Improve Dashboard information hierarchy and empty states; do not treat valid zero-data states as defects | P2 |
| UI-017 | Distinguish Compute Health operational adapter evidence from resource inventory | P2 |
| UI-018 | Improve Data Pipeline inventory tables, column readability, typography, and responsiveness | P2 |
| UI-019 | Distinguish registered API Endpoints from operational service-probe evidence | P2 |
| UI-020 | Improve Alerts filter labels and toolbar consistency, without expanding deferred Alerts redesign | P2 |
| UI-021 | Correct Incidents pagination and record-count alignment | P2 |
| UI-022 | Improve Resource Management nested navigation for Event Parameters and Alert Rules | P1 |
| UI-023 | Standardize stepper interaction and presentation across Compute and ETL configuration journeys | P1 |

## Scope authority

- UI-001–UI-012 previously approved.
- UI-013–UI-023 explicitly approved on 2026-10-20.
- Entire UAT Test 1 text explicitly approved on 2026-10-20, including functional workflow changes and removal of redundant Data Pipeline Integration/create UI while preserving registrations and retaining legacy creation.
- UAT Test 1's `#Alerts — For now ignore` excludes a full Alerts page redesign; maintain existing Alerts functionality and necessary cross-page links.

## Original UAT Test 1

See `UAT_TEST_1_UI_ALIGNMENT_FIX.txt` in the same directory. Its text is copied verbatim from the user-uploaded source.
