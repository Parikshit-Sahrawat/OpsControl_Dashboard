# Test, defect, security and qualification disposition

This is a source/evidence review, not a new security certification or a silent waiver. Current correction execution is in the linked [visual report](../oc-dev-comp-001-visual-correction/REPORT.md).

| Item | Evidence/status | Sprint1 versus later scope |
|---|---|---|
| Prior visual candidate | Owner explicitly REJECTED; correction has new desktop screenshots and tests, owner review still pending | Direct Sprint1 acceptance blocker |
| Incomplete applicability/history/writers | Source-confirmed deficiencies listed in REPORT/register; not represented as newly reproduced exploit outcomes | Direct COMP-S01-02 technical blockers; policy/design followed by separately authorized backend/database work |
| UI correction first lint failure | `innerWidth/innerHeight` unqualified identifiers; corrected to window properties | Actual failed attempt preserved; focused final frontend checks rerun |
| First browser failure | Flyout anchored slightly within sidebar; fixed using nav edge | Actual failed attempt retained; subsequent position check passes |
| Second browser failure | Existing pipeline test expected an always-expanded Resource Management group | Updated navigation path explicitly expands category; full original business assertions retained; main integration rerun passes |
| Operator fixture failure | User creation422 because ordinary users require existing Department | Corrected test onboarding only; no backend/RBAC bypass. Final evidence must show Department + separate customer operator membership. This demonstrates separation, not a product defect |
| Backend focused regression |68 tests at c460426 passed; final focused12 in separate exact-source run | Repeated subsets overlap; do not add to original564 unique discovery count |
| Historical broad backend |562 pass/2 skips at95b4ab6; unchanged backend byte comparison retained | Two actual pinned Contrib tests NOT TESTED, not retroactive PASS. Runtime/OS integration belongs to authorized collector sprint |
| Runtime tests skipped | `test_actual_contrib_accepts_five_methods`; `test_actual_scrape_and_log_rotation_truncation_restart`; pinned binary not configured | Sprint2 real component prerequisite; cannot certify provider/runtime from current config tests |
| Python audit |10 records: Black25.1.0 three, pip25.0.1 six, extra oauthlib4.0.0 one; exact identifiers/fixes retained in SECURITY_FINDINGS.json | Installed development toolchain differs from source pins; no immutable release-image exposure conclusion. Security gate remains BLOCKED; remediation belongs to authorized security work, not this assessment |
| npm audit |Four moderate affected entries: eslint, minimatch, @eslint/config-array, @eslint-community/eslint-utils; dependency edges may share underlying advisories | Four graph entries are not four distinct CVEs. Locks unchanged; no fixes/waivers here |
| Unrestricted existing-file Ruff |19 existing findings versus baseline20; no new signatures in prior assessment | Does not become PASS because frontend lint passes. Relevant CI/security policies unchanged |
| Image/SBOM/licenses |No final immutable release candidate cleared; image scanners/dedicated secrets scanner/actionlint unavailable in prior task environment | NOT TESTED/BLOCKED independent release qualification; generic syntax checks are not equivalent scanners |
| Historical responsiveness RM-DEF-036 | PR82 records matched OTLP750/750 source ordinals, no missing/duplicate sample rows, but global defect NOT REPRODUCED, not fixed. Current retained200-sample direct-SQL probe is not OTLP. Neither is full-system certification | Preserve historical measurements; representative global performance belongs to Sprint9, not a visual-fix claim |
| OC-DEV-503 publication preflight | `pull_release.check_ci` rejects unreviewed trusted workflow mapping; current focused test proves fail-closed behavior | Separate release/operations prerequisite; no workflow weakening, publish or deploy here |
| Hosted CI |Standing Trigger-and-Exit policy: no monitoring/polling or assumed conclusions. Prior run URLs available on PR; no new owner-provided CI result | Local verification separate; final PR update triggers checks and results remain pending for owner |
| Genuine Windows/Linux/EC2/Pentaho |No genuine-provider acceptance in this correction; no real provider credentials/endpoints used | Qualification deferred to applicable approved sprint/authorization; saved config can be development-verified while connectivity/health remains UNVERIFIED |
| CHK001/CHK002/security |FAIL/BLOCKED/BLOCKED; releaseNO-GO | Independent gates must not be promoted to close UI review. Central PostgreSQL spool remains architecture, not implemented by this review |
| Owner/UAT/source decisions |Nine selections Pending, historical controlled-scope approvals intact; formal UAT Pending; D07/D08 Pending;30 original numbered journeys unrecovered | No approvals fabricated. D07/D08 later ETL semantics do not block ordinary resource UI; full traceability remains incomplete |

No additional backend/schema change was made to resolve or hide any finding. Recommendations identify missing implementation separately from missing policy and missing test infrastructure. Passing fixtures and HTTP200 do not imply full-product acceptance.
