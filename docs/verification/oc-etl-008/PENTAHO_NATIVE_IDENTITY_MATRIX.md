# Native identity matrix

All provider stability assessments below are candidates requiring exact-build evidence, not certification.

| Identity | Scope / proposed evidence | Stability and current disposition |
|---|---|---|
| OpsControl Workflow | Organization/environment + Workflow UUID | Application identity; not a native scheduler or provider control |
| OpsControl Job / PipelineJob | Existing Job/resource/PipelineJob UUID and immutable temporal binding ID | Application stable identities, preserved; no implicit reparenting |
| Server/repository authority | Installed Server instance + repository identity/namespace from independent native metadata and build provenance | Stability across restore/clone/repository switch UNKNOWN; hostname/display name alone insufficient |
| Native repository Job | Repository instance + native object ID + object type/version | Candidate durable object identity; rename/move/import/export/delete/recreate stability UNVERIFIED |
| Native transformation | Repository instance + native transformation object ID/type | Different from Job definition even when name equal; mapping through logical OpsControl Job requires exact contract review |
| Native schedule | Scheduler authority + native schedule ID + revision + target object binding | Candidate schedule identity; edit/recreate/owner changes and persistence UNVERIFIED |
| Native occurrence | Schedule authority/revision + native occurrence ID + original scheduled instant | Must be exported native identity; timestamp or cron-derived occurrence alone is not proof |
| Native execution / attempt | Server history ID or Carte registration ID + authority + workload kind; attempt links only if native evidence exists | Execution-scoped, not persistent Job identity; no inferred retry order or parent-child UUID |
| Carte authority/epoch | Server instance + independently proven restart epoch + registration/execution ID | Existing parser requires epoch; automatic discovery/proof absent. Restart may clear inventory; same UUID without epoch insufficient |
| Kitchen/Pan invocation | Resource/host + process-start epoch + native invocation + executable hash | Invocation scoped; PID/name/exit0 alone insufficient. Not a scheduler |
| Source generation / fence | Backend PipelineSource UUID/generation, reader method/revision/hash, lease/fence/continuity evidence | OpsControl authority, not a PDI build ID. Change invalidates old proof; active rebind remains blocked |
| Raw receipt / event | Existing accepted evidence UUID, payload SHA256, source generation and immutable binding version | Never replace raw ID with display name; duplicate observations must retain original dedup identity and historical attribution |

Proposed cross-surface mapping requires original Server repository-object metadata, schedule-to-target metadata, and a native execution-to-object link attributable to the same namespace. Carte registration IDs alone cannot supply this chain. If stable object or alias proof is absent, quarantine/retain claims separately and keep confirmation blocked.

Canonical object key representation must be reviewed for namespace/type uniqueness, rename/move behavior, length and restore/clone behavior. No new key encoding is standardized or persisted here. Proof envelope object_kind remains JOB (logical existing contract); it does not authorize adding TRANSFORMATION/SCHEDULE enum values. Provider object type belongs in original referenced evidence and a reviewed canonical key, pending exact mapping approval.


**Offline preparation only. Genuine qualification BLOCKED / NOT RUN. CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**
