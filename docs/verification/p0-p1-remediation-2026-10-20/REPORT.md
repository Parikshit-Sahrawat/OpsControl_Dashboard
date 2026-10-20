# P0/P1 remediation — candidate acceptance

Status: **DELIVERED — RUNTIME REMEDIATION INTEGRATED AND REMOTE SOURCE VERIFIED**. Production remains NOT READY; independent remediation UAT remains pending. Runtime/main acceptance commit: `e7c31b7a54efa46f89b468f9df94c7928ef99a0d`. This containing follow-up is documentation/evidence only; use Git for its own SHA. [Final integration ledger](INTEGRATION.md) supersedes the earlier candidate-pending state.

Repository: `Parikshit-Sahrawat/OpsControl_Dashboard`. Temporary branch: `fix/audit-p0-p1-remediation`. Audited/unchanged remote main: `c694af45055557b062bedeb974d73140ac75c6c9`. Implementation commit: `efabfb0f1d712d5b34ca2c018f29bf03bd8383f2`; exact runtime content is independently frozen in [source hashes](evidence/runtime-source-sha256.json). Tests before commit ran this working source, not pristine baseline.

Both confirmed P0 defects are locally corrected and regression-proven. The audit's partial batch0/3 now persists3/3 native observations in actual PostgreSQL; repeated/empty partial polling is idempotent and preserves history. Missing/contradictory native proof cannot fabricate success or erase the last defensible outcome; canonical conflicts enter existing review/quarantine. Native Y/N/status/errors, copied step metrics and transport health/completeness remain distinct through fenced ingestion, persistence, authenticated API and UI. Repeated observed step rows remain distinct without inventing a native child UUID.

Authorized P1 corrections cover atomic inline customer/resource onboarding, scoped/stable server pagination and full selector traversal, bounded dependency history, current browser contracts, supported CI runners and previously skipped PostgreSQL coverage wiring. Main's canonical ORM registration, authorization resolver, schema/migrations and grouped/six-page UI remain intact. Five selected reviewed parser/adapter/legacy ingestion units and related tests came from local `feat/pentaho-carte-compat-001@49b0c505a837753dd1f28c155d10a0f3933bc9c3`, followed by narrowly scoped integration corrections on main; no whole branch merge.

## Acceptance snapshot

- Full owned PostgreSQL regression:503 passed,0 failures/skips; all discovered backend modules, fences/replay/source ownership and customer isolation.
- Focused native compatibility:92 passed,0 failures/skips; new actual database/HTTP remediation tests8/8 (also included in503).
- Authenticated V16/Sprint03–09 API47 groups pass. Chromium V16wizard, Sprint07 seventeen groups, Sprint08 five, Sprint09 three pass.
- Actual Agent/Contrib/verifiedTLS runtime passes; ARCH browser wizard/configuration/reporting and AccessV1.5 five groups pass after correcting explicit-scope/mobile test setup.
- UI recovery52 checks; separate Access25 HTTP/seven Chromium groups; frontend lint/five unit files/build and scoped Python/workflow/security checks pass.
- Critical backend/Agent combined line+branch coverage **81.28%**, unchanged80% gate; no modules excluded or thresholds lowered.
- Populated migrations/ORM drift/prohibited populated downgrade and REC01–06 restore/legal-hold preservation pass; no new migration. Local backup0.369s/restore0.890s is not a production RPO/RTO guarantee.
- Actual five-service Docker build/start/restart/auth passes, including226 API/worker source comparisons; temporary build-only environment CA trust described in verification. No deployment setting changed.

Exact commands, skips, initial failures and evidence maturity: [verification](VERIFICATION.md). [Changed files](CHANGED_FILES.md), [all finding dispositions](DISPOSITIONS.md), [readiness](PRODUCTION_READINESS.md), [roadmap amendment](ROADMAP_UPDATE.md), [independent UAT checklist](MANUAL_UAT_CHECKLIST.md).

## Integration control and result

Mandatory local and exact-commit CI gates passed before integration. Fetch/recheck main immediately before fast-forward integration; reconcile concurrent changes rather than overwrite them. Run post-integration smoke/targeted regressions, normal non-force push only, then verify remote SHA and runtime tree against this snapshot. The normal push succeeded and fetched origin/main matched the accepted commit. No bypass, PR or deployment occurred. PR33 is read-only and its state/head remained unchanged in the recorded checks.

The original audit package and all historical sprint evidence remain unchanged. [Protected-file integrity](evidence/protected-integrity.json) covers approved architecture, migration history and native artifacts. No protected customer identities/records are rewritten. Runtime experiments used disposable owned PostgreSQL and synthetic/sanitized fixtures only.

## Remaining issues

Production **NOT READY**: all six P0, eight P1 and two P2 production-readiness gaps remain open/partial at certification level. Canonical shared-resource multi-customer positive behavior (XBA06) is absent; optional legacy method attribution is an open policy question (XBA16). Graph/aggregate/fence performance, external-client adoption, fleet lifecycle, notifications, real provider/CA/private-route/offsite/PITR and storage/log cost evidence remain. Independent remediation UAT is pending. Historical IMP001–062 remain source-unrecovered and18OC-IMP proposals individually unapproved. RT001–020 **NOT RUN**; native repeated child identity **UNVERIFIED**.

Next bounded proposal: close exact-source CI/integration and owner UAT, then seek specific approval for shared-resource association/attribution design before any schema/runtime increment. See [proposal](NEXT_SPRINT_PROPOSAL.md). No numbered future sprint, ETL workload, customer-source activation, deployment, branch deletion, history rewrite or PR33 modification occurred.

Known adapter bounds remain explicit: numeric native input accepts up to seven decimal digits and at most100 structured step observations. Larger ranges/builds are not certified by these fixtures and can be rejected; no clamping, manufactured zero or unbounded native compatibility is claimed. Static offset pagination is deterministic; it does not provide a snapshot across concurrent dataset mutation. These limits and genuine child identity require separate representative evidence rather than an invented capability claim.
