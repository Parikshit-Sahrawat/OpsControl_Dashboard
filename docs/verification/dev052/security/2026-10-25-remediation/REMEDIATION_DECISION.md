# DEV-05.2A.1 remediation — 2026-10-25

**Security gate: BLOCKED. Release: NO-GO. No deployment, merge or DEV-05.2B work.**

Issue #68 (including the owner execution approval), SECURITY_GATE_POLICY.md and the
original DEV-05.2A decision were read in full. Original DEV-05.0/05.1/05.2A evidence
is unchanged. This report records remediation, not an exception or owner signoff.

## Production-eligible candidate set and identity gaps

`deploy/release/image-policy.json` and `production-image-set.json` designate the
candidate role allowlist: restricted backend API/worker runtime, separate production
schema-maintenance target, static frontend, TLS ingestion gateway, PostgreSQL 17
Alpine, and a collector evaluation candidate. Exact image config IDs, registry
RepoDigests where available, architectures, source revisions, archive checksums and
scan exit codes are in `image-inventory.json`. Every candidate is Linux amd64.

Demo bootstrap/root/automatic migration images are not eligible. UAT API/worker and
migration images are not silently promoted: a separate production migration target
now contains migrations, no pip and runs as UID 10001. The demo frontend path,
synthetic fixtures and browser images are excluded. Debian PostgreSQL/ECR references
are declared local/demo paths, not the proposed datastore candidate. These exclusions
are not claims about unknown existing deployments or waivers of their findings.
Selecting Alpine for an existing datastore still needs locale, backup/restore and
migration approval. All excluded baseline Critical/High matches remain in triage.

No final owner-approved registry publication/manifest digests or live deployment
inventory were supplied. Local image config IDs are immutable scan identities, **not
registry manifest digests**. Frontend final backend URL/CSP/ingress settings require
owner-approved values; the isolated build uses reserved example.invalid. Collector
0.163.2 is **evaluation-only**: the application still requires 0.123.0. The candidate
set cannot be promoted as a working approved release without resolving these gaps.

## Implemented hardening

- Backend runtime uses a digest-pinned Python base and separate dependency builder.
  Builder pip is pinned to 26.2. OS security upgrades are applied. Final runtime and
  maintenance targets remove pip, ensurepip and pip cache; application dependencies
  retain their wheel metadata/licenses. UID 10001, import behavior and API command
  are preserved. Final-stage installer removal does not permit runtime package installs.
- New frontend runtime uses a digest-pinned Node 24 builder and updated pinned NGINX
  base. Gateway uses that same patched NGINX base and the unchanged TLS/auth route
  configuration. Alpine packages were upgraded. The first new scan found one High
  curl advisory; curl was unused by the declared runtime/health paths and removed.
  Fresh scans prove absence. No TLS, egress, auth, CSP or worker assertions were relaxed.
- Declared Python CI install steps bootstrap pip 26.2; development Black is pinned
  to 26.10.1. Existing 57-file formatting checks pass after a one-blank-line-only
  agent source adjustment. A separate patched tooling environment has no reported
  vulnerabilities. Legacy/test Docker installers and the initial old-pip bootstrap
  phase remain effective-supply-chain review items, not blanket cleared exclusions.
- Collector 0.163.2 from upstream immutable digest
  `sha256:7f22d2a6748110ffb6a59bc0df448bccbf501cdb667d610ede4c61d3863d5849`
  was evaluated; binary SHA-256
  `dbd12d55073b70add777895457040f8ede59fc1ee7198d6ae179a37087eea8bb`.
  Its raw generated five-method schema validates, but the unchanged application
  version guard rejects it. The old 0.123.0 pin and tests remain unchanged. No
  protocol upgrade, production promotion or claim of native certification occurred.

Implementation commits: `a86ff35` (images/tools), `9a9ef36` (maintenance target),
`cdb8e06` (curl removal and exact-candidate gateway smoke). Full source SHAs are
retained per scanned image. These commits precede this evidence-only addition.

## Before / after, same tool/database snapshot

Syft 1.55.0 and Grype 0.121.0 were retained from checksum-verified releases. Grype
schema v6.1.10 database build is **2026-10-25T06:27:34Z**; updates were disabled for
baseline-comparable scans. Original tool/DB metadata and fresh raw JSON outputs
are retained. Docker archives are saved by image ID and config bytes verified
against that ID before the exact same archive is cataloged/scanned. No severity
filter, ignore list or VEX suppression was applied.

| Role / comparison | Before Critical / High | After Critical / High |
| --- | ---: | ---: |
| Backend runtime | 0 / 55 | 0 / 55 |
| Production migration vs UAT baseline | 0 / 55 | 0 / 55 |
| Frontend | 25 / 101 | 0 / 0 |
| Ingestion gateway | 31 / 121 | 0 / 0 |
| PostgreSQL Alpine | 0 / 0 | 0 / 0 |
| Collector evaluation (not promoted) | 14 / 68 | 0 / 0 |

Counts are scanner matches, not unique vulnerabilities or proven exploitability.
Lower severities remain too: frontend/gateway each have three Medium matches and
PostgreSQL Alpine has four. `all-remaining-findings.json` retains **342** matches of
all severities, including **110 High** matches across backend/maintenance images.

`all-baseline-critical-high-triage.json` contains **779** original Critical/High
match rows, sorted Critical first, with component/version/location, image role,
available fix, candidate comparison, exploit-path assessment and owner disposition.
No excluded demo/UAT match is relabeled fixed. Underlying frontend/gateway/collector
old matches disappear on the new snapshots, but the collector cannot be promoted.

Backend High matches remain in installed Debian OS components: glibc/libc, Perl,
ncurses, util-linux, ACL and GCC runtime libraries. Many have vendor wont-fix/unknown
fix metadata. `apt-get upgrade` does not resolve them. Vendor classification is
not an exception; essential libraries were not forcibly removed. Exact feature,
privilege and attacker-input reachability is not established for each advisory;
accountable review is still PENDING. No applicable High/Critical is waived. A
confirmed applicable unresolved High/Critical means FAIL under policy; incomplete
applicability evidence, image designation and signoff keep this gate BLOCKED.

## All nine original Black/pip dispositions

Reviewer: Codex automated technical evidence review, 2026-10-25. Accountable
security/release approval remains absent. No ACCEPTED_EXCEPTION_WITH_OWNER exists.

| Advisory | Technical disposition and scope |
| --- | --- |
| Black PYSEC-2026-2121 | FIXED in declared patched toolchain by 26.10.1; candidate runtime absent |
| Black PYSEC-2026-2120 | FIXED in declared patched toolchain by 26.10.1; no Black Action path declared |
| Black GHSA-cg8m-r9f2-5wm2 | FIXED in declared patched toolchain by 26.10.1; compatibility/audit passed |
| pip PYSEC-2026-196 | UNRESOLVED overall supply-chain review; final runtime removed, candidate builder/CI patched |
| pip PYSEC-2026-1795 | UNRESOLVED overall; runtime removed, Python data-filter evidence retained, no global fallback exception |
| pip PYSEC-2026-1796 | UNRESOLVED overall; patched builder/CI, legacy/test installer/bootstrap risk still tracked |
| pip PYSEC-2026-2875 | UNRESOLVED overall; patched builder/CI and runtime absence are bounded mitigations |
| pip PYSEC-2026-2876 | UNRESOLVED overall; no blanket self-update/bootstrap-path exemption |
| pip PYSEC-2026-3721 | UNRESOLVED overall; no approval of all possible index/bootstrap/operator paths |

`nine-advisory-dispositions.json` retains every original advisory, aliases, prior
status, applicability, listed fixes and updated evidence. Three technical FIXED
statuses do not assert owner signoff. Host/legacy tooling outside the patched
candidate/declared CI scope was not silently deemed remediated.

## Tests, failures and cleanup

- 44 targeted backend/agent/auth/worker/activation/release-hardening tests: PASS.
- Existing frontend: 36 tests PASS; lint and build PASS.
- Patched Black: existing 57-file compatibility check PASS. Initial formatting
  mismatch was a single blank line; no executable statement/assertion changed.
- Patched pip 26.2 / Black 26.10.1 tooling audit: zero known vulnerabilities reported.
- Read-only, network-none backend imports as UID 10001: PASS; pip, ensurepip and
  Black are absent. Maintenance Alembic CLI loads without connecting to a DB.
- Exact rebuilt gateway image: existing smoke assertions PASS for verified TLS/
  hostname, untrusted CA rejection, unauthorized request rejection, bearer forwarding
  and administration route isolation. Only a test image selector was added; defaults
  and all assertions remain unchanged. All fixture resources were scoped and removed.
- Final frontend NGINX config test: PASS on read-only root with declared writable
  tmpfs paths. Initial invocation omitted /run tmpfs and failed on PID creation;
  that failure is retained, not counted as a pass or fixed by writable root.
- Both unchanged legacy Contrib runtime tests: PASS, two run, zero skips/failures.
- New collector: raw schema validation exit 0; unchanged app version guard BLOCKED.
- Workflow checker exit 0; scanner driver syntax/static checks and six valid JSON
  SBOM/scan pairs PASS. Baseline-to-archive/image identity assertions passed.

The first backend test invocation used the wrong working directory and failed
import setup; corrected backend-directory invocation passed all 44 tests. Initial
curl-bearing snapshots and their raw outputs are preserved under attempts. These
are diagnosed iteration outcomes, not manufactured passes. No unrelated green CI
workflow was manually rerun.

License-file presence was inspected by exporting network-none, never-started
containers at exact image IDs. Each was removed with its own anonymous volumes.
No product service or real database was deployed. Smoke fixtures used only random
synthetic tokens and owned TLS material and removed them. No broad Docker cleanup
was run. Non-running candidate images, verified tools and build caches remain for
review. See cleanup.json and exact resource observations.

## License and NOTICE review

`license-review.json` retains direct/transitive/OS component metadata and unknowns.
`legal-file-presence.json` records paths and SHA-256 of discovered legal files.
Backend/migration each expose 154 matching legal files; frontend/gateway each six;
no matching standalone legal files were found in the PostgreSQL/collector exports.
This is a filename-based presence check, not proof of absence of all embedded
notices or fulfillment of per-component obligations. Minified JS banners, Go
transitive licenses, base OS copyright/source offers, modification notices and
redistribution packaging still require verification. No package is declared legally
cleared. No project-level application LICENSE/NOTICE declaration was found in tracked source (only prior scanner license evidence files). Owner must define the application redistribution terms as well. An accountable human license/security reviewer has not been assigned.

## Remaining blockers / decision

**BLOCKED / NO-GO** remains mandatory: 110 unresolved High matches across two
Python image roles; missing per-advisory applicability decisions and any required
owner risk disposition; six pip supply-chain reviews; new collector compatibility;
missing final registry manifests and operator configuration; datastore locale/
restore compatibility; license/NOTICE signoff; required CI/provider/operational
gates. No release, production deployment, automatic merge or DEV-05.2B transition
is authorized by these results.
