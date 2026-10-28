# DEV-05.2A.3 — collector compatibility evidence, 2026-10-25

**Security BLOCKED; collector promotion BLOCKED; release NO-GO.**
No production guard change, registry publication, deployment, merge, risk waiver
or DEV-05.2B transition. PR #69 remains draft; Issue #68 remains open.

The compatibility plan, security policy, prior followup evidence and Issue #68
authorization were reviewed. The existing branch was fast-forwarded to owner
planning commit `0d186819b40c9aa0046b5d5d4781731f832570f5`. Implementation commit:
`e8e4c055ebd0503da4fccef35cc4582e9d575201` and
`37bcdd1e6ee61a1dd29bfaaeabff4abafff607ee`.
Original product baseline remains `f617cc653a965c2ad1bb7edf9e20237e40044b97`;
DEV-05.2 main baseline remains `09a578f70282c7889a515c332c948f1940ae6719`.

## What changed

An **explicit verification-only overlay** proposes exact 0.163.2 backend/supervisor
version checks and a version-specific checkpoint setting. Separate pinned binary
provisioning, source staging, bounded authenticated E2E lab, guard negatives and
image/archive scans are reproducible under `verification/dev052/collector_compat/`.
The default backend, Agent, installers, package scripts, CI and legacy provisioner
retain 0.123.0. See [impact review](IMPACT_REVIEW.md) for all affected contracts and
the proposed diff. No application assertion or transport policy was weakened.

Actual testing found a new compatibility defect: default 0.163.2 protobuf
checkpoints prevent 0.123.0 rollback startup. The failed version-only experiment is
retained. The final experimental overlay explicitly disables
`filelog.protobufCheckpointEncoding` when validating/starting 0.163.2, retaining
legacy JSON writes. The same populated state then starts successfully on 0.123.0.
Conversion of checkpoints from the failed/default experiment was NOT TESTED;
these results do not approve a coordinated production downgrade.

## Exact results

| Run / evidence | Result |
|---|---|
| Unchanged baseline `tests.test_collection_v15`, verified 0.123.0 | **12 PASS**, before implementation |
| Same unchanged suite, verified 0.163.2 | **12 run: 11 PASS, 1 ERROR** at preserved 0.123.0 guard |
| Version-only experimental full suite | **53 PASS**, but E2E rollback failed; not full compatibility |
| Final checkpoint-compatible experimental full suite | **53 PASS**, zero skips/errors/failures |
| Exact version negative tests | **2 PASS**, ten neighbor/prerelease/custom/old-version subcases rejected |
| Checksum mismatch provisioning test | **2 PASS**, rejected before execution/source staging or offline binary promotion |
| Separate candidate online extraction and offline provisioning | **PASS**, identical pinned binary SHA-256 |
| Final five-method authenticated lab | **PASS** in `lab-attempt-4/` (prior successful attempt 3 retained); real supervisor/collector/TLS API/PostgreSQL |
| Unchanged Agent API/DB acceptance probe | **PASS**: expiry/single use, rotation/revocation, re-enrollment, checksum/method/tenant scopes, receipt verification, deduplication, audit |
| Fresh immutable-image CycloneDX + Grype | **2 PASS**, config/archive/binary/SBOM/scan binding checked |
| Helper Python formatting, syntax and CLI help | **PASS**; raw patch context spaces preserved, not normalized |
| Prior security evidence integrity | **260 hashes verified**; DEV05/DEV051/prior A/A.1/A.2 evidence unchanged |
| Genuine systemd, Windows, Pentaho/native providers | **NOT TESTED / certification BLOCKED** |
| Final source-attested product image/registry identity and full coordinated transition/rollback | **BLOCKED** pending implementation approval and remaining acceptance |

The full suite includes collection, Agent lifecycle/re-enrollment, managed
telemetry, access control and API worker modules. Counts are per run, not additive
unique-test totals. Verbose logs and `test-matrix.json` retain names and failures.

The final lab exercised HOST_METRICS, SERVICES, SYSLOG_RECEIVER, FILE_LOG and
METRIC_SCRAPE concurrently. PostgreSQL independently proves host CPU, actual Linux
process counts attributed to SERVICES, controlled scrape and TCP syslog records.
Each file marker appears **exactly once** across initial delivery, rotation,
truncation, checkpoint restart and a real API stop/restart. Applied and verified
revisions/checksums remain distinct. Services is emitted by
`service_health.envelope` through the authenticated supervisor path, not by a
replacement process scraper or invented collector metric.

Actual negatives reject invalid supervisor credentials, malformed/foreign-method
envelopes, untrusted TLS CA, wrong hostname, HTTP management and redirects before
target contact. An owned live target on a disjoint internal network is unreachable;
no unowned target was probed. TCP/UDP listeners in both IPv4/IPv6 tables remain loopback-only. The runner uses
UID 1000, read-only root, no capabilities, no-new-privileges, **512 MiB / 1 CPU /
128 PIDs**, with bounded tmpfs. This is synthetic workload evidence, not production
load/capacity or genuine host-provider certification.

## Immutable artifacts and security delta

| Artifact | Identity |
|---|---|
| Candidate upstream image | `otel/opentelemetry-collector-contrib:0.163.2@sha256:7f22d2a6748110ffb6a59bc0df448bccbf501cdb667d610ede4c61d3863d5849` |
| Candidate Linux amd64 image config | `sha256:a64fa52ad3b55378bb62d8642439aaf0ec3abf45a8ddc1ac02bac31eea7a6565` |
| Candidate binary SHA-256 | `dbd12d55073b70add777895457040f8ede59fc1ee7198d6ae179a37087eea8bb` |
| Guarded image config | `sha256:f0eaa24275f0eac77186cf0c9b1d1c72c9edde884a7c6bf9e5332ca8b5939d97` |
| Guarded binary SHA-256 | `6bca4ddd928b4b0880f7ec6c16511922f740c497b4efa4b33915b2d54a729213` |

Fresh scans: candidate **zero matches**; guarded **14 Critical / 68 High / 46 Medium /
9 Low / 2 Unknown**. This is unchanged versus A.2 with the same frozen database;
the cross-image improvement is not an actual production promotion/remediation.
Backend/migration's **110 unresolved High matches** and six pip dispositions are
unchanged historical blockers; they were not rescanned or silently waived here.

Syft **1.55.0**, Grype **0.121.0**, DB schema **v6.1.10**, built
**2026-10-25T06:27:34Z**. Raw JSON, tool versions, DB metadata, archive SHA-256,
binary-in-image hashes and SBOM/scan hashes are retained in subject bindings.
Archive manifest digests and local config IDs are not approved final product
registry manifests. No new product release image was built or published. The
fixture uses archived source plus the exact patch hash; it is not a release image.

Upstream image labels name releases revision
`6c65793ec707f673304e52dfcb642684fda1a048`. Its fetched distribution manifest
identifies release 0.163.2 and Contrib 0.163.0 components; canonical checkpoint/gate
source snapshots and hashes support the encoding diagnosis. Labels are recorded
provenance, not an independent signature or release-owner approval.

## Failures, cleanup and remaining gates

Failed attempts remain intact: initial baseline import working-directory error;
lab attempt 1's unsupported internal-network published-port lookup; lab attempt 2's
real protobuf-checkpoint rollback failure; source-tag lookup, later runner CLI
static-check setup errors and derived legal-inventory JSON-stream normalization.
The original legal-inventory stream is retained; raw scanner JSON was not changed. Lab attempt 2 also reached zero free VFS space, but the
recorded rollback error was a decoding failure, not relabeled as a disk failure.
The final stdlib-only runner reduced writable-layer space use. No unrelated images
or caches were pruned. Unified-diff blank context lines trigger whitespace warnings
and are preserved as valid patch bytes, not counted as a clean global whitespace
check. Failed assertions were neither removed nor turned into passes.

All four labs removed only their containers, owned anonymous volumes, two
networks, private credentials, database and TLS files. Extraction containers,
temporary online/offline binary copies and scan archives were removed after
redacted evidence preservation. `cleanup.json` records successful cleanup and
empty task-resource observations. Existing review images/tools remain non-running.

License inventory covers **2,025 SBOM component records**. Upstream Apache-2.0 does
not clear transitive licenses. Full component NOTICE/attribution/source-offer
mapping, distribution assembly and accountable legal signoff remain incomplete;
application LICENSE/NOTICE terms are still undecided. Copied source headers and
their upstream Apache license are retained. No legal approval is claimed.

Baseline hosted checks at `0d18681` include **failed `calico-networkpolicy`**;
`baseline-hosted-checks.json` preserves its link. It was not rerun or fixed within
this collector task. Final-head hosted/required checks need separate assessment.
Genuine Windows/systemd/provider certification, coordinated version/packaging/state
migration approval, final image identity, legal/security review and pre-existing
release-wide gates remain blockers. **Keep the 0.123.0 production guard; do not
promote the experiment or advance DEV-05.2B.**
