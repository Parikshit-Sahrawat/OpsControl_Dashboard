# DEV-05.2A — Strict production security gate

Status: **APPROVED POLICY; IMPLEMENTATION AND SCANS PENDING**  
Scope: draft PR #69, branch `release/dev-05-2-hardening`.  
Release decision: **NO-GO**. This document is a gate specification, not scan evidence or release approval.

## Decision
Unresolved **applicable High/Critical** vulnerabilities in deployable runtime images or their effective supply chain block production release. Development/CI-only advisories can be classified **not applicable to production** only with evidence showing that affected components and exploit paths are absent from production. They still require tracked CI/build-environment mitigation where relevant. Findings of lower severity require documented triage, remediation scheduling or risk acceptance. Any exception to a mandatory gate requires explicit accountable security/release-owner approval; this document grants none.

## Required inventory and provenance
1. Enumerate all production-deployable backend, frontend/web, worker, collector and ancillary images from Dockerfiles, Compose, CI and deployment manifests. Record name, build context, base image, runtime role, architecture, source revision, immutable digest and deployment inclusion. Exclude test-only images explicitly with evidence.
2. Produce **CycloneDX or SPDX image-level SBOM** for every in-scope final image digest, including OS packages and transitive application dependencies. Record tool/version, commands, timestamps and SHA-256 of raw artifacts.
3. Run vulnerability scans **against those exact immutable digests**, not only source requirements or the Python environment. Include scanner version, database timestamp, CVE/GHSA identifiers, severity, fixed version, package layer/location and exploitability context. Never present a missing scanner, unsupported platform, or failed scan as PASS.
4. Collect license inventory for direct, transitive and base-image dependencies, verify redistribution obligations and NOTICE inclusion where applicable, and record approval/exception. Contrib upstream Apache-2.0 does not establish transitive clearance.
5. Keep supply-chain inputs pinned where practical; validate image/source digests and reject mismatches. Do not embed or publish secrets in evidence.

## Nine previously observed Python environment advisories — pending triage
- **Black 25.1.0 (3)**: PYSEC-2026-2121 / CVE-2026-32274 (cell-magic cache filename); PYSEC-2026-2120 / CVE-2026-31900 (Black GitHub Action `use_pyproject`); GHSA-cg8m-r9f2-5wm2 / CVE-2026-114134 (Black Action `required-version`). Verify whether Black and the vulnerable action/configuration run in CI and whether Black exists in any deployed image. Audit indicates fixes 26.3.1, 26.3.0 and 26.10.1 respectively; independently validate compatible remediation before changing pins.
- **pip 25.0.1 (6)**: PYSEC-2026-196 / CVE-2026-8643 (entry-point path); PYSEC-2026-1795 / CVE-2025-8869 (tar symlink fallback; Python/PEP 706 applicability); PYSEC-2026-1796 / CVE-2026-1703 (wheel extraction); PYSEC-2026-2875 / CVE-2026-3219 (ambiguous archive); PYSEC-2026-2876 / CVE-2026-6357 (self-update import); PYSEC-2026-3721 / CVE-2026-13346 (doubly encoded package URL). Verify whether pip exists in runtime images, build stage only, or developer environment, plus package-index trust and installation privileges. Audit lists fixes through pip 26.2; validate compatibility and installation-time exposure.
- For **each** of the nine, record `package, installed_version, advisory, affected_surface, runtime_present, reachable_path, severity, applicability, mitigation/fix_version, test_evidence, disposition, reviewer, review_date`. Valid dispositions: FIXED, NOT_APPLICABLE_WITH_EVIDENCE, ACCEPTED_EXCEPTION_WITH_OWNER, UNRESOLVED. An unreviewed advisory remains UNRESOLVED.
- Prefer not shipping formatter/build tools in final runtime images. Keep build/CI trust risks visible even when production-not-applicable.

## Gate outcomes
- **PASS**: all final images inventoried, digest-pinned, SBOMed and scanned; license review signed; no unresolved applicable High/Critical; nine findings triaged with evidence; security/release owner approves.
- **BLOCKED**: missing image, digest, scanner, SBOM, license inventory, owner approval, or material applicability evidence.
- **FAIL**: verified unresolved applicable High/Critical or violated provenance/secret-control policy.
- Overall DEV-05.2 release remains **NO-GO** irrespective of DEV-05.2A result until provider, CI and operational gates are independently satisfied.

## Evidence deliverables (do not premark PASS)
`docs/verification/dev052/security/` should contain dated inventory, advisory-triage matrix, per-image SBOM/scan metadata and hashes, license decisions, redacted tool logs, explicit exceptions and a signed gate decision. Keep original DEV-05.0 and DEV-05.1 evidence unchanged. Use only scoped ephemeral build/scan resources; no production deployment, auto merge or broad Docker cleanup.
