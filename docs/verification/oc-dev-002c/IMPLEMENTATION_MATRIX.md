# Implementation and acceptance matrix

Review date: 2026-11-08 (Asia/Calcutta). Execution logs retain their original UTC timestamps. Tested source `80835f0065de24ebf271fc621b6d1e5e83d73bd2`; main `ffe5ac285ab8aef33a1139bce6f3da79be3d6d33`.


| Workstream | Disposition | Implemented / actual proof | Remaining boundary |
|---|---|---|---|
|A /106,121|PARTIAL|Explicit template pins/overrides in canonical Compute editor; real V1→V2 pin persistence, JSON validation, failed/stale-save persistence and HTTP concurrency/rollback|Structured applicability, immutable attachment/effective history, replacement/retirement semantics BLOCKED|
|B /103,105,106|PARTIAL|Real create/edit/reload, collector identity preservation, disabled/re-enabled state, A/B delayed inventory, viewer/revocation denial, keyboard-only edit/save, desktop/mobile templates|Full keyboard-only creation and modal A/B switch at every save boundary NOT TESTED; no claim every collector method/provider qualified|
|C /135|NOT REPRODUCED|Three bounded real OTLP levels, independently persisted sample/receipt accounting, SQL counts and CPU/RSS|Fleet/Windows load, long duration, all operational pages, all endpoint plans and exact defect reproduction missing|
|D|PARTIAL|Five repeated original resource reload scenarios PASS; route/request timelines and failed attempts retained|Original intermittent cause unproven; no non-blocking owner disposition invented|
|E /121,501|PARTIAL|Main0038 fresh/populated upgrade, refused populated downgrade, drift and full backup/restore PASS|Three PR80 integration conflicts; no reviewed combined candidate or old-writer runtime qualification|
|Supplement|PARTIAL|Evidence-backed legacy classification and ordered14-step tracker|30 numbered journey definitions unrecovered; no unsupported removal or later-step closure|

Changed paths and exact hashes: SOURCE_SHA256.json. Main app changes: api/monitoring.py, schemas/monitoring.py, services/template_resolution.py, ResourceManagementV2.jsx, UnifiedResourceManagement.jsx and the new ResourceTemplateConfiguration.jsx. Other changes are tests/disposable instrumentation only. No applied migrations, permission catalog, collector pin or runtime packaging changed.


**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**
