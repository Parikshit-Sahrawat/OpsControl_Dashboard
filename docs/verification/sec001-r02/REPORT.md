# SEC001-R02 — PostgreSQL/gosu read-only qualification

Date: 2026-11-09. Outcome: **PARTIAL STATIC QUALIFICATION; 35 FINDINGS UNRESOLVED; FIXED CANDIDATE BLOCKED**.

## Exact evidence

[BASELINES.json](BASELINES.json) preserves the reviewed source, all seven image identities and original artifact hashes. PostgreSQL image config is `sha256:a7d2ca3526ce25d3036f8c403504a77af1d05448708074dfaf2817f4f3be54e8`; artifact 13668814648, scan source b1e645f342be5bc84141f314a12a81d3c38f621b, assessment ecfdff2cf3f9d1a7b7b284e79a7f708d1baea8ce. These are historical scans, not new scans. Syft 1.57.0, Grype 0.121.2, DB built 2026-11-08T06:19:57Z; original raw tool/DB metadata remains at the assessment path.

The matrix contains all **35 Critical/High matches: 3 Critical, 32 High**. Every match concerns Go stdlib go1.24.6 embedded in `/usr/local/bin/gosu`, not an established PostgreSQL database-engine vulnerability. The other 29 PostgreSQL-image matches remain in the original inventory and are not removed or qualified by this scoped study. Each row retains the original SEC001 finding ID, advisory, CVE aliases, image identity, installed version, scanner fixes, authoritative Go stdlib fixed events, platform/symbol constraints, mitigation, risk and evidence reference. Scanner fixes and newly fetched upstream fixed events remain separate: neither overwrites the historical scan.

## Independently verified static observations

The SBOM file hash for gosu is `52c8749d0142edd234e9d6bd5237dff2d81e71f43537e2f4f66f75dd4b243dd0`. Official gosu 1.19 amd64 downloaded bytes match exactly. Its detached signature verifies against fingerprint `B42F6819007F00F88E364FD4036A9C25BF357DD4`; the key is not independently identity-certified by this exercise. Public release metadata, signature, key and verification logs are retained. The binary was quarantined mode 0400 and NEVER executed. No image extraction, container/database start, migration, rebuild or runtime mutation was performed. Final-image presence is grounded in the reviewed digest-bound SBOM, corroborated by byte-equivalent signed release bytes; no independent OCI archive extraction is claimed.

A read-only ELF parser extracted Go1.24.6, gosu v1.19.0, CGO_ENABLED=0, linux/amd64 and 2,020 function names. Upstream tag 1.19 resolves to source commit `6456aaa0f3c854d199d0f037f068eb97515b7513`; fetched main.go/go.mod are source comparison only. Embedded vcs.revision is `1.19` with an epoch timestamp, not a full commit attestation. Full source-to-binary reproducible build provenance is missing.

All 35 official Go vulnerability records were fetched and reconciled to original CVE aliases and stdlib package (not unrelated x/net affected entries). No listed affected symbol was observed in the parsed function table. This is NOT an unreachability proof: inlining, dynamic calls, compiler/runtime behavior and completeness limits remain. GO-2026-6604 / CVE-2026-56857 has Windows-only upstream import constraints while the reviewed binary is linux/amd64: evidence-backed platform discrepancy for accountable review, not a suppressed or downgraded Critical finding. All 35 reachability conclusions remain INCONCLUSIVE.

## Tool limitations, failed attempts and reproduction

The command named `go` in this environment is a game, not the Go toolchain. `go version`/`go tool nm` failed; raw errors and exit codes are preserved. No govulncheck or complete call graph was run. `inspect_binary.py` implements bounded ELF/Go metadata parsing only; `qualify.py` deterministically rebuilds the 35 rows from retained source data. Run `python docs/verification/sec001-r02/qualify.py`, then `python docs/verification/sec001-r02/validate_qualification.py`. To repeat binary inspection, download the public official 1.19 amd64 asset into an owned quarantine, verify its exact hash and detached signature without execution, then run `python docs/verification/sec001-r02/inspect_binary.py QUARANTINED_FILE OUTPUT.json`. Exact fetch URLs/tags and hashes are retained under raw; archive hashes in BASELINES.json bind the original evidence.

## Disposition

No finding is fixed, waived, suppressed or severity-reclassified. Installing runtime Go does not repair statically compiled gosu. A version-number-only gosu upgrade is insufficient; previously recorded 1.20 metadata also reports Go1.24.6 and has not been qualified as a fix. A supported official PG17 candidate must be inspected for its actual compiled dependencies and immutable identity before separate implementation approval. No supported fixed candidate has been established here. See [approval request](IMPLEMENTATION_APPROVAL_REQUEST.md).

Licences/NOTICE, broader images, provider certification and registry release identity approvals remain outside this task. Independent security and DBA reviewers have NOT signed off. No production behavior, pin or release policy changed.

**SECURITY BLOCKED · CHK-001 FAIL · CHK-002 BLOCKED · RELEASE NO-GO · Collector 0.123.0 unchanged.**
