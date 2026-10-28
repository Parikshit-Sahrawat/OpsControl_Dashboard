# Removal inventory

Baseline `09a578f70282c7889a515c332c948f1940ae6719`; implementation `274175850c8553ecbf27d8cb0e7a2d9f5136a9da`. Case-insensitive tracked repository search includes all requested terms; raw line results before/after and per-file inventory.json retained. Generic deployment/namespace/pod word matches do not alone authorize removal. Complete semantic classification remains INCOMPLETE for shared infrastructure/current documentation references.

Removed dependency chains:
- Resource Management cluster list/detail/revoke schema and routes → cluster models (models retained for history).
- Discovery scan/import → EKS/Kubernetes readers → optional Kubernetes SDK. Only EC2 discovery remains advertised.
- Collector adapter registry → KubernetesAdapter → kubernetes_health removed.
- Infrastructure Kubernetes config validator/metric family removed.
- UnifiedResourceManagement imported EKS drawer → ImportedDiscoveryInventory removed.
- New DataSource/Collector schemas and activation reject removed platforms; old worker retirement fences retained and expanded.

Retained: three legacy cluster models, customer association scope fences, migration0038, historical source/evidence rows, old tests requiring reconciliation; generic Docker/CI/deployment retained. ResourceManagementV2 contains historical EKS rendering branches behind exclusion filtering; these are remaining dead-code cleanup, not acceptance-complete removal. Shared safe evidence fields still include namespace/workload names and require compatibility review before removal.
