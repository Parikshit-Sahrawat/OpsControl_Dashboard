# Source-owned configuration contract — integration candidate

> Historical snapshot at PR head4081fc7. The [current closure follow-up](closure-followup-2026-11-08/REPORT.md) and [remaining blockers](closure-followup-2026-11-08/REMAINING_BLOCKERS.md) supersede the single-source writer, history-UX and documented fault-test status below; earlier evidence remains preserved.

Owner authority: the four contracts in INTEGRATION_LEDGER.md and the explicit PR89 implementation task. The earlier detailed S01 design remains a proposal for exact details, not an independent approval signature. No second configuration authority is introduced.

## Implemented boundary

DataSource owns a mutable integer configuration head and append-only `source_configuration_revisions`. Existing `monitoring_template_attachments` are its current projection. Migration0042 follows unmodified0041; no uncertain historical backfill. Revision content stores attachment/detachment before/after sets, exact template pins and safe package snapshots, overrides/removals, evaluated effective content, source context, evaluator/time, authenticated actor snapshot, parent/restore references and canonical UTF-8 bytes/SHA256. DB composite ownership constraints, uniqueness and immutability triggers protect history; version rows cannot be rewritten. Runtime/DB owner privileges remain a trust boundary, not tamper-proof certification.

The command locks the existing source, checks mandatory expected revision, revalidates dependencies/applicability and uses an actor/source-scoped idempotency key. Projection, revision and head commit together. Failed transactions reserve no successful receipt. Duplicate key/different request409; stale revision409; missing preconditions on old attachment writers428. Existing security transaction authority and scope hooks remain active. Rollback revalidates an older attachment set against the **current** source and creates a new ROLLBACK revision; it does not restore source credentials, checkpoints, queued telemetry, collector activation or observed health.

## Applicability v1

`package_config.applicability` is version-pinned with the package. It declares schema_version1, exact source_types, Windows/Linux OS, and real MethodInput configurations validated by existing METHOD_SCHEMAS/validate_method. No generic ANY, source-name inference or provider success is created. Optional override_components permit explicit attributes/metrics/alerts/logs components; collector_override_fields permit only explicitly named interval/interval_seconds numeric5–86400 changes, not provider type, authentication or network settings. Explicit API manifests use family API and HTTPS method settings, validated through the existing API-settings/URI parser. Worker allowlist/DNS/TLS authorization stays mandatory at activation and dispatch. Unknown legacy manifests and unqualified ETL provider mappings remain UNVERIFIED/BLOCKED. A template's declaration is a configuration compatibility claim, never provider certification. Missing required attributes, conflicts, retired dependencies, wrong OS/method and unsafe input reject the command. Existing source overrides are considered. Committed configuration remains NOT_REQUESTED/UNVERIFIED for application/health.

## API

Existing prefix `/api/v1/monitoring/data-sources/{id}/configuration`:

- GET current: revision, attachment intent and whether explicit legacy import is required.
- POST preview: complete attachment set + expected_revision; validation only, no persistence.
- POST commands: same body, mandatory UUID Idempotency-Key; revalidation and atomic commit.
- POST import-legacy: expected_revision0 + key; preserve current legacy intent explicitly UNVERIFIED, original actor/validation unknown.
- GET history: source-bound descending integer keyset `before`, limit1–100.
- GET revisions/{number}: immutable safe snapshot and provenance.
- GET diff: safe before/after documents and changed flag; not a deployed-state comparison.
- POST rollback: expected_revision + target_revision + key; new audited revision.

Existing POST/PATCH/DELETE attachment endpoints adapt to the same command with mandatory Expected-Revision and Idempotency-Key. No client-supplied actor or ownership accepted. Reads require templates.view and source visibility; changes require templates.manage with fresh authorization. CORS explicitly permits only the added precondition headers. No permission catalogue expansion.

## Explicit limits and pending completion work

- Host-method and existing HTTPS GET/HEAD configuration compatibility are implemented; ETL provider-specific template applicability remains blocked until an exact approved mapping is implemented and verified. Existing independently configured API/Pentaho paths remain separate.
- Source-context/OS changes after cutover fail closed. A complete atomic resource-context + configuration edit adapter/UI still needs implementation and integration tests; do not silently bypass the fence.
- Template-version publication is serialized and immutable but still lacks mandatory catalogue expected-version checks. Source revision checks do not certify publication concurrency for every client.
- Managed CollectorConfigVersion/AgentDeployment application provenance is still independent; no new automatic activation or deployment is authorized. Receipt/telemetry checkpoints never enter this ledger.
- Current history UI displays the first history page; full API history is keyset-paginated. Rich diff rendering, pagination controls, detach review and staged-draft application UI need further completion. Existing saved resource drafts remain non-operational.
- All history is retained. No destructive retention job, purge or hold-release endpoint is implemented; retention duration/legal hold authority remain separately reviewable.
- Concurrent source commands and injected transaction failure are tested. Process termination around COMMIT, concurrent permission revocation on this exact command, and full mixed-version configuration writer certification require additional tests before a complete S01 claim.

These limitations keep Sprint1 **NOT COMPLETE**. Green unit/browser tests do not remove them. CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.
