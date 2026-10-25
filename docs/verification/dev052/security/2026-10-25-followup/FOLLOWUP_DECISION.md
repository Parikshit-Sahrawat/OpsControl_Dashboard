# DEV-05.2A.2 — 2026-10-25

**Security gate: BLOCKED. Release: NO-GO. No exceptions, deployment, registry
publication, collector upgrade approval, merge or DEV-05.2B authorization.**
The vulnerability acceptance subgate has not passed: unresolved matches remain
visible, including Critical findings in the currently guarded collector.

Issue #68 (including owner comments), SECURITY_GATE_POLICY.md, the original
2026-10-25 SECURITY_DECISION.md and REMEDIATION_DECISION.md were reviewed.
Starting branch commit: `6f8360c5fee09c560e0a82578b1824bda67217da`.
Implementation: `563d8a815ee21740599e57ead159d57308d0ad21` and baseline-context
staging correction `edcb175cedcf6f2abb547b3a14ed3b4f13a90fe6`.
Original product verification baseline remains
`f617cc653a965c2ad1bb7edf9e20237e40044b97`; DEV-05.2 main baseline was
`09a578f70282c7889a515c332c948f1940ae6719`.

## High findings and safe-fix assessment

**110 backend/migration High matches = 14 CVEs = 55 distinct
(CVE, package, installed version, distro advisory) groups**, each affecting both
images. `unique-high-findings.json` retains every group, package/layer evidence,
Debian records, exploit prerequisite, runtime assessment and pending owner
disposition. No match is suppressed or reclassified as legally/security approved.

The live Debian tracker was fetched over verified HTTPS; its hash and URL are in
`vendor-provenance.json`, with pertinent records retained for all 55 groups.
Trixie records remain open with no fixed_version. Vendor "Minor issue",
"postponed" and scanner "wont-fix" are not exceptions to repository policy.
Fresh apt-upgraded Trixie candidates still report **55 High each**. No compatible
vendor fix for these groups was established at observation time.

The 14 CVEs cover Perl POD/archive handling, ncurses infocmp, glibc deprecated
DNS printing and monetary formatting, zlib nonblocking gzip writes, C++ aligned
allocation/priority queues, util-linux mount/nsenter and libacl pathname races.
No direct invocation of the reviewed functions/utilities was found by the retained
source search. That is not an exhaustive native dependency call graph. Essential
glibc/zlib/native libraries remain installed. Runtime probes show UID 10001,
CapEff=0, an unconfigured fstab, SUID mount, and NoNewPrivs=0. infocmp/perl/mount/
nsenter are present; ACL command-line utilities are absent but libacl remains.
Operator privileges, volume mounts and native extension paths remain unapproved.
No blanket non-applicability or exploitability claim follows from these probes.

Official pinned Python 3.12 Bookworm was built as a supported-base alternative
without deleting OS libraries. Its 36 targeted contracts passed, but the exact
image scan reports **3 Critical / 79 High**, versus Trixie's **0 / 55** per image.
Bookworm is **REJECTED, not promoted**. Its Critical matches are CVE-2026-5450
against libc-bin/libc6 (scanf width overflow) and CVE-2025-7458 against libsqlite3-0
(crafted SQL). Raw evidence is retained. Alpine/musl and unsupported hand-patched
libc replacements are NOT TESTED and are not presented as safe fixes.

## Exact available images and scanner coverage

All rows are linux/amd64. IDs below are local immutable image configuration
digests, **not approved deployment registry manifest digests**. `subject-bindings.json`
binds each raw CycloneDX SBOM to the saved archive SHA-256, verified config SHA,
Grype imageID and common archive manifest. All eight archive scans succeeded.

| Role / candidate | Immutable configuration digest | Critical | High | Medium |
|---|---|---:|---:|---:|
| API/remote worker | `sha256:531dd9fb58fd7723dedaceba177a1ea241b5c6834c7c200273eff3c16dd60b4d` | 0 | 55 | 54 |
| Separate migration operation | `sha256:bd8910833cae1071891ee926913fcab49d0dfba336a855e2d3336a9dc27d8801` | 0 | 55 | 54 |
| Static frontend | `sha256:fb9acf2bc1639c247cab2e3a802b69daac3c8d0e9dcbefbd5763ca147f32fd5f` | 0 | 0 | 3 |
| NGINX ingestion gateway | `sha256:df6f3e96d19c6bcdf3ac9518a4fc7318ee79c68f373ce79b41c1d14c7bb819c6` | 0 | 0 | 3 |
| PostgreSQL Alpine evaluation | `sha256:ab20e934b27ba3ff927c1b4c9ff8cf6c32f315f743efe68dd3441182a87fb085` | 0 | 0 | 4 |
| Currently guarded Contrib 0.123.0 | `sha256:f0eaa24275f0eac77186cf0c9b1d1c72c9edde884a7c6bf9e5332ca8b5939d97` | 14 | 68 | 46 |
| Contrib 0.163.2, NOT promoted | `sha256:a64fa52ad3b55378bb62d8642439aaf0ec3abf45a8ddc1ac02bac31eea7a6565` | 0 | 0 | 0 |
| Bookworm alternative, REJECTED | `sha256:b2e1f8187f10563a4a6d5c1cf23eaac60b3af6fe2f3e0c2a1d5f74fb03cdb686` | 3 | 79 | 97 |

The six-role set retaining guarded 0.123.0 has **14 Critical / 178 High** scanner
matches: the requested Python subset contributes 110; the guarded collector adds
68 (62 distinct High advisory IDs). The alternative new-collector candidate set
still has 110 High; it cannot substitute for current guarded-collector risk.
Low/Negligible/Unknown findings are retained in raw JSON and `all-findings.json`.
API/migration, reused frontend/gateway/Postgres and new collector severities are
unchanged versus A.1 with the same DB. `scan-summary.json` includes exact deltas.

Syft **1.55.0**, Grype **0.121.0**, schema **v6.1.10**, DB built
**2026-10-25T06:27:34Z**. Upstream checksums, version JSON, DB status, raw results,
logs and archive hashes are retained. Automatic DB updates were disabled to make
the comparison meaningful. No unsupported platform is certified.

## Production eligibility and identity gaps

API and remote worker share the restricted runtime target. Migrations are a
separate maintenance target, not an API startup operation. Frontend and TLS
gateway are separate final roles. PostgreSQL Alpine remains a locale/restore
compatibility candidate. The agent's guarded collector is retained; 0.163.2 is
evaluation only. **There are no finally approved release images.**

Demo/UAT API images (root/automatic migration/seed/embedded collector), synthetic
fixtures, disposable DEV05/browser/golden-path images and local UAT tools are
excluded from the production set. Node and dependency-builder stages are build
inputs, not final web/API roles. The frontend uses `frontend/Dockerfile.runtime`; its build-only Node stage is
distinguished from NGINX. Gateway uses `deploy/release/Dockerfile.gateway`.
`image-source-inventory.txt` and the unchanged prior source inventories record
Dockerfiles, Compose/deployment/CI references and generated build paths.

`image-inventory.json` records architecture, upstream references and prior source
attribution. New Python candidates were built from the A.2 working tree before
final formatting, so **exact committed-source build attestation is unavailable**;
the parent commit is explicitly not claimed as the entire source tree. Reused
frontend/gateway images retain their prior identity/source attribution. Raw build
logs and evaluated Bookworm Dockerfile remain available. Final source-attested
rebuilds, operator-selected manifests, registry publication authority and final
release manifest digests are **BLOCKED**. Upstream RepoDigests and archive
manifests do not fill that gap. Nothing was published.

## Collector compatibility verdict

**BLOCKED for upgrade; retain 0.123.0 guard.** No upgrade approval was provided.

- Unchanged complete `tests.test_collection_v15` with verified 0.163.2: **12 run,
  11 pass, 1 ERROR** at the existing version guard. This is not a green suite.
- Its unchanged actual runtime test passed startup, scraping, TCP syslog, file
  log rotation/truncation/checkpoint persistence and restart. Compiler/negative
  security contracts also passed.
- Separate generated concurrent five-method probe: **PASS** for HOST_METRICS,
  SERVICES, SYSLOG_RECEIVER, FILE_LOG and METRIC_SCRAPE startup/observations, plus
  rejection of an unknown receiver. Services uses the real Linux process/uptime
  observer and local OTLP serialization; it is emitted by the agent supervisor,
  not a collector process scraper. This is not genuine systemd or Windows service
  certification and does not establish end-to-end authenticated supervisor delivery.
- The first dedicated probe incorrectly expected `process.cpu.time` from SERVICES
  and failed. That failed attempt is retained in `attempts/`; the correction follows
  the actual `service_health.envelope` / supervisor contract, with no production
  assertion or guard change. Probe config uses only a local synthetic sink; it
  does not change generated production TLS/authorization/egress policy.
- Unchanged complete suite with verified guarded **0.123.0: 12 PASS**, zero skips.

## Pip, regression checks and failures

The new bootstrap downloads a fixed reviewed **pip 26.2** wheel over verified
HTTPS and checks SHA-256
`931c303696af6fa3417112103b1cad26890e5a07eccb5b99783700e33f2b8aad`
before loading it under isolated Python. It does not invoke the installed old pip
installer or contact an index during wheel installation. Python/OS/site startup
remains part of the trust base. CA trust is preserved. Online and offline upgrades
from 25.0.1 succeeded; bad-hash rejection passed. Final Python stages remove pip,
ensurepip and caches by path, without executing old pip uninstall code; no essential
runtime library was removed.

Patched paths include the production builder, 13 CI workflows, demo/UAT/test
Dockerfiles, generated golden-path build and Windows/Kubernetes installers.
DEV05 baseline application files and assertions remain pinned; a separate build
tool overlay supplies bootstrap files absent from the original baseline archive.
Context staging was checked without executing the full historical product suite.
Original failed DEV05 evidence and DEV051 remediation evidence are unchanged.

All **six pip advisories remain UNRESOLVED overall** pending platform/legacy/operator
coverage and accountable disposition; scoped Linux fixes are not a global waiver.
Three prior Black fixes remain scoped FIXED, with owner signoff pending. Each of
the nine retains its individual aliases, path, fix version, evidence and reviewer
gap in `nine-advisory-dispositions.json`; see `PIP_DISPOSITIONS.md`.

| Fresh check | Result |
|---|---|
| Local bootstrap/agent/re-enrollment/service projection/activation/hardening | 29 PASS |
| Exact rebuilt API image: agent/re-enrollment/activation/hardening/API-worker | 36 PASS; network none, read-only root; test runner root for mounted fixtures |
| Bookworm alternative: same targeted 36 contracts | 36 PASS, but rejected by scanner results |
| Exact API runtime import as UID 10001; no pip/ensurepip | PASS |
| Exact migration Alembic CLI load, without DB access | PASS; not a fresh migration execution |
| Online and offline verified wheel bootstrap from pip 25.0.1 | PASS |
| Corrupt wheel hash | Rejected before execution; included in 29-test run |
| Original workflow checker and all-workflow actionlint 1.7.7 | exit 0; downloaded tool hash verified |
| Changed Python Black check and shell syntax | PASS |
| Eight image SBOM/scan subject bindings | PASS |
| Original security evidence hashes | 74 + 90 verified; prior DEV05/DEV051 paths unchanged |
| Native Windows, full legacy stack, Kubernetes execution | NOT TESTED; no provider/deployment authority |
| Frontend/full product/provider suites | NOT RERUN; prior evidence remains historical, not fresh acceptance |

Source diff whitespace checks pass. The evidence commit whitespace check flags
trailing spaces in raw BuildKit cache diagnostics; those bytes are retained, not
normalized or represented as a passing artifact-whitespace check. See
`artifact-whitespace-check.log`.

An initial targeted invocation used incorrect relative paths and did not run tests;
the failure and corrected results are retained. Parallel VFS builds exhausted disk
space; completed images and build logs survived. Only specifically identified
task-created unused BuildKit cache records were removed to recover space. The
exact cache IDs and retained resources are listed in `cleanup.json`. This incident
and the rejected base/probe failures are not presented as passes.

## License/NOTICE and remaining release gates

`component-license-assessment.json` retains per-image component/version/PURL,
cataloged licenses, attribution/NOTICE/copyleft/source/relinking review requests
and missing human reviewer. `frontend-lock-license-assessment.json` separately
covers 189 npm lock entries: image cataloging does **not** establish complete
minified-bundle component coverage. `legal-file-presence.json` records paths and
hashes, not legal fulfillment. Guarded 0.123.0 legal-file mapping is not freshly
completed. No component is legally cleared.

Application LICENSE/NOTICE terms are still undeclared in tracked application
source. `LICENSE_DECISION_REQUESTS.md` requests accountable decisions on application
terms, bundled npm attribution, Go transitive notices and OS/Python/copyleft
corresponding source or source offers. These requests are **not legal approval**.

High/Critical applicability/remediation and owner dispositions, complete collector
compatibility/explicit upgrade approval, final source/registry identities,
license/NOTICE/source compliance, datastore compatibility and pre-existing genuine
provider/required-CI/operational gates all remain blocking. No genuine provider
certification is inferred from these local fixtures. Release remains **NO-GO**.
