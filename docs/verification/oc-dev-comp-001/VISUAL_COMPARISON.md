# Approved-reference visual review — 2026-11-08

Actual supplied image received, viewed and preserved: [PNG](../../design/references/OpsControl_Approved_UI_Admin_Reference.png), [original JPEG](../../design/references/OpsControl_Approved_UI_Admin_Reference.original.jpg), [hashes/pixel-equality provenance](../../design/references/REFERENCE_PROVENANCE.json). The PNG is lossless encoding of the supplied JPEG's decoded pixels, not a claim that the owner uploaded original PNG bytes. No generated replacement image was used.

Compare actual running application captures:

- [Admin1366](evidence/final-workspace/admin-resources-1366.png), [Admin1920](evidence/final-workspace/admin-resources-1920.png).
- [Tablet768](evidence/final-workspace/admin-resources-768.png), [Mobile390](evidence/final-workspace/admin-resources-390.png).
- [Operator1366](evidence/final-workspace/operator-resources-1366.png), [Operator390](evidence/final-workspace/operator-resources-390.png).
- [Dark1366](evidence/final-workspace/admin-resources-dark-1366.png), [Dark390](evidence/final-workspace/admin-resources-dark-390.png).
- [Actual template catalogue](evidence/final-workspace/admin-template-catalogue.png), [pinned template mobile editor](evidence/final-workspace/template-mobile.png).

| Reference element | Candidate comparison / difference |
|---|---|
| Navy left rail, blue active pills, light canvas | Implemented reusable224/64px sidebar, mobile drawer, actual allowed destinations and source controls; no excluded Incidents entry |
| Dense thin utility row | Actual source search/CtrlK, notifications, profile, Help, theme. Timezone/density collapse into Display at ordinary widths; organization/environment selectors remain operational-context controls while Resource Management has independent explicit customer/environment filters |
| Compact readable typography and cards | System font13–14px,24px heading,12px card corners, blue accent; larger readable spacing than the1280×720 reference's compressed dashboard |
| Quick filters | Real customer/environment/resource-name/configuration-state/chips/reset/apply; URL persistence and backend validation. Deep telemetry filters explicitly deferred rather than empty faux selectors |
| KPI/chart/configuration/rollout panels | Resource inventory counts and role access only in this Sprint1 workspace. Reference's fictional CPU/API/ETL/alert numbers, rollout and trend visuals deliberately not displayed. Later telemetry/report sprints must provide authoritative data/contracts |
| Selected-resource/template details | Existing real detail and authorized configuration editors, saved effective JSON and actual committed package history; no fake dry-run/attachment-history/rollback UI |
| Responsive and role adaptation | Admin/operator screenshots at390/768/1366/1920; no page horizontal overflow asserted. Wide inventory itself scrolls, keyboard-focusable. Long names truncated with full accessible/title text; viewer uses same data components without mutation controls |

Review is **qualitative against actual supplied pixels and text**, not pixel-identical certification. No computed visual-similarity percentage or owner visual signoff is claimed. Two failed screenshots are preserved, including overlap/overflow fixed during development. Separate exact operator-reference approval and formal owner visual acceptance remain Pending.
