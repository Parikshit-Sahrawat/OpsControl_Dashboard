# Security baseline and nonzero scans

Sprint0 review date:2026-11-08 Asia/Calcutta. Application baseline `ffe5ac285ab8aef33a1139bce6f3da79be3d6d33`, tested harness `d4c5e8e24b7c9d3c62fa35a5c6ea87ec75e43e79`.


Application authorization/TLS/egress/tenant/audit/worker/retention negative suites pass within their controlled fixture scope. This is not independent security clearance. Fresh installed-environment pip-audit and frontend lock npm audit each exited1; raw results and command logs in raw/security-scans. They are findings, not waived checks.

pip-audit:10 advisory entries across3 installed packages: [{"name": "black", "version": "25.1.0", "advisories": ["PYSEC-2026-2121", "PYSEC-2026-2120", "GHSA-cg8m-r9f2-5wm2"]}, {"name": "oauthlib", "version": "4.0.0", "advisories": ["GHSA-3jp2-3mrg-2vxc"]}, {"name": "pip", "version": "25.0.1", "advisories": ["PYSEC-2026-196", "PYSEC-2026-1795", "PYSEC-2026-1796", "PYSEC-2026-2875", "PYSEC-2026-2876", "PYSEC-2026-3721"]}]. Tool reports aliases as advisory entries; no unique-CVE count or runtime/build exposure adjudication inferred. Current shared dev venv inventory, pip-check and tool version recorded in research/dependency-env-*.log. pip check passes but does not establish vulnerability clearance or clean immutable-image reproduction.

npm audit: {"info": 0, "low": 0, "moderate": 4, "high": 0, "critical": 0, "total": 4}. Affected package entries are @eslint-community/eslint-utils, @eslint/config-array, eslint and minimatch. Four moderate package entries are not automatically four distinct CVEs. Development/build/CI exposure still needs evidence-backed triage; do not silently waive because tools may be devDependencies.

No Grype/Syft/Trivy executable was found in inspected available locations. Final immutable application image identities and image-level OS/transitive SBOM/scans were not established by Sprint0. Image security coverage BLOCKED/NOT TESTED, not0findings. Only task fixture PostgreSQL/TLS identities are recorded in cleanup; they are not approved production image inventory. No install/build/publish workaround or risk waiver. Existing release security/license/NOTICE and High risks remain BLOCKED; proposed Sprint9 maps remediation/scans and accountable review.

Source dependency reuse: existing venv/node_modules used to run main; installed versions recorded and dependency consistency checked. A clean isolated release-image build/pinned scanner DB is not claimed. pip-audit service/database timestamp is not separately supplied by raw output; do not invent one. Full dependency/image/secret/supply-chain certification requires exact candidate/provenance and future reviewer evidence. Limited artifact token/private-key pattern checks protect this evidence export, not an independent secrets audit.


**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO · formal owner UAT PENDING · development closure NOT COMPLETE.**

Environment applicability clarification: direct main runtime pins compared against the installed environment all match. The dev Black pin is26.10.1 but installed Black is25.1.0; source bootstrap pins pip26.2 while installed pip is25.0.1. oauthlib4.0.0 is an extra installed dependency, not a direct main runtime requirement. Thus the10advisory entries are actual installed-test-toolchain findings, not a verified vulnerability inventory of current declared source or final runtime images. First reconcile/rebuild a clean isolated candidate before assigning production exposure or repeating remediation already present in source. No source dependency was changed in Sprint0. See research/dependency-pin-comparison.json.
