# DEV-05.2A.3F — native queue recovery feasibility

Date: **2026-10-26 (Asia/Calcutta)**; raw fetch times explicitly UTC.

**CANDIDATE BLOCKED. Phase 1 gate failed; N1–N4 NOT RUN / BLOCKED.**
**CHK-001 FAIL; CHK-002 BLOCKED; SECURITY BLOCKED; RELEASE NO-GO.**
PR #69 remains draft; Issue #68 remains the tracking issue. No product/runtime,
queue, production 0.123.0 pin/guard, checkpoint recovery utility, replay integration,
or unrelated security change was made. No fork/backport/custom binary, runtime
experiment, deployment, image publication, merge, waiver or DEV-05.2B occurred.

## Authorization and baseline

Task-start branch `release/dev-05-2-hardening` was clean at ADR commit
`5fc003b8e026eb4a3479c77084ef8ef894417173`; PR #69 was open/draft on that exact head.
[Governance comment 6414180530](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/issues/68#issuecomment-6414180530)
was retrieved in full. It approves **Parikshit as both collector/runtime engineering
owner and independent verification owner for this isolated feasibility study**.
That resolves role coverage/dual-role governance for this scope. It does not approve
a custom binary/fork, product integration, a guard transition or a release. No new
human-approval blocker is invented for the authorized source review.

The ADR, NATIVE_ACCEPTANCE_PLAN, D QUEUE_DECISION/ROOT_CAUSE and associated source,
raw matrices, receipts and identity references were read. The historical evidence
is preserved: 593 artifact hashes across checkpoint, durability, queue and ADR
manifests verified; the two key historical counts were rechecked from saved PG
exports. This is evidence review, **not a rerun**:

| Historical case | Expected | PG distinct | Missing | Accepted attempts | Physical rows | Duplicate rows |
|---|---:|---:|---:|---:|---:|---:|
| Guarded 0.123.0 staggered production-size queue | 267 | 257 | 10 | 257 | 257 | 0 |
| Newer experimental binary, partial re-enqueue repeat | 267 | 258 | 9 | 258 | 258 | 0 |

The missing guarded IDs are `event-0000`–`event-0009`. The second row comes from
D `boundaries-repeat/boundary_partial_replacement_2` (IDs are run-scoped).
[D's original decision](../2026-10-26-queue/QUEUE_DECISION.md) retains its selected
native 4 PASS / 13 FAIL, historical 91 regression PASS, three bounded 267/267 recoveries
and all rejection/expiry/corruption failures. None are new F test outcomes; no
bounded replay helper ran in F.

## Authoritative source finding

Current official core latest release is **v0.163.0**, commit
`5177a6a85ca3783068077e25aec6cebbe1d50d1f`. Current inspected core main is
`82148555675e5a0a201189cd4220395eb8baa1ad`. Their queue files are **byte-identical**,
SHA-256 `a98bd9990c2405d0b24cdee951ccacec01b58b4dc347ceb6b7c256ceea789d98`.
See [candidate matrix](UPSTREAM_CANDIDATE_MATRIX.md), [source index](SOURCE_INDEX.json)
and original API/decoded source files.

The official distribution latest is **v0.163.2**, release commit
`6c65793ec707f673304e52dfcb642684fda1a048`. Its pinned Contrib manifest identifies
core/Contrib 0.163.0 components. Its release notes describe a Go/CA refresh. The
OTLP/HTTP module explicitly depends on exporterhelper0.163.0. This explains the
previous .163.2 distribution versus .163.0 component naming discrepancy using
authoritative sources; it does **not** supply a persistent-queue correction.
Distribution tags may move per the upstream README, so commit/source hashes were
recorded and tag/commit manifest bytes compared. No new source-to-binary signature
or complete build attestation verification is claimed.

### Required invariant versus inspected behavior

Required: every durably admitted unacknowledged event remains reachable from
committed queue metadata/payload or an independently committed API/PG receipt at
every accepted crash cut. Fsync alone cannot supply atomicity across transactions.

In `source/core163-queue-pinned.txt` / the identical main file:

1. `initClient` loads qmv0 and calls `enqueueNotDispatchedReqs`; legacy migration
   also calls the recovery path. This is not dead code or just the old schema path.
2. Recovery performs `Batch(Get old payloads)` followed by **a different
   `Batch(Delete old payloads)`** (lines463–464 in this source snapshot).
3. Only afterwards it unmarshals each in-memory result and calls `putInternal`
   individually (line487). Each `putInternal` stores the new payload and updated
   write metadata together, but that transaction does not include the earlier
   deletion of the old payloads (lines293–316).
4. Contrib file storage `Batch` calls its own bbolt `db.Update` for each invocation
   (`source/contrib-filestorage-client.txt`, lines118–130). Therefore a committed
   deletion followed by SIGKILL before all replacements leaves an admitted set
   with neither old nor replacement durable payload. The historical nine-ID loss
   corroborates this source-level counterexample; it is not a newly executed test.

PR13330 moves the full-queue check to Offer and consolidates metadata, explaining
ordinary restart improvement. It leaves this destructive recovery window. Core
v0.130.0 source confirms that intermediate behavior; capacity increase, successful
ordinary restart, metadata consolidation and a newer version number are not
accepted as evidence of atomic recovery.

Related PRs were inspected by merge state and patch, not title: PR13126 is closed
unmerged; shutdown proposals 15680/16140 are closed unmerged; ownership 15739,
direct-disk POC15993 and metadata-read startup16230 are open unmerged. None is a
released complete fix. The broad direct-disk POC cannot be built under the current
authorization. Metadata-read errors and Contrib shutdown/backpressure reports are
adjacent limitations, not replacement proof or new runtime findings in this task.

## Conditional execution decision

No authoritative maintained release/artifact with the required correction was
established. **Stop before Phase 2**, as instructed. No candidate was substituted,
no custom build was attempted, and no transaction boundary was silently skipped.

| ADR case | Status | Execution | Fresh observed counts |
|---|---|---|---|
| N1 — unchanged historical control | BLOCKED | NOT RUN: candidate gate is a prerequisite to Phase 2 | null |
| N2 — admission durability cuts | BLOCKED | NOT RUN | null |
| N3 — saturated SIGTERM/SIGKILL restart | BLOCKED | NOT RUN | null |
| N4 — recovery transaction cuts, repeats/partial migration | BLOCKED | NOT RUN | null |

[N1_N4_TEST_MATRIX.json](N1_N4_TEST_MATRIX.json) enumerates the prescribed cuts,
minimum repeats, consecutive crashes and restart/migration obligations, with zero
executions and null observed counts. Planned267 IDs are not reported as produced
IDs. The new feasibility run has **0 PASS / 0 FAIL / 4 BLOCKED parent cases**;
all four are NOT RUN. The mandatory CHK-001 FAIL remains based on actual historical
loss and is not changed by this source-review outcome.

The publisher's Linux amd64 archive checksum was retrieved as a small text
artifact and matched to its release asset digest. No 115 MB binary archive or image
was downloaded, built or executed after source rejection. Historical binary/image
identities, the current published archive SHA, schema, source mapping and the
historical config hash are explicit in [CANDIDATE_PROVENANCE.json](CANDIDATE_PROVENANCE.json).
There is no newly generated candidate config or runtime identity to certify.

## Limitations, failed lookups and support boundary

This review covers the recorded core/contrib source, official distribution
manifests, release entries, queue history and ten complete API search result sets.
It does not prove absence of every unpublished/unindexed or vendor-specific fix.
Official maintenance and publication do not themselves certify loss-free behavior,
LTS support, compatibility, rollback or release readiness. No false support claim
is used to admit a candidate.

Initial broad search requests returned422 because the API required an explicit
issue/pull-request qualifier; successful typed searches replaced them. Guessed
queue_state.go, repository SECURITY.md and generated distribution go.mod paths
returned404; directory enumeration found meta.proto, official README/stability
and manifest/module sources supplied the applicable information. Failed responses
remain in raw evidence. These tooling/path failures are not the decisive blocker:
the exact released recovery source still violates the required invariant.

No independent person is falsely claimed to have witnessed new tests; the user
approved dual-role ownership, while independently generated source inventories and
PG receipts remain mandatory for any future execution. No new receipts exist in
F. CHK-002 protobuf rollback, N5–N8, compatibility, security, license, final-image
and other release gates remain independently pending/blocked.

## Recommended next narrow task

Prepare an **upstream-facing defect report and atomic recovery design review**
using the pinned source counterexample and existing redacted267-ID/partial-requeue
receipts. Ask maintainers to identify a supported released correction or review a
proposal that preserves old payloads until replacements/metadata commit atomically,
or resumes existing durable indices. Require restart-safe migration, error
propagation and witnessed transaction-cut tests, including full capacity. A draft
review brief is in [UPSTREAM_GAP_REPORT.md](UPSTREAM_GAP_REPORT.md); no upstream
message or PR was sent by this task.

Do not build a fork/backport as an implicit next step. A later custom binary needs
separate authorization and support/provenance review. Once a qualifying supported
artifact exists, return to the already-authorized N1–N4 plan with exact identities,
minimum ten repeats per cut, independent receipts and no source replay. If native
safety cannot be established, B can only be considered in a separate task when
its production completeness, retention and gap detection are enforceable. No
replay implementation is part of this task.

## Preservation and cleanup

Only this new evidence directory changes. Prior failed evidence, ADR, all fixtures,
product source, guard/pin and CHK-002 utility remain byte-for-byte unchanged in git.
No Docker container, network, volume, service or synthetic credential was created;
scoped runtime cleanup is **NOT APPLICABLE**, not a fabricated cleanup test PASS.
No images were pruned or published. Fetch attempts, source identities, review
checks and new artifact hashes are retained for reproducibility.
