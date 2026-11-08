# OC-DEV-201 — centralized PostgreSQL durable spool contract

Engineering contract for accountable review, NOT owner/DBA/security signoff. OC-DEV-101 implementation remains blocked pending that review. Preserve centralized PostgreSQL; do not substitute a custom collector fork, external queue or unapproved replay-primary architecture.

Admission: authenticate source/tenant/method and current generation/fence, lock ownership, validate bounded envelope and stable producer event IDs. In one PostgreSQL transaction insert immutable payload/provenance, unique tenant/source/generation/event identity, payload hash and dispatch state. A repeated same identity/hash returns the original receipt; a different hash conflicts/quarantines rather than replacing history. Commit before acknowledging admission. Neither checkpoint advance nor successful queue enqueue is a delivery acknowledgment.

Dispatch: lease/fence bounded rows; perform transport outside the claim transaction; acknowledge an independently committed destination receipt before closing delivery. A crash before/after either commit must be replay-safe with explicit duplicate accounting. Never delete old payloads before replacement or terminal disposition is durably committed. Expired leases can retry, but stale owners cannot close newer claims.

Retention/capacity: retain undelivered originals, receipt/provenance and legal holds. Refuse/backpressure before admission when approved capacity cannot be guaranteed. Never silently evict admitted evidence, drop required libraries or claim success at retry/retention exhaustion. Exact quotas, payload storage/encryption, retention periods, expected-source inventory and HA/RPO/RTO must be reviewed; no invented numeric defaults.

Recovery tests: deterministic SIGKILL before/after admission/ack/lease/destination commit; database/storage full; transient and permanent rejection; lease expiry; duplicate/conflicting replay; retention/holds; backup/restore. Independently reconcile original stable IDs, accepted attempts, destination distinct receipts, physical duplicates and missing IDs.

Boundary: downstream PostgreSQL cannot recover records lost before admission unless independently complete source inventory and enforced retention exist. This contract does not close CHK-001/002, certify exactly-once or alter collector0.123.0. Required reviewers: data/runtime engineering, DBA, security and accountable owner. No signatures inferred. OC-DEV-101 NOT STARTED.
