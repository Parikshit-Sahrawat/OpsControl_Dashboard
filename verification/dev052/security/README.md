# Candidate security analysis (no deployment)

Recorded evidence is under docs/verification/dev052/security/2026-10-25.
The inventory/scanner driver accepts optional --only NAME for an isolated retry,
preserving prior inventory observations. It requires the exact candidate image
IDs, tool binaries and verified Grype DB recorded in evidence. Tool paths/cache
paths are local setup paths, not credentials. Rebuilding mutable tags can produce
different images; never claim a new image has the recorded old scan.

The scanner saves by immutable config ID, checks archive config bytes against that
ID, records archive SHA-256, then reads that same archive with Syft CycloneDX and
Grype JSON. It never mounts Docker into a scanner or starts a service. Local image
IDs are NOT registry manifest digests. Registry publication/production deployment
is not authorized. Obtain owner-designated release digests and rerun as necessary.

Original build Dockerfiles are untouched. Captured effective Dockerfiles add only
BuildKit public CA secret mounts for authenticated TLS verification during package
installation. Source archive commit, input hashes, base resolutions, effective
Dockerfiles, build logs, scanner release checksums, tool versions, DB metadata,
image identities, raw JSONs, license metadata, nine advisory dispositions and raw
artifact hashes are retained. Runbooks and scanner results confer no waiver or
license/security approval. Gate BLOCKED and release NO-GO remain mandatory.
