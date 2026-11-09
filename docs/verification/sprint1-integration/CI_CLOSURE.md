# Consolidated CI refresh and remaining gates

## Baseline and enforcement

Main `2e4fe5d8cb0f39170b0d789fdd7e07be4ac0219a` includes merged CI85. Integration head originally d03579b had no six-branch product integration. Active ruleset26082467 retains13 required official GitHub Actions contexts, strict up-to-date enforcement and one independent PR approval. Authorized API credentials report repository-admin access; that is permission to perform approved changes, not proof that replacements passed.

The complete workflow/job/trigger/command inventory is CI_WORKFLOW_INVENTORY.json; CI_CHECK_EQUIVALENCE.json maps every legacy required check and additive candidate. All28 workflows remain. No required check or security job was retired. Frontend build/unit executions overlap between validation, staging and broad quality, but those workflows also exercise distinct schema, TLS, packaging, fault, browser and legacy compatibility contracts. Consolidation needs exact-head equivalence first. Live-provider and privileged release/UAT workflows remain separately manual/gated. No publisher, image digest, vulnerability threshold, licence requirement, permission catalogue or bypass actor was changed.

## Repairs

- `app-api-browser`: baseline run42494607204 reached ci_scope_acceptance and failed the Incidents exclusion assertion. Integrating86 preserves the assertion and retires navigation/routes while keeping background processing. New source-revision tests run as an additional actual PostgreSQL/HTTP step; authenticated workspace separately exercises React/Playwright. ETL reload diagnostics also found erroneous token invalidation on aborted auth verification; retain token only for transport failure, but withhold protected UI, and clear it on authoritative401/403.
- `sprint-evidence`: a fail-closed aggregate of both integration prerequisites, not an independently broken test. Keep require_success unchanged; never convert failed/skipped/missing prerequisites into success.
- `image-evidence`: baseline run42494607265 produced all seven immutable-ID SBOM/Grype/licence artifacts. The PostgreSQL job reported129 High/Critical/unknown matches (4 Critical +125 High). All roles have unresolved matches and pending accountable licence review; see hosted-baseline raw finding records. These are genuine policy failures, not upload defects. No security findings were removed or downgraded. Seven archives total6,357,071 uploaded bytes in this run; Grype cache payloads are excluded and metadata/checksums retained. These observations belong to the historical synthetic merge source recorded in each artifact, **not** the new consolidated candidate.
- `security-sbom`: correctly fails when any image gate fails. Keep its dependency and policy checks intact. A green aggregation or complete inventory cannot certify independent release clearance.
- Workflow integrity: pin inherited ETL Node action; align new resource workspace with action-lock, credential non-persistence and all-PR triggers. Preserve original check identities and protected assertions. Regenerate test inventory as a union of all merged tests, retaining UNKNOWN tests as RUN; no exclusion by filename.

## Required-status transition

RULESET_ADDITIVE_PROPOSAL.json preserves every existing rule/context/approval and proposes adding scope-policy, unit-and-build, real-postgres-migration, app-api-browser, sprint-evidence, security-sbom and authenticated-workspace. No context replacement/removal is authorized by unverified equivalence. Only apply after checking live ruleset drift and exact final-head official check identities. Actual attempt: HTTP403 Resource not accessible by integration, despite repository.admin=true. Re-read confirms13 original contexts/rules unchanged; see RULESET_UPDATE_RESULT.json. No check was added or removed. Administration-write permission is required; do not bypass. A proposal is not proof of an applied change. Never weaken rules just because a new security check fails.

## Remaining blockers

1. Exact-head hosted results must be recorded independently of historical green runs. Trigger-and-Exit means newly triggered results remain PENDING until owner/reviewer inspection; do not claim completion while pending.
2. Fresh final-candidate seven-role image evidence cannot be generated locally on a Docker backing filesystem with350MiB or less free (observed0 during tests). No broad cleanup is authorized; use hosted isolated runners or provision adequate owned storage. Historical image findings and legal review remain unresolved.
3. Accountable per-component licence/NOTICE/source-offer/application licence review is absent. Inventory does not supply a reviewer signature.
4. Full source-context writer compatibility, provider-specific applicability and outstanding configuration UX/fault cases remain in CONFIGURATION_CONTRACT.md. CI must not certify unimplemented contracts.
5. Independent PR approval, owner visual acceptance and formal UAT/provider qualification remain separate. No merge, deployment or release promotion.

CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO · Sprint1 NOT COMPLETE.

## CI005 plus sequential issue95

[Exact72382ad failures and local recovery](ci005-2026-11-09/REPORT.md) distinguish actual subprocess failure, controlled runtime PASS and missing historical private stderr. Scope now includes814 reviewed/retained entries;786 UNKNOWN still RUN. [Issue95 guard](arch95-2026-11-09/REPORT.md) adds only explicit exact-ID provenance preparation to the2 existing root-test workflows. All28 workflow definitions and13 required check identities remain intact. Final18 PR-safe workflows are triggered on the new combined SHA and handed off RESULT PENDING under Trigger-and-Exit. No live provider/publisher/UAT workflow is authorized.
