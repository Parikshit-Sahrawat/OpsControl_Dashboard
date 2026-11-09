# Separate implementation approval request — not authorization

Recommended next bounded task: inspect official maintained PostgreSQL 17 candidates without publishing, then propose one digest whose actual bundled gosu compiler/module versions address each advisory (including distro and scanner disagreements). Do not assume a newer gosu tag fixes compiled stdlib. If no official fixed build exists, report the upstream gap; do not build an unapproved fork or waive findings.

Required accountable decisions: security owner reviews all 35 mappings and the Windows-platform discrepancy; platform owner selects supported distribution/architecture; DBA approves PG17 entrypoint, UID/GID, data-directory and extension/locale compatibility; legal reviewer approves relevant licences/NOTICE/source offers. Roles are named; no individual signature is fabricated. Owner must separately authorize any dependency/base replacement and isolated compatibility execution.

Before implementing a candidate: retain original image and DB backups, prove fresh/populated migrations, volume ownership, TLS/auth, locale/ICU/extensions, pg_dump/restore content hashes, crash/restart, app API/worker and older-writer compatibility. Never use PG major-format changes or old-image HTTP200 as rollback proof. Rollback must preserve data and reject unsafe schema downgrade. These tests are NOT RUN in this read-only workstream and require a separate approved disposable environment. No production database may be started or manipulated here.

Unknowns: final registry manifest approval, full source-to-binary provenance, complete Go reachability analysis, actual fixed candidate, security/DBA/legal signoff. Every finding remains UNRESOLVED. No risk acceptance or release promotion is requested by completing this assessment.
