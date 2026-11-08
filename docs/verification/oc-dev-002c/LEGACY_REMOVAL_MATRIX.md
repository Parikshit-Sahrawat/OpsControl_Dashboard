# Legacy removal matrix

Review date: 2026-11-08 (Asia/Calcutta). Execution logs retain their original UTC timestamps. Tested source `80835f0065de24ebf271fc621b6d1e5e83d73bd2`; main `ffe5ac285ab8aef33a1139bce6f3da79be3d6d33`.


|Candidate|Decision|Changed code/dependencies|Preservation|Automated proof|Disposition|
|---|---|---|---|---|---|
|Excluded Kubernetes monitoring|Prior removal retained|No new operational module deletion; scope fences unchanged|All legacy tables/FKs/audit/migrations retained|Final release retired EKS/nested platform/legacy remote rejection and full restore|Existing scope enforced; no new removal claimed|
|Service Catalog|Excluded, no active implementation found|No shared service/process/monitoring code removed|No data changes|Static journey/source inventory only; no runtime deletion to certify|No-op, not a newly verified removal|
|Standalone legacy ResourceManagementV2 wizard/editor|MODERNIZE / defer removal|Organizations/collectors still shared; new panel uses canonical Compute editor/API|No attachment/source history deleted by cleanup|Current real browser source/collector/template flows PASS; removal not performed|Requires approved exact replacement/call contract|
|Legacy ETL/native receipt paths|RETAIN|PR80 migration/authority dependencies unmerged|IDs/history/checkpoints/fences preserved|Main scope/HTTP/restore regressions; PR80 combined runtime BLOCKED|No removal|
|History, guards, deployment infrastructure and retired-channel rejections|RETAIN|Required safety/data/build dependencies|No destructive change|Scoped source/hash diff and preservation/security tests|No removal|
|Ambiguous other legacy code|AUTHORITY_PENDING|No arbitrary deletion from keyword search|Unchanged|Inventory only|Owner decision needed|

**New functionality-removal count:0.** This is an evidence-backed no-op cleanup disposition, not manufactured deletion progress. Existing0038 and prior scope-removal evidence are unchanged. The supplemental authorization requires demonstrable exclusion/supersession and safe dependencies; no additional candidate met all conditions within this slice. Future removal must identify exact journey authority, live call graph, affected API/schema/permission/model dependencies, preservation/export/recovery contract and regression acceptance first.


**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**
