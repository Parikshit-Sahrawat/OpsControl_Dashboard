# Support, provenance and review ownership

Observation date 2026-10-26; exact UTC requests in [FETCH_LOG.json](FETCH_LOG.json).
**No qualifying supported native candidate. No upstream contact or commitment.**
All sources are authoritative public repositories; open PR authors' claims are
attributed, not adopted as executed tests. Current tag resolutions were refreshed;
source citations use immutable commits, not mutable `main` or image tags.

## Released/main source mapping

| Repository/channel | Exact identity | Fresh evidence and disposition |
|---|---|---|
| Core latest v0.163.0 | `5177a6a85ca3783068077e25aec6cebbe1d50d1f` | [tag resolution](raw/core-tag.json), [release](raw/core-latest.json), [queue](source/core163-queue.txt). Official non-draft/non-prerelease; destructive recovery remains |
| Core main | `82148555675e5a0a201189cd4220395eb8baa1ad` | [head](raw/core-main.json), [queue](source/core-main-queue.txt). Identical queue bytes to latest release, not a new released correction |
| Contrib latest v0.163.0 | `df849b5403c041d5e799e7846392a6f18b0b55ae` | [resolution](raw/contrib-tag.json), [release](raw/contrib-latest.json), [storage implementation](source/storage-client.txt). Each Batch executes its own bbolt Update |
| Contrib main | `a4c4c216852c565c0ae09f4ea8be4b2d3466f21b` | [head](raw/contrib-main.json); ownership/docs refreshed, not a correction claim |
| Official Contrib distribution v0.163.2 | `6c65793ec707f673304e52dfcb642684fda1a048` | [resolution](raw/dist-tag.json), [release](raw/dist-latest.json), [manifest](source/dist-manifest.txt). Go/CA refresh; 0.163.0 components, including OTLP/HTTP; [its module](source/otlphttp-mod.txt) depends on exporterhelper0.163.0 |
| Distribution main | `fa7050c4b41e762f0d986b491438bf46bd3a6005` | [head](raw/dist-main.json). No new released corrected distribution established |

The queue SHA-256 is
`a98bd9990c2405d0b24cdee951ccacec01b58b4dc347ceb6b7c256ceea789d98` at both core
identities. [SOURCE_INDEX.json](SOURCE_INDEX.json) records decoded source SHA-256,
Git blob SHA-1 and immutable API source links; blob identities were verified.
The storage implementation was fetched by v0.163.0 and independently bound to its
recorded resolved commit and Git blob; no tag mutability is treated as assurance.
The proposed storage contract is separately reviewed in [design options](ATOMIC_RECOVERY_DESIGN_OPTIONS.md).

## Adjacent upstream changes — not qualified corrections

| PR | Refreshed state / exact identity | Relevance and rejection reason |
|---|---|---|
| [13330](https://github.com/open-telemetry/opentelemetry-collector/pull/13330) | Merged; merge `e2954b98139a839d31cd7ae4d826966f33a9180f` | Consolidated metadata/capacity correction; old-delete/per-item-replacement gap remains. Historical ancestry puts it in v0.130.0, not v0.129.0; neither tag is newly binary-tested |
| [13126](https://github.com/open-telemetry/opentelemetry-collector/pull/13126) | Closed, **unmerged**; head `918ee7607fa9fa544287db402229494ab1fc13c3` | Earlier consolidated metadata proposal; no supported release from this PR |
| [15680](https://github.com/open-telemetry/opentelemetry-collector/pull/15680) | Closed, **unmerged**; head `b2b18d219b9744a5f7eecfb543b213c27e06edce` | Failed-export shutdown retention; historical maintainer interest does not mean merged/supported atomic startup recovery |
| [16140](https://github.com/open-telemetry/opentelemetry-collector/pull/16140) | Closed, **unmerged**; head `859e0aecd4bedd24e3b49e49cae9ff469925404d` | Related shutdown proposal, changes requested; not the old-key retirement boundary |
| [15739](https://github.com/open-telemetry/opentelemetry-collector/pull/15739) | Open, **unmerged**; head `1de3da5eeb8d9694f37b2bceca42a25cc75a8b78` | Pipeline ownership on decoding; no atomic recovery implementation/support |
| [15993](https://github.com/open-telemetry/opentelemetry-collector/pull/15993) | Open **draft**, unmerged; head `b930d34a4f7f3f7acb0cf79c02e0372d09e06a88` | Broader disk queue POC, completion-frontier author claims, no released distribution or reviewed proof of this migration invariant |
| [16230](https://github.com/open-telemetry/opentelemetry-collector/pull/16230) | Open, **unmerged**; head `6569043bc424937f7f85d52a185f9f32c86bfb3c` | Fails startup on metadata read error; does not change destructive re-enqueue. No submitted reviews in captured response |

Raw `pr<number>.json`, `-comments.json`, `-reviews.json` and selected `-inline.json`
preserve current state and comment context. The existing
[F candidate matrix](../2026-10-26-native-feasibility/UPSTREAM_CANDIDATE_MATRIX.md)
and immutable patches remain evidence for source-level exclusions. Closed is not
merged; a populated merge-commit field is not used instead of the `merged` flag.

Actual review evidence, without inventing consensus:

- [POC author completion-position explanation](https://github.com/open-telemetry/opentelemetry-collector/pull/15993#issuecomment-6041392483)
  claims at-least-once restart behavior and acknowledges out-of-order duplicates.
  [Their later review request](https://github.com/open-telemetry/opentelemetry-collector/pull/15993#issuecomment-6127585713)
  still asks about leaving draft. Captured inline reviews discuss implementation
  details; none certify our full admission/fsync, migration or interrupted-cut
  invariant. Its benchmark describes periodic Sync rather than per-admission
  fsync: supported durable-admission semantics require explicit clarification.
- [Shutdown PR review](https://github.com/open-telemetry/opentelemetry-collector/pull/15680#pullrequestreview-5319189549)
  by `dmitryax` distinguishes retry/shutdown behavior and expected terminal drops.
  [An earlier merge intention](https://github.com/open-telemetry/opentelemetry-collector/pull/15680#issuecomment-5712966200)
  from `mx-psi` is not a completed merge or commitment to this different invariant.
- [Ownership PR review](https://github.com/open-telemetry/opentelemetry-collector/pull/15739#pullrequestreview-4876592292)
  requests an end-to-end ownership test. That cannot establish atomic recovery.
- Metadata issue [16232](raw/issue16232.json) and outage issue
  [15324](raw/issue15324.json) are related reports, not our newly submitted issue
  or evidence that a maintainer accepted this exact gap.

## Exact proposed review target and ownership

Proposed public target, **not submitted**:
<https://github.com/open-telemetry/opentelemetry-collector/issues/new?template=bug_report.yaml>.
Select component `exporter/exporterhelper`. The
[captured form](source/bug-template.txt) routes bug reports for triage. A new issue
would describe the destructive startup boundary and cross-reference PR13330,
PR15993 and PR16230 as related, not claim that any of them tracks an accepted fix.
If triagers prefer an existing issue or RFC, follow their direction after separate
authorization; do not create parallel unsolicited comments.

| Role / proposed consult | Authoritative ownership evidence | Commitment |
|---|---|---|
| Core exporterhelper design review: Bogdan Drutu (`bogdandrutu`), Dmitrii Anoshin (`dmitryax`), `open-telemetry/collector-approvers` | [Core CODEOWNERS](source/core-owners.txt), line68; [core README](source/core-readme.txt), maintainers list | PENDING; recorded ownership only, not assignment or signoff |
| Core storage API: `swiatekm` and Collector approvers | Core CODEOWNERS line85 | PENDING transaction/durability contract review |
| Contrib file-storage implementation: `swiatekm`, `VihasMakwana`, Contrib approvers | [Contrib CODEOWNERS](source/contrib-owners.txt), line140; [metadata](source/storage-metadata.txt), beta extension, seeking additional owner | PENDING backend guarantees, error/rollback review |
| Official distribution/release channel | `open-telemetry/opentelemetry-collector-releases`; core source release links official binary release channel; [contributing guide](source/core-contributing.txt) distinguishes source consumers/end-users | Corrected release, support duration/backport policy and immutable artifact mapping PENDING |

Current upstream maintenance/ownership is not an LTS guarantee, vendor SLA,
accepted review request, or project production approval. No named maintainer has
been contacted by this task. Human reviewer assignment and intended support
commitment for the exact correction must be obtained explicitly.

## Artifact identity distinctions and search limits

The refreshed release API advertises Linux amd64 archive
`otelcol-contrib_0.163.2_linux_amd64.tar.gz`, asset663156749, 115296360bytes,
publisher digest `sha256:cc19dd6a1b85ca694ef16655688e597f693d0e24d2baecdd50e2db597819eeff`.
G did not download/hash/verify that archive or any binary/signature. F separately
checked publisher checksum text; see [F provenance](../2026-10-26-native-feasibility/CANDIDATE_PROVENANCE.json).

Historical binary SHAs: guarded0.123.0
`6bca4ddd928b4b0880f7ec6c16511922f740c497b4efa4b33915b2d54a729213`;
experimental0.163.2
`dbd12d55073b70add777895457040f8ede59fc1ee7198d6ae179a37087eea8bb`.
Historical candidate image manifest
`sha256:7f22d2a6748110ffb6a59bc0df448bccbf501cdb667d610ede4c61d3863d5849`
and image config `sha256:a64fa52ad3b55378bb62d8642439aaf0ec3abf45a8ddc1ac02bac31eea7a6565`
are retained references, not a newly qualified G image. There is **no selected
candidate binary or generated config hash** (null, not fabricated).

G refreshed latest releases/main/tag mappings in all three repositories, seven
specific PRs with reviews/comments, relevant inline reviews, two issues, and six
typed issue/PR searches (recovery, atomic and updates since2026-10-26). Search
totals/pagination are recorded in [RESEARCH_REVIEW.json](RESEARCH_REVIEW.json).
F's broader historical search remains unchanged. Searches are finite, indexed and
not proof of absence of every possible vendor or unpublished correction. A failed
initial `storage/client.go` lookup is retained; directory discovery located the
actual `storage.go`. No failed request is silently relabelled successful.
