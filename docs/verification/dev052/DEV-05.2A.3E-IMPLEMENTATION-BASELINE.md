# DEV-05.2A.3E — Controlled Implementation Baseline

Status: Stage 1 in progress; not certified. Release gates remain CHK-001 FAIL / CHK-002 BLOCKED / SECURITY BLOCKED / RELEASE NO-GO.

## Immutable source baseline
- Repository: Parikshit-Sahrawat/OpsControl_Dashboard
- Base branch: main
- Base commit: ee4ba0db26b5f0648677b3fe69f813128fbfaefe
- Implementation branch: feat/dev-05-2a-3e-durable-telemetry
- Collector runtime guard: 0.123.0; no upgrade authorized.
- Existing generator: backend/app/telemetry/configuration.py
- Existing OTLP ingestion: backend/app/telemetry/ingestion.py
- Existing receipt schema: backend/app/telemetry/models.py
- Agent supervisor: agent/opscontrol_agent.py

## Existing behavior (source review)
- Exporter: otlphttp/opscontrol, HTTPS endpoint /api/v1/agent/otlp, Bearer token.
- Exporter queue: file_storage/opscontrol; sending_queue.enabled=true; queue_size=256.
- Retry enabled; max_elapsed_time=0s when durable file logs configured.
- File-log receiver uses file_storage and retry; durable file-log pipeline avoids batch and enables fsync.
- Other signal pipelines use batch processor.
- Ingestion dedup currently uses (agent_id, signal, payload_hash) and commits TelemetryReceipt with effects.
- Supervisor service metrics use direct HTTP /api/v1/agent/otlp/v1/metrics; no verified durable journal.
- Existing Collector persistent queue is NOT certified for crash safety; CHK-001 remains FAIL.

## Runtime preservation hold point
Before any cutover, reset, cleanup, downgrade, queue-format change, or agent deployment:
1. Identify each agent's actual state directory and Collector checkpoint/queue directories.
2. Quiesce only under an approved maintenance procedure, or use a filesystem-consistent snapshot.
3. Record filesystem type, free capacity, permissions, ownership, file inventory, SHA-256 manifest, and timestamps.
4. Copy state to an access-controlled, persistent backup location; verify manifest and perform an isolated restoration rehearsal.
5. Capture running binary SHA-256, generated configuration (with secrets redacted), agent identity, and applied revision.
6. Inventory in-flight, queued, checkpointed, accepted, and processed records where observable.
7. Require an explicit per-agent migration readiness result. If state cannot be safely inventoried or preserved, STOP cutover.
No runtime backup is claimed by this repository document.

## Authorized stages
1. Reproducible baseline and preservation hold point.
2. Source-aware local journal and stable event identity.
3. PostgreSQL spool, transactional ACK boundaries, event deduplication.
4. Replay, safe cutover, and non-destructive rollback.
5. Controlled fault-injection harness and evidence.
6. Independent review submission.

## Hard acceptance rules
- Source progress never advances beyond durable source-to-journal handoff.
- Stable tenant-scoped event identity survives restart, reserialization, and rebatching.
- Central A-ACK follows PostgreSQL commit and certified synchronous standby durability.
- Backend processing effects and dedup identity commit atomically.
- No missing centrally acknowledged event IDs; no duplicate logical effects.
- Seven-day offline recovery is contingent on verified agent capacity.
- Dedup retention >=30 days and greater than maximum replay window plus margin.
- Primary + synchronous standby; fenced failover; RTO <=15 minutes within certified failure model.
- No main merge, production deployment, production migration, or release-gate promotion without separate approval.

## Outstanding implementation proofs
- Determine feasible source-aware handoff for filelog, journald, Windows Event Log, metrics, and supervisor observations on Collector v0.123.0.
- Demonstrate old persistent queue preservation and replay-safe migration.
- Measure storage workload and certify Windows/Linux filesystem crash semantics.
- Produce independent security and reliability certification evidence.
