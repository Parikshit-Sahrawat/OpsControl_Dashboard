# REC-06 — controlled recovery timing and policy boundary

**PASS as a measured local timing, not as a production service-level result.** The final owned run used PostgreSQL 17 Alpine in a disposable Docker container on the local execution host. The source had the harness's populated migration/test fixtures plus Sprint 13's synthetic rows; 14 selected table counts are in [restore evidence](RESTORE_PRESERVATION.md). Timings used `time.monotonic()` around the existing utility's backup and restore calls.

| Measured item | Final controlled value |
|---|---:|
| Source physical DB size before backup | 15,562,419 bytes |
| Custom-format archive size | 413,811 bytes |
| Restored physical DB size | 14,997,171 bytes |
| Backup call duration | 0.217 seconds |
| Restore call duration | 0.629 seconds |
| Observed local backup + restore call time | 0.846 seconds; excludes setup, migration and application recovery |

The source and target physical sizes differ because a logical restore re-creates storage layout. Neither size measures telemetry volume, WAL generation, off-site transfer or production recovery workload. A restore into a second database in **the same container** does not exercise loss of a host/site, key retrieval, network isolation, DNS cutover, worker startup, client reconnection or independent operational response.

GOV-07 approves **configurable initial targets** of RPO 15 minutes and RTO 4 hours; it also targets daily full backups, continuous WAL/PITR where supported, 30-day operational backup retention, twelve monthly snapshots subject to data policy, monthly restore, quarterly DR drill, encryption and legal-hold precedence. This sprint measured **no recovery point**, WAL archive/restore interval, failure detection/cutover or production RTO. Achieved production RPO/RTO: **NOT VERIFIED**. Backup retention, telemetry retention, audit retention and legal-evidence retention need separate approved policies and evidence. P0-04 stays open.
