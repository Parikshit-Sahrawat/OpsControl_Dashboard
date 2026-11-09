# Bounded parallel review

501: implementation branch starts from main ffe5ac2, not PR80. PR80 958193f remains draft/unmerged. Its0040/0041 temporal writer protections are not copied, altered or weakened. Older binaries that are safely refused are not operationally rollback-compatible. Integrating that unmerged foundation requires separate candidate review; no automatic merge or migration of shared data.

503: source review identifies an unconditional fail-closed blocker: scripts/uat/pull_release.py TRUSTED_CHECK_WORKFLOWS={} while check_ci requires a complete approved mapping before any API calls. A new offline regression reproduces that refusal. This is a deterministic blocker in the published main source, not proof that it was the only failure in unavailable historical job logs. A read-only branch-protection request returned403 (protection-access.json); minimum remaining access is authorized read of protection/rulesets/review metadata plus accountable approval of the exact workflow mapping. Do not remove the guard or publish to make CI green. No publication/deployment command executed.

123: existing DEV052 security/SBOM/image/license decisions remain blockers. No newly authorized immutable image set or independent clearance is supplied. Historical match counts do not describe newly rebuilt images. Required remediation remains exact-digest provenance/SBOM/scan applicability, supported component fixes, runtime regression and accountable license/NOTICE/security review. No scans, suppressions, waivers or production changes claimed here.

201: SPOOL_TRANSACTION_CONTRACT.md supplies reviewable transaction/recovery semantics. Approval of the centralized PostgreSQL direction is preserved; exact contract review remains pending. No spool implementation started.

All nine selections Pending; historical controlled-scope approvals retained. CHK-001 FAIL; CHK-002 BLOCKED; SECURITY BLOCKED; RELEASE NO-GO.
