# DEV-05.2A.1 remediation evidence

Production candidate policy: deploy/release/image-policy.json. This is an allowlist
proposal and exact scan inventory, not deployment approval or published manifests.
Backend Dockerfile.runtime defaults to the runtime target; `--target migration`
builds separate maintenance tooling. Pass `--secret id=proxy_ca,src=/etc/ssl/certs/ca-certificates.crt`
with an appropriate trusted CA bundle. BuildKit secret mounts preserve TLS trust
without embedding the session CA. Base images are digest-pinned; apt/apk package
repositories and transitive version ranges remain reproducibility review items.

scan_candidates.py catalogs/scans the recorded candidate references via immutable
image-ID archives and supports --only NAME for scoped retries. Tool paths and DB
cache are inherited from the verified DEV-05.2A setup. No ignores/severity filters
are applied. Original outputs under security/2026-10-25 are never overwritten.
license_files.py exports never-started network-none containers to inventory legal
file presence, then removes only its own container and anonymous volumes. A file
hash or scanner label is not human license/NOTICE approval.

The new collector candidate is evaluation-only. Keep the existing 0.123.0 contract,
assertions and checksummed provisioning unchanged until a separately authorized
compatibility change. Do not promote latest merely because its scan is cleaner.
No deployment, real targets, broad cleanup, merge or DEV-05.2B execution is allowed.
