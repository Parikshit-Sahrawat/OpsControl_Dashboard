# Pentaho native scheduler qualification preparation

2026-11-07 UTC; OC-ETL-008A. Source baseline `c12db2764f6d581850b9d3ac5a89d6771a2fc002`, existing draft PR80. No live endpoint, provider credentials, discovery, workload execution or deployment is authorized. This plan is not permission to run a historical certification runbook.

## Inventory and architecture boundary

| Existing source | Actual implemented contract | Qualification gap |
|---|---|---|
| backend/app/pipeline_adapters/pentaho_contracts.py | KITCHEN_PAN / PENTAHO_SERVER / CARTE declarations; candidate families8.3/9.3/9.4/10.2.x/11.0.x; runtime_verified false | No candidate family certifies an exact build |
| backend/app/pipeline_adapters/pentaho_observations.py | Typed version1 authenticated structured observations; scope/build/epoch checks; Server scheduler/repository claims remain UNKNOWN | A claim or parsed success is not genuine source authority |
| backend/app/pipeline_adapters/pentaho_carte.py | TLS/egress-controlled GET-only fixed status paths; advisory inventory, status parsing and unchanged-response checkpoint | No durable repository catalogue, scheduler authority or automatic verified restart epoch |
| backend/app/worker/pentaho_status.py | Legacy bounded job status/log parser, sanitized step observations | Legacy display-name configuration is not durable native binding proof |
| backend/app/unified/pentaho_schedule.py and pentaho_history.py | Explicit schedule authority, native occurrence inventories, telemetry coverage/history projections | No universal Server API; configured expectations do not become native schedules |
| backend/app/unified/pentaho_execution.py, pentaho_models.py, pentaho_replay.py, pentaho_recovery.py | Existing execution/attempt/revision and evidence retention/review contracts | Synthetic repeat/recovery evidence cannot certify native completeness or exactly-once delivery |
| backend/app/etl_bindings/{authority,authority_api,commands,models,writer}.py | Signed authority envelopes, immutable binding versions, conditional confirmation/receipt authority, old-writer fence | Qualified provider admission and active cutover remain blocked |
| backend/migrations/versions/0018*,0033*,0034*,0035*,0039*,0040*,0041* | Historical/additive identity, history, Workflow, temporal binding and protocol fences | No migrations changed or executed by this task |

This is an inventory, not a second configuration owner. Resource Management retains ownership; monitoring projections consume evidence. Server schedule authority and repository identity must be independently linked to Carte execution observations. Carte cannot stand in for Server scheduling. Kitchen/Pan may be observed through already authorized Agents, never launched by this package.

## Historical evidence and limits

- `docs/verification/pentaho-carte-compat-001/RT-LAB-016D-final-reconciliation.md`: historical native inventory4 distinct registered Jobs; transformation inventory3 before restart/0 after; host-file retention observed; native DB and OpsControl runtime durability NOT VERIFIED/NOT RUN. Repeated-child distinct UUIDs UNVERIFIED. Reconciliation is not a fresh test.
- `docs/verification/dev052/PENTAHO_CERTIFICATION.md`: genuine certification BLOCKED. Its workload-launch examples are outside this task and must not be run.
- `docs/verification/oc-etl-007/REPORT.md`:117 controlled cases at2b8eada,18 hosted checks atc12db27; zero qualified provider attestations/receipts. Old writer refusal is not operational rollback certification.
- OC-ETL-002 through006 reports remain historical controlled evidence. No independent UAT or provider certification inferred. Source/evidence hashes are in SOURCE_REFERENCES.json.

## Future sequence, separately authorized

1. Accountable owner selects one isolated read-only exact-build target and signs permitted paths/IDs/window; no approval currently exists.
2. Review vendor documentation matching installed build/edition/plugin/repository/Java; inventory binary/image hashes, repository namespace, scheduler instance and restart evidence without guessing endpoints.
3. Review TLS/egress/least-privilege credentials and original evidence handling; complete PROVIDER_AUTHORIZATION_CHECKLIST.md. Candidate endpoint status stays UNVERIFIED until that review, and qualification still needs execution.
4. Read only explicitly authorized pre-existing records; do not create schedules, execute success/failure workloads or trigger retries to generate evidence. Missing native cases stay BLOCKED unless separately supplied by the target owner.
5. Independently reconcile native object, schedule, occurrence, execution and source-generation IDs. Preserve raw bytes/hash/times and discontinuities; do not merge aliases on names alone.
6. Accountable issuer signs only genuinely reviewed evidence; separate reviewer tests scoped admission/confirmation and original receipts in a separately approved disposable OpsControl DB. See OFFLINE_TEST_MATRIX.md for unexecuted live/DB cases.
7. Stop on identity/build/TLS/permission mismatch, missing inventory, stale evidence or rollback uncertainty. No aggregate activation or health follows automatically.

No live commands are provided. The offline command is in REPORT.md. D07 recurrence/calendar/occurrence semantics and D08 separate long-running/freshness/aggregation policy require exact owner decisions; existing supported fields remain unchanged. Neither is resolved by a Server cron string or Carte status.


**Offline preparation only. Genuine qualification BLOCKED / NOT RUN. CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**
