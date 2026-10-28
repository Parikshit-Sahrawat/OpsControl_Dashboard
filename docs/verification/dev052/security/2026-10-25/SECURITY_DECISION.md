# DEV-05.2A strict security gate — 2026-10-25

**Security gate: BLOCKED. Release: NO-GO. No exceptions or clearance.**

Policy read at commit `a2cc63352e59945ee0de55781f97975ce0d56e90`; Issue #68 including owner approval comment read in full. All candidates use that repository source archive. No release image designation, registry publishing, production deployment or merge was authorized/performed.

## Exact candidate inventory

All selected images are Linux amd64. IDs below are immutable **image configuration digests**, not registry manifest digests. Third-party registry RepoDigests are recorded in `image-inventory.json`. Local candidates are not published; their registry manifest digests are unavailable and must not be substituted into UAT deployment settings. Each scan reads a Docker archive saved by immutable image ID; its manifest config bytes are SHA-256 checked against that ID before scanning. Archive SHA-256 and tool exit codes bind SBOM/scan to the exact snapshot.

| Reference / role | Image config SHA-256 | SBOM / scan |
| --- | --- | --- |
| backend-runtime — API/worker restricted runtime | `sha256:39da37450ebb9c2ccec370813cb82ebdd038349bd59ff2f1a8f14e0dbc00cefe` | SCANNED |
| backend-uat — UAT API/worker/migration candidate | `sha256:48f93c7d23c396b7102a782719957a2ef46d111038114e966a2d6fe62ffddfe1` | SCANNED |
| frontend — Static frontend candidate | `sha256:3ba0a0710a426608d79be7ecba616cb855c6da32d03033d98d89c5003426cade` | SCANNED |
| postgres — Database ancillary | `sha256:82903352d6faf8f8a318bc4353d1cb1db67d4a5ff968d2799b2718e2cb00afa2` | SCANNED |
| postgres-alpine — UAT database ancillary | `sha256:ab20e934b27ba3ff927c1b4c9ff8cf6c32f315f743efe68dd3441182a87fb085` | SCANNED |
| postgres-ecr — Demo database mirror | `sha256:82903352d6faf8f8a318bc4353d1cb1db67d4a5ff968d2799b2718e2cb00afa2` | SCANNED |
| gateway — Ingestion gateway | `sha256:dc73b49f5124cf2ee538dfbdfbd121f0b4ccdcb20fea30f3a81bd477c02e2bb5` | SCANNED |
| contrib — Collector/embedded demo distribution | `sha256:f0eaa24275f0eac77186cf0c9b1d1c72c9edde884a7c6bf9e5332ca8b5939d97` | SCANNED |
| backend-demo — Demo only; not production approved | `sha256:91d9cd2998f1d99d58291c16a306258dacd5938be6f33faedf4481ef30115a71` | SCANNED |

9 references / 8 unique snapshots (Docker Hub and ECR PostgreSQL are identical). 79 source files were inspected/indexed across Dockerfiles, Compose, deployment definitions, build scripts and workflows in `source-inventory.json`. `deployment-scope.json` distinguishes production-capable, demo/UAT, build-only and test-only paths. Operator-supplied final Stage B images are unset; coverage cannot establish the actual release set.

## Scan and license coverage

Syft 1.55.0 and Grype 0.121.0 Linux amd64 were obtained from authoritative Anchore releases. Versioned archive hashes were checked against upstream checksum manifests before extraction/execution; raw checksum manifests and tool versions are retained. No signature verification is claimed. Grype database metadata/checksum URL, schema and build timestamp are in `db-status.json`; schema v6.1.10, built 2026-10-25T06:27:34Z. Database updates were disabled for all scans after this snapshot. No ignored findings/severity filter was applied.

CycloneDX SBOMs include final OS and application/transitive components (including Go binary dependencies). No scanner metadata is a claim of exhaustive runtime reachability or legally verified license obligations. Each `*.scan.json` retains vulnerability IDs/severity/fixes and package layer/location. Counts below are scanner matches, not unique vulnerabilities or proven exploitability.

| Image | Components | High | Critical | Missing license metadata |
| --- | ---: | ---: | ---: | ---: |
| backend-demo | 3900 | 123 | 14 | 3754 |
| backend-runtime | 2964 | 55 | 0 | 2819 |
| backend-uat | 2964 | 55 | 0 | 2819 |
| contrib | 936 | 68 | 14 | 935 |
| frontend | 1305 | 101 | 25 | 1237 |
| gateway | 1315 | 121 | 31 | 1243 |
| postgres-alpine | 871 | 0 | 0 | 826 |
| postgres-ecr | 7403 | 85 | 1 | 7260 |
| postgres | 7403 | 85 | 1 | 7260 |

Examples requiring investigation: frontend libcrypto3 3.3.3-r0 / CVE-2025-15467 (scanner Critical, fix 3.3.6-r0); gateway libcrypto3 3.5.5-r0 / CVE-2026-63073 (Critical, fix 3.5.8-r0); Contrib golang.org/x/crypto v0.36.0 / GHSA-5cgq-3rg8-m6cv (Critical, fix 0.52.0). These are not waived. Matching library versions alone does not prove exploitability; unknown applicability prevents clearance. Confirmed applicable unresolved High/Critical would be FAIL under policy. Current gate is BLOCKED for incomplete accountable triage, final-image designation and license review; it cannot pass.

`license-inventory.json` includes all cataloged component licenses, paths via SBOMs, and unknowns. `license-decision.json` records unverified license/NOTICE/source-offer obligations. No component is legally cleared or owner-approved. Base images and upstream Apache-2.0 collector do not confer transitive clearance.

## All nine prior advisory dispositions

Reviewer for every row: Codex automated evidence triage, 2026-10-25; accountable security/release reviewer **not assigned**. All dispositions remain **UNRESOLVED**. No applicable risk is hidden and no exception was approved. The original audit, candidate SBOMs, per-layer findings and `runtime-introspection.json` are evidence.

| Advisory | Surface and evidence | Proposed mitigation / listed fix | Disposition |
| --- | --- | --- | --- |
| PYSEC-2026-2121 (CVE-2026-32274) | Black CLI cell-magic option is not passed by declared CI; no production Black cataloged. Untrusted option injection beyond declared workflows not ruled out. | 26.3.1; compatibility not validated | UNRESOLVED |
| PYSEC-2026-2120 (CVE-2026-31900) | No psf/black Action or use_pyproject setting in declared workflows; Black CLI remains installed in CI. | 26.3.0; compatibility not validated | UNRESOLVED |
| GHSA-cg8m-r9f2-5wm2 (CVE-2026-114134) | No Black Action use_pyproject/required-version execution path declared; CI tool pin still vulnerable. | 26.10.1; compatibility not validated | UNRESOLVED |
| PYSEC-2026-196 (CVE-2026-8643) | pip installed in final Python images and invoked as root during build; malicious package entry-point installation remains an effective supply-chain path. | 26.1.2; compatibility not validated | UNRESOLVED |
| PYSEC-2026-1795 (CVE-2025-8869) | Python 3.12 data_filter exists (runtime introspection); advisory fallback prerequisite appears absent for these candidates, but all CI Python/platforms not attested. | 25.3; compatibility not validated | UNRESOLVED |
| PYSEC-2026-1796 (CVE-2026-1703) | pip wheel installation runs during image build and CI. No application runtime installer found, but pip remains shipped. | 26.0; compatibility not validated | UNRESOLVED |
| PYSEC-2026-2875 (CVE-2026-3219) | pip consumes package archives during image build/CI; ambiguous archive handling is not excluded. | 26.1; compatibility not validated | UNRESOLVED |
| PYSEC-2026-2876 (CVE-2026-6357) | pip installation/self-update path runs during build; suppression of version-check imports was not proven. | 26.1; compatibility not validated | UNRESOLVED |
| PYSEC-2026-3721 (CVE-2026-13346) | Requires malicious index and notably pip download --only-binary. No such command found in declared build/CI; future/operator index override remains unverified. | 26.2; compatibility not validated | UNRESOLVED |

Black 25.1.0 is in development requirements and CI CLI checks, but absent from the nine candidate SBOMs. This supports candidate-runtime absence only; it does not approve CI/build exclusions or unknown operator images. No declared Black GitHub Action/use_pyproject path was found. pip 25.0.1 is actually shipped in final Python candidates and used for root build-time package installation. Python 3.12.15 exposes PEP 706 data_filter, making the specific tar fallback prerequisite appear absent on these candidates, but this is not a blanket pip exception. Five pip advisory aliases match Grype Medium findings; missing matches for other prior IDs are not proof of absence. Individual reachability, severities/unknowns, fixes, locations and reviewer fields are in `advisory-triage.json`. None of the nine was remediated by changing expected hashes or suppressing scanner output.

## Build provenance, tests, failures and cleanup

Original Dockerfiles were not modified. Isolated Git-archive build contexts add only ephemeral BuildKit CA mounts to pip/npm installation lines, preserving TLS verification and keeping CA material out of layers. Effective Dockerfiles, original source hashes, complete build logs and resolved base references are retained. Mutable base tags and unconstrained transitive dependencies remain reproducibility gaps; these local candidates are not SLSA-attested release artifacts. Source architecture and image architecture are recorded separately from registry indices.

Initial Grype setup failed because the default home cache was read-only; using a task-specific cache restored normal verified database setup. A demo image was initially not yet built when scanned; its initial BLOCKED observation remains in inventory history, and the completed image was subsequently scanned. A retry-helper variable-shadowing error occurred after that image completed, was corrected, and the targeted retry exited successfully. No failed attempt was represented as a clean scan. These diagnostics are retained in logs.

Targeted checks: archive manifest-to-config digest assertions for all snapshots; valid SBOM/scan JSON and scanner exit 0; source/final image correspondence; no Black in candidate catalogs; pip/PEP706 introspection on a read-only network-none runtime container; tool checksum verification; original evidence/test files unchanged. Introspection container used --rm. No service, port, database volume, customer secret or product stack was created. Docker save archives and build staging are task-scoped temporary files; no broad cleanup was run. Candidate images/build caches and verified scanner database/tools are retained as non-running non-secret analysis dependencies.

## Required next action and signoff

Owner must designate final immutable release registry digests and architectures, appoint accountable vulnerability and license reviewers, investigate/remediate all applicable High/Critical across exact final images and effective build chain, validate Black/pip upgrades or explicit evidence-backed exclusions, fulfill NOTICE/license/source obligations, and approve any permitted lower-risk exception. None of this report is owner signoff. PR #69 remains draft and overall release remains NO-GO. DEV-05.0/05.1 evidence is preserved unchanged.
