# Read-only monitoring boundary review

Review date: 2026-11-08 (Asia/Calcutta). Execution logs retain their original UTC timestamps. Tested source `80835f0065de24ebf271fc621b6d1e5e83d73bd2`; main `ffe5ac285ab8aef33a1139bce6f3da79be3d6d33`.


Owner rule: OpsControl configures only its own monitoring behavior; monitored workloads are read-only. Modified routes attach/edit/detach policy records and resolve package configuration; new UI calls only those and existing source/resource APIs. No process/service/ETL workload action, scheduler write, remote shell or arbitrary script endpoint was added. Collector Start/Stop references in existing code concern OpsControl's own collection lifecycle, not workload control.

New unit test_sprint_monitoring_only.py accepts observation selectors (sshd/python) and rejects remote_command, service_action, restart_process and etl_retry as extra fields in VM registration; service_action rejected in monitoring parameter schema. Real authenticated browser HTTP repeats four prohibited payload fields with422 and the exact redacted errors[].loc/type contract. Existing backend configuration/secrets/TLS/egress/RBAC guards unchanged.

This is bounded review of changed surfaces, not a claim that every arbitrary package key is rejected: legacy free-form package JSON can contain inert unknown metadata. No new interpreter/executor for it was introduced. Provider readers remain unqualified until separately authorized; no genuine endpoint queried. Synthetic test permissions/transport cannot establish qualified provider health. Version/pin and D07/D08 unchanged; no production rollout or security waiver.


**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**
