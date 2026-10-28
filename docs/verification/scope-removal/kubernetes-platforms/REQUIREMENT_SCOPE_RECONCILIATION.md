# Scope reconciliation

Owner instruction OC-SCOPE-REM-001 removes Kubernetes/EKS/AKS/GKE/OpenShift and other distributions. K8S-01/K8S-02 canonical rows now REMOVED_FROM_SCOPE. Kubernetes portions of OC-IMP-017 and derived UI proposals are excluded; no unrelated requirement ownership is changed. REMOVED_FROM_SCOPE is scope disposition, not implementation completion.

Canonical register and architecture documents retain historical wording with an explicit superseding scope decision. README states exclusions. Stage2 draft PR70 remains untouched; its Kubernetes scope/gaps are now historical planning context and should consume this decision on its next authorized reconciliation. PR69 and durability gates untouched. Remaining documentation examples must not be interpreted as supported platforms; complete current-guide cleanup remains pending.
