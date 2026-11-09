# Legacy feature inventory and journey authority

Review date: 2026-11-08 (Asia/Calcutta). Execution logs retain their original UTC timestamps. Tested source `80835f0065de24ebf271fc621b6d1e5e83d73bd2`; main `ffe5ac285ab8aef33a1139bce6f3da79be3d6d33`.


Source baseline main `ffe5ac285ab8aef33a1139bce6f3da79be3d6d33`, PR80 `958193f266c89302b2f1919e3703faece591e0af`, PR81 `af9bad0428dd4023829e210cb923d32fa0adba3c`, PR82 start `2fbb959d5653f9a325651212f9c3555e9ccc5efe` and final source above. `journeys-source.txt` preserves the exact PR80 journey matrix; `backlog-source.txt` planning baseline and `scope-decision-source.txt` owner-accepted Kubernetes scope authority.31 journeys included,20 Service Catalog excluded,32 skipped.30 included numbered definitions are SOURCE_NOT_RECOVERED; no arbitrary capability-to-number mapping or deletion authority is invented. Journey33 recovered design statements still have unresolved detailed acceptance. PR80 feature/model changes remain unmerged, not assumed present on main.

| Legacy family / paths | Classification | Authority/dependency assessment |
|---|---|---|
|Kubernetes/EKS/AKS/GKE/OpenShift operational adapters/UI|REMOVE (already removed on main; no new deletion)|Owner-accepted OC-SCOPE-REM-001, Journey32 skipped. Existing Source Change/Final Acceptance reports historical; negative routes/tests remain fences|
|excludedPlatforms.js, excluded_platforms.py, retirement probes/tests|RETAIN|Prevent reactivation through nested/aliased inputs; removal would weaken explicit owner scope|
|entities.py legacy cluster/association records, migration0038|RETAIN|Historical customer/audit data and applied migration preservation; no schema retirement authorization|
|OpsControl deployment packaging/manifests|RETAIN|Supplement expressly permits Kubernetes deployment of OpsControl itself; not monitored Kubernetes product capability. No active deployment manifest removed|
|Service Catalog|REMOVE (excluded; active implementation not found)|Journey20 excluded. Search absence is not a new removal or permission to delete shared service/process observations|
|ResourceManagementV2 DataSourceWizard/TemplateEditor and old standalone tabs|MODERNIZE|Canonical caller UnifiedResourceManagement embeds organizations/collectors. Shared collector/organization ownership still active. Full default standalone call shape and historical wizard assumptions require approved convergence; no wholesale deletion|
|UnifiedResources legacy ETL/config routes, PipelineJob/JobOrder identities|RETAIN|Supported read-only monitoring and immutable IDs/history; PR80 adds temporal binding/writer fences. No native scheduler/workload controls allowed|
|Pentaho Carte/status/log readers|RETAIN|Approved monitoring-only ETL boundary. Real scheduler/Carte authority/provider-build qualification remains blocked; legacy read evidence not retired merely due new models|
|Old enrollment/config/method references|MODERNIZE|Preserve source IDs, generation/fence relationships and old-writer compatibility. Review before replacing legacy routes|
|PagerDuty/ServiceNow historical fields/evidence|RETAIN rejection/history; AUTHORITY_PENDING any reactivation/removal|Current notifications worker supports approved transport branches then raises Unsupported or retired notification channel. Existing release tests verify retired ITSM rejection. No reintroduction or deletion of audit/provenance|
|Collector runtime/0.123.0 guard and recovery utility|RETAIN|CHK001/002 independent gates; no cleanup/refactor authorized here|
|Historical reports/fixtures/malformed retired-EKS exports|RETAIN|Audit provenance, negative coverage and raw failure evidence; not product support|
|Other unmatched proposals/30 unrecovered journey definitions|AUTHORITY_PENDING|Owner must supply authoritative descriptions before removal; missing files are not approval|

Inventory inspected frontend navigation/call sites/components, backend routes/services/workers, model relationships, migration graph, permission catalogue, tests/CI and current/historical docs. Raw source search is legacy-source-search.log; generic container/deployment/service/namespace terminology is not a deletion criterion. Journey32 Kubernetes/container-monitoring remains excluded. Docker packaging and Kubernetes deployment of OpsControl itself are permitted; generic historical telemetry labels do not re-enable monitored container platforms. No new packages or permissions removed. No shared dependency/customer-data change. Broader cleanups are deferred until authority and tests exist.


**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**
