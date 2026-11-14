# APTRON-ENG-001 — First product-foundation implementation

Owner-authorized engineering slice, 14 November 2026. Draft PR #105; owner UAT/visual acceptance pending. No merge or production readiness claim.

## Source and authority

- The owner's current six-step request authorizes this bounded implementation and draft PR. It supersedes the earlier audit's read-only boundary for this slice only.
- Read the current Google Drive `APTron_ENG-001_ReadOnly_Repository_Readiness_Audit_v1.0.md`, ID `1iiPFQC_B3sr4bNYnx44e-rtjv9m6131H`; cross-checked the associated readiness register and executive memo. The separate historical `docs/engineering/ENG_001.md` is retained unchanged.
- Main was checked through GitHub and `git ls-remote`: `2e4fe5d8cb0f39170b0d789fdd7e07be4ac0219a`.
- Branch: `feat/aptron-product-foundation-20261114`.
- Initial implementation commit: `58d229934a365e3703aac752c949f9f520a1b38d`; tree: `6b9128fca26dd31bd98a0096aea9c8ee0f4e4009`.
- Legacy harness alignment: `c9a584b617a4f614e5a25e7485f3e0b45375f85c`, tree `0f5f687488961cc110f255179775771f24151c87`; replace contradictory dedicated-Incidents UI assertions with absence plus a historical incident API read. Backend lifecycle/recovery/note/tenant probes remain mandatory and unchanged.
- Tenant fixture correction: `762ed6bb038584406c76181f19b3dc899fe25928`, tree `6ecc00825e74010c2f52baa3f6b0d27c9a799f7d`; explicitly select a real authorized customer through the UI before operational bookmark checks. Product source remains unchanged from c9abf512.
- Browser harness correction: `f737a730195eeb66cfdc4a909af2e468e81ce67e`, tree `dfcdb6dd32b424091ce99a0e3322db349a4eda2e`; wait for the rendered selector after navigation/reload, preserving exact expected values, and capture failures. Product source is unchanged from c9abf512.
- Contract correction: `c9abf51232b15aa892706a135c5d821942dbd65c`, tree `db036c1cb43bcf7ea67cdecfe397e3f336d680ca`; removes the mistakenly added standalone Event Parameters selector option.
- Local source was committed before publication; the GitHub-created commit has the exact same tree. Git CLI push failed for missing CLI credentials; publication used the connected GitHub account. No force push or main write occurred.

## Reconciliation and bounded changes

| Candidate | Frozen source | Disposition |
| --- | --- | --- |
| #89 | `ecfdff2cf3f9d1a7b7b284e79a7f708d1baea8ce` | Select only incident-UI exclusions: app import/render, navigation permission, pipeline incident page/tab removals and retained historical correlation label. No broad integration, backend, templates, filters or global-search changes. |
| #103 | `83e935eaa492ea83597e6daaa75f152006bd907f` | Stacked on #89. Adapt three guarded domain hashes, domain-to-section mapping and existing inventory selection to main. Do not copy the parent workspace or catalogue. Monitoring Templates entry is deferred because main lacks that approved standalone section. |
| #104 | `90a97485d2588f522f9736265015d570cbb96652` | Adapt Help only and copy four public guide assets into the frontend distribution. Relative same-origin links avoid depending on unmerged main documentation or requiring GitHub access from a customer deployment. Retain activation FAQ and profile logic. Qualify legal/distribution and future-capability claims. |

`PR_RECONCILIATION.json` records complete changed-source lists, total changed-file counts and full changed-path-list SHA-256 relative to each relevant base, plus intersection with this slice. `CODE_FILES.txt` is the final 40-file implementation allowlist. Historical acceptance harness entry-label updates account for many files; this is not a 40-feature change.

APTron Observability appears in the browser title and sign-in; the header displays APTron / OBSERVABILITY. Reuse the existing neutral monitoring glyph and visual system; this does not certify a new logo or trademark. Internal storage keys, session keys, ETL domain identifiers, server permissions and wire headers retain their exact existing identities. Operations destinations retain their existing monitoring contracts; native SOS/JS7 behavior is not added or claimed.

Resource Management lists Compute Instances, Data Pipelines and APIs directly. Existing data-resources bookmarks remain guarded aliases. Child routes, selector and domain tabs share the existing VM/ETL/API inventories. Visibility derives from existing permissions; roles do not grant invented authority.

Dedicated Incidents pages, navigation and pipeline incident tabs are removed. Backend incident APIs, migrations, historical rows, incident-state contracts, correlation identifiers, execution audit/recovery and Alerts remain. Historical backend tests actively verify failure/retry/recovery evidence rather than interpreting removed UI as deleted data.

Help has Documentation / Learning / Training, deployment and cost responsibilities, safe lab boundaries and locally shipped links. FAQ summaries participate in modal keyboard wrapping, Escape and focus restoration. No tenant/customer payload is published in these guides.

## Validation results

These suites overlap. Do not add their counts as distinct coverage.

| Execution | Result | Evidence |
| --- | --- | --- |
| Frontend Node suite | 39 PASS, 0 FAIL, 0 SKIP | `frontend-tests.log` |
| ESLint | PASS | `frontend-lint.log` |
| Deployed guide link smoke | 3 HTTP 200 responses; local relative guide/CSV links exist | `bundled-guide-links.json` |
| Vite production build | PASS; existing >500 kB chunk warning | `frontend-build.log` |
| Backend compileall | PASS | command below; quiet on success |
| Backend discovery, ordinary test mode | 552 run = 332 PASS + 220 SKIP, 0 FAIL | `backend-discovery.log` |
| Isolated PostgreSQL 16.2 fresh migration + Alembic check | PASS | `pg-migration.log`, `pg-schema-check.log` |
| Real PostgreSQL ownership, RBAC and retained incident/history suites | 118 PASS, 0 FAIL/SKIP; unittest module imports can overlap | `pg-tenant-rbac-history.log` |
| Actual HTTP workflow | 9 groups PASS | `pg-http-workflow.log`, `api.json` |
| Actual HTTP authorization | 14 groups PASS | `pg-http-rbac.log`, `sprint08-http.json` |
| npm audit, including dev dependencies, moderate threshold | 0 advisories | `npm-audit.json` |
| pip-audit runtime requirements, strict | 41 dependencies, 0 advisories | `python-audit.json`, `python-audit.log` |
| Scope/workflow policy | PASS; all dispositions RUN; 13 required contexts retained | `ci-policy-final.json` |
| CI policy regression suite | 23 PASS | `ci-contract-tests.log` |
| Hosted foundation browser at 762ed6bb | PASS, 5 targeted groups; screenshot review completed | `final-aptron-foundation-browser.json`, CI artifact 14095231791 |
| Local Chromium | BLOCKED: Unix-domain socket operation denied by execution runtime | failure record below; not an accessibility pass |
| Local Docker/image scans | NOT RUN: Docker unavailable | existing security blockers retained |

The local PostgreSQL distribution is test-only pgserver 0.1.4 / PostgreSQL 16.2, bound to random loopback TCP with Unix sockets disabled. No shipped requirement, database image or deployment configuration changes. CI remains the PostgreSQL 17 verification target. Test fixtures and generated passwords lived in private temporary directories; owned API/PostgreSQL processes stopped after execution. No customer or production target was contacted.

## Commands

Run from repository root unless a `cd` is shown. Exact inner PostgreSQL/API invocations and isolated environment construction are in `run-local-pg.py`; it creates its own fresh directory and fixtures and never uses a configured customer database.

```sh
npm ci --prefix frontend --no-audit --no-fund
python -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements-providers.txt -r backend/requirements-hosts.txt
backend/.venv/bin/pip install pgserver
backend/.venv/bin/pip install 'pip-audit>=2.9,<3'
npm test --prefix frontend
npm run lint --prefix frontend
npm run build --prefix frontend
ENVIRONMENT=test backend/.venv/bin/python -m compileall -q backend/app backend/migrations
(cd backend && ENVIRONMENT=test .venv/bin/python -m unittest discover -s tests -v)
backend/.venv/bin/python docs/verification/aptron-foundation/run-local-pg.py
npm audit --prefix frontend --audit-level=moderate --json
backend/.venv/bin/python -m pip_audit -r backend/requirements-providers.txt -r backend/requirements-hosts.txt --strict --format json --output /tmp/aptron-python-audit.json
backend/.venv/bin/python scripts/ci/policy.py
backend/.venv/bin/python -m unittest discover -s tests -p 'test_ci_*.py' -v
node --check frontend/scripts/aptron_foundation_acceptance.mjs
node --check frontend/scripts/full_closure_acceptance.mjs
git diff --check
git diff --exit-code origin/main HEAD -- backend agent deploy .github docker-compose.yml docker-compose.demo.yml
```

The ordinary backend discovery skips PostgreSQL-dependent tests by design; the separately enabled owned PostgreSQL tests above are not counted as those skipped tests passing. Exact PostgreSQL commands include `alembic upgrade head`, `alembic check`, `unittest tests.test_pipeline_ownership_v16 tests.test_sprint08_rbac tests.test_pentaho_incident_r1 -v`, `scripts.v16_api_probe` and `scripts.sprint08_http_probe`.

## Failures, corrections and limits

1. After removal of pipeline Incident Correlation, the old Node assertion expected six pages and failed (38 PASS / 1 FAIL). Updated to five pages while preserving all seven historical incident states. The excluded dedicated-navigation assertion now rejects legacy incidents.view, including admin navigation. `frontend-initial-failure.log` retains the failure; final suite passes.
2. Scope policy initially rejected changed test names/new inventory. Updated exactly two renamed test records and one new mandatory role/route security test. Every unrelated manifest row and protected assertion is unchanged; no required context, workflow trigger, threshold or release gate changes. Initial failure is retained.
3. pgserver's default startup failed because Unix-domain sockets are not permitted. Explicitly bound the disposable PostgreSQL process to loopback TCP and disabled Unix sockets; all listed PostgreSQL/HTTP checks then passed. PostgreSQL 16.2 does not establish PostgreSQL 17 parity.
4. Local Chromium launch using installed Playwright and `/usr/bin/chromium` failed with `browserType.launch: Target page, context or browser has been closed`; Unix socket creation separately returns `PermissionError: [Errno 1] Operation not permitted`. No local screenshot or accessibility pass is asserted.
5. Local `bash scripts/check-workflows.sh` completed without output, but its individual exit status was not separately captured. Hosted Scope and Workflow Integrity run `43547400251` succeeded and includes the pinned actionlint check. No workflow file is changed.
6. Native Collector migration, SOS/JS7 certification, Synthetic/RUM, license selection and release qualification are deferred. The pre-existing OTel 0.123.0 runtime boundary is unchanged. The guides describe future curriculum, not implemented certification.
7. #104 CI run `43537886852` / job `132271555104` fails in `ci_scope_acceptance.mjs` after earlier workflow/browser groups pass. Main still offers the excluded Incidents entry; its presence conflicts with that check. This is an observed mismatch, not proof that no other failure exists. #104 image run `43537886575` / frontend job `132271635130` explicitly reports `Unresolved High/Critical/unknown severity matches: 155`. This slice does not remediate or waive those image findings.
8. Historical browser scripts dedicated to the retired pipeline incident UI (for example Sprint 07) are historical evidence tools, not current acceptance for an excluded feature. The current scope gate verifies absence instead. No historical evidence package is erased or reclassified as a new pass.

9. Initial CI staging browser capture run `43547400087` / job `132301801218` failed: `Standalone Event Parameters option unexpectedly present` (RM-DEF-034). This slice had added that selector option while adapting domain navigation. Removed the addition in `c9abf51232b15aa892706a135c5d821942dbd65c`; existing negative assertions were not weakened. Frontend lint/build re-run PASS; new CI run required.

10. Corrected-source CI staging run `43547694617` / job `132302732465` PASS, including authenticated capture, onboarding, role-restricted navigation and PostgreSQL 17.12 preservation/security checks. Artifact `14094289843` SHA-256 `4ea65a90f7525edfbd6b70d2259c20fd0ba19f4c3227fa1a98a48e8caa9926d4`; inspected the captured resource-management page. This retains inherited legacy pipeline descriptions; it is not a full native APTron migration or final visual acceptance.
11. Corrected-source image-security run `43547694744` remains FAIL. Frontend job `132302733332` again reports 155 unresolved High/Critical/unknown matches. Runtime dependency audits passing does not supersede this candidate-image failure.

12. On c9abf512, PostgreSQL 17 migration/preservation and actual HTTP workflow PASS; existing pipeline eight-step/mobile browser and five Chromium authorization groups PASS. New foundation domain assertion failed because it immediately read the previous selection (`data-pipelines`) while expecting the just-selected `apis`. Added a wait for the expected rendered selector value, with the same equality assertion and failure screenshots, in f737a730. Artifact `14095116613` retains this failure; its SHA-256 is `b0a036e8304647204fdc54454a982cf5dd22ab588360ab34ae15f8a12e58a803`.

13. On f737a730, the next foundation assertion timed out waiting for Pipeline Inventory because Resource Management uses independent filters and no global operational customer had been selected. The captured UI correctly showed `Select a customer with etl.view permission`; it did not leak an unscoped inventory. Updated only the fixture to select Controlled HTTP A through the actual organization selector in 762ed6bb. The authorization guard and expected inventory/absence assertions are unchanged. Failure artifact `14094947940`, SHA-256 `056557f6e07658054924f3762679f1972d849231862ad216c5bc453f8e4c7715`.

14. On 762ed6bb, PostgreSQL API and Browser Integration run `43548638452` PASS: jobs `132305700653` (app-api-browser), `132305700931` (real-postgres-migration), `132306752421` (sprint-evidence). `final-aptron-foundation-browser.json` records all five foundation groups PASS, including light/dark at 390/768/1366, local guides, role filtering, retired bookmark and keyboard focus. Artifact `14095231791` SHA-256 `8abd120ce6f54ba97301fc80d3ce7fe8e8ecbb72ed1f15d1dc6c49aabda55cff`. Inspected the 390px light and 1366px dark Help captures.
15. Later legacy Native Monitoring run `43548638666` failed in its browser script despite runtime/API engine PASS. Source inspection found it explicitly requires one Incidents nav item and drives the removed page. In c9a584b6 align that harness to absence and historical API preservation; retain independent existing backend transition/note/recovery/tenant probes. Its report now explicitly says incident_ui=false, excluded_incident_ui=true. Do not present this as new native Collector certification.

## Final tested source and hosted CI

Final code commit: `c9a584b617a4f614e5a25e7485f3e0b45375f85c`. Product source remains exactly c9abf512; later changes reconcile test timing, authorized fixture scope and retired UI assertions.

- PostgreSQL API / Browser run `43549232174`: PASS, including all five foundation groups and required PostgreSQL 17 checks. App/browser job `132307598114`; artifact `14095800513`, SHA-256 `fd115bfb49dc6bda7d761007c6c561d7244951dea895b495d28c7b17ad348f6c`. The `final-*.json` files are extracted from this exact artifact.
- Native Monitoring Contracts run `43549232317` / job `132307598559`: PASS after aligning the historical harness; legacy runtime boundary remains unchanged.
- Snapshot: **15 workflows success, 1 failure, 1 in progress**. The failure is Image SBOM Vulnerabilities and Licenses run `43549232226`. Integrated Quality Regression run `43549232177` was still running. This is not a blanket green-CI assertion. See `CI_RESULTS.json` for exact source/run IDs and states.
- Screenshot files retained here originate from the passing 762ed6bb run; their product/UI source is identical to the final code. Inspected light/mobile and dark/desktop. Owner visual acceptance remains pending.
- Main recheck remains `2e4fe5d8cb0f39170b0d789fdd7e07be4ac0219a`; PR #105 remains draft and unmerged.

## Review and unchanged gates

CI source commit and run IDs are recorded separately. The existing authenticated scope check now runs the new foundation assertions without changing workflow files: three domain routes/reload, excluded incident bookmark, real-viewer permission filtering, 390/768/1366 Help containment in light/dark themes, three local guide responses, FAQ Tab wrapping, Escape and focus return. These are targeted accessibility checks, not comprehensive WCAG/assistive-technology certification.

No backend/migration/agent/deploy/workflow/Compose source delta. No production deployment, provisioning, purchases, HSM/KMS actions, infrastructure changes, destructive DR exercise, automatic release-gate change, merge, branch deletion or old PR closure. Customer data and server-side security remain authoritative.

**SECURITY BLOCKED · CHK-001 FAIL · CHK-002 BLOCKED · RELEASE NO-GO · owner visual/UAT acceptance PENDING.**
