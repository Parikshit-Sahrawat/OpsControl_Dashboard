# REC-01 — backup integrity

**PASS in the owned local fixture.** The [existing utility](../../../../backend/scripts/database_backup.py) used `pg_dump --format=custom` with a private libpq service file. The source was a synthetic PostgreSQL 17 database at migration head `0037_access_boundaries`; no password or connection string appears in the evidence package. The private directory was mode 0700 and the archive/manifest mode 0600. The archive was not placed in repository history and was removed when the probe ended.

| Observation | Value |
|---|---|
| Archive size | 413,811 bytes |
| Recorded SHA-256 | `b0cc91cd781c0c7306a66251b4fe5a0296831d83658a5a322f94ffcb8d94280e` |
| Readability | `pg_restore --list` succeeded and contained `pipeline_holds` and `alembic_version` |
| Manifest and size | Utility's manifest format and byte count matched the archive |
| Integrity failure check | Altered copy plus unchanged manifest rejected with `Backup checksum or format mismatch` |

The local archive was **not encrypted**. Its private filesystem permissions reduce local exposure but do not meet GOV-07's encrypted backup target. The utility does not in this test demonstrate external encrypted storage, key custody, immutable/off-site copies, operational backup retention or WAL archiving. Those remain P0-04 production requirements. [Timing](RPO_RTO_EVIDENCE.md) and [exact execution](VERIFICATION.md) bound this finding.
