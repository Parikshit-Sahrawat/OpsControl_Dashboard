# Migration preservation and PR80 convergence

Review date: 2026-11-08 (Asia/Calcutta). Execution logs retain their original UTC timestamps. Tested source `80835f0065de24ebf271fc621b6d1e5e83d73bd2`; main `ffe5ac285ab8aef33a1139bce6f3da79be3d6d33`.


Main migration head remains0038_k8s_cluster_associations; no migrations or preservation guards changed. Final V1.6 harness verifies fresh/populated upgrade, drift check, supported empty downgrade/re-upgrade and unsafe populated refusal before schema damage. All100 tables' content hashes, columns/FKs and migration identity compare with restored DB; source unchanged after export. Final broad release independently restores100 tables/1197 rows/499 constraints, including audit immutability, backup checksum/corruption/nonempty-target refusal and template references. Raw dumps contain only isolated synthetic data, no shared customer data. PostgreSQL17.11 and exact local image identity are recorded in postgres-version.txt/release-final cleanup.json.

PR80 `958193f266c89302b2f1919e3703faece591e0af` retains0039_etl_workflow_foundation→0040_etl_native_bindings→0041_etl_authority_writer on0038. Source hashes in convergence.json were extracted without applying migrations. git apply --check of the complete Sprint1 code patch against its private detached tree exits1 in schemas/monitoring.py, scripts/v16_api_probe.py and frontend/package.json. No merge/cherry-pick/renumber/schema alteration occurred. This is textual compatibility failure, not proof a database upgrade fails.

Non-destructive convergence plan for separately approved integration: review strict input/revision changes alongside PR80 native contracts; union HTTP probes and npm test entries without dropping security/ETL cases; retain scope registry, native writer fences and rollback guards; build an immutable combined candidate. Upgrade isolated main0038 populated fixtures through PR80 originals0039–0041, verify identities/audit/receipt hashes, old-writer refusal, concurrent DAG locks, backup/restore and unsafe downgrade refusal. Do not treat old-image health200 as rollback compatibility. Any future template-history revision follows the approved integrated graph and reviewed schema contract, not a competing renumbered0039.

Current #82 branch descends from unchanged main; future PR80 conflicts do not themselves prove #82 is unmergeable. Runtime convergence/older-binary rollback remain BLOCKED pending approved combined source. Existing attachment records/package versions are restored; immutable attachment history cannot be tested because no such model exists. No destructive retirement of retained Kubernetes records.


**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**
