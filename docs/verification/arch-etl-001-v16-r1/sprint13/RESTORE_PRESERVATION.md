# REC-02 — logical restore preservation

**PASS for selected synthetic records.** The utility checked the target was empty, verified the manifest and ran `pg_restore --exit-on-error --single-transaction --no-owner --no-acl` into a separately named database in the owned disposable container. The source and restored snapshots compared actual identifiers and critical field values; user password hashes were compared in memory but not printed. This is not a whole-database cryptographic equivalence or production DR certification.

| Selected table | Source count = restored count |
|---|---:|
| organizations | 7 |
| users | 6 |
| roles | 10 |
| customer_access_grants | 3 |
| data_sources | 2 |
| collectors | 2 |
| collector_methods | 1 |
| pipeline_sources | 5 |
| pipeline_evidence | 5 |
| pipeline_holds | 3 |
| job_order_histories | 1 |
| operational_incidents | 1 |
| incident_activities | 1 |
| security_audit_events | 5 |

The seeded A/B customer IDs remained distinct; the employee's A `ALLOW` grant and B `DENY` stayed attached to their original IDs, and the restored effective-access resolver allowed `etl.view` for A and denied B. Collector, method, canonical source ID, generation, fence=7, live checkpoint `cursor=19`, recovery checkpoint `cursor=11`, held evidence identity/payload, synthetic execution history, incident-to-history/activity and audit-to-incident references all compared equal. These values were synthetic; UNKNOWN history status was not promoted to verified success.

On the restored database, a B-owned pipeline-evidence insert referencing A's source failed the composite customer FK; a repeated `(source_id, generation, external_key)` failed the unique constraint. The restored snapshot remained unchanged after both rollbacks, legal-hold cleanup and the corrupt-artifact attempt. Source physical database size was 15,562,419 bytes; restored size was 14,997,171 bytes because physical layout differs, while the tested logical projections and counts matched. [Migration](MIGRATION_SAFETY.md) and [legal hold](LEGAL_HOLD_VALIDATION.md) add separate safety checks. The current one-organization resource model remains unchanged; this test does **not** implement shared VM associations.
