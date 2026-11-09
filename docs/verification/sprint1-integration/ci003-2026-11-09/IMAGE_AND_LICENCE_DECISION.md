# Security decision — BLOCKED / no waivers

Hosted run42532627047 scans candidates for head54f26e5; raw provenance identifies each actual synthetic merge source, immutable local image ID and SBOM/scan hashes. No images were published. Every original match is retained in CVE_REMEDIATION.csv, not silently deduplicated or excluded.

| Role | Critical | High | Unknown | Current blocker |
|---|---:|---:|---:|---|
|backend-runtime|0|59|0|Debian package advisories; vendor-wont-fix is not an exception; supported base/compatibility and accountable applicability review needed|
|backend-migration|0|59|0|Same vendor findings; preserve migration tooling and PostgreSQL safeguards|
|frontend|0|0|0|3 Medium matches retained; accountable licence/NOTICE review still absent|
|ingestion-gateway|0|0|0|3 Medium matches retained; accountable licence/NOTICE review still absent|
|postgres|3|32|0|Go stdlib findings in official gosu; preserve required entrypoint dependency; supported upstream rebuilt binary/image needed|
|otel-contrib|19|81|2|Compiled dependencies of exact pinned0.123.0; no upgrade/custom binary authorized|
|uat-backend|19|140|2|Includes collector compiled findings plus Debian packages; pending licence review|

Current984 all-severity matches versus1,890 in the previous retained baseline:906 fewer matches across different rebuilt image identities. This is a match-count comparison, not906 unique CVEs fixed or a release-wide clearance. High/Critical/unknown policy matches reduce874→416. Python Critical and frontend/gateway High/Critical reductions are evidenced by exact scans, not inferred solely from updated tags. Scanner/tool/database versions and source provenance are retained per role. Future final-head candidates must be scanned anew; these are not final HEAD results.

Collector0.123.0 and digest e39311df1f3d941923c00da79ac7ba6269124a870ee87e3c3ad24d60f8aee4d2 remain unchanged. Resolving compiled findings requires separately approved supported transition, compatibility/rollback and qualification evidence; no fork, rebuild or waiver is invented. Removing gosu/essential libraries to conceal advisories is prohibited. Debian wont-fix cases require actual distro advisory/exploit-path/support assessment and supported alternative-base testing, not blanket dismissal.

LICENCE_NOTICE_REVIEW.csv contains2,451 component/role records with declared expressions, required review and accountable reviewer NOT_ASSIGNED. This is **technical triage by Codex**, not completed legal/distribution review. For each exact component, inspect authoritative source/licence/copyright and bundled notices, source offers/corresponding source for GPL-family obligations, LGPL relinking/modifications where applicable, Apache NOTICE/changes, and direct/transitive/base distribution scope. UNKNOWN metadata must be recovered. SPDX metadata alone is insufficient. No project root LICENSE/NOTICE was found in the tracked baseline; the application licensing/distribution decision must be recovered or explicitly supplied by its accountable owner.

Minimum closure prerequisite: assign an accountable legal/compliance/distribution reviewer, supply authoritative application licensing and exact component/NOTICE/source-offer evidence, and obtain independent security review of remaining findings. Inventory completeness, task authorization or a green workflow does not supply those signatures. Keep licence gate PENDING_ACCOUNTABLE_REVIEW; never fabricate REVIEWED.

Full application image builds cannot run safely on this managed Docker backing disk with0–350MiB free; tiny trust-mount proof is separate. No unrelated images/caches/volumes were removed. Final hosted seven-role build/scan remains PENDING, all thresholds and aggregators remain enforced. Manual publication workflows are not enabled or exercised; any analogous missing build-trust wiring there requires its own reviewed correction before use.

SECURITY BLOCKED · RELEASE NO-GO.
