# Upstream candidate matrix — 2026-10-26 (Asia/Calcutta)

**CANDIDATE BLOCKED. No corrected, authoritative supported candidate was
established. N1–N4 NOT RUN.** This is a source/release review, not new runtime
certification. Statuses refer to the captured API responses, not a permanent claim
about future upstream development. The inspected official projects have active
maintainers/releases; that does not establish an LTS policy, vendor SLA or approval
of any specific recovery behavior.

## Released sources and official distributions

| Source / distribution | Exact revision and support/provenance evidence | Recovery behavior / disposition |
|---|---|---|
| Core v0.123.0 | `open-telemetry/opentelemetry-collector` commit `1ad6912e6cec0c7a81edd231a2a28f11cd2e4994`; historical guarded binary SHA below | Historical product contract, not a new maintained correction. `putInternal` rejects at full capacity after recovery already deleted old keys. Historical 267 / 257/10 FAIL. |
| Core v0.130.0 / PR13330 | Core commit `91ec67dfc1e572180f2a2050d2b204c0b8eb2497`; PR merge `e2954b98139a839d31cd7ae4d826966f33a9180f` | qmv0 consolidation and capacity check moved to Offer; deletion and per-item replacement remain separate transactions. Rejected as a complete correction. No binary qualification here. |
| Core v0.163.0 | Core commit `5177a6a85ca3783068077e25aec6cebbe1d50d1f`; latest non-draft/non-prerelease core release in captured response | Same unsafe recovery sequence. Queue source SHA `a98bd9990c2405d0b24cdee951ccacec01b58b4dc347ceb6b7c256ceea789d98`. Rejected by source invariant. |
| Core main | `82148555675e5a0a201189cd4220395eb8baa1ad` | Queue file is byte-identical to inspected v0.163.0. Unreleased main is not itself a supported replacement artifact; it also retains the gap. |
| Contrib source releases | Latest source release v0.163.0; main snapshot `a4c4c216852c565c0ae09f4ea8be4b2d3466f21b` | File storage Batch uses a separate bbolt Update per call. It does not merge a queue read/delete/re-enqueue sequence into one transaction. No correcting storage alternative established. |
| Official Contrib distribution v0.163.2 | `open-telemetry/opentelemetry-collector-releases` commit `6c65793ec707f673304e52dfcb642684fda1a048`; current latest non-draft/non-prerelease distribution release; pinned manifest and release notes retained | Manifest says distribution 0.163.2 with core/Contrib 0.163.0 modules. Release notes describe Go/CA refresh, not a queue fix. OTLP/HTTP module depends on exporterhelper0.163.0. Rejected: inherited recovery window; historical experimental partial-requeue 258/267/9 corroborates it. |
| Official distribution main | `fa7050c4b41e762f0d986b491438bf46bd3a6005`; manifest captured | No newer safe queue source binding established; development metadata is not a qualified released correction. |
| Official core / OTLP / Prometheus / eBPF distributions at v0.163.2 commit | All listed in official distribution README; individual immutable-commit manifests retained | Use core OTLP/HTTP 0.163.0 where present and do not include the full filelog/syslog/file-storage contract. Neither a different binary name nor an absent component corrects this queue. Rejected as compatible full collector replacements. |
| Official Kubernetes distribution at v0.163.2 commit | Immutable manifest includes filelog/file-storage and core OTLP/HTTP 0.163.0, but no syslog receiver | Same relevant helper lineage and incomplete current five-method component set. No qualifying correction. No Kubernetes scope or runtime testing added. |

The distribution README explicitly warns that its **tags may move**. We resolved
and retained the exact release commit and fetched its manifest by commit, not only
by tag. Tag-manifest and commit-manifest bytes match. Core tag source files were
also fetched again by their resolved commits and compared byte-for-byte.

The prior .163.2-versus-.163.0 naming uncertainty is now explained by authoritative
release metadata: a .163.2 distribution can assemble .163.0 component modules.
That mapping does not fix the queue or establish that all historical/local bytes
match a freshly verified signed distribution. It removes the naming ambiguity;
functional rejection remains the decisive blocker.

## Related changes and proposals evaluated

`merged` is recorded separately from `state`; a closed PR or non-null test merge
SHA is not proof of merge or release. PR descriptions' test claims are author
reports, not tests executed in this task. Complete response/patch files are in
`raw/pr<id>-details.json` and `raw/pr<id>-files.json`.

| Upstream item | Captured status / identity | Why it does not establish an eligible correction |
|---|---|---|
| [PR13330](https://github.com/open-telemetry/opentelemetry-collector/pull/13330) | Merged, `e2954b98139a839d31cd7ae4d826966f33a9180f` | Fixes metadata/size accounting and capacity placement, not atomic recovery. Ordinary restart success is insufficient. |
| [PR13126](https://github.com/open-telemetry/opentelemetry-collector/pull/13126) | Closed, **not merged**; head `918ee7607fa9fa544287db402229494ab1fc13c3` | Alternate metadata-consolidation proposal; patch still reads/deletes/re-enqueues separately. Not a released correction. |
| [PR15680](https://github.com/open-telemetry/opentelemetry-collector/pull/15680) | Closed, **not merged**; head `b2b18d219b9744a5f7eecfb543b213c27e06edce` | Retention of failed in-flight requests during shutdown is a different boundary; patch does not make recovery replacement atomic. |
| [PR16140](https://github.com/open-telemetry/opentelemetry-collector/pull/16140) | Closed, **not merged**; head `859e0aecd4bedd24e3b49e49cae9ff469925404d` | Changes onDone shutdown handling, not the destructive startup sequence. |
| [PR16230](https://github.com/open-telemetry/opentelemetry-collector/pull/16230) / [issue16232](https://github.com/open-telemetry/opentelemetry-collector/issues/16232) | Open/unmerged; head `6569043bc424937f7f85d52a185f9f32c86bfb3c` | Proposed fail-closed metadata-read startup; patch leaves enqueueNotDispatchedReqs unchanged. Important adjacent risk, not an atomic-recovery fix or released binary. |
| [PR15739](https://github.com/open-telemetry/opentelemetry-collector/pull/15739) | Open/unmerged; head `1de3da5eeb8d9694f37b2bceca42a25cc75a8b78` | Pipeline ownership/encoding proposal; not a replacement for recovery transactions. |
| [PR15993](https://github.com/open-telemetry/opentelemetry-collector/pull/15993) | Open/unmerged POC; head `b930d34a4f7f3f7acb0cf79c02e0372d09e06a88` | Broad direct-disk queue prototype, no authoritative released distribution/compatibility qualification. Building it would be an unapproved custom binary; not attempted. |
| [issue8382](https://github.com/open-telemetry/opentelemetry-collector/issues/8382) | Closed | Retry-exhaustion re-enqueue policy discussion is not proof that startup in-flight recovery became atomic. |
| [issue15324](https://github.com/open-telemetry/opentelemetry-collector/issues/15324), [Contrib52067](https://github.com/open-telemetry/opentelemetry-collector-contrib/issues/52067) | Open reports | Outage loss and synchronous-emitter shutdown/backpressure reports are adjacent warning signals. Not reproduced here and not substitutes for the specific queue proof. No receiver workstream expanded. |

Searches covered core issues/PRs for persistent-queue recovery, restart, loss and
atomic changes, plus Contrib restart reports. Ten successful search responses each
report `incomplete_results=false` and return their complete result set (counts in
`RESEARCH_COVERAGE.json`). File history contains 16 commits for the current queue
path. Fifteen core releases and ten distribution release entries were inspected.
This is a bounded authoritative review, not proof that no unpublished, unindexed
or third-party correction exists. No vendor-maintained fork was represented as an
upstream-supported candidate without evidence.

## Artifact identities and unfulfilled qualification fields

- Publisher archive: `otelcol-contrib_0.163.2_linux_amd64.tar.gz`, asset 663156749,
  publisher SHA-256 `cc19dd6a1b85ca694ef16655688e597f693d0e24d2baecdd50e2db597819eeff`.
  The downloaded checksum text agrees with the release asset digest; the checksum
  file's own digest also matches its asset metadata. **The archive was not
  downloaded or independently hashed in this task.**
- Historical experimental binary SHA:
  `dbd12d55073b70add777895457040f8ede59fc1ee7198d6ae179a37087eea8bb`;
  historical image manifest
  `sha256:7f22d2a6748110ffb6a59bc0df448bccbf501cdb667d610ede4c61d3863d5849`.
  These are inherited verified D/A.3 identities, not newly provisioned or signed
  artifact validation in F. No binary or image was pulled/built/executed.
- Guarded historical binary SHA:
  `6bca4ddd928b4b0880f7ec6c16511922f740c497b4efa4b33915b2d54a729213`.
- Legacy queue schema: individual `ri`, `wi`, `di`, `si` keys plus indexed payloads.
  Newer schema: protobuf `qmv0` with item/byte sizes, read/write indices and
  in-flight indices; legacy fallback migration remains. This is separate from
  CHK-002 filelog checkpoint encoding.
- Qualified candidate image/binary identity and generated config hash: **null /
  NOT PROVISIONED or GENERATED**, because the source qualification gate failed.
  Historical baseline config path/hash is separately recorded in
  [CANDIDATE_PROVENANCE.json](CANDIDATE_PROVENANCE.json); it is not a candidate config.

No extra role approval is missing for this bounded study. What is missing is an
authoritative maintained correction satisfying the invariant, followed by its
exact artifact provenance and N1–N4 evidence. Custom binary/fork, integration,
transition and release approvals remain outside this authorization.
