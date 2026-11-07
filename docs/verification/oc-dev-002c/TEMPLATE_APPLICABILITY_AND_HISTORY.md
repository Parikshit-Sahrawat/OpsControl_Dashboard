# Template applicability, versioning and history contract

Review date: 2026-11-08 (Asia/Calcutta). Execution logs retain their original UTC timestamps. Tested source `80835f0065de24ebf271fc621b6d1e5e83d73bd2`; main `ffe5ac285ab8aef33a1139bce6f3da79be3d6d33`.


Current authority: main models/entities.py MonitoringTemplate/Version/Attachment and service template_resolution.py; planning PR81 `af9bad0428dd4023829e210cb923d32fa0adba3c` OC-DEV-106; scope approved by OC-DEV-002C. Templates are a shared catalogue, `scope` is free text, versions preserve package JSON, attachments are mutable and detach physically removes the attachment. CONFIG_MUTATION audit records route-level actions; it is not a complete override/effective-config timeline. No approved compatibility matrix or retention/deletion contract was recovered from these sources.

Implemented and verified: selected V1 survives V2 commit; current overrides and effective configuration survive reload; malformed packages/unknown ownership fields fail closed; inactive template cannot attach/re-enable; committed version required; source serialization and opt-in timestamp revision conflict200/409; injected PostgreSQL UPDATE failure leaves persisted attachment/effective configuration unchanged. New editor uses the same scoped backend and version rows. Successful save does not activate monitoring or assert HEALTHY. Existing package versions1–4 retained in real HTTP checks and backup.

| Exact unresolved decision | Alternatives / recommendation | Consequence and accountable action |
|---|---|---|
|A1 organization applicability|Shared global packages with explicit versioned allowed-customer metadata, or customer-owned catalogues. Recommend retaining global ownership and an explicit optional constraint model after approval|Owner defines which organizations may consume each package; security reviews cross-tenant read/write semantics. Do not reinterpret display scope|
|A2 resource/OS/environment/method matrix|Versioned explicit allowlists with defined wildcard/unknown behavior, versus human-only applicability labels. Recommend machine-readable version-scoped rules, unknown/conflict fail closed|Owner must supply supported attribute values, precedence and legacy transition. Engineering maps DataSource.source_type/opscontrol OS/environment and collector/method versions without guessed aliases|
|H1 history granularity|Per-attachment revisions plus per-source resolved snapshots, versus source aggregate revisions only. Recommend append-only source revisions referencing immutable attachment/package snapshots|DBA/security review all mutation paths including connection_config.monitoring_overrides, atomicity, secret exclusion/redaction and retention holds|
|H2 replacement/removal|Retire/supersede records plus tombstones rather than hard deletion; preserve old source/tenant/version provenance|Owner approves retirement and source-deletion behavior; no cascade deletion of history. Current DELETE is not certified historical preservation|
|H3 backfill/retention|Record existing state as an observed baseline (not reconstructed history), retain until approved retention/hold policy|No fabricated former selections or expiry defaults. Forward additive schema, fail-closed populated downgrade, backup/restore and old-writer fencing review required|
|H4 older writers/concurrent revisions|Optional expected timestamp preserves old callers (implemented); mandatory versioned revision API gives universal lost-edit refusal|Owner/API compatibility decision before mandatory enforcement. Current optional contract is not an all-writer temporal fence|

These are design requests, not signoffs. Product owner supplies exact semantics; data/runtime engineering and DBA review provenance, migration/restore and PR80 integration; security reviews RBAC, history immutability and redaction. No signatures fabricated. Block only these portions; do not substitute audit strings, template package versions or screenshots for missing history. No schema change was made. Acceptance after approval: atomic revisions for every mutation, stale-writer refusal, retire/replace preserving snapshots, unchanged effective hash after reload, historical receipts/version references and populated restore/refused rollback evidence.


**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**
