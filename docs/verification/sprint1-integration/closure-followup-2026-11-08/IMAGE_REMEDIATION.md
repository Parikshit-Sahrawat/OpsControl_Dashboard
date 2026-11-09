# Seven-role image remediation — no clearance or waiver

Baseline hosted run42513541762 belongs to PR head4081fc7; each raw artifact records its actual synthetic merge source/image identity. ALL_SEVEN_FINDINGS.csv retains every scanner match, package/version, advisory, fix state/version and role. Matches are not unique CVEs or exploitability determinations. Raw SBOM/scans and scanner DB/tool provenance are preserved.

| Role | Baseline Critical / High / Unknown | Bounded correction | Remaining condition |
|---|---|---|---|
|backend-runtime|1 /59 /0|Official Python3.12.16 index, unchanged3.12 ABI, normal OS security upgrade; no runtime pip|Exact rebuilt image scan pending;59 vendor-wont-fix High matches need supported-base/reachability review, no waiver|
|backend-migration|1 /59 /0|Same patched base; preserve migration tooling and guards|Same scan/vendor gap; migration compatibility must remain verified|
|uat-backend|19 /142 /2|Pin Python3.12.16, OS update, uninstall pip/ensurepip after dependencies|Embedded pinned OTel vulnerabilities remain; final scan pending|
|frontend|31 /119 /1|Pin maintained nginx stable; OS security upgrade; align build Node24 and trusted CA|Fresh base scan1 Critical zlib CVE-2026-4738, fix1.4-r0 available; recipe upgrades OS, final build/rescan pending|
|ingestion-gateway|46 /160 /3|Scan actual release gateway Dockerfile with maintained nginx pin and OS update|Same base zlib finding; preserve TLS config, no final clearance|
|postgres|4 /125 /0|Official PostgreSQL17 Alpine candidate, normal OS package upgrade, preserve entrypoint and required gosu|Base candidate4 Critical/32 High. Three Critical Go stdlib matches in gosu require a supported upstream rebuilt binary; zlib fix needs final build. No live volume/distro cutover authorized|
|otel-contrib|19 /81 /2|Retain exact0.123.0 pinned image; no custom rebuild/fork or upgrade|BLOCKED by independent collector transition/compatibility contract; cannot patch compiled dependencies without changing the approved binary|

Official immutable indexes verified through registry manifests:

- Python3.12.16-slim: sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b.
- nginx stable-alpine: sha256:583b7f2fce1cdb8da5ad5c39ebd3c33b98b87d493190e548bdee1fa8c619c311.
- PostgreSQL17-alpine: sha256:3540c0362c809df084ffac0ae69fe794515f9de92692f02178bcdce0ef0302ac.
- Unchanged OTel0.123.0: sha256:e39311df1f3d941923c00da79ac7ba6269124a870ee87e3c3ad24d60f8aee4d2.

Fresh official nginx base:1 Critical/0 High/0 Unknown; PostgreSQL base:4 Critical/32 High/0 Unknown. These compare different source images/distributions, not a certified final application delta. Their CycloneDX/Syft/Grype/source identities, platform, scanner binary hashes and DB built2026-11-08T06:19:57Z are in raw/candidate-*/. Recipes apply OS upgrades; actual fixed versions and final deltas are **NOT VERIFIED** until immutable built images are scanned. No scanner cache is committed.

Python baseline Critical CVE-2026-115557 lists3.12.16 as a fixed version. A registry pin is not proof that a built runtime passed integration or vulnerability policy. Debian perl/glibc findings marked wont-fix are retained, not dismissed based on vendor status. Source execution paths and alternate-base compatibility require accountable engineering/security review. No essential library or PostgreSQL privilege-switching tool was removed to hide a match.

All seven original licence inventories remain PENDING_ACCOUNTABLE_REVIEW. Accountable security and legal/compliance reviewers must inspect direct/transitive/base licences, distributed NOTICE text, source-offer obligations, application licensing and distribution roles. No reviewer signature or legal clearance is invented. Final image identities, hosted build/scan outcomes and licence clearance remain BLOCKED/PENDING. Release NO-GO.
